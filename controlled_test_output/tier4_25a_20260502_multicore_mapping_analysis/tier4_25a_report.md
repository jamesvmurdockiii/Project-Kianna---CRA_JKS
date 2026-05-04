# Tier 4.25A — Multi-Core / Mapping Feasibility Analysis

- Generated: `2026-05-02T03:34:53.721897+00:00`
- Mode: `local`
- Status: **PASS**
- Output directory: `controlled_test_output/tier4_25a_20260502_multicore_mapping_analysis`

## Hardware Baseline

| Resource | Value |
|----------|-------|
| DTCM per core | 64 KB |
| ITCM per core | 32 KB |
| SDRAM per chip | 128 MB |
| Cores per chip | 18 (16 app) |
| Routing table entries | 1024 |
| System DTCM overhead (est.) | 16 KB |
| Usable DTCM per core (est.) | 48 KB |

## Exact Struct Sizes (Source-Derived)

| Struct | Size (bytes) |
|--------|-------------|
| context_slot_t | 20 |
| route_slot_t | 20 |
| memory_slot_t | 20 |
| pending_horizon_t | 20 |
| schedule_entry_t | 28 |
| cra_state_summary_t | 116 |

## Per-Core Budget Table

| Profile | Ctx | Route | Mem | Pending | Sched | State Mgr | App Data | Total DTCM | Headroom | Util% | Fits? |
|---------|-----|-------|-----|---------|-------|-----------|----------|------------|----------|-------|-------|
| current_default | 8 | 8 | 8 | 128 | 64 | 4965 | 5741 | 22125 | 43411 | 11.7% | ✓ |
| 2x_slots_2x_pending | 16 | 16 | 16 | 256 | 64 | 8005 | 8781 | 25165 | 40371 | 17.9% | ✓ |
| 4x_slots_4x_pending | 32 | 32 | 32 | 512 | 128 | 15877 | 16653 | 33037 | 32499 | 33.9% | ✓ |
| 8x_slots_8x_pending | 64 | 64 | 64 | 1024 | 256 | 31621 | 32397 | 48781 | 16755 | 65.9% | ✓ |
| memory_heavy | 8 | 8 | 64 | 128 | 64 | 6085 | 6861 | 23245 | 42291 | 14.0% | ✓ |
| pending_heavy | 8 | 8 | 8 | 1024 | 64 | 22885 | 23661 | 40045 | 25491 | 48.1% | ✓ |

## Mapping Strategies

### A_monolithic

**Description:** All state (context, route, memory, pending, schedule, readout) on one core.

**Cores needed:** 1

**State split:**
- core_0: context + route + memory + pending + schedule + readout

**Inter-core messages:**

**Pros:**
- Simplest
- No inter-core communication
- Proven by 4.23c

**Cons:**
- Limited to one core's DTCM/ITCM
- Cannot scale beyond profile limits

**First useful test:** Already proven (4.23c)

**Routing pressure:** 1 entries (0.10% of table) — risk: low

---

### B_state_learning_split

**Description:** Core 1 holds context/route/memory state; Core 2 holds pending/readout/learning loop.

**Cores needed:** 2

**State split:**
- core_0: context_slots + route_slots + memory_slots + schedule
- core_1: pending_horizons + readout_weight/bias + learning loop

**Inter-core messages:**
- feature + prediction + target + due_timestep (schedule pending)
- mature signal + reward value (apply reward)
- readout_weight request/response (state readback)

**Pros:**
- Separates state storage from learning mechanics
- Each core has more DTCM headroom for its role
- Models future architecture: state module -> readout module

**Cons:**
- Inter-core latency per pending schedule (~200-1000ns per packet)
- Requires multicast routing entries
- More complex to debug than monolithic

**First useful test:** Two-core smoke: Core 0 schedules pending, Core 1 matures and returns weight

**Routing pressure:** 3 entries (0.29% of table) — risk: low

---

### C_context_route_split

**Description:** Core 1 holds context; Core 2 holds route; Core 3 holds memory; Core 4 holds pending/readout.

**Cores needed:** 4

**State split:**
- core_0: context_slots
- core_1: route_slots
- core_2: memory_slots
- core_3: pending_horizons + readout + schedule

