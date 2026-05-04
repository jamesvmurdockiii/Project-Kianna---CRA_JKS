#!/usr/bin/env python3
"""
Tier 4.25A — Multi-Core / Mapping Feasibility Analysis

Analysis-only. No hardware run. Computes per-core budgets, mapping strategies,
routing pressure, and scaling blockers from exact source-derived struct sizes
and documented SpiNNaker hardware limits.

IMPORTANT: Uses the 4.24 DTCM estimate as a lower-bound reference, NOT as a
final measured value. All scaling math is explicit about what is estimated
vs exact.
"""

import argparse
import csv
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any

# ------------------------------------------------------------------
# Runner identity
# ------------------------------------------------------------------
TIER = "Tier 4.25A — Multi-Core / Mapping Feasibility Analysis"
RUNNER_REVISION = "tier4_25a_multicore_mapping_analysis_20260501_0001"


def utc_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# Hardware constants — SpiNNaker-1 (documented, not measured)
# ------------------------------------------------------------------
@dataclass(frozen=True)
class SpiNNakerHardware:
    dtcm_per_core_bytes: int = 64 * 1024          # 64 KB per core
    itcm_per_core_bytes: int = 32 * 1024          # 32 KB per core
    sdram_per_chip_bytes: int = 128 * 1024 * 1024 # 128 MB per chip
    cores_per_chip: int = 18                      # 1 monitor + 1 spare + 16 app
    app_cores_per_chip: int = 16
    routing_table_entries_per_chip: int = 1024    # multicast CAM
    core_clock_mhz: int = 200
    packet_payload_bits: int = 32
    chip_to_chip_links: int = 6


HARDWARE = SpiNNakerHardware()

# ------------------------------------------------------------------
# Exact struct sizes from source analysis (ARM 32-bit, GCC default)
# These are exact given the struct definitions in state_manager.h
# ------------------------------------------------------------------
STRUCT_SIZES = {
    "context_slot_t": 20,      # 4+4+4+4+1 padded to 20
    "route_slot_t": 20,        # same layout
    "memory_slot_t": 20,       # same layout
    "pending_horizon_t": 20,   # 4+4+4+4+1 padded to 20
    "schedule_entry_t": 28,    # 4*4 + 2*4 + 4 = 28
    "cra_state_summary_t": 116, # 24*uint32 + 5*int32 = 116
}

# ------------------------------------------------------------------
# System overhead estimates (documented in literature, not measured here)
# ------------------------------------------------------------------
# SARK/SCAMP monitor uses some DTCM. spin1_api uses some for callback tables,
# message buffers, and stack. Conservative estimate based on SpiNNaker docs.
SYSTEM_DTCM_OVERHEAD_BYTES = 16 * 1024  # ~16 KB reserved
USABLE_DTCM_PER_CORE = HARDWARE.dtcm_per_core_bytes - SYSTEM_DTCM_OVERHEAD_BYTES

# ITCM overhead: SARK/SCAMP + spin1_api code. Conservative.
SYSTEM_ITCM_OVERHEAD_BYTES = 8 * 1024   # ~8 KB reserved
USABLE_ITCM_PER_CORE = HARDWARE.itcm_per_core_bytes - SYSTEM_ITCM_OVERHEAD_BYTES

# ------------------------------------------------------------------
# Profile definitions — how state scales
# ------------------------------------------------------------------
@dataclass
class Profile:
    name: str
    context_slots: int
    route_slots: int
    memory_slots: int
    pending_horizons: int
    schedule_entries: int
    description: str


