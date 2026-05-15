#!/usr/bin/env python3
"""Tier 5.45 — Healthy-NEST Rebaseline Decision Contract.

This contract closes the repo-alignment remediation loop by predeclaring how to
rerun the organism-development mechanisms after the NEST fallback correction.
It is contract-only: no mechanism promotion, baseline freeze, or benchmark claim
is made by this file.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"

from coral_reef_spinnaker.config import LifecycleConfig

TIER = "Tier 5.45 — Healthy-NEST Rebaseline Decision Contract"
RUNNER_REVISION = "tier5_45_healthy_nest_rebaseline_contract_20260514_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_45_20260514_healthy_nest_rebaseline_contract"
NEXT_GATE = "Tier 5.45a — Healthy-NEST Rebaseline Scoring Gate"

EXPERIMENTAL_FLAGS = [
    "enable_neural_heritability",
    "enable_stream_specialization",
    "enable_variable_allocation",
    "enable_task_fitness_selection",
    "enable_operator_diversity",
    "enable_synaptic_heritability",
    "enable_niche_pressure",
    "enable_signal_transport",
    "enable_energy_economy",
    "enable_maturation",
    "enable_vector_readout",
    "enable_alignment_pressure",
    "enable_task_coupled_selection",
    "enable_causal_credit_selection",
    "enable_cross_polyp_coupling",
]

REFERENCE_MODELS = [
    "v2_6_predictive_reference",
    "organism_defaults_experimental_off",
    "persistence_baseline",
    "online_linear_or_lag_ridge",
    "esn_or_random_reservoir",
]

TASKS = [
    "sine",
    "mackey_glass",
    "lorenz",
    "narma10",
]

SEEDS = [42, 43, 44]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(v: Any) -> Any:
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, dict):
        return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)):
        return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json_safe(row.get(k, "")) for k in fieldnames})


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "criterion": name,
        "value": json_safe(value),
        "rule": rule,
        "passed": bool(passed),
        "note": note,
    }


def lifecycle_flag_defaults() -> dict[str, bool]:
    cfg = LifecycleConfig()
    available = {field.name for field in fields(LifecycleConfig)}
    return {flag: bool(getattr(cfg, flag)) for flag in EXPERIMENTAL_FLAGS if flag in available}


def build_contract() -> dict[str, Any]:
    single_feature_conditions = [
        {
            "name": flag.removeprefix("enable_"),
            "config_overrides": {f"lifecycle.{f}": (f == flag) for f in EXPERIMENTAL_FLAGS},
            "role": "single opt-in mechanism candidate",
        }
        for flag in EXPERIMENTAL_FLAGS
    ]
    return {
        "question": (
            "After the NEST fallback correction and repo-alignment cleanup, do any "
            "currently opt-in organism-development mechanisms improve prediction or "
            "a predeclared substrate metric enough to justify promotion beyond the "
            "v2.7 diagnostic snapshot?"
        ),
        "hypothesis": (
            "At least one opt-in mechanism or the full opt-in stack will improve either "
            "locked predictive metrics or a predeclared substrate metric under healthy "
            "NEST with zero synthetic fallback, while separating from the relevant sham."
        ),
        "null_hypothesis": (
            "Healthy-NEST reruns show that the opt-in mechanism stack changes internal "
            "state descriptors or population metadata but does not improve predictive "
            "performance or sham-separated substrate metrics. In that case, v2.6 remains "
            "the predictive baseline and v2.7 remains diagnostic only."
        ),
        "reference_models": REFERENCE_MODELS,
        "tasks": TASKS,
        "seeds": SEEDS,
        "run_lengths": {
            "primary_steps": 2000,
            "optional_long_run_steps": [8000],
            "long_run_rule": "Only run long horizon if the 2000-step gate shows a candidate worth stress-testing.",
        },
        "conditions": {
            "reference_conditions": [
                {
                    "name": "v2_6_predictive_reference",
                    "role": "current predictive benchmark baseline; standalone/reference path if applicable",
                    "promotion_rule": "Only superseded if a candidate beats it under locked metrics and external-baseline context.",
                },
                {
                    "name": "organism_defaults_experimental_off",
                    "role": "current conservative NEST organism with all experimental flags false",
                    "config_overrides": {f"lifecycle.{flag}": False for flag in EXPERIMENTAL_FLAGS},
                },
            ],
            "single_feature_conditions": single_feature_conditions,
            "full_stack_condition": {
                "name": "full_opt_in_stack",
                "config_overrides": {f"lifecycle.{flag}": True for flag in EXPERIMENTAL_FLAGS},
                "role": "interaction stressor; cannot promote individual mechanisms without single-feature support or follow-up ablation.",
            },
            "external_baselines": [
                "persistence_baseline",
                "online_linear_or_lag_ridge",
                "esn_or_random_reservoir",
            ],
        },
        "required_metrics": [
            "mse",
            "nmse",
            "tail_mse",
            "test_correlation",
            "per_polyp_participation_ratio",
            "per_neuron_participation_ratio",
            "rank95_or_effective_rank",
            "population_size_trajectory",
            "birth_death_counts",
            "lineage_diversity",
            "fallback_counters",
            "sim_run_failures",
            "summary_read_failures",
            "synthetic_fallbacks",
            "resetkernel_recoveries",
            "seed_mean_median_std_worst",
            "rank_against_external_baselines",
        ],
        "required_controls_and_shams": [
            "all experimental flags off",
            "single-feature opt-in isolation",
            "full-stack interaction stressor",
            "matched-capacity or population-size sham where a lifecycle feature increases population",
            "feature-specific ablation or shuffle for any candidate that appears beneficial",
            "zero-fallback healthy-NEST gate before interpreting PR or MSE",
        ],
        "promotion_rules": {
            "predictive_baseline_supersession": (
                "Candidate must improve locked aggregate MSE versus v2.6 by at least 5%, "
                "show no material task regression above 10%, survive all seeds, and be "
                "interpreted against persistence/lag-ridge/ESN baselines."
            ),
            "organism_predictive_candidate": (
                "Candidate improves the conservative organism baseline by at least 5% "
                "aggregate MSE with no material regression, but does not supersede v2.6. "
                "This authorizes a repair/promotion tier, not a baseline freeze."
            ),
            "substrate_candidate": (
                "Candidate improves PR/rank/lineage diversity by a predeclared margin "
                "with sham separation and zero fallback, but does not improve MSE. This "
                "may be kept as substrate evidence only, not public usefulness evidence."
            ),
            "no_promotion": (
                "No candidate improves locked prediction or sham-separated substrate "
                "metrics. v2.6 remains predictive baseline; v2.7 remains diagnostic."
            ),
        },
        "outcome_classes": [
            "predictive_baseline_candidate",
            "organism_predictive_candidate",
            "substrate_only_candidate",
            "full_stack_interaction_only",
            "no_promotion_confirmed",
            "blocked_by_fallback_or_backend_instability",
        ],
        "expected_artifacts_for_scoring_gate": [
            "tier5_45a_results.json",
            "tier5_45a_report.md",
            "tier5_45a_summary.csv",
            "tier5_45a_seed_runs.csv",
            "tier5_45a_model_task_metrics.csv",
            "tier5_45a_mechanism_decisions.csv",
            "tier5_45a_backend_diagnostics.json",
        ],
        "claim_boundary": (
            "Contract only. This tier does not prove a mechanism, freeze a baseline, "
            "claim hardware transfer, claim public usefulness, or claim AGI/ASI relevance."
        ),
        "next_gate": NEXT_GATE,
    }


def write_report(path: Path, payload: dict[str, Any]) -> None:
    contract = payload["contract"]
    rows = [
        f"# {TIER}",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Outcome: `{payload['outcome']}`",
        f"- Runner revision: `{RUNNER_REVISION}`",
        f"- Next gate: `{NEXT_GATE}`",
        "",
        "## Question",
        "",
        contract["question"],
        "",
        "## Conditions",
        "",
        f"- Reference models: `{', '.join(contract['reference_models'])}`",
        f"- Tasks: `{', '.join(contract['tasks'])}`",
        f"- Seeds: `{', '.join(str(s) for s in contract['seeds'])}`",
        f"- Experimental flags: `{len(EXPERIMENTAL_FLAGS)}` current `LifecycleConfig` opt-in flags",
        "",
        "## Promotion Boundary",
        "",
        contract["claim_boundary"],
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for c in payload["criteria"]:
        rows.append(f"| {c['name']} | `{c['value']}` | `{c['rule']}` | {'yes' if c['passed'] else 'no'} |")
    rows.extend([
        "",
        "## Decision",
        "",
        "This contract authorizes Tier 5.45a scoring only. Promotion requires the scoring gate, sham separation, zero fallback, and documentation updates.",
        "",
    ])
    path.write_text("\n".join(rows), encoding="utf-8")


def run(output_dir: Path | None = None) -> dict[str, Any]:
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    contract = build_contract()
    actual_defaults = lifecycle_flag_defaults()
    available_fields = {field.name for field in fields(LifecycleConfig)}
    missing_flags = [flag for flag in EXPERIMENTAL_FLAGS if flag not in available_fields]
    enabled_defaults = [flag for flag, enabled in actual_defaults.items() if enabled]

    criteria = [
        criterion("question locked", bool(contract["question"]), "true", bool(contract["question"])),
        criterion("experimental flags exist", missing_flags, "[]", not missing_flags),
        criterion("experimental defaults off", enabled_defaults, "[]", not enabled_defaults),
        criterion("all single-feature conditions declared", len(contract["conditions"]["single_feature_conditions"]), f"== {len(EXPERIMENTAL_FLAGS)}", len(contract["conditions"]["single_feature_conditions"]) == len(EXPERIMENTAL_FLAGS)),
        criterion("v2.6 reference included", "v2_6_predictive_reference" in contract["reference_models"], "true", "v2_6_predictive_reference" in contract["reference_models"]),
        criterion("organism conservative baseline included", "organism_defaults_experimental_off" in contract["reference_models"], "true", "organism_defaults_experimental_off" in contract["reference_models"]),
        criterion("external baselines included", len(contract["conditions"]["external_baselines"]), ">= 3", len(contract["conditions"]["external_baselines"]) >= 3),
        criterion("standard tasks included", contract["tasks"], "contains sine, MG, Lorenz, NARMA10", all(task in contract["tasks"] for task in TASKS)),
        criterion("three seeds locked", contract["seeds"], "== [42, 43, 44]", contract["seeds"] == SEEDS),
        criterion("zero fallback metric required", "synthetic_fallbacks" in contract["required_metrics"], "true", "synthetic_fallbacks" in contract["required_metrics"]),
        criterion("fallback-blocked outcome defined", "blocked_by_fallback_or_backend_instability" in contract["outcome_classes"], "true", "blocked_by_fallback_or_backend_instability" in contract["outcome_classes"]),
        criterion("no baseline freeze in contract", "contract_only", "no freeze claim", True),
    ]
    status = "pass" if all(c["passed"] for c in criteria) else "fail"
    outcome = "healthy_nest_rebaseline_contract_locked" if status == "pass" else "healthy_nest_rebaseline_contract_blocked"
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "outcome": outcome,
        "criteria": criteria,
        "criteria_passed": sum(1 for c in criteria if c["passed"]),
        "criteria_total": len(criteria),
        "experimental_flags": EXPERIMENTAL_FLAGS,
        "lifecycle_default_values": actual_defaults,
        "contract": contract,
        "output_dir": str(output_dir),
    }

    write_json(output_dir / "tier5_45_results.json", payload)
    write_json(output_dir / "tier5_45_contract.json", contract)
    write_csv(
        output_dir / "tier5_45_summary.csv",
        [
            {
                "status": status,
                "outcome": outcome,
                "criteria_passed": payload["criteria_passed"],
                "criteria_total": payload["criteria_total"],
                "experimental_flag_count": len(EXPERIMENTAL_FLAGS),
                "next_gate": NEXT_GATE,
            }
        ],
    )
    write_csv(
        output_dir / "tier5_45_conditions.csv",
        [
            {
                "condition": cond["name"],
                "role": cond["role"],
                "enabled_flag": flag,
            }
            for flag, cond in zip(EXPERIMENTAL_FLAGS, contract["conditions"]["single_feature_conditions"])
        ],
    )
    write_report(output_dir / "tier5_45_report.md", payload)
    write_json(
        output_dir / "tier5_45_latest_manifest.json",
        {
            "tier": TIER,
            "status": status,
            "outcome": outcome,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": payload["generated_at_utc"],
            "artifacts": {
                "results_json": str(output_dir / "tier5_45_results.json"),
                "contract_json": str(output_dir / "tier5_45_contract.json"),
                "report_md": str(output_dir / "tier5_45_report.md"),
                "summary_csv": str(output_dir / "tier5_45_summary.csv"),
                "conditions_csv": str(output_dir / "tier5_45_conditions.csv"),
            },
        },
    )
    return payload


def main() -> int:
    payload = run()
    print(json.dumps({
        "status": payload["status"],
        "outcome": payload["outcome"],
        "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
        "output_dir": payload["output_dir"],
    }, indent=2))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
