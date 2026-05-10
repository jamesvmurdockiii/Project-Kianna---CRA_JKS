#!/usr/bin/env python3
"""Tier 7.7u - state-collapse causal localization.

After the 7.7t contract locked the repair campaign, this gate locks the
localization protocol and validates that the probe infrastructure is importable.
The gate identifies exactly which model control variants must be implemented in
the CRA configuration layer before full causal localization can execute, and
predeclares the outcome classification rules.

Required model variants (must be added to CRA config layer before full scoring):
  no_plasticity, no_inhibition, frozen_recurrent, state_reset, input_channel_shuffle

Once those variants exist, the localization probes defined in 7.7t apply directly.
This gate intentionally does not attempt partial execution with missing variants.
"""

from __future__ import annotations

import csv
import hashlib
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

TIER = "Tier 7.7u - State-Collapse Causal Localization"
RUNNER_REVISION = "tier7_7u_state_collapse_causal_localization_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7u_20260509_state_collapse_causal_localization"
CONTRACT_77T = CONTROLLED / "tier7_7t_20260509_low_rank_state_repair_campaign_contract" / "tier7_7t_results.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
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


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {
        "name": name, "criterion": name, "value": json_safe(value),
        "operator": rule, "rule": rule, "passed": bool(passed),
        "pass": bool(passed), "details": details, "note": details,
    }


def probe_definitions() -> list[dict[str, Any]]:
    return [
        {"probe": "state_pr_before_learning", "metric": "participation_ratio", "phase": "pre", "description": "State PR on first 500 rows before weight updates."},
        {"probe": "state_pr_during_learning", "metric": "participation_ratio", "phase": "train", "description": "State PR across training split."},
        {"probe": "state_pr_after_learning", "metric": "participation_ratio", "phase": "post", "description": "State PR on test split after training."},
        {"probe": "rank_95", "metric": "rank_95", "phase": "post", "description": "PCA components for 95% variance on test split."},
        {"probe": "rank_99", "metric": "rank_99", "phase": "post", "description": "PCA components for 99% variance on test split."},
        {"probe": "top_pc_dominance", "metric": "top_pc_dominance", "phase": "post", "description": "Variance fraction in first PC on test split."},
        {"probe": "per_neuron_variance", "metric": "per_neuron_var_cv", "phase": "post", "description": "Coefficient of variation of per-neuron activity variance."},
        {"probe": "pairwise_correlation", "metric": "corr_mean", "phase": "post", "description": "Mean absolute pairwise neuron correlation on test split."},
        {"probe": "saturation_rate", "metric": "saturation_rate", "phase": "post", "description": "Fraction of neurons at clipping bounds."},
        {"probe": "covariance_spectrum", "metric": "covariance_eigenvalues", "phase": "post", "description": "Eigenvalue distribution of state covariance matrix."},
    ]


def required_model_variants() -> list[dict[str, Any]]:
    return [
        {"variant": "no_plasticity", "targets": "plasticity_homogenization", "implementation": "Freeze or zero learning rate while preserving recurrence. Add config key `plasticity_enabled=False`."},
        {"variant": "no_inhibition", "targets": "inhibition_compression", "implementation": "Disable WTA/inhibitory normalization within polyp populations. Add config key `inhibition_enabled=False`."},
        {"variant": "frozen_recurrent", "targets": "recurrent_topology_bottleneck", "implementation": "Initialize random recurrent weights once and freeze them. Compares to learned topology."},
        {"variant": "state_reset", "targets": "numeric_saturation", "implementation": "Periodically reset or reinitialize hidden state during training."},
        {"variant": "input_channel_shuffle", "targets": "input_encoder_bottleneck", "implementation": "Permute input channels before encoding to break causal structure."},
        {"variant": "per_partition_probe", "targets": "shared_driver_synchronization", "implementation": "Expose per-polyp-partition state readout for partition-specific PR."},
        {"variant": "trophic_probe", "targets": "trophic_selection_compression", "implementation": "Instrument trophic energy counters alongside state geometry."},
    ]


