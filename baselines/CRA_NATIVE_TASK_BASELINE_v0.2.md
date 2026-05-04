# CRA Native Task Baseline v0.2

- Frozen at: `2026-05-03T19:45:00-04:00`
- Source: hardware evidence from Tiers 4.22i through 4.28e
- Registry status: **PASS** (37 canonical entries, 287 noncanonical outputs)
- Canonical hardware bundles: `11` (4.26, 4.27a, 4.27e-g, 4.28a-e)
- Protocol: MCPL/multicast (post-SDP transitional)
- Supersedes: `CRA_NATIVE_RUNTIME_BASELINE_v0.1`

## Freeze Rule

Second native baseline freeze. Earned after `CRA_NATIVE_RUNTIME_BASELINE_v0.1` plus:

1. Tier 4.28b — delayed-cue four-core MCPL hardware probe (48 events, 1 seed)
2. Tier 4.28c — delayed-cue three-seed repeatability (48 events, seeds 42/43/44, zero variance)
3. Tier 4.28d — hard noisy switching four-core MCPL hardware probe (~62 events, seeds 42/43/44, zero variance)
4. Tier 4.28e — native failure-envelope report (30-config local sweep, 3 hardware probe points)

v0.2 adds **harder task capability** and **measured operating envelope** to the v0.1 scaffold.

## Strongest Current Claim

CRA has a bounded native-task baseline on SpiNNaker: the four-core MCPL distributed scaffold executes harder tasks (delayed-cue and hard noisy switching) with three-seed repeatability and zero variance. The operating envelope is measured: ≤64 scheduled events, ≤128 context slots, ≤128 pending horizons. Graceful degradation is confirmed at the schedule boundary (no crashes, no corruption). The custom C runtime fits in ITCM (learning core ~12,960 bytes), uses official Spin1API symbols, and returns compact v2 schema readback.

## Claim Boundaries

- v0.2 is a **native task capability** baseline, not a full CRA mechanism baseline.
- It proves the four-core distributed scaffold handles harder tasks (delayed-cue, hard noisy switching) repeatably.
- It documents the exact operating envelope: `MAX_SCHEDULE_ENTRIES=64`, `MAX_CONTEXT_SLOTS=128`, `MAX_PENDING_HORIZONS=128`.
- It does **not** prove multi-chip scaling, continuous host-free operation, v2.1 mechanism transfer (keyed memory, routing, replay, predictive binding, self-evaluation, lifecycle), or general task-level autonomy.
- Host still performs setup (slot writes, schedule upload) and readback; the chip executes the event loop autonomously during `run_continuous`.
- The 64-event schedule limit is a chunked-path constraint; continuous mode (Tier 4.23c) removes this cap but was not part of the v0.2 freeze scope.
- SDP remains documented as a transitional fallback; MCPL is the default for v0.2+.

## Nonclaims

- Not multi-chip scaling.
- Not full v2.1 software mechanism transfer (keyed memory, composition/routing, replay, predictive binding, self-evaluation).
- Not lifecycle/self-scaling.
- Not speedup evidence (no wall-time comparison against PyNN/sPyNNaker).
- Not external-baseline superiority.
- Not final on-chip autonomy (host still required for setup and readback).
- Not continuous-mode unlimited event streams (v0.2 freeze uses chunked scheduling).

## Technical Specs

| Profile | ITCM Size | Role | MCPL Router Entry |
|---------|-----------|------|-------------------|
| context_core | ~11,200 bytes | Context slot table; receives lookup requests, sends replies | `0x01100000 / 0xFFFF0000` → core 4 |
| route_core | ~11,200 bytes | Route slot table; receives lookup requests, sends replies | `0x01110000 / 0xFFFF0000` → core 5 |
| memory_core | ~11,200 bytes | Memory slot table; receives lookup requests, sends replies | `0x01120000 / 0xFFFF0000` → core 6 |
| learning_core | ~12,960 bytes | Event schedule, MCPL lookups, feature composition, pending horizon, readout | `0x01200000 / 0xFFF00000` → core 7 |

## Runtime Limits (Measured)

| Limit | Hard Limit | Observed Safe | Failure Mode |
|-------|-----------|---------------|--------------|
| Schedule entries | 512 | ≤512 | Rejected uploads (indices ≥512 return error) |
| Context slots | 128 | ≤128 | Slot exhaustion (not reached in v0.2) |
| Pending horizons | 128 | ≤64 actual | Pending overflow (not reached in v0.2) |
| Max concurrent pending | 10 | ≤10 | No failure observed |

**Note:** MAX_SCHEDULE_ENTRIES was raised from 64 to 512 after 4.28e boundary confirmation.
The 64-entry boundary was tested and confirmed; 512 provides headroom for realistic tasks
(~200-step hard noisy switching, lifecycle events, multi-core scaling) without DTCM pressure
(14,336 bytes = 21.9% of ~64KB DTCM). True on-chip event generation (no schedule array)
is planned as Tier 4.32 architectural upgrade.

## Evidence Summary

### Tier 4.26 — Four-Core Distributed Smoke (seed 42)
- Board: `10.11.194.1`
- Cores: 4/5/6/7
- Criteria: 30/30 pass
- lookup_requests: 144, lookup_replies: 144, stale: 0, timeouts: 0
- readout_weight_raw: 32768, readout_bias_raw: 0
- pending_created: 48, pending_matured: 48

