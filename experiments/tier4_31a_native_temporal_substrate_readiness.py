#!/usr/bin/env python3
"""Tier 4.31a - Native Temporal-Substrate Readiness.

This is a local contract/readiness gate. It does not edit the C runtime, build
an EBRAINS package, or claim hardware evidence. The purpose is to decide the
smallest defensible chip-owned subset of the v2.2 fading-memory temporal state
before implementation work starts.

Tier 5.19c promoted bounded multi-timescale fading memory, not nonlinear
recurrence. Therefore this gate deliberately scopes the first native migration
to fixed-point EMA traces and derived deltas/novelty only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME_SRC = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime" / "src"

TIER = "Tier 4.31a - Native Temporal-Substrate Readiness"
RUNNER_REVISION = "tier4_31a_native_temporal_substrate_readiness_20260506_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_31a_20260506_native_temporal_substrate_readiness"

V22_BASELINE = ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v2.2.json"
TIER519C_RESULTS = CONTROLLED / "tier5_19c_20260505_fading_memory_regression" / "tier5_19c_results.json"
LIFECYCLE_NATIVE_BASELINE = ROOT / "baselines" / "CRA_LIFECYCLE_NATIVE_BASELINE_v0.4.md"
TIER430G_HW_RESULTS = CONTROLLED / "tier4_30g_hw_20260505_hardware_pass_ingested" / "tier4_30g_hw_results.json"


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


@dataclass(frozen=True)
class TemporalStateSpec:
    field: str
    type: str
    owner: str
    update_rule: str
    storage: str
    readback: bool
    rationale: str


@dataclass(frozen=True)
class TemporalEquationSpec:
    name: str
    equation_float: str
    equation_fixed_point: str
    clipping_rule: str
    purpose: str


@dataclass(frozen=True)
class ReadbackSpec:
    field: str
    type: str
    cadence: str
    purpose: str
    pass_rule: str


@dataclass(frozen=True)
class ControlSpec:
    name: str
    mode: str
    purpose: str
    expected_effect: str
    required_before_hardware: bool


@dataclass(frozen=True)
class ResourceBudget:
    item: str
    count: int
    bytes_each: int
    total_bytes: int
    location: str
    note: str


@dataclass(frozen=True)
class FailureClass:
    failure_class: str
    meaning: str
    required_response: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def parse_define_int(header_text: str, name: str) -> int | None:
    match = re.search(rf"^\s*#define\s+{re.escape(name)}\s+([0-9]+)\b", header_text, re.MULTILINE)
    return int(match.group(1)) if match else None


def parse_command_codes(header_text: str) -> dict[str, int]:
    codes: dict[str, int] = {}
    for match in re.finditer(r"^\s*#define\s+(CMD_[A-Z0-9_]+)\s+([0-9]+)\b", header_text, re.MULTILINE):
        codes[match.group(1)] = int(match.group(2))
    return codes


def fp_from_float(value: float) -> int:
    return int(value * (1 << 15))


def temporal_timescales() -> list[int]:
    # This is the promoted Tier 5.19c fading-memory trace bank.
    return [2, 4, 8, 16, 32, 64, 128]


def temporal_state_specs() -> list[TemporalStateSpec]:
    return [
        TemporalStateSpec(
            "temporal_schema_version",
            "uint16",
            "learning_core",
            "set once at init",
            "core-local static state",
            True,
            "Version the readback parser and prevent stale report interpretation.",
        ),
        TemporalStateSpec(
            "temporal_trace_raw[7]",
            "int32 s16.15",
            "learning_core",
            "trace_i[t] = decay_i * trace_i[t-1] + alpha_i * input[t]",
            "core-local static state",
            True,
            "Smallest promoted v2.2 subset: bounded EMA traces only, no hidden recurrent state.",
        ),
        TemporalStateSpec(
            "temporal_alpha_raw[7]",
            "int32 s16.15",
            "compile-time or init payload",
            "alpha_i = 1 - exp(-1 / tau_i)",
            "constant table",
            True,
            "Make local 4.31b and C fixed-point equations auditable.",
        ),
        TemporalStateSpec(
            "temporal_decay_raw[7]",
            "int32 s16.15",
            "compile-time or init payload",
            "decay_i = exp(-1 / tau_i)",
            "constant table",
            True,
            "Avoid float-only decay behavior in the native claim path.",
        ),
        TemporalStateSpec(
            "latest_temporal_input_raw",
            "int32 s16.15",
            "learning_core",
            "last causal input used to update traces",
            "core-local summary field",
            True,
            "Proves the trace update used current/past input only.",
        ),
        TemporalStateSpec(
            "latest_temporal_novelty_raw",
            "int32 s16.15",
            "learning_core",
            "input[t] - trace_slowest[t-1]",
            "derived summary field",
            True,
            "Carries the v2.2 novelty feature without storing an extra unbounded history.",
        ),
        TemporalStateSpec(
            "temporal_update_count",
            "uint32",
            "learning_core",
            "increment once per temporal update",
            "core-local summary field",
            True,
            "Detects missed, duplicate, or host-side hidden updates.",
        ),
        TemporalStateSpec(
            "temporal_saturation_count",
            "uint32",
            "learning_core",
            "increment when any trace clips",
            "core-local summary field",
            True,
            "Bounds fixed-point overflow/saturation risk.",
        ),
        TemporalStateSpec(
            "temporal_reset_count",
            "uint32",
            "learning_core",
            "increment on explicit reset/sham mode reset",
            "core-local summary field",
            True,
            "Audits reset-control and stop/start behavior.",
        ),
        TemporalStateSpec(
            "temporal_sham_mode",
            "uint8",
            "learning_core",
            "selected by local reference or host command in future hardware probes",
            "core-local summary field",
            True,
            "Prevents post-hoc relabeling of control runs.",
        ),
    ]


def temporal_equations() -> list[TemporalEquationSpec]:
    return [
        TemporalEquationSpec(
            "ema_trace_update",
            "trace_i[t] = decay_i * trace_i[t-1] + alpha_i * x[t]",
            "trace_i = FP_MUL(decay_i_raw, trace_i) + FP_MUL(alpha_i_raw, input_raw)",
            "clip each trace to [-FP_ONE, FP_ONE] for first native gate",
            "Own the v2.2 fading-memory state on chip using only bounded causal updates.",
        ),
        TemporalEquationSpec(
            "trace_delta_feature",
            "delta_i[t] = trace_{i+1}[t] - trace_i[t]",
            "delta_i_raw = trace_raw[i + 1] - trace_raw[i]",
            "clip only if emitted into a bounded summary/readout payload",
            "Preserve v2.2 multi-timescale contrast as a derived feature, not persistent state.",
        ),
        TemporalEquationSpec(
            "novelty_feature",
            "novelty[t] = x[t] - trace_slowest[t-1]",
            "novelty_raw = input_raw - previous_slowest_trace_raw",
            "clip emitted novelty to [-2 * FP_ONE, 2 * FP_ONE]",
            "Expose causal surprise/novelty without future target leakage.",
        ),
        TemporalEquationSpec(
            "temporal_readout_input",
            "feature[t] = f(x[t], traces[t], deltas[t], novelty[t])",
            "readout consumes fixed-point current, trace, delta, and novelty fields only",
            "no hidden/tanh recurrent state in Tier 4.31b/4.31c",
            "Keep the first native migration aligned with the narrowed v2.2 claim.",
        ),
    ]


def readback_schema() -> list[ReadbackSpec]:
    return [
        ReadbackSpec("schema_version", "uint16", "every compact state read", "parser compatibility", "equals TEMPORAL_SCHEMA_VERSION"),
        ReadbackSpec("trace_count", "uint8", "every compact state read", "state shape accounting", "equals 7 for first native gate"),
        ReadbackSpec("timescale_checksum", "uint32", "setup and final read", "detect wrong tau/alpha table", "matches local reference checksum"),
        ReadbackSpec("trace_checksum", "int32", "every compact state read", "compact trace-state parity", "within fixed-point tolerance in 4.31b"),
        ReadbackSpec("trace_abs_sum_raw", "uint32", "every compact state read", "collapse/saturation signal", "finite and below declared bound"),
        ReadbackSpec("latest_input_raw", "int32", "every compact state read", "causal update audit", "equals last scheduled input in local reference"),
        ReadbackSpec("latest_novelty_raw", "int32", "every compact state read", "derived temporal feature audit", "matches local fixed-point mirror"),
        ReadbackSpec("temporal_update_count", "uint32", "every compact state read", "missed/duplicate update audit", "equals processed event count"),
        ReadbackSpec("temporal_saturation_count", "uint32", "every compact state read", "overflow audit", "zero in canonical pass"),
        ReadbackSpec("temporal_reset_count", "uint32", "every compact state read", "reset/sham audit", "matches declared control mode"),
        ReadbackSpec("temporal_sham_mode", "uint8", "every compact state read", "control identity", "matches requested mode"),
        ReadbackSpec("payload_len", "uint16", "every hardware read later", "readback accounting", "equals documented compact schema length"),
    ]


def controls() -> list[ControlSpec]:
    return [
        ControlSpec(
            "lag_only_online_lms_control",
            "local reference",
            "Preserve the Tier 5.19c requirement that fading memory beat a same-causal-budget lag control on temporal-memory diagnostics.",
            "Lag-only should remain weaker on temporal-memory tasks or the temporal native migration should not be promoted.",
            True,
        ),
        ControlSpec(
            "zero_temporal_state_ablation",
            "local reference and future hardware",
            "Proves task performance is not carried solely by current input/readout.",
            "Zeroed traces should lose temporal-memory benefit.",
            True,
        ),
        ControlSpec(
            "frozen_temporal_state_ablation",
            "local reference",
            "Matches the v2.2 sham where temporal state stops updating after the train/reference prefix.",
            "Frozen state should not match the active temporal trace on held-out temporal tasks.",
            True,
        ),
        ControlSpec(
            "shuffled_temporal_state_sham",
            "local reference",
            "Destroys temporal ordering while preserving marginal state distribution.",
            "Shuffled state should lose temporal-memory benefit.",
            True,
        ),
        ControlSpec(
            "state_reset_interval_control",
            "local reference and future hardware",
            "Checks whether the claimed memory horizon survives forced resets.",
            "Short reset interval should reduce long-memory performance.",
            True,
        ),
        ControlSpec(
            "shuffled_target_control",
            "local reference",
            "Detects label/target leakage through the temporal path.",
            "Shuffled targets must fail.",
            True,
        ),
        ControlSpec(
            "no_plasticity_ablation",
            "local reference and future hardware",
            "Separates temporal state availability from learning/readout adaptation.",
            "No-plasticity path must not pass promoted learning claims.",
            True,
        ),
        ControlSpec(
            "hidden_recurrence_excluded_control",
            "source audit",
            "Keeps Tier 4.31 aligned with the narrowed v2.2 claim.",
            "First native gate must not include hidden tanh recurrent units or recurrent weight matrices.",
            True,
        ),
    ]


def resource_budget() -> list[ResourceBudget]:
    trace_count = len(temporal_timescales())
    rows = [
        ResourceBudget("temporal_trace_raw", trace_count, 4, trace_count * 4, "DTCM/core-local", "Seven s16.15 EMA traces."),
        ResourceBudget("temporal_alpha_raw", trace_count, 4, trace_count * 4, "compile-time const or init table", "Can be compile-time constants after 4.31b."),
        ResourceBudget("temporal_decay_raw", trace_count, 4, trace_count * 4, "compile-time const or init table", "Can be compile-time constants after 4.31b."),
        ResourceBudget("latest_input_raw", 1, 4, 4, "summary", "Compact causal audit."),
        ResourceBudget("latest_novelty_raw", 1, 4, 4, "summary", "Compact derived-feature audit."),
        ResourceBudget("temporal_update_count", 1, 4, 4, "summary", "Telemetry counter."),
        ResourceBudget("temporal_saturation_count", 1, 4, 4, "summary", "Overflow counter."),
        ResourceBudget("temporal_reset_count", 1, 4, 4, "summary", "Reset/sham counter."),
        ResourceBudget("temporal_sham_mode/schema/trace_count padding", 1, 8, 8, "summary", "Packed compact-state fields."),
    ]
    return rows


def failure_classes() -> list[FailureClass]:
    return [
        FailureClass("host_hidden_temporal_update", "Host updates the temporal state outside the declared chip-owned path.", "Fail the native claim and return to local source audit."),
        FailureClass("future_target_leakage", "Temporal state depends on target/reward before it is causally available.", "Fail and add shuffled-target/wrong-horizon diagnostics before retry."),
        FailureClass("fixed_point_overflow_or_saturation", "Trace values clip or overflow under canonical inputs.", "Fail 4.31b; reduce gain/range or widen state before hardware."),
        FailureClass("lag_only_explains_effect", "Same-budget lag control matches the temporal trace.", "Do not promote native temporal migration; narrow claim."),
        FailureClass("sham_control_passes", "Zero/frozen/shuffled/reset controls reproduce the benefit.", "Fail and repair task/control separation."),
        FailureClass("readback_schema_drift", "Readback fields are missing, stale, or ambiguous.", "Fail ingest; update schema version and parser before rerun."),
        FailureClass("resource_budget_exceeded", "Initial state/readback exceeds declared compact budget.", "Fail readiness; redesign state subset before implementation."),
        FailureClass("nonlinear_recurrence_smuggled_in", "Hidden recurrent units or recurrence-specific claims enter the first native gate.", "Fail contract; separate into a later explicit recurrence tier."),
        FailureClass("ebrains_package_prepared_too_early", "Hardware upload is prepared before 4.31b local fixed-point parity passes.", "Invalidate package and restore local-first sequence."),
    ]


def command_plan(existing_codes: dict[str, int]) -> dict[str, Any]:
    proposed = {
        "CMD_TEMPORAL_INIT": 39,
        "CMD_TEMPORAL_UPDATE": 40,
        "CMD_TEMPORAL_READ_STATE": 41,
        "CMD_TEMPORAL_SHAM_MODE": 42,
    }
    collisions = {name: code for name, code in proposed.items() if code in set(existing_codes.values()) or name in existing_codes}
    return {
        "proposed_codes": proposed,
        "collisions": collisions,
        "host_sdp_scope": "setup, sham selection, compact readback only",
        "inter_core_scope": "none in 4.31b; later MCPL only if temporal state must be shared across cores",
        "implementation_rule": "do not add commands until 4.31b local fixed-point reference passes",
    }


def fixed_point_table() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tau in temporal_timescales():
        decay = math.exp(-1.0 / float(tau))
        alpha = 1.0 - decay
        rows.append(
            {
                "tau_steps": tau,
                "decay_float": decay,
                "alpha_float": alpha,
                "decay_raw_s16_15": fp_from_float(decay),
                "alpha_raw_s16_15": fp_from_float(alpha),
            }
        )
    return rows


def checksum_timescales(rows: list[dict[str, Any]]) -> int:
    checksum = 0
    for row in rows:
        checksum = (checksum * 1315423911 + int(row["tau_steps"]) * 17 + int(row["alpha_raw_s16_15"]) + int(row["decay_raw_s16_15"])) & 0xFFFFFFFF
    return checksum


def build_payload(output_dir: Path) -> dict[str, Any]:
    v22 = load_json(V22_BASELINE) if V22_BASELINE.exists() else {}
    tier519c = load_json(TIER519C_RESULTS) if TIER519C_RESULTS.exists() else {}
    tier430g_hw = load_json(TIER430G_HW_RESULTS) if TIER430G_HW_RESULTS.exists() else {}
    config_h = read_text(RUNTIME_SRC / "config.h") if (RUNTIME_SRC / "config.h").exists() else ""
    state_h = read_text(RUNTIME_SRC / "state_manager.h") if (RUNTIME_SRC / "state_manager.h").exists() else ""
    host_c = read_text(RUNTIME_SRC / "host_interface.c") if (RUNTIME_SRC / "host_interface.c").exists() else ""
    codes = parse_command_codes(config_h)
    fixed_rows = fixed_point_table()
    budget_rows = resource_budget()
    persistent_state_bytes = sum(row.total_bytes for row in budget_rows if row.location in {"DTCM/core-local", "summary"})
    total_initial_bytes = sum(row.total_bytes for row in budget_rows)
    proposed_commands = command_plan(codes)

    subset_decision = {
        "decision": "migrate_fading_memory_ema_traces_first",
        "state_subset": "seven causal EMA traces over the current temporal input; deltas and novelty are derived, not stored",
        "timescales": temporal_timescales(),
        "timescale_checksum": checksum_timescales(fixed_rows),
        "why": (
            "Tier 5.19c promoted fading_memory_only_ablation and explicitly did not "
            "promote bounded nonlinear recurrence. The smallest chip-owned subset is "
            "therefore the causal EMA trace bank plus compact counters/readback."
        ),
        "explicitly_excluded": [
            "hidden tanh recurrent units",
            "recurrent weight matrices",
            "Python-side temporal dictionaries in hardware claims",
            "future target or reward in temporal state updates",
            "multi-chip temporal sharing",
            "speedup or benchmark-superiority claims",
        ],
        "next_gate": "Tier 4.31b local fixed-point reference/parity; no EBRAINS package before that passes",
    }

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("v2.2 baseline exists", str(V22_BASELINE), "exists", V22_BASELINE.exists()),
        criterion("v2.2 baseline frozen", v22.get("status"), "== frozen", v22.get("status") == "frozen"),
        criterion("Tier 5.19c result exists", str(TIER519C_RESULTS), "exists", TIER519C_RESULTS.exists()),
        criterion("Tier 5.19c passed", tier519c.get("status"), "== pass", tier519c.get("status") == "pass"),
        criterion("Tier 5.19c freeze authorized", tier519c.get("summary", {}).get("freeze_authorized"), "== true", tier519c.get("summary", {}).get("freeze_authorized") is True),
        criterion("nonlinear recurrence excluded", tier519c.get("summary", {}).get("nonclaims", []), "contains not bounded nonlinear recurrence", "not bounded nonlinear recurrence" in tier519c.get("summary", {}).get("nonclaims", [])),
        criterion("lifecycle native baseline exists", str(LIFECYCLE_NATIVE_BASELINE), "exists", LIFECYCLE_NATIVE_BASELINE.exists()),
        criterion("Tier 4.30g hardware pass exists", str(TIER430G_HW_RESULTS), "exists", TIER430G_HW_RESULTS.exists()),
        criterion("Tier 4.30g hardware status passed", tier430g_hw.get("status"), "== pass", tier430g_hw.get("status") == "pass"),
        criterion("runtime fixed-point helpers present", "FP_MUL FP_FROM_FLOAT", "present in config.h", "FP_MUL" in config_h and "FP_FROM_FLOAT" in config_h),
        criterion("runtime bounded state constants present", "MAX_MEMORY_SLOTS/MAX_PENDING_HORIZONS", "present", "MAX_MEMORY_SLOTS" in config_h and "MAX_PENDING_HORIZONS" in config_h),
        criterion("existing lifecycle/native summary surface present", "cra_state_summary_t", "present", "cra_state_summary_t" in state_h and "host_if_pack_state_summary" in host_c),
        criterion("smallest temporal subset declared", subset_decision["state_subset"], "EMA traces only", "EMA traces" in subset_decision["state_subset"] and "hidden tanh recurrent units" in subset_decision["explicitly_excluded"]),
        criterion("fixed-point table complete", len(fixed_rows), f"== {len(temporal_timescales())}", len(fixed_rows) == len(temporal_timescales())),
        criterion("persistent temporal state budget compact", persistent_state_bytes, "<= 128 bytes", persistent_state_bytes <= 128),
        criterion("total initial temporal budget compact", total_initial_bytes, "<= 256 bytes", total_initial_bytes <= 256),
        criterion("readback schema declared", len(readback_schema()), ">= 10 fields", len(readback_schema()) >= 10),
        criterion("control suite declared", len(controls()), ">= 7 controls", len(controls()) >= 7),
        criterion("required controls include lag/frozen/shuffled/reset/no-plasticity", [c.name for c in controls()], "contains core controls", {"lag_only_online_lms_control", "frozen_temporal_state_ablation", "shuffled_temporal_state_sham", "state_reset_interval_control", "no_plasticity_ablation"}.issubset({c.name for c in controls()})),
        criterion("failure classes declared", len(failure_classes()), ">= 8 classes", len(failure_classes()) >= 8),
        criterion("proposed command codes do not collide", proposed_commands["collisions"], "empty", not proposed_commands["collisions"]),
        criterion("no EBRAINS package prepared", "local-readiness only", "no ebrains_jobs output", True, "This runner writes only controlled_test_output artifacts."),
        criterion("next step remains local", subset_decision["next_gate"], "Tier 4.31b local before hardware", subset_decision["next_gate"].startswith("Tier 4.31b local")),
    ]
    status = "pass" if all(item.passed for item in criteria) else "fail"
    failure_reason = "" if status == "pass" else "Failed criteria: " + ", ".join(item.name for item in criteria if not item.passed)
    return {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "criteria": criteria,
        "criteria_passed": sum(1 for item in criteria if item.passed),
        "criteria_total": len(criteria),
        "claim_boundary": (
            "Tier 4.31a is local readiness/contract evidence only. A pass defines "
            "the smallest native fading-memory temporal-state subset, fixed-point "
            "equations, controls, readback schema, resource budget, command plan, "
            "and failure classes before any implementation or EBRAINS package. It "
            "does not prove C runtime implementation, SpiNNaker hardware transfer, "
            "speedup, multi-chip scaling, nonlinear recurrence, universal benchmark "
            "superiority, language, planning, AGI, or ASI."
        ),
        "subset_decision": subset_decision,
        "fixed_point_table": fixed_rows,
        "state_specs": temporal_state_specs(),
        "equation_specs": temporal_equations(),
        "readback_schema": readback_schema(),
        "controls": controls(),
        "resource_budget": budget_rows,
        "persistent_state_bytes": persistent_state_bytes,
        "total_initial_temporal_bytes": total_initial_bytes,
        "failure_classes": failure_classes(),
        "command_plan": proposed_commands,
        "prerequisites": {
            "v2_2_baseline": str(V22_BASELINE),
            "tier5_19c_results": str(TIER519C_RESULTS),
            "lifecycle_native_baseline": str(LIFECYCLE_NATIVE_BASELINE),
            "tier4_30g_hw_results": str(TIER430G_HW_RESULTS),
        },
        "next_step": {
            "tier": "Tier 4.31b - Native Temporal-Substrate Local Fixed-Point Reference",
            "required_work": [
                "mirror the EMA trace update in local Python fixed-point",
                "compare against the Tier 5.19c fading-memory reference on temporal-memory diagnostics",
                "run lag-only, zero/frozen/shuffled/reset/no-plasticity/shuffled-target controls",
                "predeclare fixed-point tolerances and saturation limits",
                "only then consider C source implementation and EBRAINS packaging",
            ],
        },
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.31a Native Temporal-Substrate Readiness",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Output directory: `{payload['output_dir']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Decision",
        "",
        f"- Decision: `{payload['subset_decision']['decision']}`",
        f"- State subset: {payload['subset_decision']['state_subset']}",
        f"- Timescales: `{payload['subset_decision']['timescales']}`",
        f"- Timescale checksum: `{payload['subset_decision']['timescale_checksum']}`",
        f"- Persistent state bytes: `{payload['persistent_state_bytes']}`",
        f"- Total initial temporal bytes: `{payload['total_initial_temporal_bytes']}`",
        "",
        "The first native migration is **not** a hidden recurrent substrate. It is the v2.2-promoted causal EMA trace bank with derived deltas and novelty.",
        "",
        "## Fixed-Point Trace Table",
        "",
        "| tau | decay raw | alpha raw |",
        "| ---: | ---: | ---: |",
    ]
    for row in payload["fixed_point_table"]:
        lines.append(f"| {row['tau_steps']} | {row['decay_raw_s16_15']} | {row['alpha_raw_s16_15']} |")
    lines.extend(
        [
            "",
            "## Controls Required Before Hardware",
            "",
        ]
    )
    for row in payload["controls"]:
        lines.append(f"- `{row.name}`: {row.purpose}")
    lines.extend(
        [
            "",
            "## Proposed Command Plan",
            "",
            f"- Proposed codes: `{payload['command_plan']['proposed_codes']}`",
            f"- Collisions: `{payload['command_plan']['collisions']}`",
            f"- Implementation rule: {payload['command_plan']['implementation_rule']}",
            "",
            "## Next Step",
            "",
            f"- {payload['next_step']['tier']}",
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in payload["criteria"]:
        value = json.dumps(json_safe(item.value), sort_keys=True) if isinstance(item.value, (dict, list, tuple)) else str(item.value)
        lines.append(f"| {item.name} | `{value}` | {item.rule} | {'yes' if item.passed else 'no'} |")
    lines.append("")
    (output_dir / "tier4_31a_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = build_payload(output_dir)
    write_json(output_dir / "tier4_31a_results.json", payload)
    write_csv(output_dir / "tier4_31a_state_subset.csv", [asdict(row) for row in payload["state_specs"]])
    write_csv(output_dir / "tier4_31a_equations.csv", [asdict(row) for row in payload["equation_specs"]])
    write_csv(output_dir / "tier4_31a_readback_schema.csv", [asdict(row) for row in payload["readback_schema"]])
    write_csv(output_dir / "tier4_31a_controls.csv", [asdict(row) for row in payload["controls"]])
    write_csv(output_dir / "tier4_31a_resource_budget.csv", [asdict(row) for row in payload["resource_budget"]])
    write_csv(output_dir / "tier4_31a_failure_classes.csv", [asdict(row) for row in payload["failure_classes"]])
    write_csv(output_dir / "tier4_31a_fixed_point_table.csv", payload["fixed_point_table"])
    write_report(output_dir, payload)
    manifest = {
        "tier": TIER,
        "status": payload["status"],
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier4_31a_results.json"),
        "report_md": str(output_dir / "tier4_31a_report.md"),
        "criteria_passed": payload["criteria_passed"],
        "criteria_total": payload["criteria_total"],
        "claim_boundary": payload["claim_boundary"],
    }
    write_json(output_dir / "tier4_31a_latest_manifest.json", manifest)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = run(args)
    print(f"{TIER}: {payload['status']} ({payload['criteria_passed']}/{payload['criteria_total']} criteria)")
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
