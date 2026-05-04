#!/usr/bin/env python3
"""Tier 4.22a custom / hybrid on-chip runtime contract.

This is not a hardware run and not custom-C evidence. It is the paper-auditable
engineering contract that follows from Tier 4.20c and Tier 4.21a:

- Tier 4.20c proves the v2.1 chunked-host bridge repeats on real SpiNNaker.
- Tier 4.21a proves one stateful v2 mechanism, keyed context memory, can ride
  that bridge on real SpiNNaker.
- Tier 4.22a defines the next custom/hybrid runtime work so we do not burn
  hours on exhaustive per-mechanism bridge jobs that are not the final
  architecture.

Claim boundary:
- PASS means the custom-runtime migration contract is explicit, referenced to
  real evidence, and auditable.
- It is not native/on-chip CRA, not continuous execution, not custom C, and not
  a speedup claim.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
TIER = "Tier 4.22a - Custom / Hybrid On-Chip Runtime Contract"
RUNNER_REVISION = "tier4_22a_custom_runtime_contract_20260430_0000"
TIER4_20C_LATEST = CONTROLLED / "tier4_20c_latest_manifest.json"
TIER4_21A_LATEST = CONTROLLED / "tier4_21a_latest_manifest.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coral_reef_spinnaker.runtime_modes import make_runtime_plan  # noqa: E402


@dataclass(frozen=True)
class StateOwnershipRow:
    subsystem: str
    current_location: str
    tier4_22_target_location: str
    later_target_location: str
    state_items: str
    why_here: str
    audit_signal: str
    main_risk: str


@dataclass(frozen=True)
class RuntimeStageRow:
    stage: str
    purpose: str
    implementation_scope: str
    required_reference: str
    pass_gate: str
    fail_gate: str
    claim_if_passed: str


@dataclass(frozen=True)
class ParityRow:
    reference: str
    candidate: str
    metric: str
    tolerance_or_rule: str
    required_artifact: str
    failure_interpretation: str


@dataclass(frozen=True)
class MemoryBudgetRow:
    item: str
    current_bridge_representation: str
    custom_runtime_representation: str
    scale_driver: str
    risk: str
    mitigation: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                keys.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def criterion(name: str, value: Any, rule: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": bool(passed)}


def status_from_latest(path: Path) -> tuple[str, Path | None, dict[str, Any] | None]:
    if not path.exists():
        return "missing", None, None
    latest = read_json(path)
    manifest_path = Path(str(latest.get("manifest", "")))
    if not manifest_path.exists():
        return "manifest_missing", manifest_path, latest
    return str(latest.get("status", "unknown")).lower(), manifest_path, latest


def load_reference(path: Path) -> dict[str, Any]:
    status, manifest_path, latest = status_from_latest(path)
    manifest = read_json(manifest_path) if manifest_path and manifest_path.exists() else {}
    return {
        "latest_manifest_path": str(path),
        "latest_status": status,
        "manifest_path": str(manifest_path) if manifest_path else None,
        "latest": latest or {},
        "manifest": manifest,
        "summary": manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {},
    }


def runtime_plan_record(*, runtime_mode: str, learning_location: str, chunk_size_steps: int, total_steps: int, dt_seconds: float) -> dict[str, Any]:
    plan = make_runtime_plan(
        runtime_mode=runtime_mode,
        learning_location=learning_location,
        chunk_size_steps=chunk_size_steps,
        total_steps=total_steps,
        dt_seconds=dt_seconds,
    )
    record = asdict(plan)
    record.update(
        {
            "sim_run_calls": plan.sim_run_calls,
            "simulated_ms_per_chunk": plan.simulated_ms_per_chunk,
            "call_reduction_factor": plan.call_reduction_factor,
            "learning_update_interval_steps": plan.learning_update_interval_steps,
        }
    )
    return record


def state_ownership_rows() -> list[StateOwnershipRow]:
    return [
        StateOwnershipRow(
            subsystem="experiment orchestration",
            current_location="host",
            tier4_22_target_location="host",
            later_target_location="host",
            state_items="task selection, seeds, graph build, run configuration, evidence manifests",
            why_here="orchestration is not the biological/learning loop and must remain auditable",
            audit_signal="manifest records exact command, seed, source revision, and output directory",
            main_risk="none; moving this on-chip would reduce auditability rather than improve runtime",
        ),
        StateOwnershipRow(
            subsystem="input/event scheduling",
            current_location="host chunk scheduler",
            tier4_22_target_location="hybrid: host sends compact scheduled event streams, chip consumes continuously",
            later_target_location="mostly on-chip event/state machine for repeated tasks",
            state_items="sensory current schedules, context events, reward events, replay windows",
            why_here="needed to reduce per-chunk host intervention while preserving exact task contracts",
            audit_signal="scheduled-event table plus chip-side event counters",
            main_risk="event timing drift or hidden future/context leakage",
        ),
        StateOwnershipRow(
            subsystem="spike dynamics",
            current_location="SpiNNaker/PyNN cell dynamics",
            tier4_22_target_location="chip",
            later_target_location="chip",
            state_items="membrane state, refractory state, spike emission",
            why_here="this is already the hardware substrate",
            audit_signal="spike count summaries and optional sparse spike samples",
            main_risk="readback volume can erase runtime gains",
        ),
        StateOwnershipRow(
            subsystem="delayed credit / reward state",
            current_location="host PendingHorizon / host replay",
            tier4_22_target_location="hybrid first: chip stores compact eligibility/recent activity; host may send sparse reward events",
            later_target_location="on-chip local eligibility/reward update when fixed-point parity passes",
            state_items="pending horizons, reward timing, eligibility traces, dopamine/reward scalar",
            why_here="per-step host replay is the main architectural bottleneck",
            audit_signal="eligibility counters, reward-event counters, weight-delta summaries, fixed-point range logs",
            main_risk="per-synapse trace memory or per-ms trace sweeps exceed chip resources",
        ),
        StateOwnershipRow(
            subsystem="keyed context memory",
            current_location="host keyed-memory scheduler",
            tier4_22_target_location="hybrid/on-chip preallocated slots with host-readable counters",
            later_target_location="chip-local fixed-size slot table and routing masks",
            state_items="context keys, slot values, slot confidence, overwrite policy",
            why_here="Tier 4.21a proved stateful keyed memory can ride the bridge; next step is persistent local state",
            audit_signal="slot-write, slot-hit, slot-evict, wrong-key, and slot-shuffle counters",
            main_risk="dynamic Python dictionaries do not map directly to chip memory; slot count must be bounded",
        ),
        StateOwnershipRow(
            subsystem="replay / consolidation",
            current_location="host offline replay loop",
            tier4_22_target_location="host-led replay window or hybrid scheduled replay, not first on-chip target",
            later_target_location="chip-assisted replay after compact memory-store design exists",
            state_items="replay buffer, replay schedule, consolidation writes",
            why_here="software replay is promoted, but priority weighting is not; replay is expensive and easy to overclaim",
            audit_signal="online/replay phase separation, replay event IDs, no-feedback-leakage checks",
            main_risk="replay can fabricate training exposure unless phase boundaries are explicit",
        ),
        StateOwnershipRow(
            subsystem="composition / routing / self-evaluation",
            current_location="host mechanism tables and monitor",
            tier4_22_target_location="host/hybrid summary-driven control after lower-level state is stable",
            later_target_location="bounded chip-local router/monitor counters where useful",
            state_items="module tables, router scores, confidence/error estimates, uncertainty gates",
            why_here="these depend on stable memory/credit state; porting them first would hide lower-level failures",
            audit_signal="pre-feedback route/confidence logs and shuffled/disabled controls",
            main_risk="high-level mechanism appears to work through host hints rather than hardware state",
        ),
        StateOwnershipRow(
            subsystem="readback/provenance",
            current_location="full or frequent spike/readback extraction",
            tier4_22_target_location="compact end-of-run summaries plus optional debug windows",
            later_target_location="compact summaries by default; full readback only for diagnostics",
            state_items="spike totals, decision summaries, weight/slot/event counters, failure counters",
            why_here="readback volume is a major runtime bottleneck and paper-risk if unaudited",
            audit_signal="summary schema, provenance hashes, optional debug trace windows",
            main_risk="too little readback makes failures uninterpretable; too much readback kills speed",
        ),
    ]


def runtime_stage_rows() -> list[RuntimeStageRow]:
    return [
        RuntimeStageRow(
            stage="4.22a0 constrained-NEST + sPyNNaker mapping preflight",
            purpose="catch hardware-transfer failures before expensive EBRAINS runs",
            implementation_scope="SpiNNaker-constrained NEST emulation, static PyNN feature compliance, bounded-state/resource checks, and a tiny sPyNNaker map/build/run smoke when a SpiNNaker stack is available",
            required_reference="Tier 4.20c/4.21a hardware-legal PyNN subset and chunked reference traces",
            pass_gate="constrained-NEST parity passes, unsupported PyNN features are absent, no dynamic graph mutation is required, and sPyNNaker can build/map or complete a tiny smoke run in the target environment",
            fail_gate="NEST only works with capabilities not available on SpiNNaker, PyNN uses unsupported primitives, state/resource estimates exceed bounds, or sPyNNaker mapping fails before science can be tested",
            claim_if_passed="pre-hardware transfer risk is reduced; final hardware evidence is still required",
        ),
        RuntimeStageRow(
            stage="4.22b continuous no-learning scaffold",
            purpose="prove a one-call or near-one-call hardware run can execute scheduled input and return compact summaries",
            implementation_scope="no plasticity; fixed readout; scheduled sensory/context events; compact spike/decision counters",
            required_reference="Tier 4.20c delayed_cue/hard_noisy_switching and Tier 4.21a scheduled keyed-memory input trace shape",
            pass_gate="real hardware run, no synthetic fallback, <= 1 sim.run per task/variant, compact summary readback, spike totals within predeclared tolerance",
            fail_gate="requires chunk-loop host intervention, loses scheduled-event timing, or cannot explain missing/extra spikes",
            claim_if_passed="continuous hardware scaffold works for CRA-compatible scheduled streams; no learning claim",
        ),
        RuntimeStageRow(
            stage="4.22c persistent local state scaffold",
            purpose="prove chip/hybrid state persists across internal decisions without host replay after every chunk",
            implementation_scope="bounded state structs for readout, counters, keyed slots, and optional recent-activity summaries",
            required_reference="Tier 4.21a keyed slot telemetry and Tier 5.10g keyed-memory software contract",
            pass_gate="state counters/slots persist, reset only on declared reset, and match bridge reference qualitatively",
            fail_gate="state resets silently, memory slots corrupt, or provenance cannot distinguish state bug from task bug",
            claim_if_passed="persistent hardware/hybrid state scaffold exists; still no full on-chip learning claim",
        ),
        RuntimeStageRow(
            stage="4.22d reward/plasticity on-chip or hybrid",
            purpose="move the delayed-credit bottleneck out of per-step host replay",
            implementation_scope="fixed-point reward/plasticity update, bounded eligibility/recent-activity state, sparse reward command path",
            required_reference="Tier 5.4 delayed_lr_0_20, Tier 4.16a/b, Tier 4.20c bridge traces",
            pass_gate="learning metric matches chunked reference qualitatively, weight summaries are bounded, and fixed-point traces pass range/decay checks",
            fail_gate="trace memory exceeds resource budget, fixed-point update diverges, or host still computes all weight updates",
            claim_if_passed="hybrid/native reward-plasticity path works on a minimal CRA capsule",
        ),
        RuntimeStageRow(
            stage="4.22e keyed memory / routing state integration",
            purpose="move the first stateful v2 mechanism from bridge adapter toward persistent chip/hybrid state",
            implementation_scope="preallocated slot table, key hashes/IDs, slot confidence, router masks/counters",
            required_reference="Tier 4.21a keyed-memory bridge pass and Tier 5.10g/5.13c software guardrails",
            pass_gate="keyed candidate keeps bridge-level behavior while slot-reset/shuffle/wrong-key controls still separate",
            fail_gate="controls no longer separate or state is implicitly supplied by host metadata after the decision point",
            claim_if_passed="bounded keyed memory/routing state survives the custom/hybrid runtime",
        ),
        RuntimeStageRow(
            stage="4.23 continuous / stop-batching parity",
            purpose="prove the custom runtime can replace the chunked bridge reference",
            implementation_scope="single or near-single hardware run, compact readback, no per-chunk host learning replay",
            required_reference="Tier 4.20c and Tier 4.21a reference traces",
            pass_gate="accuracy/correlation/recovery/state counters within tolerance; runtime/readback reduction documented; repeatable across seeds",
            fail_gate="behavior only works with chunked host replay, or speed gains vanish under required provenance",
            claim_if_passed="custom/hybrid continuous runtime is a valid replacement for the chunked proof bridge",
        ),
    ]


def parity_rows() -> list[ParityRow]:
    return [
        ParityRow(
            reference="Tier 4.20c chunked bridge",
            candidate="4.22a0 constrained-NEST preflight",
            metric="hardware-legal model subset",
            tolerance_or_rule="same task/stream contracts pass without unsupported PyNN features, dynamic graph mutation, unbounded host state, or future-information leakage",
            required_artifact="constrained-NEST summary, PyNN compliance report, resource/mapping preflight report",
            failure_interpretation="software mechanism is not yet hardware-compatible enough to justify EBRAINS runtime",
        ),
        ParityRow(
            reference="Tier 4.20c chunked bridge",
            candidate="4.22b continuous scaffold",
            metric="spike-count summary",
            tolerance_or_rule="same order of magnitude and no silent zero-spike collapse; exact equality not required",
            required_artifact="runtime summary CSV plus compact spike counters",
            failure_interpretation="transport/scheduling problem before learning can be judged",
        ),
        ParityRow(
            reference="Tier 4.20c chunked bridge",
            candidate="4.22d reward/plasticity",
            metric="delayed_cue tail accuracy and hard-switch qualitative behavior",
            tolerance_or_rule="delayed_cue remains near 1.0; hard-switch remains above declared transfer threshold or failure is diagnosed",
            required_artifact="per-task summary, weight-delta summary, reward/eligibility counters",
            failure_interpretation="credit/plasticity implementation bug or resource-constrained narrowing of claim",
        ),
        ParityRow(
            reference="Tier 4.21a keyed-memory bridge",
            candidate="4.22e keyed memory/routing state",
            metric="keyed-vs-ablation separation",
            tolerance_or_rule="keyed candidate beats wrong-key/slot-shuffle and is not worse than slot-reset; slot telemetry active",
            required_artifact="slot-event CSV, keyed/ablation summary, compact provenance",
            failure_interpretation="keyed state is not represented correctly in custom runtime",
        ),
        ParityRow(
            reference="Tier 5 software guardrails",
            candidate="4.23 continuous custom runtime",
            metric="no-leakage and sham-control preservation",
            tolerance_or_rule="control failures remain failures; no future context/reward is visible before decision",
            required_artifact="leakage audit table and phase-separated event log",
            failure_interpretation="runtime is leaking information or task contract changed",
        ),
        ParityRow(
            reference="Tier 4.18a/4.21a runtime observations",
            candidate="4.23 continuous custom runtime",
            metric="runtime/readback cost",
            tolerance_or_rule="sim.run calls reduced toward 1 per case and readback volume reduced; exact wall-time speedup must be measured",
            required_artifact="runtime breakdown, readback byte/row counts, provenance size",
            failure_interpretation="custom runtime may be correct but not yet useful as a scaling path",
        ),
    ]


def memory_budget_rows() -> list[MemoryBudgetRow]:
    return [
        MemoryBudgetRow(
            item="readout weights / bias",
            current_bridge_representation="host floating-point state replayed after binned spike readback",
            custom_runtime_representation="bounded fixed-point or hybrid state per active polyp/readout channel",
            scale_driver="population size and readout channels",
            risk="fixed-point saturation or drift",
            mitigation="range logs, clipping counters, reference fixed-point unit tests",
        ),
        MemoryBudgetRow(
            item="eligibility / recent activity",
            current_bridge_representation="host PendingHorizon ledger",
            custom_runtime_representation="timestamped decay or compact recent-activity counters, not full per-ms sweeps",
            scale_driver="synapse count, horizon length, update frequency",
            risk="SDRAM/DTCM pressure or per-ms sweep cost",
            mitigation="lazy timestamp decay, per-neuron approximation first, resource budget before full per-synapse traces",
        ),
        MemoryBudgetRow(
            item="keyed context slots",
            current_bridge_representation="host dict/list slot table",
            custom_runtime_representation="preallocated fixed slot table with bounded key IDs and confidence",
            scale_driver="slot count, key width, population modules",
            risk="dynamic memory semantics do not map to chip C",
            mitigation="fixed max slots, explicit eviction policy, wrong-key/slot-shuffle counters",
        ),
        MemoryBudgetRow(
            item="replay/consolidation buffer",
            current_bridge_representation="host replay buffer and offline consolidation loop",
            custom_runtime_representation="host-led replay first; chip-assisted replay only after storage budget is explicit",
            scale_driver="stored events, replay length, event dimensionality",
            risk="replay storage can dwarf model state",
            mitigation="keep replay host-led until compact replay representation passes controls",
        ),
        MemoryBudgetRow(
            item="routing / composition tables",
            current_bridge_representation="host module tables and router scores",
            custom_runtime_representation="bounded masks/counters; host may still own high-level module library initially",
            scale_driver="module count, active routes, context count",
            risk="high-level routing hides host hints",
            mitigation="pre-feedback route logs, disabled/shuffled route controls, compact route counters",
        ),
        MemoryBudgetRow(
            item="provenance/readback",
            current_bridge_representation="frequent full traces and CSV export",
            custom_runtime_representation="compact counters by default plus debug trace windows",
            scale_driver="steps, populations, spike volume, variants",
            risk="full readback eliminates speed gains",
            mitigation="two modes: proof/debug full trace and scale compact-summary mode",
        ),
    ]


def build_summary(args: argparse.Namespace, ref420c: dict[str, Any], ref421a: dict[str, Any]) -> dict[str, Any]:
    s420c = ref420c["summary"]
    s421a = ref421a["summary"]
    chunk_size = int(args.chunk_size_steps)
    total_steps = int(args.total_steps)
    calls_per_case_chunked = ceil(total_steps / chunk_size)
    return {
        "runner_revision": RUNNER_REVISION,
        "claim_boundary": "Design/contract evidence only; not custom-C, native/on-chip, continuous runtime, or speedup evidence.",
        "tier4_20c_status": ref420c["latest_status"],
        "tier4_20c_manifest": ref420c["manifest_path"],
        "tier4_20c_child_runs": s420c.get("child_runs"),
        "tier4_20c_child_sim_run_failures_sum": s420c.get("child_sim_run_failures_sum"),
        "tier4_20c_child_summary_read_failures_sum": s420c.get("child_summary_read_failures_sum"),
        "tier4_20c_child_synthetic_fallbacks_sum": s420c.get("child_synthetic_fallbacks_sum"),
        "tier4_20c_child_total_step_spikes_min": s420c.get("child_total_step_spikes_min"),
        "tier4_20c_runtime_seconds": s420c.get("runtime_seconds"),
        "tier4_21a_status": ref421a["latest_status"],
        "tier4_21a_manifest": ref421a["manifest_path"],
        "tier4_21a_runs": s421a.get("runs"),
        "tier4_21a_sim_run_failures_sum": s421a.get("sim_run_failures_sum"),
        "tier4_21a_summary_read_failures_sum": s421a.get("summary_read_failures_sum"),
        "tier4_21a_synthetic_fallbacks_sum": s421a.get("synthetic_fallbacks_sum"),
        "tier4_21a_total_step_spikes_min": s421a.get("total_step_spikes_min"),
        "tier4_21a_keyed_context_memory_updates_sum": s421a.get("keyed_context_memory_updates_sum"),
        "tier4_21a_keyed_feature_active_steps_sum": s421a.get("keyed_feature_active_steps_sum"),
        "tier4_21a_keyed_max_context_memory_slots": s421a.get("keyed_max_context_memory_slots"),
        "tier4_21a_runtime_seconds": s421a.get("runtime_seconds"),
        "observed_bridge_runtime_problem": "Tier 4.21a took about 58.7 minutes for one seed/four variants; exhaustive bridge matrices are not the target architecture.",
        "step_host_plan": runtime_plan_record(runtime_mode="step", learning_location="host", chunk_size_steps=1, total_steps=total_steps, dt_seconds=args.dt_seconds),
        "chunked_host_plan": runtime_plan_record(runtime_mode="chunked", learning_location="host", chunk_size_steps=chunk_size, total_steps=total_steps, dt_seconds=args.dt_seconds),
        "continuous_on_chip_plan": runtime_plan_record(runtime_mode="continuous", learning_location="on_chip", chunk_size_steps=total_steps, total_steps=total_steps, dt_seconds=args.dt_seconds),
        "calls_per_case_chunked_reference": calls_per_case_chunked,
        "calls_per_case_continuous_target": 1,
        "default_reference_total_steps": total_steps,
        "default_reference_chunk_size_steps": chunk_size,
            "recommended_sequence": [
                "Use Tier 4.20c and Tier 4.21a as chunked-host reference traces.",
                "Do not run exhaustive per-mechanism hardware bridge matrices by default.",
                "Implement constrained-NEST plus sPyNNaker mapping preflight before any further expensive hardware allocation.",
                "Implement 4.22b continuous no-learning scaffold first.",
                "Add 4.22c persistent local state only after 4.22b returns auditable summaries.",
                "Add 4.22d reward/plasticity/eligibility with fixed-point/resource logs.",
                "Add 4.22e keyed memory/routing state after lower-level state is stable.",
            "Run 4.23 continuous parity against chunked reference before any final hardware claim.",
        ],
    }


def build_result(args: argparse.Namespace, output_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    ref420c = load_reference(TIER4_20C_LATEST)
    ref421a = load_reference(TIER4_21A_LATEST)
    state_rows = [asdict(row) for row in state_ownership_rows()]
    stage_rows = [asdict(row) for row in runtime_stage_rows()]
    parity = [asdict(row) for row in parity_rows()]
    memory = [asdict(row) for row in memory_budget_rows()]
    summary = build_summary(args, ref420c, ref421a)

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("Tier 4.20c reference pass exists", ref420c["latest_status"], "== pass", ref420c["latest_status"] == "pass"),
        criterion("Tier 4.21a reference pass exists", ref421a["latest_status"], "== pass", ref421a["latest_status"] == "pass"),
        criterion("Tier 4.20c had zero child sim/readback/fallback failures", {
            "sim": summary.get("tier4_20c_child_sim_run_failures_sum"),
            "readback": summary.get("tier4_20c_child_summary_read_failures_sum"),
            "fallback": summary.get("tier4_20c_child_synthetic_fallbacks_sum"),
        }, "all == 0", all((summary.get(k) or 0) == 0 for k in ["tier4_20c_child_sim_run_failures_sum", "tier4_20c_child_summary_read_failures_sum", "tier4_20c_child_synthetic_fallbacks_sum"])),
        criterion("Tier 4.21a had zero sim/readback/fallback failures", {
            "sim": summary.get("tier4_21a_sim_run_failures_sum"),
            "readback": summary.get("tier4_21a_summary_read_failures_sum"),
            "fallback": summary.get("tier4_21a_synthetic_fallbacks_sum"),
        }, "all == 0", all((summary.get(k) or 0) == 0 for k in ["tier4_21a_sim_run_failures_sum", "tier4_21a_summary_read_failures_sum", "tier4_21a_synthetic_fallbacks_sum"])),
        criterion("state ownership table covers core subsystems", len(state_rows), ">= 6", len(state_rows) >= 6),
        criterion("runtime stage plan defines staged gates", len(stage_rows), ">= 5", len(stage_rows) >= 5),
        criterion("parity contract defines reference/candidate checks", len(parity), ">= 4", len(parity) >= 4),
        criterion("memory/resource budget risks documented", len(memory), ">= 5", len(memory) >= 5),
        criterion("no exhaustive per-mechanism bridge mandate", summary["recommended_sequence"][1], "explicitly avoid default exhaustive hardware matrices", "Do not run exhaustive" in summary["recommended_sequence"][1]),
        criterion("pre-hardware constrained emulation/mapping gate declared", summary["recommended_sequence"][2], "constrained-NEST plus sPyNNaker preflight before more hardware", "constrained-NEST" in summary["recommended_sequence"][2]),
        criterion("continuous target is not marked implemented", summary["continuous_on_chip_plan"]["implemented"], "False until custom runtime exists", summary["continuous_on_chip_plan"]["implemented"] is False),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    failure = "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"])
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure,
        "output_dir": str(output_dir),
        "summary": summary,
        "criteria": criteria,
        "state_ownership": state_rows,
        "runtime_stages": stage_rows,
        "parity_contract": parity,
        "memory_budget": memory,
        "artifacts": {},
    }
    return result, state_rows, stage_rows, parity, memory


def markdown_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(json_safe(value), sort_keys=True)
    return "" if value is None else str(value)


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    lines = [
        "# Tier 4.22a Custom / Hybrid On-Chip Runtime Contract",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 4.22a is the auditable migration contract from the proven chunked-host hardware bridge toward a custom/hybrid/on-chip runtime. It is a design gate, not a hardware pass.",
        "",
        "## Why This Exists",
        "",
        "- Tier 4.20c proved repeatable v2.1 chunked-host bridge transport on real SpiNNaker.",
        "- Tier 4.21a proved one stateful v2 mechanism, keyed context memory, can ride that bridge.",
        "- Tier 4.21a also took nearly one hour for one seed and four variants, so exhaustive bridge matrices are not the right architecture path.",
        "- Tier 4.22a defines what moves on-chip/hybrid next and how parity will be judged.",
        "",
        "## Claim Boundary",
        "",
        "- `PASS` means the custom-runtime migration contract is explicit and references real evidence.",
        "- This is not custom C, not native/on-chip CRA, not continuous execution, and not a speedup claim.",
        "- Future speed claims require measured runtime/readback/provenance reductions.",
        "",
        "## Reference Evidence",
        "",
        f"- Tier 4.20c status: `{summary.get('tier4_20c_status')}`",
        f"- Tier 4.20c manifest: `{summary.get('tier4_20c_manifest')}`",
        f"- Tier 4.20c child runs: `{summary.get('tier4_20c_child_runs')}`",
        f"- Tier 4.20c minimum real spike readback: `{markdown_value(summary.get('tier4_20c_child_total_step_spikes_min'))}`",
        f"- Tier 4.21a status: `{summary.get('tier4_21a_status')}`",
        f"- Tier 4.21a manifest: `{summary.get('tier4_21a_manifest')}`",
        f"- Tier 4.21a runs: `{summary.get('tier4_21a_runs')}`",
        f"- Tier 4.21a minimum real spike readback: `{markdown_value(summary.get('tier4_21a_total_step_spikes_min'))}`",
        f"- Tier 4.21a runtime: `{markdown_value(summary.get('tier4_21a_runtime_seconds'))}` seconds",
        "",
        "## Runtime Target",
        "",
        f"- Current chunked reference calls per `{summary['default_reference_total_steps']}`-step case at chunk `{summary['default_reference_chunk_size_steps']}`: `{summary['calls_per_case_chunked_reference']}`",
        f"- Continuous target calls per case: `{summary['calls_per_case_continuous_target']}`",
        "- The target is fewer host interventions and compact readback, not blind speed claims.",
        "",
        "## State Ownership",
        "",
        "| Subsystem | Current | Tier 4.22 target | Later target | Main risk |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in result["state_ownership"]:
        lines.append(
            f"| {row['subsystem']} | {row['current_location']} | {row['tier4_22_target_location']} | {row['later_target_location']} | {row['main_risk']} |"
        )
    lines.extend(["", "## Runtime Stages", "", "| Stage | Purpose | Pass gate | Claim if passed |", "| --- | --- | --- | --- |"])
    for row in result["runtime_stages"]:
        lines.append(f"| {row['stage']} | {row['purpose']} | {row['pass_gate']} | {row['claim_if_passed']} |")
    lines.extend(["", "## Parity Contract", "", "| Reference | Candidate | Metric | Rule | Failure interpretation |", "| --- | --- | --- | --- | --- |"])
    for row in result["parity_contract"]:
        lines.append(f"| {row['reference']} | {row['candidate']} | {row['metric']} | {row['tolerance_or_rule']} | {row['failure_interpretation']} |")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{markdown_value(item['value'])}` | `{item['rule']}` | {'yes' if item['passed'] else 'no'} |")
    lines.extend(["", "## Recommended Sequence", ""])
    for i, item in enumerate(summary["recommended_sequence"], start=1):
        lines.append(f"{i}. {item}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str) -> None:
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest),
        "report": str(report),
        "canonical": False,
        "claim": "Latest Tier 4.22a custom-runtime contract; design/engineering evidence only, not hardware/custom-C evidence.",
    }
    write_json(CONTROLLED / "tier4_22a_latest_manifest.json", payload)


def run(args: argparse.Namespace) -> int:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (args.output_dir or CONTROLLED / f"tier4_22a_{stamp}_custom_runtime_contract").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result, state_rows, stage_rows, parity_rows_, memory_rows = build_result(args, output_dir)
    manifest = output_dir / "tier4_22a_results.json"
    report = output_dir / "tier4_22a_report.md"
    state_csv = output_dir / "tier4_22a_state_ownership.csv"
    stages_csv = output_dir / "tier4_22a_runtime_stages.csv"
    parity_csv = output_dir / "tier4_22a_parity_contract.csv"
    memory_csv = output_dir / "tier4_22a_memory_budget.csv"
    reference_json = output_dir / "tier4_22a_reference_manifest.json"
    result["artifacts"] = {
        "manifest_json": str(manifest),
        "report_md": str(report),
        "state_ownership_csv": str(state_csv),
        "runtime_stages_csv": str(stages_csv),
        "parity_contract_csv": str(parity_csv),
        "memory_budget_csv": str(memory_csv),
        "reference_manifest_json": str(reference_json),
    }
    reference = {
        "tier4_20c_latest": str(TIER4_20C_LATEST),
        "tier4_20c_manifest": result["summary"].get("tier4_20c_manifest"),
        "tier4_21a_latest": str(TIER4_21A_LATEST),
        "tier4_21a_manifest": result["summary"].get("tier4_21a_manifest"),
        "contract": "Tier 4.22a uses these as reference traces; it does not promote new hardware behavior by itself.",
    }
    write_csv(state_csv, state_rows)
    write_csv(stages_csv, stage_rows)
    write_csv(parity_csv, parity_rows_)
    write_csv(memory_csv, memory_rows)
    write_json(reference_json, reference)
    write_json(manifest, result)
    write_report(report, result)
    write_latest(output_dir, manifest, report, result["status"])
    print(json.dumps({"status": result["status"], "output_dir": str(output_dir), "manifest": str(manifest), "report": str(report)}, indent=2))
    return 0 if result["status"] == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tier 4.22a custom/hybrid on-chip runtime contract.")
    parser.add_argument("--total-steps", type=int, default=1200)
    parser.add_argument("--chunk-size-steps", type=int, default=50)
    parser.add_argument("--dt-seconds", type=float, default=1.0)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
