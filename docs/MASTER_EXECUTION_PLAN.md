# CRA Master Execution Plan

Last updated: 2026-05-15T23:50:00+00:00.

This is the operational execution plan from the current CRA evidence state to a
paper-ready, reviewer-defensible release. Use this file for what to do next, in
what order, when to freeze baselines, and when to narrow claims. Use
`docs/PAPER_READINESS_ROADMAP.md` for the broader strategy and
`CONTROLLED_TEST_PLAN.md` for tier-specific pass/fail definitions.

## 0. Purpose

CRA is not trying to publish one lucky task curve. The project is testing
whether CRA can become a useful, functional, organism-style neuromorphic
learning architecture whose mechanisms matter under delayed credit,
nonstationarity, memory pressure, compositional pressure, lifecycle pressure,
hardware constraints, and eventually more realistic adaptive tasks.

Every broad claim must be earned. If a gate fails, the claim narrows.

## 1. Current Evidence State

Current software baseline lines:

```text
v2.6 = current predictive benchmark baseline.
       Frozen by Tier 7.7z-r0. Edge-of-chaos recurrent dynamics remain the
       best documented predictive benchmark line unless a later clean
       promotion gate supersedes them.

v2.7 = diagnostic NEST organism-development snapshot only.
       It records opt-in lifecycle/operator/readout/conservation mechanisms
       after the healthy-NEST correction. It does not supersede v2.6 for
       predictive benchmarks because true organism PR remained near ~2 and
       MSE did not improve across tested mechanism configurations.

Active execution mode = repo-alignment remediation Gate 5.
       Tier 5.45 locked the healthy-NEST rebaseline contract. The Tier 5.45a
       scoring runner is implemented and smoke-validated, and a resumable
       shard orchestrator is available. The next required gate is full Tier
       5.45a scoring before any new mechanism promotion, baseline freeze, or
       paper-facing claim. Current shard progress is 13/204 cells complete:
       organism_defaults_experimental_off completed sine, mackey_glass, lorenz,
       and narma10 across seeds 42, 43, and 44; enable_neural_heritability
       sine seed 42 also passed 10/10. All completed cells have zero fallback,
       zero sim.run failures, and zero summary-read failures.
       Use
       docs/TIER5_45A_SHARD_EXECUTION_PLAN.md as the operational shard/merge
       procedure for that gate.
```

Current hardware/custom-runtime state:

```text
Tier 4.23a = LOCAL PASS (continuous fixed-point reference, 21/21)
Tier 4.23b = RUNTIME PASS (continuous custom-runtime host tests, 28/28)
Tier 4.23c = HARDWARE PASS (single-core continuous smoke, 22/22 + 15/15 ingest)
Tier 4.24 = RESOURCE CHARACTERIZATION PASS (continuous resource profile, 16/16)
Tier 4.24b = EBRAINS BUILD/SIZE PASS (10/10 + 11/11 ingest)
Tier 4.25A = MAPPING ANALYSIS PASS (14/14)
Tier 4.25B = HARDWARE PASS (two-core state/learning split, 23/23)
Tier 4.25C = HARDWARE PASS (two-core repeatability, 3 seeds)
Tier 4.26 = HARDWARE PASS (four-core distributed context/route/memory/learning, 30/30)
Tier 4.27a = HARDWARE PASS (four-core SDP instrumentation, 38/38 + 38/38 ingest)
Tier 4.28a = HARDWARE PASS (four-core MCPL repeatability, 38/38 x3 seeds)
Tier 4.28b = HARDWARE PASS (delayed-cue four-core MCPL, 38/38)
Tier 4.28c = HARDWARE PASS (delayed-cue three-seed repeatability, 38/38 x3)
Tier 4.28d = HARDWARE PASS (hard noisy switching four-core MCPL, 38/38 x3)
Tier 4.28e = LOCAL PASS / HARDWARE PASS (native failure-envelope report, 3 probes)
Tier 4.29a = HARDWARE PASS (native keyed-memory overcapacity, 3 seeds)
Tier 4.29b = HARDWARE PASS (native routing/composition, 3 seeds)
Tier 4.29c = HARDWARE PASS (native predictive binding, 3 seeds)
Tier 4.29d = HARDWARE PASS (native self-evaluation/confidence gating, 3 seeds)
Tier 4.29e = HARDWARE PASS (native replay/consolidation bridge, 38/38 x3 seeds)
Tier 4.29f = EVIDENCE-REGRESSION PASS (native mechanism bridge audit, 113/113)
```

Important Tier 4.26 result:

```text
output = controlled_test_output/tier4_26_20260502_pass_ingested/
board = 10.11.194.1
cores = 4/5/6/7
learning core = decisions 48, reward_events 48, pending_created 48,
                pending_matured 48, active_pending 0,
                readout_weight_raw 32768, readout_bias_raw 0
context core = slot_hits 48
criteria = 30/30 hardware + 30/30 ingest
fallback = 0
```

Tier 4.26 claim boundary:

```text
A four-core distributed custom runtime can hold context, route, memory, and
learning state on separate SpiNNaker cores and reproduce the monolithic delayed-
credit result within tolerance on a 48-event task. This is not speedup evidence,
not multi-chip scaling, not arbitrary task execution, not lifecycle hardware,
not full native v2.1, and not final autonomy.
```

Latest lifecycle hardware result:

```text
Tier 4.30b-hw = HARDWARE FUNCTIONAL PASS AFTER INGEST CORRECTION
output = controlled_test_output/tier4_30b_hw_20260505_hardware_pass_ingested/
raw remote status = fail
corrected ingest status = pass
reason = rev-0001 checked cumulative readback_bytes instead of compact payload_len
board = 10.11.226.17
selected core = (0,0,4)
canonical_32 corrected scenario criteria = 16/16
boundary_64 corrected scenario criteria = 16/16
payload_len = 68 for both scenarios
active masks / lineage checksums / trophic checksums matched reference
fallback = 0
```

Latest lifecycle split result:

```text
Tier 4.30c = LOCAL CONTRACT/REFERENCE PASS, 22/22
output = controlled_test_output/tier4_30c_20260505_multicore_lifecycle_split/
core roles = context_core, route_core, memory_core, learning_core, lifecycle_core
canonical_32 = 32 event acks, 13 mask syncs, exact 4.30a/4.30b-hw parity
boundary_64 = 64 event acks, 22 mask syncs, exact 4.30a/4.30b-hw parity
transport target = inter-core MCPL/multicast for lifecycle requests and mask syncs
boundary = local contract/reference only; no C implementation or hardware claim
```

Latest lifecycle runtime source result:

```text
Tier 4.30d = LOCAL SOURCE/RUNTIME HOST PASS, 14/14
output = controlled_test_output/tier4_30d_20260505_lifecycle_runtime_source_audit/
runner = experiments/tier4_30d_lifecycle_runtime_source_audit.py
runtime additions = lifecycle_core profile, lifecycle MCPL/multicast-target
  event/trophic/active-mask-sync stubs, active-mask/count/lineage sync payload
  coverage, lifecycle split counters, ownership guards, and local C host tests
boundary = local source/runtime host evidence only; no EBRAINS hardware claim
```

Latest lifecycle hardware result:

```text
Tier 4.30e = HARDWARE PASS, INGESTED
output = controlled_test_output/tier4_30e_hw_20260505_hardware_pass_ingested/
runner = experiments/tier4_30e_multicore_lifecycle_hardware_smoke.py
board = 10.11.226.145
raw remote status = pass
ingest status = pass
hardware criteria = 75/75
ingest criteria = 5/5
scope = five-profile hardware smoke: context_core, route_core,
  memory_core, learning_core, lifecycle_core
result = all five profiles built/loaded/read back; non-lifecycle ownership
  guards passed; canonical_32 and boundary_64 lifecycle schedules matched
  reference; duplicate/stale lifecycle event rejection passed
boundary = hardware smoke only; not lifecycle task benefit, not sham-control
  success, not speedup, not multi-chip scaling, not v2.2 temporal migration,
  and not a lifecycle baseline freeze
```

## 2. Immediate Baseline Decision

Do not freeze a new software baseline from Tier 7.7j or the next Tier 7.7k
contract alone.

Current frozen lines:

```text
Software baseline: v2.5
Native mechanism bridge baseline: CRA_NATIVE_MECHANISM_BRIDGE_v0.3
Lifecycle native baseline: CRA_LIFECYCLE_NATIVE_BASELINE_v0.4
Native-scale substrate baseline: CRA_NATIVE_SCALE_BASELINE_v0.5
```

Reason:

```text
v2.x software baselines are for promoted CRA mechanisms plus regression.
Tier 7.7j narrowed the standardized-benchmark failure diagnosis to low-rank
state collapse; it did not promote a mechanism. Tier 7.7k is a contract step;
it cannot freeze anything until implementation, shams, baselines, and compact
regression pass.
```

Baseline decision rule:

```text
Tier 5.19c passed and froze v2.2 as a bounded fading-memory temporal-state
software baseline. Tier 7.0j passed and froze v2.3 as a generic bounded
recurrent-state software baseline after the locked public scoreboard and full
NEST compact regression passed. Tier 7.4c passed and froze v2.4 as a
cost-aware policy/action software baseline after the locked 7.4b expected-
utility candidate passed a full NEST compact regression. v2.4 does not prove
public usefulness, hardware/native policy transfer, long-horizon planning,
language, AGI, or ASI.
Tier 4.30-readiness passed on 2026-05-05 with 16/16 criteria. The lifecycle
native path layers initially on `CRA_NATIVE_MECHANISM_BRIDGE_v0.3`, using v2.2
only as a software reference boundary. Tier 4.32h then froze
`CRA_NATIVE_SCALE_BASELINE_v0.5` as a bounded native-scale substrate closeout
over the completed 4.32a/4.32d/4.32e/4.32g evidence. Do not smuggle v2.2
or v2.3 host-side temporal/recurrent state, speedup, benchmark usefulness, true
partitioned learning, or lifecycle scaling into the v0.5 claim.
```

The native runtime and native mechanism bridge lines remain separate from the
`CRA_EVIDENCE_BASELINE_v2.x` software line.

## 3. Baseline Freeze Rules From Here

Freeze only when the relevant line earns it.

| Baseline line | Freeze only after | Do not freeze from |
| --- | --- | --- |
| Software `v2.x` | New software mechanism passes ablations, controls, baselines where relevant, and compact regression. | Hardware primitive or runtime smoke. |
| Native runtime `v0.x` | Runtime architecture is characterized, resource/timing envelope is measured, protocol decision is made, and validation passes. | One successful smoke without timing/resource envelope. |
| Native mechanism bridge `v0.x` | Promoted software mechanisms are mapped to native/hybrid equivalents and pass controls. | A host bridge that only proves transport. |
| Lifecycle native `v0.x` | Static-pool lifecycle works with lineage, masks, sham controls, and resource accounting. | Software lifecycle evidence alone. |
| Paper release `v1.0` | Final software matrix, final hardware subset, statistics, limitations, and reproduction capsule pass. | Any single tier. |

## 4. What Fully Chip Native Means

A chip-native claim can be made only for the named subset that passes. Full CRA
native/on-chip is not claimed until all of these are true for the claimed scope:

| Requirement | Current state |
| --- | --- |
| Chip-owned delayed credit | Tiny fixed-point pending/readout path proven through 4.22j-4.23c. |
| Continuous execution | Single-core continuous smoke passed in 4.23c. |
| Compact readback | Proven for current micro-runtime path. |
| Distributed state | Four-core context/route/memory/learning split passed in 4.26. |
| Runtime resource envelope | Partly measured; four-core timing/message envelope still needs 4.27. |
| Stable inter-core protocol | SDP works for 4.26 as a transitional scaffold; MCPL/multicast is the scaling target and needs a migration gate. |
| Promoted v2 mechanisms native | Keyed memory (4.29a), routing/composition (4.29b), predictive binding (4.29c), self-evaluation (4.29d), and host-scheduled replay/consolidation (4.29e) complete. 4.29f froze the cumulative native mechanism bridge evidence baseline. Lifecycle remains. |
| Lifecycle/self-scaling native | Static-pool lifecycle and host-ferried task bridge are frozen in v0.4; two-chip lifecycle traffic/resource smoke is included in v0.5. Lifecycle scaling and autonomous lifecycle-to-learning MCPL are not proven. |
| Continuous temporal dynamics substrate | v2.2 promotes bounded host-side fading-memory temporal state after Tier 5.19c; native/on-chip temporal dynamics and bounded nonlinear recurrence remain unproven. |
| Multi-chip scaling | Bounded two-chip communication, learning micro-task, and lifecycle traffic/resource smokes are included in v0.5. True two-partition learning, multi-shard learning, speedup, and useful task scaling remain unproven. |
| Useful task-level native proof | Not complete beyond tiny micro-tasks. |

## 5. Core Operating Order

Do not jump directly from a smoke pass to scale. The order is:

```text
contract -> local reference -> static/source audit -> local implementation ->
prepare package -> hardware smoke -> ingest -> characterize -> repeat/scale -> freeze if earned
```

For hardware-native work, always ask:

```text
What is chip-owned?
What is host-owned?
What is merely a bridge?
What is measured?
What is inferred?
What claim boundary follows?
```

## 5.1 Remaining Mechanic Queue And Dependency Order

This list is deliberately broader than the next few tiers. It prevents the
project from forgetting planned mechanisms, while preserving the rule that only
one major mechanism is implemented and promoted at a time.

These mechanics are not all meant to live inside every single polyp. They are
substrate capabilities distributed across polyps, population state, routing
state, readout interfaces, lifecycle machinery, and native runtime support. A
polyp should remain small; the reef earns capability through many small
specialists, shared state primitives, and controlled composition.

Known remaining or unpromoted mechanics:

```text
1. Continuous temporal dynamics / fading-memory substrate.
2. CRA-native nonlinear recurrent state, distinct from simple lag regression.
3. Local continuous-value readout/interface that survives lag-only and sham controls.
4. Revisit macro/native eligibility only if temporal dynamics exposes a credit blocker.
5. Lifecycle/self-scaling layered on the stronger temporal substrate.
6. Native lifecycle/self-scaling with static pools, masks, lineage, and sham controls.
7. Native/on-chip temporal dynamics and compact state update.
8. Native/on-chip replay buffers or sleep-like replay, beyond host-scheduled replay.
9. Native/on-chip eligibility traces at scale, if justified by measured blockers.
10. Policy/action-selection loop with delayed consequences and exploration pressure.
11. Real-ish task adapters and held-out task families.
12. Curriculum/environment generator.
13. Long-horizon planning / subgoal control.
14. Single-chip multi-core scale stress.
15. Multi-chip communication and learning.
16. Final expanded baselines, fairness audit, reproduction capsule, and paper lock.
```

Mechanism policy:

```text
Add one major mechanism -> targeted test -> sham controls -> baseline comparison
-> compact regression -> freeze if earned, otherwise park or narrow.
```

The Tier 7.0 benchmark branch did not justify a benchmark-specific trick. It
did expose a general missing substrate: continuous temporal dynamics. That
mechanism must be tested before assuming lifecycle alone will evolve the
ability.

## 6. Next 74-Step Execution Plan

### Phase A - Close 4.26 And Decide The Runtime Protocol

1. Close Tier 4.26 as a hardware-native distributed-runtime milestone.
   Do not freeze `v2.2` or a native baseline yet.

2. Preserve the full 4.26 failure/repair ledger as noncanonical engineering
   evidence. Keep the passed `cra_426f` run as the canonical 4.26 pass.

3. Define Tier 4.27 as `Four-Core Runtime Resource / Timing Characterization +
   MCPL Decision Gate` in the roadmap, test plan, and contract.

4. ~~Tier 4.27a local instrumentation: add counters for lookup requests/replies,
   payload bytes, stale replies, duplicate replies, timeouts, per-core command
   counts, schedule length, and compact readback bytes.~~ DONE.
   Runner: `experiments/tier4_27a_four_core_distributed_smoke.py`.
   Package: `ebrains_jobs/cra_427a`. All host tests pass, all four profile .aplx
   images build locally (ITCM headroom confirmed).

