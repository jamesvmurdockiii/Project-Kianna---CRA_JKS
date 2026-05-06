#!/usr/bin/env python3
"""Tier 4.30a local static-pool lifecycle reference.

This tier builds the deterministic reference model that future lifecycle-native
C/runtime work must match. It is intentionally local-only: no C edits, no
hardware package, no lifecycle performance claim, and no baseline freeze.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 4.30a - Local Static-Pool Lifecycle Reference"
RUNNER_REVISION = "tier4_30a_static_pool_reference_20260505_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_30a_20260505_static_pool_lifecycle_reference"
CONTRACT_RESULTS = (
    CONTROLLED
    / "tier4_30_20260505_lifecycle_native_contract"
    / "tier4_30_contract_results.json"
)

FP_ONE = 1 << 15
FP_CLIP_MIN = -4 * FP_ONE
FP_CLIP_MAX = 4 * FP_ONE
EVENT_NAMES = {
    "none": 0,
    "trophic_update": 1,
    "cleavage": 2,
    "adult_birth": 3,
    "death": 4,
    "maturity_handoff": 5,
}
CONTROL_MODES = [
    "enabled",
    "fixed_static_pool_control",
    "random_event_replay_control",
    "active_mask_shuffle_control",
    "lineage_id_shuffle_control",
    "no_trophic_pressure_control",
    "no_dopamine_or_plasticity_control",
]


@dataclass
class SlotState:
    slot_id: int
    active_mask: int
    polyp_id: int
    lineage_id: int
    parent_slot: int
    generation: int
    age_steps: int
    trophic_health_raw: int
    cyclin_d_raw: int
    bax_raw: int
    last_event_type: int
    event_count: int


@dataclass(frozen=True)
class LifecycleEvent:
    event_index: int
    event_type: str
    target_slot: int = -1
    parent_slot: int = -1
    child_slot: int = -1
    trophic_delta_raw: int = 0
    reward_raw: int = 0


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fp(value: float) -> int:
    return int(round(value * FP_ONE))


def clip_raw(value: int) -> int:
    return max(FP_CLIP_MIN, min(FP_CLIP_MAX, int(value)))


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


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


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


class LifecycleReference:
    def __init__(
        self,
        *,
        pool_size: int = 8,
        founder_count: int = 2,
        seed: int = 42,
        mode: str = "enabled",
    ) -> None:
        self.pool_size = pool_size
        self.founder_count = founder_count
        self.seed = seed
        self.mode = mode
        self.next_polyp_id = 2000
        self.next_lineage_id = 100
        self.event_count = 0
        self.attempted_event_count = 0
        self.cleavage_count = 0
        self.birth_count = 0
        self.death_count = 0
        self.invalid_event_count = 0
        self.sham_counter = 0
        self.rows: list[dict[str, Any]] = []
        self.permutation = self._make_permutation()
        self.slots = self._init_slots()

    def _make_permutation(self) -> dict[int, int]:
        ids = list(range(self.pool_size))
        rng = random.Random(1000 + self.seed)
        rng.shuffle(ids)
        return {source: target for source, target in enumerate(ids)}

    def _init_slots(self) -> list[SlotState]:
        slots: list[SlotState] = []
        lineage_map = list(range(1, self.pool_size + 1))
        if self.mode == "lineage_id_shuffle_control":
            lineage_map = list(reversed(lineage_map))
        for slot_id in range(self.pool_size):
            active = 1 if slot_id < self.founder_count else 0
            slots.append(
                SlotState(
                    slot_id=slot_id,
                    active_mask=active,
                    polyp_id=1000 + slot_id if active else 0,
                    lineage_id=lineage_map[slot_id] if active else 0,
                    parent_slot=-1,
                    generation=0,
                    age_steps=0,
                    trophic_health_raw=FP_ONE if active else 0,
                    cyclin_d_raw=0,
                    bax_raw=0,
                    last_event_type=EVENT_NAMES["none"],
                    event_count=0,
                )
            )
        return slots

    def active_slots(self) -> list[int]:
        return [slot.slot_id for slot in self.slots if slot.active_mask]

    def inactive_slots(self) -> list[int]:
        return [slot.slot_id for slot in self.slots if not slot.active_mask]

    def active_mask_bits(self) -> int:
        mask = 0
        for slot in self.slots:
            if slot.active_mask:
                mask |= 1 << slot.slot_id
        return mask

    def lineage_checksum(self) -> int:
        checksum = 0
        for slot in self.slots:
            checksum = (
                checksum
                + (slot.slot_id + 1)
                * (slot.lineage_id + 17)
                * (slot.generation + 1)
                * (slot.parent_slot + 3)
                * (1 if slot.active_mask else 5)
            ) & 0xFFFFFFFF
        return checksum

    def trophic_checksum(self) -> int:
        total = 0
        for slot in self.slots:
            total += (slot.slot_id + 1) * (
                slot.trophic_health_raw + slot.cyclin_d_raw - slot.bax_raw
            )
        return int(total)

    def summary(self) -> dict[str, Any]:
        active_count = len(self.active_slots())
        return {
            "mode": self.mode,
            "pool_size": self.pool_size,
            "founder_count": self.founder_count,
            "active_count": active_count,
            "inactive_count": self.pool_size - active_count,
            "active_mask_bits": self.active_mask_bits(),
            "lineage_checksum": self.lineage_checksum(),
            "trophic_checksum": self.trophic_checksum(),
            "event_count": self.event_count,
            "attempted_event_count": self.attempted_event_count,
            "cleavage_count": self.cleavage_count,
            "birth_count": self.birth_count,
            "death_count": self.death_count,
            "invalid_event_count": self.invalid_event_count,
            "sham_counter": self.sham_counter,
            "max_active_count": max((row["active_count"] for row in self.rows), default=active_count),
        }

    def final_state_rows(self, scenario: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for slot in self.slots:
            row = asdict(slot)
            row.update({"scenario": scenario, "mode": self.mode})
            rows.append(row)
        return rows

    def _map_event_for_mode(self, event: LifecycleEvent) -> LifecycleEvent:
        if self.mode not in {"active_mask_shuffle_control", "random_event_replay_control"}:
            return event
        mapped = self.permutation
        return LifecycleEvent(
            event_index=event.event_index,
            event_type=event.event_type,
            target_slot=mapped.get(event.target_slot, event.target_slot) if event.target_slot >= 0 else -1,
            parent_slot=mapped.get(event.parent_slot, event.parent_slot) if event.parent_slot >= 0 else -1,
            child_slot=mapped.get(event.child_slot, event.child_slot) if event.child_slot >= 0 else -1,
            trophic_delta_raw=event.trophic_delta_raw,
            reward_raw=event.reward_raw,
        )

    def _touch_active_ages(self) -> None:
        for slot in self.slots:
            if slot.active_mask:
                slot.age_steps += 1

    def _record(self, scenario: str, event: LifecycleEvent, accepted: bool, note: str) -> None:
        self.rows.append(
            {
                "scenario": scenario,
                "mode": self.mode,
                "event_index": event.event_index,
                "event_type": event.event_type,
                "target_slot": event.target_slot,
                "parent_slot": event.parent_slot,
                "child_slot": event.child_slot,
                "trophic_delta_raw": event.trophic_delta_raw,
                "reward_raw": event.reward_raw,
                "accepted": int(accepted),
                "note": note,
                **self.summary(),
            }
        )

    def apply(self, scenario: str, event: LifecycleEvent) -> None:
        event = self._map_event_for_mode(event)
        self.attempted_event_count += 1
        self.event_count += 1
        self._touch_active_ages()

        if self.mode == "fixed_static_pool_control" and event.event_type in {
            "cleavage",
            "adult_birth",
            "death",
        }:
            self.sham_counter += 1
            self._record(scenario, event, True, "fixed-pool sham suppressed mask mutation")
            return

        if event.event_type == "trophic_update":
            self._apply_trophic_update(scenario, event)
        elif event.event_type == "cleavage":
            self._apply_child_event(scenario, event, is_adult_birth=False)
        elif event.event_type == "adult_birth":
            self._apply_child_event(scenario, event, is_adult_birth=True)
        elif event.event_type == "death":
            self._apply_death(scenario, event)
        elif event.event_type == "maturity_handoff":
            self._apply_maturity(scenario, event)
        else:
            self.invalid_event_count += 1
            self._record(scenario, event, False, "unknown event")

    def _valid_slot(self, slot_id: int) -> bool:
        return 0 <= slot_id < self.pool_size

    def _apply_trophic_update(self, scenario: str, event: LifecycleEvent) -> None:
        if not self._valid_slot(event.target_slot) or not self.slots[event.target_slot].active_mask:
            self.invalid_event_count += 1
            self.sham_counter += int(self.mode != "enabled")
            self._record(scenario, event, False, "inactive trophic target")
            return
        slot = self.slots[event.target_slot]
        if self.mode != "no_trophic_pressure_control":
            reward_component = 0 if self.mode == "no_dopamine_or_plasticity_control" else event.reward_raw // 4
            net = event.trophic_delta_raw + reward_component
            slot.trophic_health_raw = clip_raw(slot.trophic_health_raw + net)
            if net >= 0:
                slot.cyclin_d_raw = clip_raw(slot.cyclin_d_raw + net // 2)
                slot.bax_raw = max(0, slot.bax_raw - net // 4)
            else:
                slot.bax_raw = clip_raw(slot.bax_raw + (-net) // 2)
                slot.cyclin_d_raw = max(0, slot.cyclin_d_raw + net // 4)
        else:
            self.sham_counter += 1
        slot.last_event_type = EVENT_NAMES["trophic_update"]
        slot.event_count += 1
        self._record(scenario, event, True, "trophic update")

    def _apply_child_event(self, scenario: str, event: LifecycleEvent, *, is_adult_birth: bool) -> None:
        if not (
            self._valid_slot(event.parent_slot)
            and self._valid_slot(event.child_slot)
            and self.slots[event.parent_slot].active_mask
            and not self.slots[event.child_slot].active_mask
        ):
            self.invalid_event_count += 1
            self.sham_counter += int(self.mode != "enabled")
            self._record(scenario, event, False, "invalid child event")
            return
        parent = self.slots[event.parent_slot]
        child = self.slots[event.child_slot]
        child.active_mask = 1
        child.polyp_id = self.next_polyp_id
        self.next_polyp_id += 1
        if is_adult_birth:
            child.lineage_id = self.next_lineage_id
            self.next_lineage_id += 1
            self.birth_count += 1
            event_name = "adult_birth"
        else:
            child.lineage_id = parent.lineage_id
            self.cleavage_count += 1
            event_name = "cleavage"
        child.parent_slot = parent.slot_id
        child.generation = parent.generation + 1
        child.age_steps = 0
        child.trophic_health_raw = max(fp(0.25), parent.trophic_health_raw // 2)
        child.cyclin_d_raw = 0
        child.bax_raw = 0
        child.last_event_type = EVENT_NAMES[event_name]
        child.event_count = 1
        parent.trophic_health_raw = clip_raw(parent.trophic_health_raw - child.trophic_health_raw // 4)
        parent.last_event_type = EVENT_NAMES[event_name]
        parent.event_count += 1
        self._record(scenario, event, True, event_name)

    def _apply_death(self, scenario: str, event: LifecycleEvent) -> None:
        if not self._valid_slot(event.target_slot) or not self.slots[event.target_slot].active_mask:
            self.invalid_event_count += 1
            self.sham_counter += int(self.mode != "enabled")
            self._record(scenario, event, False, "invalid death")
            return
        slot = self.slots[event.target_slot]
        slot.active_mask = 0
        slot.last_event_type = EVENT_NAMES["death"]
        slot.event_count += 1
        self.death_count += 1
        self._record(scenario, event, True, "death")

    def _apply_maturity(self, scenario: str, event: LifecycleEvent) -> None:
        if not self._valid_slot(event.target_slot) or not self.slots[event.target_slot].active_mask:
            self.invalid_event_count += 1
            self.sham_counter += int(self.mode != "enabled")
            self._record(scenario, event, False, "invalid maturity")
            return
        slot = self.slots[event.target_slot]
        if self.mode != "no_trophic_pressure_control":
            slot.trophic_health_raw = clip_raw(slot.trophic_health_raw + fp(0.0625))
            slot.cyclin_d_raw = clip_raw(slot.cyclin_d_raw + fp(0.125))
            slot.bax_raw = max(0, slot.bax_raw - fp(0.03125))
        else:
            self.sham_counter += 1
        slot.last_event_type = EVENT_NAMES["maturity_handoff"]
        slot.event_count += 1
        self._record(scenario, event, True, "maturity handoff")


def choose_event(state: LifecycleReference, event_index: int) -> LifecycleEvent:
    active = state.active_slots()
    inactive = state.inactive_slots()
    kind = event_index % 8
    if kind == 0:
        return LifecycleEvent(
            event_index,
            "trophic_update",
            target_slot=active[(event_index // 8) % len(active)],
            trophic_delta_raw=fp(0.20),
            reward_raw=fp(0.10),
        )
    if kind == 1 and inactive:
        return LifecycleEvent(
            event_index,
            "cleavage",
            parent_slot=active[(event_index * 3) % len(active)],
            child_slot=inactive[0],
        )
    if kind == 2:
        return LifecycleEvent(
            event_index,
            "trophic_update",
            target_slot=active[-1],
            trophic_delta_raw=-fp(0.10),
            reward_raw=-fp(0.05),
        )
    if kind == 3:
        return LifecycleEvent(event_index, "maturity_handoff", target_slot=active[0])
    if kind == 4 and inactive and len(active) > 1:
        return LifecycleEvent(
            event_index,
            "adult_birth",
            parent_slot=active[-1],
            child_slot=inactive[0],
        )
    if kind == 5:
        return LifecycleEvent(
            event_index,
            "trophic_update",
            target_slot=active[(event_index + 1) % len(active)],
            trophic_delta_raw=fp(0.08),
            reward_raw=fp(0.02),
        )
    if kind == 6 and len(active) > 2:
        return LifecycleEvent(event_index, "death", target_slot=active[-1])
    return LifecycleEvent(
        event_index,
        "trophic_update",
        target_slot=active[(event_index * 2) % len(active)],
        trophic_delta_raw=-fp(0.04),
        reward_raw=0,
    )


def generate_schedule(num_events: int, *, seed: int = 42) -> list[LifecycleEvent]:
    state = LifecycleReference(seed=seed)
    schedule: list[LifecycleEvent] = []
    for event_index in range(num_events):
        event = choose_event(state, event_index)
        schedule.append(event)
        state.apply("schedule_generation", event)
    if state.invalid_event_count:
        raise RuntimeError("generated enabled schedule contains invalid events")
    return schedule


def run_schedule(scenario: str, schedule: list[LifecycleEvent], *, mode: str) -> LifecycleReference:
    events = list(schedule)
    if mode == "random_event_replay_control":
        rng = random.Random(4242)
        events = list(events)
        rng.shuffle(events)
        events = [
            LifecycleEvent(
                event_index=index,
                event_type=event.event_type,
                target_slot=event.target_slot,
                parent_slot=event.parent_slot,
                child_slot=event.child_slot,
                trophic_delta_raw=event.trophic_delta_raw,
                reward_raw=event.reward_raw,
            )
            for index, event in enumerate(events)
        ]
    state = LifecycleReference(mode=mode)
    for event in events:
        state.apply(scenario, event)
    return state


def scenario_result(scenario: str, event_count: int) -> dict[str, Any]:
    schedule = generate_schedule(event_count)
    mode_states = {mode: run_schedule(scenario, schedule, mode=mode) for mode in CONTROL_MODES}
    enabled = mode_states["enabled"]
    repeat = run_schedule(scenario, schedule, mode="enabled")
    summary_by_mode = {mode: state.summary() for mode, state in mode_states.items()}
    return {
        "scenario": scenario,
        "event_count": event_count,
        "schedule": schedule,
        "mode_states": mode_states,
        "summary_by_mode": summary_by_mode,
        "enabled_repeat_summary": repeat.summary(),
        "enabled_deterministic": enabled.summary() == repeat.summary(),
    }


def control_separation(summary_by_mode: dict[str, dict[str, Any]]) -> dict[str, bool]:
    enabled = summary_by_mode["enabled"]
    return {
        "fixed_static_pool_control": summary_by_mode["fixed_static_pool_control"]["active_mask_bits"]
        != enabled["active_mask_bits"],
        "random_event_replay_control": summary_by_mode["random_event_replay_control"]["lineage_checksum"]
        != enabled["lineage_checksum"],
        "active_mask_shuffle_control": summary_by_mode["active_mask_shuffle_control"]["active_mask_bits"]
        != enabled["active_mask_bits"],
        "lineage_id_shuffle_control": summary_by_mode["lineage_id_shuffle_control"]["lineage_checksum"]
        != enabled["lineage_checksum"],
        "no_trophic_pressure_control": summary_by_mode["no_trophic_pressure_control"]["trophic_checksum"]
        != enabled["trophic_checksum"],
        "no_dopamine_or_plasticity_control": summary_by_mode["no_dopamine_or_plasticity_control"]["trophic_checksum"]
        != enabled["trophic_checksum"],
    }


def build_results() -> dict[str, Any]:
    contract = load_json(CONTRACT_RESULTS)
    scenarios = [
        scenario_result("canonical_32", 32),
        scenario_result("boundary_64", 64),
    ]
    canonical = scenarios[0]
    boundary = scenarios[1]
    canonical_enabled = canonical["summary_by_mode"]["enabled"]
    boundary_enabled = boundary["summary_by_mode"]["enabled"]
    canonical_control_separation = control_separation(canonical["summary_by_mode"])
    boundary_control_separation = control_separation(boundary["summary_by_mode"])

    criteria = [
        criterion("Tier 4.30 contract passed", contract.get("status"), "== pass", contract.get("status") == "pass"),
        criterion(
            "contract criteria complete",
            f"{contract.get('criteria_passed')}/{contract.get('criteria_total')}",
            "== 14/14",
            contract.get("criteria_passed") == contract.get("criteria_total") == 14,
        ),
        criterion("canonical schedule length", len(canonical["schedule"]), "== 32", len(canonical["schedule"]) == 32),
        criterion("boundary schedule length", len(boundary["schedule"]), "== 64", len(boundary["schedule"]) == 64),
        criterion("canonical enabled invalid events", canonical_enabled["invalid_event_count"], "== 0", canonical_enabled["invalid_event_count"] == 0),
        criterion("boundary enabled invalid events", boundary_enabled["invalid_event_count"], "== 0", boundary_enabled["invalid_event_count"] == 0),
        criterion("canonical event counters match", canonical_enabled["event_count"], "== 32", canonical_enabled["event_count"] == 32),
        criterion("boundary event counters match", boundary_enabled["event_count"], "== 64", boundary_enabled["event_count"] == 64),
        criterion("canonical includes cleavage/birth/death", canonical_enabled, "all counts >= 1", canonical_enabled["cleavage_count"] >= 1 and canonical_enabled["birth_count"] >= 1 and canonical_enabled["death_count"] >= 1),
        criterion("boundary includes cleavage/birth/death", boundary_enabled, "all counts >= 1", boundary_enabled["cleavage_count"] >= 1 and boundary_enabled["birth_count"] >= 1 and boundary_enabled["death_count"] >= 1),
        criterion("canonical capacity bounded", canonical_enabled["max_active_count"], "<= 8", canonical_enabled["max_active_count"] <= 8),
        criterion("boundary capacity bounded", boundary_enabled["max_active_count"], "<= 8", boundary_enabled["max_active_count"] <= 8),
        criterion("canonical active/inactive accounting", canonical_enabled, "active+inactive==pool", canonical_enabled["active_count"] + canonical_enabled["inactive_count"] == canonical_enabled["pool_size"]),
        criterion("boundary active/inactive accounting", boundary_enabled, "active+inactive==pool", boundary_enabled["active_count"] + boundary_enabled["inactive_count"] == boundary_enabled["pool_size"]),
        criterion("canonical deterministic repeat", canonical["enabled_deterministic"], "== true", canonical["enabled_deterministic"]),
        criterion("boundary deterministic repeat", boundary["enabled_deterministic"], "== true", boundary["enabled_deterministic"]),
        criterion("canonical controls separated", canonical_control_separation, "all true", all(canonical_control_separation.values())),
        criterion("boundary controls separated", boundary_control_separation, "all true", all(boundary_control_separation.values())),
        criterion("all modes preserve event budget canonical", {mode: s["event_count"] for mode, s in canonical["summary_by_mode"].items()}, "all == 32", all(s["event_count"] == 32 for s in canonical["summary_by_mode"].values())),
        criterion("all modes preserve event budget boundary", {mode: s["event_count"] for mode, s in boundary["summary_by_mode"].items()}, "all == 64", all(s["event_count"] == 64 for s in boundary["summary_by_mode"].values())),
    ]
    failed = [item for item in criteria if not item.passed]

    return {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if not failed else "fail",
        "mode": "local-reference",
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "criteria": criteria,
        "failed_criteria": failed,
        "source_inputs": {
            "contract_results": str(CONTRACT_RESULTS),
        },
        "scenarios": [
            {
                "scenario": scenario["scenario"],
                "event_count": scenario["event_count"],
                "summary_by_mode": scenario["summary_by_mode"],
                "enabled_repeat_summary": scenario["enabled_repeat_summary"],
                "enabled_deterministic": scenario["enabled_deterministic"],
                "control_separation": control_separation(scenario["summary_by_mode"]),
            }
            for scenario in scenarios
        ],
        "claim_boundary": (
            "Tier 4.30a is a local deterministic reference only. It proves the "
            "static-pool lifecycle state model is explicit, bounded, repeatable, "
            "and has precomputed sham-control outputs. It does not implement C "
            "runtime lifecycle state, does not run hardware, does not prove task "
            "benefit, does not freeze a lifecycle baseline, and does not migrate "
            "v2.2 temporal state."
        ),
        "next_step": "Tier 4.30b source audit / single-core lifecycle mask smoke preparation",
        "_scenario_objects": scenarios,
    }


def flatten_event_rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in results["_scenario_objects"]:
        for mode, state in scenario["mode_states"].items():
            rows.extend(state.rows)
    return rows


def flatten_final_state_rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in results["_scenario_objects"]:
        for mode, state in scenario["mode_states"].items():
            rows.extend(state.final_state_rows(scenario["scenario"]))
    return rows


def control_summary_rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in results["scenarios"]:
        enabled = scenario["summary_by_mode"]["enabled"]
        for mode, summary in scenario["summary_by_mode"].items():
            row = {
                "scenario": scenario["scenario"],
                "mode": mode,
                **summary,
                "active_mask_differs_from_enabled": summary["active_mask_bits"] != enabled["active_mask_bits"],
                "lineage_checksum_differs_from_enabled": summary["lineage_checksum"] != enabled["lineage_checksum"],
                "trophic_checksum_differs_from_enabled": summary["trophic_checksum"] != enabled["trophic_checksum"],
            }
            rows.append(row)
    return rows


def write_report(path: Path, results: dict[str, Any]) -> None:
    safe = json_safe({key: value for key, value in results.items() if key != "_scenario_objects"})
    lines = [
        "# Tier 4.30a Local Static-Pool Lifecycle Reference",
        "",
        f"- Generated: `{safe['generated_at_utc']}`",
        f"- Runner revision: `{safe['runner_revision']}`",
        f"- Status: **{safe['status'].upper()}**",
        f"- Criteria: `{safe['criteria_passed']}/{safe['criteria_total']}`",
        "",
        "## Claim Boundary",
        "",
        safe["claim_boundary"],
        "",
        "## Scenario Summaries",
        "",
    ]
    for scenario in safe["scenarios"]:
        lines.append(f"### {scenario['scenario']}")
        lines.append("")
        lines.append("| Mode | Events | Invalid | Active Mask | Active | Cleavage | Birth | Death | Lineage Checksum | Trophic Checksum |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for mode in CONTROL_MODES:
            summary = scenario["summary_by_mode"][mode]
            lines.append(
                f"| `{mode}` | `{summary['event_count']}` | `{summary['invalid_event_count']}` | `{summary['active_mask_bits']}` | `{summary['active_count']}` | `{summary['cleavage_count']}` | `{summary['birth_count']}` | `{summary['death_count']}` | `{summary['lineage_checksum']}` | `{summary['trophic_checksum']}` |"
            )
        lines.append("")
        lines.append(f"- Deterministic repeat: `{scenario['enabled_deterministic']}`")
        lines.append(f"- Control separation: `{scenario['control_separation']}`")
        lines.append("")
    lines.extend(["## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in safe["criteria"]:
        lines.append(
            f"| {item['name']} | `{item['value']}` | `{item['rule']}` | {'yes' if item['passed'] else 'no'} | {item.get('note', '')} |"
        )
    lines.extend(["", "## Next Step", "", safe["next_step"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    results = build_results()
    event_rows = flatten_event_rows(results)
    final_rows = flatten_final_state_rows(results)
    control_rows = control_summary_rows(results)
    serializable = {key: value for key, value in results.items() if key != "_scenario_objects"}
    serializable["output_dir"] = str(output_dir)

    write_json(output_dir / "tier4_30a_results.json", serializable)
    write_report(output_dir / "tier4_30a_report.md", results | {"output_dir": str(output_dir)})
    write_csv(output_dir / "tier4_30a_event_trace.csv", event_rows)
    write_csv(output_dir / "tier4_30a_final_state.csv", final_rows)
    write_csv(output_dir / "tier4_30a_control_summary.csv", control_rows)
    write_json(
        CONTROLLED / "tier4_30a_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": serializable["generated_at_utc"],
            "status": serializable["status"],
            "manifest": str(output_dir / "tier4_30a_results.json"),
            "output_dir": str(output_dir),
        },
    )
    return serializable


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
                "next": results["next_step"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if results["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