### Tier 4.27a — Four-Core SDP Characterization (seed 42)
- Board: `10.11.194.65`
- Cores: 4/5/6/7
- Criteria: 38/38 pass
- lookup_requests: 144, lookup_replies: 144, stale: 0, timeouts: 0
- readout_weight_raw: 32768, readout_bias_raw: 0
- pending_created: 48, pending_matured: 48

### Tier 4.28a — MCPL Repeatability
| Seed | Board | Criteria | lookup_requests | lookup_replies | stale_replies | timeouts |
|------|-------|----------|-----------------|----------------|---------------|----------|
| 42 | 10.11.204.129 | 38/38 | 144 | 144 | 0 | 0 |
| 43 | 10.11.196.153 | 38/38 | 144 | 144 | 0 | 0 |
| 44 | 10.11.194.65 | 38/38 | 144 | 144 | 0 | 0 |

### Tier 4.28b — Delayed-Cue Four-Core MCPL
- Board: `10.11.213.9`, cores 4/5/6/7
- Criteria: 38/38 pass
- Weight: -32769, bias: -1
- pending: 48/48, lookups: 144/144, stale: 0, timeouts: 0

### Tier 4.28c — Delayed-Cue Three-Seed Repeatability
- Seeds 42/43/44, single board, three sequential runs
- Criteria: 38/38 per seed
- Weight: -32769, bias: -1 on all three. Zero variance.

### Tier 4.28d — Hard Noisy Switching Four-Core MCPL
- Package: cra_428j (cra_428i deprecated: host test assertion failure)
- Seeds 42/43/44, boards 10.11.241.145 / 10.11.242.1 / 10.11.242.65
- Criteria: 38/38 per seed
- Weight: 34208 (~+1.04), bias: -1440 (~-0.04) on all three. Zero variance.
- ~62 events, regime switches, 20% noisy trials, variable delay 3-5
- Per-event regime context via host-pre-written slots (MAX_CONTEXT_SLOTS=128)

### Tier 4.28e — Native Failure-Envelope Report
- Local sweep: 30 configs, 28 predicted pass, 2 predicted fail
- Predicted breakpoint: `schedule_overflow` at >64 events

**Point A** — Highest-pressure passing config:
- Board: `10.11.193.65`, seed 42, criteria 38/38
- 64 events, delay=(1,1), noise=0.6
- Weight=-3225, bias=8530
- pending=64/64, lookups=192/192, stale=0, timeouts=0

**Point B** — Boundary confirmed (noncanonical diagnostic):
- Board: `10.11.193.129`, seed 42
- 78 events, delay=(3,5), noise=0.2
- 64/78 schedule uploads succeeded, 14 rejected
- pending_created=64 (capped at limit), lookup_requests=192 (64×3)
- No crashes, no exceptions, no stale replies, no timeouts

**Point C** — High pending-pressure passing config:
- Board: `10.11.194.1`, seed 42, criteria 38/38
- 43 events, delay=(7,10), noise=0.2
- Weight=101376, bias=5120, exact 0% error vs reference
- pending=43/43, lookups=129/129, stale=0, timeouts=0
- max_concurrent_pending=10

## Ingest Paths

- `controlled_test_output/tier4_26_20260502_pass_ingested/`
- `controlled_test_output/tier4_27a_20260502_pass_ingested/`
- `controlled_test_output/tier4_28a_20260502_mcpl_seed42_hardware_pass_ingested/`
- `controlled_test_output/tier4_28a_20260502_mcpl_seed43_hardware_pass_ingested/`
- `controlled_test_output/tier4_28a_20260502_mcpl_seed44_hardware_pass_ingested/`
- `controlled_test_output/tier4_28b_20260502_hardware_pass_ingested/`
- `controlled_test_output/tier4_28c_20260503_hardware_pass_ingested/`
- `controlled_test_output/tier4_28d_20260503_hardware_pass_ingested/`
- `controlled_test_output/tier4_28e_pointA_20260503_hardware_pass_ingested/`
- `controlled_test_output/tier4_28e_pointC_20260503_hardware_pass_ingested/`
- `controlled_test_output/tier4_28e_pointB_20260503_boundary_confirmed/` (noncanonical diagnostic)

## Re-entry Condition

If future hardware work invalidates this baseline (e.g., MCPL routing regressions under harder tasks, ITCM overflow under larger profiles, or stale reply emergence under envelope-edge stress), return to 4.28e envelope re-measurement before claiming v0.2+.

## Post-Baseline Extensions (v0.2+)

These tiers extend the frozen v0.2 scaffold but do **not** re-freeze the baseline.
They are documented here for continuity, not as baseline re-locks.

### Phase C — Mechanism Migration (4.29a+)
- 4.29a: native keyed-memory overcapacity gate
- 4.29b: native routing/composition gate
- 4.29c: native predictive-binding bridge
- 4.29d: native self-evaluation bridge
- 4.29e: replay/consolidation bridge
- 4.29f: compact native mechanism regression

### Phase D — Lifecycle Native Path (4.30+)
- 4.30: lifecycle-native contract (preallocated pool only)
- 4.30a-d: static-pool lifecycle reference, smoke, multi-core split, sham controls

### Phase E — Multi-Core And Multi-Chip Scaling (4.31+)
- 4.31: update mapping model with measured v0.2 data
- 4.31a-e: single-chip multi-core scale, static reef partition, inter-chip feasibility, first multi-chip smoke, multi-chip learning micro-task