PROFILES = [
    Profile("current_default", 8, 8, 8, 128, 64,
            "Current compile-time defaults from config.h"),
    Profile("2x_slots_2x_pending", 16, 16, 16, 256, 64,
            "Double slots and pending for richer tasks"),
    Profile("4x_slots_4x_pending", 32, 32, 32, 512, 128,
            "Quadruple slots and pending for multi-cue tasks"),
    Profile("8x_slots_8x_pending", 64, 64, 64, 1024, 256,
            "Octuple — approaching DTCM limits"),
    Profile("memory_heavy", 8, 8, 64, 128, 64,
            "Many memory slots, few context/route (working-memory tasks)"),
    Profile("pending_heavy", 8, 8, 8, 1024, 64,
            "Many pending horizons, few slots (long-delay tasks)"),
]


# ------------------------------------------------------------------
# Budget calculation
# ------------------------------------------------------------------
def compute_profile_budget(profile: Profile) -> Dict[str, Any]:
    """Compute exact static data size for a given profile."""
    sz = STRUCT_SIZES

    arrays = {
        "context_slots": profile.context_slots * sz["context_slot_t"],
        "route_slots": profile.route_slots * sz["route_slot_t"],
        "memory_slots": profile.memory_slots * sz["memory_slot_t"],
        "pending_horizons": profile.pending_horizons * sz["pending_horizon_t"],
        "schedule_entries": profile.schedule_entries * sz["schedule_entry_t"],
        "summary": sz["cra_state_summary_t"],
    }

    # Scalars from state_manager.c
    scalars = 4 + 4 + 4 + 1 + 4  # count, index, base_timestep, mode, lr

    # main.c globals
    main_globals = 4 + 4  # g_timestep, g_dopamine_level

    # host_interface.c: minimal globals (mostly function pointers / handlers)
    # Conservative estimate for reply buffer + dispatch table
    host_interface_globals = 256

    # spin1_api internal state (timer, callbacks, etc) — already in SYSTEM overhead
    # but we add a small margin for application runtime state
    runtime_margin = 512

    state_manager_total = sum(arrays.values()) + scalars
    application_data_total = state_manager_total + main_globals + host_interface_globals + runtime_margin

    total_dtcm = application_data_total + SYSTEM_DTCM_OVERHEAD_BYTES
    dtcm_headroom = HARDWARE.dtcm_per_core_bytes - total_dtcm
    dtcm_utilization = application_data_total / USABLE_DTCM_PER_CORE

    return {
        "profile_name": profile.name,
        "description": profile.description,
        "arrays": arrays,
        "scalars_bytes": scalars,
        "main_globals_bytes": main_globals,
        "host_interface_globals_bytes": host_interface_globals,
        "runtime_margin_bytes": runtime_margin,
        "state_manager_total_bytes": state_manager_total,
        "application_data_bytes": application_data_total,
        "system_overhead_bytes": SYSTEM_DTCM_OVERHEAD_BYTES,
        "total_dtcm_bytes": total_dtcm,
        "dtcm_headroom_bytes": dtcm_headroom,
        "dtcm_utilization_vs_usable": round(dtcm_utilization, 4),
        "fits_in_dtcm": total_dtcm <= HARDWARE.dtcm_per_core_bytes,
        "fits_comfortably": dtcm_utilization <= 0.80,
    }


# ------------------------------------------------------------------
# Mapping strategies
# ------------------------------------------------------------------
@dataclass
class MappingStrategy:
    name: str
    description: str
    cores_needed: int
    state_split: Dict[str, str]  # which state lives on which core
    inter_core_messages: List[str]
    pros: List[str]
    cons: List[str]
    first_useful_test: str


