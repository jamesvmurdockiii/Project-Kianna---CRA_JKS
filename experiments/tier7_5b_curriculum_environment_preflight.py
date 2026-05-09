#!/usr/bin/env python3
"""Tier 7.5b - curriculum/environment generator implementation preflight.

This gate materializes deterministic dry-run generator artifacts under the
Tier 7.5a contract. It intentionally does not score CRA or baselines. Hidden
holdout labels are replaced with hashes in the public stream artifact so later
scoring can prove labels were not exposed during implementation.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 7.5b - Curriculum / Environment Generator Implementation Preflight"
RUNNER_REVISION = "tier7_5b_curriculum_environment_preflight_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_5b_20260509_curriculum_environment_preflight"

PREREQ = CONTROLLED / "tier7_5a_20260509_curriculum_environment_contract" / "tier7_5a_results.json"
NEXT_GATE = "Tier 7.5c - Curriculum / Environment Generator Scoring Gate"

FAMILIES = [
    "generated_delayed_credit",
    "generated_hidden_context_reentry",
    "generated_nonstationary_switching",
    "generated_compositional_reuse",
    "generated_policy_action_cost",
    "generated_predictive_binding",
]
SPLITS = ["generator_train", "generator_validation", "generated_holdout", "generator_ood_holdout"]
BASELINES = [
    "current_cra_v2_4",
    "v2_2_reference",
    "lag_ridge_or_ar",
    "online_logistic_or_perceptron",
    "reservoir_esn",
    "small_gru",
    "bandit_or_simple_rl",
    "stpd_only_snn",
    "oracle_upper_bound",
]
FEATURES = ["cue", "context_key", "route_key", "memory_key", "noise", "lag_1", "lag_2", "cost_hint"]


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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        "value": value,
        "operator": rule,
        "rule": rule,
        "passed": bool(passed),
        "pass": bool(passed),
        "note": details,
        "details": details,
    }


def family_seed(family: str, split: str) -> int:
    return int(sha256_text(f"{family}:{split}:tier7_5b")[:8], 16)


def hidden_label_hash(family: str, split: str, row_id: str, target: float, action: str) -> str:
    return sha256_text(f"{family}|{split}|{row_id}|{target:.6f}|{action}|hidden_v1")


def row_count_for(split: str) -> int:
    return {
        "generator_train": 24,
        "generator_validation": 16,
        "generated_holdout": 12,
        "generator_ood_holdout": 12,
    }[split]


def generate_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    stream_rows: list[dict[str, Any]] = []
    hidden_rows: list[dict[str, Any]] = []
    split_rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        for split in SPLITS:
            rng = random.Random(family_seed(family, split))
            difficulty = 1 if split == "generator_train" else 2 if split == "generator_validation" else 3 if split == "generated_holdout" else 4
            count = row_count_for(split)
            hidden = split in {"generated_holdout", "generator_ood_holdout"}
            split_rows.append(
                {
                    "family_id": family,
                    "split": split,
                    "rows": count,
                    "difficulty_level": difficulty,
                    "hidden_from_development": hidden,
                    "seed": family_seed(family, split),
                    "label_visibility": "hash_only" if hidden else "visible_for_development_only",
                }
            )
            for i in range(count):
                cue = rng.choice([-1.0, 1.0])
                context_key = rng.randint(0, 5 + difficulty)
                route_key = rng.randint(0, 3 + difficulty)
                memory_key = rng.randint(0, 4 + difficulty)
                noise = round(rng.uniform(-0.25 * difficulty, 0.25 * difficulty), 6)
                lag_1 = round(math.sin((i + 1) * (difficulty + 1) / 5.0), 6)
                lag_2 = round(math.cos((i + 2) * (difficulty + 2) / 7.0), 6)
                cost_hint = round((difficulty * 0.1) + (0.05 if family == "generated_policy_action_cost" else 0.0), 6)
                target = cue * (1 if (context_key + route_key + memory_key) % 2 == 0 else -1) + 0.15 * lag_1 - 0.10 * lag_2 + noise
                action = "act" if target > 0.35 else "monitor" if target > -0.15 else "wait"
                row_id = f"{family}:{split}:{i:03d}"
                label_hash = hidden_label_hash(family, split, row_id, target, action)
                stream_rows.append(
                    {
                        "row_id": row_id,
                        "family_id": family,
                        "split": split,
                        "difficulty_level": difficulty,
                        "time_index": i,
                        "cue": cue,
                        "context_key": context_key,
                        "route_key": route_key,
                        "memory_key": memory_key,
                        "noise": noise,
                        "lag_1": lag_1,
                        "lag_2": lag_2,
                        "cost_hint": cost_hint,
                        "target_visible_online": False,
                        "label_visible_to_development": not hidden,
                        "target_value": "" if hidden else round(target, 6),
                        "action_label": "" if hidden else action,
                        "hidden_label_hash": label_hash,
                    }
                )
                hidden_rows.append(
                    {
                        "row_id": row_id,
                        "family_id": family,
                        "split": split,
                        "hidden": hidden,
                        "target_hash": label_hash,
                        "target_value_stored_in_public_stream": not hidden,
                    }
                )
    return stream_rows, hidden_rows, split_rows


def baseline_compatibility_rows() -> list[dict[str, Any]]:
    rows = []
    for family in FAMILIES:
        for baseline in BASELINES:
            compatible = not (baseline == "bandit_or_simple_rl" and family not in {"generated_policy_action_cost", "generated_nonstationary_switching"})
            rows.append(
                {
                    "family_id": family,
                    "baseline": baseline,
                    "compatible": compatible,
                    "reason": "action family required" if not compatible else "schema-compatible dry run",
                    "features": ",".join(FEATURES),
                    "labels_available_online": False,
                }
            )
    return rows


def schema_rows() -> list[dict[str, Any]]:
    return [
        {"field": "row_id", "type": "string", "online_visible": True, "required": True},
        {"field": "family_id", "type": "string", "online_visible": True, "required": True},
        {"field": "split", "type": "string", "online_visible": True, "required": True},
        {"field": "difficulty_level", "type": "int", "online_visible": True, "required": True},
        *[
            {"field": feature, "type": "float_or_int", "online_visible": True, "required": True}
            for feature in FEATURES
        ],
        {"field": "target_visible_online", "type": "bool", "online_visible": True, "required": True},
        {"field": "target_value", "type": "float_or_blank", "online_visible": False, "required": False},
        {"field": "action_label", "type": "string_or_blank", "online_visible": False, "required": False},
        {"field": "hidden_label_hash", "type": "sha256", "online_visible": True, "required": True},
    ]


def leakage_check_rows(stream_rows: list[dict[str, Any]], hidden_rows: list[dict[str, Any]], compatibility: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hidden_stream_rows = [r for r in stream_rows if r["split"] in {"generated_holdout", "generator_ood_holdout"}]
    return [
        {
            "check": "hidden_holdout_targets_blank",
            "value": sum(1 for r in hidden_stream_rows if r["target_value"] == "" and r["action_label"] == ""),
            "expected": len(hidden_stream_rows),
            "pass": all(r["target_value"] == "" and r["action_label"] == "" for r in hidden_stream_rows),
        },
        {
            "check": "hidden_label_hashes_present",
            "value": sum(1 for r in hidden_stream_rows if r["hidden_label_hash"]),
            "expected": len(hidden_stream_rows),
            "pass": all(bool(r["hidden_label_hash"]) for r in hidden_stream_rows),
        },
        {
            "check": "online_target_visibility_false",
            "value": sum(1 for r in stream_rows if not r["target_visible_online"]),
            "expected": len(stream_rows),
            "pass": all(not r["target_visible_online"] for r in stream_rows),
        },
        {
            "check": "hidden_hash_manifest_matches_stream",
            "value": len(hidden_rows),
            "expected": len(stream_rows),
            "pass": len(hidden_rows) == len(stream_rows),
        },
        {
            "check": "baseline_schema_compatibility_nonempty",
            "value": sum(1 for r in compatibility if r["compatible"]),
            "expected": ">= families * 6",
            "pass": sum(1 for r in compatibility if r["compatible"]) >= len(FAMILIES) * 6,
        },
    ]


def make_report(output_dir: Path, status: str, criteria: list[dict[str, Any]], decision: dict[str, Any]) -> str:
    passed = sum(1 for c in criteria if c["passed"])
    return "\n".join(
        [
            "# Tier 7.5b Curriculum / Environment Generator Implementation Preflight",
            "",
            f"- Generated: `{utc_now()}`",
            f"- Status: **{status}**",
            f"- Output directory: `{output_dir}`",
            f"- Runner revision: `{RUNNER_REVISION}`",
            "",
            "## Boundary",
            "",
            "This preflight materializes deterministic stream/split/schema artifacts only. It does not score CRA, compare performance, tune mechanisms, freeze a baseline, or authorize hardware/native transfer.",
            "",
            "## Summary",
            "",
            f"- criteria_passed: `{passed}/{len(criteria)}`",
            f"- outcome: `{decision['outcome']}`",
            f"- next_gate: `{decision['next_gate']}`",
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass | Details |",
            "| --- | --- | --- | --- | --- |",
            *[
                f"| {c['criterion']} | `{c['value']}` | {c['rule']} | {'yes' if c['passed'] else 'no'} | {c.get('details', '')} |"
                for c in criteria
            ],
            "",
        ]
    )


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
    prereq = read_json(PREREQ)
    stream_rows, hidden_rows, split_rows = generate_rows()
    compatibility = baseline_compatibility_rows()
    schemas = schema_rows()
    leakage = leakage_check_rows(stream_rows, hidden_rows, compatibility)
    family_count = len({r["family_id"] for r in stream_rows})
    split_count = len({r["split"] for r in stream_rows})
    hidden_rows_count = sum(1 for r in stream_rows if r["split"] in {"generated_holdout", "generator_ood_holdout"})
    stream_hash = sha256_text(json.dumps(stream_rows, sort_keys=True))
    manifest = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "families": FAMILIES,
        "splits": SPLITS,
        "features": FEATURES,
        "rows": len(stream_rows),
        "hidden_rows": hidden_rows_count,
        "stream_hash": stream_hash,
        "contract_source": str(PREREQ),
        "scoring_performed": False,
    }
    decision = {
        "tier": TIER,
        "status": "PASS",
        "outcome": "curriculum_generator_preflight_materialized_no_scoring",
        "next_gate": NEXT_GATE,
        "scoring_performed": False,
        "cra_scored": False,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "broad_public_usefulness_authorized": False,
    }
    criteria = [
        criterion("tier7_5a_prerequisite_exists", PREREQ.exists(), "must exist", PREREQ.exists(), str(PREREQ)),
        criterion("tier7_5a_prerequisite_passed", prereq.get("status"), "case-insensitive == PASS", str(prereq.get("status", "")).upper() == "PASS"),
        criterion("family_count", family_count, "== 6", family_count == 6),
        criterion("split_count", split_count, "== 4", split_count == 4),
        criterion("stream_rows_materialized", len(stream_rows), ">= 300", len(stream_rows) >= 300),
        criterion("hidden_rows_materialized", hidden_rows_count, ">= 100", hidden_rows_count >= 100),
        criterion("schema_fields_defined", len(schemas), ">= 12", len(schemas) >= 12),
        criterion("baseline_compatibility_rows", len(compatibility), "== families * baselines", len(compatibility) == len(FAMILIES) * len(BASELINES)),
        criterion("leakage_checks_defined", len(leakage), ">= 5", len(leakage) >= 5),
        criterion("leakage_checks_pass", sum(1 for r in leakage if r["pass"]), "all pass", all(r["pass"] for r in leakage)),
        criterion("stream_hash_present", stream_hash, "sha256 non-empty", len(stream_hash) == 64),
        criterion("scoring_not_performed", decision["scoring_performed"], "must be False", not decision["scoring_performed"]),
        criterion("cra_not_scored", decision["cra_scored"], "must be False", not decision["cra_scored"]),
        criterion("freeze_blocked", decision["freeze_authorized"], "must be False", not decision["freeze_authorized"]),
        criterion("hardware_transfer_blocked", decision["hardware_transfer_authorized"], "must be False", not decision["hardware_transfer_authorized"]),
        criterion("next_gate_selected", decision["next_gate"], "non-empty", bool(decision["next_gate"])),
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
        "manifest": manifest,
        "leakage_checks": leakage,
    }
    artifacts = {
        "results_json": output_dir / "tier7_5b_results.json",
        "summary_csv": output_dir / "tier7_5b_summary.csv",
        "report_md": output_dir / "tier7_5b_report.md",
        "generator_manifest_json": output_dir / "tier7_5b_generator_manifest.json",
        "split_manifest_csv": output_dir / "tier7_5b_split_manifest.csv",
        "task_family_streams_csv": output_dir / "tier7_5b_task_family_streams.csv",
        "hidden_label_hashes_csv": output_dir / "tier7_5b_hidden_label_hashes.csv",
        "schema_contract_csv": output_dir / "tier7_5b_schema_contract.csv",
        "baseline_compatibility_csv": output_dir / "tier7_5b_baseline_compatibility.csv",
        "leakage_checks_csv": output_dir / "tier7_5b_leakage_checks.csv",
        "decision_json": output_dir / "tier7_5b_decision.json",
        "decision_csv": output_dir / "tier7_5b_decision.csv",
    }
    write_json(artifacts["results_json"], results)
    write_csv(artifacts["summary_csv"], criteria, ["criterion", "value", "rule", "pass", "details"])
    write_json(artifacts["generator_manifest_json"], manifest)
    write_csv(artifacts["split_manifest_csv"], split_rows)
    write_csv(artifacts["task_family_streams_csv"], stream_rows)
    write_csv(artifacts["hidden_label_hashes_csv"], hidden_rows)
    write_csv(artifacts["schema_contract_csv"], schemas)
    write_csv(artifacts["baseline_compatibility_csv"], compatibility)
    write_csv(artifacts["leakage_checks_csv"], leakage)
    write_json(artifacts["decision_json"], decision)
    write_csv(artifacts["decision_csv"], [decision])
    artifacts["report_md"].write_text(make_report(output_dir, status, criteria, decision), encoding="utf-8")
    latest = make_manifest(output_dir, artifacts, status)
    artifacts["latest_manifest_json"] = output_dir / "tier7_5b_latest_manifest.json"
    write_json(artifacts["latest_manifest_json"], latest)
    print(json.dumps(json_safe({"status": status, "outcome": decision["outcome"], "output_dir": output_dir, "next_gate": NEXT_GATE}), indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