5. ~~Tier 4.27b hardware characterization on the current SDP four-core path:
   run the 48-event stream and measure wall time, load time, task time,
   pause/readback time, per-core counters, and lookup reliability.~~ DONE.
   Board 10.11.194.65, cores 4/5/6/7, seed 42. 38/38 criteria pass.
   Schema v2 readback validated with instrumentation counters.

6. ~~Tier 4.27c schedule-length/resource sweep: 48, 96, and 192 events if
    practical.~~ DEPRECATED. Envelope characterization moved to 4.28e.

7. ~~Tier 4.27 decision point: SDP characterization decides only how much, if
    any, near-term debugging work may remain on SDP.~~ DONE.
    MCPL selected as default protocol; SDP remains transitional fallback.

8. ~~Run Tier 4.27d MCPL feasibility regardless of whether SDP survives as a
   temporary scaffold: compile-time and local tests using official
   `MC_PACKET_RECEIVED` / `MCPL_PACKET_RECEIVED` symbols, no guessed callback
   names.~~ DONE.
   MCPL key format macros, send/receive functions, and callback registration all
   compile. Host test 19/19 pass. All four profile .aplx builds succeed.
   ITCM headroom: learning_core text=12,448 bytes.

9. ~~Run Tier 4.27e two-core MCPL round-trip smoke: one state core and one
   learning core, one lookup type, one board, one seed.~~ DONE (local build).
   MCPL wired into full lookup state machine: `_send_lookup_request` and
   `_send_lookup_reply` use MCPL path when `CRA_USE_MCPL_LOOKUP` defined.
   `mcpl_lookup_callback` routes to `cra_state_mcpl_lookup_receive` which
   dispatches REQUEST to state cores and REPLY to learning core.
   `cra_state_mcpl_init` sets up router entries per core role.
   Runner `tier4_27e_two_core_mcpl_smoke.py` validates wiring + builds.
   context_core ITCM=11,240 bytes; learning_core ITCM=12,960 bytes.
   Hardware deployment pending EBRAINS access.

10. ~~Run Tier 4.27f three-state-core MCPL lookup smoke: context/route/memory
    replies to learning core with sequence IDs.~~ DONE (local build).
    Learning core router mask broadened to 0xFFFF0000 to catch all lookup-type
    replies via single router entry. All four profile .aplx images build with
    MCPL: context=11,240B, route=11,272B, memory=11,272B, learning=12,960B.
    Runner validates wiring + builds. Hardware deployment pending EBRAINS.

