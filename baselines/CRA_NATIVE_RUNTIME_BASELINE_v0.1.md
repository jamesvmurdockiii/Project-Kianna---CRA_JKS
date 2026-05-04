# CRA Native Runtime Baseline v0.1

- Frozen at: `2026-05-02T22:35:00-04:00`
- Source: hardware evidence from Tiers 4.22i through 4.28a
- Registry status: **PASS** (3/3 seeds)
- Canonical hardware bundles: `3` (4.27a seed 42, 4.28a seeds 42/43/44)
- Protocol: MCPL/multicast (post-SDP transitional)

## Freeze Rule

First native-runtime hardware baseline freeze. Earned after:
1. Tier 4.22i — custom runtime board load + `CMD_READ_STATE` round-trip
2. Tier 4.22j — minimal closed-loop learning smoke (pending/maturation)
3. Tier 4.22l — signed fixed-point learning parity
4. Tier 4.22m — 12-event task micro-loop
5. Tier 4.22n — delayed-cue micro-task
6. Tier 4.22o — noisy-switching micro-task
7. Tier 4.22p — A-B-A reentry micro-task
8. Tier 4.22q — integrated v2 bridge smoke
9. Tier 4.22x — compact v2 bridge decoupled smoke (48 events, 1 seed)
10. Tier 4.26 — four-core SDP distributed smoke (48 events, 1 seed)
11. Tier 4.27a — four-core SDP characterization with instrumentation counters
12. Tier 4.27d–g — MCPL feasibility, two-core smoke, three-state-core smoke, SDP-vs-MCPL analysis
13. Tier 4.28a — four-core MCPL repeatability (48 events, seeds 42/43/44)

## Strongest Current Claim

CRA has a bounded native-runtime baseline on SpiNNaker: four independent cores hold distributed context, route, memory, and learning state; execute a 48-event delayed-credit task autonomously; and communicate via MCPL multicast with zero stale replies and zero timeouts across three seeds. The custom C runtime fits in ITCM (learning core 12,960 bytes), uses official Spin1API symbols, and returns compact v2 schema readback.

## Claim Boundaries

- v0.1 is a **native runtime architecture** baseline, not a full CRA capability baseline.
- It proves the four-core distributed scaffold + MCPL inter-core protocol is hardware-real and repeatable.
- It does **not** prove multi-chip scaling, continuous host-free operation, v2.1 mechanism transfer (keyed memory, routing, replay, predictive binding, self-evaluation, lifecycle), or general task-level autonomy.
- The 48-event task is a tiny delayed-credit micro-loop, not full CRA hard_noisy_switching or delayed_cue.
- Host still performs setup (slot writes, schedule upload) and readback; the chip executes the event loop autonomously during `run_continuous`.
- SDP remains documented as a transitional fallback; MCPL is the default for v0.1+.

## Nonclaims

- Not multi-chip scaling.
- Not full v2.1 software mechanism transfer (keyed memory, composition/routing, replay, predictive binding, self-evaluation).
- Not lifecycle/self-scaling.
- Not speedup evidence (no wall-time comparison against PyNN/sPyNNaker).
- Not external-baseline superiority.
- Not final on-chip autonomy (host still required for setup and readback).

## Technical Specs

| Profile | ITCM Size | Role | MCPL Router Entry |
|---------|-----------|------|-------------------|
| context_core | 11,248 bytes | Context slot table; receives lookup requests, sends replies | `0x01100000 / 0xFFFF0000` → core 4 |
| route_core | 11,280 bytes | Route slot table; receives lookup requests, sends replies | `0x01110000 / 0xFFFF0000` → core 5 |
| memory_core | 11,280 bytes | Memory slot table; receives lookup requests, sends replies | `0x01120000 / 0xFFFF0000` → core 6 |
| learning_core | 12,968 bytes | Event schedule, MCPL lookups, feature composition, pending horizon, readout | `0x01200000 / 0xFFF00000` → core 7 |

## Evidence Summary

### Tier 4.27a — SDP Characterization (seed 42)
- Board: `10.11.194.65`
- Cores: 4/5/6/7
- Criteria: 38/38 pass
- lookup_requests: 144
- lookup_replies: 144
- stale_replies: 0
- timeouts: 0
- readout_weight_raw: 32768
- readout_bias_raw: 0
- pending_created: 48
- pending_matured: 48

### Tier 4.28a — MCPL Repeatability
| Seed | Board | Criteria | lookup_requests | lookup_replies | stale_replies | timeouts |
|------|-------|----------|-----------------|----------------|---------------|----------|
| 42 | 10.11.204.129 | 38/38 | 144 | 144 | 0 | 0 |
| 43 | 10.11.196.153 | 38/38 | 144 | 144 | 0 | 0 |
| 44 | 10.11.194.65 | 38/38 | 144 | 144 | 0 | 0 |

## Ingest Paths

- `controlled_test_output/tier4_27a_20260502_pass_ingested/`
- `controlled_test_output/tier4_28a_20260502_mcpl_seed42_hardware_pass_ingested/`
- `controlled_test_output/tier4_28a_20260502_mcpl_seed43_hardware_pass_ingested/`
- `controlled_test_output/tier4_28a_20260502_mcpl_seed44_hardware_pass_ingested/`

## Re-entry Condition

If future hardware work invalidates this baseline (e.g., MCPL routing regressions, ITCM overflow under larger profiles, or stale reply emergence under harder tasks), return to 4.27d-g feasibility before claiming v0.1+.

## Post-Baseline Extensions (v0.1+)

These tiers extend the frozen v0.1 scaffold but do **not** re-freeze the baseline.
They are documented here for continuity, not as baseline re-locks.

### Tier 4.28b — Delayed-Cue Four-Core MCPL Hardware Probe (2026-05-02)
- Board: `10.11.213.9`, cores 4/5/6/7
- Criteria: 38/38 pass
- Weight: -32769, bias: -1
- pending: 48/48, lookups: 144/144, stale: 0, timeouts: 0
- First attempt (cra_428f) failed: lookup key mismatch. Fixed in cra_428g.
- Ingest: `controlled_test_output/tier4_28b_20260502_hardware_pass_ingested/`

### Tier 4.28c — Delayed-Cue Three-Seed Repeatability (2026-05-03)
- Seeds 42/43/44, single board, three sequential runs
- Criteria: 38/38 per seed
- Weight: -32769, bias: -1 on all three. Zero variance.
- Ingest: `controlled_test_output/tier4_28c_20260503_hardware_pass_ingested/`

### Tier 4.28d — Hard Noisy Switching Four-Core MCPL Hardware Probe (2026-05-03)
- Package: cra_428j (cra_428i deprecated: host test assertion failure)
- Seeds 42/43/44, boards 10.11.241.145 / 10.11.242.1 / 10.11.242.65
- Criteria: 38/38 per seed
- Weight: 34208 (~+1.04), bias: -1440 (~-0.04) on all three. Zero variance.
- ~62 events, regime switches, 20% noisy trials, variable delay 3-5
- Per-event regime context via host-pre-written slots (MAX_CONTEXT_SLOTS=128)
- pending: 62/62, lookups: 186/186, stale: 0, timeouts: 0
- Claim boundary: host-pre-written regime; not autonomous detection
- Ingest: `controlled_test_output/tier4_28d_20260503_hardware_pass_ingested/`
