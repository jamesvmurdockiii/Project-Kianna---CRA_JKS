#!/usr/bin/env python3
"""Tier 7.4d - cost-aware policy/action held-out usefulness contract.

Tier 7.4c froze v2.4 as a host-side software baseline for cost-aware
policy/action selection after a local utility diagnostic and full compact
regression. This tier does not score that baseline. It pre-registers the
held-out/public action-cost evaluation before any scoring so later results
cannot be rescued by threshold tuning, same-subset policy selection, or private
task drift.

Boundary: contract only. This is not public usefulness evidence, not a scoring
run, not a new baseline freeze, and not hardware/native transfer.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
BASELINES = ROOT / "baselines"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier7_1g_nab_source_data_scoring_preflight import criterion, sha256_file, write_csv, write_json  # noqa: E402


TIER = "Tier 7.4d - Cost-Aware Policy/Action Held-Out/Public Usefulness Contract"
RUNNER_REVISION = "tier7_4d_cost_aware_policy_action_heldout_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_4d_20260509_cost_aware_policy_action_heldout_contract"
TIER7_4C_RESULTS = CONTROLLED / "tier7_4c_20260509_cost_aware_policy_action_promotion_gate" / "tier7_4c_results.json"
TIER7_1B_RESULTS = CONTROLLED / "tier7_1b_20260508_cmapss_source_data_preflight" / "tier7_1b_results.json"
TIER7_1G_RESULTS = CONTROLLED / "tier7_1g_20260508_nab_source_data_scoring_preflight" / "tier7_1g_results.json"
V24_BASELINE = BASELINES / "CRA_EVIDENCE_BASELINE_v2.4.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def make_contract() -> dict[str, Any]:
    return {
        "question": (
            "Does the frozen v2.4 cost-aware policy/action layer preserve a measurable "
            "utility advantage on external or held-out action-cost tasks without "
            "threshold tuning, leakage, or same-subset policy selection?"
        ),
        "hypothesis": (
            "If v2.4 learned a general cost-aware policy/action mechanism rather than a "
            "private-task trick, it should improve expected utility or regret on at "
            "least one held-out public/real-ish action-cost family while separating "
            "confidence, memory, recurrent-state, and shuffled-cost shams."
        ),
        "null_hypothesis": (
            "v2.4 does not beat fixed train-only thresholds, rolling policies, "
            "online learners, reservoir/ESN policy baselines, or trivial act/abstain "
            "controls on held-out action-cost tasks under locked costs and splits."
        ),
        "claim_boundary": (
            "Tier 7.4d is a pre-registration contract. It authorizes a later held-out "
            "scoring preflight/gate, but it does not score v2.4, freeze a new baseline, "
            "claim public usefulness, or authorize hardware/native policy transfer."
        ),
        "task_families": [
            {
                "name": "nab_heldout_alarm_action_cost",
                "kind": "public_realish_primary",
                "source": "Numenta Anomaly Benchmark pinned by Tier 7.1g",
                "heldout_rule": "use streams/categories not used to choose same-subset NAB policies",
                "actions": ["abstain", "wait", "alert"],
                "primary_metric": "expected_utility_with_false_positive_missed_event_latency_costs",
                "claim_role": "public streaming alarm/action usefulness candidate",
            },
            {
                "name": "cmapss_maintenance_action_cost",
                "kind": "public_realish_primary",
                "source": "NASA C-MAPSS FD001 source audited by Tier 7.1b",
                "heldout_rule": "train/calibrate on train units only; test actions emitted before RUL feedback",
                "actions": ["wait", "monitor", "maintain"],
                "primary_metric": "maintenance_utility_and_regret_vs_oracle",
                "claim_role": "public predictive-maintenance action usefulness candidate",
            },
            {
                "name": "standard_dynamical_action_cost",
                "kind": "standardized_secondary",
                "source": "locked Mackey-Glass, Lorenz, and NARMA10 streams from the Tier 7.0 scoreboard",
                "heldout_rule": "use locked train/calibration/test windows; no retuning on test windows",
                "actions": ["abstain", "wait", "act"],
                "primary_metric": "geomean_cost_normalized_mse_or_utility",
                "claim_role": "standardized regression-to-action diagnostic, not public usefulness alone",
            },
            {
                "name": "heldout_synthetic_policy_stress",
                "kind": "diagnostic_only",
                "source": "predeclared hidden-context/delayed-action local stressors",
                "heldout_rule": "locked seeds and task parameters before scoring",
                "actions": ["abstain", "wait", "act", "route"],
                "primary_metric": "expected_utility_and_sham_separation",
                "claim_role": "mechanism localization only; cannot support public usefulness by itself",
            },
        ],
        "action_set": [
            "abstain",
            "wait",
            "act_or_alert",
            "monitor",
            "maintain",
            "route_or_escalate",
        ],
        "locked_cost_model": {
            "correct_event_action": 10.0,
            "early_but_useful_action": 4.0,
            "false_positive_action": -3.0,
            "missed_event": -15.0,
            "late_action_per_step": -0.5,
            "unnecessary_maintenance": -4.0,
            "premature_maintenance": -6.0,
            "failure_without_maintenance": -20.0,
            "wait_or_abstain_cost_per_step": -0.05,
            "correct_abstain_under_low_confidence": 0.25,
        },
        "split_and_leakage_rules": [
            "All thresholds, policy temperatures, abstain costs, and calibration transforms are selected on train/calibration splits only.",
            "No test-label threshold tuning is allowed for any model, baseline, policy, cost, or abstention rule.",
            "No same-subset policy selection: if a policy is selected on a diagnostic subset, confirmation must use disjoint held-out streams/units/windows.",
            "Each action is emitted before the feedback, anomaly label, RUL label, or outcome update for that row/window is visible.",
            "Labels and event windows stay in separate artifacts from online input rows until offline scoring.",
            "Public-source checksums, selected streams/units, split ids, and ignored raw-data-cache paths must be recorded.",
            "Any repair after a failed held-out score returns to a new contract or diagnostic; it cannot overwrite the held-out result.",
        ],
        "baselines": [
            "always_abstain_or_wait",
            "always_act_or_alert",
            "fixed_train_only_threshold",
            "rolling_zscore_policy",
            "ewma_mad_residual_policy",
            "lag_ridge_policy",
            "online_logistic_policy",
            "online_perceptron_policy",
            "reservoir_or_esn_policy_readout",
            "small_gru_sequence_policy_if_budget_allows",
            "random_policy",
            "oracle_policy_upper_bound_nonclaim",
        ],
        "shams_and_ablations": [
            "shuffled_cost_or_reward",
            "key_label_permuted_cost",
            "random_confidence",
            "confidence_disabled",
            "memory_disabled",
            "recurrent_state_disabled",
            "policy_learning_disabled",
            "wrong_context_key",
            "no_action_cost_ablation",
            "always_action_collapse_guard",
            "test_label_leakage_guard",
        ],
        "primary_metrics": [
            "expected_utility",
            "cost_normalized_score",
            "regret_vs_oracle",
            "event_f1_or_window_recall",
            "false_positive_cost_per_1000",
            "missed_event_cost",
            "action_latency",
            "maintenance_failure_cost",
            "calibration_error",
            "action_rate_and_no_action_collapse_rate",
        ],
        "statistics": [
            "per-stream_or_per-unit_table",
            "mean_median_std_min_max",
            "bootstrap_95_ci_for_delta_vs_best_baseline",
            "paired_effect_size_where_units_match",
            "task_family_win_loss_table",
            "worst_case_seed_or_stream_behavior",
        ],
        "pass_criteria": [
            "v2.4 beats or complements the strongest reproduced baseline on the primary utility metric for at least one public/real-ish held-out family.",
            "The result is not explained by fixed train-only thresholds, rolling z-score, reservoir/ESN policy, always-act, or always-abstain controls.",
            "Shuffled cost, random confidence, confidence-disabled, memory-disabled, and recurrent-state-disabled controls lose on the claimed family.",
            "No-action and always-action collapse are explicitly ruled out by action-rate and recall/precision guards.",
            "Bootstrap confidence intervals or paired effect sizes support the claimed utility delta on the held-out family.",
            "No leakage, same-subset policy selection, or test-label threshold tuning is detected.",
        ],
        "fail_criteria": [
            "A simple fixed threshold, rolling z-score, lag/ridge, or reservoir/ESN policy wins the held-out public family.",
            "v2.4 wins only on private/synthetic diagnostics and not on any public/real-ish held-out family.",
            "Any sham or ablation matches the intact v2.4 result on the claimed family.",
            "The policy collapses into abstain/wait or always-act behavior while gaming utility.",
            "The score requires threshold or cost tuning on the held-out/test subset.",
            "Public data, split, or label-separation artifacts are missing or unverifiable.",
        ],
        "nonclaims": [
            "not a scoring run",
            "not public usefulness proof",
            "not broad anomaly or predictive-maintenance superiority",
            "not a baseline freeze",
            "not hardware/native transfer",
            "not long-horizon planning",
            "not language",
            "not AGI/ASI evidence",
        ],
        "expected_artifacts_next_gate": [
            "tier7_4e_results.json",
            "tier7_4e_report.md",
            "tier7_4e_summary.csv",
            "tier7_4e_task_family_scores.csv",
            "tier7_4e_model_scores.csv",
            "tier7_4e_per_stream_or_unit_scores.csv",
            "tier7_4e_sham_ablation_scores.csv",
            "tier7_4e_split_manifest.json",
            "tier7_4e_cost_model.json",
            "tier7_4e_decision.json",
        ],
        "next_gate_if_accepted": "Tier 7.4e - Cost-Aware Policy/Action Held-Out Scoring Preflight",
    }


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


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    contract = payload["contract"]
    lines = [
        "# Tier 7.4d Cost-Aware Policy/Action Held-Out/Public Usefulness Contract",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Next gate: `{contract['next_gate_if_accepted']}`",
        "",
        "## Boundary",
        "",
        contract["claim_boundary"],
        "",
        "## Question",
        "",
        contract["question"],
        "",
        "## Primary Held-Out Families",
        "",
    ]
    for family in contract["task_families"]:
        lines.extend(
            [
                f"### {family['name']}",
                "",
                f"- Kind: `{family['kind']}`",
                f"- Source: {family['source']}",
                f"- Held-out rule: {family['heldout_rule']}",
                f"- Claim role: {family['claim_role']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Pass Criteria",
            "",
            *[f"- {item}" for item in contract["pass_criteria"]],
            "",
            "## Fail Criteria",
            "",
            *[f"- {item}" for item in contract["fail_criteria"]],
            "",
            "## Baselines",
            "",
            *[f"- {item}" for item in contract["baselines"]],
            "",
            "## Shams And Ablations",
            "",
            *[f"- {item}" for item in contract["shams_and_ablations"]],
            "",
            "## Nonclaims",
            "",
            *[f"- {item}" for item in contract["nonclaims"]],
            "",
        ]
    )
    output_dir.joinpath("tier7_4d_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    tier7_4c = read_json(TIER7_4C_RESULTS) if TIER7_4C_RESULTS.exists() else {}
    v24 = read_json(V24_BASELINE) if V24_BASELINE.exists() else {}
    tier7_1b = read_json(TIER7_1B_RESULTS) if TIER7_1B_RESULTS.exists() else {}
    tier7_1g = read_json(TIER7_1G_RESULTS) if TIER7_1G_RESULTS.exists() else {}
    contract = make_contract()

    public_families = [f for f in contract["task_families"] if f["kind"].startswith("public_realish")]
    diagnostic_families = [f for f in contract["task_families"] if f["kind"] == "diagnostic_only"]
    cost_keys = set(contract["locked_cost_model"])
    baseline_names = set(contract["baselines"])
    sham_names = set(contract["shams_and_ablations"])
    metric_names = set(contract["primary_metrics"])
    leakage_text = " ".join(contract["split_and_leakage_rules"]).lower()
    nonclaims = set(contract["nonclaims"])

    criteria = [
        criterion("Tier 7.4c exists", str(TIER7_4C_RESULTS), "exists", TIER7_4C_RESULTS.exists()),
        criterion("Tier 7.4c passed", tier7_4c.get("status"), "== pass", tier7_4c.get("status") == "pass"),
        criterion("v2.4 baseline exists", str(V24_BASELINE), "exists", V24_BASELINE.exists()),
        criterion("v2.4 baseline frozen", v24.get("status"), "== frozen", v24.get("status") == "frozen"),
        criterion("C-MAPSS source preflight passed", tier7_1b.get("status"), "== pass", tier7_1b.get("status") == "pass"),
        criterion("NAB source preflight passed", tier7_1g.get("status"), "== pass", tier7_1g.get("status") == "pass"),
        criterion("question/hypothesis/null defined", [contract["question"], contract["hypothesis"], contract["null_hypothesis"]], "all non-empty", bool(contract["question"] and contract["hypothesis"] and contract["null_hypothesis"])),
        criterion("task families include public held-out families", [f["name"] for f in public_families], ">= 2 public/real-ish", len(public_families) >= 2),
        criterion("synthetic tasks are diagnostic only", [f["name"] for f in diagnostic_families], ">=1 diagnostic-only family", len(diagnostic_families) >= 1),
        criterion("actions include abstain wait and act", contract["action_set"], "contains abstain/wait/act", {"abstain", "wait", "act_or_alert"}.issubset(set(contract["action_set"]))),
        criterion("cost model locks FP miss latency and maintenance", sorted(cost_keys), "contains required costs", {"false_positive_action", "missed_event", "late_action_per_step", "failure_without_maintenance"}.issubset(cost_keys)),
        criterion("split rules block test tuning/leakage", contract["split_and_leakage_rules"], "contains no same-subset/test-label leakage rules", "no same-subset" in leakage_text and "test" in leakage_text and "label" in leakage_text),
        criterion("baselines include threshold zscore reservoir online", contract["baselines"], ">=10 and required families", len(contract["baselines"]) >= 10 and {"fixed_train_only_threshold", "rolling_zscore_policy", "reservoir_or_esn_policy_readout", "online_logistic_policy"}.issubset(baseline_names)),
        criterion("shams and ablations include confidence memory recurrent cost", contract["shams_and_ablations"], ">=8 and required controls", len(contract["shams_and_ablations"]) >= 8 and {"shuffled_cost_or_reward", "random_confidence", "memory_disabled", "recurrent_state_disabled"}.issubset(sham_names)),
        criterion("metrics include utility regret latency calibration", contract["primary_metrics"], "contains required metrics", {"expected_utility", "regret_vs_oracle", "action_latency", "calibration_error"}.issubset(metric_names)),
        criterion("statistics include CI effect size and per-unit table", contract["statistics"], "contains paper-grade statistics", any("bootstrap_95_ci" in s for s in contract["statistics"]) and any("effect_size" in s for s in contract["statistics"]) and any("per-stream" in s or "per-unit" in s for s in contract["statistics"])),
        criterion("pass/fail criteria are explicit", [len(contract["pass_criteria"]), len(contract["fail_criteria"])], ">=6 each", len(contract["pass_criteria"]) >= 6 and len(contract["fail_criteria"]) >= 6),
        criterion("nonclaims block scoring freeze hardware AGI", contract["nonclaims"], "contains required nonclaims", {"not a scoring run", "not a baseline freeze", "not hardware/native transfer", "not AGI/ASI evidence"}.issubset(nonclaims)),
        criterion("next gate is preflight not immediate promotion", contract["next_gate_if_accepted"], "contains Held-Out Scoring Preflight", "Held-Out Scoring Preflight" in contract["next_gate_if_accepted"]),
        criterion("expected artifacts declared", contract["expected_artifacts_next_gate"], ">=8 artifacts", len(contract["expected_artifacts_next_gate"]) >= 8),
    ]

    status = "pass" if all(c["passed"] for c in criteria) else "fail"
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": sum(1 for c in criteria if c["passed"]),
        "criteria_total": len(criteria),
        "contract": contract,
        "prior_evidence": {
            "tier7_4c_results": str(TIER7_4C_RESULTS),
            "tier7_4c_status": tier7_4c.get("status"),
            "v2_4_baseline": str(V24_BASELINE),
            "v2_4_status": v24.get("status"),
            "cmapss_preflight": str(TIER7_1B_RESULTS),
            "cmapss_preflight_status": tier7_1b.get("status"),
            "nab_preflight": str(TIER7_1G_RESULTS),
            "nab_preflight_status": tier7_1g.get("status"),
        },
        "decision": {
            "outcome": "heldout_public_usefulness_contract_locked" if status == "pass" else "heldout_public_usefulness_contract_incomplete",
            "scoring_authorized": status == "pass",
            "freeze_authorized": False,
            "hardware_transfer_authorized": False,
            "next_gate": contract["next_gate_if_accepted"],
        },
    }

    paths = {
        "results_json": output_dir / "tier7_4d_results.json",
        "report_md": output_dir / "tier7_4d_report.md",
        "summary_csv": output_dir / "tier7_4d_summary.csv",
        "contract_json": output_dir / "tier7_4d_contract.json",
        "task_families_csv": output_dir / "tier7_4d_task_families.csv",
        "baselines_csv": output_dir / "tier7_4d_baselines.csv",
        "shams_csv": output_dir / "tier7_4d_shams_ablations.csv",
        "cost_model_csv": output_dir / "tier7_4d_cost_model.csv",
        "decision_json": output_dir / "tier7_4d_decision.json",
        "decision_csv": output_dir / "tier7_4d_decision.csv",
    }

    write_json(paths["results_json"], payload)
    write_json(paths["contract_json"], contract)
    write_json(paths["decision_json"], payload["decision"])
    write_report(output_dir, payload)
    write_csv(paths["summary_csv"], [
        {
            "tier": TIER,
            "status": status,
            "criteria_passed": payload["criteria_passed"],
            "criteria_total": payload["criteria_total"],
            "outcome": payload["decision"]["outcome"],
            "next_gate": contract["next_gate_if_accepted"],
            "freeze_authorized": False,
            "hardware_transfer_authorized": False,
        }
    ])
    write_csv(paths["task_families_csv"], contract["task_families"])
    write_csv(paths["baselines_csv"], [{"baseline": item} for item in contract["baselines"]])
    write_csv(paths["shams_csv"], [{"sham_or_ablation": item} for item in contract["shams_and_ablations"]])
    write_csv(paths["cost_model_csv"], [{"cost_item": key, "value": value} for key, value in contract["locked_cost_model"].items()])
    write_csv(paths["decision_csv"], [payload["decision"]])

    manifest = make_manifest(output_dir, paths, status)
    manifest_path = output_dir / "tier7_4d_latest_manifest.json"
    write_json(manifest_path, manifest)
    write_json(CONTROLLED / "tier7_4d_latest_manifest.json", manifest)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    payload = run(args)
    print(
        json.dumps(
            {
                "tier": TIER,
                "status": payload["status"],
                "criteria_passed": payload["criteria_passed"],
                "criteria_total": payload["criteria_total"],
                "output_dir": str(Path(args.output_dir).resolve()),
                "next_gate": payload["decision"]["next_gate"],
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