11. ~~Run Tier 4.27g SDP-vs-MCPL protocol comparison: compare reliability,
    payload, latency, load, command count, failure modes, routing pressure, and
    implementation risk.~~ DONE (local analysis).
    MCPL round-trip = 16 bytes (71% reduction from SDP's 54 bytes). For 48-event
    schedule: SDP ~8,064 bytes inter-core lookup traffic vs MCPL ~2,304 bytes.
    SDP latency ~5-20 us (monitor-bound); MCPL ~0.5-2 us (hardware router).
    SDP requires 0 router entries but scales poorly; MCPL requires 4 entries
    (one per core role) and scales via hardware router. Recommendation: make
    MCPL default for Tier 4.28+; keep SDP as fallback until MCPL hardware smoke.

12. ~~Freeze `CRA_NATIVE_RUNTIME_BASELINE_v0.1` only if Tier 4.27 gives a measured
    resource/timing envelope plus a concrete MCPL migration result or schedule.~~ DONE.
    Baseline v0.1 frozen from 4.28a. Later superseded by `CRA_NATIVE_TASK_BASELINE_v0.2`
    (from 4.28a-e).

### Phase B - Native Task Hardening After Runtime Decision

13. ✅ **COMPLETE** - Tier 4.28a four-core MCPL repeatability (2026-05-02).
    Seeds 42/43/44 all pass 38/38 criteria. Zero stale replies, zero timeouts.
    Weight=32768, bias=0, pending=48/48. Freezes `CRA_NATIVE_RUNTIME_BASELINE_v0.1`.

14. ✅ **COMPLETE** - Tier 4.28b delayed-cue four-core MCPL hardware probe
    (2026-05-02). Seed 42, board 10.11.213.9. Weight=-32769, bias=-1, 38/38.
    First attempt (cra_428f) failed: lookup key mismatch. Fixed in cra_428g.

15. ✅ **COMPLETE** - Tier 4.28c delayed-cue three-seed repeatability (2026-05-03).
    Seeds 42/43/44, all 38/38. Weight=-32769, bias=-1 on all. Zero variance.

16. ✅ **COMPLETE** - Tier 4.28d hard noisy switching four-core MCPL hardware probe
    (2026-05-03). Seeds 42/43/44, all 38/38. Weight=34208, bias=-1440 on all.
    Zero variance. ~62 events, regime switches, 20% noisy trials, variable delay.
    Package cra_428j (cra_428i deprecated: host test assertion failure).

17. ✅ **COMPLETE** - Tier 4.28e native failure-envelope report.
    Local sweep complete (30 configs, 28 predicted pass, 2 predicted fail).
    Predicted breakpoint: schedule_overflow at >64 events (MAX_SCHEDULE_ENTRIES hard limit).
    Probe Point A - HARDWARE PASS, INGESTED. Seed 42, board 10.11.193.65. 38/38 criteria.
      Weight=-3225, bias=8530. Pending=64/64, lookups=192/192, stale=0, timeouts=0.
    Probe Point B - BOUNDARY CONFIRMED (noncanonical diagnostic). Seed 42, board 10.11.193.129.
      78 events generated, 64 schedule uploads succeeded, 14 rejected. pending_created=64 (capped at limit).
      Confirms exact MAX_SCHEDULE_ENTRIES=64 boundary. No crashes, no exceptions, no stale replies.
    Probe Point C - HARDWARE PASS, INGESTED. Seed 42, board 10.11.194.1. 38/38 criteria.
      Weight=101376, bias=5120, exact 0% error vs reference. Pending=43/43, lookups=129/129, stale=0, timeouts=0.
      Confirms safe operation well below schedule limit with high pending pressure (max_concurrent_pending=10).
    POST-4.28E DECISION: MAX_SCHEDULE_ENTRIES raised from 64 to 512.
      64-entry boundary confirmed via Point B; 512 provides headroom for realistic tasks
      (~200-step hard noisy switching, lifecycle, multi-core) without DTCM pressure.
      True on-chip event generation (no schedule array) is Tier 4.32 future work.

18. ✅ **COMPLETE** - Freeze `CRA_NATIVE_TASK_BASELINE_v0.2`.
    Repeatability: 4.28a (three-seed MCPL), 4.28c (delayed-cue three-seed), 4.28d (hard switching three-seed).
    Harder native tasks: 4.28b (delayed-cue four-core), 4.28d (hard noisy switching four-core).
    Envelope measured: 4.28e (≤512 schedule entries, ≤128 context slots, ≤128 pending).
    Baseline file: `baselines/CRA_NATIVE_TASK_BASELINE_v0.2.md`.
    Registry snapshot: `baselines/CRA_NATIVE_TASK_BASELINE_v0.2_STUDY_REGISTRY.snapshot.json`.
    Supersedes `CRA_NATIVE_RUNTIME_BASELINE_v0.1`.
    Next: Phase C (4.29a+) - mechanism migration toward native v2.1.

### Phase C - Move Promoted v2 Mechanisms Toward Native/On-Chip

19. ✅ **COMPLETE** - Mechanism migration map defined.
    Promoted to native: keyed context memory (4.29a), composition/routing (4.29b),
    predictive binding (4.29c), self-evaluation (4.29d), replay/consolidation (4.29e),
    lifecycle (4.30). Parked: macro eligibility (5.9c, stays host-side).
    Migration rules: local first, one mechanism at a time, controls required,
    resource budget checked, compact regression after each bridge.
    Documented in `CONTROLLED_TEST_PLAN.md` Phase C section.

20. ✅ **COMPLETE** - Tier 4.29a native keyed-memory overcapacity gate.
    HARDWARE PASS, INGESTED. Three-seed repeatability complete.
    Seeds 42/43/44, all 10/10 criteria. Wrong-key and slot-shuffle controls pass.

21. ✅ **COMPLETE** - Tier 4.29b native routing/composition gate.
    HARDWARE PASS, INGESTED. Three-seed repeatability complete.
    Seeds 42/43/44, all 52/52 criteria. Previous cra_429c FAILED (48/52).
    Root cause: host_interface.c context-slot counter emission for ALL profiles.
    Fixed in C runtime, rebuilt, bumped to cra_429d.

22. ✅ **COMPLETE** - Tier 4.29c native predictive-binding bridge.
    HARDWARE PASS, INGESTED. Three-seed repeatability complete.
    Seeds 42/43/44, all 24/24 criteria. Zero variance.
    Weight=30912, bias=-1856 on all seeds. Pending=20/20, lookups=60/60.
    Package: cra_429h.

23. ✅ **COMPLETE** - Tier 4.29d native self-evaluation bridge.
    HARDWARE PASS, INGESTED. Three-seed repeatability complete.
    Seeds 42/43/44, all 30/30 criteria per seed, 90/90 total.
    Zero-confidence: exact weight=0, bias=0 (proves confidence gating).
    Half-confidence: weight=28093, bias=3517 (diff=61 from ref).
    First attempt (cra_429i) failed: MCPL lookup lacks confidence transmission.
    Fix: revert to SDP inter-core lookup. Rebuilt as cra_429j.

24. ✅ **COMPLETE** - Tier 4.29e replay/consolidation bridge.
    HARDWARE PASS, INGESTED after `cra_429p` repair.
    `cra_429o` returned real hardware but failed as a noncanonical diagnostic
    because the local schedule/reference gate was wrong. That failure is
    preserved at `controlled_test_output/tier4_29e_20260505_cra_429o_hardware_fail/`.
    Canonical artifact: `controlled_test_output/tier4_29e_20260505_pass_ingested/`.
    Runner revision: `tier4_29e_native_replay_consolidation_20260505_0003`.
    Seeds 42/43/44 passed on boards 10.11.226.129 / 10.11.226.1 / 10.11.226.65.
    Criteria: 38/38 per seed, 114/114 total.
    Controls: no_replay, correct_replay, wrong_key_replay, random_event_replay.
    Correct replay changes readout weight versus no_replay; wrong-key replay
    blocks weight consolidation; random-event replay remains distinct.
    Boundary: host-scheduled replay through native state primitives only; not
    native replay buffers or biological sleep.

25. ✅ **COMPLETE** - Tier 4.29f compact native mechanism regression.
    Evidence-regression audit over canonical 4.29a-e hardware passes.
    Criteria: 113/113.
    Output: `controlled_test_output/tier4_29f_20260505_native_mechanism_regression/`.
    Boundary: not a new SpiNNaker execution and not a monolithic all-mechanism task.

26. ✅ **COMPLETE** - Freeze `CRA_NATIVE_MECHANISM_BRIDGE_v0.3`.
    Baseline file: `baselines/CRA_NATIVE_MECHANISM_BRIDGE_v0.3.md`.
    Registry snapshot: `baselines/CRA_NATIVE_MECHANISM_BRIDGE_v0.3_STUDY_REGISTRY.snapshot.json`.
    Supersedes `CRA_NATIVE_TASK_BASELINE_v0.2` for native mechanism bridge evidence.

27. ✅ **COMPLETE** - Tier 7.0 standard dynamical benchmarks in software:
    Mackey-Glass, Lorenz, NARMA10, and geometric-mean aggregate MSE completed
    with 10/10 harness criteria. CRA v2.1 online ranked 5/5 by aggregate
    geomean MSE against the tested causal sequence baselines; echo-state
    network was best. This is a diagnostic pass and a capability gap, not a
    superiority claim and not a new baseline freeze.

28. ✅ **COMPLETE** - Tier 7.0b continuous-regression failure analysis:
    localized the Tier 7.0 gap to
    `recoverable_state_signal_default_readout_failure`. Raw CRA geomean MSE was
    1.2233; leakage-safe CRA internal-state ridge probe improved to 0.4433;
    CRA state plus the same causal lag budget improved to 0.0544; shuffled
    target state control remained worse at 0.7533. This is diagnostic evidence,
    not a promoted repair.

29. ✅ **COMPLETE** - Tier 7.0c bounded continuous readout/interface repair:
    passed 10/10 integrity criteria and improved raw CRA aggregate geomean MSE
    from 1.2233 to 0.1904 with the best bounded state+lag repair. However,
    lag-only online LMS reached 0.1515 and explains most of the gain. This is
    limited repair-candidate evidence, not a promoted CRA mechanism, not a
    baseline freeze, and not a hardware-migration trigger.

30. ✅ **COMPLETE** - Tier 7.0d state-specific continuous interface repair / claim-narrowing contract:
    passed 10/10 criteria and classified the Tier 7 standard dynamical benchmark
    path as `lag_regression_explains_benchmark`. The best state-specific online
    candidate reached geomean MSE 0.1455 versus lag-only 0.1515, but this did
    not clear the predeclared margin and a shuffled residual sham reached
    0.1409. Train-prefix ridge lag-only also beat lag+state probes. No
    continuous-readout mechanism is promoted and this benchmark path should not
    move to hardware under the current interface.

### Phase D - Continuous Temporal Dynamics Substrate

31. ✅ **COMPLETE** - Tier 5.19 / 7.0e continuous temporal dynamics substrate contract:
    define the general fading-memory / recurrent temporal-state mechanism before
    writing code. This is not a Mackey-Glass trick; it is a substrate repair for
    continuous temporal memory, nonlinear recurrence, and local continuous
    prediction under strict lag-only and sham controls.

32. ✅ **COMPLETE** - Tier 5.19a local temporal substrate reference: implemented the smallest
    software-only candidate with multi-timescale fading state, bounded nonlinear
    recurrent state, and a local online continuous interface. Compare against
    lag-only, random reservoir, fixed ESN, no recurrence, frozen state,
    shuffled state, shuffled target, and current v2.1.
    Result: local software pass, 12/12 criteria. Classification =
    `fading_memory_ready_but_recurrence_not_yet_specific`. Held-out long-memory
    task showed strong fading-memory value (candidate MSE 0.3857 vs lag-only
    1.2710, shuffled-state 1.8900, frozen-state 0.5685), but no-recurrence MSE
    0.3974 leaves recurrence-specific value insufficiently separated.

33. ✅ **COMPLETE** - Tier 5.19b benchmark/sham gate: implemented a stricter
    software-only matrix over Mackey-Glass, Lorenz, NARMA10, held-out long
    memory, and recurrence-pressure diagnostics with current v2.1, lag-only,
    random/fixed reservoir, fading-only, recurrent-only, state-reset,
    recurrent-permutation, frozen-state, shuffled-state, shuffled-target, and
    no-plasticity controls.
    Result: pass, 12/12 criteria. Classification =
    `fading_memory_supported_recurrence_unproven`. Held-out long-memory value
    remained strong (candidate MSE 0.3857 vs lag-only 1.2710), but
    recurrence-pressure did not separate from lag-only or state-reset
    (candidate 0.8982, lag-only 0.8967, state-reset 0.9029). Do not claim
    bounded nonlinear recurrence and do not freeze or migrate to hardware.

34. ✅ **COMPLETE** - Tier 5.19c fading-memory narrowing / compact regression
    decision: the narrowed multi-timescale fading-memory temporal substrate
    earned promotion without a recurrence claim.
    Result: pass, 11/11 criteria, full NEST compact regression passed.
    Classification = `fading_memory_ready_for_v2_2_freeze`.
    v2.2 frozen at `baselines/CRA_EVIDENCE_BASELINE_v2.2.md`.
    Key metrics: temporal-memory geomean candidate MSE 0.2275 vs lag-only
    0.8954 (3.94x margin) and raw v2.1 2.1842 (9.60x margin). Standard-three
    lag-only remains stronger than the candidate, so do not claim universal
    benchmark superiority or migrate the benchmark path to hardware.

35. ✅ **COMPLETE** - Tier 4.30-readiness audit: before writing
    lifecycle-native code, decide whether lifecycle hardware should layer on
    v2.2 software state, the v2.1-era native mechanism bridge, or a deliberately
    scoped subset of both. This audit must define the static-pool constraints,
    lifecycle counters, lineage/mask/trophic readback fields, sham controls, and
    artifact expectations for Tier 4.30.
    Result: pass, 16/16 criteria.
    Output: `controlled_test_output/tier4_30_readiness_20260505_lifecycle_native_audit/`.
    Runner: `experiments/tier4_30_readiness_audit.py`.
    Decision: layer initial lifecycle-native work on
    `CRA_NATIVE_MECHANISM_BRIDGE_v0.3`, with v2.2 as a software reference only.
    Explicitly exclude dynamic PyNN population creation, legacy SDRAM
    malloc/free neuron birth/death as the proof, unscoped v2.2 temporal-state
    migration, multi-chip scaling, speedup claims, and paper-level lifecycle
    superiority.

### Phase E - Lifecycle / Organism Dynamics Native Path

36. ✅ **COMPLETE** - Tier 4.30 lifecycle-native contract:
    preallocated pool only. No dynamic
    PyNN population creation mid-run. Birth/cleavage/death are activation,
    masking, assignment, or lineage events inside static state.
    Result: pass, 14/14 criteria.
    Output: `controlled_test_output/tier4_30_20260505_lifecycle_native_contract/`.
    Runner: `experiments/tier4_30_lifecycle_native_contract.py`.
    Contract: 8-slot static pool, 2 founders, command schema for lifecycle
    init/event/trophic update/readback/sham mode, 23 readback fields, 5 event
    semantics, 5 gate definitions, and 7 failure classes.

37. ✅ **COMPLETE** - Tier 4.30a local static-pool lifecycle reference: active/inactive masks,
    lineage IDs, trophic state, birth/cleavage/death counters, fixed max-pool
    control, random event replay control.
    Result: pass, 20/20 criteria.
    Output: `controlled_test_output/tier4_30a_20260505_static_pool_lifecycle_reference/`.
    Runner: `experiments/tier4_30a_static_pool_lifecycle_reference.py`.
    Scope: canonical 32-event trace plus boundary 64-event trace, 8-slot pool,
    2 founders, zero invalid events on enabled path, deterministic repeat,
    fixed-pool/random-replay/mask-shuffle/lineage-shuffle/no-trophic/no-dopamine
    controls precomputed.

38. ✅ **COMPLETE** - Tier 4.30b source audit / single-core lifecycle
    mask-smoke preparation: mapped the Tier 4.30a static-pool reference into the
    smallest runtime-facing lifecycle state surface.
    Result: pass, 13/13 criteria.
    Output: `controlled_test_output/tier4_30b_20260505_lifecycle_source_audit/`.
    Runner: `experiments/tier4_30b_lifecycle_source_audit.py`.
    Runtime surface: lifecycle init/event/trophic/readback/sham opcodes,
    `lifecycle_slot_t`, `cra_lifecycle_summary_t`, exact canonical_32 and
    boundary_64 checksum parity, separate lifecycle readback preserving existing
    `CMD_READ_STATE` schema v2, and local runtime/profile tests passing.
    Boundary: local source/runtime host evidence only; not EBRAINS hardware,
    not task benefit, not multi-core lifecycle, and not a baseline freeze.

39. ✅ **COMPLETE** - Tier 4.30b single-core lifecycle active-mask /
    lineage hardware smoke package/run: package the audited runtime surface and
    run the smallest EBRAINS smoke that proves lifecycle metadata survives a real
    SpiNNaker execution/readback path. Scope is active mask, lineage/checksum,
    event counters, and compact lifecycle readback only; still no task-effect or
    multi-core lifecycle claim.
    Prepared package: `ebrains_jobs/cra_430b`.
    Prepared result: `controlled_test_output/tier4_30b_hw_20260505_prepared/`,
    status `prepared`, 6/6 criteria. The package includes the current
    lifecycle host controller, `RUNTIME_PROFILE=decoupled_memory_route` build
    path, canonical_32 and boundary_64 lifecycle reference expectations, and
    the JobManager command.
    Returned result: `controlled_test_output/tier4_30b_hw_20260505_hardware_pass_ingested/`,
    corrected ingest status `pass`, 5/5 ingest criteria. The raw remote status
    was `fail` because runner rev-0001 checked cumulative `readback_bytes`
    instead of actual compact `payload_len`; raw artifacts preserved both
    `payload_len=68` and exact lifecycle state/reference parity for
    `canonical_32` and `boundary_64`.

40. ✅ **COMPLETE** - Tier 4.30c multi-core lifecycle state split:
    distribute lifecycle masks and
    lineage across the selected runtime protocol without corrupting state.
    Result: local contract/reference pass, 22/22 criteria.
    Output: `controlled_test_output/tier4_30c_20260505_multicore_lifecycle_split/`.
    Runner: `experiments/tier4_30c_multicore_lifecycle_split.py`.
    Scope: five-core ownership contract (`context_core`, `route_core`,
    `memory_core`, `learning_core`, `lifecycle_core`), inter-core lifecycle
    event/trophic/mask-sync message contract with MCPL/multicast as the target,
    host setup/readback only, explicit failure classes, and deterministic
    split-reference parity for `canonical_32` and `boundary_64`.
    Boundary: local contract/reference only; not C implementation, not hardware
    evidence, not task benefit, not speedup, not v2.2 temporal migration, and
    not a lifecycle baseline freeze.

41. ✅ **COMPLETE** - Tier 4.30d multi-core lifecycle runtime source
    audit/local C host test:
    Result: local source/runtime host pass, 14/14 criteria.
    Output: `controlled_test_output/tier4_30d_20260505_lifecycle_runtime_source_audit/`.
    Runner: `experiments/tier4_30d_lifecycle_runtime_source_audit.py`.
    Scope: dedicated `lifecycle_core` profile, lifecycle inter-core
    event/trophic request stubs, active-mask/count/lineage sync send/receive
    bookkeeping, duplicate/stale/missing-ack counters, non-lifecycle ownership
    guards, compact `payload_len=68` preservation, and local C host tests
    against the Tier 4.30c contract.
    Boundary: local source/runtime host evidence only; not EBRAINS hardware
    evidence, not task benefit, not speedup, not multi-chip scaling, not v2.2
    temporal migration, and not a lifecycle baseline freeze.

42. ✅ **COMPLETE** - Tier 4.30e multi-core lifecycle hardware smoke:
    proved the 4.30d runtime source surface survives real SpiNNaker
    execution/readback before any lifecycle sham-control hardware subset.
    Prepared output: `controlled_test_output/tier4_30e_hw_20260505_prepared/`.
    Ingested output:
    `controlled_test_output/tier4_30e_hw_20260505_hardware_pass_ingested/`.
    Upload folder: `ebrains_jobs/cra_430e`.
    Runner: `experiments/tier4_30e_multicore_lifecycle_hardware_smoke.py`.
    Board: `10.11.226.145`.
    Raw remote status: `pass`; ingest status: `pass`.
    Hardware criteria: 75/75; ingest criteria: 5/5.
    Result: `context_core`, `route_core`, `memory_core`, `learning_core`, and
    `lifecycle_core` all built/loaded/read back; non-lifecycle ownership guards
    passed; `canonical_32` and `boundary_64` lifecycle schedules matched
    reference; duplicate/stale lifecycle event rejection passed.
    Boundary: hardware smoke only; not lifecycle task benefit, not sham-control
    success, not speedup, not multi-chip scaling, not v2.2 temporal migration,
    and not a lifecycle baseline freeze.

43. ✅ **COMPLETE** - Tier 4.30f lifecycle sham-control hardware subset:
    fixed max pool, random event replay, mask shuffle, no trophic pressure, and
    no dopamine/plasticity over the canonical 32-event lifecycle trace. The C
    runtime implements behavioral sham semantics: fixed-pool suppresses
    active-mask mutation, random/mask controls remap lifecycle event slots,
    no-trophic suppresses trophic/maturity mutation, and no-dopamine removes
    the reward component from trophic updates. Local host tests included
    canonical sham-reference parity before upload, and the returned EBRAINS
    artifacts passed ingest.
    Prepared output: `controlled_test_output/tier4_30f_hw_20260505_prepared/`.
    Ingested output:
    `controlled_test_output/tier4_30f_hw_20260505_hardware_pass_ingested/`.
    Upload folder: `ebrains_jobs/cra_430f`.
    Runner: `experiments/tier4_30f_lifecycle_sham_hardware_subset.py`.
    JobManager command used:
    `cra_430f/experiments/tier4_30f_lifecycle_sham_hardware_subset.py --mode run-hardware --output-dir tier4_30f_hw_job_output`.
    Board: `10.11.227.9`.
    Raw remote status: `pass`; ingest status: `pass`.
    Hardware criteria: 185/185; ingest criteria: 5/5.
    Returned artifacts preserved: 35.
    Result: all five profiles built and loaded; hardware target acquisition
    succeeded through the PyNN/sPyNNaker probe path; enabled mode stayed
    canonical; fixed-pool separated active-mask bits and suppressed mask
    mutation counters; random replay separated lineage checksum; active-mask
    shuffle separated active-mask bits; no-trophic and no-dopamine/no-plasticity
    separated trophic checksums; compact lifecycle payload length stayed 68;
    synthetic fallback remained zero.
    Boundary: compact lifecycle sham-control hardware subset only; not
    lifecycle task-benefit, full Tier 6.3 hardware, speedup, multi-chip scaling,
    v2.2 temporal migration, or a lifecycle baseline freeze.

44. ✅ **COMPLETE** - Tier 4.30g lifecycle task-benefit/resource bridge local
    contract/reference:
    defined the bounded bridge from native lifecycle summary state into a
    task-bearing path before hardware packaging. Enabled lifecycle opened the
    bridge gate; fixed-pool, random replay, active-mask shuffle, no-trophic,
    and no-dopamine/no-plasticity controls closed it.
    Output:
    `controlled_test_output/tier4_30g_20260506_lifecycle_task_benefit_resource_bridge/`.
    Runner: `experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py`.
    Criteria: 9/9.
    Result: enabled tail accuracy `1.0`; control tail-accuracy ceiling `0.375`;
    enabled-control margin `0.625`; resource/readback fields declared.
    Boundary: local contract/reference only; not hardware task-benefit
    evidence, not autonomous lifecycle-to-learning MCPL, not speedup, not
    multi-chip scaling, not v2.2 temporal migration, and not a lifecycle
    baseline freeze.

45. ✅ **COMPLETE** - Tier 4.30g hardware task-benefit/resource bridge:
    returned EBRAINS artifacts passed raw hardware execution and formal ingest.
    Prepared output: `controlled_test_output/tier4_30g_hw_20260506_prepared/`.
    Ingested output: `controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/`.
    Upload folder: `ebrains_jobs/cra_430g`.
    Runner: `experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py`.
    Runner revision: `tier4_30g_lifecycle_task_benefit_resource_bridge_20260506_0001`.
    Board: `10.11.242.97`.
    Raw remote status: `pass`; ingest status: `pass`.
    Hardware criteria: 285/285; ingest criteria: 5/5.
    Returned artifacts preserved: 36.
    Result: enabled lifecycle opened the bounded task gate; fixed-pool,
    random replay, active-mask shuffle, no-trophic, and no-dopamine/no-plasticity
    controls closed it. Resource/readback accounting was returned for every mode.
    Enabled reference tail accuracy: `1.0`; control reference tail accuracy:
    `0.375`; compact lifecycle payload length: `68`; stale replies/timeouts: `0`.
    Boundary: host-ferried lifecycle task-benefit/resource bridge only; not
    autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip scaling,
    not v2.2 temporal migration, and not full organism autonomy.

46. ✅ **COMPLETE** - Freeze `CRA_LIFECYCLE_NATIVE_BASELINE_v0.4`.
    Baseline file: `baselines/CRA_LIFECYCLE_NATIVE_BASELINE_v0.4.md`.
    Registry snapshot: `baselines/CRA_LIFECYCLE_NATIVE_BASELINE_v0.4_STUDY_REGISTRY.snapshot.json`.
    Supersedes `CRA_NATIVE_MECHANISM_BRIDGE_v0.3` for lifecycle-native evidence.
    Freeze rule met: lifecycle telemetry, controls, resource accounting, and one
    bounded useful hardware task effect all passed. The organism/lifecycle claim
    remains bounded to static-pool lifecycle-native evidence with a host-ferried
    task bridge.

### Phase F - Native Temporal / Replay / Eligibility Bridge Decisions

47. ✅ **COMPLETE** - Tier 4.31a native temporal-substrate readiness:
    local pass, 24/24. The smallest first native v2.2 temporal subset is seven
    causal fixed-point EMA traces over current input; deltas and novelty are
    derived, not stored. Persistent state budget is 56 bytes; total initial
    trace/table budget is 112 bytes. This is contract/readiness only, not C
    implementation or hardware evidence.

48. ✅ **COMPLETE** - Tier 4.31b native temporal-substrate local fixed-point reference:
    local pass, 16/16. Fixed-point geomean MSE 0.22723731574965408 vs float
    reference 0.22752229502159751; fixed/float ratio 0.9987474666079806; max
    feature error 0.004646656591329457; selected saturation count 0; destructive
    controls separated. This authorizes source/runtime work, not hardware.

49. ✅ **COMPLETE** - Tier 4.31c native temporal-substrate source/runtime implementation:
    local pass, 17/17. The C runtime now owns seven EMA traces, the 4.31b ±2
    fixed-point trace range, alpha/decay constants, update/reset/sham counters,
    compact 48-byte temporal readback, command codes 39-42, ownership guards,
    and local C host tests. This authorizes hardware smoke preparation, not a
    baseline freeze.

50. ✅ **COMPLETE** - Tier 4.31d native temporal-substrate hardware smoke:
    one board, one seed, one minimal temporal-state task, explicit enabled versus
    zero/frozen/reset controls, compact payload_len=48, zero fallback, and real
    readback. Hardware pass ingested at
    `controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested/`.
    Board `10.11.216.121`; runner revision
    `tier4_31d_native_temporal_hardware_smoke_20260506_0003`; remote hardware
    criteria `59/59`; ingest criteria `5/5`; returned artifacts `28`;
    enabled/zero/frozen/reset scenarios all pass.
    First EBRAINS return was incomplete: two partial artifacts came back
    (`tier4_31d_test_profiles_stdout.txt`, `coral_reef (26).elf`) but no
    `tier4_31d_hw_results.json`, so it is not hardware evidence. The partial
    return is preserved at
    `controlled_test_output/tier4_31d_hw_20260506_incomplete_return/`. Re-run
    package revision `tier4_31d_native_temporal_hardware_smoke_20260506_0003`,
    which adds streamed build logs, build timeout, milestone breadcrumbs,
    partial-return ingest preservation, and structured exception finalization.
    Boundary: one-board hardware smoke only; not repeatability, speedup,
    benchmark superiority, multi-chip scaling, nonlinear recurrence, native
    replay/sleep, native macro eligibility, or full v2.2 hardware transfer.

51. ✅ **COMPLETE** - Tier 4.31e native replay-buffer / sleep-like replay
    and eligibility decision closeout:
    local pass, 15/15. Output:
    `controlled_test_output/tier4_31e_20260506_native_replay_eligibility_decision_closeout/`.
    Decision: native replay buffers, native sleep-like replay, and native macro
    eligibility are deferred until measured blockers exist; Tier 4.31f is
    deferred; Tier 4.32 mapping/resource modeling is authorized next; no
    baseline freeze. Boundary: local decision evidence only, not hardware, not
    implementation, not speedup, not multi-chip scaling, and not full v2.2
    hardware transfer.

52. Tier 4.31f native eligibility-trace implementation gate: DEFERRED by
    4.31e. Revisit macro/native eligibility only if a current promoted
    mechanism exposes a measured credit-assignment or on-chip timing blocker.
    Do not revive 5.9 by vibes alone.

### Phase G - Multi-Core And Multi-Chip Scaling

53. ✅ **COMPLETE** - Tier 4.32 native-runtime mapping/resource model:
    local pass, 23/23. Output:
    `controlled_test_output/tier4_32_20260506_mapping_resource_model/`.
    Consolidated measured 4.27-4.31 evidence into the current resource
    envelope: MCPL round trip `16` bytes vs SDP `54`; 48-event MCPL pressure
    `2304` bytes vs SDP `8064`; measured four-core pressure `43` events,
    `43` context slots, `10` max pending, `129/129` lookup request/reply
    parity, and zero stale/duplicate/timeout events; five-core lifecycle bridge
    measured `24` schedule uploads, `72/72` lookup request/reply parity,
    lifecycle compact payload `68`, temporal compact payload `48`, and positive
    returned profile ITCM/DTCM headroom. Decision: Tier 4.32a authorized next;
    Tier 4.32b-e remain blocked in order; no native-scale baseline freeze.

54. Tier 4.32a single-chip multi-core scale-stress preflight: **COMPLETED**.
    Local pass `19/19` at
    `controlled_test_output/tier4_32a_20260506_single_chip_scale_stress/`.
    It predeclared 4/5/8/12/16-core MCPL-first stress points but correctly
    blocked replicated 8/12/16-core shard stress because the current MCPL lookup
    key has no shard/group field and `dest_core` is reserved/ignored. It
    authorized only single-shard 4/5-core Tier 4.32a-hw, required Tier 4.32a-r1
    shard-aware MCPL before replicated stress, and kept
    4.32b/multi-chip/native-scale baseline freeze blocked.

55. Tier 4.32a-r0 protocol truth audit: **COMPLETED**. Local pass `10/10` at
    `controlled_test_output/tier4_32a_r0_20260506_protocol_truth_audit/`.
    This corrective audit blocked the planned MCPL-first 4.32a-hw package:
    confidence-gated learning still uses transitional SDP because MCPL replies
    drop confidence/hit status and MCPL receive hardcodes confidence=1.0. The
    audit also preserved the earlier shard blocker: the MCPL key has no
    shard/group field and `dest_core` is reserved/ignored.

56. Tier 4.32a-r1 confidence-bearing shard-aware MCPL lookup repair:
    **COMPLETED**. Local pass `14/14` at
    `controlled_test_output/tier4_32a_r1_20260506_mcpl_lookup_repair/`.
    MCPL now carries value plus confidence/hit/status metadata through
    value/meta packets; keys carry shard identity; learning receive no longer
    hardcodes confidence=1.0; identical seq/type cross-shard controls and
    wrong-shard negative controls pass; full/zero/half-confidence four-core
    local learning controls pass over MCPL.

57. Tier 4.32a-hw EBRAINS single-shard single-chip stress: COMPLETE. Hardware
    pass ingested at
    `controlled_test_output/tier4_32a_hw_20260507_hardware_pass_ingested/`.
    Board `10.11.215.185`; raw remote status `pass`; ingest status `pass`;
    `31/31` raw hardware criteria; `8/8` ingest criteria; `63` returned
    artifacts; point04 `48` events / `144` lookup replies; point05 `96` events
    / `288` lookup replies; zero stale replies, duplicate replies, timeouts,
    and synthetic fallback. Boundary: single-shard hardware stress only, not
    replicated-shard scaling and not a baseline freeze.

58. Tier 4.32a-hw-replicated replicated-shard EBRAINS single-chip stress:
    COMPLETE. Hardware pass ingested at
    `controlled_test_output/tier4_32a_hw_replicated_20260507_hardware_pass_ingested/`.
    Board `10.11.215.121`; raw remote status `pass`; ingest status `pass`;
    `185/185` raw hardware criteria; `9/9` ingest criteria; `80` returned
    artifacts. `point_08c_dual_shard` passed with `2` shards, `192` total events,
    and `288` lookup replies per shard. `point_12c_triple_shard` passed with
    `3` shards, `384` total events, and `384` lookup replies per shard.
    `point_16c_quad_shard` passed with `4` shards, `512` total events, and
    `384` lookup replies per shard. All points reported zero stale replies,
    duplicate replies, timeouts, and synthetic fallback. Boundary: single-chip
    replicated-shard stress only, not static reef partition proof, not
    multi-chip, not speedup, and not a baseline freeze.

59. Tier 4.32b static reef partition smoke/resource mapping: COMPLETE. Local
    pass `25/25` at
    `controlled_test_output/tier4_32b_20260507_static_reef_partition_smoke/`.
    Canonical `quad_mechanism_partition_v0` maps four static reef partitions to
    the measured point16 16-core replicated envelope, assigns static polyp slots
    `0-7` two per partition, preserves `384/384` lookup parity per partition,
    rejects one-polyp-one-chip as unsupported, and blocks quad partition plus a
    dedicated lifecycle core at `17` cores on one conservative single-chip
    envelope. Boundary: local static partition/resource evidence only, not a
    new hardware run, not speedup, not multi-chip, and not a baseline freeze.

60. Tier 4.32c inter-chip feasibility contract: COMPLETE. Local pass `19/19`
    at `controlled_test_output/tier4_32c_20260507_interchip_feasibility_contract/`.
    It defines required board/chip/core/role/partition/shard/seq identity fields,
    remote split-role MCPL lookup paths, compact readback ownership, failure
    classes, and the exact two-chip split-role single-shard smoke target. True
    two-partition cross-chip learning remains blocked until origin/target shard
    semantics are defined. Boundary: local
    contract evidence only, not hardware, not speedup, not multi-chip learning,
    and not a baseline freeze.

61. Tier 4.32d-r0 inter-chip route/source/package audit: COMPLETE. Local pass
    `10/10` at
    `controlled_test_output/tier4_32d_r0_20260507_interchip_route_source_audit/`.
    It confirms MCPL key/value/meta packet construction is source-backed, but
    blocks the EBRAINS package because `cra_state_mcpl_init()` currently routes
    request/reply keys to local cores only and lacks explicit inter-chip link
    routing. Boundary: local audit evidence only, not hardware and not an upload
    package.

62. Tier 4.32d-r1 inter-chip MCPL route repair/local QA: COMPLETE. Local pass
    `14/14` at
    `controlled_test_output/tier4_32d_r1_20260507_interchip_route_repair_local_qa/`.
    It adds/proves explicit route-link entries for the two-chip split-role
    single-shard smoke: learning-core outbound request link routes, state-core
    local request delivery, and state-core outbound value/meta reply link routes.
    Existing MCPL lookup and four-core MCPL regressions still pass. Boundary:
    local route/source QA only, not hardware and not an upload package.

63. ✅ **COMPLETE** - Tier 4.32d first two-chip split-role single-shard
    MCPL lookup hardware smoke: HARDWARE PASS / INGEST PASS. Prepared output:
    `controlled_test_output/tier4_32d_20260507_prepared/`; ingested output:
    `controlled_test_output/tier4_32d_20260507_hardware_pass_ingested/`.
    Returned EBRAINS run used source/learning chip `(0,0)`, remote state chip
    `(1,0)`, shard `0`, 32 events, and 96 expected lookup replies. Result:
    raw remote status `pass`, ingest status `pass`, 7/7 ingest criteria, 96/96
    lookup replies, zero stale replies, zero duplicate replies, zero timeouts,
    compact readback, zero synthetic fallback, and 40 returned artifacts
    preserved. Boundary: communication and
    readback smoke only; not speedup, not benchmark evidence, not true
    two-partition learning, not lifecycle scaling, not multi-shard learning,
    and not a native-scale baseline freeze.

64. ✅ **COMPLETE** - Tier 4.32e multi-chip learning micro-task:
    HARDWARE PASS / INGEST PASS. Prepared output:
    `controlled_test_output/tier4_32e_20260507_prepared/`; ingested output:
    `controlled_test_output/tier4_32e_20260507_hardware_pass_ingested/`.
    Returned EBRAINS run used board `10.11.205.161`, source/learning chip
    `(0,0)`, remote state chip `(1,0)`, shard `0`, two cases, 32 events per
    case, and 96 expected lookup replies per case. Result: raw remote status
    `pass`, ingest status `pass`, 96/96 lookup replies in both cases, zero
    stale replies, zero duplicate replies, zero timeouts, compact readback,
    zero synthetic fallback, and 42 returned artifacts preserved. Enabled LR
    0.25 matched readout `32768/0`; no-learning LR 0.0 stayed `0/0`. Boundary:
    two-chip single-shard learning micro-task only; not speedup, not benchmark
    evidence, not true two-partition learning, not lifecycle scaling, not
    multi-shard learning, and not a native-scale baseline freeze.

65. ✅ **COMPLETE** - Tier 4.32f multi-chip resource/lifecycle decision
    contract: local pass `22/22` at
    `controlled_test_output/tier4_32f_20260507_multichip_resource_lifecycle_decision/`.
    It selected multi-chip lifecycle traffic with resource counters as the next
    direction after the 4.32e learning pass, classified that lifecycle
    inter-chip route entries are not yet source-proven, authorized Tier 4.32g-r0
    source/route repair audit next, and blocked immediate 4.32g hardware
    packaging.

66. ✅ **COMPLETE** - Tier 4.32g-r0 multi-chip lifecycle route/source repair
    audit: local pass `14/14` at
    `controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit/`.
    It source-proved lifecycle event request, trophic update, and active-mask/
    lineage sync MCPL routes for learning/lifecycle profiles, passed the new
    lifecycle inter-chip route C test plus lookup-route and lifecycle-split
    regressions, authorized Tier 4.32g hardware package preparation, and kept
    true partition semantics, speedup, benchmarks, multi-shard learning, and
    native-scale baseline freeze blocked.

67. ✅ **COMPLETE** - Tier 4.32g-r2 two-chip lifecycle traffic/resource
    hardware smoke: HARDWARE PASS / INGEST PASS. Ingested output:
    `controlled_test_output/tier4_32g_20260508_hardware_pass_ingested/`.
    Returned runner revision
    `tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003`,
    proving EBRAINS ran the cache-proof repaired package rather than the stale
    `cra_432g` package. Board target `10.11.205.177`; source learning core
    `(0,0,p7)`; remote lifecycle core `(1,0,p4)`. Result: raw hardware status
    `pass`, ingest status `pass`, source event/trophic requests `1/1`, source
    active-mask sync received `1`, lifecycle accepted trophic+death events `2`,
    lifecycle mask sync sent `1`, active mask/count/death/trophic counters `1`,
    reset/pause controls passed, payload lengths `>=149`, zero stale replies,
    zero duplicate replies, zero missing ACKs, zero synthetic fallback, and
    `30` returned artifacts preserved. Boundary: two-chip lifecycle
    traffic/resource smoke only; not lifecycle scaling, speedup, benchmark
    evidence, true partitioned ecology, multi-shard learning, or a
    native-scale baseline freeze.

68. ✅ **COMPLETE** - Tier 4.32h native-scale evidence closeout /
    baseline decision. Local closeout passed `64/64` criteria at
    `controlled_test_output/tier4_32h_20260508_native_scale_evidence_closeout/`
    and froze `CRA_NATIVE_SCALE_BASELINE_v0.5` under `baselines/`. The freeze
    consumes the 4.32a replicated single-chip stress, 4.32d two-chip
    communication smoke, 4.32e two-chip learning micro-task, and 4.32g two-chip
    lifecycle traffic/resource pass. Boundary: substrate baseline only; not
    speedup, benchmark usefulness, true two-partition learning, lifecycle
    scaling, multi-shard learning, or AGI/ASI evidence.

### Phase H - Software Usefulness And Final Baselines

69. **COMPLETE / PARTIALLY BLOCKED** - Tier 7.0e standardized dynamical
    benchmark rerun with run-length/training-budget sweep:
    the runner `experiments/tier7_0e_standard_dynamical_v2_2_sweep.py` now has
    two modes: `scoreboard` for long public-benchmark exposure and
    `full_diagnostic` for shorter raw-CRA/sham audits. The 720/2000
    calibration at
    `controlled_test_output/tier7_0e_20260508_length_calibration/` passed
    8/8 criteria and showed v2.2 improved strongly versus raw v2.1 but remained
    noncompetitive with the ESN baseline. The 10k scoreboard attempt at
    `controlled_test_output/tier7_0e_20260508_length_10000_scoreboard/` failed
    7/8 criteria because NARMA10 seed 44 generated 1,688 non-finite target
    values. This is a benchmark-stream validity blocker, not a CRA model pass
    or failure. No v2.3 freeze, usefulness claim, or hardware transfer is
    authorized from Tier 7.0e.

70. **COMPLETE** - Tier 7.0f benchmark-protocol repair and public failure
    localization: passed 8/8 at
    `controlled_test_output/tier7_0f_20260508_benchmark_protocol_failure_localization/`.
    It confirmed the 10k NARMA10 seed-44 finite-stream blocker, selected
    `8000` as the largest original-seed finite rerun length, and localized the
    current public benchmark gap: Mackey-Glass/Lorenz favor ESN/offline
    train-prefix readout, while NARMA10 favors explicit lag memory over v2.2
    fading memory. This is diagnostic evidence only, not a new mechanism,
    baseline freeze, hardware evidence, or benchmark-superiority claim.

71. **COMPLETE** - Tier 7.0e valid same-seed 8000-step scoreboard rerun:
    `controlled_test_output/tier7_0e_20260508_length_8000_scoreboard/` passed
    8/8 with zero invalid streams. v2.2 ranked second overall at aggregate
    geomean MSE `0.19348969000027122`, beating lag-only LMS
    `0.1986311714577415` and random reservoir `0.2075278737499566`, but ESN
    remained far ahead at `0.020109884207162095`. This answers the immediate
    "longer run" question: longer exposure alone did not close the public
    scoreboard gap.

72. **COMPLETE** - Tier 7.0g general mechanism-selection contract:
    passed 7/7 at
    `controlled_test_output/tier7_0g_20260508_general_mechanism_selection_contract/`.
    It selected `bounded_nonlinear_recurrent_continuous_state_interface` as the
    next planned mechanism because the measured public gap is nonlinear
    recurrent state / readout-interface strength, not sleep/replay, lifecycle,
    or hardware transfer. Boundary: contract only, not mechanism proof.

73. **COMPLETE** - Tier 7.0h bounded nonlinear recurrent
    continuous-state/interface gate: passed 10/10 at
    `controlled_test_output/tier7_0h_20260508_bounded_recurrent_interface_gate/`.
    The candidate materially improved valid 8000-step aggregate geomean MSE
    versus v2.2 (`0.09530752189727928` vs `0.19348969000027122`), beat
    lag-only and random-reservoir online controls, and narrowed the ESN gap.
    Boundary: promotion is blocked because recurrence/topology controls did not
    separate; the permuted-recurrence sham stayed close with only
    `1.036590722013174` margin at 8000. No baseline freeze, hardware transfer,
    native migration, or ESN-superiority claim is authorized.

74. **COMPLETE** - Tier 7.0i recurrence/topology specificity repair gate:
    passed 11/11 at
    `controlled_test_output/tier7_0i_20260508_recurrence_topology_specificity_gate/`.
    Structured bounded recurrence improved valid 8000-step aggregate geomean
    MSE versus v2.2 (`0.09964414908204765` vs `0.19348969000027122`), but did
    not beat the generic 7.0h recurrent reference (`0.09530752189727928`).
    Destructive controls separated; topology controls did not separate.
    Boundary: topology-specific recurrence is not supported on this public
    suite. No baseline freeze, hardware transfer, native migration, ESN
    superiority, or topology-specific claim is authorized.

75. **COMPLETE** - Tier 7.0j generic bounded recurrent-state promotion /
    compact regression gate: passed 14/14 at
    `controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate/`.
    Full NEST compact regression passed. The narrow generic bounded recurrent
    continuous-state interface is frozen as software baseline `v2.3`.
    Boundary: v2.3 does not claim topology-specific recurrence, ESN
    superiority, hardware transfer, native migration, language, planning, AGI,
    or ASI.

76. **COMPLETE** - Tier 6.2a targeted hard-task validation over v2.3:
    passed 12/12 at
    `controlled_test_output/tier6_2a_20260508_targeted_usefulness_validation/`.
    v2.3 was best only on `variable_delay_multi_cue`, beat v2.2 only on that
    task, and separated from shams on three tasks. v2.2 won the aggregate
    targeted hard-task geomean (`0.15892013746238234` vs v2.3
    `0.17604715537423876`). Classification:
    `v2_3_partial_regime_signal_next_needs_failure_specific_mechanism_or_7_1_probe`.
    Boundary: diagnostic hard tasks only; no new baseline freeze, no public
    usefulness claim, and no hardware/native transfer.

77. **COMPLETE** - Tier 7.1a real-ish/public adapter contract:
    passed 12/12 at
    `controlled_test_output/tier7_1a_20260508_realish_adapter_contract/`.
    It selected `nasa_cmapss_rul_streaming` as the first public/real-ish
    adapter family to test the Tier 6.2a variable-delay signal under fixed
    sources, splits, metrics, baselines, leakage controls, and nonclaims.
    Boundary: contract only; no C-MAPSS score, no public usefulness claim, no
    baseline freeze, and no hardware/native transfer.

78. **COMPLETE** - Tier 7.1b NASA C-MAPSS source/data preflight:
    passed 16/16 at
    `controlled_test_output/tier7_1b_20260508_cmapss_source_data_preflight/`.
    It verified the official NASA C-MAPSS zip, SHA256
    `74bef434a34db25c7bf72e668ea4cd52afe5f2cf8e44367c55a82bfd91a5a34f`,
    FD001 schema and row counts, train-only normalization, prediction-before-
    update stream rows, and label-separated smoke artifacts. Boundary:
    preflight only; no C-MAPSS scoring, public usefulness claim, baseline
    freeze, or hardware/native transfer.

79. **COMPLETE** - Tier 7.1c compact C-MAPSS FD001 scoring gate:
    passed 12/12 at
    `controlled_test_output/tier7_1c_20260508_cmapss_fd001_scoring_gate/`.
    Outcome: `v2_3_no_public_adapter_advantage`. The monotone age-to-RUL ridge
    baseline won with test RMSE `46.10944999532139`; v2.3 ranked `5` with RMSE
    `49.4908802462679` and did not beat v2.2 (`48.739451335025144`). Boundary:
    compact scalar-adapter software scoring only; no public usefulness win, no
    baseline freeze, and no hardware/native transfer.

80. **COMPLETE** - Tier 7.1d C-MAPSS failure analysis / adapter repair:
    passed 14/14 at
    `controlled_test_output/tier7_1d_20260508_cmapss_failure_analysis_adapter_repair/`.
    Outcome: `compact_failure_partly_readout_or_target_policy`. Capped RUL and
    ridge readout repaired most of the compact scalar failure; v2.2 ridge capped
    was the best promotable model with RMSE `20.271418942340336`, narrowly ahead
    of lag-multichannel ridge RMSE `20.305268771358435`. v2.3 still did not win.
    Boundary: failure analysis only; no public usefulness win, no baseline
    freeze, and no hardware/native transfer.

81. **COMPLETE** - Tier 7.1e C-MAPSS capped-RUL/readout fairness confirmation:
    passed 12/12 at
    `controlled_test_output/tier7_1e_20260508_cmapss_capped_readout_fairness_confirmation/`.
    Outcome: `v2_2_capped_signal_not_statistically_confirmed`. The primary
    paired per-unit comparison versus lag-multichannel ridge had mean delta
    `-0.3690103080637045` RMSE (positive would mean candidate better), bootstrap
    95% CI `[-1.4191012103865384, 0.6704668696286052]`, effect size
    `-0.06884079972999842`, and a 50/50 better/worse unit split. Boundary:
    fairness/statistical confirmation only; no public usefulness win, no
    baseline freeze, and no hardware/native transfer.

82. **COMPLETE** - Tier 7.1f next public adapter contract / family selection:
    passed 10/10 at
    `controlled_test_output/tier7_1f_20260508_next_public_adapter_contract/`.
    It selected `numenta_nab_streaming_anomaly` as the next public adapter
    family after C-MAPSS non-promotion. Boundary: contract only; no NAB data
    preflight, no scoring, no public usefulness claim, no baseline freeze, and
    no hardware/native transfer.

83. **COMPLETE** - Tier 5.20a resonant branch polyp internal-model diagnostic:
    passed 11/11 as a harness at
    `controlled_test_output/tier5_20a_20260508_resonant_branch_polyp_diagnostic/`,
    but the full 16-resonant-branch proxy was not promoted. It helped
    `variable_delay_multi_cue` and slightly helped `anomaly_detection_stream`,
    but materially regressed Mackey-Glass, Lorenz, NARMA10, and
    hidden-context reentry versus v2.3. Boundary: optional software diagnostic
    only; no core polyp replacement, no baseline freeze, and no hardware/native
    transfer.

84. **COMPLETE** - Tier 5.20b hybrid resonant/LIF polyp diagnostic:
    passed 12/12 as a harness at
    `controlled_test_output/tier5_20b_20260508_hybrid_resonant_polyp_diagnostic/`,
    but neither same-budget hybrid earned promotion. The best candidate,
    `hybrid_8_lif_8_resonant`, had all-task geomean MSE
    `0.2852846857844163` versus v2.3 `0.2610804850928049`, two task wins, two
    material regressions, and only one sham-separated task. The 12/4 hybrid
    had fewer regressions but weaker wins. Boundary: optional software repair
    diagnostic only; do not integrate into the core organism yet.

85. **COMPLETE** - Tier 5.20c minimal hybrid resonant/LIF polyp diagnostic:
    passed 10/10 as a harness at
    `controlled_test_output/tier5_20c_20260508_minimal_resonant_polyp_diagnostic/`,
    but the 14 LIF / 2 resonant variant was not promoted. It had all-task
    geomean MSE `0.2777975100580056` versus v2.3 `0.2610804850928049`, zero
    task wins, one material regression, and zero sham-separated tasks.

86. **COMPLETE** - Tier 5.20d resonant-heavy hybrid LIF polyp diagnostic:
    passed 10/10 as a harness at
    `controlled_test_output/tier5_20d_20260508_resonant_heavy_polyp_diagnostic/`,
    but the 4 LIF / 12 resonant variant was not promoted. It had all-task
    geomean MSE `0.29289224348599796` versus v2.3 `0.2610804850928049`, three
    task wins, two material regressions, and two sham-separated tasks.

87. **COMPLETE** - Tier 5.20e near-full resonant hybrid LIF polyp diagnostic:
    passed 10/10 as a harness at
    `controlled_test_output/tier5_20e_20260508_near_full_resonant_polyp_diagnostic/`,
    but the 2 LIF / 14 resonant variant was not promoted. It had all-task
    geomean MSE `0.30374770797663714` versus v2.3 `0.2610804850928049`, three
    task wins, three material regressions, and two sham-separated tasks.
    Decision: the current resonant dose sweep covers 16/0, 14/2, 12/4, 8/8,
    4/12, 2/14, and 0/16; no resonant variant is promoted.

88. **COMPLETE** - Tier 7.1g NAB source/data/scoring preflight:
    passed 24/24 at
    `controlled_test_output/tier7_1g_20260508_nab_source_data_scoring_preflight/`.
    It pinned official NAB commit
    `ea702d75cc2258d9d7dd35ca8e5e2539d71f3140`, cached official source/data/
    label/scoring files under ignored `.cra_data_cache/`, parsed five selected
    streams, documented one raw-order chronology irregularity, emitted
    adapter-sorted chronological smoke rows, separated 12 anomaly windows into
    offline scoring artifacts, and documented scoring-interface feasibility.
    Boundary: preflight only; no NAB scoring, usefulness claim, freeze, or
    hardware transfer.

89. **COMPLETE** - Tier 7.1h compact NAB scoring gate:
    passed 16/16 at
    `controlled_test_output/tier7_1h_20260508_compact_nab_scoring_gate/`.
    It scored the pinned compact NAB subset with label-separated online anomaly
    scores, fair online baselines, CRA v2.2/v2.3 detectors, v2.3 shams, and
    bootstrap support. Outcome:
    `v2_3_partial_nab_signal_requires_confirmation`. v2.3 ranked second,
    beating v2.2 (`0.22649365525011686` versus `0.19995024953915835`) and all
    three v2.3 shams, but it did not beat the fixed random-reservoir online
    residual baseline (`0.23437791375440906`), and the paired bootstrap CI
    against that baseline crossed zero (`[-0.03766786485787427,
    0.015726447281909233]`). Boundary: compact software scoring only; no full
    NAB benchmark claim, public usefulness proof, freeze, or hardware/native
    transfer.

90. **COMPLETE** - Tier 7.1i NAB fairness/statistical confirmation or failure
    localization:
    passed 18/18 at
    `controlled_test_output/tier7_1i_20260508_nab_fairness_confirmation/`.
    It broadened NAB scoring to 20 streams across 6 categories. Outcome:
    `v2_3_nab_signal_localized_not_confirmed`. v2.3 beat v2.2
    (`0.09880252815842962` versus `0.08150013601217254`) and all three shams,
    but rolling z-score ranked first (`0.140951459207744`) and v2.3 ranked
    fourth. Bootstrap versus the best external baseline crossed zero
    (`[-0.13027269733009264, 0.03602365729899069]`). The signal localized to
    realAdExchange and two streams. Boundary: broader NAB software
    confirmation/localization only; no public usefulness proof, freeze, or
    hardware/native transfer.

91. **COMPLETE** - Tier 7.1j NAB failure/localization analysis:
    passed 12/12 at
    `controlled_test_output/tier7_1j_20260508_nab_failure_localization/`.
    Failure class: `threshold_or_fp_penalty_sensitive`. Under the default
    policy rolling z-score still wins (`0.140951459207744`), but v2.3 ranks
    third within the key diagnostic subset (`0.09880252815842962`), wins 3/15
    policy cells, and beats rolling z-score in 5/15 policy cells. Component
    deltas show v2.3 has better event-F1 and window recall, but worse
    false-positive/NAB-style pressure. Boundary: software failure analysis only;
    no public usefulness proof, freeze, or hardware/native transfer.

92. **COMPLETE** - Tier 7.1k NAB adapter/readout false-positive repair:
    passed 9/9 at
    `controlled_test_output/tier7_1k_20260508_nab_false_positive_repair/`.
    Outcome: `v2_3_nab_false_positive_repair_candidate`. The same-subset
    `persist3` no-label alarm policy made v2.3 rank first on the broad NAB
    diagnostic subset (`0.44632600314828624` primary score), reduced FP/1000
    from `16.537437704270094` to `2.5685172711420603`, beat rolling z-score
    and v2.2 under that policy, and separated all three shams. Boundary:
    policy was selected on the same broad subset and window recall dropped
    versus raw v2.3, so no public usefulness proof, freeze, or hardware/native
    transfer is authorized.

93. **COMPLETE** - Tier 7.1l NAB locked-policy holdout confirmation:
    passed 13/13 at
    `controlled_test_output/tier7_1l_20260508_nab_locked_policy_holdout_confirmation/`.
    Outcome: `v2_3_locked_policy_reduced_fp_but_not_confirmed`. The locked
    `persist3` policy reduced v2.3 FP/1000 versus raw v2.3 on held-out streams,
    but v2.3 ranked fifth, did not beat rolling z-score or v2.2, and separated
    only two of three shams. Boundary: this narrows the NAB claim and blocks any
    public usefulness proof, freeze, or hardware/native transfer from the 7.1k
    same-subset repair.

94. **COMPLETE** - Tier 7.1m NAB closeout / mechanism-return decision:
    passed 13/13 at
    `controlled_test_output/tier7_1m_20260508_nab_closeout_mechanism_return_decision/`.
    Outcome: `nab_claim_narrowed_return_to_general_mechanisms`. The NAB chain
    is narrowed to partial/local signal only; no public usefulness proof,
    baseline freeze, or hardware/native transfer is authorized. Adapter-policy
    tuning is stopped, and the selected next gate is Tier 7.4a cost-aware
    policy/action selection.

95. **COMPLETE** - Tier 7.4a cost-aware policy/action selection contract:
    passed 13/13 at
    `controlled_test_output/tier7_4a_20260509_cost_aware_policy_action_contract/`.
    Contract defined state -> action -> delayed consequence tasks, asymmetric
    false-positive/missed-event/latency costs, abstain/act/wait actions, fair
    policy baselines, shams, ablations, metrics, pass/fail criteria, and
    compact-regression requirements.

96. **COMPLETE** - Tier 7.4b cost-aware policy/action local diagnostic:
    passed 15/15 at
    `controlled_test_output/tier7_4b_20260509_cost_aware_policy_action_local_diagnostic/`.
    The local v2.3 cost-aware policy ranked first among non-oracle models,
    beat the best external baseline by expected utility (`18.046296296296294`
    versus `5.924382716049381`), won 2/3 task families versus the best
    external baseline, separated shams/ablations, and avoided no-action
    collapse. Boundary: candidate software evidence only; no freeze and no
    hardware/native transfer.

97. **COMPLETE** - Tier 7.4c cost-aware policy/action promotion + compact
    regression gate:
    passed 16/16 at
    `controlled_test_output/tier7_4c_20260509_cost_aware_policy_action_promotion_gate/`.
    The locked 7.4b candidate preserved expected-utility advantage,
    sham/ablation separation, no-action checks, and leakage guards, then passed
    full NEST compact regression. `CRA_EVIDENCE_BASELINE_v2.4` is frozen.
    Boundary: host-side software policy/action baseline only; no public
    usefulness claim and no hardware/native transfer.

98. **COMPLETE** - Tier 7.4d cost-aware policy/action held-out/public
    usefulness contract:
    passed 20/20 at
    `controlled_test_output/tier7_4d_20260509_cost_aware_policy_action_heldout_contract/`.
    The gate locks public/real-ish action-cost task families, fixed costs,
    action set, split/leakage rules, baselines, shams/ablations, statistics,
    failure classes, and artifacts before v2.4 held-out scoring. Boundary:
    contract only; no scoring, no public usefulness proof, no new freeze, and
    no hardware/native transfer.

99. **COMPLETE** - Tier 7.4e cost-aware policy/action held-out
    scoring preflight:
    passed 20/20 at
    `controlled_test_output/tier7_4e_20260509_cost_aware_policy_action_heldout_preflight/`.
    The gate verifies source/split/cost/schema readiness before scoring:
    public NAB/C-MAPSS source preflights, disjoint held-out splits, fixed cost
    model, online/offline label separation, baseline/sham inventories, scoring
    schemas, and expected next-gate artifacts. Boundary: no performance score,
    no public usefulness proof, no new freeze, and no hardware/native transfer.

100. **COMPLETE** - Tier 7.4f cost-aware policy/action held-out
    scoring gate:
    passed 20/20 at
    `controlled_test_output/tier7_4f_20260509_cost_aware_policy_action_heldout_scoring_gate/`.
    Outcome `v2_4_heldout_public_action_usefulness_qualified_cmapss_only`: v2.4
    ranked first on C-MAPSS maintenance utility and beat the strongest external
    baseline, but NAB did not confirm and C-MAPSS did not separate from v2.2
    with a positive paired CI. Boundary: qualified C-MAPSS-only public-action
    signal; no broad public usefulness claim, no incremental v2.4 superiority
    claim, no freeze, and no hardware/native transfer.

101. **COMPLETE** - Tier 7.4g held-out policy/action confirmation +
    reference separation:
    passed 20/20 at
    `controlled_test_output/tier7_4g_20260509_policy_action_confirmation_reference_separation/`.
    Outcome `cmapss_external_signal_confirmed_reference_not_separated_nab_failed`:
    the narrow C-MAPSS external/sham action-cost signal was confirmed, v2.4
    still did not separate from v2.2 with a positive paired CI, and NAB remained
    an event-coverage non-confirmation. Boundary: no broad public usefulness
    claim, no incremental v2.4 superiority claim, no freeze, and no
    hardware/native transfer.

102. **COMPLETE** - Tier 7.4h policy/action attribution closeout /
    mechanism return decision:
    passed 16/16 at
    `controlled_test_output/tier7_4h_20260509_policy_action_attribution_closeout/`.
    Outcome `policy_action_track_closed_narrow_cmapss_signal_return_to_mechanism_benchmark_loop`:
    the narrow C-MAPSS action-cost signal is preserved, broad public usefulness
    and incremental v2.4-over-v2.2 claims are blocked, freeze/hardware transfer
    are blocked, and Tier 7.5a is selected next.

103. **COMPLETE** - Tier 7.5a curriculum / environment generator contract:
    passed 16/16 at
    `controlled_test_output/tier7_5a_20260509_curriculum_environment_contract/`.
    Outcome `curriculum_environment_contract_locked_no_scoring`: generated task
    families, difficulty schedule, hidden holdout splits, baselines, leakage
    guards, metrics, pass/fail gates, and future artifacts are locked before
    implementation/scoring.

104. **COMPLETE** - Tier 7.5b curriculum / environment generator
    implementation preflight:
    passed 16/16 at
    `controlled_test_output/tier7_5b_20260509_curriculum_environment_preflight/`.
    Outcome `curriculum_generator_preflight_materialized_no_scoring`:
    deterministic generated streams, split manifests, hidden-label hashes,
    schema contracts, baseline compatibility rows, and leakage checks are
    materialized without scoring CRA or exposing hidden holdout labels.

105. **COMPLETE** - Tier 7.5c curriculum / environment generator scoring gate:
    passed 17/17 at
    `controlled_test_output/tier7_5c_20260509_curriculum_environment_scoring_gate/`.
    Outcome `generated_family_signal_confirmed_requires_attribution_gate`:
    current CRA v2.4 confirmed generated-family software signal on 6/6 locked
    synthetic curriculum families against fair external baselines, the v2.2
    reference, and shams/ablations. Boundary: generated synthetic diagnostic
    only; no public usefulness claim, no freeze, and no hardware/native transfer.

106. **COMPLETE** - Tier 7.5d curriculum / environment score attribution and
    promotion decision:
    passed 18/18 at
    `controlled_test_output/tier7_5d_20260509_curriculum_environment_attribution_closeout/`.
    Outcome `synthetic_mechanism_attribution_supported_no_freeze`: synthetic
    keyed/compositional mechanism attribution is supported on 6/6 generated
    families, near-oracle generator-feature alignment risk is documented on 6/6,
    and public-usefulness/freeze/hardware-transfer claims are blocked.

107. **COMPLETE** - Tier 7.6a long-horizon planning / subgoal-control contract:
    passed 19/19 at
    `controlled_test_output/tier7_6a_20260509_long_horizon_planning_contract/`.
    Outcome `long_horizon_planning_contract_locked_no_scoring`: 5 task
    families, 4 splits, 9 baselines, 9 shams, metrics, leakage guards, pass/fail
    gates, nonclaims, and expected artifacts are locked before implementation.

108. **COMPLETE** - Tier 7.6b long-horizon planning / subgoal-control
    local diagnostic:
    passed 19/19 at
    `controlled_test_output/tier7_6b_20260509_long_horizon_planning_local_diagnostic/`.
    Outcome `subgoal_control_local_diagnostic_candidate_supported_requires_attribution`:
    local scaffold signal is supported on aggregate against the strongest
    non-oracle baseline with positive paired support, beats v2.4 reactive
    references on at least three families, and separates destructive shams. The
    strict per-family signal is 3/5, so attribution/promotion is mandatory.

109. **COMPLETE** - Tier 7.6c long-horizon planning / subgoal-control
    attribution + promotion decision:
    passed 17/17 at
    `controlled_test_output/tier7_6c_20260509_long_horizon_planning_attribution_closeout/`.
    Outcome `planning_scaffold_signal_preserved_no_promotion`: the 7.6b local
    scaffold signal is preserved as diagnostic evidence, but promotion/freeze/
    hardware transfer are blocked by high feature-alignment risk, strict support
    of only 3/5 families, and missing reduced-feature generalization.

110. **COMPLETE** - Tier 7.6d reduced-feature planning generalization /
    task repair:
    passed 18/18 at
    `controlled_test_output/tier7_6d_20260509_reduced_feature_planning_generalization/`.
    Outcome `reduced_feature_planning_signal_supported_requires_promotion_gate`:
    raw keys were hidden, only aliased/coarse features were available, aggregate
    support remained positive, both prior weak families were repaired, and 4/5
    families supported the signal. No freeze or hardware/native transfer.

111. **COMPLETE** - Tier 7.6e planning/subgoal-control promotion +
    compact regression gate:
    passed 20/20 at
    `controlled_test_output/tier7_6e_20260509_planning_promotion_compact_regression/`.
    Outcome `reduced_feature_planning_ready_for_v2_5_freeze`: locked Tier 7.6d
    support survived full NEST compact regression, `CRA_EVIDENCE_BASELINE_v2.5`
    is frozen as bounded host-side software planning/subgoal-control evidence,
    and hardware/native transfer plus broad planning claims remain blocked.

112. **COMPLETE** - Tier 7.7a v2.5 standardized benchmark/usefulness scoreboard
    contract:
    passed 20/20 at
    `controlled_test_output/tier7_7a_20260509_v2_5_standardized_scoreboard_contract/`.
    The primary scoreboard is locked as Mackey-Glass, Lorenz, and NARMA10 at
    8000 steps, horizon 8, seeds 42/43/44, chronological 65/35 split. C-MAPSS
    FD001 and NAB are secondary public/real-ish confirmation tracks only. This
    is contract/pre-registration evidence only, not a benchmark score, public
    usefulness claim, new freeze, or hardware/native transfer.

113. **COMPLETE** - Tier 7.7b v2.5 standardized benchmark/usefulness
    scoreboard scoring gate:
    passed 15/15 at
    `controlled_test_output/tier7_7b_20260509_v2_5_standardized_scoreboard_scoring_gate/`.
    Outcome `standardized_progress_pass`: frozen v2.5 improved the locked
    8000-step Mackey-Glass/Lorenz/NARMA10 aggregate versus v2.3
    (`0.0735414741` geomean MSE versus `0.0951071342`, ratio `1.2932448715`,
    paired delta CI `0.0197948122` to `0.0244083440`). The signal is
    one-task-driven: Mackey-Glass improved strongly, while Lorenz and NARMA10
    were flat/slightly worse, and ESN/online-linear/ridge baselines still beat
    v2.5 on aggregate. No freeze or hardware/native transfer is authorized.

114. **COMPLETE** - Tier 7.7c standardized long-run/failure localization
    contract:
    passed 15/15 at
    `controlled_test_output/tier7_7c_20260509_standardized_long_run_failure_contract/`.
    It locks required stream lengths 8000/16000/32000, optional diagnostic
    length 50000, same tasks/seeds/splits, explicit shams, expected artifacts,
    and failure classes before scoring. This is contract/pre-registration
    evidence only: no score, freeze, public-usefulness claim, or hardware/native
    transfer.

115. **COMPLETE** - Tier 7.7d standardized long-run/failure localization
    scoring gate:
    passed 12/12 at
    `controlled_test_output/tier7_7d_20260509_standardized_long_run_failure_scoring_gate/`.
    Outcome `benchmark_stream_invalid`: Mackey-Glass ratios persisted across
    8000/16000/32000, Lorenz did not materially improve, external baselines
    remained blockers, and required NARMA10 became non-finite at 16000 and
    32000. This blocks any complete long-run scoreboard claim.

116. **COMPLETE** - Tier 7.7e finite-stream repair/preflight contract:
    passed 16/16 at
    `controlled_test_output/tier7_7e_20260509_finite_stream_repair_preflight/`.
    Outcome `finite_stream_repair_preflight_passed`: the original
    `narma10_standard_u05` generator reproduced 2/9 non-finite required cells,
    while selected `narma10_reduced_input_u02` passed 9/9 required cells at
    8000/16000/32000 across seeds 42/43/44. This authorizes a repaired-stream
    long-run rerun only; it does not score CRA, freeze a baseline, or authorize
    hardware/native transfer.

117. **COMPLETE** - Tier 7.7f repaired finite-stream long-run scoreboard:
    passed 16/16 at
    `controlled_test_output/tier7_7f_20260509_repaired_finite_stream_long_run_scoreboard/`.
    Outcome `mackey_only_localized`: the repaired stream removed the NARMA
    finite-stream blocker, Mackey-Glass persisted at ~2.17x-2.20x versus v2.3,
    repaired NARMA10 stayed near-flat, Lorenz stayed flat/weak, shams remained
    separated, and ESN remained the best external baseline. No freeze, broad
    usefulness claim, external-baseline superiority, or hardware/native transfer
    is authorized.

118. **COMPLETE** - Tier 7.7g Lorenz state-capacity / NARMA memory-depth
    diagnostic contract:
    passed 15/15 at
    `controlled_test_output/tier7_7g_20260509_lorenz_capacity_narma_memory_contract/`.
    Outcome `lorenz_capacity_narma_memory_contract_locked`: locks temporal-state
    capacity 16/32/64/128, matched-capacity ESN/reservoir references, repaired
    NARMA stream use, Mackey anchor, shams, metrics, and fail/pass classes
    before scoring.

119. **COMPLETE** - Tier 7.7h Lorenz capacity / NARMA memory-depth
    scoring gate:
    passed 19/19 at
    `controlled_test_output/tier7_7h_20260509_lorenz_capacity_narma_memory_scoring_gate/`.
    Outcome `overfit_or_sham_blocked`: capacity improved Mackey-Glass and
    Lorenz materially, but Lorenz was blocked because the best-capacity
    permuted-recurrence sham beat the candidate. Repaired NARMA improved only
    weakly. No freeze, mechanism promotion, broad usefulness claim,
    external-baseline superiority, or hardware/native transfer is authorized.

120. **COMPLETE** - Tier 7.7i capacity sham-separation /
    state-specificity contract:
    passed 19/19 at
    `controlled_test_output/tier7_7i_20260509_capacity_sham_separation_contract/`.
    Outcome `capacity_sham_separation_contract_locked`: predeclares the next
    diagnostic to decide whether the 7.7h capacity gains
    are candidate-specific state geometry or generic high-dimensional/permuted
    recurrent features. The contract must include effective-dimensionality
    diagnostics such as hidden-state participation ratio, rank-95 variance
    count, top-PC dominance, state-kernel alignment, and readout weight
    concentration for candidate versus permuted/state-reset shams. No score,
    repair, mechanism promotion, freeze, public usefulness claim, or
    hardware/native transfer is authorized.

121. **COMPLETE** - Tier 7.7j capacity sham-separation /
    state-specificity scoring gate:
    passed 15/15 at
    `controlled_test_output/tier7_7j_20260509_capacity_sham_separation_scoring_gate/`.
    Outcome `low_rank_collapse_confirmed`: Lorenz target/time shuffles separated
    strongly and readout concentration did not explain the failure, but the
    candidate state stayed near participation ratio 2 (`2.1911` at 128) and the
    max probe PR also stayed low (`2.2214`). The best generic family remained
    permuted recurrence. No repair, mechanism promotion, freeze, broad
    usefulness claim, external-baseline superiority, or hardware/native transfer
    is authorized.

122. **COMPLETE** - Tier 7.7k effective-state-dimensionality repair
    contract:
    passed 18/18 at
    `controlled_test_output/tier7_7k_20260509_effective_state_dimensionality_repair_contract/`.
    The contract locks `partitioned_driver_diverse_recurrent_state` as the next
    repair candidate, names shared-driver synchronization and input-state
    bottleneck as the primary suspects, and requires sham separation,
    target/time-shuffle guards, Mackey/NARMA regression guards, state geometry
    metrics, readout concentration metrics, and compact regression before any
    promotion. Contract only: no implementation, score, freeze, public
    usefulness claim, external-baseline superiority, or hardware/native
    transfer.

123. **COMPLETE** - Tier 7.7l effective-state-dimensionality repair
    scoring gate:
    passed 15/15 at
    `controlled_test_output/tier7_7l_20260509_effective_state_dimensionality_repair_scoring_gate/`.
    Outcome `task_gain_without_dimension`: the repair improved Lorenz versus
    the prior/single-pool reference (`0.0034485307` vs `0.0065086836`) and
    improved Mackey/NARMA versus single-pool, while target/time-shuffle guards
    stayed strong. However, PR rose only to `2.6645`, diversity-disabled was too
    close (`1.0165x`), and the predeclared state-dimensionality/attribution
    gate did not pass. No mechanism promotion, freeze, broad usefulness claim,
    external-baseline superiority, or hardware/native transfer is authorized.

124. **COMPLETE** - Tier 7.7m partitioned-driver attribution
    contract:
    passed 22/22 at
    `controlled_test_output/tier7_7m_20260509_partitioned_driver_attribution_contract/`.
    It locks the next gate to distinguish causal driver partitioning from
    nonlinear/lag feature enrichment, readout/interface budget, diversity
    pressure, generic basis effects, leakage, and non-reproducible scoring
    noise. Contract only: no attribution implementation, model score, mechanism
    promotion, freeze, broad usefulness claim, external-baseline superiority, or
    hardware/native transfer is authorized.

125. **COMPLETE** - Tier 7.7n partitioned-driver attribution scoring
    gate:
    passed 15/15 at
    `controlled_test_output/tier7_7n_20260509_partitioned_driver_attribution_scoring_gate/`.
    Outcome `generic_projection_explains_gain`: the full partitioned driver
    remained useful versus single-pool on Lorenz, but same-feature random
    projection and nonlinear/lag unpartitioned controls exceeded it. This blocks
    CRA-specific partitioned-driver promotion, freeze, broad usefulness claim,
    external-baseline superiority, and hardware/native transfer.

126. **COMPLETE** - Tier 7.7o generic temporal-interface reframing
    contract:
    passed 14/14 at
    `controlled_test_output/tier7_7o_20260509_generic_temporal_interface_reframing_contract/`.
    It parks the partitioned-driver repair, makes random-projection/nonlinear-
    lag controls mandatory, and authorizes a separate CRA-native temporal-
    interface internalization contract. No mechanism implementation, score,
    promotion, freeze, external-baseline superiority, broad usefulness claim, or
    hardware/native transfer is authorized.

127. **COMPLETE** - Tier 7.7p CRA-native temporal-interface
    internalization contract:
    passed 17/17 at
    `controlled_test_output/tier7_7p_20260509_cra_native_temporal_interface_internalization_contract/`.
    It locks `cra_native_sparse_temporal_expansion` as the next candidate and
    requires the scoring gate to beat or cleanly separate from random-
    projection and nonlinear-lag controls before any promotion. Contract only:
    no implementation, score, promotion, freeze, external-baseline superiority,
    broad usefulness claim, or hardware/native transfer is authorized.

128. **COMPLETE** - Tier 7.7q CRA-native temporal-interface internalization
    scoring gate:
    passed 14/14 at
    `controlled_test_output/tier7_7q_20260509_cra_native_temporal_interface_internalization_scoring_gate/`.
    Outcome: `external_controls_still_win`. The native sparse temporal
    expansion candidate improved over current CRA on Lorenz (`2.88x`),
    Mackey-Glass, and NARMA10 with strong target/time-shuffle separation, but
    same-feature random projection and nonlinear-lag controls still beat the
    native candidate on the key Lorenz claim. Diagnostic only: no mechanism
    promotion, freeze, external-baseline superiority, broad usefulness claim, or
    hardware/native transfer is authorized.

129. **COMPLETE** - Tier 7.7r native temporal-basis repair/reframing
    contract:
    passed 15/15 at
    `controlled_test_output/tier7_7r_20260509_native_temporal_basis_reframing_contract/`.
    It preserves the 7.7q positive signal without overclaiming it by splitting
    bounded engineering/interface utility from stricter CRA-specific mechanism
    promotion. Contract only: no new score, mechanism promotion, freeze,
    external-baseline superiority, broad usefulness claim, or hardware/native
    transfer is authorized.

130. **COMPLETE** - Tier 7.7s bounded temporal-basis utility
    promotion/regression gate:
    passed 13/13 at
    `controlled_test_output/tier7_7s_20260509_bounded_temporal_basis_utility_promotion/`.
    Outcome: `utility_promoted_mechanism_not_promoted`. The temporal-basis
    interface is carried forward as bounded engineering utility after repo
    pytest regression passed. It remains explicitly non-mechanism unless a later
    gate beats or cleanly separates from random-projection and nonlinear-lag
    controls.

131. **COMPLETE** - Tier 7.7t low-rank state repair campaign contract:
    passed 23/23 at
    `controlled_test_output/tier7_7t_20260509_low_rank_state_repair_campaign_contract/`.
    Outcome: `campaign_contract_locked`. Eight failure modes, five repair families
    (A-E), mandatory controls, state-geometry and task metrics, thirteen outcome
    classes, five-stage baseline escalation, three stopping rules, four route
    conditions to Tier 7.8/7.9, and explicit do-not-rules are locked before
    Tier 7.7u causal localization. Contract only; no repair implementation, no
    scoring, no mechanism promotion, no baseline freeze.

132. **COMPLETE** - Tier 7.7u state-collapse causal localization:
    passed 13/13 at
    `controlled_test_output/tier7_7u_20260509_state_collapse_causal_localization/`.
    Outcome: `localization_protocol_locked_awaits_model_variants`. Ten probe
    definitions, seven required diagnostic model variants, seven diagnostic
    controls, and nine outcome classification rules are locked. Probe
    infrastructure is importable. Full causal scoring awaits CRA config-layer
    model-variant implementation. Tier 7.7v repair candidate compact score is
    the next gate but requires at least the top-4 priority model variants
    (no_plasticity, no_inhibition, frozen_recurrent, input_channel_shuffle).

133. **COMPLETE** - Tier 7.7v-r0 diagnostic model variant implementation:
    passed 13/13 at
    `controlled_test_output/tier7_7v_r0_20260509_diagnostic_model_variants/`.
    Outcome: `diagnostic_variants_implemented_and_verified`. Six model variants
    registered and verified with distinct participation ratios. Extended
    tier7_7j.basis_features with random_recurrent and shuffled_input modes.

134. **COMPLETE** - Tier 7.7v repair candidate compact score (Family B):
    passed 11/11 at
    `controlled_test_output/tier7_7v_20260509_repair_candidate_compact_score/`.
    Outcome: `mechanism_candidate_requires_expanded_confirmation`. Family B
    candidate (orthogonalized input + block-structured recurrence) achieves
    PR=5.49 vs baseline PR=2.01, beats shuffled_input (PR=4.57).

135. **CURRENT ACTIVE STEP** - Tier 7.7w expanded standardized confirmation:
    required lengths 8000/16000/32000, seeds 42/43/44, Mackey-Glass/Lorenz/
    repaired-NARMA10, plus ESN/reservoir, online lag/ridge, and small GRU
    baselines. Run only if compact repair passes at 8000. If expanded
    confirmation survives, route to 7.7x promotion/regression.

134. Tier 7.7w expanded standardized confirmation, only after a compact repair
    candidate survives:
    rerun Mackey-Glass, Lorenz, and repaired NARMA10 across longer lengths and
    stronger external baselines. Include ESN/reservoir and online lag/ridge
    references where already supported. Do not run the full public adapter
    suite until a new baseline exists or a repair candidate needs external
    validation.

135. Tier 7.7x promotion/regression gate, only after expanded confirmation:
    run compact regression, mechanism ablations, leakage guards, and a freeze
    decision. A single Lorenz score gain, PR gain without task gain, or
    useful-but-generic feature improvement is not enough for a new software
    baseline.

136. Tier 7.8 polyp morphology/template variability contract - queued, not
    current active:
    activate only if Tier 7.7 localizes the bottleneck to lack of intrinsic
    unit/template diversity, if earlier repair families fail cleanly, or if a
    7.7 closeout explicitly routes there. Canonical queued details live in
    `docs/TIER_7_8_POLYP_MORPHOLOGY_PLAN.md`.

137. Tier 7.8a compact scoring gate, only after the Tier 7.8 contract passes:
    score same-budget heterogeneous polyp templates against current CRA,
    temporal-basis utility reference, same-capacity fixed-template control,
    morphology shams, random projection, nonlinear-lag, target shuffle, and
    time shuffle on Mackey-Glass, Lorenz, and repaired NARMA10 at 8000 steps
    and seeds 42/43/44. Do not start with the full long-run matrix.

138. Tier 7.8b expanded standardized confirmation, only if Tier 7.8a passes
    or produces a bounded utility signal:
    rerun the standardized benchmark family across longer lengths and stronger
    external baselines. Include ESN/reservoir and online lag/ridge references
    where already supported, plus any repo-supported GRU/SNN reviewer-defense
    baseline. If random projection or nonlinear-lag still explains the gain,
    preserve only a bounded utility/control result.

139. Tier 7.8c promotion/regression gate, only if Tier 7.8b survives:
    run compact regression, mechanism ablations, leakage guards, and baseline
    freeze review. A new software baseline is eligible only if morphology
    improves usefulness, increases state diversity, separates from shams and
    strong controls, and preserves prior guard tasks.

140. Tier 7.8d hardware/native transfer decision, only after promotion or a
    clearly useful bounded utility result:
    write a separate transfer contract before any C/PyNN/SpiNNaker work. Do
    not port morphology variability to hardware merely because it is on the
    roadmap.

141. Tier 7.9 morphology-aware lifecycle/evolution contract - queued after
    Tier 7.8:
    do not fold full lifecycle/evolution into Tier 7.8. Lifecycle tests whether
    selection over variation adds value; morphology tests whether useful
    variation exists. Use static pools and active masks, not dynamic allocation.

142. Mechanism iteration loop: add exactly one planned general mechanism at a
    time, ablate it, run compact regression, then rerun the same standardized
    benchmark scoreboard. If the full planned mechanism stack still cannot move
    Mackey-Glass/Lorenz/NARMA10 or any other selected public benchmark family,
    stop the broad usefulness track and narrow the paper.

143. Tier 7.1 real-ish adapter suite: audited sensor/anomaly/concept-drift/event-
    stream/control adapters with fixed preprocessing, no leakage, and fair
    baselines. Start only after the standardized scoreboard or failure diagnosis
    identifies a winning regime, a real failure mode, or a mechanism needing
    external validation.

144. Tier 7.2 held-out task challenge: define held-out families before running;
    no tuning on the holdout. Include at least one synthetic holdout and one
    real-ish adapter holdout if Tier 7.1 is active.

145. Tier 7.3 real data tasks: small reproducible datasets, locked splits,
    licenses, preprocessing, and external baselines. Candidate domains include
    streaming anomaly detection, predictive-maintenance sensor streams, human
    activity streams, event prediction, ECG/biosignal streams, and finance as
    one domain only rather than the whole proof.

146. Tier 7.4 policy/action selection held-out scoring: the current held-out
    chain is complete through 7.4h. No further NAB/C-MAPSS policy tuning is
    authorized from this chain; only the narrow C-MAPSS action-cost signal is
    preserved, with no broad action/policy claim, freeze, or hardware/native
    transfer.

147. Tier 7.5 curriculum/environment generator and Tier 7.6 long-horizon
    planning/subgoal control: run only after the shorter hard/real-ish tasks are
    stable. Do not claim language, AGI, or broad planning from toy gates.

148. Run expanded external baselines and fairness audit at the phase lock:
    random/sign persistence, online perceptron/logistic, lag/ridge where
    relevant, reservoir/ESN, small GRU, STDP-only SNN, simple evolutionary
    population, simple control baselines, and SNN reviewer-defense baselines
    where practical.

149. Freeze the next software baseline only if new software capability work
    passes ablations, fair baselines, leakage controls, and compact regression.
    If no new software mechanism is promoted, keep v2.5.

### Phase I - Final Paper Lock

128. Select final paper claim level: strong usefulness paper, bounded architecture
    study, or narrowed diagnostic report. Let the evidence decide.

129. Run final software matrix and final hardware subset matrix. Include effect
    sizes, confidence intervals, worst seed, sample efficiency, runtime, command
    count, resource budgets, and claim-boundary table.

130. Build the independent reproduction capsule: fresh checkout instructions,
    environment lock, validation command, registry/table regeneration, EBRAINS
    ingest instructions, artifact hash manifest, and one local tier rerun.

131. Draft paper/whitepaper only after the Phase H usefulness/baseline gates pass. Write
    limitations first, then claims. Preserve failed and parked diagnostics.

132. External dry run: have a clean agent or human follow only the docs. If they
    need hidden chat context, the repo is not ready.

## 7. Current Tier 4.27 Definition

Tier 4.27 name:

```text
Four-Core Runtime Resource / Timing Characterization + MCPL Decision Gate
```

Question:

```text
What is the measured envelope of the current four-core SDP scaffold, and what
is the concrete MCPL/multicast migration path required for scalable inter-core
event traffic?
```

Hypothesis:

```text
The 4.26 four-core SDP protocol provides a measurable scaffold, while
MCPL/multicast provides the intended scalable data plane. Tier 4.27 should
quantify SDP, prove or expose MCPL feasibility, and decide the exact next
migration step.
```

Null hypothesis:

```text
The 4.26 pass is only a smoke success. The runtime cost, latency, failure risk,
or instrumentation gap is too unclear to use as a stable foundation.
```

Measure:

```text
inter-core lookup request/reply counts
lookup latency if measurable
timeouts
stale/duplicate reply rate
wall time
load time
pause/readback time
payload bytes
per-core compact readback
schedule length tolerance: 48, 96, 192 if practical
message count per event
host command count
resource footprint per runtime profile
```

Pass:

```text
the four-core runtime envelope is measured
the bottleneck is identified
MCPL migration decision and scope are explicit
next tier is selected from evidence, not informal rationale
```

Decision logic:

```text
SDP may remain only as a transitional debug/control scaffold.

MCPL/multicast is required for the scalable inter-core data plane.

If MCPL passes 4.27d-f:
  make MCPL the default for subsequent multi-core/multi-chip runtime gates.

If MCPL fails 4.27d-f:
  repair MCPL before claiming scalable runtime architecture; any SDP-based
  follow-on must be explicitly labeled temporary/non-scaling.
```

Claim boundary:

```text
Tier 4.27 is engineering characterization and protocol decision evidence. It is
not a new learning mechanism, not speedup proof unless measured and compared,
not multi-chip scaling, and not a baseline freeze by itself.
```

## 8. When Life Dynamics Start

Native lifecycle work starts after the runtime communication path is stable,
after the key native state/memory/routing gates are mapped, and after the
Tier 5.19 / 7.0e temporal-substrate decision is explicit. The first lifecycle
hardware tier is not dynamic population creation. It is:

```text
preallocated static pool
active/inactive masks
lineage IDs
birth/cleavage/death counters
host- or chip-declared lifecycle boundary
fixed max-pool control
random event replay control
mask shuffle control
```

This begins at Tier 4.30 in the current execution plan, after the
Tier 4.30-readiness audit.

## 9. When Multi-Core And Multi-Chip Start

Multi-core has already started:

```text
4.25B = two-core split
4.25C = two-core repeatability
4.26 = four-core distributed split
```

Next multi-core work is not more cores immediately. First characterize and
possibly replace the inter-core protocol in 4.27. Then harden tasks and
mechanisms on the four-core path. Only after that do controlled 8/16-core and
multi-chip tests start in Tier 4.31.

## 10. What Not To Do Now

Do not:

```text
freeze v2.2 from 4.26
claim speedup from 4.26
claim full native v2.1 from 4.26
jump to multi-chip before 4.27 timing/resource decision
start lifecycle hardware before static-pool contract and native state path
move every Tier 5 mechanism native at once
skip MCPL because SDP happened to work on a tiny smoke
claim SDP is the long-term scalable inter-core data plane
use MCPL without official symbol/API guards and local compile tests
```

## 11. Source-Of-Truth Update Rules

After each completed run or design tier:

1. Ingest returned artifacts if any.
2. Classify evidence: pass, fail, prepared-only, noncanonical diagnostic,
   canonical hardware pass, or baseline freeze.
3. Update `codebasecontract.md` Section 0.
4. Update this master execution plan.
5. Update `CONTROLLED_TEST_PLAN.md` for tier definitions and pass/fail criteria.
6. Update `docs/PAPER_READINESS_ROADMAP.md` for strategic roadmap changes.
7. Update `README.md`, `experiments/README.md`, and `docs/CODEBASE_MAP.md` if
   user-facing status or runner map changed.
8. Update EBRAINS/custom-runtime runbooks for platform lessons.
9. Run `make validate`.
10. Preserve failures. Do not erase false starts.

## 12. Current Immediate Next Action

Most recent completed gate:

```text
Tier 7.7g = COMPLETE / PASS, 15/15 criteria.
Output: controlled_test_output/tier7_7g_20260509_lorenz_capacity_narma_memory_contract/
Outcome: lorenz_capacity_narma_memory_contract_locked.
Result: locks temporal-state capacity 16/32/64/128, matched-capacity ESN and
random-reservoir references, repaired NARMA U(0,0.2), Mackey positive-control
anchor, shams, metrics, and decision classes before scoring.
Boundary: contract/pre-registration only; no score, mechanism promotion,
baseline freeze, hardware/native transfer, public usefulness claim, language,
AGI, or ASI.
```

Latest scoring result:

```text
Tier 7.7h - Lorenz Capacity / NARMA Memory-Depth Scoring Gate
Status: COMPLETE / PASS, 19/19 criteria.
Output: controlled_test_output/tier7_7h_20260509_lorenz_capacity_narma_memory_scoring_gate/
Outcome: overfit_or_sham_blocked.
Result: capacity materially improved Mackey-Glass and Lorenz, but Lorenz did
not separate from the best-capacity permuted-recurrence sham. Repaired NARMA
improved only weakly.
Boundary: scoring evidence only; no baseline freeze, mechanism promotion,
public usefulness claim, external-baseline superiority, hardware/native
transfer, language, AGI, or ASI.
```

Recent contract:

```text
Tier 7.7i - Capacity Sham-Separation / State-Specificity Contract
Status: COMPLETE / PASS, 19/19 criteria.
Output: controlled_test_output/tier7_7i_20260509_capacity_sham_separation_contract/
Outcome: capacity_sham_separation_contract_locked.

Predeclare whether the 7.7h high-capacity gains are candidate-specific state
geometry or generic high-dimensional/permuted recurrent features before adding
mechanics or tuning the standardized benchmark scoreboard. Required diagnostics
include participation ratio, rank-95, top-PC fraction, state-kernel similarity,
candidate/sham seed stability, and readout weight concentration.
```

Latest scored gate:

```text
Tier 7.7j - Capacity Sham-Separation / State-Specificity Scoring Gate
Status: COMPLETE / PASS, 15/15 criteria.
Output: controlled_test_output/tier7_7j_20260509_capacity_sham_separation_scoring_gate/
Outcome: low_rank_collapse_confirmed.

Result: the locked probe matrix found dynamic but effectively low-dimensional
state behavior. Lorenz candidate PR stayed near 2 at high capacity, target/time
shuffles separated strongly, the readout was not the dominant bottleneck, and
the best generic family remained permuted recurrence. This blocks nominal-
capacity-only repair and points to effective-state-dimensionality repair.
```

The next concrete action is now:

```text
Tier 7.7k - Effective-State-Dimensionality Repair Contract
Status: COMPLETE / PASS, 18/18 criteria.
Output: controlled_test_output/tier7_7k_20260509_effective_state_dimensionality_repair_contract/

Result: the contract locks partitioned causal drivers plus diverse recurrent
state as the repair candidate. Primary suspected failure modes are shared-driver
synchronization and input-state bottleneck. Required controls include
diversity-disabled, same-capacity single-pool, permuted recurrence, orthogonal,
block, target-shuffle, and time-shuffle probes.
```

The next concrete action is now:

```text
Tier 7.7l - Effective-State-Dimensionality Repair Scoring Gate
Status: COMPLETE / PASS, 15/15 criteria.
Output: controlled_test_output/tier7_7l_20260509_effective_state_dimensionality_repair_scoring_gate/
Outcome: task_gain_without_dimension.

Result: partitioned causal drivers improved Lorenz, Mackey-Glass, and repaired
NARMA versus the single-pool reference, but the predeclared dimensionality and
diversity-pressure attribution conditions did not pass.
```

The next concrete action is now:

```text
Tier 7.7m - Partitioned-Driver Attribution Contract
Status: COMPLETE / PASS, 22/22 criteria.
Output: controlled_test_output/tier7_7m_20260509_partitioned_driver_attribution_contract/

Pre-register whether the 7.7l gain is caused by driver partitioning,
nonlinear/lag features, readout/interface changes, diversity pressure, or
another confound before promotion or architecture changes.
```

The next concrete action is now:

```text
Tier 7.7n - Partitioned-Driver Attribution Scoring Gate
Status: COMPLETE / PASS, 15/15 criteria.
Output: controlled_test_output/tier7_7n_20260509_partitioned_driver_attribution_scoring_gate/
Outcome: generic_projection_explains_gain.

Score the locked 7.7m variants and driver-group ablations. Promote nothing
unless the full candidate separates from partition, feature, readout/interface,
generic-basis, target-shuffle, and time-shuffle controls while preserving
Mackey/NARMA regression guards and compact regression.
```

The next concrete action is now:

```text
Tier 7.7o - Generic Temporal-Interface Reframing Contract
Status: COMPLETE / PASS, 14/14 criteria.
Output: controlled_test_output/tier7_7o_20260509_generic_temporal_interface_reframing_contract/

The 7.7n random-projection and nonlinear/lag controls beat the full
partitioned-driver candidate. Lock whether this becomes an external baseline,
an optional adapter, or a new CRA-internal mechanism candidate before any
implementation, tuning, promotion, or freeze.
```

The next concrete action is now:

```text
Tier 7.7t - Low-Rank State Repair Campaign Contract

Tier 7.7 remains the active standardized-benchmark repair chain. The low-rank
state bottleneck is not closed merely because Tier 7.7s promoted a bounded
temporal-basis utility.

Canonical planning reference:

```text
docs/TIER_7_7_LOW_RANK_REPAIR_PLAN.md
```

The next concrete action is:

```text
Tier 7.7t - Low-Rank State Repair Campaign Contract
```

Contract requirements:

```text
lock the ~2D effective-state collapse as the active failure class
predeclare the causal-localization gate (7.7u)
predeclare repair families and their controls
define what counts as fixed: state geometry plus usefulness plus attribution
define compact scoring before expanded baselines
define conditions for routing to Tier 7.8 morphology
```

Claim boundary:

```text
contract only; no scoring, no mechanism promotion, no baseline freeze, no
public usefulness claim, no hardware/native transfer
```

Tier 7.8 - Polyp Morphology / Template Variability Contract (Queued)

Tier 7.7s promoted the temporal-basis interface only as bounded engineering
utility. Tier 7.8 is now explicitly queued behind the Tier 7.7 low-rank repair
campaign. It should activate only if Tier 7.7 localizes the bottleneck to lack
of intrinsic template diversity, if earlier repair families fail cleanly, or if
a 7.7 closeout contract routes the repair campaign there.

Canonical planning reference:

```text
docs/TIER_7_8_POLYP_MORPHOLOGY_PLAN.md
```

Required contract contents:

```text
question / hypothesis / null hypotheses
same-budget heterogeneous template candidates
secondary same-budget polyp-size variability path
controls: current CRA, temporal-utility reference, same-capacity fixed template,
          morphology shuffles, same-feature random projection, nonlinear-lag,
          target shuffle, time shuffle
tasks: Mackey-Glass, Lorenz, repaired NARMA10 first
metrics: geomean MSE, PR, rank-95/rank-99, top-PC fraction, covariance spectrum,
         per-template activity, readout concentration, seed variance, runtime
outcome classes: morphology mechanism candidate, bounded utility only,
                 state-diversity-without-task-gain, task-gain-without-state-
                 diversity, generic-projection-explains-gain, capacity-
                 confounded, regression-or-leakage-blocked, inconclusive
baseline escalation: compact 7.8a first, expanded baselines only if warranted
```

Interpretation rule:

```text
If morphology helps a little and does not hurt, that is useful evidence, but it
is not automatically promotable. It becomes a CRA-specific mechanism only if it
separates from shams and strong generic controls. Otherwise carry it as bounded
utility or archive it as diagnostic evidence.
```
```

Recent closeout:

```text
Tier 7.4e passed at
controlled_test_output/tier7_4e_20260509_cost_aware_policy_action_heldout_preflight/.
It verified the public source/preflight artifacts, disjoint held-out splits,
fixed costs, baseline/sham inventories, online/offline label separation, and
scoring schemas before held-out v2.4 scoring. Hardware/native policy transfer
remains blocked pending a separate transfer contract.
```

Current reference state:

```text
Software baseline: v2.5 (`baselines/CRA_EVIDENCE_BASELINE_v2.5.md`)
Native lifecycle baseline: CRA_LIFECYCLE_NATIVE_BASELINE_v0.4
Baseline file: baselines/CRA_LIFECYCLE_NATIVE_BASELINE_v0.4.md
Registry snapshot: baselines/CRA_LIFECYCLE_NATIVE_BASELINE_v0.4_STUDY_REGISTRY.snapshot.json
Tier 4.30g-hw ingested output: controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/
Raw remote status: pass
Ingest status: pass
Board: 10.11.242.97
Hardware criteria: 285/285
Ingest criteria: 5/5
Returned artifacts preserved: 36
Enabled lifecycle bridge gate: open
Five predeclared lifecycle controls: closed
Resource/readback accounting: returned for every mode
Temporal substrate status: Tier 4.31d one-board hardware smoke passed and was
ingested; repeatability, speedup, multi-chip scaling, nonlinear recurrence,
native replay/sleep, native eligibility, and full v2.2 hardware transfer remain
unproven
Tier 4.31e decision status: passed 15/15; native replay buffers, sleep-like
replay, and native macro eligibility deferred until measured blockers exist;
Tier 4.32 authorized next
Tier 4.32 resource-model status: passed 23/23; MCPL-first scale path selected
as the target; no native-scale baseline freeze
Tier 4.32a preflight status: passed 19/19; 4/5/8/12/16-core stress envelope
predeclared; 4/5-core single-shard stress authorized next; replicated 8/12/16
core stress blocked until shard-aware MCPL; 4.32b/multi-chip/native-scale
baseline freeze remain blocked
Tier 4.32a-r0 protocol truth audit: passed 10/10; MCPL-first 4.32a-hw blocked
until confidence-bearing and shard-aware MCPL lookup repair passes
Tier 4.32a-r1 MCPL lookup repair: passed 14/14; MCPL value/meta replies,
shard-aware keys, cross-shard controls, and full/zero/half-confidence local
learning controls are repaired. Tier 4.32a-hw single-shard and
Tier 4.32a-hw-replicated both passed after EBRAINS ingest. Tier 4.32b static
reef partition smoke/resource mapping passed locally. Tier 4.32c inter-chip
feasibility contract passed locally; Tier 4.32d-r0 route/source/package audit
then passed locally and blocked package upload until inter-chip route repair.
Tier 4.32d-r1 passed route repair/local QA; Tier 4.32d package preparation then
passed at controlled_test_output/tier4_32d_20260507_prepared/ and refreshed
ebrains_jobs/cra_432d. Tier 4.32d then passed on EBRAINS and was ingested at
controlled_test_output/tier4_32d_20260507_hardware_pass_ingested/. Tier 4.32e
multi-chip learning micro-task design/package now passed locally at
controlled_test_output/tier4_32e_20260507_prepared/ and refreshed
ebrains_jobs/cra_432e. Tier 4.32e then passed on EBRAINS and was ingested at
controlled_test_output/tier4_32e_20260507_hardware_pass_ingested/. Tier 4.32f
then passed locally and selected lifecycle traffic/resource counters while
blocking immediate hardware until lifecycle inter-chip routes are source-proven.
Tier 4.32g-r0 then passed locally and authorized Tier 4.32g hardware package
preparation. Tier 4.32g-r2 then passed on EBRAINS after the stale-package rerun
was isolated, proving two-chip lifecycle traffic/resource counters over the
repaired package. Tier 4.32h then passed locally and froze
`CRA_NATIVE_SCALE_BASELINE_v0.5`. Tier 7.0e has now run: short/medium
calibration improved over raw v2.1 but stayed behind ESN, and the 10k scoreboard
is blocked by a non-finite NARMA10 seed-44 stream. The next action is Tier 7.0f:
repair the long public-benchmark finite-stream protocol and localize the
standard-scoreboard failure. Tier 6.2 diagnostics may explain failures, but they
may not replace public/standardized benchmark evidence. This is not
benchmarks-as-claims, speedup, true two-partition learning, lifecycle scaling,
multi-shard learning, or new native migration.
```

Purpose:

```text
Tier 4.31d completed the first one-board hardware smoke for moving the v2.2
fading-memory temporal-state subset toward chip-native form. Tier 4.31e then
closed the replay/eligibility decision gate and found no measured blocker that
justifies immediate native replay buffers, sleep-like replay, or native macro
eligibility. Tier 4.32 converted measured 4.27-4.31 evidence into an explicit
resource envelope. Tier 4.32a then turned that envelope into a concrete local
preflight and caught a real scale blocker: replicated shards need shard-aware
MCPL routing because the current key has no shard/group field and `dest_core` is
reserved/ignored. Tier 4.32a-r0 then caught the remaining protocol truth
problem before packaging hardware: the promoted confidence-gated learning path
still used SDP because MCPL did not yet transmit confidence/hit status. Tier
4.32a-r1 repaired that blocker locally. Tier 4.32a-hw then passed
single-shard hardware stress, and Tier 4.32a-hw-replicated then passed
8/12/16-core replicated-shard hardware stress. The next action is now Tier
4.32b static reef partition smoke/resource mapping. Tier 4.32b then passed
locally, and Tier 4.32c then passed as the inter-chip feasibility contract. Tier
4.32d-r0 then passed as the route/source/package audit and blocked the upload
because explicit inter-chip link routing was not source-proven before 4.32d-r1.
Tier 4.32d-r1 then passed as route repair/local QA. Tier 4.32d then passed as
the first two-chip split-role MCPL lookup hardware smoke after EBRAINS ingest.
Tier 4.32e then passed as the first two-chip learning-bearing hardware
micro-task after EBRAINS ingest. Tier 4.32f then passed as the multi-chip
resource/lifecycle decision contract and authorized Tier 4.32g-r0 before any
further multi-chip hardware run. Tier 4.32g-r0 then source-proved lifecycle
event/trophic/mask-sync inter-chip routes and authorized Tier 4.32g hardware
preparation, not benchmarks, speedup, true two-partition learning, lifecycle
scaling, multi-shard learning, or baseline-freeze claims.
```

Required coverage:

```text
Use v2.4 as the software reference for policy/action work and `CRA_LIFECYCLE_NATIVE_BASELINE_v0.4` as
the native lifecycle baseline. Keep Tier 4.31d's boundary strict: one-board
temporal-state hardware smoke only; not nonlinear recurrence, not speedup, not
multi-chip scaling, not benchmark superiority, and not full organism autonomy.
Tier 4.32g-r2 passed and Tier 4.32h froze `CRA_NATIVE_SCALE_BASELINE_v0.5`.
Tier 7.0e short/medium calibration showed v2.2 improves over raw v2.1 but does
not close the ESN gap; the 10k standardized scoreboard is blocked by a
non-finite NARMA10 seed-44 target stream. Tier 7.0f then repaired the protocol
boundary, selected 8000 as the largest original-seed finite rerun length, and
the 8000 rerun showed v2.2 ranks second but remains about 9.6x behind ESN.
Tier 7.0g selected bounded nonlinear recurrent continuous-state/interface
repair as the next mechanism. Tier 7.0h then showed that the bounded recurrent
candidate improves the public scoreboard versus v2.2 and beats simple online
controls. Tier 7.0i then falsified/narrowed the topology-specific recurrence
claim: generic bounded recurrent state remains useful, but topology shams and
no-recurrence controls match or beat the structured candidate. Tier 7.0j then
passed full NEST compact regression and froze v2.3 as the narrow generic
bounded recurrent-state software baseline. Tier 6.2a then passed targeted
hard-task validation: v2.3 was best only on `variable_delay_multi_cue`, while
v2.2 won the aggregate diagnostic geomean. Tier 7.1a then passed as a
contract-only real-ish/public adapter selection and chose NASA C-MAPSS RUL
streaming. Tier 7.1b then passed source/data preflight, verified FD001 access,
checksums, schema, train-only normalization, prediction-before-update stream
ordering, and label-separated smoke artifacts. Tier 7.1c then passed compact
C-MAPSS FD001 scoring but narrowed the claim: v2.3 ranked 5th and did not beat
v2.2 or the monotone age baseline. Tier 7.1d then localized most of that compact
failure to target/readout policy: capped RUL plus ridge readout repaired scalar
scoring, but v2.3 still did not win. Tier 7.1e then rejected the tiny v2.2
capped-ridge signal as statistically unconfirmed against lag-multichannel ridge.
Tier 7.1f then selected Numenta NAB streaming anomaly detection as the next
public adapter family. Tier 5.20a-e then tested the resonant branch idea across
a same-budget dose sweep: 16/0 (v2.3), 14/2, 12/4, 8/8, 4/12, 2/14, and 0/16.
All harnesses passed, but no resonant variant earned promotion because localized
variable-delay/anomaly/NARMA value did not survive broad-task regression,
aggregate, and sham-separation gates. Tier 7.1g then passed NAB source/data/
scoring preflight: the official source commit is pinned, selected streams and
labels parse, label windows are separated from online rows, chronological smoke
streams are adapter-sorted, and scoring-interface feasibility is documented.
Tier 7.1h then passed compact NAB scoring: v2.3 ranked second, beat v2.2 and
all three v2.3 shams, but did not beat the fixed random-reservoir online
residual baseline and did not clear bootstrap confirmation. Tier 7.1i then
broadened NAB to 20 streams across 6 categories: v2.3 beat v2.2 and shams, but
rolling z-score won the aggregate and the v2.3 signal localized rather than
confirming. Tier 7.1j then localized the gap to threshold/false-positive policy:
v2.3 has better event-F1/window recall but worse NAB-style/false-positive
pressure. Tier 7.1k found a same-subset no-label `persist3` false-positive
repair candidate, but it must be confirmed on held-out NAB streams/categories
because the policy was selected on the broad diagnostic subset and traded off
window recall. Tier 7.1l tested that locked policy on 12 held-out NAB streams:
it reduced false positives but did not beat rolling z-score or v2.2, ranked
fifth, and separated only two of three shams. Tier 7.1m closed the adapter loop
by narrowing the NAB claim and selecting Tier 7.4a cost-aware policy/action
selection as the next general mechanism contract. Tier 7.4a then passed the
contract gate, Tier 7.4b passed the local diagnostic as candidate evidence,
Tier 7.4c froze bounded software baseline v2.4, Tier 7.4d locked the
held-out/public action-cost scoring contract, and Tier 7.4e verified the
scoring preflight. Tier 7.4f then produced a qualified C-MAPSS-only action-cost signal while NAB remained unconfirmed; Tier 7.4g confirmed only the narrow C-MAPSS external/sham signal and preserved the non-separation from v2.2. Tier 7.4h closed the policy/action chain without claim inflation. Tier 7.5a locked the curriculum/environment-generator contract, and Tier 7.5b materialized deterministic preflight artifacts without scoring CRA. Tier 7.5c generated-family scoring is the next active software work.
Reopen native work only for targeted transfer after a software task/mechanism
earns it under the Tier 7/6.2 gates and a separate transfer contract is written.
It must preserve explicit board/chip/shard identity, message paths, compact
readback ownership, failure counters, placement assumptions,
enabled-vs-no-learning separation, and resource measurements while adding the
lifecycle traffic/resource evidence that 4.32f selected and 4.32g-r0 unblocked.
Do not claim true two-partition cross-chip learning until origin/target shard
semantics are defined. Only reopen replay buffers, sleep-like replay, or native
eligibility if a later measured blocker specifically demands it.
```


## 13. Make-Or-Break Gates

| Gate | If it passes | If it fails |
| --- | --- | --- |
| Tier 5.19 temporal substrate | CRA gains a general fading-memory/recurrent-state path for continuous temporal tasks. | Keep Tier 7 benchmark limitation explicit and do not migrate that path to hardware. |
| Tier 4.27 runtime envelope | Native runtime path becomes a stable engineering foundation. | Repair SDP/MCPL protocol before scaling. |
| Native task hardening | Hardware-native path supports harder delayed/adaptive tasks. | Keep native claim to micro-runtime primitives. |
| Native mechanism bridges | Promoted v2 mechanisms begin moving on chip. | Keep those mechanisms host-side and narrow hardware claim. |
| Native lifecycle | Organism/self-scaling claim has hardware feasibility. | Keep lifecycle as software-only evidence. |
| Multi-chip | Scaling path becomes credible beyond one chip. | Publish measured single-chip/multi-core boundary only. |
| Hard/real-ish tasks | CRA earns practical usefulness regime. | Paper becomes controlled architecture study. |
| Final reproduction | Serious reviewers can reproduce core evidence. | Not ready for release. |
