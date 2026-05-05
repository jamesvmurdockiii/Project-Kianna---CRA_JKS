#!/usr/bin/env python3
"""Tier 4.30-readiness audit: lifecycle-native preflight / layering decision.

This is an engineering contract gate, not a hardware run. It deliberately sits
between the v2.2 software freeze and Tier 4.30 lifecycle-native implementation
so the repo does not accidentally mix three different claims:

1. v2.2 host-side fading-memory temporal state.
2. v2.1-era native mechanism bridge evidence through Tier 4.29f.
3. future native lifecycle/self-scaling with static pools, masks, and lineage.

The audit passes only when the layering decision, required static-pool contract,
controls, readback fields, and artifact expectations are explicit.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
RUNTIME_SRC = RUNTIME / "src"

TIER = "Tier 4.30-readiness - Lifecycle-Native Preflight / Layering Audit"
RUNNER_REVISION = "tier4_30_readiness_audit_20260505_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_30_readiness_20260505_lifecycle_native_audit"


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


@dataclass(frozen=True)
class ContractField:
    field: str
    type: str
    owner: str
    required_for: str
    initial_value: str
    readback: bool


@dataclass(frozen=True)
class ControlSpec:
    name: str
    purpose: str
    expected_effect: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_define_int(header_text: str, name: str) -> int | None:
    match = re.search(rf"^\s*#define\s+{re.escape(name)}\s+([0-9]+)\b", header_text, re.MULTILINE)
    return int(match.group(1)) if match else None


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def lifecycle_fields() -> list[ContractField]:
    return [
        ContractField("slot_id", "uint16", "lifecycle_core", "stable static-pool index", "0..pool_size-1", True),
        ContractField("active_mask", "uint8", "lifecycle_core", "activate/silence preallocated units", "founder slots active only", True),
        ContractField("polyp_id", "uint32", "lifecycle_core", "auditable identity", "stable deterministic id", True),
        ContractField("lineage_id", "uint32", "lifecycle_core", "lineage accounting", "founder lineage id", True),
        ContractField("parent_slot", "int16", "lifecycle_core", "birth/cleavage provenance", "-1 for founders", True),
        ContractField("generation", "uint16", "lifecycle_core", "cleavage/birth depth", "0", True),
        ContractField("age_steps", "uint32", "lifecycle_core", "maturity / juvenile gates", "0", True),
        ContractField("trophic_health", "s16.15", "lifecycle_core", "survival/reproduction gates", "initial trophic seed", True),
        ContractField("cyclin_d", "s16.15", "lifecycle_core", "reproduction gate", "0", True),
        ContractField("bax", "s16.15", "lifecycle_core", "death gate", "0", True),
        ContractField("last_event_type", "uint8", "lifecycle_core", "event audit", "none", True),
        ContractField("event_count", "uint32", "lifecycle_core", "lifecycle telemetry", "0", True),
    ]


def lifecycle_controls() -> list[ControlSpec]:
    return [
        ControlSpec(
            "fixed_static_pool_control",
            "Shows any benefit is not just the preallocated max capacity.",
            "Lifecycle-enabled path must beat or differ from fixed active mask only on lifecycle-pressure tasks.",
        ),
        ControlSpec(
            "random_event_replay_control",
            "Matches event count while destroying event causality.",
            "Random matched events should not reproduce lineage/trophic/task benefit.",
        ),
        ControlSpec(
            "active_mask_shuffle_control",
            "Destroys identity-to-slot binding while preserving active count.",
            "Mask shuffle should break lineage-specific or specialist reuse claims.",
        ),
        ControlSpec(
            "lineage_id_shuffle_control",
            "Checks whether lineage bookkeeping is causal or decorative.",
            "Lineage shuffle should damage lineage-dependent claims without changing raw capacity.",
        ),
        ControlSpec(
            "no_trophic_pressure_control",
            "Removes ecology pressure while leaving state machinery alive.",
            "No-trophic path should lose lifecycle selection-specific effects.",
        ),
        ControlSpec(
            "no_dopamine_or_plasticity_control",
            "Separates lifecycle bookkeeping from actual learning/reward coupling.",
            "No learning/plasticity should not pass task-effect gates.",
        ),
    ]


def load_prerequisites() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    v22 = load_json(ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v2.2.json")
    native_bridge = load_json(ROOT / "baselines" / "CRA_NATIVE_MECHANISM_BRIDGE_v0.3.json")
    tier429f = load_json(CONTROLLED / "tier4_29f_20260505_native_mechanism_regression" / "tier4_29f_results.json")
    return v22, native_bridge, tier429f


def build_audit() -> dict[str, Any]:
    v22, native_bridge, tier429f = load_prerequisites()
    config_h = read_text(RUNTIME_SRC / "config.h")
    state_h = read_text(RUNTIME_SRC / "state_manager.h")
    neuron_c = read_text(RUNTIME_SRC / "neuron_manager.c")
    neuron_h = read_text(RUNTIME_SRC / "neuron_manager.h")
    host_c = read_text(RUNTIME_SRC / "host_interface.c")
    v22_claim_boundary_text = json.dumps(v22.get("claim_boundaries", []), sort_keys=True).lower()

    constants = {
        name: parse_define_int(config_h, name)
        for name in (
            "MAX_NEURONS",
            "MAX_CONTEXT_SLOTS",
            "MAX_ROUTE_SLOTS",
            "MAX_MEMORY_SLOTS",
            "MAX_PENDING_HORIZONS",
            "MAX_SCHEDULE_ENTRIES",
        )
    }
    has_dynamic_neuron_alloc = "sark_alloc" in neuron_c and "sark_free" in neuron_c
    has_legacy_birth_death_cmds = "CMD_BIRTH" in config_h and "CMD_DEATH" in config_h
    has_lifecycle_static_fields = any(
        token in state_h
        for token in ("lineage_id", "trophic_health", "active_mask", "cyclin_d", "bax")
    )
    has_read_state = "CMD_READ_STATE" in host_c and "host_if_pack_state_summary" in host_c
    has_mcpl = "MAKE_MCPL_KEY" in config_h and "cra_state_mcpl_lookup" in state_h

    layering_decision = {
        "decision": "layer_initial_lifecycle_native_work_on_native_mechanism_bridge_v0_3_with_v2_2_as_software_reference_only",
        "why": (
            "Lifecycle/self-scaling is an organism/ecology mechanism. The existing native "
            "bridge already owns context, route, memory, prediction, confidence, replay, "
            "pending maturation, and MCPL-distributed lookup primitives. v2.2 adds useful "
            "host-side fading-memory temporal state, but it is not yet native/on-chip and "
            "should not be smuggled into the first lifecycle hardware gate."
        ),
        "initially_in_scope": [
            "static preallocated lifecycle pool",
            "active/inactive masks",
            "lineage IDs and parent links",
            "trophic-health counters",
            "birth/cleavage/death event telemetry",
            "fixed-pool and sham controls",
            "compact readback and local fixed-point parity",
        ],
        "explicitly_out_of_scope": [
            "dynamic PyNN population creation mid-run",
            "legacy SDRAM malloc/free neuron_birth/neuron_death as the lifecycle proof",
            "native v2.2 temporal fading-memory state",
            "native nonlinear recurrence",
            "multi-chip scaling",
            "speedup claims",
            "paper-level lifecycle superiority",
        ],
    }

    static_pool_contract = {
        "initial_pool_slots": 8,
        "initial_active_slots": 2,
        "capacity_rule": "fixed compile-time pool; events toggle/assign slots rather than allocate/free graph objects",
        "event_semantics": {
            "cleavage": "activate one inactive slot from a parent lineage with deterministic parent/child split",
            "birth": "activate one inactive slot after adult gates pass; parent remains active",
            "death": "clear active_mask and preserve final lineage/event telemetry",
            "handoff": "record maturity transition; no dynamic graph creation",
        },
        "runtime_owner": "new lifecycle state path or lifecycle profile layered beside existing state/context/route/memory/learning cores",
        "first_local_task": "short static-pool lifecycle event stream with fixed reference and no hardware allocation",
        "first_hardware_task": "single-board seed-42 lifecycle mask smoke only after local parity and source audit",
    }

    fields = lifecycle_fields()
    controls = lifecycle_controls()
    required_artifacts = [
        "tier4_30_contract_or_readiness_results.json",
        "tier4_30_contract_or_readiness_report.md",
        "tier4_30_lifecycle_fields.csv",
        "tier4_30_lifecycle_controls.csv",
        "local fixed-point reference JSON for Tier 4.30a",
        "prepared EBRAINS source-only package only after local pass",
        "ingested hardware report only after returned real hardware artifacts",
    ]

    criteria = [
        criterion("v2.2 baseline exists and is frozen", v22.get("baseline_id"), "== v2.2 and status frozen", v22.get("baseline_id") == "v2.2" and v22.get("status") == "frozen"),
        criterion("v2.2 registry stayed green", v22.get("registry_status"), "== pass", v22.get("registry_status") == "pass"),
        criterion("v2.2 boundary excludes hardware/on-chip temporal claim", v22.get("claim_boundaries", []), "mentions no hardware/on-chip temporal dynamics", "hardware" in v22_claim_boundary_text and "on-chip" in v22_claim_boundary_text),
        criterion("native mechanism bridge v0.3 exists", native_bridge.get("baseline_id"), "== CRA_NATIVE_MECHANISM_BRIDGE_v0.3", native_bridge.get("baseline_id") == "CRA_NATIVE_MECHANISM_BRIDGE_v0.3"),
        criterion("native bridge registry stayed green", native_bridge.get("registry_status"), "== pass", native_bridge.get("registry_status") == "pass"),
        criterion("Tier 4.29f evidence regression passed", f"{tier429f.get('criteria_passed')}/{tier429f.get('criteria_total')}", "== 113/113 and status pass", tier429f.get("status") == "pass" and tier429f.get("criteria_passed") == tier429f.get("criteria_total") == 113),
        criterion("runtime source tree exists", str(RUNTIME_SRC), "config/state/host/neuron source files present", all((RUNTIME_SRC / name).exists() for name in ("config.h", "state_manager.h", "host_interface.c", "neuron_manager.c"))),
        criterion("static state capacity exists", constants, "context>=16 route>=4 memory>=4 pending>=32 schedule>=128", (constants["MAX_CONTEXT_SLOTS"] or 0) >= 16 and (constants["MAX_ROUTE_SLOTS"] or 0) >= 4 and (constants["MAX_MEMORY_SLOTS"] or 0) >= 4 and (constants["MAX_PENDING_HORIZONS"] or 0) >= 32 and (constants["MAX_SCHEDULE_ENTRIES"] or 0) >= 128),
        criterion("MCPL data plane available for native scaling path", has_mcpl, "== true", has_mcpl),
        criterion("compact readback path available", has_read_state, "== true", has_read_state),
        criterion("legacy dynamic birth/death identified", has_dynamic_neuron_alloc and has_legacy_birth_death_cmds, "== true and excluded from initial lifecycle-native proof", has_dynamic_neuron_alloc and has_legacy_birth_death_cmds, "Existing neuron_birth/death uses SDRAM allocation/free and must not be treated as the static-pool lifecycle proof."),
        criterion("lifecycle static-pool fields are not already implemented", has_lifecycle_static_fields, "== false; blocker explicitly declared", not has_lifecycle_static_fields, "This is expected at readiness stage; Tier 4.30 must add a bounded lifecycle state surface before hardware."),
        criterion("layering decision explicit", layering_decision["decision"], "non-empty with out-of-scope list", bool(layering_decision["decision"]) and len(layering_decision["explicitly_out_of_scope"]) >= 6),
        criterion("static-pool contract fields declared", len(fields), ">= 10 readback fields", len(fields) >= 10 and all(field.readback for field in fields)),
        criterion("lifecycle sham controls declared", len(controls), ">= 6 controls", len(controls) >= 6),
        criterion("artifact expectations declared", len(required_artifacts), ">= 6 artifacts", len(required_artifacts) >= 6),
    ]
    failed = [item for item in criteria if not item.passed]

    return {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if not failed else "fail",
        "mode": "local-readiness-audit",
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "criteria": criteria,
        "failed_criteria": failed,
        "source_inputs": {
            "v2_2_baseline": "baselines/CRA_EVIDENCE_BASELINE_v2.2.json",
            "native_bridge_baseline": "baselines/CRA_NATIVE_MECHANISM_BRIDGE_v0.3.json",
            "tier4_29f_results": "controlled_test_output/tier4_29f_20260505_native_mechanism_regression/tier4_29f_results.json",
            "runtime_config": "coral_reef_spinnaker/spinnaker_runtime/src/config.h",
            "runtime_state": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h",
        },
        "layering_decision": layering_decision,
        "static_pool_contract": static_pool_contract,
        "lifecycle_fields": fields,
        "lifecycle_controls": controls,
        "runtime_observations": {
            "constants": constants,
            "legacy_dynamic_neuron_birth_death": has_dynamic_neuron_alloc and has_legacy_birth_death_cmds,
            "lifecycle_static_fields_present": has_lifecycle_static_fields,
            "mcpl_lookup_surface_present": has_mcpl,
            "compact_read_state_present": has_read_state,
            "neuron_manager_boundary": (
                "neuron_birth/neuron_death are useful legacy primitives but use SDRAM "
                "allocation/free. Tier 4.30 lifecycle-native proof must use a static "
                "pool/mask/lineage surface instead of dynamic allocation."
            ),
        },
        "required_artifacts": required_artifacts,
        "recommended_sequence": [
            "Tier 4.30 contract: formalize static-pool lifecycle surface and command/readback schema.",
            "Tier 4.30a local reference: deterministic static-pool event stream and fixed-point parity.",
            "Tier 4.30b single-core hardware smoke: active-mask and lineage telemetry only.",
            "Tier 4.30c multi-core lifecycle state split if 4.30b passes.",
            "Tier 4.30d lifecycle sham-control hardware subset before any lifecycle-native baseline freeze.",
            "Separate native temporal-readiness tier only if v2.2 fading-memory state is selected for hardware migration.",
        ],
        "claim_boundary": (
            "Tier 4.30-readiness is a local engineering audit. It does not implement "
            "lifecycle hardware, does not run EBRAINS/SpiNNaker, does not prove native "
            "lifecycle, does not migrate v2.2 temporal state, and does not freeze a "
            "new lifecycle or native baseline."
        ),
    }


def write_report(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.30-Readiness Lifecycle-Native Audit",
        "",
        f"- Generated: `{results['generated_at_utc']}`",
        f"- Runner revision: `{results['runner_revision']}`",
        f"- Status: **{results['status'].upper()}**",
        f"- Criteria: `{results['criteria_passed']}/{results['criteria_total']}`",
        "",
        "## Claim Boundary",
        "",
        results["claim_boundary"],
        "",
        "## Layering Decision",
        "",
        f"- Decision: `{results['layering_decision']['decision']}`",
        f"- Rationale: {results['layering_decision']['why']}",
        "",
        "In scope for the first lifecycle-native path:",
        "",
        *[f"- {item}" for item in results["layering_decision"]["initially_in_scope"]],
        "",
        "Out of scope for the first lifecycle-native path:",
        "",
        *[f"- {item}" for item in results["layering_decision"]["explicitly_out_of_scope"]],
        "",
        "## Static-Pool Contract",
        "",
        f"- Initial pool slots: `{results['static_pool_contract']['initial_pool_slots']}`",
        f"- Initial active slots: `{results['static_pool_contract']['initial_active_slots']}`",
        f"- Capacity rule: {results['static_pool_contract']['capacity_rule']}",
        f"- Runtime owner: {results['static_pool_contract']['runtime_owner']}",
        "",
        "## Lifecycle Fields",
        "",
        "| Field | Type | Owner | Required For | Initial Value | Readback |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for field in results["lifecycle_fields"]:
        lines.append(
            f"| `{field['field']}` | `{field['type']}` | `{field['owner']}` | {field['required_for']} | `{field['initial_value']}` | {'yes' if field['readback'] else 'no'} |"
        )
    lines.extend(["", "## Controls", "", "| Control | Purpose | Expected Effect |", "| --- | --- | --- |"])
    for control in results["lifecycle_controls"]:
        lines.append(f"| `{control['name']}` | {control['purpose']} | {control['expected_effect']} |")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in results["criteria"]:
        lines.append(
            f"| {item['name']} | `{item['value']}` | `{item['rule']}` | {'yes' if item['passed'] else 'no'} | {item.get('note', '')} |"
        )
    lines.extend(["", "## Recommended Sequence", ""])
    for index, step in enumerate(results["recommended_sequence"], start=1):
        lines.append(f"{index}. {step}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    results = build_audit()
    results["output_dir"] = str(output_dir)

    write_json(output_dir / "tier4_30_readiness_results.json", results)
    write_report(output_dir / "tier4_30_readiness_report.md", json_safe(results))
    write_csv(output_dir / "tier4_30_lifecycle_fields.csv", [asdict(field) for field in lifecycle_fields()])
    write_csv(output_dir / "tier4_30_lifecycle_controls.csv", [asdict(control) for control in lifecycle_controls()])
    write_json(
        CONTROLLED / "tier4_30_readiness_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": results["generated_at_utc"],
            "status": results["status"],
            "manifest": str(output_dir / "tier4_30_readiness_results.json"),
            "output_dir": str(output_dir),
        },
    )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    results = run(args)
    print(
        json.dumps(
            {
                "tier": TIER,
                "status": results["status"],
                "criteria": f"{results['criteria_passed']}/{results['criteria_total']}",
                "output_dir": results["output_dir"],
                "next": results["recommended_sequence"][0],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if results["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
