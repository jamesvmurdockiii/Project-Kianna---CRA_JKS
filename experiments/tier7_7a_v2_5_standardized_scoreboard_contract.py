#!/usr/bin/env python3
"""Tier 7.7a - v2.5 standardized benchmark / usefulness scoreboard contract.

This is a contract-only gate. It does not score v2.5. It locks the benchmark
matrix, baselines, splits, metrics, shams, leakage rules, pass/fail criteria,
artifacts, and claim boundaries before the next scoring run.

The point is to prevent post-hoc benchmark rescue. If v2.5 does not improve the
locked scoreboard, that is evidence too.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
BASELINES = ROOT / "baselines"

TIER = "Tier 7.7a - v2.5 Standardized Benchmark / Usefulness Scoreboard Contract"
RUNNER_REVISION = "tier7_7a_v2_5_standardized_scoreboard_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7a_20260509_v2_5_standardized_scoreboard_contract"

PREREQ_76E = CONTROLLED / "tier7_6e_20260509_planning_promotion_compact_regression" / "tier7_6e_results.json"
PREREQ_70J = CONTROLLED / "tier7_0j_20260508_generic_recurrent_promotion_gate" / "tier7_0j_results.json"
V25_BASELINE = BASELINES / "CRA_EVIDENCE_BASELINE_v2.5.json"
NEXT_GATE = "Tier 7.7b - v2.5 Standardized Benchmark / Usefulness Scoreboard Scoring Gate"


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def task_matrix_rows() -> list[dict[str, Any]]:
    return [
        {
            "task_id": "mackey_glass_future_prediction",
            "family": "standard_dynamical_core",
            "source": "standard generated Mackey-Glass delay-differential series",
            "length": 8000,
            "horizon": 8,
            "seeds": "42,43,44",
            "split": "chronological train 65%, test 35%",
            "primary_metric": "test_mse",
            "aggregate_role": "all_three_geomean_mse",
            "claim_role": "standardized future-prediction component",
            "required_for_primary_scoreboard": True,
        },
        {
            "task_id": "lorenz_future_prediction",
            "family": "standard_dynamical_core",
            "source": "standard generated Lorenz chaotic attractor series",
            "length": 8000,
            "horizon": 8,
            "seeds": "42,43,44",
            "split": "chronological train 65%, test 35%",
            "primary_metric": "test_mse",
            "aggregate_role": "all_three_geomean_mse",
            "claim_role": "standardized chaotic future-prediction component",
            "required_for_primary_scoreboard": True,
        },
        {
            "task_id": "narma10_memory_system_identification",
            "family": "standard_dynamical_core",
            "source": "standard NARMA10 nonlinear memory/system-identification stream",
            "length": 8000,
            "horizon": 8,
            "seeds": "42,43,44",
            "split": "chronological train 65%, test 35%",
            "primary_metric": "test_mse",
            "aggregate_role": "all_three_geomean_mse",
            "claim_role": "standardized nonlinear memory component",
            "required_for_primary_scoreboard": True,
        },
        {
            "task_id": "standard_three_geomean",
            "family": "standard_dynamical_core_aggregate",
            "source": "Mackey-Glass + Lorenz + NARMA10 locked 8000-step same-seed scoreboard",
            "length": 8000,
            "horizon": 8,
            "seeds": "42,43,44",
            "split": "aggregate only after all three tasks pass finite-stream checks",
            "primary_metric": "geomean_test_mse",
            "aggregate_role": "primary_standardized_scoreboard",
            "claim_role": "primary standardized usefulness diagnostic, not public usefulness alone",
            "required_for_primary_scoreboard": True,
        },
        {
            "task_id": "short_medium_calibration_sweeps",
            "family": "diagnostic_only",
            "source": "same standard generators at 720 and 2000 steps",
            "length": "720,2000",
            "horizon": 8,
            "seeds": "42,43,44",
            "split": "chronological train 65%, test 35%",
            "primary_metric": "calibration_delta_only",
            "aggregate_role": "diagnostic_not_claim",
            "claim_role": "debug over/under-exposure without replacing 8000-step scoreboard",
            "required_for_primary_scoreboard": False,
        },
        {
            "task_id": "cmapss_fd001_maintenance_utility",
            "family": "public_realish_secondary",
            "source": "NASA C-MAPSS FD001 source already audited in Tier 7.1b",
            "length": "dataset-defined",
            "horizon": "RUL/action window defined by held-out policy contract",
            "seeds": "dataset split ids, plus deterministic model seeds",
            "split": "train units for calibration, held-out test units for scoring",
            "primary_metric": "maintenance_utility_and_regret_vs_oracle",
            "aggregate_role": "secondary_public_action_confirmation",
            "claim_role": "real-ish confirmation only; cannot rescue failed standard scoreboard alone",
            "required_for_primary_scoreboard": False,
        },
        {
            "task_id": "nab_heldout_alarm_action_cost",
            "family": "public_realish_secondary",
            "source": "Numenta Anomaly Benchmark streams audited in Tier 7.1g-7.1m",
            "length": "stream-defined",
            "horizon": "event window / alert latency scoring",
            "seeds": "stream ids plus deterministic model seeds",
            "split": "no same-subset policy selection; held-out streams only",
            "primary_metric": "expected_utility_false_positive_and_missed_event_cost",
            "aggregate_role": "secondary_public_action_confirmation",
            "claim_role": "real-ish confirmation only; preserve prior NAB non-confirmation unless newly passed",
            "required_for_primary_scoreboard": False,
        },
    ]


def baseline_rows() -> list[dict[str, Any]]:
    return [
        {
            "baseline_id": "cra_v2_5_host_side_candidate",
            "class": "CRA_candidate",
            "applies_to": "all primary standardized tasks; secondary public adapters where implemented",
            "fairness_rule": "same causal inputs, same train/calibration/test split, no test-label tuning",
        },
        {
            "baseline_id": "cra_v2_3_generic_recurrent_reference",
            "class": "CRA_previous_reference",
            "applies_to": "standardized dynamical core",
            "fairness_rule": "same locked 8000-step protocol used for v2.3 freeze comparison",
        },
        {
            "baseline_id": "cra_v2_4_cost_aware_policy_reference",
            "class": "CRA_previous_reference",
            "applies_to": "action-cost secondary tracks and any standardized action-cost transform",
            "fairness_rule": "same locked costs and no same-subset policy selection",
        },
        {
            "baseline_id": "persistence",
            "class": "simple_sequence_baseline",
            "applies_to": "standardized dynamical core",
            "fairness_rule": "prediction uses only causal prior values",
        },
        {
            "baseline_id": "online_lms",
            "class": "online_linear_baseline",
            "applies_to": "standardized dynamical core",
            "fairness_rule": "prequential prediction before online update",
        },
        {
            "baseline_id": "ridge_lag",
            "class": "train_prefix_linear_baseline",
            "applies_to": "standardized dynamical core",
            "fairness_rule": "fit on train prefix only with same lag budget",
        },
        {
            "baseline_id": "echo_state_network",
            "class": "reservoir_baseline",
            "applies_to": "standardized dynamical core and secondary adapters where feasible",
            "fairness_rule": "predeclared reservoir size and train-prefix readout only",
        },
        {
            "baseline_id": "small_gru",
            "class": "gradient_recurrent_reviewer_defense",
            "applies_to": "standardized dynamical core if runtime budget allows",
            "fairness_rule": "predeclared hidden size, epochs, early stopping on validation only",
        },
        {
            "baseline_id": "rolling_or_ewma_threshold_policy",
            "class": "public_adapter_baseline",
            "applies_to": "NAB and C-MAPSS action-cost tracks",
            "fairness_rule": "thresholds selected on train/calibration streams only",
        },
        {
            "baseline_id": "online_logistic_or_perceptron_policy",
            "class": "public_adapter_online_baseline",
            "applies_to": "secondary public adapters",
            "fairness_rule": "same causal features and feedback timing",
        },
        {
            "baseline_id": "always_wait_or_abstain",
            "class": "negative_policy_control",
            "applies_to": "secondary public adapters",
            "fairness_rule": "reported to expose action-cost imbalance",
        },
        {
            "baseline_id": "oracle_upper_bound",
            "class": "upper_bound_nonclaim",
            "applies_to": "all tasks where an oracle is definable",
            "fairness_rule": "reported only; not a baseline CRA must beat and never used for tuning",
        },
    ]


def split_rows() -> list[dict[str, Any]]:
    return [
        {
            "split_id": "standard_train_prefix",
            "visible_to_development": True,
            "claim_allowed": False,
            "rule": "first 65% of each standardized stream; normalization and readouts fit here only",
        },
        {
            "split_id": "standard_test_suffix",
            "visible_to_development": False,
            "claim_allowed": True,
            "rule": "last 35% of each standardized stream; no model, threshold, or hyperparameter changes after viewing",
        },
        {
            "split_id": "standard_tail_test",
            "visible_to_development": False,
            "claim_allowed": True,
            "rule": "final quartile of the test suffix; used for late-run stability and forgetting diagnostics",
        },
        {
            "split_id": "public_adapter_train_calibration",
            "visible_to_development": True,
            "claim_allowed": False,
            "rule": "public training units/streams only; used for thresholds, costs, and candidate selection",
        },
        {
            "split_id": "public_adapter_heldout",
            "visible_to_development": False,
            "claim_allowed": True,
            "rule": "held-out units/streams/windows not used for same-subset policy selection",
        },
    ]


def metric_rows() -> list[dict[str, Any]]:
    return [
        {"metric": "test_mse", "scope": "standardized", "purpose": "primary per-task regression error"},
        {"metric": "test_nmse", "scope": "standardized", "purpose": "scale-normalized per-task regression error"},
        {"metric": "tail_mse", "scope": "standardized", "purpose": "late-run stability and forgetting pressure"},
        {"metric": "all_three_geomean_mse", "scope": "standardized", "purpose": "primary aggregate across Mackey-Glass, Lorenz, and NARMA10"},
        {"metric": "rank_vs_baselines", "scope": "standardized_and_public", "purpose": "prevent single-number cherry picking"},
        {"metric": "paired_seed_delta", "scope": "standardized_and_public", "purpose": "same-seed comparison versus v2.3/v2.4 and best non-oracle baseline"},
        {"metric": "bootstrap_or_paired_ci", "scope": "standardized_and_public", "purpose": "confidence interval around effect size"},
        {"metric": "worst_seed_score", "scope": "standardized_and_public", "purpose": "prevent mean-only claims hiding collapse"},
        {"metric": "sample_efficiency_curve", "scope": "optional_diagnostic", "purpose": "check whether longer exposure helps rather than only final score"},
        {"metric": "expected_utility", "scope": "public_adapter_secondary", "purpose": "action-cost usefulness where applicable"},
        {"metric": "regret_vs_oracle", "scope": "public_adapter_secondary", "purpose": "distance from unattainable upper bound without using it as a claim baseline"},
        {"metric": "false_positive_or_missed_event_cost", "scope": "public_adapter_secondary", "purpose": "ensure utility does not hide dangerous collapse modes"},
        {"metric": "runtime_and_wall_clock", "scope": "all", "purpose": "resource accounting and reproducibility"},
    ]


def sham_rows() -> list[dict[str, Any]]:
    return [
        {"sham": "target_shuffle", "purpose": "break input-target relation while preserving marginal target distribution"},
        {"sham": "time_shuffle", "purpose": "destroy temporal structure while preserving value distribution"},
        {"sham": "lag_only_control", "purpose": "determine whether CRA state adds beyond explicit lag memory"},
        {"sham": "state_disabled", "purpose": "remove v2.3 recurrent state"},
        {"sham": "memory_disabled", "purpose": "remove keyed context memory contribution"},
        {"sham": "replay_disabled", "purpose": "remove v1.7 replay/consolidation contribution"},
        {"sham": "prediction_disabled", "purpose": "remove predictive/context modeling contribution"},
        {"sham": "self_evaluation_disabled", "purpose": "remove reliability/confidence gating contribution"},
        {"sham": "composition_routing_disabled", "purpose": "remove module routing and compositional reuse contribution"},
        {"sham": "policy_action_disabled", "purpose": "remove v2.4 cost-aware action layer where relevant"},
        {"sham": "planning_disabled", "purpose": "remove v2.5 reduced-feature planning/subgoal state"},
        {"sham": "future_label_leak_guard", "purpose": "detect any access to future targets, labels, or event windows before prediction/action"},
    ]


def leakage_rows() -> list[dict[str, Any]]:
    return [
        {"guard": "train_only_normalization", "rule": "normalization statistics fit only on train prefix or train units"},
        {"guard": "prediction_before_update", "rule": "online rows must emit prediction/action before target/reward update"},
        {"guard": "target_shift_before_split", "rule": "future targets are shifted before chronological splitting"},
        {"guard": "finite_stream_precheck", "rule": "all standardized streams must be finite before scoring; non-finite rows block the run"},
        {"guard": "no_test_threshold_tuning", "rule": "all thresholds, policy costs, lags, reservoirs, and hyperparameters locked before test scoring"},
        {"guard": "same_seed_pairing", "rule": "candidate and baselines are compared on the same seeds and streams"},
        {"guard": "same_feature_budget_or_disclosed", "rule": "baselines receive equivalent causal features or any advantage is explicitly labeled"},
        {"guard": "oracle_nonclaim", "rule": "oracle is reported as upper bound only and never treated as a beatable baseline"},
        {"guard": "secondary_adapters_cannot_rescue_core_failure", "rule": "C-MAPSS/NAB signals cannot erase a failed standardized core scoreboard"},
    ]


def pass_fail_rows() -> list[dict[str, Any]]:
    return [
        {
            "kind": "strong_pass",
            "rule": "v2.5 improves all-three 8000-step geomean MSE versus v2.3 by >= 10% and paired CI excludes zero, while at least one public/real-ish secondary family also supports v2.5 or v2.4+v2.5 utility without sham match",
            "claim_allowed": "bounded usefulness candidate; still not AGI, language, hardware/native transfer, or universal superiority",
        },
        {
            "kind": "standardized_progress_pass",
            "rule": "v2.5 improves all-three 8000-step geomean MSE versus v2.3 by >= 10% with paired support, but does not beat ESN/ridge or lacks public/real-ish confirmation",
            "claim_allowed": "software mechanism progress on standardized dynamical benchmarks only",
        },
        {
            "kind": "localized_pass",
            "rule": "v2.5 improves one or two standardized tasks or a secondary public adapter, but not the all-three aggregate",
            "claim_allowed": "localized task-family signal only; no broad usefulness claim",
        },
        {
            "kind": "no_promotion",
            "rule": "v2.5 fails to improve v2.3 on the all-three aggregate or matches shams/lag-only controls",
            "claim_allowed": "no usefulness upgrade; route to failure localization before further mechanism layering",
        },
        {
            "kind": "stop_or_narrow",
            "rule": "full planned mechanism stack still fails standardized/public scoreboards after fair tests",
            "claim_allowed": "stop broad usefulness track and narrow the paper to architecture/evidence/hardware substrate",
        },
    ]


def expected_artifact_rows() -> list[dict[str, Any]]:
    return [
        {"artifact": "tier7_7b_results.json", "purpose": "scoring result and classification"},
        {"artifact": "tier7_7b_summary.csv", "purpose": "criteria summary"},
        {"artifact": "tier7_7b_report.md", "purpose": "human-readable result and boundaries"},
        {"artifact": "tier7_7b_scoreboard_rows.csv", "purpose": "per task/model/seed metrics"},
        {"artifact": "tier7_7b_aggregate_scoreboard.csv", "purpose": "aggregate geomean/rank/effect-size table"},
        {"artifact": "tier7_7b_sham_controls.csv", "purpose": "sham/ablation separation"},
        {"artifact": "tier7_7b_leakage_audit.json", "purpose": "finite-stream and causal-order audit"},
        {"artifact": "tier7_7b_fairness_contract.json", "purpose": "exact scoring contract used by runner"},
        {"artifact": "tier7_7b_claim_boundary.md", "purpose": "allowed claims and nonclaims"},
        {"artifact": "tier7_7b_latest_manifest.json", "purpose": "registry pointer"},
    ]


def contract_payload() -> dict[str, Any]:
    return {
        "question": "Does frozen v2.5 improve CRA's public/standardized usefulness posture beyond bounded synthetic planning diagnostics?",
        "hypothesis": (
            "If the v2.5 planning/subgoal-control stack adds general value, it should improve the locked "
            "8000-step Mackey-Glass/Lorenz/NARMA10 standardized scoreboard versus the v2.3 software "
            "reference without matching shams or relying on future-label leakage. Real-ish adapters may "
            "support a stronger usefulness posture, but cannot rescue a failed standardized core by themselves."
        ),
        "null_hypothesis": (
            "v2.5 does not improve the locked standardized scoreboard versus v2.3 or simpler non-oracle "
            "sequence baselines, or the apparent improvement is explained by lag-only controls, shams, "
            "test leakage, same-subset policy selection, or a single lucky seed/task."
        ),
        "primary_scoreboard": "Mackey-Glass + Lorenz + NARMA10, length=8000, horizon=8, seeds=42,43,44, chronological 65/35 split",
        "secondary_public_confirmation": "C-MAPSS FD001 and NAB held-out action-cost tracks are included as secondary confirmation only, not as replacements for the standardized core.",
        "next_gate": NEXT_GATE,
        "claim_boundary": (
            "Tier 7.7a is a contract/pre-registration gate only. It performs no scoring, freezes no new "
            "baseline, claims no public usefulness, and authorizes no hardware/native transfer."
        ),
        "nonclaims": [
            "not a benchmark score",
            "not a public usefulness claim",
            "not proof of ESN/ridge/GRU superiority",
            "not a new baseline freeze",
            "not hardware or native-on-chip evidence",
            "not language, broad planning, AGI, or ASI evidence",
        ],
        "task_matrix": task_matrix_rows(),
        "baselines": baseline_rows(),
        "splits": split_rows(),
        "metrics": metric_rows(),
        "shams": sham_rows(),
        "leakage_rules": leakage_rows(),
        "pass_fail_criteria": pass_fail_rows(),
        "expected_artifacts": expected_artifact_rows(),
    }


def build_report(results: dict[str, Any]) -> str:
    contract = results["contract"]
    lines = [
        f"# {TIER}",
        "",
        f"- Generated: `{results['generated_at_utc']}`",
        f"- Runner revision: `{RUNNER_REVISION}`",
        f"- Status: **{results['status'].upper()}**",
        f"- Output directory: `{results['output_dir']}`",
        "",
        "## Question",
        "",
        contract["question"],
        "",
        "## Locked Primary Scoreboard",
        "",
        contract["primary_scoreboard"],
        "",
        "## Secondary Public Confirmation",
        "",
        contract["secondary_public_confirmation"],
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in results["criteria"]:
        lines.append(f"| {item['name']} | `{item['value']}` | {item['rule']} | {'yes' if item['passed'] else 'no'} |")
    lines.extend(
        [
            "",
            "## Pass/Fail Boundary",
            "",
            "| Outcome | Rule | Claim Allowed |",
            "| --- | --- | --- |",
        ]
    )
    for row in contract["pass_fail_criteria"]:
        lines.append(f"| `{row['kind']}` | {row['rule']} | {row['claim_allowed']} |")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            contract["claim_boundary"],
            "",
            "Nonclaims:",
        ]
    )
    for item in contract["nonclaims"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            f"`{NEXT_GATE}`",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    prereq_76e = read_json(PREREQ_76E)
    prereq_70j = read_json(PREREQ_70J)
    baseline_v25 = read_json(V25_BASELINE)
    contract = contract_payload()

    task_rows = contract["task_matrix"]
    baseline_rows_ = contract["baselines"]
    split_rows_ = contract["splits"]
    metric_rows_ = contract["metrics"]
    sham_rows_ = contract["shams"]
    leakage_rows_ = contract["leakage_rules"]
    pass_fail_rows_ = contract["pass_fail_criteria"]
    expected_rows = contract["expected_artifacts"]

    primary_tasks = [row for row in task_rows if row.get("required_for_primary_scoreboard")]
    external_baselines = [row for row in baseline_rows_ if row["class"] not in {"CRA_candidate", "CRA_previous_reference", "upper_bound_nonclaim"}]
    secondary_rows = [row for row in task_rows if row["family"].startswith("public_realish")]

    criteria = [
        criterion("v2.5 baseline exists", str(V25_BASELINE), "exists", V25_BASELINE.exists()),
        criterion("Tier 7.6e prerequisite passed", prereq_76e.get("status"), "== pass", prereq_76e.get("status") == "pass"),
        criterion("Tier 7.0j reference passed", prereq_70j.get("status"), "== pass", prereq_70j.get("status") == "pass"),
        criterion("primary standardized tasks locked", len(primary_tasks), ">= 4 including aggregate", len(primary_tasks) >= 4),
        criterion(
            "Mackey/Lorenz/NARMA included",
            ",".join(row["task_id"] for row in task_rows),
            "contains all three",
            all(any(name in row["task_id"] for row in task_rows) for name in ["mackey_glass", "lorenz", "narma10"]),
        ),
        criterion("8000-step finite protocol locked", sorted({str(row["length"]) for row in primary_tasks}), "== 8000", all(row["length"] == 8000 for row in primary_tasks)),
        criterion("three same seeds locked", sorted({str(row["seeds"]) for row in primary_tasks}), "contains 42,43,44", all(row["seeds"] == "42,43,44" for row in primary_tasks)),
        criterion("chronological split locked", ",".join(row["split"] for row in primary_tasks[:3]), "train 65%, test 35%", all("65%" in row["split"] and "35%" in row["split"] for row in primary_tasks[:3])),
        criterion("v2.5 candidate baseline included", [row["baseline_id"] for row in baseline_rows_], "contains cra_v2_5", any(row["baseline_id"] == "cra_v2_5_host_side_candidate" for row in baseline_rows_)),
        criterion("prior CRA references included", [row["baseline_id"] for row in baseline_rows_], "contains v2.3 and v2.4", all(any(row["baseline_id"] == needed for row in baseline_rows_) for needed in ["cra_v2_3_generic_recurrent_reference", "cra_v2_4_cost_aware_policy_reference"])),
        criterion("external baseline coverage", len(external_baselines), ">= 6 non-CRA non-oracle baselines", len(external_baselines) >= 6),
        criterion("ESN and lag/ridge included", [row["baseline_id"] for row in baseline_rows_], "contains echo_state_network and ridge_lag", all(any(row["baseline_id"] == needed for row in baseline_rows_) for needed in ["echo_state_network", "ridge_lag"])),
        criterion("mandatory shams included", [row["sham"] for row in sham_rows_], "contains target/time/future/planning shams", all(any(row["sham"] == needed for row in sham_rows_) for needed in ["target_shuffle", "time_shuffle", "future_label_leak_guard", "planning_disabled"])),
        criterion("real-ish adapter decision explicit", [row["task_id"] for row in secondary_rows], ">= 2 secondary public tracks", len(secondary_rows) >= 2),
        criterion("pass/fail criteria locked", len(pass_fail_rows_), ">= 5 outcome classes", len(pass_fail_rows_) >= 5),
        criterion("expected scoring artifacts locked", len(expected_rows), ">= 8 artifacts", len(expected_rows) >= 8),
        criterion("contract does not score benchmark", False, "must remain false", True),
        criterion("claim boundary blocks public usefulness", contract["claim_boundary"], "contains no public usefulness", "claims no public usefulness" in contract["claim_boundary"]),
        criterion("hardware/native transfer blocked", contract["claim_boundary"], "contains no hardware/native transfer", "authorizes no hardware/native transfer" in contract["claim_boundary"]),
        criterion("next scoring gate named", NEXT_GATE, "starts with Tier 7.7b", NEXT_GATE.startswith("Tier 7.7b")),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"

    manifest = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "output_dir": str(output_dir),
        "artifacts": {
            "results_json": str(output_dir / "tier7_7a_results.json"),
            "summary_csv": str(output_dir / "tier7_7a_summary.csv"),
            "report_md": str(output_dir / "tier7_7a_report.md"),
            "contract_json": str(output_dir / "tier7_7a_scoreboard_contract.json"),
        },
    }
    results = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": manifest["generated_at_utc"],
        "status": status,
        "output_dir": str(output_dir),
        "classification": {
            "outcome": "v2_5_standardized_scoreboard_contract_locked" if status == "pass" else "v2_5_standardized_scoreboard_contract_incomplete",
            "scoring_authorized": status == "pass",
            "public_usefulness_authorized": False,
            "baseline_freeze_authorized": False,
            "hardware_transfer_authorized": False,
            "next_gate": NEXT_GATE,
        },
        "prerequisites": {
            "tier7_6e_results": str(PREREQ_76E),
            "tier7_6e_sha256": sha256_file(PREREQ_76E) if PREREQ_76E.exists() else "",
            "tier7_0j_results": str(PREREQ_70J),
            "tier7_0j_sha256": sha256_file(PREREQ_70J) if PREREQ_70J.exists() else "",
            "v2_5_baseline": str(V25_BASELINE),
            "v2_5_baseline_sha256": sha256_file(V25_BASELINE) if V25_BASELINE.exists() else "",
            "v2_5_baseline_claim": baseline_v25.get("strongest_current_claim", baseline_v25.get("claim", "")),
        },
        "contract": contract,
        "criteria": criteria,
    }

    write_json(output_dir / "tier7_7a_scoreboard_contract.json", contract)
    write_csv(output_dir / "tier7_7a_task_matrix.csv", task_rows)
    write_csv(output_dir / "tier7_7a_baselines.csv", baseline_rows_)
    write_csv(output_dir / "tier7_7a_splits.csv", split_rows_)
    write_csv(output_dir / "tier7_7a_metrics.csv", metric_rows_)
    write_csv(output_dir / "tier7_7a_shams.csv", sham_rows_)
    write_csv(output_dir / "tier7_7a_leakage_rules.csv", leakage_rows_)
    write_csv(output_dir / "tier7_7a_pass_fail_criteria.csv", pass_fail_rows_)
    write_csv(output_dir / "tier7_7a_expected_artifacts.csv", expected_rows)
    write_json(output_dir / "tier7_7a_results.json", results)
    write_csv(output_dir / "tier7_7a_summary.csv", criteria)
    (output_dir / "tier7_7a_report.md").write_text(build_report(results) + "\n", encoding="utf-8")
    (output_dir / "tier7_7a_claim_boundary.md").write_text(
        "\n".join(
            [
                "# Tier 7.7a Claim Boundary",
                "",
                contract["claim_boundary"],
                "",
                "## Nonclaims",
                "",
                *[f"- {item}" for item in contract["nonclaims"]],
                "",
            ]
        ),
        encoding="utf-8",
    )

    manifest["artifacts"].update(
        {
            "task_matrix_csv": str(output_dir / "tier7_7a_task_matrix.csv"),
            "baselines_csv": str(output_dir / "tier7_7a_baselines.csv"),
            "splits_csv": str(output_dir / "tier7_7a_splits.csv"),
            "metrics_csv": str(output_dir / "tier7_7a_metrics.csv"),
            "shams_csv": str(output_dir / "tier7_7a_shams.csv"),
            "leakage_rules_csv": str(output_dir / "tier7_7a_leakage_rules.csv"),
            "pass_fail_csv": str(output_dir / "tier7_7a_pass_fail_criteria.csv"),
            "expected_artifacts_csv": str(output_dir / "tier7_7a_expected_artifacts.csv"),
            "claim_boundary_md": str(output_dir / "tier7_7a_claim_boundary.md"),
        }
    )
    write_json(output_dir / "tier7_7a_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7a_latest_manifest.json", manifest)
    print(json.dumps({"status": status, "criteria": f"{sum(c['passed'] for c in criteria)}/{len(criteria)}", "output_dir": str(output_dir), "next_gate": NEXT_GATE}, indent=2))


if __name__ == "__main__":
    main()
