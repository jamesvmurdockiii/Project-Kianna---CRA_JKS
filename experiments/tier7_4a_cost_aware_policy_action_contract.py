#!/usr/bin/env python3
"""Tier 7.4a - cost-aware policy/action selection contract.

Tier 7.1m closed the NAB adapter-policy loop and selected policy/action
selection as the next general mechanism because anomaly alarms are actions with
asymmetric costs. This contract gate defines the next mechanism test before any
implementation: tasks, costs, controls, shams, baselines, metrics, pass/fail
rules, and nonclaims.

Boundary: contract only. This is not a scoring run, not a mechanism promotion,
not a baseline freeze, and not hardware/native transfer.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
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

from tier7_1g_nab_source_data_scoring_preflight import criterion, sha256_file, write_csv, write_json  # noqa: E402


TIER = "Tier 7.4a - Cost-Aware Policy/Action Selection Contract"
RUNNER_REVISION = "tier7_4a_cost_aware_policy_action_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_4a_20260509_cost_aware_policy_action_contract"
TIER7_1M_RESULTS = CONTROLLED / "tier7_1m_20260508_nab_closeout_mechanism_return_decision" / "tier7_1m_results.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def make_contract() -> dict[str, Any]:
    return {
        "question": (
            "Can CRA learn a general policy/action layer that converts internal "
            "state, confidence, memory, and prediction error into actions under "
            "asymmetric costs, instead of relying on adapter-specific thresholds?"
        ),
        "hypothesis": (
            "A cost-aware action gate can reduce false-positive cost without "
            "collapsing recall by learning when to act, abstain, or wait under "
            "delayed and noisy consequences."
        ),
        "null_hypothesis": (
            "Cost-aware policy/action selection does not outperform fixed "
            "thresholds, abstain/always-act controls, or simple external policy "
            "baselines under fair train-only calibration."
        ),
        "tasks": [
            "synthetic_alarm_cost_stream",
            "delayed_action_consequence",
            "hidden_context_action_switch",
            "variable_delay_multi_action",
            "NAB-style heldout adapter only after local mechanism gate",
        ],
        "actions": ["abstain", "alert_or_act", "wait", "context_switch_or_route"],
        "costs": {
            "false_positive": "explicit negative utility",
            "missed_event": "explicit negative utility",
            "late_action": "latency-shaped negative utility",
            "correct_action": "positive utility",
            "abstain": "small cost unless abstention is correct under uncertainty",
        },
        "metrics": [
            "expected_utility",
            "cost_normalized_score",
            "event_f1",
            "window_recall",
            "false_positive_cost_per_1000",
            "missed_event_cost",
            "latency_cost",
            "calibration_error",
            "regret_vs_oracle",
            "seed_variance",
        ],
        "baselines": [
            "always_abstain",
            "always_act",
            "fixed_train_only_threshold",
            "rolling_zscore_cost_threshold",
            "online_logistic_policy",
            "online_perceptron_policy",
            "reservoir_policy_readout",
            "random_policy",
            "oracle_policy_upper_bound_nonclaim",
        ],
        "controls_and_ablations": [
            "shuffled_reward_cost",
            "random_confidence",
            "confidence_disabled",
            "memory_disabled",
            "recurrent_state_disabled",
            "policy_learning_disabled",
            "wrong_context_key",
            "label_leakage_guard",
        ],
        "pass_criteria": [
            "policy/action gate improves expected utility versus fixed thresholds and trivial policies",
            "benefit survives seeds and at least two task families",
            "confidence/memory/recurrent ablations lose when used by the policy",
            "shuffled reward/cost and wrong-context controls do not match intact CRA",
            "no test-label threshold tuning or leakage",
            "compact regression over v2.3 guardrails stays green before promotion",
        ],
        "fail_criteria": [
            "fixed threshold or trivial policy wins the utility metric",
            "benefit appears only on NAB or only after test-label tuning",
            "shams/ablations match intact policy",
            "recall collapses enough that the utility score is a degenerate abstain policy",
            "compact regression fails",
        ],
        "nonclaims": [
            "not public usefulness proof",
            "not reinforcement learning solved",
            "not planning",
            "not a baseline freeze",
            "not hardware/native transfer",
            "not AGI/ASI evidence",
        ],
        "next_gate_if_accepted": "Tier 7.4b - Cost-Aware Policy/Action Local Diagnostic",
    }


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    return {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": output_dir,
        "artifacts": [
            {"name": name, "path": path, "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in sorted(artifacts.items())
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    contract = payload["contract"]
    lines = [
        "# Tier 7.4a Cost-Aware Policy/Action Selection Contract",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Next gate: `{contract['next_gate_if_accepted']}`",
        "",
        "## Question",
        "",
        contract["question"],
        "",
        "## Pass Criteria",
        "",
        *[f"- {item}" for item in contract["pass_criteria"]],
        "",
        "## Baselines",
        "",
        *[f"- {item}" for item in contract["baselines"]],
        "",
        "## Controls And Ablations",
        "",
        *[f"- {item}" for item in contract["controls_and_ablations"]],
        "",
        "## Boundary",
        "",
        payload["claim_boundary"],
        "",
    ]
    output_dir.joinpath("tier7_4a_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prior = read_json(TIER7_1M_RESULTS) if TIER7_1M_RESULTS.exists() else {}
    contract = make_contract()
    selected_next = prior.get("closeout", {}).get("selected_next_gate", "")
    criteria = [
        criterion("Tier 7.1m exists", TIER7_1M_RESULTS, "exists", TIER7_1M_RESULTS.exists()),
        criterion("Tier 7.1m passed", prior.get("status"), "== pass", prior.get("status") == "pass"),
        criterion("Tier 7.1m selected policy/action next", selected_next, "contains Policy/Action", "Policy/Action" in str(selected_next)),
        criterion("question defined", contract["question"], "non-empty", bool(contract["question"])),
        criterion("hypothesis and null defined", [contract["hypothesis"], contract["null_hypothesis"]], "both non-empty", bool(contract["hypothesis"] and contract["null_hypothesis"])),
        criterion("tasks cover local and delayed action", contract["tasks"], ">= 4 tasks", len(contract["tasks"]) >= 4),
        criterion("actions include abstain and act", contract["actions"], "contains abstain/act", {"abstain", "alert_or_act"}.issubset(set(contract["actions"]))),
        criterion("costs include FP and miss", sorted(contract["costs"]), "contains false_positive/missed_event", {"false_positive", "missed_event"}.issubset(set(contract["costs"]))),
        criterion("metrics include utility and regret", contract["metrics"], "contains utility/regret", {"expected_utility", "regret_vs_oracle"}.issubset(set(contract["metrics"]))),
        criterion("external baselines defined", contract["baselines"], ">= 6 baselines", len(contract["baselines"]) >= 6),
        criterion("controls and ablations defined", contract["controls_and_ablations"], ">= 6 controls", len(contract["controls_and_ablations"]) >= 6),
        criterion("pass/fail criteria defined", [len(contract["pass_criteria"]), len(contract["fail_criteria"])], ">= 5 each", len(contract["pass_criteria"]) >= 5 and len(contract["fail_criteria"]) >= 5),
        criterion("nonclaims block freeze/hardware", contract["nonclaims"], "contains baseline/hardware nonclaims", "not a baseline freeze" in contract["nonclaims"] and "not hardware/native transfer" in contract["nonclaims"]),
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
        "failed_criteria": [c for c in criteria if not c["passed"]],
        "contract": contract,
        "prior_gate": str(TIER7_1M_RESULTS),
        "output_dir": str(output_dir),
        "claim_boundary": (
            "Tier 7.4a is a contract-only gate for a general cost-aware "
            "policy/action mechanism. It is not a scoring run, not a promoted "
            "mechanism, not a baseline freeze, and not hardware/native transfer."
        ),
    }
    paths = {
        "results_json": output_dir / "tier7_4a_results.json",
        "report_md": output_dir / "tier7_4a_report.md",
        "summary_csv": output_dir / "tier7_4a_summary.csv",
        "contract_json": output_dir / "tier7_4a_contract.json",
        "contract_csv": output_dir / "tier7_4a_contract.csv",
    }
    write_json(paths["results_json"], payload)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_json(paths["contract_json"], contract)
    write_csv(paths["contract_csv"], [{"field": key, "value": json.dumps(json_safe(value))} for key, value in contract.items()])
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    write_json(output_dir / "tier7_4a_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_4a_latest_manifest.json", manifest)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def main() -> None:
    payload = run(parse_args())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                "next_gate": payload["contract"]["next_gate_if_accepted"],
                "output_dir": payload["output_dir"],
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