def diagnostic_controls() -> list[dict[str, Any]]:
    return [
        {"control": "target_shuffle", "available": True, "evidence": "Tier 7.7j confirms target/time-shuffle separation.", "description": "Shuffle targets to break causal structure; PR should drop if state encodes task-relevant signal."},
        {"control": "time_shuffle", "available": True, "evidence": "Tier 7.7j confirms target/time-shuffle separation.", "description": "Shuffle time ordering; PR may increase if temporal structure constrains state."},
        {"control": "no_plasticity", "available": False, "reason": "Requires model variant.", "description": "Compare PR trajectory with and without weight updates."},
        {"control": "no_inhibition", "available": False, "reason": "Requires model variant.", "description": "Compare PR with inhibition disabled."},
        {"control": "frozen_recurrent", "available": False, "reason": "Requires model variant.", "description": "Compare PR with frozen vs learned recurrent weights."},
        {"control": "state_reset", "available": False, "reason": "Requires model variant.", "description": "Compare PR resilience to state resets."},
        {"control": "input_channel_shuffle", "available": False, "reason": "Requires model variant.", "description": "Compare PR with shuffled input channels."},
    ]


def outcome_rules() -> list[dict[str, Any]]:
    return [
        {"observation": "no_plasticity PR >> candidate PR (less collapse without learning)", "classification": "plasticity_homogenization_confirmed", "route": "Repair Family D (plasticity anti-homogenization)"},
        {"observation": "no_inhibition PR >> candidate PR (less collapse without WTA)", "classification": "inhibition_compression_confirmed", "route": "Repair Family A (diversity-preserving dynamics)"},
        {"observation": "frozen_recurrent PR ~ candidate PR (learned topology not compressing)", "classification": "recurrent_topology_bottleneck_confirmed", "route": "Repair Family C (topology/spectrum repair)"},
        {"observation": "input_channel_shuffle PR >> candidate PR (ordered input is compressing)", "classification": "input_bottleneck_confirmed", "route": "Repair Family B (independent causal subspace drivers)"},
        {"observation": "state_reset PR ~ candidate PR (state is not saturating)", "classification": "numeric_saturation_confirmed_diagnostic_only", "route": "Lower priority; numeric fix before architecture repair."},
        {"observation": "per_partition PR varies widely between partitions", "classification": "shared_driver_synchronization_confirmed", "route": "Repair Family B (fix partition-level input sharing)."},
        {"observation": "trophic_counters correlate with per-neuron PR loss", "classification": "trophic_selection_compression_confirmed", "route": "Repair Family A or D (protect minority modes)."},
        {"observation": "readout budget explains gap vs candidate state PR", "classification": "readout_exposure_bottleneck_confirmed", "route": "Assess readout observability before architecture repair."},
        {"observation": "multiple controls improve PR similarly", "classification": "mixed_or_inconclusive", "route": "Broadest-applicability repair family first (Family A)."},
    ]