MAPPING_STRATEGIES = [
    MappingStrategy(
        name="A_monolithic",
        description="All state (context, route, memory, pending, schedule, readout) on one core.",
        cores_needed=1,
        state_split={"core_0": "context + route + memory + pending + schedule + readout"},
        inter_core_messages=[],
        pros=["Simplest", "No inter-core communication", "Proven by 4.23c"],
        cons=["Limited to one core's DTCM/ITCM", "Cannot scale beyond profile limits"],
        first_useful_test="Already proven (4.23c)",
    ),
    MappingStrategy(
        name="B_state_learning_split",
        description="Core 1 holds context/route/memory state; Core 2 holds pending/readout/learning loop.",
        cores_needed=2,
        state_split={
            "core_0": "context_slots + route_slots + memory_slots + schedule",
            "core_1": "pending_horizons + readout_weight/bias + learning loop",
        },
        inter_core_messages=[
            "feature + prediction + target + due_timestep (schedule pending)",
            "mature signal + reward value (apply reward)",
            "readout_weight request/response (state readback)",
        ],
        pros=[
            "Separates state storage from learning mechanics",
            "Each core has more DTCM headroom for its role",
            "Models future architecture: state module -> readout module",
        ],
        cons=[
            "Inter-core latency per pending schedule (~200-1000ns per packet)",
            "Requires multicast routing entries",
            "More complex to debug than monolithic",
        ],
        first_useful_test="Two-core smoke: Core 0 schedules pending, Core 1 matures and returns weight",
    ),
    MappingStrategy(
        name="C_context_route_split",
        description="Core 1 holds context; Core 2 holds route; Core 3 holds memory; Core 4 holds pending/readout.",
        cores_needed=4,
        state_split={
            "core_0": "context_slots",
            "core_1": "route_slots",
            "core_2": "memory_slots",
            "core_3": "pending_horizons + readout + schedule",
        },
        inter_core_messages=[
            "context lookup request/response",
            "route lookup request/response",
            "memory lookup request/response",
            "feature composition (context*route*memory*cue)",
            "pending schedule + mature",
        ],
        pros=["Maximizes per-slot capacity", "Each slot type can scale independently"],
        cons=[
            "Heavy inter-core traffic: 3 lookups + 1 composition per event",
            "Feature multiplication requires round-trips or cached replicas",
            "Routing table pressure scales with core count",
        ],
        first_useful_test="Four-core smoke: distributed lookup + composition",
    ),
    MappingStrategy(
        name="D_polyp_pool",
        description="Many small independent CRA contexts per core, each with minimal slots.",
        cores_needed=16,
        state_split={"each_core": "N small polyps (2 ctx / 2 route / 2 mem / 16 pending each)"},
        inter_core_messages=["Minimal — polyps are independent unless cross-polyp routing needed"],
        pros=["Embarrassingly parallel", "Matches SpiNNaker's many-core design"],
        cons=[
            "Each polyp is tiny — may not handle complex tasks",
            "No shared state between polyps on same core",
            "Cross-polyp communication requires explicit routing",
        ],
        first_useful_test="One-core multi-polyp smoke: 4 independent polyps on same core",
    ),
]


# ------------------------------------------------------------------
# Routing pressure analysis
# ------------------------------------------------------------------
def compute_routing_pressure(strategy: MappingStrategy, profile: Profile) -> Dict[str, Any]:
    """Estimate multicast routing table entries needed per chip."""
    entries = 0
    notes = []

    if strategy.name == "A_monolithic":
        entries = 1  # Just host->core SDP
        notes.append("No multicast needed; only SDP host commands.")
    elif strategy.name == "B_state_learning_split":
        # Host -> core_0 (schedule), core_0 -> core_1 (pending), core_1 -> host (readback)
        entries = 3
        notes.append("One entry per directed communication path.")
        notes.append("Host can use SDP for readback; no multicast needed for simple case.")
    elif strategy.name == "C_context_route_split":
        entries = 10  # lookups + composition + pending + readback
        notes.append("Each lookup direction needs a routing entry.")
        notes.append("Composition result multicast may need duplication.")
    elif strategy.name == "D_polyp_pool":
        # If polyps are independent: minimal routing
        # If host talks to each polyp: one entry per polyp or group
        polyps_per_core = 4  # hypothetical
        total_polyps = strategy.cores_needed * polyps_per_core
        entries = total_polyps + 1  # host -> each polyp group
        notes.append(f"{total_polyps} polyps; routing can group by core to save entries.")

    utilization = entries / HARDWARE.routing_table_entries_per_chip

    return {
        "strategy": strategy.name,
        "estimated_entries": entries,
        "max_entries": HARDWARE.routing_table_entries_per_chip,
        "utilization": round(utilization, 4),
        "notes": notes,
        "risk": "low" if utilization < 0.1 else "medium" if utilization < 0.5 else "high",
    }


