#!/usr/bin/env python3
"""Tier 7.1m - NAB closeout / mechanism-return decision.

Tier 7.1h-7.1l established a bounded NAB story: CRA v2.3 has a partial and
localized anomaly signal, but the locked false-positive repair did not survive
held-out confirmation as public usefulness proof. This tier closes the adapter
loop so we do not tune NAB policies indefinitely, records the narrowed claim,
and routes the project back to a general mechanism gate.

Boundary: evidence synthesis / decision gate only. This is not a new benchmark
score, not a mechanism promotion, not a baseline freeze, and not hardware/native
transfer.
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


TIER = "Tier 7.1m - NAB Closeout / Mechanism-Return Decision"
RUNNER_REVISION = "tier7_1m_nab_closeout_mechanism_return_decision_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_1m_20260508_nab_closeout_mechanism_return_decision"

PRIOR_RESULTS = {
    "tier7_1h": CONTROLLED / "tier7_1h_20260508_compact_nab_scoring_gate" / "tier7_1h_results.json",
    "tier7_1i": CONTROLLED / "tier7_1i_20260508_nab_fairness_confirmation" / "tier7_1i_results.json",
    "tier7_1j": CONTROLLED / "tier7_1j_20260508_nab_failure_localization" / "tier7_1j_results.json",
    "tier7_1k": CONTROLLED / "tier7_1k_20260508_nab_false_positive_repair" / "tier7_1k_results.json",
    "tier7_1l": CONTROLLED / "tier7_1l_20260508_nab_locked_policy_holdout_confirmation" / "tier7_1l_results.json",
}


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


def prior_outcome(priors: dict[str, dict[str, Any]], key: str) -> str:
    payload = priors.get(key, {})
    return str(
        payload.get("classification", {}).get("outcome")
        or payload.get("diagnosis", {}).get("failure_class")
        or payload.get("outcome")
        or ""
    )


def prior_status(priors: dict[str, dict[str, Any]], key: str) -> str:
    return str(priors.get(key, {}).get("status", ""))


def build_closeout(priors: dict[str, dict[str, Any]]) -> dict[str, Any]:
    h = priors["tier7_1h"].get("classification", {})
    i = priors["tier7_1i"].get("classification", {})
    j = priors["tier7_1j"].get("diagnosis", {})
    k = priors["tier7_1k"].get("classification", {})
    l = priors["tier7_1l"].get("classification", {})
    return {
        "outcome": "nab_claim_narrowed_return_to_general_mechanisms",
        "public_usefulness_confirmed": False,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "adapter_policy_tuning_authorized": False,
        "nab_claim_boundary": (
            "CRA v2.3 showed a partial/localized NAB anomaly signal and a "
            "same-subset false-positive repair candidate, but held-out "
            "locked-policy confirmation did not prove public NAB usefulness."
        ),
        "tier7_1h_summary": {
            "outcome": h.get("outcome"),
            "v2_3_rank": h.get("v2_3_rank"),
            "v2_3_primary_score": h.get("v2_3_primary_score"),
            "best_external_primary_score": h.get("best_external_primary_score"),
        },
        "tier7_1i_summary": {
            "outcome": i.get("outcome"),
            "best_model": i.get("best_model"),
            "v2_3_rank": i.get("v2_3_rank"),
            "v2_3_primary_score": i.get("v2_3_primary_score"),
            "localized_category_wins": i.get("v2_3_category_wins"),
        },
        "tier7_1j_summary": {
            "failure_class": j.get("failure_class"),
            "v2_3_policy_wins": j.get("v2_3_policy_wins"),
            "v2_3_beats_rolling_zscore_cells": j.get("v2_3_beats_rolling_zscore_cells"),
        },
        "tier7_1k_summary": {
            "outcome": k.get("outcome"),
            "best_policy": k.get("best_v2_3_policy"),
            "best_v2_3_rank": k.get("best_v2_3_rank"),
            "fp_reduction_vs_raw": k.get("fp_per_1000_reduction_vs_raw"),
            "window_recall_loss_vs_raw": k.get("window_recall_loss_vs_raw"),
        },
        "tier7_1l_summary": {
            "outcome": l.get("outcome"),
            "locked_policy": l.get("locked_policy"),
            "locked_v2_3_rank": l.get("locked_v2_3_rank"),
            "v2_3_beats_rolling_zscore": l.get("v2_3_beats_rolling_zscore_under_locked_policy"),
            "v2_3_beats_v2_2": l.get("v2_3_beats_v2_2_under_locked_policy"),
            "sham_separations": l.get("v2_3_sham_separations_under_locked_policy"),
            "fp_reduction_vs_raw": l.get("fp_per_1000_reduction_vs_raw"),
            "window_recall_loss_vs_raw": l.get("window_recall_loss_vs_raw"),
        },
        "failure_modes_carried_forward": [
            "false-positive versus recall tradeoff under event/anomaly scoring",
            "adapter/readout policy can improve a same subset without holding out",
            "no-update or other sham controls can remain competitive under aggressive alarm filtering",
            "standard rolling z-score remains a strong baseline on held-out NAB streams",
        ],
        "stop_rules": [
            "Do not tune additional NAB alarm policies on the same heldout set.",
            "Do not claim public NAB usefulness from Tier 7.1h-7.1l.",
            "Do not transfer the NAB adapter path to hardware without a new promoted general mechanism.",
        ],
        "selected_next_gate": "Tier 7.4a - Cost-Aware Policy/Action Selection Contract",
        "selected_next_gate_rationale": (
            "The held-out NAB failure is an action-cost problem: anomaly alarms "
            "are actions with asymmetric false-positive and missed-event costs. "
            "The next work should test a general policy/action-selection "
            "mechanism, not another NAB-specific threshold repair."
        ),
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["closeout"]
    lines = [
        "# Tier 7.1m NAB Closeout / Mechanism-Return Decision",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        "",
        "## Decision",
        "",
        f"- Public usefulness confirmed: `{c['public_usefulness_confirmed']}`",
        f"- Freeze authorized: `{c['freeze_authorized']}`",
        f"- Hardware transfer authorized: `{c['hardware_transfer_authorized']}`",
        f"- Adapter-policy tuning authorized: `{c['adapter_policy_tuning_authorized']}`",
        f"- Selected next gate: `{c['selected_next_gate']}`",
        "",
        "## Claim Boundary",
        "",
        c["nab_claim_boundary"],
        "",
        "## Failure Modes Carried Forward",
        "",
        *[f"- {item}" for item in c["failure_modes_carried_forward"]],
        "",
        "## Stop Rules",
        "",
        *[f"- {item}" for item in c["stop_rules"]],
        "",
        "## Next Gate Rationale",
        "",
        c["selected_next_gate_rationale"],
        "",
    ]
    output_dir.joinpath("tier7_1m_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    priors = {key: read_json(path) if path.exists() else {} for key, path in PRIOR_RESULTS.items()}
    closeout = build_closeout(priors)
    criteria = [
        criterion("Tier 7.1h exists", PRIOR_RESULTS["tier7_1h"], "exists", PRIOR_RESULTS["tier7_1h"].exists()),
        criterion("Tier 7.1i exists", PRIOR_RESULTS["tier7_1i"], "exists", PRIOR_RESULTS["tier7_1i"].exists()),
        criterion("Tier 7.1j exists", PRIOR_RESULTS["tier7_1j"], "exists", PRIOR_RESULTS["tier7_1j"].exists()),
        criterion("Tier 7.1k exists", PRIOR_RESULTS["tier7_1k"], "exists", PRIOR_RESULTS["tier7_1k"].exists()),
        criterion("Tier 7.1l exists", PRIOR_RESULTS["tier7_1l"], "exists", PRIOR_RESULTS["tier7_1l"].exists()),
        criterion("all prior gates passed as harnesses", [prior_status(priors, key) for key in PRIOR_RESULTS], "all pass", all(prior_status(priors, key) == "pass" for key in PRIOR_RESULTS)),
        criterion("7.1h partial signal only", prior_outcome(priors, "tier7_1h"), "partial / requires confirmation", "partial" in prior_outcome(priors, "tier7_1h") or "requires_confirmation" in prior_outcome(priors, "tier7_1h")),
        criterion("7.1i not confirmed", prior_outcome(priors, "tier7_1i"), "contains not_confirmed", "not_confirmed" in prior_outcome(priors, "tier7_1i")),
        criterion("7.1j localized false-positive pressure", priors["tier7_1j"].get("diagnosis", {}).get("failure_class"), "threshold_or_fp_penalty_sensitive", priors["tier7_1j"].get("diagnosis", {}).get("failure_class") == "threshold_or_fp_penalty_sensitive"),
        criterion("7.1k repair candidate only", prior_outcome(priors, "tier7_1k"), "contains candidate", "candidate" in prior_outcome(priors, "tier7_1k")),
        criterion("7.1l not confirmed", prior_outcome(priors, "tier7_1l"), "contains not_confirmed", "not_confirmed" in prior_outcome(priors, "tier7_1l")),
        criterion("no freeze authorized", closeout["freeze_authorized"], "== false", closeout["freeze_authorized"] is False),
        criterion("no hardware transfer authorized", closeout["hardware_transfer_authorized"], "== false", closeout["hardware_transfer_authorized"] is False),
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
        "prior_results": {key: str(path) for key, path in PRIOR_RESULTS.items()},
        "prior_outcomes": {key: prior_outcome(priors, key) for key in PRIOR_RESULTS},
        "closeout": closeout,
        "output_dir": str(output_dir),
        "claim_boundary": (
            "Tier 7.1m is a synthesis/decision gate over Tier 7.1h-7.1l. It is "
            "not a new benchmark score, not a promoted mechanism, not a "
            "baseline freeze, and not hardware/native transfer."
        ),
    }
    paths = {
        "results_json": output_dir / "tier7_1m_results.json",
        "report_md": output_dir / "tier7_1m_report.md",
        "summary_csv": output_dir / "tier7_1m_summary.csv",
        "decision_json": output_dir / "tier7_1m_decision.json",
        "decision_csv": output_dir / "tier7_1m_decision.csv",
    }
    write_json(paths["results_json"], payload)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_json(paths["decision_json"], closeout)
    write_csv(
        paths["decision_csv"],
        [
            {"field": "outcome", "value": closeout["outcome"]},
            {"field": "public_usefulness_confirmed", "value": closeout["public_usefulness_confirmed"]},
            {"field": "freeze_authorized", "value": closeout["freeze_authorized"]},
            {"field": "hardware_transfer_authorized", "value": closeout["hardware_transfer_authorized"]},
            {"field": "selected_next_gate", "value": closeout["selected_next_gate"]},
        ],
    )
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    write_json(output_dir / "tier7_1m_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_1m_latest_manifest.json", manifest)
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
                "outcome": payload["closeout"]["outcome"],
                "selected_next_gate": payload["closeout"]["selected_next_gate"],
                "output_dir": payload["output_dir"],
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
