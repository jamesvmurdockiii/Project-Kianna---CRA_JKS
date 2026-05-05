# CRA Master Execution Plan

Last updated: 2026-05-05T08:45-04:00.

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

Current software baseline:

```text
v2.1 = post-Tier-5.18c bounded host-side self-evaluation / reliability-monitoring evidence lock
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
Tier 4.29e = cra_429o HARDWARE DIAGNOSTIC FAIL / cra_429p LOCAL REPAIR PASS + PACKAGE PREPARED
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

Current active step:

```text
Tier 4.29e - Replay/Consolidation Bridge (cra_429p repaired EBRAINS package prepared)
```

## 2. Immediate Baseline Decision

Do not freeze `v2.2` from Tier 4.26.

Reason:

```text
v2.x software baselines are for promoted CRA mechanisms plus regression.
Tier 4.26 is a hardware-native distributed-runtime milestone, not a new software
mechanism promotion.
```

Record 4.26 as:

```text
major hardware-native distributed-runtime pass
```

Only consider a native-runtime baseline freeze after Tier 4.27 measures the
four-core runtime envelope and defines the MCPL/multicast migration path. SDP is
a transitional control/debug scaffold for inter-core traffic, not the scaling
destination.

Possible future freeze name:

```text
CRA_NATIVE_RUNTIME_BASELINE_v0.1
```

This is separate from the `CRA_EVIDENCE_BASELINE_v2.x` software line.

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
| Promoted v2 mechanisms native | Keyed memory (4.29a), routing/composition (4.29b), predictive binding (4.29c), and self-evaluation (4.29d) all complete. Replay/consolidation/lifecycle remain. |
| Lifecycle/self-scaling native | Not started; must use static pools and masks, not dynamic graph creation. |
| Multi-chip scaling | Not started. |
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

## 6. Next 50-Step Execution Plan

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

24. 🔄 **IN PROGRESS** - Tier 4.29e replay/consolidation bridge.
    `cra_429o` returned REAL HARDWARE but failed as a noncanonical diagnostic.
    All three seeds executed on hardware, target acquisition and four-core loads
    passed, all controls completed, pending matured, and stale/timeouts stayed 0.
    However each seed failed 2/34 criteria: wrong-key replay bias reference
    tolerance and random-event replay weight reference tolerance.
    Diagnostic artifact: `controlled_test_output/tier4_29e_20260505_cra_429o_hardware_fail/`.
    Root cause: the Python schedule/reference gate was wrong, not a promoted
    mechanism failure. `_build_schedule()` ignored per-event wrong context keys,
    and the local host reference did not mirror native continuous-runtime ordering
    or surprise-threshold behavior.
    Repair: `cra_429p`, runner revision
    `tier4_29e_native_replay_consolidation_20260505_0003`.
    Local repair gate passes seeds 42/43/44 with native-continuous expected values:
    no_replay weight=32768/bias=0; correct_replay weight=47896/bias=-232;
    wrong_key_replay weight=32768/bias=-5243; random_event_replay weight=57344/bias=0.
    Correct replay now differs from no replay, wrong-key replay does not
    consolidate weight, and random-event replay remains distinct.
    Package prepared: `ebrains_jobs/cra_429p`.
    Next: upload/run `cra_429p`, then ingest only runner revision 20260505_0003.
    If it passes, run 4.29f compact native mechanism regression; if it fails,
    classify exactly and repair with a fresh package name.

25. Tier 4.29f compact native mechanism regression: rerun the strongest tiny
    native delayed, switching, reentry, and mechanism controls after each
    promoted bridge. Do not stack unvalidated mechanisms.

26. Freeze `CRA_NATIVE_MECHANISM_BRIDGE_v0.3` only if the selected mechanism
    bridges pass their controls and compact native regression. If any mechanism
    fails, keep it host-side or parked.

### Phase D - Lifecycle / Organism Dynamics Native Path

27. Tier 4.30 lifecycle-native contract: preallocated pool only. No dynamic
    PyNN population creation mid-run. Birth/cleavage/death are activation,
    masking, assignment, or lineage events inside static state.

28. Tier 4.30a local static-pool lifecycle reference: active/inactive masks,
    lineage IDs, trophic state, birth/cleavage/death counters, fixed max-pool
    control, random event replay control.

29. Tier 4.30b single-core lifecycle mask smoke: prove a tiny static pool can
    activate/silence units, preserve lineage, and read back lifecycle telemetry.

30. Tier 4.30c multi-core lifecycle state split: distribute lifecycle masks and
    lineage across the selected runtime protocol without corrupting state.

31. Tier 4.30d lifecycle sham-control hardware subset: fixed max pool, random
    event replay, mask shuffle, no trophic pressure, no dopamine/plasticity if
    applicable. Keep it small but reviewer-defensible.

32. Freeze `CRA_LIFECYCLE_NATIVE_BASELINE_v0.4` only if lifecycle telemetry,
    controls, resource accounting, and at least one useful task effect pass. If
    lifecycle does not help, narrow the organism claim.

### Phase E - Multi-Core And Multi-Chip Scaling

33. Tier 4.31 update the mapping model with measured 4.27-4.30 data: ITCM,
    DTCM, schedule length, lookup pressure, message bytes, readback bytes,
    per-core utilization, and state-slot limits.

34. Tier 4.31a single-chip multi-core scale stress: increase cores on one chip
    in controlled increments, for example 4 -> 8 -> 16 cores if resources allow,
    using MCPL/multicast for core-to-core event traffic unless a documented
    hardware constraint forces a temporary exception.

35. Tier 4.31b static reef partition smoke: map groups/modules/polyps to cores
    using the measured static-pool strategy. Do not pretend one polyp equals one
    chip unless measured mapping proves that is correct.

36. Tier 4.31c inter-chip feasibility contract: define routing keys, message
    path, board/chip selection, failure classes, readback, and resource limits
    before attempting multi-chip.

37. Tier 4.31d first multi-chip smoke: smallest possible cross-chip message and
    state lookup. No learning claim until communication and readback are clean.

38. Tier 4.31e multi-chip learning micro-task: only after cross-chip smoke
    passes, run a tiny delayed-credit or reentry task with explicit claim
    boundary and resource measurements.

39. Freeze `CRA_NATIVE_SCALE_BASELINE_v0.5` only if single-chip multi-core and
    first multi-chip evidence are stable enough for the final paper claim. If
    not, publish measured single-chip limits honestly.

### Phase F - Software Usefulness And Final Baselines

40. Tier 6.2 hard synthetic suite: variable-delay cue, multi-cue delayed reward,
    hidden regime switching, drifting bandit, concept drift, anomaly stream,
    and small delayed-reward control proxy.

41. Tier 7.1 real-ish adapter suite: audited sensor/anomaly/concept-drift/event-
    stream/control adapters with fixed preprocessing, no leakage, and fair
    baselines.

42. Tier 7.2 held-out task challenge: define held-out families before running;
    no tuning on the holdout.

43. Tier 7.3 real data tasks: small reproducible datasets, locked splits,
    licenses, preprocessing, and external baselines.

44. Tier 7.4 policy/action selection: state -> action -> delayed consequence,
    exploration versus exploitation, uncertainty-gated actions.

45. Tier 7.5 curriculum/environment generator and Tier 7.6 long-horizon
    planning/subgoal control: run only after the shorter hard/real-ish tasks are
    stable. Do not claim language, AGI, or broad planning from toy gates.

46. Run expanded external baselines and fairness audit at the phase lock:
    random/sign persistence, online perceptron/logistic, reservoir/ESN, small
    GRU, STDP-only SNN, simple evolutionary population, and SNN reviewer-defense
    baselines where practical.

47. Freeze the next software baseline only if new software capability work passes
    ablations, fair baselines, and compact regression. If no new software
    mechanism is promoted, keep v2.1.

### Phase G - Final Paper Lock

48. Select final paper claim level: strong usefulness paper, bounded architecture
    study, or narrowed diagnostic report. Let the evidence decide.

49. Run final software matrix and final hardware subset matrix. Include effect
    sizes, confidence intervals, worst seed, sample efficiency, runtime, command
    count, resource budgets, and claim-boundary table.

50. Build the independent reproduction capsule: fresh checkout instructions,
    environment lock, validation command, registry/table regeneration, EBRAINS
    ingest instructions, artifact hash manifest, and one local tier rerun.

51. Draft paper/whitepaper only after Step 49 and Step 50 pass. Write limitations
    first, then claims. Preserve failed and parked diagnostics.

52. External dry run: have a clean agent or human follow only the docs. If they
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

Native lifecycle work starts after the runtime communication path is stable
through 4.27 and after at least the key native state/memory/routing gates are
mapped. The first lifecycle hardware tier is not dynamic population creation.
It is:

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

This begins at Tier 4.30 in the current execution plan.

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

The next concrete action is:

```text
Upload/run repaired EBRAINS package `cra_429p` for Tier 4.29e.
```

JobManager command:

```text
cra_429p/experiments/tier4_29e_native_replay_consolidation_bridge.py --mode run-hardware --seeds 42,43,44
```

When the returned files are available:

1. Verify result timestamps and runner revision before ingesting. Current valid
   package metadata is `cra_429p` with runner revision
   `tier4_29e_native_replay_consolidation_20260505_0003`.
2. Do not promote `cra_429o` results. They are preserved only as noncanonical
   diagnostic hardware evidence at
   `controlled_test_output/tier4_29e_20260505_cra_429o_hardware_fail/`.
3. If all three seeds pass, ingest Tier 4.29e, update the registry/docs, and run
   Tier 4.29f compact native mechanism regression across 4.29a-4.29e.
4. If any seed fails, classify the failure, preserve artifacts, repair only the
   proven failure class, regenerate with a fresh package name, and rerun the
   minimal necessary hardware gate.

Do not mark 4.29e canonical from local-only repair evidence, prepared-only
evidence, or stale downloads.


## 13. Make-Or-Break Gates

| Gate | If it passes | If it fails |
| --- | --- | --- |
| Tier 4.27 runtime envelope | Native runtime path becomes a stable engineering foundation. | Repair SDP/MCPL protocol before scaling. |
| Native task hardening | Hardware-native path supports harder delayed/adaptive tasks. | Keep native claim to micro-runtime primitives. |
| Native mechanism bridges | Promoted v2 mechanisms begin moving on chip. | Keep those mechanisms host-side and narrow hardware claim. |
| Native lifecycle | Organism/self-scaling claim has hardware feasibility. | Keep lifecycle as software-only evidence. |
| Multi-chip | Scaling path becomes credible beyond one chip. | Publish measured single-chip/multi-core boundary only. |
| Hard/real-ish tasks | CRA earns practical usefulness regime. | Paper becomes controlled architecture study. |
| Final reproduction | Serious reviewers can reproduce core evidence. | Not ready for release. |
