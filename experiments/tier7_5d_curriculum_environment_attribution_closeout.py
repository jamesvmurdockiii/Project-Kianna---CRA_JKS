#!/usr/bin/env python3
"""Tier 7.5d - curriculum/environment score attribution closeout.

This is a decision/attribution gate, not a new performance run. Tier 7.5c
confirmed a strong synthetic generated-family signal. This tier decides what
that signal can honestly support:

- whether the 7.5c win depends on CRA's keyed/compositional mechanism path,
- whether shams/ablations/reference comparisons support attribution,
- whether near-oracle alignment with the public generator grammar creates a
  claim-risk that blocks promotion, and
- where the roadmap should go next.

Boundary: generated synthetic software attribution only. This does not freeze a
new baseline, prove public usefulness, or authorize hardware/native transfer.
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

TIER = "Tier 7.5d - Curriculum / Environment Score Attribution + Promotion Decision"
RUNNER_REVISION = "tier7_5d_curriculum_environment_attribution_closeout_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_5d_20260509_curriculum_environment_attribution_closeout"

TIER7_5C_DIR = CONTROLLED / "tier7_5c_20260509_curriculum_environment_scoring_gate"
TIER7_5C_RESULTS = TIER7_5C_DIR / "tier7_5c_results.json"
TIER7_5C_DECISION = TIER7_5C_DIR / "tier7_5c_decision.json"
TIER7_5C_FAMILY_DECISIONS = TIER7_5C_DIR / "tier7_5c_family_decisions.csv"
TIER7_5C_STAT_SUPPORT = TIER7_5C_DIR / "tier7_5c_statistical_support.csv"
TIER7_5C_MODEL_SUMMARY = TIER7_5C_DIR / "tier7_5c_model_summary.csv"
TIER7_5C_SHAMS = TIER7_5C_DIR / "tier7_5c_sham_controls.csv"

NEXT_GATE = "Tier 7.6a - Long-Horizon Planning / Subgoal Control Contract"
CANDIDATE = "current_cra_v2_4"
REFERENCE = "v2_2_reference"


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
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in {None, ""}:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


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


def support_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(row.get("family_id", ""), row.get("baseline", "")): row for row in rows}


def model_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(row.get("family_id", ""), row.get("model", "")): row for row in rows if row.get("split_group") == "hidden"}


def build_attribution_rows(
    family_rows: list[dict[str, str]],
    support_rows: list[dict[str, str]],
    model_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    support = support_lookup(support_rows)
    models = model_lookup(model_rows)
    out: list[dict[str, Any]] = []
    for row in family_rows:
        family = row["family_id"]
        candidate_mse = to_float(row["candidate_hidden_mse"])
        oracle_mse = to_float(models.get((family, "oracle_upper_bound"), {}).get("mse"))
        key_shuffle_mse = to_float(models.get((family, "key_shuffle_sham"), {}).get("mse"))
        target_shuffle_mse = to_float(models.get((family, "target_shuffle_sham"), {}).get("mse"))
        no_key_mse = to_float(models.get((family, "no_key_ablation"), {}).get("mse"))
        best_sham = row["best_sham"]
        best_external = row["best_external"]
        ext_support = support.get((family, best_external), {})
        sham_support = support.get((family, best_sham), {})
        ref_support = support.get((family, REFERENCE), {})
        out.append(
            {
                "family_id": family,
                "candidate_hidden_mse": candidate_mse,
                "candidate_hidden_sign_accuracy": to_float(row["candidate_hidden_sign_accuracy"]),
                "candidate_expected_utility_per_1000": to_float(row["candidate_hidden_expected_utility_per_1000"]),
                "oracle_hidden_mse": oracle_mse,
                "near_oracle_candidate": candidate_mse <= 1e-6,
                "best_external": best_external,
                "external_ci_low": to_float(ext_support.get("ci_low")),
                "best_sham": best_sham,
                "best_sham_ci_low": to_float(sham_support.get("ci_low")),
                "reference_ci_low": to_float(ref_support.get("ci_low")),
                "key_shuffle_mse": key_shuffle_mse,
                "target_shuffle_mse": target_shuffle_mse,
                "no_key_mse": no_key_mse,
                "key_shuffle_loses": key_shuffle_mse > candidate_mse,
                "target_shuffle_loses": target_shuffle_mse > candidate_mse,
                "no_key_loses": no_key_mse > candidate_mse,
                "reference_loses_with_positive_ci": as_bool(row["candidate_beats_reference_mse"]) and to_float(ref_support.get("ci_low")) > 0.0,
                "external_loses_with_positive_ci": as_bool(row["candidate_beats_best_external_mse"]) and to_float(ext_support.get("ci_low")) > 0.0,
                "best_sham_loses_with_positive_ci": as_bool(row["candidate_beats_best_sham_mse"]) and to_float(sham_support.get("ci_low")) > 0.0,
                "mechanism_attribution_supported": (
                    as_bool(row["candidate_beats_reference_mse"])
                    and as_bool(row["candidate_beats_best_external_mse"])
                    and as_bool(row["candidate_beats_best_sham_mse"])
                    and to_float(ref_support.get("ci_low")) > 0.0
                    and to_float(ext_support.get("ci_low")) > 0.0
                    and to_float(sham_support.get("ci_low")) > 0.0
                    and key_shuffle_mse > candidate_mse
                    and target_shuffle_mse > candidate_mse
                    and no_key_mse > candidate_mse
                ),
            }
        )
    return out


def make_claim_rows(decision: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "claim": "Generated-family synthetic keyed/compositional mechanism signal",
            "authorized": decision["generated_synthetic_mechanism_attribution_authorized"],
            "basis": "7.5c candidate beat external baselines, v2.2 reference, and shams/ablations with positive paired support across locked synthetic families.",
            "boundary": "Synthetic generated-family software evidence only; requires public/real-ish confirmation before usefulness claims.",
        },
        {
            "claim": "New software baseline freeze",
            "authorized": decision["freeze_authorized"],
            "basis": "7.5d is attribution closeout and introduces no new mechanism beyond v2.4.",
            "boundary": "Keep CRA_EVIDENCE_BASELINE_v2.4 as the current software baseline.",
        },
        {
            "claim": "Broad public usefulness",
            "authorized": decision["broad_public_usefulness_authorized"],
            "basis": "Generated synthetic families are not public/real-world benchmarks and the generator grammar is known.",
            "boundary": "Not authorized.",
        },
        {
            "claim": "Hardware/native transfer",
            "authorized": decision["hardware_transfer_authorized"],
            "basis": "The result is synthetic software attribution only and does not justify native migration.",
            "boundary": "Not authorized.",
        },
        {
            "claim": "AGI/ASI, language, or broad planning",
            "authorized": False,
            "basis": "7.5c/7.5d test generated curriculum families, not language, open-ended planning, or general intelligence.",
            "boundary": "Not authorized.",
        },
    ]


def make_route_rows() -> list[dict[str, Any]]:
    return [
        {
            "route": "preserve_generated_family_signal",
            "selected": True,
            "reason": "The 7.5c signal separates from external baselines, v2.2 reference, and shams on locked synthetic families.",
        },
        {
            "route": "do_not_freeze_v2_5",
            "selected": True,
            "reason": "No new mechanism was introduced; v2.4 remains the current frozen software baseline.",
        },
        {
            "route": "do_not_transfer_7_5c_to_hardware",
            "selected": True,
            "reason": "The gate is synthetic software attribution, not a native mechanism migration target.",
        },
        {
            "route": "start_tier_7_6a_long_horizon_planning_contract",
            "selected": True,
            "reason": "After curriculum/environment generation, the roadmap's next unclosed capability is long-horizon planning/subgoal control.",
        },
        {
            "route": "return_to_generator_tuning",
            "selected": False,
            "reason": "Changing generated tasks after scoring would contaminate the locked 7.5a/7.5b evidence chain.",
        },
    ]


def make_risk_rows(attribution_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    near_oracle_count = sum(1 for row in attribution_rows if row["near_oracle_candidate"])
    return [
        {
            "risk": "generator_feature_alignment",
            "level": "high" if near_oracle_count == len(attribution_rows) else "medium",
            "evidence": f"{near_oracle_count}/{len(attribution_rows)} families have candidate hidden MSE <= 1e-6.",
            "mitigation": "Do not freeze or claim public usefulness; require public/real-ish confirmation or a harder hidden generator before stronger claims.",
        },
        {
            "risk": "synthetic_holdout_is_not_public_benchmark",
            "level": "high",
            "evidence": "Tier 7.5b generator and hash recipe are part of the repository.",
            "mitigation": "Use this only as mechanism-pressure evidence; route public claims through real-ish adapters and standardized benchmarks.",
        },
        {
            "risk": "mechanism_shortcut_overclaim",
            "level": "medium",
            "evidence": "The candidate feature path can express the synthetic generator grammar.",
            "mitigation": "Carry claim as keyed/compositional attribution only; require future black-box/held-out task families before promotion.",
        },
    ]


def make_claim_boundary(decision: dict[str, Any], risk_rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# Tier 7.5d Claim Boundary",
            "",
            f"- Outcome: `{decision['outcome']}`",
            f"- Synthetic mechanism attribution authorized: `{decision['generated_synthetic_mechanism_attribution_authorized']}`",
            f"- Broad public usefulness authorized: `{decision['broad_public_usefulness_authorized']}`",
            f"- Freeze authorized: `{decision['freeze_authorized']}`",
            f"- Hardware transfer authorized: `{decision['hardware_transfer_authorized']}`",
            f"- Next gate: `{decision['next_gate']}`",
            "",
            "Tier 7.5d preserves a bounded synthetic generated-family mechanism signal. It does not make a public usefulness claim because the generator grammar is known and aligned with keyed/compositional features. It does not freeze a new baseline because no new CRA mechanism was introduced beyond v2.4.",
            "",
            "## Risk Register",
            "",
            *[f"- `{row['risk']}`: {row['level']} - {row['mitigation']}" for row in risk_rows],
            "",
        ]
    )


def make_report(
    output_dir: Path,
    status: str,
    criteria: list[dict[str, Any]],
    decision: dict[str, Any],
    attribution_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
    route_rows: list[dict[str, Any]],
    risk_rows: list[dict[str, Any]],
) -> str:
    passed = sum(1 for c in criteria if c["passed"])
    supported = sum(1 for row in attribution_rows if row["mechanism_attribution_supported"])
    lines = [
        "# Tier 7.5d Curriculum / Environment Score Attribution Closeout",
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
        f"- mechanism_attribution_supported_families: `{supported}/{len(attribution_rows)}`",
        f"- next_gate: `{decision['next_gate']}`",
        f"- freeze_authorized: `{decision['freeze_authorized']}`",
        f"- hardware_transfer_authorized: `{decision['hardware_transfer_authorized']}`",
        "",
        "## Attribution Checks",
        "",
        "| Family | Attribution Supported | Near Oracle | Reference CI Low | External CI Low | Best Sham CI Low |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in attribution_rows:
        lines.append(
            f"| {row['family_id']} | {row['mechanism_attribution_supported']} | {row['near_oracle_candidate']} | "
            f"{row['reference_ci_low']} | {row['external_ci_low']} | {row['best_sham_ci_low']} |"
        )
    lines.extend(["", "## Claim Decisions", "", "| Claim | Authorized | Boundary |", "| --- | --- | --- |"])
    for row in claim_rows:
        lines.append(f"| {row['claim']} | {row['authorized']} | {row['boundary']} |")
    lines.extend(["", "## Route Decisions", "", "| Route | Selected | Reason |", "| --- | --- | --- |"])
    for row in route_rows:
        lines.append(f"| {row['route']} | {row['selected']} | {row['reason']} |")
    lines.extend(["", "## Risks", "", "| Risk | Level | Mitigation |", "| --- | --- | --- |"])
    for row in risk_rows:
        lines.append(f"| {row['risk']} | {row['level']} | {row['mitigation']} |")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Details |", "| --- | --- | --- | --- | --- |"])
    for row in criteria:
        lines.append(
            f"| {row['criterion']} | `{row['value']}` | {row['rule']} | "
            f"{'yes' if row['passed'] else 'no'} | {row.get('details', '')} |"
        )
    lines.append("")
    return "\n".join(lines)


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    return {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": str(output_dir),
        "artifacts": [
            {"name": name, "path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in sorted(artifacts.items())
        ],
    }


def main() -> int:
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    results_5c = read_json(TIER7_5C_RESULTS)
    decision_5c = read_json(TIER7_5C_DECISION)
    family_rows = read_csv_rows(TIER7_5C_FAMILY_DECISIONS)
    support_rows = read_csv_rows(TIER7_5C_STAT_SUPPORT)
    model_rows = read_csv_rows(TIER7_5C_MODEL_SUMMARY)
    sham_rows = read_csv_rows(TIER7_5C_SHAMS)

    attribution_rows = build_attribution_rows(family_rows, support_rows, model_rows)
    supported_count = sum(1 for row in attribution_rows if row["mechanism_attribution_supported"])
    near_oracle_count = sum(1 for row in attribution_rows if row["near_oracle_candidate"])
    risk_rows = make_risk_rows(attribution_rows)
    decision = {
        "tier": TIER,
        "status": "PASS",
        "outcome": "synthetic_mechanism_attribution_supported_no_freeze",
        "generated_synthetic_mechanism_attribution_authorized": supported_count == len(attribution_rows) and supported_count > 0,
        "generated_family_signal_preserved": as_bool(decision_5c.get("generated_family_signal_authorized")),
        "broad_public_usefulness_authorized": False,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "feature_alignment_risk_high": near_oracle_count == len(attribution_rows) and near_oracle_count > 0,
        "next_gate": NEXT_GATE,
    }
    claim_rows = make_claim_rows(decision)
    route_rows = make_route_rows()

    criteria = [
        criterion("tier7_5c_results_exist", TIER7_5C_RESULTS.exists(), "must exist", TIER7_5C_RESULTS.exists(), str(TIER7_5C_RESULTS)),
        criterion("tier7_5c_status_pass", results_5c.get("status"), "case-insensitive == PASS", str(results_5c.get("status", "")).upper() == "PASS"),
        criterion("tier7_5c_signal_count", decision_5c.get("confirmed_generated_family_count"), "== 6", int(decision_5c.get("confirmed_generated_family_count", 0)) == 6),
        criterion("attribution_rows_written", len(attribution_rows), "== 6", len(attribution_rows) == 6),
        criterion("all_families_attribution_supported", supported_count, "== attribution rows", supported_count == len(attribution_rows) and supported_count > 0),
        criterion("reference_separation_preserved", sum(1 for row in attribution_rows if row["reference_loses_with_positive_ci"]), "== 6", sum(1 for row in attribution_rows if row["reference_loses_with_positive_ci"]) == 6),
        criterion("external_separation_preserved", sum(1 for row in attribution_rows if row["external_loses_with_positive_ci"]), "== 6", sum(1 for row in attribution_rows if row["external_loses_with_positive_ci"]) == 6),
        criterion("sham_separation_preserved", sum(1 for row in attribution_rows if row["best_sham_loses_with_positive_ci"]), "== 6", sum(1 for row in attribution_rows if row["best_sham_loses_with_positive_ci"]) == 6),
        criterion("feature_ablation_loss_preserved", sum(1 for row in attribution_rows if row["no_key_loses"] and row["key_shuffle_loses"] and row["target_shuffle_loses"]), "== 6", sum(1 for row in attribution_rows if row["no_key_loses"] and row["key_shuffle_loses"] and row["target_shuffle_loses"]) == 6),
        criterion("near_oracle_risk_documented", near_oracle_count, "== 6 and blocks overclaim", near_oracle_count == 6),
        criterion("risk_register_written", len(risk_rows), ">= 3", len(risk_rows) >= 3),
        criterion("claim_rows_written", len(claim_rows), ">= 5", len(claim_rows) >= 5),
        criterion("route_rows_written", len(route_rows), ">= 5", len(route_rows) >= 5),
        criterion("broad_public_claim_blocked", decision["broad_public_usefulness_authorized"], "must be False", not decision["broad_public_usefulness_authorized"]),
        criterion("freeze_blocked", decision["freeze_authorized"], "must be False", not decision["freeze_authorized"]),
        criterion("hardware_transfer_blocked", decision["hardware_transfer_authorized"], "must be False", not decision["hardware_transfer_authorized"]),
        criterion("next_gate_selected", decision["next_gate"], f"== {NEXT_GATE}", decision["next_gate"] == NEXT_GATE),
        criterion("sham_controls_source_loaded", len(sham_rows), ">= 18", len(sham_rows) >= 18),
    ]
    status = "PASS" if all(c["passed"] for c in criteria) else "FAIL"
    decision["status"] = status

    results = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "criteria": criteria,
        "decision": decision,
        "attribution_checks": attribution_rows,
        "risk_register": risk_rows,
    }
    artifacts = {
        "results_json": output_dir / "tier7_5d_results.json",
        "summary_csv": output_dir / "tier7_5d_summary.csv",
        "report_md": output_dir / "tier7_5d_report.md",
        "attribution_checks_csv": output_dir / "tier7_5d_attribution_checks.csv",
        "claim_decisions_csv": output_dir / "tier7_5d_claim_decisions.csv",
        "route_decisions_csv": output_dir / "tier7_5d_route_decisions.csv",
        "risk_register_csv": output_dir / "tier7_5d_risk_register.csv",
        "decision_json": output_dir / "tier7_5d_decision.json",
        "decision_csv": output_dir / "tier7_5d_decision.csv",
        "claim_boundary_md": output_dir / "tier7_5d_claim_boundary.md",
    }
    write_json(artifacts["results_json"], results)
    write_csv(artifacts["summary_csv"], criteria, ["criterion", "value", "rule", "pass", "details"])
    write_csv(artifacts["attribution_checks_csv"], attribution_rows)
    write_csv(artifacts["claim_decisions_csv"], claim_rows)
    write_csv(artifacts["route_decisions_csv"], route_rows)
    write_csv(artifacts["risk_register_csv"], risk_rows)
    write_json(artifacts["decision_json"], decision)
    write_csv(artifacts["decision_csv"], [decision])
    artifacts["claim_boundary_md"].write_text(make_claim_boundary(decision, risk_rows), encoding="utf-8")
    artifacts["report_md"].write_text(make_report(output_dir, status, criteria, decision, attribution_rows, claim_rows, route_rows, risk_rows), encoding="utf-8")
    latest = make_manifest(output_dir, artifacts, status)
    artifacts["latest_manifest_json"] = output_dir / "tier7_5d_latest_manifest.json"
    write_json(artifacts["latest_manifest_json"], latest)

    print(
        json.dumps(
            json_safe(
                {
                    "status": status,
                    "outcome": decision["outcome"],
                    "attribution_supported_families": supported_count,
                    "near_oracle_risk_families": near_oracle_count,
                    "output_dir": output_dir,
                    "next_gate": NEXT_GATE,
                }
            ),
            indent=2,
        )
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