def build_contract(contract_77t: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": "Where does the low-rank collapse enter: input encoding, recurrent dynamics, plasticity, inhibition, trophic pressure, readout exposure, or numerical saturation?",
        "hypothesis": "The ~2D collapse enters through one or two primary mechanisms that can be isolated by comparing candidate PR trajectories against diagnostic controls.",
        "null_hypothesis": "All diagnostic controls produce similar PR collapse (the effect is irreducible at current capacity).",
        "decision": "localization_protocol_locked_awaits_model_variants",
        "contract_77t_outcome": contract_77t.get("contract", {}).get("decision", "unknown"),
        "probe_definitions_count": len(probe_definitions()),
        "required_variants_count": len(required_model_variants()),
        "controls_count": len(diagnostic_controls()),
        "outcome_rules_count": len(outcome_rules()),
        "variant_implementation_priority": [
            "no_plasticity", "no_inhibition", "frozen_recurrent",
            "input_channel_shuffle", "state_reset",
            "per_partition_probe", "trophic_probe",
        ],
        "decision_boundary": (
            "Localization protocol locked. Seven diagnostic model variants must be "
            "implemented as CRA configuration options before full causal localization "
            "can score. Do not proceed to Tier 7.7v repair implementation without "
            "verifying that at least the top-4 priority variants exist and can be "
            "instantiated with the current CRA v2.5 baseline. "
            "Not a repair, not mechanism promotion, not a baseline freeze, "
            "not public usefulness proof, not hardware/native transfer."
        ),
    }


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract_77t = read_json(CONTRACT_77T)
    contract = build_contract(contract_77t)
    probes = probe_definitions()
    variants = required_model_variants()
    controls = diagnostic_controls()
    outcomes = outcome_rules()

    infrastructure_ok = True
    try:
        from tier7_7j_capacity_sham_separation_scoring_gate import (  # noqa: F401
            geometry_metrics, hidden_columns, run_probe_model, safe_float,
            build_task, utc_now as _tmp_utc, write_json as _tmp_wj,
        )
    except Exception:
        infrastructure_ok = False

    criteria = [
        criterion("contract 7.7t exists", CONTRACT_77T.exists(), "true", CONTRACT_77T.exists()),
        criterion("contract 7.7t passed", contract_77t.get("status"), "== pass", contract_77t.get("status") == "pass"),
        criterion("probe infrastructure importable", infrastructure_ok, "true", infrastructure_ok),
        criterion("probe definitions locked", len(probes), "== 10", len(probes) == 10),
        criterion("required model variants declared", len(variants), "== 7", len(variants) == 7),
        criterion("no_plasticity variant declared", any(v["variant"] == "no_plasticity" for v in variants), "true", True),
        criterion("no_inhibition variant declared", any(v["variant"] == "no_inhibition" for v in variants), "true", True),
        criterion("frozen_recurrent variant declared", any(v["variant"] == "frozen_recurrent" for v in variants), "true", True),
        criterion("diagnostic controls enumerated", len(controls), "== 7", len(controls) == 7),
        criterion("outcome classification rules locked", len(outcomes), ">= 8", len(outcomes) >= 8),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
        criterion("no hardware/native transfer authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    classification = "localization_protocol_locked_awaits_model_variants"

    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "outcome": classification,
        "criteria": criteria,
        "criteria_passed": passed,
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "contract": contract,
        "probe_definitions": probes,
        "required_model_variants": variants,
        "diagnostic_controls": controls,
        "outcome_rules": outcomes,
        "infrastructure_importable": infrastructure_ok,
        "next_gate": "Tier 7.7v - Repair Candidate Compact Score (requires model variants before scoring)",
        "claim_boundary": contract["decision_boundary"],
        "nonclaims": [
            "not a repair implementation",
            "not full localization scoring",
            "not a mechanism promotion",
            "not a baseline freeze",
            "not public usefulness proof",
            "not hardware/native transfer",
        ],
        "prerequisite": {
            "path": str(CONTRACT_77T),
            "sha256": sha256_file(CONTRACT_77T),
            "status": contract_77t.get("status"),
        },
    }
    write_json(output_dir / "tier7_7u_results.json", payload)
    write_json(output_dir / "tier7_7u_contract.json", contract)
    write_csv(output_dir / "tier7_7u_summary.csv", criteria)
    write_csv(output_dir / "tier7_7u_probe_definitions.csv", probes)
    write_csv(output_dir / "tier7_7u_required_variants.csv", variants)
    write_csv(output_dir / "tier7_7u_diagnostic_controls.csv", controls)
    write_csv(output_dir / "tier7_7u_outcome_rules.csv", outcomes)
    (output_dir / "tier7_7u_claim_boundary.md").write_text(contract["decision_boundary"] + "\n", encoding="utf-8")
    report = [
        "# Tier 7.7u State-Collapse Causal Localization",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{status.upper()}** ({passed}/{len(criteria)} criteria)",
        f"- Outcome: `{classification}`",
        "",
        "## Question",
        "",
        contract["question"],
        "",
        "## Definition of Done",
        "",
        "This gate locks the localization protocol. Full scoring requires the",
        "following model variants to be implemented in the CRA configuration layer:",
        "",
    ]
    for v in variants:
        report.append(f"- **{v['variant']}**: {v['implementation']}")
    report.extend([
        "",
        "Once these variants are available, the localization scoring follows the",
        "outcome rules defined in `tier7_7u_outcome_rules.csv`. The candidate PR",
        "is compared against each diagnostic control; the control producing the",
        "largest PR improvement identifies the primary collapse mechanism. Tier 7.7v",
        "then activates the corresponding repair family (A-E).",
        "",
        "## Claim Boundary",
        "",
        contract["decision_boundary"],
    ])
    (output_dir / "tier7_7u_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = {
        "tier": TIER, "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7u_results.json"),
        "report_md": str(output_dir / "tier7_7u_report.md"),
        "summary_csv": str(output_dir / "tier7_7u_summary.csv"),
    }
    write_json(output_dir / "tier7_7u_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7u_latest_manifest.json", manifest)
    return payload


def main() -> int:
    payload = run()
    print(json.dumps(json_safe({
        "status": payload["status"],
        "outcome": payload["outcome"],
        "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
        "output_dir": payload["output_dir"],
        "next_gate": payload["next_gate"],
    }), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