**Inter-core messages:**
- context lookup request/response
- route lookup request/response
- memory lookup request/response
- feature composition (context*route*memory*cue)
- pending schedule + mature

**Pros:**
- Maximizes per-slot capacity
- Each slot type can scale independently

**Cons:**
- Heavy inter-core traffic: 3 lookups + 1 composition per event
- Feature multiplication requires round-trips or cached replicas
- Routing table pressure scales with core count

**First useful test:** Four-core smoke: distributed lookup + composition

**Routing pressure:** 10 entries (0.98% of table) — risk: low

---

### D_polyp_pool

**Description:** Many small independent CRA contexts per core, each with minimal slots.

**Cores needed:** 16

**State split:**
- each_core: N small polyps (2 ctx / 2 route / 2 mem / 16 pending each)

**Inter-core messages:**
- Minimal — polyps are independent unless cross-polyp routing needed

**Pros:**
- Embarrassingly parallel
- Matches SpiNNaker's many-core design

**Cons:**
- Each polyp is tiny — may not handle complex tasks
- No shared state between polyps on same core
- Cross-polyp communication requires explicit routing

**First useful test:** One-core multi-polyp smoke: 4 independent polyps on same core

**Routing pressure:** 65 entries (6.35% of table) — risk: low

---

## Blockers Summary

| Severity | Category | Description |
|----------|----------|-------------|
| info | ITCM | ITCM footprint measured by 4.24b: text=13,608 bytes / 32,768 bytes = 41.5%. Comfortable headroom for inter-core messaging code. |
| info | SDRAM | SDRAM usage not measured — schedule arrays could move to SDRAM to free DTCM |
| warning | latency | Inter-core packet latency is 200-1000ns CPU overhead + routing delay. At 1ms timestep, this is 0.02-0.1% of tick. |
| blocking | architecture | Dynamic population creation mid-run is NOT supported by current runtime |

## Key Findings

1. **Current default profile fits comfortably.** 22125 bytes total DTCM vs 65536 bytes available = 11.7% of usable space. Plenty of headroom for stack and runtime growth.

2. **8x_slots_8x_pending is the first profile that fails DTCM.** 48781 bytes exceeds 65536 bytes. This is the hard scaling ceiling for monolithic single-core deployment.

3. **Strategy B (state/learning split) is the most promising next step.** It separates state storage from learning mechanics, uses only 2 cores, requires minimal routing entries, and tests a real architecture boundary.

4. **Strategy C is too chatty.** Four cores with distributed lookups requires ~3 round-trips per event. At 1ms timestep, this is manageable but adds complexity without clear benefit over Strategy B.

5. **Strategy D (polyp pool) is premature.** Without a defined inter-polyp communication protocol, independent polyps don't form a useful system.

6. **Dynamic population creation is a hard blocker.** The runtime uses compile-time fixed arrays. Any mapping strategy must respect static allocation.

7. **ITCM size is still unknown.** The .text section has never been measured. This is an acceptable gap for 4.25A but MUST be closed before any hardware smoke that pushes code size (e.g., adding inter-core message handlers).

## Criteria

| Criterion | Value | Rule | Pass |
|-----------|-------|------|------|
| runner revision current | `tier4_25a_multicore_mapping_analysis_20260501_0001` | `expected current source` | ✓ |
| hardware specs documented | `DTCM=64K ITCM=32K SDRAM=128M cores=18 routing=1024` | `all present` | ✓ |
| exact struct sizes computed | `6` | `== 6` | ✓ |
| profile count >= 4 | `6` | `>= 4` | ✓ |
| current_default fits in DTCM | `True` | `== True` | ✓ |
| current_default has DTCM headroom | `43411` | `> 0` | ✓ |
| all profiles have budgets computed | `6` | `== len(PROFILES)` | ✓ |
| mapping strategies >= 3 | `4` | `>= 3` | ✓ |
| monolithic strategy documented | `True` | `== True` | ✓ |
| state_learning_split documented | `True` | `== True` | ✓ |
| routing pressure analyzed | `24` | `> 0` | ✓ |
| blockers identified | `4` | `> 0` | ✓ |
| dynamic_creation flagged as blocker | `True` | `== True` | ✓ |
| ITCM measured and documented | `True` | `== True` | ✓ |

---
*End of report.*