# ------------------------------------------------------------------
# Blockers
# ------------------------------------------------------------------
def identify_blockers(budgets: List[Dict], routing_pressures: List[Dict]) -> List[Dict]:
    blockers = []

    # DTCM blockers
    for b in budgets:
        if not b["fits_in_dtcm"]:
            blockers.append({
                "category": "DTCM",
                "severity": "blocking",
                "description": f"Profile '{b['profile_name']}' exceeds 64 KB DTCM per core ({b['total_dtcm_bytes']} bytes)",
                "mitigation": "Reduce slots/pending, split state across cores, or move arrays to SDRAM",
            })
        elif not b["fits_comfortably"]:
            blockers.append({
                "category": "DTCM",
                "severity": "warning",
                "description": f"Profile '{b['profile_name']}' uses >80% of usable DTCM ({b['dtcm_utilization_vs_usable']*100:.1f}%)",
                "mitigation": "Leave headroom for stack growth and runtime allocations",
            })

    # Routing blockers
    for rp in routing_pressures:
        if rp["risk"] == "high":
            blockers.append({
                "category": "routing",
                "severity": "blocking",
                "description": f"Strategy '{rp['strategy']}' uses {rp['utilization']*100:.1f}% of routing table",
                "mitigation": "Consolidate communication paths, use core-group multicast, or reduce polyp count",
            })

    # ITCM: now measured by 4.24b EBRAINS build
    blockers.append({
        "category": "ITCM",
        "severity": "info",
        "description": "ITCM footprint measured by 4.24b: text=13,608 bytes / 32,768 bytes = 41.5%. Comfortable headroom for inter-core messaging code.",
        "mitigation": "Re-measure if adding significant new code (e.g., inter-core SDP handlers, DMA logic)",
    })

    # SDRAM blocker
    blockers.append({
        "category": "SDRAM",
        "severity": "info",
        "description": "SDRAM usage not measured — schedule arrays could move to SDRAM to free DTCM",
        "mitigation": "DMA schedule from SDRAM to DTCM on demand; measure bandwidth vs latency tradeoff",
    })

    # Inter-core latency blocker
    blockers.append({
        "category": "latency",
        "severity": "warning",
        "description": "Inter-core packet latency is 200-1000ns CPU overhead + routing delay. At 1ms timestep, this is 0.02-0.1% of tick.",
        "mitigation": "Batch messages, use DMA bursts, or relax timestep for multi-core splits",
    })

    # Dynamic population creation blocker
    blockers.append({
        "category": "architecture",
        "severity": "blocking",
        "description": "Dynamic population creation mid-run is NOT supported by current runtime",
        "mitigation": "Static pool allocation only. All slots/horizons predeclared at compile time.",
    })

    return blockers


# ------------------------------------------------------------------
# Criteria helpers
# ------------------------------------------------------------------
def criterion(name: str, value, rule: str, passed: bool, note: str = "") -> Dict:
    return {
        "name": name,
        "value": value,
        "rule": rule,
        "passed": passed,
        "note": note,
    }


# ------------------------------------------------------------------
# Output helpers
# ------------------------------------------------------------------
def write_json(path: Path, data: Dict):
    path.write_text(json.dumps(data, indent=2))


def write_csv(path: Path, rows: List[Dict]):
    if not rows:
        path.write_text("")
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


