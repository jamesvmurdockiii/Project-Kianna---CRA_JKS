#!/usr/bin/env python3
"""Tier 7.4h - policy/action attribution closeout.

This is a decision/attribution gate, not a new performance run. It closes the
Tier 7.4 held-out policy/action chain by reconciling:

- Tier 7.4f: qualified C-MAPSS-only action-cost signal,
- Tier 7.4g: C-MAPSS external/sham confirmation,
- Tier 7.4g: no v2.4-v2.2 reference separation, and
- Tier 7.4g: NAB non-confirmation classified as event-coverage gap.

The purpose is to prevent claim inflation before the project returns to the
mechanism/benchmark loop.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 7.4h - Policy/Action Attribution Closeout / Mechanism Return Decision"
RUNNER_REVISION = "tier7_4h_policy_action_attribution_closeout_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_4h_20260509_policy_action_attribution_closeout"

TIER7_4F_DIR = CONTROLLED / "tier7_4f_20260509_cost_aware_policy_action_heldout_scoring_gate"
TIER7_4G_DIR = CONTROLLED / "tier7_4g_20260509_policy_action_confirmation_reference_separation"

TIER7_4F_RESULTS = TIER7_4F_DIR / "tier7_4f_results.json"
TIER7_4F_DECISION = TIER7_4F_DIR / "tier7_4f_decision.json"
TIER7_4G_RESULTS = TIER7_4G_DIR / "tier7_4g_results.json"
TIER7_4G_DECISION = TIER7_4G_DIR / "tier7_4g_decision.json"
TIER7_4G_CONFIRMATION = TIER7_4G_DIR / "tier7_4g_confirmation_checks.csv"
TIER7_4G_NAB_FAILURE = TIER7_4G_DIR / "tier7_4g_nab_failure_analysis.csv"

NEXT_GATE = "Tier 7.5a - Curriculum / Environment Generator Contract"


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


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in fieldnames})


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in {None, ""}:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "criterion": name,
        "value": value,
        "operator": rule,
        "rule": rule,
        "passed": bool(passed),
        "pass": bool(passed),
        "note": details,
        "details": details,
    }


def confirmation_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row.get("comparison", ""): row for row in rows}


def make_claim_rows(decision: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "claim": "Narrow C-MAPSS action-cost signal versus external/sham controls",
            "authorized": decision["narrow_cmapss_action_cost_claim_authorized"],
            "basis": "Tier 7.4g positive paired CI versus strongest external baseline and sham.",
            "boundary": "C-MAPSS maintenance-action utility only; software held-out scoring only.",
        },
        {
            "claim": "Broad public usefulness across public/real-ish tasks",
            "authorized": decision["broad_public_usefulness_authorized"],
            "basis": "NAB did not confirm; only one family has a narrow positive signal.",
            "boundary": "Not authorized.",
        },
        {
            "claim": "Incremental v2.4 superiority over prior v2.2 CRA reference",
            "authorized": decision["incremental_v2_4_over_v2_2_claim_authorized"],
            "basis": "C-MAPSS v2.4-v2.2 paired CI crosses zero; NAB is also not separated.",
            "boundary": "Not authorized.",
        },
        {
            "claim": "New software baseline freeze",
            "authorized": decision["freeze_authorized"],
            "basis": "Tier 7.4h is attribution closeout only.",
            "boundary": "Keep CRA_EVIDENCE_BASELINE_v2.4 as current frozen host-side policy/action baseline.",
        },
        {
            "claim": "Hardware/native transfer of the policy/action result",
            "authorized": decision["hardware_transfer_authorized"],
            "basis": "Held-out software signal is too narrow and not v2.4-specific.",
            "boundary": "Native substrate work remains separate engineering evidence.",
        },
    ]


def make_route_rows() -> list[dict[str, Any]]:
    return [
        {
            "route": "stop_policy_action_heldout_tuning",
            "selected": True,
            "reason": "The NAB chain already had diagnostic/repair/holdout/closeout gates; retroactive tuning would contaminate held-out evidence.",
        },
        {
            "route": "keep_v2_4_baseline_without_new_freeze",
            "selected": True,
            "reason": "v2.4 remains the frozen host-side policy/action baseline, but 7.4g did not justify v2.5 or hardware transfer.",
        },
        {
            "route": "return_to_general_mechanism_benchmark_loop",
            "selected": True,
            "reason": "The next evidence question is not more NAB/C-MAPSS policy tuning; it is whether a general mechanism improves public/real-ish tasks under locked controls.",
        },
        {
            "route": "start_tier_7_5a_curriculum_environment_contract",
            "selected": True,
            "reason": "The roadmap's next unclosed general capability branch is curriculum/environment generation before longer-horizon planning.",
        },
        {
            "route": "hardware_transfer_policy_action_result",
            "selected": False,
            "reason": "No broad or incremental held-out policy/action claim is authorized.",
        },
    ]


def make_report(
    output_dir: Path,
    status: str,
    criteria: list[dict[str, Any]],
    decision: dict[str, Any],
    claim_rows: list[dict[str, Any]],
    route_rows: list[dict[str, Any]],
) -> str:
    passed = sum(1 for c in criteria if c["passed"])
    lines = [
        "# Tier 7.4h Policy/Action Attribution Closeout",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{status}**",
        f"- Output directory: `{output_dir}`",
        f"- Runner revision: `{RUNNER_REVISION}`",
        "",
        "## Summary",
        "",
        f"- criteria_passed: `{passed}/{len(criteria)}`",
        f"- outcome: `{decision['outcome']}`",
        f"- next_gate: `{decision['next_gate']}`",
        f"- freeze_authorized: `{decision['freeze_authorized']}`",
        f"- hardware_transfer_authorized: `{decision['hardware_transfer_authorized']}`",
        "",
        "## Claim Decisions",
        "",
        "| Claim | Authorized | Boundary |",
        "| --- | --- | --- |",
    ]
    for row in claim_rows:
        lines.append(f"| {row['claim']} | {row['authorized']} | {row['boundary']} |")
    lines.extend(
        [
            "",
            "## Route Decisions",
            "",
            "| Route | Selected | Reason |",
            "| --- | --- | --- |",
        ]
    )
    for row in route_rows:
        lines.append(f"| {row['route']} | {row['selected']} | {row['reason']} |")
    lines.extend(
        [
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass | Details |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in criteria:
        lines.append(
            f"| {row['criterion']} | `{row['value']}` | {row['rule']} | "
            f"{'yes' if row['passed'] else 'no'} | {row.get('details', '')} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Tier 7.4h closes the current policy/action chain without inflating it. The evidence supports a narrow C-MAPSS maintenance-action utility signal against external/sham controls, but it does not support broad public usefulness, incremental v2.4 superiority over v2.2, a new freeze, or hardware/native transfer. The correct next step is to stop tuning this held-out chain and return to the general mechanism/benchmark roadmap, starting with the Tier 7.5a curriculum/environment-generator contract.",
            "",
        ]
    )
    return "\n".join(lines)


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


def main() -> int:
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    f_results = read_json(TIER7_4F_RESULTS)
    f_decision = read_json(TIER7_4F_DECISION)
    g_results = read_json(TIER7_4G_RESULTS)
    g_decision = read_json(TIER7_4G_DECISION)
    confirmation = confirmation_lookup(read_csv_rows(TIER7_4G_CONFIRMATION))
    nab_failure_rows = read_csv_rows(TIER7_4G_NAB_FAILURE)
    nab_failure = nab_failure_rows[0] if nab_failure_rows else {}

    cmapss_external = confirmation.get("cmapss_candidate_vs_best_external", {})
    cmapss_sham = confirmation.get("cmapss_candidate_vs_best_sham", {})
    cmapss_reference = confirmation.get("cmapss_candidate_vs_v2_2_reference", {})
    nab_external = confirmation.get("nab_candidate_vs_best_external", {})

    narrow_cmapss_signal = (
        as_bool(g_decision.get("narrow_cmapss_external_signal_authorized"))
        and as_bool(cmapss_external.get("positive_ci_confirmed"))
        and as_bool(cmapss_sham.get("positive_ci_confirmed"))
    )
    reference_not_separated = not as_bool(g_decision.get("incremental_v2_4_reference_claim_authorized"))
    nab_not_confirmed = to_float(nab_external.get("mean_delta"), 1.0) <= 0.0 and not as_bool(nab_external.get("positive_ci_confirmed"))

    decision = {
        "tier": TIER,
        "status": "PASS",
        "outcome": "policy_action_track_closed_narrow_cmapss_signal_return_to_mechanism_benchmark_loop",
        "narrow_cmapss_action_cost_claim_authorized": narrow_cmapss_signal,
        "incremental_v2_4_over_v2_2_claim_authorized": False,
        "broad_public_usefulness_authorized": False,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "retroactive_heldout_tuning_authorized": False,
        "current_frozen_software_baseline": "CRA_EVIDENCE_BASELINE_v2.4",
        "next_gate": NEXT_GATE,
        "rationale": (
            "Tier 7.4g confirms only the narrow C-MAPSS external/sham signal. "
            "Reference separation and NAB confirmation both fail, so the action-policy "
            "track closes without a new freeze or hardware transfer."
        ),
    }

    criteria = [
        criterion("tier7_4f_results_exist", TIER7_4F_RESULTS.exists(), "must exist", TIER7_4F_RESULTS.exists(), str(TIER7_4F_RESULTS)),
        criterion("tier7_4f_status_pass", f_results.get("status"), "case-insensitive == PASS", str(f_results.get("status", "")).upper() == "PASS"),
        criterion("tier7_4g_results_exist", TIER7_4G_RESULTS.exists(), "must exist", TIER7_4G_RESULTS.exists(), str(TIER7_4G_RESULTS)),
        criterion("tier7_4g_status_pass", g_results.get("status"), "case-insensitive == PASS", str(g_results.get("status", "")).upper() == "PASS"),
        criterion("narrow_cmapss_signal_preserved", narrow_cmapss_signal, "must be True", narrow_cmapss_signal),
        criterion("cmapss_external_ci_positive", cmapss_external.get("ci_low"), "> 0", to_float(cmapss_external.get("ci_low")) > 0.0),
        criterion("cmapss_sham_ci_positive", cmapss_sham.get("ci_low"), "> 0", to_float(cmapss_sham.get("ci_low")) > 0.0),
        criterion("reference_nonseparation_preserved", cmapss_reference.get("ci_low"), "<= 0", reference_not_separated and to_float(cmapss_reference.get("ci_low"), 1.0) <= 0.0),
        criterion("nab_nonconfirmation_preserved", nab_external.get("mean_delta"), "<= 0 and CI not positive", nab_not_confirmed),
        criterion("nab_failure_class_preserved", nab_failure.get("failure_class_vs_ewma"), "non-empty", bool(nab_failure.get("failure_class_vs_ewma"))),
        criterion("broad_claim_blocked", decision["broad_public_usefulness_authorized"], "must be False", not decision["broad_public_usefulness_authorized"]),
        criterion("incremental_v2_4_claim_blocked", decision["incremental_v2_4_over_v2_2_claim_authorized"], "must be False", not decision["incremental_v2_4_over_v2_2_claim_authorized"]),
        criterion("freeze_blocked", decision["freeze_authorized"], "must be False", not decision["freeze_authorized"]),
        criterion("hardware_transfer_blocked", decision["hardware_transfer_authorized"], "must be False", not decision["hardware_transfer_authorized"]),
        criterion("retroactive_tuning_blocked", decision["retroactive_heldout_tuning_authorized"], "must be False", not decision["retroactive_heldout_tuning_authorized"]),
        criterion("next_gate_selected", decision["next_gate"], "non-empty", bool(decision["next_gate"])),
    ]
    status = "PASS" if all(c["passed"] for c in criteria) else "FAIL"
    decision["status"] = status

    claim_rows = make_claim_rows(decision)
    route_rows = make_route_rows()
    results = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "source_artifacts": {
            "tier7_4f_results": str(TIER7_4F_RESULTS),
            "tier7_4f_decision": str(TIER7_4F_DECISION),
            "tier7_4g_results": str(TIER7_4G_RESULTS),
            "tier7_4g_decision": str(TIER7_4G_DECISION),
            "tier7_4g_confirmation": str(TIER7_4G_CONFIRMATION),
            "tier7_4g_nab_failure": str(TIER7_4G_NAB_FAILURE),
        },
        "criteria": criteria,
        "decision": decision,
        "claim_rows": claim_rows,
        "route_rows": route_rows,
    }

    artifacts: dict[str, Path] = {
        "results_json": output_dir / "tier7_4h_results.json",
        "summary_csv": output_dir / "tier7_4h_summary.csv",
        "report_md": output_dir / "tier7_4h_report.md",
        "decision_json": output_dir / "tier7_4h_decision.json",
        "decision_csv": output_dir / "tier7_4h_decision.csv",
        "claim_boundary_csv": output_dir / "tier7_4h_claim_boundary.csv",
        "route_decision_csv": output_dir / "tier7_4h_route_decision.csv",
    }
    write_json(artifacts["results_json"], results)
    write_csv(artifacts["summary_csv"], criteria, ["criterion", "value", "rule", "pass", "details"])
    write_json(artifacts["decision_json"], decision)
    write_csv(artifacts["decision_csv"], [decision])
    write_csv(artifacts["claim_boundary_csv"], claim_rows)
    write_csv(artifacts["route_decision_csv"], route_rows)
    artifacts["report_md"].write_text(make_report(output_dir, status, criteria, decision, claim_rows, route_rows), encoding="utf-8")
    manifest = make_manifest(output_dir, artifacts, status)
    artifacts["latest_manifest_json"] = output_dir / "tier7_4h_latest_manifest.json"
    write_json(artifacts["latest_manifest_json"], manifest)

    print(json.dumps(json_safe({"status": status, "outcome": decision["outcome"], "output_dir": output_dir, "next_gate": NEXT_GATE}), indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