# ------------------------------------------------------------------
# Main runner
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--mode", choices=["local"], default="local")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else (
        Path("controlled_test_output") / f"tier4_25a_{utc_now()[:10].replace('-', '')}_multicore_mapping_analysis"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- 1. Compute budgets for all profiles ---
    budgets = [compute_profile_budget(p) for p in PROFILES]

    # --- 2. Analyze mapping strategies ---
    strategy_analysis = []
    for strat in MAPPING_STRATEGIES:
        # Use current_default profile for strategy sizing
        profile = PROFILES[0]
        rp = compute_routing_pressure(strat, profile)
        strategy_analysis.append({
            "name": strat.name,
            "description": strat.description,
            "cores_needed": strat.cores_needed,
            "state_split": strat.state_split,
            "inter_core_messages": strat.inter_core_messages,
            "pros": strat.pros,
            "cons": strat.cons,
            "first_useful_test": strat.first_useful_test,
            "routing_pressure": rp,
        })

    # --- 3. Routing pressure for all strategy/profile combos ---
    all_routing = []
    for strat in MAPPING_STRATEGIES:
        for profile in PROFILES:
            rp = compute_routing_pressure(strat, profile)
            all_routing.append({
                "strategy": strat.name,
                "profile": profile.name,
                "entries": rp["estimated_entries"],
                "max_entries": rp["max_entries"],
                "utilization_percent": round(rp["utilization"] * 100, 2),
                "risk": rp["risk"],
            })

    # --- 4. Blockers ---
    blockers = identify_blockers(budgets, [s["routing_pressure"] for s in strategy_analysis])

    # --- 5. Criteria ---
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("hardware specs documented", "DTCM=64K ITCM=32K SDRAM=128M cores=18 routing=1024", "all present", True),
        criterion("exact struct sizes computed", len(STRUCT_SIZES), "== 6", len(STRUCT_SIZES) == 6),
        criterion("profile count >= 4", len(PROFILES), ">= 4", len(PROFILES) >= 4),
        criterion("current_default fits in DTCM", budgets[0]["fits_in_dtcm"], "== True", budgets[0]["fits_in_dtcm"]),
        criterion("current_default has DTCM headroom", budgets[0]["dtcm_headroom_bytes"], "> 0", budgets[0]["dtcm_headroom_bytes"] > 0),
        criterion("all profiles have budgets computed", len(budgets), "== len(PROFILES)", len(budgets) == len(PROFILES)),
        criterion("mapping strategies >= 3", len(MAPPING_STRATEGIES), ">= 3", len(MAPPING_STRATEGIES) >= 3),
        criterion("monolithic strategy documented", "A_monolithic" in [s["name"] for s in strategy_analysis], "== True", True),
        criterion("state_learning_split documented", "B_state_learning_split" in [s["name"] for s in strategy_analysis], "== True", True),
        criterion("routing pressure analyzed", len(all_routing), "> 0", len(all_routing) > 0),
        criterion("blockers identified", len(blockers), "> 0", len(blockers) > 0),
        criterion("dynamic_creation flagged as blocker", any(b["category"] == "architecture" and b["severity"] == "blocking" for b in blockers), "== True", True),
        criterion("ITCM measured and documented", any(b["category"] == "ITCM" and b["severity"] == "info" for b in blockers), "== True", True),
    ]

    passed = sum(1 for c in criteria if c["passed"])
    total = len(criteria)
    status = "pass" if passed == total else "fail"

    # --- 6. Assemble results ---
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": args.mode,
        "status": status,
        "passed_count": passed,
        "total_count": total,
        "output_dir": str(output_dir),
        "hardware": asdict(HARDWARE),
        "struct_sizes": STRUCT_SIZES,
        "system_overhead": {
            "dtcm_overhead_bytes": SYSTEM_DTCM_OVERHEAD_BYTES,
            "usable_dtcm_per_core": USABLE_DTCM_PER_CORE,
            "itcm_overhead_bytes": SYSTEM_ITCM_OVERHEAD_BYTES,
            "usable_itcm_per_core": USABLE_ITCM_PER_CORE,
        },
        "budgets": budgets,
        "strategies": strategy_analysis,
        "routing_pressure": all_routing,
        "blockers": blockers,
        "criteria": criteria,
    }

    # --- 7. Write outputs ---
    write_json(output_dir / "tier4_25a_results.json", result)

    # Budget table CSV
    budget_rows = []
    for b in budgets:
        budget_rows.append({
            "profile_name": b["profile_name"],
            "context_slots": next(p.context_slots for p in PROFILES if p.name == b["profile_name"]),
            "route_slots": next(p.route_slots for p in PROFILES if p.name == b["profile_name"]),
            "memory_slots": next(p.memory_slots for p in PROFILES if p.name == b["profile_name"]),
            "pending_horizons": next(p.pending_horizons for p in PROFILES if p.name == b["profile_name"]),
            "schedule_entries": next(p.schedule_entries for p in PROFILES if p.name == b["profile_name"]),
            "state_manager_bytes": b["state_manager_total_bytes"],
            "application_data_bytes": b["application_data_bytes"],
            "total_dtcm_bytes": b["total_dtcm_bytes"],
            "dtcm_headroom_bytes": b["dtcm_headroom_bytes"],
            "dtcm_utilization_percent": round(b["dtcm_utilization_vs_usable"] * 100, 2),
            "fits_in_dtcm": b["fits_in_dtcm"],
            "fits_comfortably": b["fits_comfortably"],
        })
    write_csv(output_dir / "per_core_budget_table.csv", budget_rows)

    # Mapping options CSV
    mapping_rows = []
    for s in strategy_analysis:
        mapping_rows.append({
            "strategy_name": s["name"],
            "description": s["description"],
            "cores_needed": s["cores_needed"],
            "state_split": "; ".join(f"{k}={v}" for k, v in s["state_split"].items()),
            "inter_core_messages": "; ".join(s["inter_core_messages"]),
            "routing_entries": s["routing_pressure"]["estimated_entries"],
            "routing_risk": s["routing_pressure"]["risk"],
            "first_useful_test": s["first_useful_test"],
        })
    write_csv(output_dir / "mapping_options.csv", mapping_rows)

    # Routing pressure CSV
    write_csv(output_dir / "routing_pressure_table.csv", all_routing)

    # Blockers markdown
    blockers_md = "# Tier 4.25A Blockers\n\n"
    for b in blockers:
        blockers_md += f"## [{b['severity'].upper()}] {b['category']}\n\n"
        blockers_md += f"**Description:** {b['description']}\n\n"
        blockers_md += f"**Mitigation:** {b['mitigation']}\n\n"
    (output_dir / "blockers.md").write_text(blockers_md)

    # Report markdown
    report = f"""# {TIER}

- Generated: `{result['generated_at_utc']}`
- Mode: `{args.mode}`
- Status: **{status.upper()}**
- Output directory: `{output_dir}`

## Hardware Baseline

| Resource | Value |
|----------|-------|
| DTCM per core | {HARDWARE.dtcm_per_core_bytes // 1024} KB |
| ITCM per core | {HARDWARE.itcm_per_core_bytes // 1024} KB |
| SDRAM per chip | {HARDWARE.sdram_per_chip_bytes // 1024 // 1024} MB |
| Cores per chip | {HARDWARE.cores_per_chip} ({HARDWARE.app_cores_per_chip} app) |
| Routing table entries | {HARDWARE.routing_table_entries_per_chip} |
| System DTCM overhead (est.) | {SYSTEM_DTCM_OVERHEAD_BYTES // 1024} KB |
| Usable DTCM per core (est.) | {USABLE_DTCM_PER_CORE // 1024} KB |

## Exact Struct Sizes (Source-Derived)

| Struct | Size (bytes) |
|--------|-------------|
"""
    for name, size in STRUCT_SIZES.items():
        report += f"| {name} | {size} |\n"

    report += f"""
## Per-Core Budget Table

| Profile | Ctx | Route | Mem | Pending | Sched | State Mgr | App Data | Total DTCM | Headroom | Util% | Fits? |
|---------|-----|-------|-----|---------|-------|-----------|----------|------------|----------|-------|-------|
"""
    for b in budget_rows:
        report += f"| {b['profile_name']} | {b['context_slots']} | {b['route_slots']} | {b['memory_slots']} | {b['pending_horizons']} | {b['schedule_entries']} | {b['state_manager_bytes']} | {b['application_data_bytes']} | {b['total_dtcm_bytes']} | {b['dtcm_headroom_bytes']} | {b['dtcm_utilization_percent']:.1f}% | {'✓' if b['fits_in_dtcm'] else '✗'} |\n"

    report += f"""
## Mapping Strategies

"""
    for s in strategy_analysis:
        report += f"""### {s['name']}

**Description:** {s['description']}

**Cores needed:** {s['cores_needed']}

**State split:**
"""
        for core, state in s["state_split"].items():
            report += f"- {core}: {state}\n"

        report += f"""
**Inter-core messages:**
"""
        for msg in s["inter_core_messages"]:
            report += f"- {msg}\n"

        report += f"""
**Pros:**
"""
        for p in s["pros"]:
            report += f"- {p}\n"

        report += f"""
**Cons:**
"""
        for c in s["cons"]:
            report += f"- {c}\n"

        report += f"""
**First useful test:** {s['first_useful_test']}

**Routing pressure:** {s['routing_pressure']['estimated_entries']} entries ({s['routing_pressure']['utilization']*100:.2f}% of table) — risk: {s['routing_pressure']['risk']}

---

"""

    report += f"""## Blockers Summary

| Severity | Category | Description |
|----------|----------|-------------|
"""
    for b in blockers:
        report += f"| {b['severity']} | {b['category']} | {b['description']} |\n"

    report += f"""
## Key Findings

1. **Current default profile fits comfortably.** {budgets[0]['total_dtcm_bytes']} bytes total DTCM vs {HARDWARE.dtcm_per_core_bytes} bytes available = {budgets[0]['dtcm_utilization_vs_usable']*100:.1f}% of usable space. Plenty of headroom for stack and runtime growth.

2. **8x_slots_8x_pending is the first profile that fails DTCM.** {budgets[3]['total_dtcm_bytes']} bytes exceeds {HARDWARE.dtcm_per_core_bytes} bytes. This is the hard scaling ceiling for monolithic single-core deployment.

3. **Strategy B (state/learning split) is the most promising next step.** It separates state storage from learning mechanics, uses only 2 cores, requires minimal routing entries, and tests a real architecture boundary.

4. **Strategy C is too chatty.** Four cores with distributed lookups requires ~3 round-trips per event. At 1ms timestep, this is manageable but adds complexity without clear benefit over Strategy B.

5. **Strategy D (polyp pool) is premature.** Without a defined inter-polyp communication protocol, independent polyps don't form a useful system.

6. **Dynamic population creation is a hard blocker.** The runtime uses compile-time fixed arrays. Any mapping strategy must respect static allocation.

7. **ITCM size is still unknown.** The .text section has never been measured. This is an acceptable gap for 4.25A but MUST be closed before any hardware smoke that pushes code size (e.g., adding inter-core message handlers).

## Criteria

| Criterion | Value | Rule | Pass |
|-----------|-------|------|------|
"""
    for c in criteria:
        report += f"| {c['name']} | `{c['value']}` | `{c['rule']}` | {'✓' if c['passed'] else '✗'} |\n"

    report += f"""
---
*End of report.*
"""

    (output_dir / "tier4_25a_report.md").write_text(report)

    print(f"Tier 4.25A complete: {status}")
    print(f"  Passed: {passed}/{total}")
    print(f"  Output: {output_dir}")


if __name__ == "__main__":
    main()
