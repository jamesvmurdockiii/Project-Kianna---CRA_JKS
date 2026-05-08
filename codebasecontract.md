# CRA Maintainer Operating Contract

This document is the operating contract for any automated maintainer, human collaborator, or
future maintainer working on the Coral Reef Architecture (CRA) repository. Its
purpose is to preserve the standard we have been building toward: clean,
auditable, reproducible, paper-grade research engineering that can survive review
by serious neuromorphic, SNN, SpiNNaker, and machine-learning researchers.

This file is not a replacement for the roadmap, runbooks, evidence registry, or
experiment plans. It is the contract that tells you how to use them, when to
update them, what counts as evidence, and what is forbidden.

If you only read one thing before changing this repo, read this file first.

## 0. Live Handoff State

This section is intentionally current-stateful. Update it whenever work
finishes, a run returns, the active tier changes, the next plan changes, or a
new baseline is frozen. Do not let this section become stale.

Last updated: 2026-05-08T21:36:31+00:00.

Current repo root:

```text
/Users/james/JKS:CRA
```

Current frozen software baseline:

```text
v2.3 = post-Tier-7.0j generic bounded recurrent-state software evidence lock
       Source: controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate/
       Runner: experiments/tier7_0j_generic_recurrent_promotion_gate.py
       Criteria: 14/14
       Compact gate: full NEST compact regression passed
       Claim: generic bounded recurrent continuous-state improves the locked
              8000-step Mackey-Glass/Lorenz/NARMA10 public scoreboard versus
              v2.2 while preserving existing CRA guardrails.
       Boundary: not topology-specific recurrence, not ESN superiority, not
                 hardware evidence, not native on-chip recurrence, not
                 language/planning/AGI/ASI.
```

Latest targeted usefulness diagnostic:

```text
Tier 6.2a = COMPLETE, PASS, 12/12 criteria
  Source: controlled_test_output/tier6_2a_20260508_targeted_usefulness_validation/
  Runner: experiments/tier6_2a_targeted_usefulness_validation.py
  Outcome: v2_3_partial_regime_signal_next_needs_failure_specific_mechanism_or_7_1_probe
  Key result: v2.3 was best on variable_delay_multi_cue only; v2.2 won the
              aggregate hard-task geomean (0.15892013746238234 vs v2.3
              0.17604715537423876).
  Boundary: software diagnostic only; custom hard tasks are not public
            usefulness proof, not a baseline freeze, and not hardware/native
            transfer evidence.
```

Latest real-ish/public adapter contract:

```text
Tier 7.1a = COMPLETE, PASS, 12/12 criteria
  Source: controlled_test_output/tier7_1a_20260508_realish_adapter_contract/
  Runner: experiments/tier7_1a_realish_adapter_contract.py
  Selected adapter: nasa_cmapss_rul_streaming
  Decision: use NASA C-MAPSS / turbofan remaining-useful-life streaming as the
            first real-ish/public adapter family to test the Tier 6.2a
            variable-delay signal outside private diagnostics.
  Boundary: contract only; not a data run, not a usefulness claim, not a
            baseline freeze, and not hardware/native transfer evidence.
```

Latest public source/data preflight:

```text
Tier 7.1b = COMPLETE, PASS, 16/16 criteria
  Source: controlled_test_output/tier7_1b_20260508_cmapss_source_data_preflight/
  Runner: experiments/tier7_1b_cmapss_source_data_preflight.py
  Dataset: NASA C-MAPSS FD001 from https://data.nasa.gov/docs/legacy/CMAPSSData.zip
  ZIP SHA256: 74bef434a34db25c7bf72e668ea4cd52afe5f2cf8e44367c55a82bfd91a5a34f
  Result: source access, checksums, schema, train/test/RUL parse, train-only
          normalization, prediction-before-update stream ordering, and
          label-separated smoke artifacts are verified.
  Boundary: preflight only; not C-MAPSS scoring, not public usefulness proof,
            not a baseline freeze, and not hardware/native transfer evidence.
  Raw data policy: raw C-MAPSS zip/extracted files live under .cra_data_cache/
                   and must remain ignored, not committed.
```

Latest public adapter scoring gate:

```text
Tier 7.1c = COMPLETE, PASS, 12/12 criteria
  Source: controlled_test_output/tier7_1c_20260508_cmapss_fd001_scoring_gate/
  Runner: experiments/tier7_1c_cmapss_fd001_scoring_gate.py
  Outcome: v2_3_no_public_adapter_advantage
  Best model: monotone_age_to_rul_ridge, test RMSE 46.10944999532139
  v2.3: rank 5, test RMSE 49.4908802462679
  v2.2: test RMSE 48.739451335025144
  Boundary: compact scalar-adapter software scoring only; not a full C-MAPSS
            benchmark, not a public usefulness win, not a baseline freeze, and
            not hardware/native transfer evidence.
```

Latest public adapter failure analysis:

```text
Tier 7.1d = COMPLETE, PASS, 14/14 criteria
  Source: controlled_test_output/tier7_1d_20260508_cmapss_failure_analysis_adapter_repair/
  Runner: experiments/tier7_1d_cmapss_failure_analysis_adapter_repair.py
  Outcome: compact_failure_partly_readout_or_target_policy
  Best promotable model: scalar_pca1_v2_2_ridge_capped125,
                         test RMSE 20.271418942340336
  Best public baseline: lag_multichannel_ridge_capped125,
                        test RMSE 20.305268771358435
  v2.3 scalar ridge capped: test RMSE 20.688665138670245
  multichannel v2.3 ridge capped: test RMSE 22.697166948526846
  Interpretation: the compact 7.1c failure was mostly target/readout-policy
                  related. Multichannel v2.3 was sham-separated but did not
                  beat the scalar repair or fair public baselines.
  Boundary: software failure analysis only; not a full C-MAPSS benchmark, not a
            public usefulness win, not a promoted mechanism, not a baseline
            freeze, and not hardware/native transfer evidence.
```

Latest public adapter fairness confirmation:

```text
Tier 7.1e = COMPLETE, PASS, 12/12 criteria
  Source: controlled_test_output/tier7_1e_20260508_cmapss_capped_readout_fairness_confirmation/
  Runner: experiments/tier7_1e_cmapss_capped_readout_fairness_confirmation.py
  Outcome: v2_2_capped_signal_not_statistically_confirmed
  Candidate: scalar_pca1_v2_2_ridge_capped125
  Primary baseline: lag_multichannel_ridge_capped125
  Primary per-unit mean delta RMSE, positive means candidate better:
    -0.3690103080637045
  Bootstrap 95% CI: [-1.4191012103865384, 0.6704668696286052]
  Effect size d: -0.06884079972999842
  Boundary: statistical/fairness confirmation over Tier 7.1d per-unit results
            only; not a full C-MAPSS benchmark, not a public usefulness win,
            not a promoted mechanism, not a baseline freeze, and not
            hardware/native transfer evidence.
```

Latest next public adapter contract:

```text
Tier 7.1f = COMPLETE, PASS, 10/10 criteria
  Source: controlled_test_output/tier7_1f_20260508_next_public_adapter_contract/
  Runner: experiments/tier7_1f_next_public_adapter_contract.py
  Selected adapter: numenta_nab_streaming_anomaly
  Dataset family: Numenta Anomaly Benchmark (NAB)
  Decision: stop tuning C-MAPSS for now; use NAB as the next public streaming
            anomaly benchmark family because it directly pressures online
            prediction error, surprise, adaptation, false positives, and
            detection latency.
  Boundary: contract/family-selection only; not NAB data preflight, not scoring,
            not public usefulness evidence, not a baseline freeze, and not
            hardware/native transfer evidence.
```

Current hardware/runtime baseline decision:

```text
FROZEN: CRA_NATIVE_SCALE_BASELINE_v0.5
  Source: Tier 4.32h native-scale evidence closeout over 4.32a-replicated,
          4.32d, 4.32e, and 4.32g returned evidence.
  File: baselines/CRA_NATIVE_SCALE_BASELINE_v0.5.md
  JSON: baselines/CRA_NATIVE_SCALE_BASELINE_v0.5.json
  Registry snapshot: baselines/CRA_NATIVE_SCALE_BASELINE_v0.5_STUDY_REGISTRY.snapshot.json
  Supersedes: CRA_LIFECYCLE_NATIVE_BASELINE_v0.4 for native scale/substrate evidence

  Claim: CRA has a bounded native-scale SpiNNaker substrate baseline: replicated
         single-chip MCPL stress, two-chip MCPL communication/readback, a
         two-chip learning-bearing micro-task, and two-chip lifecycle
         traffic/resource counters have all passed canonical evidence gates
         with preserved returned artifacts, zero synthetic fallback, and explicit
         claim boundaries.

  Boundary: not a software capability baseline, not speedup evidence, not
            benchmark or real-task usefulness evidence, not true two-partition
            learning, not lifecycle scaling, not multi-shard learning, not proof
            that every v2.2 software mechanism is fully chip-native, and not
            language/planning/AGI/ASI. Hardware/native work should pause here
            except for targeted transfer of mechanisms or task paths that win
            software usefulness gates.

PREVIOUS FROZEN: CRA_LIFECYCLE_NATIVE_BASELINE_v0.4
  Source: Tiers 4.30-readiness through 4.30g-hw
  File: baselines/CRA_LIFECYCLE_NATIVE_BASELINE_v0.4.md
  JSON: baselines/CRA_LIFECYCLE_NATIVE_BASELINE_v0.4.json
  Registry snapshot: baselines/CRA_LIFECYCLE_NATIVE_BASELINE_v0.4_STUDY_REGISTRY.snapshot.json
  Supersedes: CRA_NATIVE_MECHANISM_BRIDGE_v0.3 for lifecycle-native evidence

  Claim: static-pool lifecycle state, lineage/active-mask/trophic counters,
         multi-core lifecycle profile isolation, lifecycle sham controls, and a
         host-ferried lifecycle-to-task bridge have passed canonical gates on
         real SpiNNaker. Enabled lifecycle opens the bounded task gate; five
         predeclared controls close it; resource/readback accounting is returned
         and preserved.

  Evidence lock:
    Tier 4.30-readiness PASS, 16/16.
    Tier 4.30 lifecycle-native contract PASS, 14/14.
    Tier 4.30a static-pool lifecycle reference PASS, 20/20.
    Tier 4.30b lifecycle runtime source audit PASS, 13/13.
    Tier 4.30b-hw single-core lifecycle hardware smoke PASS after ingest correction.
    Tier 4.30c multi-core lifecycle split contract PASS, 22/22.
    Tier 4.30d multi-core lifecycle runtime source audit PASS, 14/14.
    Tier 4.30e multi-core lifecycle hardware smoke PASS: board 10.11.226.145,
      raw pass, ingest pass, 75/75 hardware criteria, 5/5 ingest criteria.
    Tier 4.30f lifecycle sham-control hardware subset PASS: board 10.11.227.9,
      raw pass, ingest pass, 185/185 hardware criteria, 5/5 ingest criteria,
      35 returned artifacts preserved.
    Tier 4.30g local task-benefit/resource bridge PASS, 9/9.
    Tier 4.30g-hw lifecycle task-benefit/resource bridge PASS: board
      10.11.242.97, raw pass, ingest pass, 285/285 hardware criteria, 5/5
      ingest criteria, 36 returned artifacts preserved.

  4.30g-hw result:
    Ingested output:
      controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/
    Runner:
      experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py
    Runner revision:
      tier4_30g_lifecycle_task_benefit_resource_bridge_20260506_0001
    Enabled lifecycle bridge gate: 1.
    Control bridge gates: 0 for fixed-pool, random replay, active-mask shuffle,
      no-trophic, and no-dopamine/no-plasticity.
    Enabled reference tail accuracy: 1.0.
    Control reference tail accuracy: 0.375.
    Compact lifecycle payload length: 68.
    Stale replies/timeouts: 0.

  Boundary: lifecycle-native baseline, not full organism autonomy. Tier 4.30g-hw
            is a host-ferried lifecycle task-benefit/resource bridge, not
            autonomous lifecycle-to-learning MCPL; not speedup, not multi-chip
            scaling, not dynamic PyNN population creation, not v2.2 native
            temporal migration, not external-baseline superiority, and not
            language/planning/AGI/ASI.

  Latest native scale update: Tier 4.32e multi-chip learning micro-task passed
        on EBRAINS and was ingested at
        controlled_test_output/tier4_32e_20260507_hardware_pass_ingested/.
        Tier 4.32f multi-chip resource/lifecycle decision contract passed
        locally at
        controlled_test_output/tier4_32f_20260507_multichip_resource_lifecycle_decision/.
        Tier 4.32g-r0 then passed locally at
        controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit/
        with 14/14 criteria and source-proved lifecycle event request,
        trophic update, and active-mask/lineage sync MCPL routes for learning/
        lifecycle profiles. Tier 4.32g-r2 then passed on EBRAINS and was
        ingested at
        controlled_test_output/tier4_32g_20260508_hardware_pass_ingested/.
        Returned runner revision:
        tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003.
        Board target: 10.11.205.177. Source chip/core: (0,0,p7) learning.
        Remote chip/core: (1,0,p4) lifecycle. Result: raw hardware pass,
        ingest pass, source event/trophic requests 1/1, source mask sync
        received 1, lifecycle accepted trophic+death 2, lifecycle mask sync
        sent 1, active mask/count/death/trophic counters 1, zero stale/
        duplicate/missing-ack counters, reset/pause controls pass, payloads
        >=149, 30 returned artifacts preserved, zero synthetic fallback, and
        stale_package_detected false.
        Boundary: first two-chip single-shard learning evidence plus two-chip
        lifecycle traffic/resource evidence only. Tier 4.32h has now frozen
        `CRA_NATIVE_SCALE_BASELINE_v0.5` as a substrate baseline only; speedup
        claims, benchmark evidence, true two-partition learning, lifecycle
        scaling, and multi-shard learning remain blocked.
```

Current active tier state:

```text
Tier 4.31a — COMPLETE. Native temporal-substrate readiness.
  Status: LOCAL PASS, 24/24.
  Output: controlled_test_output/tier4_31a_20260506_native_temporal_substrate_readiness/
  Decision: migrate the v2.2 fading-memory substrate first as seven causal
    fixed-point EMA traces. Deltas and novelty are derived, not stored.
  Budget: 56 bytes persistent state, 112 bytes total initial trace/table budget.
  Boundary: local contract/readiness only; not C implementation, not hardware,
    not speedup, not nonlinear recurrence, and not a baseline freeze.

Tier 4.31b — COMPLETE. Native temporal-substrate local fixed-point reference.
  Status: LOCAL PASS, 16/16.
  Output: controlled_test_output/tier4_31b_20260506_native_temporal_fixed_point_reference/
  Result: fixed-point geomean MSE 0.22723731574965408 vs float reference
    0.22752229502159751; fixed/float ratio 0.9987474666079806; max feature
    error 0.004646656591329457; selected saturation count 0.
  Controls: lag-only, zero-state, frozen-state, shuffled-state, reset-interval,
    shuffled-target, and no-plasticity all separated.
  Boundary: local fixed-point reference only; not C runtime or hardware evidence.

Tier 4.31c — COMPLETE. Native temporal-substrate source/runtime implementation.
  Status: LOCAL PASS, 17/17.
  Output: controlled_test_output/tier4_31c_20260506_native_temporal_runtime_source_audit/
  Result: C runtime owns seven EMA traces, fixed-point alpha/decay table,
    selected ±2 trace range, update/reset/sham counters, compact 48-byte
    temporal readback, command codes 39-42, and profile ownership guards.
  Tests: runtime test-temporal-state, test-profiles, test, test-lifecycle, and
    test-lifecycle-split passed.
  Boundary: local source/runtime host evidence only; not SpiNNaker hardware,
    not speedup, not nonlinear recurrence, not replay/sleep, and not a freeze.

Tier 4.31d — COMPLETE. Native temporal-substrate hardware smoke.
  Question: Does the C-owned seven-EMA temporal state execute/read back cleanly
    on one SpiNNaker board with the same compact state and controls?
  Prepared output:
    controlled_test_output/tier4_31d_hw_20260506_prepared/
  Upload folder:
    ebrains_jobs/cra_431d_r1
  JobManager command:
    cra_431d_r1/experiments/tier4_31d_native_temporal_hardware_smoke.py --mode run-hardware --output-dir tier4_31d_hw_job_output
  Runner revision:
    tier4_31d_native_temporal_hardware_smoke_20260506_0003
  First EBRAINS return:
    INCOMPLETE, not hardware evidence. Returned only profile-test stdout and an
    ARM ELF, with no run-hardware JSON/report. Revision 0003 hardens the runner
    with streamed build logs, build timeout, `tier4_31d_hw_milestone.json`,
    incomplete-return artifact preservation, and structured exception
    finalization.
  Hardware pass:
    controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested/
    Board: 10.11.216.121
    Runner revision: tier4_31d_native_temporal_hardware_smoke_20260506_0003
    Remote hardware criteria: 59/59
    Ingest criteria: 5/5
    Returned artifacts preserved: 21
    Scenarios: enabled, zero_state, frozen_state, reset_each_update all pass
    Compact temporal payload length: 48
    Synthetic fallback: false
  Boundary: one-board hardware execution/readback for the temporal state only.
    Not repeatability, not speedup, not benchmark superiority, not multi-chip
    scaling, not nonlinear recurrence, not native replay/sleep, not native
    macro eligibility, and not full v2.2 hardware transfer.

Tier 4.31e — COMPLETE. Native replay/eligibility decision closeout.
  Question: Do current promoted mechanisms expose a measured blocker that
    requires native replay buffers or native eligibility traces now?
  Status: LOCAL PASS, 15/15.
  Output: controlled_test_output/tier4_31e_20260506_native_replay_eligibility_decision_closeout/
  Decision: native replay buffers, native sleep-like replay, and native macro
    eligibility are deferred until measured blockers exist. Tier 4.31f is
    deferred. Tier 4.32 mapping/resource modeling is authorized next. No
    baseline freeze.
  Boundary: local decision evidence only; not hardware, not implementation, not
    speedup, not multi-chip scaling, not native replay/sleep proof, not native
    eligibility proof, and not full v2.2 hardware transfer.

Tier 4.32 — COMPLETE. Native-runtime mapping/resource model.
  Status: LOCAL PASS, 23/23.
  Output: controlled_test_output/tier4_32_20260506_mapping_resource_model/
  Decision: MCPL is the scale data plane; SDP remains host control/readback or
    fallback only. Current returned profile builds have positive ITCM/DTCM
    headroom. Tier 4.32a single-chip multi-core scale stress is authorized next.
    Tier 4.32b-e remain blocked in order. No native-scale baseline freeze.
  Boundary: local resource/mapping model only; not new hardware, not speedup,
    not multi-chip scaling, not benchmark superiority, and not a baseline freeze.

Tier 4.32a — COMPLETE. Single-chip multi-core scale-stress preflight.
  Status: LOCAL PASS, 19/19.
  Output: controlled_test_output/tier4_32a_20260506_single_chip_scale_stress/
  Decision: 4/5-core single-shard MCPL-first stress points are eligible for
    EBRAINS hardware stress. Replicated 8/12/16-core shard points are blocked
    until shard-aware MCPL routing exists because the current MCPL key has no
    shard/group field and dest_core is reserved/ignored. Tier 4.32a-hw is
    authorized as single-shard only. Tier 4.32a-r1 is required before
    replicated-shard stress. Tier 4.32b-e and native-scale baseline freeze
    remain blocked.
  Boundary: local preflight only; not hardware, not speedup, not multi-chip,
    not replicated-shard scaling, not static reef partition proof, not
    benchmark superiority, and not a baseline freeze.

Tier 4.32a-r0 — COMPLETE. Protocol truth audit.
  Status: LOCAL PASS, 10/10.
  Output: controlled_test_output/tier4_32a_r0_20260506_protocol_truth_audit/
  Decision: the MCPL-first 4.32a-hw package is blocked. The source still uses
    SDP for confidence-gated lookup traffic because MCPL reply payload packing
    drops confidence/hit status and MCPL receive hardcodes confidence=1.0.
    The same source inspection also confirms the MCPL key has no shard/group
    field and dest_core is reserved/ignored.
  Boundary: local source/documentation truth audit only; not hardware, not
    speedup, not multi-chip scaling, not static reef partitioning, and not a
    baseline freeze.

Tier 4.32a-r1 — COMPLETE. Confidence-bearing shard-aware MCPL lookup repair.
  Status: LOCAL PASS, 14/14.
  Output: controlled_test_output/tier4_32a_r1_20260506_mcpl_lookup_repair/
  Question: Can the MCPL lookup protocol preserve value, confidence, hit/status,
    lookup type, and shard/group identity without duplicate cross-shard replies?
  Result: MCPL key layout is now app_id/msg_type/lookup_type/shard_id/seq_id;
    replies use value and confidence/meta packets; learning receive no longer
    hardcodes confidence=1.0; identical seq/type cross-shard controls and
    wrong-shard negative controls pass; full/zero/half-confidence four-core
    local learning controls pass over MCPL.
  Boundary: local source/runtime evidence only; not SpiNNaker hardware,
    speedup, replicated-shard scaling, multi-chip scaling, static reef
    partitioning, or a baseline freeze.

Tier 4.32a-hw — COMPLETE. EBRAINS single-shard single-chip stress.
  Status: HARDWARE PASS, INGESTED.
  Output: controlled_test_output/tier4_32a_hw_20260507_hardware_pass_ingested/
  Board: 10.11.215.185.
  Result: raw remote status pass, ingest status pass, 31/31 raw hardware
    criteria, 8/8 ingest criteria, 63 returned artifacts, point04 48 events /
    144 lookup replies, point05 96 events / 288 lookup replies, zero stale
    replies, zero duplicate replies, zero timeouts, and zero synthetic
    fallback.
  Boundary: single-shard hardware stress only; not replicated-shard scaling,
    not static reef partition proof, not multi-chip, and not a baseline freeze.

Tier 4.32a-hw-replicated — COMPLETE. Replicated-shard 8/12/16-core
  MCPL-first hardware stress.
  Status: HARDWARE PASS, INGESTED.
  Output: controlled_test_output/tier4_32a_hw_replicated_20260507_hardware_pass_ingested/.
  Board: 10.11.215.121.
  Result: raw remote status pass, ingest status pass, 185/185 raw hardware
    criteria, 9/9 ingest criteria, 80 returned artifacts, point08 2 shards /
    192 total events / 288 lookup replies per shard, point12 3 shards / 384
    total events / 384 lookup replies per shard, point16 4 shards / 512 total
    events / 384 lookup replies per shard, zero stale replies, zero duplicate
    replies, zero timeouts, and zero synthetic fallback.
  Boundary: single-chip replicated-shard hardware stress only; not static reef
    partition proof, not multi-chip, not speedup, and not a baseline freeze.

Tier 4.32b — COMPLETE. Static reef partition smoke/resource mapping.
  Status: LOCAL PASS, 25/25.
  Output: controlled_test_output/tier4_32b_20260507_static_reef_partition_smoke/.
  Result: canonical quad_mechanism_partition_v0 maps four static reef partitions
    to the measured point16 16-core replicated envelope: each partition owns one
    context/route/memory/learning core group, two static polyp slots, 128 events,
    and 384 lookup requests/replies with zero stale, duplicate, or timeout
    counters inherited from hardware. One-polyp-one-chip is rejected as an
    unsupported claim; quad partition plus dedicated lifecycle core is blocked
    at 17 cores on one conservative single-chip envelope.
  Boundary: local static partition/resource evidence only; not a new hardware
    run, not one-polyp-one-chip evidence, not multi-chip, not speedup, and not a
    native-scale baseline freeze.

Tier 4.32c — COMPLETE. Inter-chip feasibility contract.
  Status: LOCAL PASS, 19/19.
  Output: controlled_test_output/tier4_32c_20260507_interchip_feasibility_contract/.
  Result: defines required board/chip/core/role/partition/shard/seq identity
    fields, remote split-role MCPL lookup paths, compact readback ownership,
    failure classes, and the exact two-chip split-role single-shard smoke target.
    True two-partition cross-chip learning remains blocked until origin/target
    shard semantics are defined.
  Boundary: local contract evidence only; not hardware execution, not speedup,
    not multi-chip learning, and not a baseline freeze.

Tier 4.32d-r0 — COMPLETE. Inter-chip route/source/package audit.
  Status: LOCAL PASS, 10/10.
  Output: controlled_test_output/tier4_32d_r0_20260507_interchip_route_source_audit/.
  Result: MCPL key/value/meta source path exists, but cra_state_mcpl_init()
    installs local-core routes only and lacks explicit inter-chip link routing.
    The 4.32d EBRAINS package is blocked.
  Boundary: local audit evidence only; not hardware and not an upload package.

Tier 4.32d-r1 — COMPLETE. Inter-chip MCPL route repair/local QA.
  Status: LOCAL PASS, 14/14.
  Output: controlled_test_output/tier4_32d_r1_20260507_interchip_route_repair_local_qa/.
  Result: explicit inter-chip request/reply link-route macros and local route
    contract tests now prove the two-chip split-role single-shard smoke can be
    packaged without the 4.32d-r0 source blocker.
  Boundary: route/source/local QA only; not hardware, learning scale, speedup,
    benchmark superiority, or a baseline freeze.

Tier 4.32d — COMPLETE. Two-chip split-role single-shard MCPL lookup hardware smoke.
  Status: HARDWARE PASS / INGEST PASS.
  Prepared output: controlled_test_output/tier4_32d_20260507_prepared/.
  Ingested output: controlled_test_output/tier4_32d_20260507_hardware_pass_ingested/.
  Result: real EBRAINS hardware run with source/learning chip (0,0), remote
    state chip (1,0), shard 0, 32 events, 96 expected lookup replies, 96 actual
    lookup replies, zero stale replies, zero duplicates, zero timeouts, compact
    readback, and zero synthetic fallback.
  Boundary: hardware communication/readback smoke only; not learning scale,
    speedup, benchmark superiority, true two-partition learning, or a
    native-scale baseline freeze.

Tier 4.32e — COMPLETE. Multi-chip learning micro-task.
  Status: HARDWARE PASS / INGEST PASS.
  Prepared output: controlled_test_output/tier4_32e_20260507_prepared/.
  Ingested output: controlled_test_output/tier4_32e_20260507_hardware_pass_ingested/.
  Result: board 10.11.205.161, source/learning chip (0,0), remote state chip
    (1,0), shard 0, two cases, 32 events per case, 96/96 lookup replies per
    case, zero stale replies, zero duplicate replies, zero timeouts, compact
    readback, zero synthetic fallback, and 42 returned artifacts.
  Separation: enabled LR 0.25 readout 32768/0; no-learning LR 0.0 readout 0/0.
  Boundary: first two-chip single-shard learning micro-task only; not speedup,
    benchmark superiority, broad multi-chip organism scaling, true
    two-partition learning, multi-shard learning, or a native-scale baseline
    freeze.

Tier 4.32f — COMPLETE. Multi-chip resource/lifecycle decision contract.
  Status: LOCAL PASS 22/22.
  Output: controlled_test_output/tier4_32f_20260507_multichip_resource_lifecycle_decision/.
  Decision: lifecycle traffic with resource counters is the next multi-chip
    direction, but 4.32g hardware is blocked until lifecycle inter-chip routes
    are source-proven.
  Boundary: local decision/contract only; not hardware, not speedup, not
    lifecycle scaling, not true two-partition learning, not multi-shard
    learning, and not a native-scale baseline freeze.

Tier 4.32g-r0 — COMPLETE. Multi-chip lifecycle route/source repair audit.
  Status: LOCAL PASS 14/14.
  Output: controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit/.
  Result: lifecycle event request, trophic update, and active-mask/lineage sync
    MCPL routes are source-proven for learning/lifecycle profiles. The new
    lifecycle inter-chip route C test, lookup-route regression, and lifecycle
    split regression all pass.
  Decision: Tier 4.32g hardware preparation is authorized next. True partition
    semantics, speedup, benchmarks, multi-shard learning, and native-scale
    baseline freeze remain blocked.
  Boundary: local source/runtime QA only; not hardware evidence.

Tier 4.32g — COMPLETE. Two-chip lifecycle traffic/resource hardware smoke.
  Status: HARDWARE PASS, INGESTED.
  Output: controlled_test_output/tier4_32g_20260508_hardware_pass_ingested/.
  Runner revision: tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003.
  Board target: 10.11.205.177.
  Source chip/core: (0,0,p7) learning; remote chip/core: (1,0,p4) lifecycle.
  Result: raw hardware pass, ingest pass, source event/trophic requests 1/1,
    source mask sync received 1, lifecycle accepted trophic+death 2,
    lifecycle mask sync sent 1, active mask/count/death/trophic counters 1,
    zero stale/duplicate/missing-ack counters, reset/pause controls pass,
    payloads >=149, 30 returned artifacts preserved, and zero synthetic
    fallback.
  Boundary: two-chip lifecycle traffic/resource smoke only; not lifecycle
    scaling, speedup evidence, benchmark evidence, true partitioned ecology,
    multi-shard learning, or a native-scale baseline freeze.

Tier 4.32h — COMPLETE. Native-scale evidence closeout / baseline decision.
  Status: LOCAL PASS, 64/64, baseline frozen.
  Output: controlled_test_output/tier4_32h_20260508_native_scale_evidence_closeout/
  Baseline: baselines/CRA_NATIVE_SCALE_BASELINE_v0.5.md
  Result: consumed 4.32a replicated single-chip stress, 4.32d two-chip
    communication smoke, 4.32e two-chip learning micro-task, and 4.32g two-chip
    lifecycle traffic/resource smoke. All required evidence passed, all returned
    artifacts were preserved, no synthetic fallback/stale/duplicate/timeout
    blocker remained, and the claim boundary explicitly rejects speedup,
    benchmark usefulness, true partitioned learning, lifecycle scaling,
    multi-shard learning, and AGI/ASI.

Tier 7.0e — COMPLETE / PARTIALLY BLOCKED. Standardized dynamical benchmark
  rerun with v2.2 and run-length/training-budget sweep.
  Status: 720/2000 calibration passed; 10k scoreboard failed benchmark-stream
    validity because NARMA10 seed 44 generated non-finite target values.
  Key evidence:
    controlled_test_output/tier7_0e_20260508_length_calibration/
    controlled_test_output/tier7_0e_20260508_length_10000_scoreboard/
  Boundary: this is public/standardized software benchmark evidence only. It
    shows v2.2 improves over raw v2.1 at short/medium lengths but remains behind
    ESN; the 10k failure is a benchmark-protocol blocker, not a CRA model pass
    or failure.

Tier 7.0f — COMPLETE. Benchmark-protocol repair and public failure localization.
  Key evidence:
    controlled_test_output/tier7_0f_20260508_benchmark_protocol_failure_localization/
    controlled_test_output/tier7_0e_20260508_length_8000_scoreboard/
  Status: 7.0f passed 8/8. The valid 8000-step same-seed public rerun passed
    8/8 with zero invalid streams.
  Boundary: v2.2 ranks second at 8000 but remains about 9.6x behind ESN on
    aggregate geomean MSE. Longer exposure alone did not close the public
    benchmark gap.

Tier 7.0g — COMPLETE. General mechanism-selection contract.
  Status: COMPLETE, 7/7 criteria.
  Key evidence:
    controlled_test_output/tier7_0g_20260508_general_mechanism_selection_contract/
  Selected mechanism:
    bounded_nonlinear_recurrent_continuous_state_interface
  Boundary: contract only, not mechanism proof.

Tier 7.0h — COMPLETE. Bounded nonlinear recurrent continuous-state /
  readout-interface gate.
  Key evidence:
    controlled_test_output/tier7_0h_20260508_bounded_recurrent_interface_gate/
  Status: PASS, 10/10 criteria. The candidate improved valid 8000-step
    aggregate geomean MSE versus v2.2 (0.09530752189727928 vs
    0.19348969000027122), beat lag-only and random-reservoir online controls,
    and narrowed the ESN gap.
  Boundary: not promoted. The permuted-recurrence sham stayed too close
    (1.036590722013174 margin at 8000), so recurrence/topology specificity is
    unproven. No baseline freeze, hardware transfer, or native migration.

Tier 7.0i — COMPLETE. Recurrence/topology specificity repair gate.
  Key evidence:
    controlled_test_output/tier7_0i_20260508_recurrence_topology_specificity_gate/
  Status: PASS, 11/11 criteria. Structured bounded recurrence improved valid
    8000-step aggregate geomean MSE versus v2.2 (0.09964414908204765 vs
    0.19348969000027122), but did not beat the generic 7.0h recurrent reference
    (0.09530752189727928). Destructive controls separated; topology controls
    did not separate.
  Boundary: topology-specific recurrence is falsified/not supported on this
    public suite. No baseline freeze, hardware transfer, native migration, ESN
    superiority, or topology-specific claim is authorized from 7.0i.

Tier 7.0j — COMPLETE. Generic bounded recurrent-state promotion /
  compact regression gate.
  Status: COMPLETE, PASS, 14/14 criteria. Full NEST compact regression passed.
  Key evidence:
    controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate/
  Baseline: CRA_EVIDENCE_BASELINE_v2.3 frozen.
  Claim: generic bounded recurrent continuous-state interface improves the
    locked 8000-step Mackey-Glass/Lorenz/NARMA10 public scoreboard versus v2.2.
  Boundary: do not claim topology-specific recurrence, ESN superiority,
    hardware transfer, native migration, language, planning, AGI, or ASI.

Tier 6.2a — COMPLETE. Targeted hard-task validation over v2.3.
  Status: LOCAL SOFTWARE PASS, 12/12 criteria.
  Output: controlled_test_output/tier6_2a_20260508_targeted_usefulness_validation/
  Result: v2.3 showed a narrow variable-delay signal but did not beat v2.2 on
    the aggregate targeted hard-task geomean. No freeze or hardware transfer.

Tier 7.1a — COMPLETE. Real-ish/public adapter contract.
  Status: LOCAL CONTRACT PASS, 12/12 criteria.
  Output: controlled_test_output/tier7_1a_20260508_realish_adapter_contract/
  Result: selected NASA C-MAPSS RUL streaming as the first public/real-ish
    adapter family; no dataset scoring, freeze, or hardware transfer.

Tier 7.1b — COMPLETE. NASA C-MAPSS source/data preflight.
  Status: LOCAL PREFLIGHT PASS, 16/16 criteria.
  Output: controlled_test_output/tier7_1b_20260508_cmapss_source_data_preflight/
  Result: official source access, checksums, schema, train-only normalization,
    prediction-before-update ordering, and label-separated smoke artifacts
    passed. No model scoring, freeze, or hardware transfer.

Tier 7.1c — COMPLETE. Compact C-MAPSS FD001 scoring gate.
  Status: LOCAL SOFTWARE PASS, 12/12 criteria.
  Output: controlled_test_output/tier7_1c_20260508_cmapss_fd001_scoring_gate/
  Result: v2.3 showed no public-adapter advantage under compact scalar FD001
    scoring; it ranked 5th and did not beat v2.2 or the monotone age baseline.
    No freeze or hardware transfer.

Tier 7.1d — COMPLETE. C-MAPSS failure analysis / adapter repair.
  Status: LOCAL SOFTWARE PASS, 14/14 criteria.
  Output: controlled_test_output/tier7_1d_20260508_cmapss_failure_analysis_adapter_repair/
  Result: capped RUL plus ridge readout repaired the compact scalar failure;
    v2.2 ridge capped narrowly beat lag-multichannel ridge, while v2.3 still did
    not win. No freeze or hardware transfer.

Tier 7.1e — COMPLETE. C-MAPSS capped-RUL/readout fairness confirmation.
  Status: LOCAL SOFTWARE PASS, 12/12 criteria.
  Output: controlled_test_output/tier7_1e_20260508_cmapss_capped_readout_fairness_confirmation/
  Result: the tiny v2.2 capped-ridge signal was not statistically confirmed
    against lag-multichannel ridge under paired per-unit bootstrap analysis. No
    freeze or hardware transfer.

Tier 7.1f — COMPLETE. Next public adapter contract / family selection.
  Status: LOCAL CONTRACT PASS, 10/10 criteria.
  Output: controlled_test_output/tier7_1f_20260508_next_public_adapter_contract/
  Result: selected Numenta NAB streaming anomaly detection as the next public
    adapter family. No data preflight, scoring, freeze, or hardware transfer.

Tier 7.1g — CURRENT ACTIVE STEP. NAB source/data/scoring preflight.
  Required first move: verify source access, source hash/commit, file and label
    parsing, label-separated online streams, tiny leakage-safe smoke rows, and
    scoring-interface feasibility before full NAB scoring.

Tier 4.30g-hw — COMPLETE. Lifecycle task-benefit/resource bridge.
  Status: HARDWARE PASS, INGESTED. Board 10.11.242.97, 285/285 hardware
    criteria, 5/5 ingest criteria, 36 returned artifacts.
  Baseline: CRA_LIFECYCLE_NATIVE_BASELINE_v0.4 frozen.
  Boundary: host-ferried lifecycle task bridge only; not autonomous
    lifecycle-to-learning MCPL, speedup, multi-chip scaling, v2.2 temporal
    migration, or full organism autonomy.

Tier 4.28a-e — COMPLETE. Native task baseline v0.2 frozen.

Tier 4.29a — COMPLETE. Native keyed-memory overcapacity gate.
  Status: HARDWARE PASS, INGESTED. Three-seed repeatability complete.

Tier 4.29b — COMPLETE. Native routing/composition gate.
  Status: HARDWARE PASS, INGESTED. Three-seed repeatability complete.
  Previous: cra_429c FAILED on EBRAINS (48/52 criteria per seed, 3 seeds).
    Root cause: host_interface.c host_if_pack_state_summary() emitted context-slot
    counters for ALL profiles, but route_core updated route-slot counters.
    Host read zeros for route metrics. Fixed in C runtime, rebuilt, bumped to cra_429d.
  Question: Can native route_core handle keyed routing with composition controls?
  Mechanism: Keyed route slots + context * route * cue composition.
  Controls: wrong-route, route overwrite, context overwrite, host-composed sham.
  Rule: local first, then hardware. Within ≤512 event envelope.
  Local reference: 32 events, 2 route keys (+1.0, -1.0), 8 context slots,
    8 wrong-context, 8 wrong-route, 2 context overwrite, 6 route overwrite.
    18/18 local criteria pass.
    Seed 42: board 10.11.193.145, 47/47 criteria
    Seed 43: board 10.11.194.129, 47/47 criteria
    Seed 44: board 10.11.193.81, 47/47 criteria
    Weight=32768, bias=0, pending=32/32, lookups=96/96, stale=0, timeouts=0
    Context hits=26, misses=6, active_slots=8, slot_writes=9
    Exact parity across all three seeds. Zero variance.
  Hardware evidence: 52/52 criteria per seed, 3 seeds, 3 boards.
    Seed 42: board 10.11.194.81, weight=32781, bias=3
    Seed 43: board 10.11.195.1, weight=32781, bias=3
    Seed 44: board 10.11.195.129, weight=32781, bias=3
    Pending=32/32, lookups=96/96, stale=0, timeouts=0
    Context hits=24, misses=8, active_slots=8, slot_writes=9
    Route hits=24, misses=8, active_slots=2, slot_writes=3
    Exact parity across all three seeds. Zero variance.
  Claim boundary: Native routing/composition hardware evidence only; not speedup,
    not multi-chip scaling, not full v2.1 mechanism transfer, not lifecycle,
    not external-baseline superiority.

Tier 4.29c — COMPLETE. Native predictive binding bridge.
  Status: HARDWARE PASS, INGESTED. Three-seed repeatability complete.
  Previous: 4.29b passed compact regression; 4.29c authorized per Phase C map.
  Question: Can the native learning_core compute, store, and use predictions
    before feedback arrives, separating prediction from reward?
  Mechanism: Existing C runtime prediction path (`cra_state_predict_readout`,
    `g_pending_horizons[].prediction`, `_apply_reward_to_feature_prediction`).
    Host verifies prediction parity, pre-reward readback, and error-sign controls.
  Controls: zero-error (stable weight), positive-surprise (weight increases),
    negative-surprise (weight decreases), sign-flip (prediction sign matches cue).
  Rule: local first, then hardware. One mechanism at a time.
  Local reference: 20 events, delay=2, lr=0.25, feature=cue (+1.0/-1.0 context).
    5 zero-error, 5 positive-surprise, 5 negative-surprise, 5 sign-flip.
    All 7 local criteria PASS (seed 42):
      - zero_error_events_have_near_zero_error: max |error| = 0
      - positive_surprise_increases_weight: all positive_err events have delta_w > 0
      - negative_surprise_decreases_weight: all negative_err events have delta_w < 0
      - sign_flip_prediction_matches_feature_sign: prediction sign matches feature sign
      - all_events_matured: 20/20
      - final_weight_in_reasonable_range: final weight = 0.9062
      - no_missing_predictions: missing predictions = 0
    Final weight: 0.9062, bias: -0.0938.
  Hardware evidence: 24/24 criteria per seed, 3 seeds, 3 boards.
    Seed 42: board 10.11.218.169, 24/24 criteria
    Seed 43: board 10.11.218.41, 24/24 criteria
    Seed 44: board 10.11.218.105, 24/24 criteria
    Weight=30912 (0.943), bias=-1856 (-0.057) on ALL three seeds.
    Exact zero variance across seeds.
    Pending=20/20, decisions=20, reward_events=20, active_pending=0.
    Lookups=60/60, stale=0, timeouts=0.
    Context/route/memory slot_hits=20 each (all lookups hit).
    Reference: final_weight_raw=29696 (0.906), final_bias_raw=-3072 (-0.094).
    Weight delta=1216 (0.037), bias delta=1216 (0.037) — within ±8192 tolerance.
  Package: cra_429h (cra_429e deprecated: monolithic commands; cra_429f
    deprecated: Rule 2 violation; cra_429g deprecated: timestep=0 unreachable).
  Claim boundary: Native predictive-binding hardware evidence only; not full
    world modeling, not hidden-regime inference, not speedup, not multi-chip.
  Canonical evidence: controlled_test_output/tier4_29c_20260504_pass_ingested/

Tier 4.29d — COMPLETE. Native self-evaluation bridge.
  Status: HARDWARE PASS, INGESTED. Three-seed repeatability complete.
  Previous: 4.29c passed compact regression; 4.29d authorized per Phase C map.
  Question: Does the native learning_core modulate plasticity by the composite
    confidence of contextual, routing, and memory slots?
  Hypothesis: Yes. Effective LR = base_lr * product(ctx_conf, route_conf, mem_conf).
  Null hypothesis: Learning rate is invariant to slot confidence.
  Mechanism: C runtime `_apply_reward_to_feature_prediction` now receives
    `effective_lr` scaled by `ph->composite_confidence` when `ph->has_confidence`.
    Learning core tick retrieves lookup confidences, computes composite product,
    stores it in pending horizon via new `schedule_pending_horizon_with_target_and_confidence`.
  Controls:
    - full_confidence: all slots confidence=1.0; learning proceeds normally.
    - zero_confidence: all slots confidence=0.0; zero weight/bias change (exact).
    - zero_context_confidence: ctx_conf=0.0, others=1.0; product=0; zero change (exact).
    - half_context_confidence: ctx_conf=0.5, others=1.0; reduced magnitude vs full.
  Local reference: 20 events, delay=2, lr=0.25, initial weight=0, initial bias=0.
    Host reference computes composite_confidence = product of slot confidences.
    All 4 controls pass local criteria (seed 42):
      - full: final weight=0.8750, bias=-0.1250
      - zero: final weight=0.0000, bias=0.0000
      - zero_context: final weight=0.0000, bias=0.0000
      - half_context: final weight=0.8555, bias=0.1055 (magnitude < full)
  Hardware evidence: 30/30 criteria per seed, 3 seeds, 3 boards. 90/90 total.
    Seed 42: board 10.11.214.49, 30/30 criteria
    Seed 43: board 10.11.214.113, 30/30 criteria
    Seed 44: board 10.11.215.161, 30/30 criteria
    Full confidence: weight=30912, bias=-1856 (consistent with 4.29c baseline).
    Zero confidence: weight=0, bias=0 (exact zero on all seeds — proves confidence gating).
    Zero-context confidence: weight=0, bias=0 (exact zero — single-slot zero blocks all learning).
    Half-context confidence: weight=28093, bias=3517 (diff=61 from ref, within tolerance).
  First attempt failed (cra_429i): MCPL lookup protocol does not transmit confidence.
    `cra_state_mcpl_lookup_send_reply` ignores confidence arg; learning core's
    `cra_state_mcpl_lookup_receive` hardcodes confidence=FP_ONE. All controls
    received effective confidence=1.0, producing identical weight=30912.
  Fix: Disable MCPL lookup paths in `_send_lookup_request` and `_send_lookup_reply`;
    revert to SDP which transmits confidence via `msg->arg3`. Rebuilt as cra_429j.
  Package: cra_429j (cra_429i deprecated: MCPL lookup lacks confidence transmission).
  Runner: experiments/tier4_29d_native_self_evaluation_bridge.py
  Claim boundary: Native confidence-gated learning hardware evidence only;
    not full world modeling, not hidden-regime inference, not speedup, not multi-chip.
  Follow-up complete: Tier 4.29f passed compact native mechanism regression and
    froze `CRA_NATIVE_MECHANISM_BRIDGE_v0.3`.

Tier 4.29e — COMPLETE. Native replay/consolidation bridge.
  Status: HARDWARE PASS, INGESTED after `cra_429p` repair.
  Previous: `cra_429o` returned real hardware but failed as a noncanonical
    reference/schedule diagnostic; preserved at
    controlled_test_output/tier4_29e_20260505_cra_429o_hardware_fail/.
  Canonical artifact: controlled_test_output/tier4_29e_20260505_pass_ingested/
  Runner revision: tier4_29e_native_replay_consolidation_20260505_0003
  Hardware evidence: seeds 42/43/44, boards 10.11.226.129 / 10.11.226.1 /
    10.11.226.65, 38/38 criteria per seed (114/114 total).
  Controls:
    - no_replay: hardware weight=32768, bias=0; exact reference match.
    - correct_replay: hardware weight=47896, bias=-232; exact reference match;
      differs from no_replay and wrong_key_replay.
    - wrong_key_replay: hardware weight=32768, bias=0; weight matches no_replay
      and differs from correct_replay; bias within repaired tolerance.
    - random_event_replay: hardware weight=57344, bias=0; exact reference match;
      differs from correct_replay.
  Claim boundary: Native host-scheduled replay/consolidation through existing
    four-core state primitives only. Not native on-chip replay buffers, not
    biological sleep, not speedup, not multi-chip, not performance superiority.

Tier 4.29f — COMPLETE. Compact native mechanism regression.
  Status: PASS. Evidence-regression audit over canonical 4.29a-e real-hardware
    passes. 113/113 criteria.
  Output: controlled_test_output/tier4_29f_20260505_native_mechanism_regression/
  Baseline frozen: baselines/CRA_NATIVE_MECHANISM_BRIDGE_v0.3.md
  Boundary: not a new SpiNNaker execution and not a single-task all-mechanism
    stack proof.

Tier 7.0 — COMPLETE. Standard dynamical benchmark suite in software.
  Purpose: benchmark CRA on Mackey-Glass, Lorenz, NARMA10, and aggregate
    geometric-mean MSE against standard baselines before hardware migration.
  Status: DIAGNOSTIC PASS. The harness completed with 10/10 criteria, but CRA
    v2.1 online ranked 5/5 by aggregate geomean MSE. Echo-state network was
    best. This is not a superiority claim; it is a clean benchmark failure
    signal.

Tier 7.0b — COMPLETE. Continuous-regression failure analysis.
  Purpose: determine why CRA underperformed on Tier 7.0 before adding,
    tuning, or moving anything to hardware.
  Status: DIAGNOSTIC PASS. Failure class =
    recoverable_state_signal_default_readout_failure. Raw CRA geomean MSE was
    1.2233; leakage-safe CRA internal-state ridge probe improved to 0.4433;
    CRA state plus the same causal lag budget improved to 0.0544; shuffled
    target state control remained worse at 0.7533.

Tier 7.0c — COMPLETE. Bounded continuous readout/interface repair.
  Purpose: test whether a predeclared, leakage-safe continuous readout/interface
    can use the state signal found in 7.0b without becoming an unconstrained
    supervised model.
  Status: LIMITED REPAIR DIAGNOSTIC PASS. The best bounded state+lag repair
    improved raw CRA aggregate geomean MSE from 1.2233 to 0.1904 and beat
    shuffled/frozen controls, but lag-only online LMS reached 0.1515 and
    explains most of the benchmark gain. Do not promote, freeze, or migrate this
    benchmark to hardware from 7.0c alone.

Tier 7.0d — COMPLETE. State-specific continuous interface repair / claim-narrowing contract.
  Purpose: decide whether CRA state adds value beyond causal lag regression
    under stricter controls.
  Status: CLAIM-NARROWING DIAGNOSTIC PASS. Outcome =
    lag_regression_explains_benchmark. The best state-specific online candidate
    did not clear the margin versus lag-only and did not separate from shuffled
    residual controls. Train-prefix ridge lag-only also beat lag+state probes.
    Do not promote, freeze, or move this benchmark path to hardware under the
    current interface.

Tier 5.19 / 7.0e — COMPLETE. Continuous temporal dynamics substrate contract.
  Status: contract written and linked.
  Contract: docs/TIER5_19_CONTINUOUS_TEMPORAL_DYNAMICS_CONTRACT.md

Tier 5.19a — COMPLETE. Local continuous temporal substrate reference.
  Status: LOCAL SOFTWARE PASS, noncanonical diagnostic/reference evidence.
  Output: controlled_test_output/tier5_19a_20260505_temporal_substrate_reference/
  Criteria: 12/12.
  Classification: fading_memory_ready_but_recurrence_not_yet_specific.
  Key result: held-out long-memory candidate MSE 0.3857 vs lag-only 1.2710
    (3.30x margin), shuffled-state 1.8900 (4.90x margin), frozen-state 0.5685
    (1.47x margin), no-plasticity 2.9750 (7.71x margin), but no-recurrence
    MSE 0.3974 gives only 1.03x recurrence-specific margin.
  Boundary: local software reference only; not a baseline freeze, not hardware,
    not a promoted temporal-substrate mechanism, and not recurrence-specific
    proof.

Tier 5.19b — COMPLETE. Temporal-substrate benchmark/sham gate.
  Status: LOCAL SOFTWARE PASS, claim-narrowing diagnostic.
  Runner: experiments/tier5_19b_temporal_substrate_gate.py
  Output: controlled_test_output/tier5_19b_20260505_temporal_substrate_gate/
  Criteria: 12/12.
  Classification: fading_memory_supported_recurrence_unproven.
  Key result: held-out long-memory candidate MSE 0.3857 vs lag-only 1.2710
    (3.30x margin), and recurrence-pressure candidate MSE 0.8982 vs lag-only
    0.8967 (0.998x), fading-only 1.0348 (1.15x), state-reset 0.9029
    (1.01x), and shuffled-state 1.1686 (1.30x).
  Boundary: 5.19b supports a narrowed fading-memory temporal-state story but
    does not prove bounded nonlinear recurrence, does not freeze a software
    baseline, and does not authorize hardware migration.

Tier 5.19c — COMPLETE. Fading-memory narrowing / compact-regression decision.
  Status: PASS. Baseline freeze authorized and recorded as v2.2.
  Runner: experiments/tier5_19c_fading_memory_regression.py
  Output: controlled_test_output/tier5_19c_20260505_fading_memory_regression/
  Criteria: 11/11.
  Classification: fading_memory_ready_for_v2_2_freeze.
  Key result: temporal-memory geomean candidate MSE 0.2275 vs lag-only 0.8954
    (3.94x margin) and vs raw v2.1 2.1842 (9.60x margin). Standard-three
    lag-only remains stronger than the candidate, so do not claim universal
    benchmark superiority.
  Boundary: v2.2 is bounded host-side fading-memory temporal state only; not
    nonlinear recurrence, not hardware/on-chip temporal dynamics, not language,
    planning, AGI, or ASI.

Tier 4.30-readiness — COMPLETE. Lifecycle-native preflight / layering audit.
  Status: PASS, 16/16 criteria.
  Runner: experiments/tier4_30_readiness_audit.py
  Output: controlled_test_output/tier4_30_readiness_20260505_lifecycle_native_audit/
  Purpose: decide exactly how native lifecycle work layers on the current repo
    state before writing Tier 4.30 hardware code.
  Decision: initial lifecycle-native work layers on
    CRA_NATIVE_MECHANISM_BRIDGE_v0.3, with v2.2 as software reference only.
  Rule: confirm source-of-truth docs, native mechanism bridge status, v2.2
    software boundary, static-pool constraints, metrics, shams, and artifacts
    before implementation.

Tier 4.30 — COMPLETE. Lifecycle-native contract.
  Status: PASS, 14/14 criteria.
  Runner: experiments/tier4_30_lifecycle_native_contract.py
  Output: controlled_test_output/tier4_30_20260505_lifecycle_native_contract/
  Purpose: define how lifecycle/self-scaling moves onto the custom runtime using
    a static preallocated pool.
  Rule: birth/cleavage/death are active-mask, allocation, lineage, and trophic
    state transitions inside fixed capacity. Do not design dynamic PyNN
    population creation mid-run.

Tier 4.30a — COMPLETE. Local static-pool lifecycle reference.
  Status: PASS, 20/20 criteria.
  Runner: experiments/tier4_30a_static_pool_lifecycle_reference.py
  Output: controlled_test_output/tier4_30a_20260505_static_pool_lifecycle_reference/
  Purpose: build the deterministic reference for the Tier 4.30 command/readback
    schema before any runtime C implementation or EBRAINS package.
  Rule: exact active-mask, lineage, event-count, checksum, and sham-control
    outputs first; no hardware before local reference and source audit pass.

Tier 4.30b — COMPLETE. Source audit / single-core lifecycle mask smoke prep.
  Status: PASS, 13/13 criteria.
  Runner: experiments/tier4_30b_lifecycle_source_audit.py
  Output: controlled_test_output/tier4_30b_20260505_lifecycle_source_audit/
  Purpose: map the 4.30a static-pool reference into the smallest runtime-facing
    lifecycle state surface needed for a single-core active-mask/lineage smoke.
  Result: runtime lifecycle opcodes, `lifecycle_slot_t`,
    `cra_lifecycle_summary_t`, exact 4.30a canonical/boundary checksum parity,
    lifecycle SDP readback, and existing runtime/profile tests preserved.
  Boundary: local source/runtime host evidence only; not hardware evidence, not
    task benefit, not multi-core lifecycle, and not a baseline freeze.

Tier 4.30b-hw — COMPLETE. Single-core lifecycle active-mask/lineage hardware
  smoke run/ingest.
  Prepared package: `/Users/james/JKS:CRA/ebrains_jobs/cra_430b`.
  Prepared output: `controlled_test_output/tier4_30b_hw_20260505_prepared/`.
  Ingested output: `controlled_test_output/tier4_30b_hw_20260505_hardware_pass_ingested/`.
  Purpose: prove the audited lifecycle metadata surface survives real SpiNNaker
    execution/readback on the smallest possible single-core smoke.
  Result: hardware functional pass after ingest correction. Raw remote status
    was `fail`; corrected ingest status is `pass`. Correction reason:
    runner rev-0001 checked cumulative `readback_bytes` instead of actual
    compact `payload_len`. Returned artifacts preserved both the raw failure and
    the corrected status.
  Rule: require zero fallback, zero sim/run/readback failure, real lifecycle
    readback, active-mask and checksum agreement. Do not
    claim task benefit, multi-core lifecycle, v2.2 temporal migration, scaling,
    speedup, or lifecycle baseline freeze.

Tier 4.30c — COMPLETE. Multi-core lifecycle state split contract/local
  reference.
  Status: PASS, 22/22 criteria.
  Runner: `experiments/tier4_30c_multicore_lifecycle_split.py`.
  Output: `controlled_test_output/tier4_30c_20260505_multicore_lifecycle_split/`.
  Result: five-core ownership contract (`context_core`, `route_core`,
    `memory_core`, `learning_core`, `lifecycle_core`), host setup/readback only,
    MCPL/multicast-targeted inter-core lifecycle messages, explicit distributed
    lifecycle failure classes, and exact canonical/boundary split-reference
    parity.
  Boundary: local contract/reference only; not C implementation, not hardware
    evidence, not task benefit, not speedup, not v2.2 temporal migration, and
    not a lifecycle baseline freeze.

Tier 4.30d — COMPLETE. Multi-core lifecycle runtime source audit/local C
  host test.
  Status: PASS, 14/14 criteria.
  Runner: `experiments/tier4_30d_lifecycle_runtime_source_audit.py`.
  Output:
    `controlled_test_output/tier4_30d_20260505_lifecycle_runtime_source_audit/`.
  Result: dedicated `lifecycle_core` profile, lifecycle inter-core
    event/trophic request stubs, active-mask/count/lineage sync send/receive
    bookkeeping, duplicate/stale/missing-ack counters, non-lifecycle profile
    ownership guards, compact `payload_len=68` preservation, and local C host
    tests.
  Boundary: local source/runtime host evidence only; not EBRAINS hardware
    evidence, not task benefit, not speedup, not multi-chip scaling, not v2.2
    temporal migration, and not a lifecycle baseline freeze.

Tier 4.30e — HARDWARE PASS / INGESTED. Multi-core lifecycle hardware smoke.
  Runner: `experiments/tier4_30e_multicore_lifecycle_hardware_smoke.py`.
  Prepared output: `controlled_test_output/tier4_30e_hw_20260505_prepared/`.
  Ingested output:
    `controlled_test_output/tier4_30e_hw_20260505_hardware_pass_ingested/`.
  Board: `10.11.226.145`.
  Raw remote status: `pass`; ingest status: `pass`.
  Hardware criteria: 75/75; ingest criteria: 5/5.
  Result: five profile builds/loads/readbacks, profile ownership guards,
    canonical/boundary lifecycle parity, and duplicate/stale lifecycle event
    rejection passed on real SpiNNaker.
  Boundary: hardware smoke only; not lifecycle task benefit, not sham-control
    success, not speedup, not multi-chip scaling, not v2.2 temporal migration,
    and not a lifecycle baseline freeze.


Current status summary:

```text
Tier 4.23c = single-core continuous hardware pass.
Tier 4.24/4.24b = continuous runtime resource/build-size characterization pass.
Tier 4.25B = two-core state/learning split hardware pass.
Tier 4.25C = two-core split repeatability pass across seeds 42/43/44.
Tier 4.26 = four-core context/route/memory/learning distributed hardware pass.
Tier 4.27a = HARDWARE PASS, INGESTED. Board 10.11.194.65, cores 4/5/6/7.
  38/38 hardware + 38/38 ingest criteria. SDP-based four-core distributed
  scaffold with schema v2 readback (105 bytes).

Tier 4.28a = HARDWARE PASS, INGESTED. Three-seed repeatability gate complete.
  Seed 42: board 10.11.204.129, 38/38 criteria
  Seed 43: board 10.11.196.153, 38/38 criteria
  Seed 44: board 10.11.194.65, 38/38 criteria
  MCPL-based four-core distributed lookup: lookup_requests=144, lookup_replies=144,
  stale_replies=0, timeouts=0 on all three seeds. Final readout weight=32768,
  bias=0, pending=48/48, active_pending=0, decisions=48, reward_events=48.

Tier 4.28b = HARDWARE PASS, INGESTED. Board 10.11.213.9, cores 4/5/6/7.
  38/38 criteria. Delayed-cue task (target=-feature): readout_weight_raw=-32769,
  readout_bias_raw=-1, pending_created=48, pending_matured=48, active_pending=0,
  decisions=48, reward_events=48, lookup_requests=144, lookup_replies=144,
  stale_replies=0, timeouts=0. First EBRAINS attempt (cra_428f) failed due to
  lookup key mismatch (key_id=0 vs written slots at 101/1101/2101); fixed in
  cra_428g per fresh-package Rule 10.

Tier 4.29a = HARDWARE PASS, INGESTED. Three-seed repeatability complete.
  Seed 42: board 10.11.213.9, 24/24 criteria
  Seed 43: board 10.11.213.73, 24/24 criteria
  Seed 44: board 10.11.212.201, 24/24 criteria
  Overcapacity gate: pending_created=20/20, pending_matured=20/20, active_pending=0,
  decisions=20, reward_events=20. Context slots active=20/128, evictions=0.

Tier 4.29b = HARDWARE PASS, INGESTED. Three-seed repeatability complete.
  Seed 42: board 10.11.194.81, 47/47 criteria
  Seed 43: board 10.11.195.1, 47/47 criteria
  Seed 44: board 10.11.195.129, 47/47 criteria
  Weight=32781, bias=3 on all seeds. Exact parity. Pending=32/32, lookups=96/96.

Tier 4.29c = HARDWARE PASS, INGESTED. Three-seed repeatability complete.
  Seed 42: board 10.11.218.169, 24/24 criteria
  Seed 43: board 10.11.218.41, 24/24 criteria
  Seed 44: board 10.11.218.105, 24/24 criteria
  Weight=30912 (0.943), bias=-1856 (-0.057) on ALL seeds. Exact zero variance.
  Pending=20/20, decisions=20, reward_events=20, lookups=60/60.

Tier 4.29d = HARDWARE PASS, INGESTED. Three-seed repeatability complete.
  Seed 42: board 10.11.214.49, 30/30 criteria
  Seed 43: board 10.11.214.113, 30/30 criteria
  Seed 44: board 10.11.215.161, 30/30 criteria
  Zero-confidence controls: exact weight=0, bias=0 on all seeds.
  Half-confidence: weight=28093, bias=3517 (diff=61 from ref).
  Package: cra_429j (cra_429i deprecated: MCPL lacked confidence transmission).

Tier 4.29e = HARDWARE PASS, INGESTED. Native host-scheduled replay/consolidation
  bridge after `cra_429p` repair. Seeds 42/43/44, 38/38 criteria per seed,
  114/114 total. `cra_429o` preserved as noncanonical schedule/reference failure.

Tier 4.29f = EVIDENCE-REGRESSION PASS, INGESTED. Compact audit over canonical
  4.29a-e hardware passes. 113/113 criteria. Freezes
  `CRA_NATIVE_MECHANISM_BRIDGE_v0.3`.
```

Tier 4.27a canonical evidence:

```text
output = controlled_test_output/tier4_27a_20260502_pass_ingested/
board = 10.11.194.65
cores = 4/5/6/7
criteria = 38/38 hardware + 38/38 ingest
learning core = decisions 48, reward_events 48, pending_created 48,
                pending_matured 48, active_pending 0,
                readout_weight_raw 32768, readout_bias_raw 0,
                lookup_requests 144, lookup_replies 144,
                stale_replies 0, timeouts 0,
                commands_received 196, schedule_length 48,
                readback_bytes 210
schema_version = 2
payload_bytes = 105
context/route/memory cores = lookup_replies 0 each (no lookups on state servers)
```

Tier 4.27a claim boundary:

```text
The four-core SDP scaffold is instrumented and measured. Lookup telemetry,
per-core command counts, schedule length, and readback bytes are all captured.
Hardware execution reproduces the monolithic delayed-credit result within
tolerance. This is not speedup evidence, not multi-chip scaling, not a general
multi-core framework, not full native v2.1 autonomy, and not MCPL/multicast.
SDP remains transitional.
```

Tier 4.26 canonical evidence:

```text
output = controlled_test_output/tier4_26_20260502_pass_ingested/
board = 10.11.194.1
cores = 4/5/6/7
criteria = 30/30 hardware + 30/30 ingest
learning core = decisions 48, reward_events 48, pending_created 48,
                pending_matured 48, active_pending 0,
                readout_weight_raw 32768, readout_bias_raw 0
context core = slot_hits 48
fallback = 0
```

Tier 4.26 claim boundary:

```text
Four independent cores can hold distributed context, route, memory, and learning
state and reproduce the monolithic delayed-credit result within tolerance on a
48-event task. This is not speedup evidence, not multi-chip scaling, not full
native v2.1, not lifecycle hardware, and not final autonomy.
```

Tier 4.27a purpose:

```text
Measure the current four-core SDP scaffold with instrumented counters (schema v2,
105-byte readback). Capture timing envelope, lookup telemetry, and exact reference
parity. This is resource/timing characterization evidence, not a new learning
result or a baseline freeze.
```

Local build capability (established 2026-05-02):

```text
- spinnaker_tools cloned from SpiNNakerManchester/spinnaker_tools and built
- ARM GNU Toolchain 13.3 Rel1 downloaded from ARM and extracted to /tmp/
- All four profile .aplx images build locally without EBRAINS
- Host tests (make test, make test-profiles, make test-four-core-48event) all pass
```

Immediate next steps:

1. Keep Tier 4.31d/4.31e boundaries strict: one-board temporal-state smoke plus
   local replay/eligibility decision closeout only, no new freeze.
2. Tier 4.32h native-scale evidence closeout passed and froze
   `CRA_NATIVE_SCALE_BASELINE_v0.5` at
   controlled_test_output/tier4_32h_20260508_native_scale_evidence_closeout/.
   This is a native-scale substrate freeze only: do not claim speedup, benchmark
   usefulness, true two-partition cross-chip learning, lifecycle scaling,
   multi-shard learning, or AGI/ASI from it. Tier 7.0j froze v2.3 as a narrow
   generic bounded recurrent-state software baseline. Tier 6.2a then showed
   v2.3 has only a narrow targeted variable-delay signal and does not beat v2.2
   on the aggregate diagnostic hard-task geomean. Do not move v2.3 native/on-chip
   until a separate transfer contract is justified; do not claim topology-specific
   recurrence, ESN superiority, broad usefulness, or public real-task success.
3. Keep the 4.31b/4.31c range refinement explicit: selected trace bound is ±2
   in s16.15; the older ±1 sketch saturated and must not silently return.
4. Keep public repo hygiene green before the next upload or commit: no
   credentialed remotes, no `ebrains_jobs/` symlinks, no transient root output
   dirs, no generated host binaries, and `make validate` passing.
5. Before authorizing replicated-core or multi-chip stress, inspect the runtime
   routing key space and send helpers. Replicating profiles is not enough. The
   protocol must carry shard/group identity or directed-routing semantics, and
   local C tests must prove independent shards cannot receive each other's
   lookup requests or replies.


## 1. North Star

CRA is being developed and tested as a local-learning, organism-inspired,
spiking, population/ecology architecture with a long-term path toward scalable
neuromorphic substrate research.

Do not interpret every planned capability as something that must live inside one
giant polyp. A polyp should remain a small specialist. Larger capabilities are
allowed to emerge from distributed reef machinery: many polyps, shared runtime
state, routing, memory slots, lifecycle masks, readout interfaces, and carefully
bounded native primitives. When adding a mechanism, state explicitly whether it
is a per-polyp mechanism, a population mechanism, a readout/interface mechanism,
a lifecycle mechanism, or a runtime substrate mechanism.

Known remaining or unpromoted mechanism families must stay visible in the master
plan: continuous temporal dynamics / fading memory, CRA-native nonlinear
recurrent state, local continuous-value interface, macro/native eligibility if a
measured blocker justifies it, lifecycle/self-scaling, native lifecycle,
on-chip temporal state, on-chip replay buffers, on-chip eligibility traces,
policy/action selection, real-ish task adapters, curriculum generation,
long-horizon planning, single-chip scale stress, multi-chip scaling, final
baseline fairness, and reproduction packaging. This is not a license to add all
features at once; it is a queue that must be worked one mechanism at a time.

The project is not allowed to rely on informal rationale, unsupported speculation, or single-run demonstrations. Every
claim must be earned through staged evidence, controls, ablations, baselines,
reproducible artifacts, and explicit claim boundaries.

The long-term ambition is large: prove that CRA can become a useful, functional,
paradigm-shifting substrate direction. The near-term discipline is stricter:
prove one capability at a time, against fair controls, and never claim more than
the evidence supports.

## 2. Core Principles

These rules are non-negotiable.

1. Evidence first. No claim is promoted because it sounds biologically plausible,
   exciting, or strategically useful.
2. No hidden failures. Failed, blocked, ambiguous, and noncanonical runs must be
   preserved and documented.
3. Claim boundaries are mandatory. Every result must say what it proves and what
   it does not prove.
4. Prepared is not hardware evidence. A prepared EBRAINS package proves source
   and packaging readiness only.
5. One major mechanism at a time. Add, test, ablate, compare, regress, then
   freeze only if earned.
6. No p-hacking. Do not tune forever until a desired result appears. Use focused
   repair cycles with explicit failure modes and pass criteria.
7. Baselines matter. CRA must be compared against simple and strong baselines
   under fair task streams, seed sets, scoring windows, and tuning budgets.
8. Hardware evidence must be real. Hardware claims require real `pyNN.spiNNaker`
   or custom SpiNNaker runtime execution, zero synthetic fallback, no hidden
   summary-read failures, and returned artifacts.
9. Do not confuse hybrid, chunked, bridge, and native/on-chip evidence. They are
   different claim levels.
10. Do not make the operator upload generated evidence to EBRAINS. Job upload folders
    must be clean, source-only packages.
11. Generated docs should be regenerated by tooling, not hand-edited, unless the
    generator itself is being repaired.
12. The repo must stay readable enough that another competent researcher can
    reproduce the result without uncommitted context.
13. Hard problems are not pushed off casually. A problem may be deferred only if
    it is explicitly classified, documented, bounded, and given a re-entry
    condition.
14. Use leading standards from software engineering, neuroscience, SNN research,
    statistics, mathematics, and hardware engineering. If the relevant standard
    is not known, stop and research it from primary or official sources before
    implementing.
15. Public-repo hygiene is evidence integrity. Do not commit credentials,
    machine-local symlinks, transient root output directories, generated host
    binaries, or private Downloads artifacts.

## 2.1 Agent Thinking Contract

Any automated maintainer working here must reason like a careful research engineer, not like
a demo builder.

The required thinking loop is:

1. Orient: identify the current frozen baseline, active tier, claim boundary,
   and latest returned evidence.
2. Separate categories: decide whether the current problem is science,
   implementation, packaging, platform, documentation, statistics, or user
   workflow.
3. Reduce the problem: find the smallest testable question that advances the
   roadmap without hiding the larger goal.
4. Predeclare: define expected result, pass criteria, fail criteria, artifacts,
   and claim boundary before interpreting outputs.
5. Act minimally: change the smallest surface area that can answer the question.
6. Verify locally: use local simulation, constrained preflight, host tests,
   py-compile, C compile smoke, or unit tests before spending EBRAINS hardware.
7. Escalate deliberately: use hardware, larger seed sweeps, or custom runtime
   work only after the smaller evidence says it is warranted.
8. Preserve evidence: keep success, failure, ambiguity, stdout/stderr, returned
   reports, and generated metrics.
9. Update paperwork immediately: docs must reflect what changed while the reason
   is still fresh.
10. Reassess roadmap: after every meaningful pass/fail, decide whether to
    promote, repair, park, narrow the claim, or move to the next tier.

Do not optimize for appearances. Optimize for making the project more accurate, reproducible, and interpretable.

## 2.1.1 Verify-Before-Work Protocol

Before doing substantive work, verify the current state from repo sources. Do
not rely on chat memory, filenames alone, assumptions, or stale context.

Default verification sequence:

1. Confirm repo root.
2. Check Section 0 of this contract for live handoff state.
3. Check `README.md` for current status.
4. Check `docs/PAPER_READINESS_ROADMAP.md` for current order and next step.
5. Check `CONTROLLED_TEST_PLAN.md` for active tier criteria and boundaries.
6. Check the relevant job README under `ebrains_jobs/` if EBRAINS is involved.
7. Check the relevant runtime/protocol docs if custom runtime is involved.
8. Check latest ingested evidence or Downloads only if the task depends on
   returned results.

Example required behavior:

```text
Before updating the active 4.22w handoff, verify the current 4.22w package and
status from repo docs first, including README, roadmap/test plan, ebrains_jobs
README, and the active job README.
```

This protocol applies before:

1. Writing code.
2. Updating docs.
3. Preparing EBRAINS folders.
4. Giving the operator a JobManager command.
5. Ingesting results.
6. Declaring what is next.
7. Freezing a baseline.
8. Promoting or parking a mechanism.

If verification reveals stale or conflicting docs, resolve the conflict before
continuing. The correct next action is often a documentation repair, not code.

## 2.2 Decision-Making Tree

Use this decision tree after every run or implementation result.

| Observation | Decision | Required Action |
| --- | --- | --- |
| All predeclared criteria pass and regression passes. | Promote or freeze if the tier was a promotion gate. | Update baseline/docs/registry, run validation, state bounded claim. |
| Main metric passes but sham controls also pass. | Effect is not causally isolated. | Do not promote. Add sharper sham separation or narrow claim. |
| CRA improves but strongest external baseline still wins. | Useful internal capability, not superiority. | Document bounded capability, avoid superiority claims, keep baselines visible. |
| Mechanism fails but failure mode is unclear. | Diagnose before adding mechanisms. | Run failure-analysis tier, inspect traces, metrics, leakage, task pressure, and implementation. |
| Mechanism fails cleanly and ablation says it adds no value. | Park or remove from carried baseline. | Preserve as noncanonical scaffold; do not keep tuning indefinitely. |
| Infrastructure blocks run before model execution. | Platform/package failure, not science failure. | Preserve error, repair environment/package/command, rerun only after local check. |
| Hardware fails but local constrained test passes. | Transfer or platform issue. | Compare readback, timing, mapping, resource limits, command protocol, and runner assumptions. |
| Local constrained test fails. | Do not spend hardware. | Repair locally first. |
| New issue threatens current tier validity. | Do not defer silently. | Classify, document, either fix now or record why it is outside the tier and when it returns. |

When uncertain, prefer the path that gives the cleanest falsifiable evidence with
the least new machinery.

## 2.3 Step Granularity Contract

Work in small enough steps that failures are interpretable.

Default unit of progress:

1. One claim per tier.
2. One major mechanism per promotion cycle.
3. One new custom-runtime command surface per hardware primitive tier.
4. One hardware package per prepared upload folder.
5. One active baseline freeze after one promotion/regression gate.

For software mechanisms, the smallest acceptable progression is usually:

```text
diagnostic -> repair/prototype -> sham controls -> external baselines -> compact regression -> freeze
```

For custom SpiNNaker runtime work, the smallest acceptable progression is
usually:

```text
local protocol/host test -> local compile/profile -> prepared EBRAINS package -> one-seed hardware smoke -> multi-seed or harder hardware if scientifically needed
```

For hardware bridge work, the smallest acceptable progression is usually:

```text
local constrained PyNN/sPyNNaker check -> one-seed hardware probe -> multi-seed hardware confirmation -> runtime/resource characterization
```

Do not combine unrelated changes just to move faster. Moving faster by mixing
mechanisms creates slower science because no one can tell what worked.

## 2.4 No Lazy Deferral Contract

It is acceptable to stage work. It is not acceptable to bury a blocker.

A deferral is valid only if all of the following are true:

1. The issue is outside the current tier's claim boundary.
2. The issue does not invalidate the result being claimed now.
3. The issue is documented in the relevant roadmap, test plan, runbook, or
   evidence report.
4. The re-entry condition is explicit, for example: "return before hardware
   transfer", "return if local constrained parity fails", or "return before
   paper lock".
5. The deferral does not force future agents to rediscover the same problem from
   uncommitted context.

If an issue affects correctness, reproducibility, leakage, evidence integrity,
hardware transfer, or claim boundaries, fix or diagnose it now.

## 2.5 Scientific And Engineering Standard

CRA should be built and evaluated as if it will be reviewed by domain experts.
That means the standard is not "the script ran." The standard is "the result is
methodologically defensible."

### Code Standard

1. Prefer simple, deterministic, testable modules.
2. Keep experiment runners explicit and auditable.
3. Avoid hidden global state, hidden generated dependencies, and private manual
   steps.
4. Validate inputs, modes, paths, and expected artifact shapes.
5. Preserve raw metrics and intermediate traces needed for diagnosis.
6. Keep host/hardware/runtime interfaces versioned and documented.
7. Keep source packages small enough that EBRAINS jobs are clean and uploadable.
8. Do not add clever abstractions unless they reduce future ambiguity.

### Neuroscience And SNN Standard

1. Tie mechanisms to known concepts when making mechanistic claims: STDP,
   reward-modulated/three-factor learning, eligibility traces, recurrent and
   lateral motifs, WTA/inhibition, predictive coding, replay/consolidation,
   context binding, working memory, and structural plasticity.
2. Do not use neuroscience words as decoration. If a mechanism is only an
   analogy, say so.
3. Test whether spike timing matters with time-shuffle and rate-only controls
   before making SNN-native claims.
4. Test neuron-parameter sensitivity before claiming robustness.
5. Test circuit motifs with ablations before claiming reef/circuit causality.
6. Distinguish biological inspiration from biological realism.

### Statistics Standard

1. Use multiple seeds for repeatability claims.
2. Preserve per-seed results.
3. Report mean, median, standard deviation, minimum, and tail metrics when
   relevant.
4. Use effect sizes versus strongest relevant baselines.
5. Use confidence intervals or bootstrap intervals for paper-facing comparisons
   when practical.
6. Use paired comparisons when task streams/seeds are paired.
7. Track variance and worst-case collapse, not just average performance.
8. Avoid post-hoc metric switching.
9. If sample count is small, say so and narrow the claim.

### Mathematics And Measurement Standard

1. Define units, scales, horizons, delays, fixed-point formats, and clipping
   bounds.
2. Preserve equations or pseudocode for nontrivial transforms.
3. Track invariants: queue depth, slot capacity, eligibility bounds, memory
   collisions, readout ranges, spike counts, and resource budgets.
4. For runtime work, distinguish wall time, simulated time, `sim.run` calls,
   chip execution, host readback, build/load time, and provenance/report time.
5. For hardware work, track cores/chips used, readback volume, image size,
   compile profile, and resource-limit failures when available.

### Research Standard

1. Use official docs, primary papers, local headers, and returned toolchain
   artifacts for syntax and platform behavior.
2. If a claim depends on an external literature area, update the reviewer-defense
   or roadmap docs with the relevant comparison.
3. If the agent is not sure about a platform/API/math/statistics claim, research
   before coding.
4. Do not rely on memory for unstable external facts or platform details.

## 2.6 Long-Term Goal Versus Current-Tier Discipline

The long-term goal is scalable, increasingly native/on-chip CRA. The current
tier still decides what is legitimate to claim today.

Use this rule:

```text
Build toward the long-term architecture, but prove only the capability actually tested.
```

Examples:

1. A chunked host-learning pass supports hardware transfer of a bounded task; it
   does not prove full continuous on-chip learning.
2. A tiny custom-runtime command pass supports native primitive feasibility; it
   does not prove full CRA mechanism transfer.
3. A one-seed hardware smoke supports feasibility; it does not prove
   repeatability.
4. A software mechanism pass supports capability in software; it does not prove
   SpiNNaker transfer.
5. A predictive or memory scaffold supports the bounded diagnostic; it does not
   prove language, planning, self-awareness, AGI, or ASI.

Do not let future ambition contaminate present evidence. Do not let present
staging erase the long-term architecture.

## 2.7 CRA Is Not A Transformer Contract

Future agents must not accidentally reason about CRA as if it were a transformer,
MLP, standard differentiable RNN, or backprop-trained deep network.

CRA's core research direction is different:

1. No global backpropagation through the full organism for the main CRA claim.
2. No traditional end-to-end gradient-loss optimization for the main CRA claim.
3. No assumption that learning means minimizing a differentiable scalar loss over
   dense layers.
4. No assumption that memory is a hidden-state vector learned by BPTT.
5. No assumption that attention, routing, or composition should default to
   transformer-style softmax attention.
6. No assumption that scaling means only bigger dense models, more parameters,
   or larger training corpora.

CRA should be interpreted through its own mechanisms:

1. Local plasticity.
2. Reward/dopamine-style modulation.
3. Delayed credit through pending horizons or eligibility-like traces.
4. Spiking and temporal structure.
5. Population/ecology dynamics.
6. Lifecycle/self-scaling.
7. Circuit motifs and inhibition.
8. Context memory, routing, replay, predictive binding, and self-evaluation as
   local or bounded mechanisms.
9. Hardware-constrained execution on SpiNNaker or custom runtime paths.

Backprop-trained models, transformers, GRUs, reservoirs, perceptrons, logistic
regression, surrogate-gradient SNNs, and ANN-to-SNN systems are allowed as
baselines or comparison systems. They are not the mental model for implementing
CRA unless a specific tier explicitly defines them as a baseline.

When tempted to ask "how would a transformer solve this?", ask instead:

1. What local signal is available?
2. What delayed consequence is available?
3. What memory or trace can be maintained without leakage?
4. What population/ecology pressure should change behavior?
5. What can plausibly transfer to PyNN/sPyNNaker or native SpiNNaker runtime?
6. What control would prove this is not just hidden supervision?

## 2.8 Hypothesis And Theoretical Work Contract

CRA contains work at different maturity levels. Do not flatten them into one
claim.

Use these labels:

| Label | Meaning | Allowed Language |
| --- | --- | --- |
| `hypothesis` | A proposed mechanism or research direction not yet implemented. | "We hypothesize", "candidate", "planned". |
| `scaffold` | A controlled implementation that tests whether a capability is possible, often host-side. | "Diagnostic scaffold", "bounded prototype". |
| `prototype` | A working mechanism that has not passed sham controls/regression. | "Promising but unpromoted". |
| `promoted mechanism` | Passed controls, ablations, baselines, and compact regression. | "Carried-forward baseline mechanism". |
| `canonical evidence` | Registry/paper-facing evidence with all criteria passed. | "Supports the bounded claim". |
| `theoretical roadmap item` | Future work needed for long-term architecture. | "Not yet evidence". |

For any theoretical or unproven idea, document:

1. Why it is biologically, computationally, or hardware-motivated.
2. What failure mode it is supposed to solve.
3. What would count as success.
4. What would count as failure.
5. What sham control would catch a fake success.
6. Whether it is software-only, PyNN-transferable, hybrid, or native-runtime
   plausible.
7. What must happen before it can affect paper claims.

Do not let theoretical mechanisms leak into claims. It is acceptable to design
toward AGI/ASI-scale substrate questions. It is not acceptable to claim AGI/ASI
evidence without the relevant capability, baseline, transfer, and safety gates.

## 2.9 Long-Term Architecture Migration Contract

The long-term path is not to leave everything as host-side scaffolding. The
long-term path is staged migration toward hardware-realistic and eventually
native/on-chip mechanisms where SpiNNaker makes that possible.

Every promoted host-side mechanism must eventually receive a migration note:

1. Current implementation location: host, PyNN/sPyNNaker, hybrid, or C runtime.
2. State it requires: memory slots, pending queues, traces, routes, readouts,
   counters, random sources, replay buffers, etc.
3. Update frequency: per timestep, per chunk, per event, per reward, or offline.
4. Data movement: what must cross host/chip boundary.
5. Hardware risk: memory, SDRAM, DTCM/ITCM, routing, readback, timing, compile
   size, core count, or protocol complexity.
6. Native path: PyNN-supported, sPyNNaker extension, custom C command, custom C
   continuous loop, or future multi-core runtime.
7. Blocking unknowns and tests needed before hardware transfer.

Host-first mechanism discovery is allowed because it is much cheaper and more
diagnosable. But every host-first mechanism must be honest about migration debt.
If a mechanism cannot plausibly be mapped to hardware, say so before it becomes
central to the architecture.

The goal is not to rewrite everything in C immediately. The goal is to avoid
building mechanisms that make native or scalable execution impossible later.

## 3. Source-Of-Truth Documents

Start with these documents in this order when orienting yourself:

1. `codebasecontract.md`: this operating contract.
2. `README.md`: current top-level status, start-here index, and active claim
   summary.
3. `docs/PAPER_READINESS_ROADMAP.md`: strategic path from current evidence to
   paper-ready claims.
4. `docs/MASTER_EXECUTION_PLAN.md`: operational step-by-step queue from current state through native hardware migration, remaining capability tiers, final matrices, and paper lock.
5. `CONTROLLED_TEST_PLAN.md`: staged tiers, pass/fail criteria, and active test
   boundaries.
6. `docs/REVIEWER_DEFENSE_PLAN.md`: hostile reviewer attacks, fairness rules,
   statistics, and missing proof targets.
7. `docs/CODEBASE_MAP.md`: full map of source, experiments, runtime sidecar,
   evidence, and generated files.
8. `experiments/README.md`: how each experiment runner is intended to be used.
9. `experiments/EVIDENCE_SCHEMA.md`: canonical registry schema and citation
   rules.
10. `STUDY_EVIDENCE_INDEX.md`: generated current canonical evidence index.
11. `docs/PAPER_RESULTS_TABLE.md`: generated paper-facing results table.
12. `docs/RESEARCH_GRADE_AUDIT.md`: generated repository hygiene audit.
13. `docs/SPINNAKER_EBRAINS_RUNBOOK.md`: EBRAINS upload/run/ingest operations and
    lessons learned.
14. `docs/SPINNAKER_EBRAINS_CUSTOM_RUNTIME_GUIDE.md`: custom SpiNNaker runtime
    build/load/protocol guide.
15. `coral_reef_spinnaker/spinnaker_runtime/PROTOCOL_SPEC.md`: custom runtime SDP
    command contract.
16. `coral_reef_spinnaker/spinnaker_runtime/README.md`: custom runtime status,
    scope, and limitations.
17. `docs/PUBLIC_REPO_HYGIENE.md`: public Apache-2.0 artifact policy, ignore
    policy, EBRAINS package rules, security scans, and clean/commit SOP.
18. `baselines/CRA_EVIDENCE_BASELINE_vX.Y.md`: frozen baseline locks.

If these documents conflict, do not guess. Prefer the most specific current
source for the topic, then update the stale document so the conflict disappears.

## 3.1 Question Routing Directory

Use this table to decide where to look before answering, coding, or changing
claims. Do not infer the answer from memory when a source-of-truth document
exists.

| Question | First Place To Look | Then Check |
| --- | --- | --- |
| What is the repo's current state? | `README.md` | `CONTROLLED_TEST_PLAN.md`, `docs/PAPER_READINESS_ROADMAP.md` |
| Where exactly did the last session leave off? | Section 0 of this contract | `README.md`, active job README, latest evidence output |
| What is the current tier order? | `docs/MASTER_EXECUTION_PLAN.md` | `docs/PAPER_READINESS_ROADMAP.md`, `CONTROLLED_TEST_PLAN.md`, latest baseline lock |
| What has actually been proven? | `STUDY_EVIDENCE_INDEX.md` | `docs/PAPER_RESULTS_TABLE.md`, `baselines/CRA_EVIDENCE_BASELINE_vX.Y.md` |
| What is canonical versus noncanonical? | `controlled_test_output/README.md` | `experiments/evidence_registry.py`, `experiments/EVIDENCE_SCHEMA.md` |
| What do we claim in paper language? | `docs/WHITEPAPER.md` | `docs/ABSTRACT.md`, `docs/PAPER_READINESS_ROADMAP.md` |
| What would reviewers attack? | `docs/REVIEWER_DEFENSE_PLAN.md` | `CONTROLLED_TEST_PLAN.md` |
| Where is a source file or system component? | `docs/CODEBASE_MAP.md` | `README.md`, local `rg` search |
| How do experiments run? | `experiments/README.md` | Individual `experiments/tier*.py` runner |
| What artifacts must an experiment emit? | `experiments/EVIDENCE_SCHEMA.md` | Nearby tier runner outputs |
| How do we freeze baselines? | Section 8 of this contract | Existing `baselines/CRA_EVIDENCE_BASELINE_vX.Y.md` |
| How do we validate the repo? | `Makefile` | Section 14 of this contract |
| How do we run EBRAINS jobs? | `docs/SPINNAKER_EBRAINS_RUNBOOK.md` | `ebrains_jobs/README.md`, exact job README |
| What folder should be uploaded to EBRAINS? | `ebrains_jobs/README.md` | Prepared tier report and job README |
| How do we ingest JobManager results? | Section 9.4 of this contract | Tier-specific `--mode ingest`, runbook |
| How does custom C runtime protocol work? | `coral_reef_spinnaker/spinnaker_runtime/PROTOCOL_SPEC.md` | Runtime README, custom-runtime guide |
| Why custom C instead of PyNN? | `coral_reef_spinnaker/spinnaker_runtime/README.md` | Section 10 of this contract |
| What is source versus generated? | `ARTIFACTS.md` | `docs/CODEBASE_MAP.md`, `docs/PUBLIC_REPO_HYGIENE.md` |
| What belongs in the public Git repo? | `docs/PUBLIC_REPO_HYGIENE.md` | `.gitignore`, `.gitattributes`, `ARTIFACTS.md` |
| What is CRA architecturally? | `ARCHITECTURE.md` | `MICROCIRCUIT_DESIGN.md`, whitepaper |
| What code owns configuration? | `coral_reef_spinnaker/config.py` | `coral_reef_spinnaker/config_adapters.py`, codebase map |
| What code owns runtime modes? | `coral_reef_spinnaker/runtime_modes.py` | Tier 4.17+ runners, codebase map |
| What code owns evidence registry? | `experiments/evidence_registry.py` | `experiments/EVIDENCE_SCHEMA.md` |
| What code owns paper table generation? | `experiments/export_paper_results_table.py` | `docs/PAPER_RESULTS_TABLE.md` |
| What code owns audit checks? | `experiments/repo_audit.py` | `docs/RESEARCH_GRADE_AUDIT.md` |
| What is the long-term goal? | `docs/PAPER_READINESS_ROADMAP.md` | `docs/MASTER_EXECUTION_PLAN.md`, Sections 1, 2.6, and 2.9 of this contract |

If the question is code-specific and this table is too broad, use
`docs/CODEBASE_MAP.md` first, then `rg` by symbol/name. Do not open random files
blindly when the map already routes the question.

## 3.2 Tier Order Source Of Truth

The roadmap controls order. File names do not.

Use this priority order when deciding what comes next:

1. `docs/MASTER_EXECUTION_PLAN.md`: operational current execution queue and next-step sequence.
2. `docs/PAPER_READINESS_ROADMAP.md`: canonical forward roadmap and long-term
   goal sequence.
3. `CONTROLLED_TEST_PLAN.md`: exact current test definitions, pass/fail gates,
   and tier boundaries.
4. Latest frozen baseline in `baselines/`: what is currently safe to build on.
5. Latest returned/ingested evidence under `controlled_test_output/`: what just
   happened.
6. `README.md`: human-facing status summary.
7. Current user instruction: can redirect work, but should not silently override
   evidence discipline.

When deciding order, ask:

1. Are we still repairing a failed or blocked active tier?
2. Has the current mechanism passed promotion/regression?
3. Is a baseline freeze required before building on it?
4. Is the next step a science test, hardware transfer, runtime engineering,
   baseline comparison, or documentation/reproduction task?
5. Would doing the next thing now force us to redo avoidable work later?
6. Would postponing the current blocker hide a correctness/scaling problem?

If the roadmap is stale because a new result landed, update the roadmap before
continuing. Do not proceed using a stale plan and hope future agents notice.

## 4. Repository Map

Important top-level paths:

| Path | Role | Rules |
| --- | --- | --- |
| `coral_reef_spinnaker/` | Main CRA source package and SpiNNaker integration. | Source of model behavior. Keep code deterministic, typed where practical, and tied to tests. |
| `coral_reef_spinnaker/spinnaker_runtime/` | Experimental custom C SpiNNaker runtime sidecar. | Use for native primitives PyNN/sPyNNaker cannot express or for on-chip loop migration. Not the default learning source of truth until promoted. |
| `experiments/` | Tier runners, evidence registry, paper-table export, audit tooling. | Every tier runner must emit JSON/CSV/MD artifacts and explicit criteria. |
| `baselines/` | Frozen evidence locks. | Only add a new baseline after a promotion/regression gate passes. Do not rewrite old locks casually. |
| `controlled_test_output/` | Generated evidence, canonical bundles, noncanonical history, manifests, plots. | Never upload this to EBRAINS. It can be very large. Preserve failures. |
| `docs/` | Research-facing docs, roadmap, reviewer defense, runbooks. | Update whenever claims, workflows, tiers, or hardware lessons change. |
| `ebrains_jobs/` | Clean source-only EBRAINS upload folders. | Upload the specific `cra_*` folder only. Do not upload the full repo. |
| `/Users/james/Downloads` | Temporary location where returned EBRAINS artifacts arrive. | Ingest/copy relevant outputs into `controlled_test_output/`; do not treat Downloads as canonical evidence. |
| `docs/PUBLIC_REPO_HYGIENE.md` | Public repo hygiene SOP. | Use for artifact classification, clean/commit passes, security scans, and GitHub readiness. |

## 5. Evidence Levels

Use these labels consistently.

| Label | Meaning | Claim Strength |
| --- | --- | --- |
| `prepared` | Local package/source bundle exists and can be uploaded. | No hardware or science claim. |
| `local_pass` | Local simulation, local diagnostic, or local runtime test passed. | Software/local-only evidence. |
| `hardware_pass` | Returned real hardware artifacts passed all predeclared criteria. | Hardware evidence for the bounded tier only. |
| `blocked` | Infrastructure, packaging, target, build, command, or environment issue prevented the intended test. | No science failure unless the model actually ran and failed. |
| `failed` | The intended scientific/technical criterion was executed and did not pass. | Evidence against that mechanism/config under the tested conditions. |
| `noncanonical` | Useful diagnostic or failed/parked evidence not promoted to paper-table claim. | Keep it; do not overclaim it. |
| `canonical` | Registry/paper-table evidence accepted as a formal result. | Paper-facing claim with explicit boundary. |
| `frozen_baseline` | A baseline lock after promotion/regression. | Reproducible branching point. |

`Noncanonical` does not mean invalid data. It means the result is not a formal
paper-table claim by itself.

## 6. Standard Work Loop For Any New Tier

Do this every time.

1. Read the active roadmap section and controlled test-plan section.
2. State the exact question the tier answers.
3. State the claim boundary before running anything.
4. Define pass criteria and fail criteria before looking at results.
5. Identify controls, ablations, baselines, seeds, run lengths, and metrics.
6. Implement the smallest source change that can test the question.
7. Add or update the tier runner in `experiments/`.
8. Run local or constrained simulation first whenever possible.
9. If hardware is needed, prepare a clean `ebrains_jobs/cra_*` upload folder.
10. Use the exact command emitted by the prepared report or job README.
11. After EBRAINS returns, ingest the downloaded files into
    `controlled_test_output/`.
12. Classify the result: pass, fail, blocked, noncanonical, canonical, or frozen.
13. Update all affected docs and registries.
14. Run validation.
15. Tell the operator what happened, what it means, what it does not mean, and the
    exact next step.

Do not skip local/preflight work just because hardware is the eventual goal. Do
not keep rerunning hardware when a local constrained test could catch the issue.

### 6.1 Tier Design Template

Every new tier or substantial sub-tier should be designed from this template.

```text
Tier:
Status:
Current baseline:
Question:
Hypothesis:
Null hypothesis:
Mechanism under test:
Claim boundary:
Nonclaims:
Tasks:
Seeds:
Run lengths:
Backends:
Hardware mode:
Controls:
Ablations:
External baselines:
Metrics:
Statistical summary:
Pass criteria:
Fail criteria:
Leakage checks:
Resource/runtime measurements:
Expected artifacts:
Docs to update:
Promotion/freeze condition:
Re-entry condition if parked:
```

The null hypothesis matters. A tier should be able to fail cleanly. If no one
can state what result would falsify or narrow the claim, the tier is not ready.

The mechanism under test must be separable from the task and from the runner. If
the only evidence is "the total system changed and a number improved", the tier
is diagnostic at best, not a mechanism proof.

## 7. Mechanism Promotion Contract

A mechanism can be added to the carried-forward CRA baseline only if it earns
promotion.

Required path:

1. Diagnostic tier: show the failure mode exists or the capability is missing.
2. Repair/prototype tier: implement the candidate mechanism.
3. Sham-control tier: prove the effect is not leakage, extra capacity, shuffled
   labels, random replay, wrong keys, or bookkeeping artifacts.
4. Baseline comparison: compare against current frozen CRA and relevant external
   baselines.
5. Ablation: remove or corrupt the mechanism and show the benefit is reduced.
6. Compact regression: ensure Tier 1/2/3 style controls and current baseline
   capabilities still pass.
7. Freeze: create a new `baselines/CRA_EVIDENCE_BASELINE_vX.Y.md` only after the
   promotion/regression gate passes.

If a mechanism is plausible but not yet useful, park it as non-promoted
research scaffolding. Do not keep tuning indefinitely unless a focused failure
analysis identifies a specific bug or pressure mismatch.

## 8. Baseline Freeze Contract

Freeze when a new capability or repair has passed its promotion gate and compact
regression.

A baseline freeze must include:

1. A baseline markdown lock in `baselines/`.
2. A frozen registry snapshot when applicable.
3. Updated `README.md` status.
4. Updated `docs/PAPER_READINESS_ROADMAP.md`.
5. Updated `CONTROLLED_TEST_PLAN.md`.
6. Updated `docs/CODEBASE_MAP.md`.
7. Updated `STUDY_EVIDENCE_INDEX.md` through registry generation if registry
   evidence changed.
8. A clear claim boundary.
9. A clear list of nonclaims.
10. Validation passing.

Do not freeze after a single diagnostic win if no regression/promotional gate was
run. Do not freeze after a hardware package is merely prepared.

## 9. Hardware And EBRAINS Contract

Hardware work has caused the most avoidable pain. Follow this exactly.

### 9.1 Upload Rules

1. Upload only the specific folder under `ebrains_jobs/`, for example
   `ebrains_jobs/cra_422ag`.
2. Do not upload the full repo.
3. Do not upload `controlled_test_output/`.
4. Do not upload `/Users/james/Downloads`.
5. Do not upload caches, compiled host binaries, old reports, or random
   generated clutter.
6. If code changes after a failed EBRAINS run, create a fresh upload folder name
   to avoid stale cache confusion.
7. `ebrains_jobs/cra_*` folders committed to Git must be real source
   directories, never symlinks to `/tmp`, `/private/tmp`, `tier*_output/`, or
   any machine-local path.
8. The JobManager command must include the uploaded folder name, for example:

```text
cra_422ag/experiments/tier4_22w_native_decoupled_memory_route_composition_smoke.py --mode run-hardware --output-dir tier4_22w_job_output
```

Do not invent `bash`, `cd`, or wrapper commands unless the specific prepared job
README says to use them. The EBRAINS JobManager command style used here is the
direct script path plus arguments.

### 9.1.1 Prepared Package QA Rules

Before telling the operator what to upload or run, verify the prepared package systematically, not from memory.

Required checks:

1. Open the prepared `*_report.md` and `*_results.json`.
2. Confirm local mode passed before prepare mode.
3. Confirm prepare mode status is `prepared`, not merely that a folder exists.
4. Count criteria using the correct result field. Current tier criteria use
   `passed`, not always `pass`.
5. Confirm every criterion passes; if the field name is ambiguous, inspect the
   report table rather than trusting a quick script.
6. Confirm the `upload_folder`, `stable_upload_folder`, and `jobmanager_command`
   agree.
7. Confirm the stable `ebrains_jobs/cra_*` folder is byte-for-byte or
   tree-equivalent to the prepared `ebrains_upload_bundle/cra_*` folder.
8. Confirm the upload folder name is fresh for the active tier and not an older
   tier with a similar name. For example, `cra_422x` was a Tier 4.22o repair
   package; Tier 4.22x uses `cra_422ah`.
9. Confirm the job README filename, title, tier number, uploaded folder name,
   command, and report all refer to the same tier. If the README filename says
   the wrong tier, fix the runner/package before telling the operator to upload it.
10. Confirm the package is source-only and does not require
    `controlled_test_output/`, `/Users/james/Downloads`, local caches, or hidden
    chat context.
11. Confirm the command is direct JobManager style and begins with the uploaded
    folder name.
12. Confirm stale docs are either updated immediately or explicitly called out
    before any handoff. Never leave a handoff saying "not yet implemented" after
    local/prepare have already passed.

If any check fails, do not say the job is ready. Repair the package, regenerate
prepare output if needed, and run validation.

### 9.1.2 Pre-Upload Preventive Checks (learned from repeated 4.26 failures)

These checks are mandatory before any EBRAINS handoff. Each rule maps to a
specific failure that cost a hardware attempt.

**Rule 1 — JobManager argparse compatibility (from `cra_426a`).**
EBRAINS JobManager passes ALL arguments as `--flag value`. A runner that uses
positional arguments for mode, output path, or any required parameter will fail
with `unrecognized arguments`. Verify the parser has `--mode`, `--output`, etc.
and that positional fallbacks are optional (`nargs="?"`).

**Rule 2 — Base-module argument contract (from `cra_426d`).**
If the runner imports a base module (e.g., `tier4_22i_custom_runtime_roundtrip`)
and passes `args` to base functions, the runner's `argparse` MUST declare every
argument those functions access. When the base module adds `--dest-cpu`,
`--auto-dest-cpu`, or `--target-probe-run-ms`, every dependent runner must add
them too. Do not rely on exception catching inside the base module to hide the
missing argument.

**Rule 3 — C header declaration guard parity (from `cra_426d`).**
When a `.c` file calls a function inside `#if defined(A) || defined(B)`, the
function's declaration in the `.h` file MUST use the exact same guard
condition. A narrower guard (e.g., `#ifdef A` only) causes an implicit-
declaration warning that becomes a silent runtime failure on hardware.

**Rule 4 — Inter-core message send audit (from `cra_426c`).**
Local C tests for distributed/multi-core features must verify that messages are
actually transmitted, not just stored in a table. A function named
`cra_state_lookup_send()` that only stores state without calling
`spin1_send_sdp_msg()` is a bug, not an implementation. Add a test that
inspects the sent message buffer or the receiving core's state.

**Rule 5 — Command-surface audit for new profiles (from `cra_426e`).**
When adding a new runtime profile, enumerate EVERY command the host runner
sends to cores with that profile. Each command must have an explicit `case` in
the profile's `host_interface.c` dispatch block. Do not assume "the core doesn't
need this command." If the host sends it, the core must ack intentionally.

**Rule 6 — Profile test guard parity (from `cra_426e`).**
`tests/test_profiles.c` must verify both expected commands (status == 0) and
unexpected commands (status == 0xFF) for every profile. When a command moves
from "unexpected" to "expected" for a profile (e.g., adding `CMD_RUN_CONTINUOUS`
to state-server cores), update both the C dispatch AND the profile test in the
same commit.

**Rule 7 — Intermediate artifact writes (from `cra_426b/c`).**
Hardware runners must call `write_json` after each major pre-hardware step:
build completion, target acquisition, and per-core app load. These writes must
be inside the `try` block, not just the `finally` block. If the process is
killed mid-flight, partial artifacts must exist for diagnosis.

**Rule 8 — Top-level crash report coverage (from `cra_426c`).**
The runner's `main()` must catch `BaseException`, not just `Exception`, and
write a `tier*_crash_report.json` before exiting. `SystemExit`, `KeyboardInterrupt`,
and signal-induced termination must all produce a crash report.

**Rule 9 — Parser-key / criteria-key name parity (from `cra_427a`).**
When the C runtime adds new fields to a compact readback schema and the Python
parser extracts them, the dict keys returned by `parse_state_payload()` MUST be
identical to the keys used in the runner's `EXPECTED_METRICS` and `mode_run`
criteria. A mismatch (e.g., parser returns `lookup_requests_sent` but criteria
check `lookup_requests`) causes a silent `None` failure on hardware that looks
like a runtime bug but is actually a naming drift. Mandatory pre-upload check:
1. Print the parser's returned keys for a schema-v2 test payload.
2. Print the criteria keys checked in `mode_run`.
3. Verify they match character-for-character. Do not rely on memory or visual
   inspection of distant code blocks.

**Rule 10 — README-command / argparse-choice parity (from `cra_428a`).**
Any command documented in a runner's README (or JobManager command string) MUST
be accepted by the runner's `argparse` without error. If the README says
`--mode run-hardware`, the `choices=` list in `argparse` MUST include
`run-hardware`. A runner that only implements `local` and `prepare` but documents
`run-hardware` will fail on EBRAINS with `invalid choice` before any hardware
is touched. After any EBRAINS failure, the upload package name MUST be bumped
(e.g., `cra_428a` → `cra_428b`) to avoid cache contamination. Mandatory pre-upload check:
1. Read the README/JobManager command string.
2. Run the exact command locally with `--help` or dry-run.
3. Verify every flag and every mode choice is accepted by the parser.
4. If repairing after a failed upload, bump the package folder name before re-uploading.

**Rule 11 — Container dependency check and upload-size verification (from `cra_429a`).**
EBRAINS JobManager containers may lack standard utilities such as `jq`. If the
job's `setup.bash` or entry script depends on `jq` to parse metadata, the
fallback path may extract the zip incorrectly, use the wrong working directory,
or fail to find the runner script. Additionally, stale cached uploads or
browser-UI zip creation can produce packages much smaller than the local
verified bundle. Mandatory pre-upload checks:
1. Verify the local prepared package zip size. A correct zip of a four-core
   MCPL package with runtime source and `.aplx` images is typically 200–250KB.
   A zip under 100KB is suspicious and likely incomplete or stale.
2. If the EBRAINS web UI creates the zip automatically, confirm the uploaded
   folder contains all transitive Python imports, C source, and `.aplx` files.
3. If a previous upload of the same name failed, ALWAYS bump the package name
   per Rule 10. Do not rely on the web UI to invalidate stale cached zips.
4. If the runner depends on `jq`, `python3`, or other shell utilities inside
   `setup.bash`, verify they exist in the EBRAINS container or make the script
   robust to their absence with explicit fallbacks.

### 9.2 Hardware Evidence Rules

A hardware tier is not passed until returned artifacts show all required
criteria. Typical criteria include:

1. Real hardware run attempted.
2. Hardware target configured or board selected by the actual runner.
3. Correct backend or custom runtime path used.
4. Zero synthetic fallback.
5. Zero `sim.run` failures for PyNN/sPyNNaker tiers, or zero load/SDP/runtime
   failures for custom-runtime tiers.
6. Zero summary-read/readback failures.
7. Real spike readback, state readback, or protocol readback as required by the
   tier.
8. Metrics above threshold.
9. Returned artifacts ingested into `controlled_test_output/`.
10. Claim boundary documented.

A target-check failure can be an environment/visibility problem. It is not a
science failure unless the model actually ran and failed the scientific metric.

### 9.3 Ingest Rules

The operator downloads EBRAINS returned outputs to `/Users/james/Downloads`.

Use tier-specific ingest commands when available, usually of this shape:

```text
experiments/<tier_runner>.py --mode ingest --ingest-dir /Users/james/Downloads --output-dir controlled_test_output/<tier>_<timestamp>_<status>_ingested
```

If an ingest command is intentionally ingesting a failed run and returns nonzero,
it can be acceptable to run it with shell tolerance, but only if the resulting
failure is documented accurately. Do not hide the nonzero status.

Do not delete files from Downloads unless the operator explicitly asks. Copy or
normalize what is needed into `controlled_test_output/`.

### 9.4 JobManager Result Ingest SOP

When the operator says an EBRAINS/JobManager run finished or errored and files were
downloaded, follow this exact process.

1. Stop adding new mechanisms. First preserve and interpret the returned run.
2. Identify likely returned files in `/Users/james/Downloads` by timestamp,
   filename, tier name, report title, zip contents, and output directory names.
3. Open the most relevant human report first, usually `*_report*.md`,
   `README*.md`, or a top-level failure traceback.
4. Open the machine-readable results next, usually `*_results*.json`,
   `*_summary*.csv`, manifest files, stdout/stderr, traceback text, and build
   logs.
5. If a `reports.zip` or similar archive is present, inspect or extract it into
   a temporary/local controlled ingest path; do not treat the zip name alone as
   sufficient evidence.
6. Determine the failure/pass stage before interpreting science:
   command/entrypoint, import, dependency, package path, build, target
   acquisition, load, SDP/protocol, `sim.run`, readback, metric, criteria, or
   ingest correction.
7. Use the tier-specific ingest mode if the runner provides one.
8. Write the ingested output under a clear directory name in
   `controlled_test_output/`, including tier, date, and status such as
   `hardware_pass_ingested`, `hardware_fail_ingested`, `ebrains_build_fail`, or
   `blocked_ingested`.
9. Preserve exact returned error text, stdout/stderr, build logs, and remote
   metadata. Do not summarize away the only diagnostic clue.
10. If the remote runner has a known criterion bug and the raw remote status is
    wrong, preserve both the raw status and the corrected ingest status. Explain
    the correction in the report and docs.
11. Update latest manifest pointers only when the tier convention expects them.
12. Update `ebrains_jobs/README.md` when a prepared job returns a pass/fail or a
    command/platform lesson changes.
13. Update `docs/SPINNAKER_EBRAINS_RUNBOOK.md` for every new platform lesson,
    mistake, command rule, target issue, build issue, or upload packaging rule.
14. Update `docs/SPINNAKER_EBRAINS_CUSTOM_RUNTIME_GUIDE.md` for every custom
    runtime build/load/protocol lesson.
15. Update `CONTROLLED_TEST_PLAN.md`, `docs/PAPER_READINESS_ROADMAP.md`, and
    `README.md` if the result changes the active roadmap or claim state.
16. Run validation after doc/evidence updates.
17. Report to the operator using this shape:

```text
What happened:
Evidence files:
Failure/pass stage:
Science meaning:
What it does not mean:
Docs/artifacts updated:
Validation:
Exact next step:
```

Never respond to a returned EBRAINS error by guessing a new upload command before
reading the returned files. Never make the operator upload `controlled_test_output/`
to fix an ingest or source packaging problem.

## 10. PyNN, sPyNNaker, And Custom Runtime Boundaries

The project uses layers. Do not blur them.

| Layer | Use It For | Do Not Claim |
| --- | --- | --- |
| Local software/NEST/Brian2 diagnostics | Fast science tests, mechanism development, constrained preflight. | Hardware transfer. |
| PyNN/sPyNNaker standard runtime | Supported SpiNNaker network mapping, standard populations, standard readback, chunked proof-grade hardware runs. | Dynamic topology or native on-chip mechanism if host is doing it. |
| Chunked host learning | Audited hardware bridge where the board runs chunks and host updates between chunks. | Fully continuous/on-chip learning. |
| Custom C runtime sidecar | Native primitives PyNN cannot express, persistent on-chip state, pending horizons, compact protocol tests, future continuous loops. | Full CRA backend until promoted through gates. |
| Future full native runtime | Long-term goal for continuous on-chip/hybrid autonomy. | Current evidence unless actually implemented and passed. |

Use PyNN/sPyNNaker first for standard supported operations. Use custom C only
where it is needed for native state, command surfaces, unsupported dynamic
behavior, on-chip pending horizons, efficient compact readback, or continuous
runtime migration.

Full on-chip operation is the long-term target, but the route there is staged:
small native primitives, local parity, EBRAINS hardware smoke, composition,
mechanism transfer, then broader continuous loops.

## 11. Custom C Runtime Contract

The custom runtime must remain small, testable, and protocol-driven.

Rules:

1. `PROTOCOL_SPEC.md` is the command contract. Update it for every command,
   payload, response, status code, and fixed-point format change.
2. `colony_controller.py` and C opcode definitions must stay synchronized.
3. Host tests must cover new commands before EBRAINS hardware attempts.
4. Use fixed-size bounded structures unless a specific dynamic allocation path is
   justified and tested.
5. Use s16.15 or documented fixed-point math consistently when the protocol says
   so.
6. Pending horizons must not store hidden target labels if the tier is testing
   delayed credit without leakage.
7. State readback must expose enough data to distinguish transport failure from
   model failure.
8. Runtime profiles such as `RUNTIME_PROFILE=decoupled_memory_route` must record
   what command surface is enabled and what is compiled out.
9. If EBRAINS build/load fails, preserve stdout/stderr and classify the failure
   by exact cause: ITCM overflow, missing symbol, callback enum mismatch, target
   allocation, command timeout, readback schema mismatch, etc.
10. If image size is the issue, prefer real profile/resource-budget fixes over
    bandaids. Compile only needed handlers for tiny primitive tiers, use
    `-Os`, section invalid data collection, and document the profile.

Current runtime source of truth lives in:

1. `coral_reef_spinnaker/spinnaker_runtime/README.md`
2. `coral_reef_spinnaker/spinnaker_runtime/PROTOCOL_SPEC.md`
3. `docs/SPINNAKER_EBRAINS_CUSTOM_RUNTIME_GUIDE.md`
4. `docs/SPINNAKER_EBRAINS_RUNBOOK.md`

## 12. Experiment Runner Contract

Every substantial tier runner in `experiments/` should follow this pattern.

Required behavior:

1. Deterministic seeds.
2. Explicit tier name and claim boundary.
3. Modes where appropriate: `local`, `prepare`, `run-hardware`, `ingest`.
4. Machine-readable `*_results.json`.
5. Human-readable `*_report.md`.
6. Summary `*.csv` when multiple tasks/seeds/variants exist.
7. Manifest or latest-manifest pointer when the tier is part of the active
   evidence stream.
8. Criteria table with pass/fail per criterion.
9. Raw metrics preserved, not just pass/fail.
10. External baselines included when the tier makes comparative claims.
11. Controls and ablations included for mechanism claims.
12. `prepared` reports clearly marked as not hardware evidence.
13. Returned hardware reports clearly separate remote run status and ingest
    correction status if a runner bug affected criteria.

Do not create experiment scripts that require uncommitted context, manually
copied hidden files, or generated evidence folders to run.

## 13. Documentation Update Matrix

When something changes, update the right docs.

| Change | Must Update |
| --- | --- |
| New active status or major result | `README.md`, `CONTROLLED_TEST_PLAN.md`, `docs/PAPER_READINESS_ROADMAP.md` |
| New claim or claim boundary | `README.md`, `docs/WHITEPAPER.md`, `docs/PAPER_READINESS_ROADMAP.md`, `docs/REVIEWER_DEFENSE_PLAN.md` if reviewer-facing |
| New tier runner | `experiments/README.md`, `docs/CODEBASE_MAP.md`, relevant roadmap/test-plan sections |
| New canonical evidence | `experiments/evidence_registry.py`, generated `STUDY_EVIDENCE_INDEX.md`, generated `docs/PAPER_RESULTS_TABLE.md`, generated `controlled_test_output/README.md` |
| New noncanonical failure/diagnostic | `CONTROLLED_TEST_PLAN.md`, `docs/CODEBASE_MAP.md`, possibly `docs/SPINNAKER_EBRAINS_RUNBOOK.md` for platform lessons |
| New frozen baseline | `baselines/CRA_EVIDENCE_BASELINE_vX.Y.md`, `README.md`, `docs/README.md` if listed, `docs/CODEBASE_MAP.md` |
| New EBRAINS upload folder | `ebrains_jobs/README.md`, `docs/SPINNAKER_EBRAINS_RUNBOOK.md` if command or lesson changed |
| New custom runtime command | `PROTOCOL_SPEC.md`, runtime `README.md`, `docs/SPINNAKER_EBRAINS_CUSTOM_RUNTIME_GUIDE.md`, host tests |
| New baseline model or fairness rule | `docs/REVIEWER_DEFENSE_PLAN.md`, `CONTROLLED_TEST_PLAN.md`, `experiments/README.md` |
| Public-repo hygiene or artifact-policy change | `.gitignore`, `.gitattributes`, `ARTIFACTS.md`, `docs/PUBLIC_REPO_HYGIENE.md`, `docs/CODEBASE_MAP.md` |
| Prepared package QA issue | Fix runner/package source first, regenerate prepared output, update job README/report references, then validation |
| Generated doc becomes stale | Fix generator, then run validation. Do not hand-edit generated output unless documented. |

Generated docs include at least:

1. `STUDY_EVIDENCE_INDEX.md`
2. `docs/PAPER_RESULTS_TABLE.md`
3. `docs/RESEARCH_GRADE_AUDIT.md`
4. `controlled_test_output/README.md`

### 13.1 Documentation Update SOP

Use this SOP whenever code, evidence, hardware status, roadmap order, or claims
change.

#### Step 1: Classify The Change

First classify what happened. Pick all that apply:

1. Source code change.
2. New or changed experiment runner.
3. New local result.
4. New EBRAINS/hardware result.
5. Failed or blocked run.
6. New platform lesson.
7. New custom runtime command/protocol.
8. New mechanism promotion/regression.
9. New frozen baseline.
10. New paper-facing claim.
11. Roadmap/order change.
12. Documentation-only clarification.

The classification determines which docs must change. Do not update only the
README if the roadmap, runbook, protocol, or registry also changed.

#### Step 2: Start With The Most Specific Truth

Update documents in this order:

1. Source-level truth: code, protocol specs, experiment runner constants, pass
   criteria, and artifact schemas.
2. Evidence-level truth: ingested outputs, JSON/CSV summaries, manifests,
   registry entries, and baseline locks.
3. Operational truth: EBRAINS job README, runbook, custom-runtime guide, exact
   upload folder and command.
4. Roadmap/test-plan truth: controlled test plan, paper-readiness roadmap,
   reviewer-defense plan.
5. Reader-facing summaries: README, abstract, whitepaper, codebase map.
6. Generated summaries: evidence index, paper table, audit, controlled output
   README through validation tooling.

This prevents the human-facing summary from saying something the source or
evidence does not support.

#### Step 3: Update By Scenario

For a new experiment runner:

1. Add or update the runner in `experiments/`.
2. Add its purpose, modes, expected artifacts, and claim boundary to
   `experiments/README.md`.
3. Add it to `docs/CODEBASE_MAP.md`.
4. Add or update its tier section in `CONTROLLED_TEST_PLAN.md`.
5. Add roadmap references only if it changes forward order.
6. Run syntax checks and validation.

For a local pass:

1. Preserve artifacts in `controlled_test_output/`.
2. Mark it as local/software evidence, not hardware evidence.
3. Update `CONTROLLED_TEST_PLAN.md` if it changes tier status.
4. Update roadmap only if the result changes the next step.
5. Freeze only if this was a promotion/regression gate.

For a local fail:

1. Preserve artifacts.
2. Classify whether the failure is implementation, task design, mechanism,
   baseline, statistics, or environment.
3. Update test plan with the narrowed conclusion.
4. Do not promote.
5. Decide whether to repair, sharpen controls, park, or narrow the claim.

For an EBRAINS/hardware pass:

1. Ingest returned files using Section 9.4.
2. Update `ebrains_jobs/README.md` with returned status, metrics, command, and
   boundary.
3. Update `docs/SPINNAKER_EBRAINS_RUNBOOK.md` if any platform lesson changed.
4. Update custom-runtime guide/protocol if native runtime behavior changed.
5. Update `README.md`, `CONTROLLED_TEST_PLAN.md`, and roadmap if the active
   evidence state changed.
6. Update Section 0 of this contract with the new live handoff state and next
   plan.
7. Update registry only if the result is canonical paper-table evidence.
8. Run validation.

For an EBRAINS/hardware fail or blocked run:

1. Ingest and preserve returned files.
2. Identify exact failure stage before suggesting a fix.
3. Update runbook with the mistake, symptom, cause, and repair.
4. Update job README if the active upload folder is superseded.
5. Do not call it a science failure unless the model actually ran and failed
   the scientific criteria.
6. Update Section 0 of this contract with the new live handoff state and next
   repair plan.
7. Prepare a new upload folder after source changes; do not reuse stale package
   names.

For a prepared EBRAINS package:

1. Run the Prepared Package QA Rules in Section 9.1.1.
2. Verify the stable upload folder and generated upload bundle match.
3. Verify the job README filename/title/tier/command match the active tier.
4. Verify the command starts with the actual folder the operator must upload.
5. Verify similarly named older folders are called out if they might confuse the
   user.
6. Update Section 0 with the exact folder and command only after all checks pass.
7. Run validation before handoff.

For a custom runtime command/protocol change:

1. Update C headers/source and host controller together.
2. Update `PROTOCOL_SPEC.md`.
3. Update runtime README status if tier capability changed.
4. Update custom-runtime guide if build/load/EBRAINS behavior changed.
5. Add or update host tests.
6. Run runtime host tests and repo validation.

For a mechanism promotion:

1. Confirm sham controls, ablations, baseline comparison, and compact regression
   passed.
2. Freeze a baseline.
3. Update roadmap, controlled test plan, README, and relevant claim docs.
4. Add migration notes if the mechanism is host-side and must later transfer to
   hardware.
5. Update Section 0 of this contract with the new current baseline and next
   roadmap step.
6. Do not promote theoretical/scaffold work without the gate.

For a roadmap/order change:

1. Update `docs/PAPER_READINESS_ROADMAP.md` first.
2. Update `CONTROLLED_TEST_PLAN.md` so the executable tier plan agrees.
3. Update README status if the next-step summary changes.
4. Update reviewer-defense plan if the change affects paper-grade safeguards.
5. Update Section 0 of this contract so the live handoff state matches the new
   order.

#### Step 4: Regenerate Generated Docs

After source/evidence/doc changes, run the appropriate generation path.

Default:

```text
make validate
```

If only registry/paper table changed and time matters:

```text
make registry
make paper-table
make audit
```

Generated docs should not be patched by hand to force a pass. Fix the source of
truth or generator instead.

#### Step 5: Final Documentation Sanity Check

Before final response, check:

1. Does README still match the roadmap?
2. Does the controlled test plan still match the runner?
3. Does the roadmap still match the latest baseline/evidence?
4. Does the EBRAINS runbook contain any new platform lesson?
5. Does the custom runtime guide/protocol match the code?
6. Are generated docs regenerated?
7. Are failures preserved rather than erased?
8. Is the claim boundary explicit?

If any answer is no, keep working.

## 14. Validation Contract

Before declaring work complete, run the strongest reasonable validation for the
change.

Common commands:

```text
make validate
make test
make registry
make paper-table
make audit
```

### 14.1 Automated Guardrails

Manual discipline is not enough for this project. Any mistake that causes an
EBRAINS failure, stale status claim, wrong upload package, wrong JobManager
command, false evidence claim, or repeated human confusion must be converted
into an automated or semi-automated guardrail before final handoff whenever it
is technically practical.

Guardrail ownership:

| Problem class | Primary guardrail location | Required behavior |
| --- | --- | --- |
| Tier-specific pass/fail logic | The tier runner criteria list and generated report/results JSON | The runner must fail closed and preserve every failed criterion. |
| Repo, evidence, and documentation consistency | `experiments/repo_audit.py` through `make audit` / `make validate` | Stale claims, missing evidence files, broken registry rows, or contradictory docs must fail validation where practical. |
| Registry and paper-table drift | `make registry`, `make paper-table`, and generated audit artifacts | Canonical evidence and paper tables must regenerate from source, not hand edits. |
| Python syntax/import mistakes | `make test`, `python3 -m py_compile`, and targeted runner execution | A runner is not ready if it has not at least compiled and run in local/prepare mode when applicable. |
| EBRAINS package mistakes | Tier prepare mode plus Section 9.1.1 package QA | The upload folder, README, command, artifacts, and report must agree before the operator is told to upload. |
| Custom runtime protocol drift | `coral_reef_spinnaker/spinnaker_runtime` host tests, compile smokes, and `PROTOCOL_SPEC.md` | C/Python command IDs, payload layouts, response semantics, and runtime profiles must stay synchronized. |
| Hardware claim inflation | Tier report criteria, evidence registry, and roadmap claim boundary | Local, prepared, one-seed, three-seed, PyNN, custom-runtime, hybrid, and on-chip claims must never be conflated. |

Specific failures that must be caught by guardrails:

1. A prepared package report says one tier while the job README filename, title,
   or command says another tier.
2. The command references an old similarly named folder, for example a stale
   `cra_422x` folder when the active package is `cra_422ah`.
3. A source doc still says "not yet run", "not implemented", or "planned only"
   after local/prepare/hardware evidence has already passed.
4. A prepared package includes or depends on `controlled_test_output/`,
   `/Users/james/Downloads`, local caches, compiled binaries, or hidden chat
   context.
5. A quick script counts the wrong criterion field, for example reading `pass`
   when the current result schema uses `passed`.
6. A JobManager command invents `bash`, `cd`, `python3`, or wrapper syntax that
   the prepared job README does not require.
7. A runner says hardware evidence exists when the run was only local or
   prepared.
8. A custom runtime command changes in C but not in the Python host controller,
   protocol spec, runtime guide, and tests.
9. A generated doc is patched by hand instead of regenerating from the source of
   truth.
10. A validation failure is dismissed as "acceptable" without recording the
    exact claim boundary and risk.
11. A returned hardware-pass ingest leaves stale upload/run instructions for the
    tier that already passed.
12. A source doc says "awaiting returned hardware", "awaits returned EBRAINS",
    or equivalent after a `*_hardware_pass_ingested` bundle exists for that tier.
13. Criteria counts are reported ambiguously. If a run has remote criteria plus
    ingest criteria, docs must say both, for example `89 remote + 1 ingest = 90
    total`, not a loose `89/89` everywhere.
14. A compact-readback criterion checks a cumulative telemetry counter instead
    of the actual host-observed payload length. For lifecycle schema-v1,
    `payload_len` proves the compact reply size; `readback_bytes` is cumulative
    and is expected to grow after repeated replies.

Definition of done for a new guardrail:

1. Reproduce the failure mode with a deterministic check, fixture, local
   package, or known bad artifact.
2. Add the check to the narrowest correct layer:
   - tier-local criteria for tier-specific science/runtime failures
   - `experiments/repo_audit.py` for cross-doc/evidence/package consistency
   - runtime host tests for C/protocol behavior
   - registry/paper-table generation for canonical evidence drift
3. Confirm the check fails on the bad state or would have caught the observed
   mistake.
4. Repair the bad state.
5. Run the strongest relevant validation, usually `make validate`, and record
   the result in the final response or handoff.
6. Update this contract, the EBRAINS runbook, or the relevant guide if the new
   guardrail changes the operating procedure.

If a guardrail cannot be automated cleanly, write an explicit manual checklist
item in this contract or the relevant runbook and explain why automation is not
currently practical. Do not rely on memory, uncommitted context, or "we know what we
mean."

For custom runtime host-side changes:

```text
make -C coral_reef_spinnaker/spinnaker_runtime clean-host test
```

For Python runner syntax:

```text
python3 -m py_compile experiments/<runner>.py
```

For C profile compile smoke, use the relevant profile macros and include paths.
Example shape:

```text
cc -std=c11 -Wall -Wextra -Wno-unused-parameter -Wno-int-to-pointer-cast \
  -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 \
  -I coral_reef_spinnaker/spinnaker_runtime/stubs \
  -I coral_reef_spinnaker/spinnaker_runtime/src \
  -c coral_reef_spinnaker/spinnaker_runtime/src/main.c \
  -o /tmp/cra_main_dec.o
```

If validation cannot be run, say exactly why and what risk remains.

## 15. Reference And Syntax Contract

Do not guess external APIs or SpiNNaker syntax.

Reference order:

1. Local repo docs and code.
2. Local installed package docs or source.
3. EBRAINS returned artifacts, toolchain errors, and official headers visible in
   the job environment.
4. Official documentation from the relevant project.
5. Primary papers or official specs for research claims.

For SpiNNaker/PyNN/sPyNNaker custom runtime work, prefer:

1. `docs/SPINNAKER_EBRAINS_RUNBOOK.md`
2. `docs/SPINNAKER_EBRAINS_CUSTOM_RUNTIME_GUIDE.md`
3. `coral_reef_spinnaker/spinnaker_runtime/PROTOCOL_SPEC.md`
4. Existing working EBRAINS job READMEs under `ebrains_jobs/`
5. Official SpiNNakerManchester, PyNN, sPyNNaker, Spin1API, SARK, and EBRAINS
   docs or headers.

If internet research is needed, use official or primary sources, cite links in
the final answer, and update the relevant runbook with the lesson learned.

## 16. Baseline Fairness And Statistics Contract

Comparative claims require fair baselines.

Baseline fairness means:

1. Same task stream.
2. Same train/test/evaluation windows.
3. Same seed set where possible.
4. Same reward visibility.
5. Same delay information.
6. Similar tuning budget or documented tuning budget.
7. No CRA-only task hints.
8. No hidden oracle data.
9. Strong simple baselines included, not only weak ones.
10. Per-seed results preserved.

Paper-grade metrics should include:

1. Mean, median, standard deviation, and minimum where applicable.
2. Seed variance.
3. Tail accuracy or late-window performance when adaptation matters.
4. Recovery after switches.
5. Effect size versus strongest relevant baseline.
6. Confidence interval or bootstrap interval when the result is paper-facing.
7. Runtime/resource profile for hardware claims.

## 17. Reviewer-Defense Contract

Assume reviewers will ask hostile but fair questions.

Common attacks and required defenses:

| Reviewer Attack | Required Defense |
| --- | --- |
| It only works on one seed. | Multi-seed repeats or explicit single-seed boundary. |
| It is leakage. | Shuffled labels, wrong-key controls, no-reward controls, no-hidden-target pending horizons. |
| It is just extra capacity. | Same-capacity fixed controls, sham lifecycle controls, active-mask controls. |
| It is just a baseline task. | External baselines with fair tuning and hard tasks. |
| It is not really spiking. | Temporal-code tests, spike readback, time-shuffle/rate-only controls. |
| It is one fragile LIF setting. | Neuron-parameter sensitivity tests. |
| It is not hardware. | Returned real SpiNNaker artifacts with zero fallback. |
| It is not on-chip. | Explicitly separate host/chunked/hybrid/native evidence. |
| It is not scalable. | Runtime characterization, resource accounting, custom runtime data structures, compact readback. |
| It is unsupported speculation. | Claim boundaries, failures preserved, nonclaims stated. |

## 18. Current Capability Ladder

The roadmap owns the live order, but the conceptual ladder is:

1. Reflex adaptation.
2. Delayed credit.
3. Nonstationary adaptation.
4. Hardware transfer.
5. Runtime/resource characterization.
6. Lifecycle/self-scaling.
7. Circuit motif causality.
8. Context memory and keyed binding.
9. Replay/consolidation.
10. Predictive/context modeling.
11. Compositional reuse and routing.
12. Temporal-code and neuron-parameter robustness.
13. Pre-reward predictive-binding representation.
14. Self-evaluation/reliability monitoring.
15. Policy/action selection.
16. Working memory/context binding expansion.
17. Curriculum/environment generation.
18. Long-horizon planning/subgoal control.
19. Hardware transfer of promoted mechanisms.
20. Hybrid/on-chip and eventually continuous/native operation.
21. Real-ish external tasks and reproduction package.
22. Paper lock.

Do not jump to the end. Every rung needs proof or an explicit decision to narrow
the claim.

## 19. Communication Contract

When reporting to the operator, separate these clearly:

1. What happened.
2. What file or artifact proves it.
3. Whether it is science, infrastructure, packaging, or command failure.
4. What it means.
5. What it does not mean.
6. What was updated.
7. What validation ran.
8. The exact next command, folder, or decision.

Do not delegate investigative work that can be completed from the repository or returned artifacts. Do not ask the
operator to upload GB-scale generated folders. Do not tell the operator to run shell
commands for EBRAINS if the actual platform expects a direct JobManager command.

## 20. Anti-Patterns To Avoid

These are known ways to damage the project.

1. Uploading `controlled_test_output/` to EBRAINS.
2. Making EBRAINS jobs depend on local generated evidence folders.
3. Reusing stale upload folder names after source changes.
4. Treating a target-check failure as a model failure.
5. Treating prepared packages as hardware evidence.
6. Treating one-seed hardware as repeatability.
7. Calling chunked host learning fully on-chip.
8. Calling tiny custom-runtime smoke tests full CRA mechanism transfer.
9. Adding several mechanisms at once and not knowing which one helped.
10. Freezing a baseline without compact regression.
11. Hand-editing generated registry outputs instead of updating generators.
12. Hiding failed runs because they look bad.
13. Overstating AGI/ASI relevance before capability evidence exists.
14. Using unofficial or guessed SpiNNaker API syntax when official docs or
    headers can be checked.
15. Leaving stale docs after a run changes the active status.
16. Trusting a folder name without checking the prepared report and job README.
17. Letting a copied README filename or title point to the wrong tier.
18. Telling the operator to upload a similarly named older `cra_*` folder.

## 21. Session Start Checklist For Any Automated Maintainer

At the start of a new work session:

1. Confirm repo root. Preferred root is `/Users/james/JKS:CRA` unless the operator
   explicitly says otherwise.
2. Read this file.
3. Read `README.md` current status.
4. Read the relevant section of `CONTROLLED_TEST_PLAN.md`.
5. Read the relevant section of `docs/PAPER_READINESS_ROADMAP.md`.
6. If EBRAINS is involved, read `docs/SPINNAKER_EBRAINS_RUNBOOK.md` and the
   exact job README under `ebrains_jobs/`.
7. If custom runtime is involved, read `PROTOCOL_SPEC.md` and the runtime README.
8. Inspect returned files in `/Users/james/Downloads` only if the operator says new
   output was downloaded.
9. Avoid broad rewrites until you know whether the task is documentation,
   ingestion, diagnosis, repair, or new mechanism work.
10. Preserve unrelated user changes.

## 22. Completion Checklist

Before saying a task is done:

1. Files were changed intentionally.
2. Generated files were generated by tooling when applicable.
3. Evidence was classified accurately.
4. Docs that should point to the result were updated.
5. Runbook was updated if a platform lesson was learned.
6. Hardware commands/folders were exact and current.
7. Section 0 of this contract was updated if the current status, active tier,
   baseline, or next plan changed.
8. Validation ran or the residual risk was stated.
9. Public-repo checks were considered for commits: no credentialed remotes, no
   `ebrains_jobs/` symlinks, no transient root outputs, no generated host
   binaries, and no unexpected large files.
10. The final answer includes absolute file references when pointing to files.
11. The next step is clear.

## 23. Agent Quality And Handoff Contract

This section exists so another automated maintainer can continue the project at the same
standard instead of merely following filenames.

### 23.1 Quality Bar

The expected quality bar is:

1. Research-grade evidence discipline.
2. Industry-grade code hygiene.
3. Neuroscience/SNN claims tied to mechanisms and controls.
4. Statistical claims tied to seeds, variance, baselines, and effect sizes.
5. Hardware claims tied to returned artifacts, resource limits, and exact command
   paths.
6. Documentation that lets a cold reader reproduce the workflow.
7. No hidden manual state.
8. No casual deferrals of correctness, reproducibility, leakage, or scalability
   problems.

If a future agent cannot meet this bar with current context, it must stop and
read/research rather than improvise.

### 23.2 Handoff Package For Another Agent

When handing work to another agent or future session, provide:

1. Repo root.
2. Current baseline version.
3. Active tier.
4. Current claim boundary.
5. Latest pass/fail/blocked result.
6. Exact artifacts or downloaded files to inspect.
7. Exact docs already updated.
8. Exact docs still needing update.
9. Exact validation status.
10. Exact next command or next decision.
11. Known traps or previous failed attempts.
12. Whether the next task is local, EBRAINS, custom runtime, mechanism science,
    baseline comparison, or documentation.

Do not leave a handoff that says only "continue." A useful handoff should let
the next agent begin without reconstructing the last hour from chat.

### 23.3 Code Review Before Completion

Before completing any code-changing task, the agent must review its own work:

1. Is the changed surface area minimal?
2. Did it touch unrelated files?
3. Does it preserve deterministic seeds and artifact names?
4. Does it preserve source/generated boundaries?
5. Does it preserve hardware claim boundaries?
6. Does it introduce hidden host state or leakage?
7. Does it break EBRAINS source-only package assumptions?
8. Does it require generated evidence to run?
9. Does it need new tests?
10. Did validation cover the risk?

If the answer reveals a risk, fix it or document it before final response.

### 23.4 Research Review Before Promotion

Before promoting a result, the agent must ask:

1. What is the null hypothesis?
2. What baseline could explain this result more simply?
3. What leakage path could fake this result?
4. What sham control would break a fake mechanism?
5. Does the effect survive seeds?
6. Does the effect survive ablation?
7. Does it improve the current frozen baseline or only match it?
8. Does it regress any previous capability?
9. Is the result software-only, hardware bridge, or native/on-chip?
10. Is the claim phrased at the correct level?

Promotion without this review is not allowed.

### 23.5 When To Research Instead Of Coding

Stop and research before coding when:

1. The task depends on SpiNNaker/PyNN/sPyNNaker API behavior not already proven
   in this repo.
2. The task depends on C runtime symbols, event enums, memory layout, or linker
   behavior not already verified.
3. The task depends on a statistical method, baseline, or neuroscience concept
   the agent cannot explain clearly.
4. The operator asks whether the current approach is scientifically correct.
5. The result will affect paper claims, hardware claims, or long-term
   architecture.

Use official docs, local headers, primary papers, and returned toolchain
artifacts. Then update the relevant runbook or reviewer-defense document so the
research becomes part of the repo, not uncommitted context.

### 23.6 User Interaction Standard

The operator should not have to compensate for unclear automation or incomplete handoffs.

The agent must:

1. Give short progress updates during substantial work.
2. Be explicit when confused and then investigate.
3. Avoid making the operator upload unnecessary folders.
4. Give exact EBRAINS upload folders and JobManager commands.
5. Explain failures as science, infrastructure, command, packaging, build, or
   readback failures.
6. Keep the long-term goal visible without overclaiming current evidence.
7. Be willing to say "this is not proven yet."
8. Be willing to say "the current plan is wrong" if evidence says so.
9. Never lower documentation or code quality to save time or tokens.

## 24. Final Rule

This repo is allowed to be ambitious, but it is not allowed to be sloppy.

Every future agent should optimize for the same thing: make CRA easier to audit,
easier to reproduce, harder to dismiss, and more honest about what has and has
not been proven.

## 25. Contract Self-Test For New Agents

Before giving a new automated maintainer write access to serious code, evidence, EBRAINS
jobs, or claims, test whether it can follow this contract.

### 25.1 Minimum Onboarding Test

Ask the agent to answer these questions from the repo, not from chat memory:

1. What is the repo root?
2. What is the current frozen baseline?
3. What is the active hardware/custom-runtime tier?
4. What has actually been proven canonically?
5. What is noncanonical but important?
6. What is the next roadmap step and which document says so?
7. What folder should be uploaded to EBRAINS for the active prepared job?
8. What exact JobManager command should be used?
9. What should never be uploaded to EBRAINS?
10. How should returned JobManager files be ingested?
11. What docs must be updated after a hardware pass?
12. What docs must be updated after a hardware fail?
13. What does `prepared` mean?
14. What does `hardware_pass` mean?
15. What is the difference between chunked host learning, PyNN/sPyNNaker
    hardware transfer, and custom native runtime evidence?
16. Why is CRA not a transformer/backprop project?
17. What would trigger baseline freeze?
18. What validation command must run before completion?

A capable agent should answer with file references and claim boundaries. If it
answers vaguely, guesses, or invents commands, do not let it proceed.

### 25.2 Practical Dry-Run Test

Before real work, give the agent a fake scenario and require a plan.

Example:

```text
The operator downloaded 20 files from a failed EBRAINS run. What do you do?
```

Expected answer:

1. Inspect `/Users/james/Downloads`.
2. Identify reports/results/stdout/stderr/zip contents.
3. Classify failure stage before proposing a fix.
4. Use tier-specific ingest if available.
5. Preserve returned artifacts in `controlled_test_output/`.
6. Update EBRAINS runbook/job README if a platform lesson exists.
7. Avoid calling it a science failure until model execution and metric failure
   are confirmed.
8. Run validation after updates.
9. Report exact cause, meaning, nonmeaning, docs updated, validation, and next
   step.

If the agent immediately suggests reuploading random folders, uploading
`controlled_test_output/`, or changing code before reading returned files, it
failed the contract.

### 25.3 Code-Change Dry-Run Test

Before letting a new agent modify architecture or runtime code, ask:

```text
You need to add a new native custom-runtime command. What files and tests do you
touch?
```

Expected answer:

1. C command definitions and handler source.
2. Host controller/opcode mirror.
3. `PROTOCOL_SPEC.md`.
4. Runtime README if status/capability changes.
5. Custom-runtime guide if EBRAINS behavior changes.
6. Host tests for payload, response, reset behavior, and error status.
7. Tier runner or local protocol smoke if needed.
8. Prepared EBRAINS package only after local tests pass.
9. Validation before completion.

If the agent edits only C code and does not update protocol/docs/tests, it
failed the contract.

### 25.4 Research-Claim Dry-Run Test

Before letting a new agent promote a mechanism, ask:

```text
The new mechanism improves average accuracy. Can we freeze it?
```

Expected answer:

Not automatically. The agent must check:

1. Was there a predeclared pass criterion?
2. Did strongest relevant baselines lose?
3. Did sham controls lose?
4. Did ablations remove the benefit?
5. Did multiple seeds pass?
6. Did compact regression pass?
7. Was leakage ruled out?
8. Was the claim bounded correctly?
9. Were docs and baseline locks updated?

If the agent says "yes" based only on a better average metric, it failed the
contract.

### 25.5 Red Flags

Stop and correct the agent if it:

1. Uses chat memory instead of repo documents.
2. Guesses EBRAINS commands.
3. Suggests uploading `controlled_test_output/`.
4. Calls prepared packages hardware evidence.
5. Calls a target/build/import failure a model failure.
6. Treats CRA like a transformer or backprop-trained deep network.
7. Adds multiple mechanisms at once.
8. Promotes a mechanism without sham controls and compact regression.
9. Defers correctness, leakage, or scalability problems without documenting
   re-entry conditions.
10. Fails to update docs after changing code/evidence.
11. Hand-edits generated evidence docs instead of fixing generators.
12. Gives a final answer without validation status.

### 25.6 Passing The Contract Test

An agent passes the contract test only if it can:

1. Locate truth from the correct documents.
2. Preserve claim boundaries.
3. Separate science failures from infrastructure failures.
4. Use the correct upload/ingest workflow.
5. Update docs in the correct order.
6. Keep generated and source artifacts distinct.
7. Explain the current long-term goal without overclaiming current evidence.
8. Run or request the correct validation.

If a future agent cannot pass this test, restrict it to read-only analysis until
it can.

## 26. FAQ, Known Errors, And Lessons-Learned Index

This section is a fast triage guide. It does not replace the detailed runbooks.
When an error matches one of these patterns, use the linked source document and
update it if the current run teaches a new lesson.

### 26.1 FAQ

| Question | Short Answer | Full Source |
| --- | --- | --- |
| Where do I start? | Read this contract, then `README.md`, then the active roadmap/test-plan sections. | Sections 3, 3.1, 21 |
| What is the active tier order? | The master execution plan controls the operational next step; the roadmap controls strategy. File names do not. | `docs/MASTER_EXECUTION_PLAN.md`, `docs/PAPER_READINESS_ROADMAP.md`, Section 3.2 |
| What is proven versus planned? | Check canonical evidence and baseline locks; planned work must stay labeled as hypothesis/scaffold/prototype. | `STUDY_EVIDENCE_INDEX.md`, `baselines/`, Sections 2.8 and 5 |
| What do I upload to EBRAINS? | Only the specific clean `ebrains_jobs/cra_*` folder for the prepared job. | `ebrains_jobs/README.md`, Section 9.1 |
| What should never be uploaded to EBRAINS? | Never upload `controlled_test_output/`, Downloads, caches, or the whole repo. | Section 9.1 |
| How do I run the EBRAINS job? | Use the exact direct JobManager command from the prepared report or job README. | `ebrains_jobs/README.md`, `docs/SPINNAKER_EBRAINS_RUNBOOK.md` |
| How do I ingest returned files? | Inspect Downloads, classify failure/pass stage, then use tier-specific ingest into `controlled_test_output/`. | Section 9.4 |
| Is a prepared package hardware evidence? | No. Prepared means source/package readiness only. | Sections 5 and 9 |
| Is a one-seed hardware pass repeatability? | No. It is feasibility unless the tier explicitly only claims one-seed smoke. | Sections 5, 9, 16 |
| Is chunked host learning full on-chip learning? | No. It is hardware bridge/transfer evidence only. | Sections 10 and 2.6 |
| Is CRA trained with backprop? | Mainline CRA claims are not backprop/gradient-loss claims. Backprop systems are baselines only unless a tier says otherwise. | Section 2.7 |
| When do we freeze a baseline? | Only after promotion/sham/ablation/baseline comparison/compact regression gates pass. | Sections 7 and 8 |
| What if a result is promising but controls are ambiguous? | Do not promote. Add sharper controls or narrow the claim. | Sections 2.2 and 7 |
| Where do platform lessons go? | EBRAINS lessons go in the EBRAINS runbook; custom runtime lessons also go in the custom-runtime guide/protocol docs. | Sections 9.4 and 13.1 |

### 26.2 Error Triage Index

| Symptom | Likely Category | First Files To Inspect | First Docs To Check |
| --- | --- | --- | --- |
| JobManager says script/path not found. | Upload folder or command path error. | Returned stdout/stderr, job README, upload folder contents. | `ebrains_jobs/README.md`, `docs/SPINNAKER_EBRAINS_RUNBOOK.md` |
| Python import fails on EBRAINS. | Source package/upload packaging error. | traceback, uploaded folder tree, runner import lines. | `experiments/README.md`, runbook |
| `pyNN.spiNNaker` exists but no target is visible. | Target allocation/preflight visibility issue. | target-check logs, runner hardware status JSON. | EBRAINS runbook |
| `hardware_target_configured=false`. | Environment/target detection or runner preflight issue. | results JSON, target logs, traceback. | EBRAINS runbook |
| `.aplx` build fails. | Custom runtime build/toolchain/source issue. | build stdout/stderr, linker map if present. | custom-runtime guide, runtime README |
| `region ITCM overflowed`. | Custom runtime image size/resource issue. | linker stderr, Makefile profile, object/source list. | custom-runtime guide, runtime README, Section 11 |
| Missing C symbol or callback enum mismatch. | SpiNNaker API/header mismatch. | build stderr, included headers, source enum names. | custom-runtime guide, official/local headers |
| Board load fails. | Hardware load, binary, target, or path issue. | load logs, `.aplx` path, board metadata. | EBRAINS runbook, custom-runtime guide |
| SDP command times out. | Protocol, core selection, load/run state, or response mismatch. | command logs, protocol response bytes, state readback. | `PROTOCOL_SPEC.md`, custom-runtime guide |
| State/readback schema mismatch. | Host/controller/protocol version mismatch. | raw bytes, unpacking code, protocol docs. | `PROTOCOL_SPEC.md` |
| `sim.run` fails. | PyNN/sPyNNaker runtime/network issue. | traceback, backend diagnostics, spike/readback logs. | EBRAINS runbook, experiment report |
| Summary-read failure. | Readback or artifact extraction issue. | summary JSON, readback logs, traceback. | EBRAINS runbook |
| Metrics fail but run executed. | Science/model/task failure. | results JSON, CSV, traces, task reports. | controlled test plan, roadmap |
| Shuffled/wrong-key controls also pass. | Leakage or nonspecific mechanism. | control metrics, task generation, labels/keys. | reviewer-defense plan, Sections 2.2 and 7 |
| Generated audit fails. | Documentation/evidence consistency issue. | audit JSON/MD, registry JSON/CSV. | `experiments/repo_audit.py`, evidence schema |
| Paper table missing row. | Registry/generator issue. | `experiments/evidence_registry.py`, output registry. | evidence schema |
| README says one thing, roadmap says another. | Stale docs. | both docs, latest baseline/evidence. | Documentation SOP Section 13.1 |
| Prepared report says one tier but README filename/title says another. | Copied package metadata / prepared package QA issue. | runner `prepare_bundle`, prepared report, job README, stable `ebrains_jobs/cra_*` folder. | Sections 9.1.1 and 13.1 |
| Two similar `cra_*` folders exist. | Stale upload-folder ambiguity. | `ebrains_jobs/`, prepared report `stable_upload_folder`, job README command. | Sections 9.1 and 9.1.1 |

### 26.3 Lessons Learned That Must Not Be Forgotten

1. EBRAINS upload folders must be clean and specific. Uploading the full repo or
   generated evidence is wrong.
2. The JobManager command is the direct uploaded script path plus arguments,
   unless the prepared job README explicitly says otherwise.
3. If source changes after a failed EBRAINS run, create a fresh upload folder
   name. EBRAINS/JobManager does not allow reuploading the same folder name
   more than once; attempting to do so silently uses stale cached source or
   fails. Increment the suffix (e.g. `cra_423` → `cra_423a` → `cra_423b`).
4. Read returned files before proposing a fix. The first visible error is often
   not the root cause.
5. Target-check/preflight visibility failures are not automatically CRA science
   failures.
6. `.aplx` build failures are not model failures. Preserve stderr and classify
   build/toolchain/resource cause.
7. ITCM/DTCM/resource issues require real runtime-profile or data-structure
   fixes, not hidden claim changes.
8. Tiny custom-runtime primitive passes are valuable but are not full CRA
   transfer.
9. Hardware bridge/chunked evidence is valuable but is not fully continuous
   on-chip learning.
10. One good seed is not repeatability.
11. A mechanism that sounds biologically right still needs sham controls.
12. If sham controls pass too, the mechanism is not causally isolated.
13. Do not hand-edit generated evidence outputs to make the repo look clean.
14. Every platform mistake that cost time belongs in the runbook.
15. A partial EBRAINS return with host-test stdout and an `.elf` but no
    tier-specific `*_results.json` is not a pass and not a science failure.
    Preserve the partial artifacts, harden the runner if it failed before
    structured finalization, and rerun the clean `ebrains_jobs/cra_*` package.
16. A prepared EBRAINS package is not ready to hand off until report, manifest,
    stable folder, generated upload bundle, job README filename/title, and
    command all agree.
17. Similar names are dangerous. `cra_422x` and Tier `4.22x` are not the same
    thing unless the prepared report says so.
18. When a package README filename is copied from a previous tier, fix the runner
    and regenerate the package before handoff.
19. After a hardware pass is ingested, perform a stale-status sweep across
    `codebasecontract.md`, `docs/MASTER_EXECUTION_PLAN.md`,
    `docs/PAPER_READINESS_ROADMAP.md`, `CONTROLLED_TEST_PLAN.md`,
    `docs/CODEBASE_MAP.md`, `experiments/README.md`, `README.md`, and
    `STUDY_EVIDENCE_INDEX.md`. The top-level status being correct is not enough.
20. When documenting criteria counts, distinguish remote runner criteria from
    ingest criteria so later reviewers can reconcile reports and JSON exactly.

21. MCPL/multicast is the target inter-core data plane for scalable native
    runtime work. SDP may be used for host control, readback, diagnostics, and
    transitional scaffolds, but do not describe SDP core-to-core traffic as the
    final scaling architecture.
22. An EBRAINS upload bundle must include **every transitive Python import**,
    not just the direct runner script. If the runner imports module A, and
    module A imports module B, both A and B must be in the bundle. Verify this
    with a dry-run import from the bundle path before every upload.
23. Upload package names must match the tier they represent. Tier 4.23 gets
    `cra_423` (or `cra_423a`, `cra_423b` after failures), not an incremental
    continuation of the 4.22 letter series like `cra_422ai`. Naming discipline
    prevents stale-cache confusion and makes evidence indexing unambiguous.
24. When a runner inherits hardware acquisition or other base-module logic, the
    argument parser must expose **every argument that the base module reads from
    the Namespace**. A missing parser argument causes `AttributeError` at runtime
    on EBRAINS. The failure is invisible in local testing because local mode does
    not call the hardware path. Before uploading, trace every `args.<name>`
    access in every imported base module and ensure the runner's parser defines
    it.
25. A timer-driven continuous event loop on SpiNNaker must treat schedule entry
    timesteps as **relative to when continuous mode starts**, not as absolute
    chip-boot timesteps. The SpiNNaker timer increments from boot; by the time
    the host finishes reset, state writes, and schedule upload, `g_timestep` may
    already be in the thousands. Absolute schedule entries at timestep 1-48 will
    never fire. The runtime must record `g_timestep` at `run_continuous` and
    offset every schedule comparison by that base. Host tests must validate this
    behavior because local test mocks do not experience real timer drift.
26. Do not run two C-runtime build/test/package commands in parallel. Targets
    such as `clean-host`, `test-lifecycle`, `test-profiles`, and EBRAINS
    prepare modes share `spinnaker_runtime/tests/*` binaries and `build/`
    outputs. Parallel execution can delete a freshly built test binary and
    create a false infrastructure failure. Run Python validation in parallel
    with read-only checks if useful, but serialize all commands that invoke
    `make -C coral_reef_spinnaker/spinnaker_runtime ...`.
27. Ingesting returned JobManager artifacts from `Downloads` must not copy the
    whole Downloads directory. Use the tier-specific ingest path and preserve
    only the returned job artifact set, either from a clean returned-output
    folder or from a bounded artifact-selection rule around the tier result
    anchor. A clean hardware pass should not become a public-repo clutter bomb.

### 26.4 Where To Add New Lessons

| Lesson Type | Add It To |
| --- | --- |
| EBRAINS command/upload/target lesson | `docs/SPINNAKER_EBRAINS_RUNBOOK.md` |
| Custom runtime build/load/protocol lesson | `docs/SPINNAKER_EBRAINS_CUSTOM_RUNTIME_GUIDE.md`, `PROTOCOL_SPEC.md` if protocol changed |
| Evidence classification lesson | `experiments/EVIDENCE_SCHEMA.md`, this contract if general |
| Mechanism/control/statistics lesson | `docs/REVIEWER_DEFENSE_PLAN.md`, `CONTROLLED_TEST_PLAN.md` |
| Roadmap/order lesson | `docs/PAPER_READINESS_ROADMAP.md` |
| Source/generated artifact lesson | `ARTIFACTS.md` |
| Common future-agent mistake | This contract, especially Sections 20, 25, or 26 |

If a mistake happens twice, it deserves a rule, not a memory.

## 27. Paste-Ready Handoff Prompt And First-Task Protocol

Use this section when handing the repo to another automated maintainer. The goal is to force
the agent to load the operating contract, route questions through repo docs, and
prove it understands the evidence discipline before it changes anything.

### 27.1 Paste-Ready Handoff Prompt

Paste this into a new agent session before asking for work:

```text
You are working in the CRA repository at /Users/james/JKS:CRA.

Before touching code, read codebasecontract.md. Treat it as mandatory operating
policy. Then read README.md, docs/PAPER_READINESS_ROADMAP.md, CONTROLLED_TEST_PLAN.md,
docs/CODEBASE_MAP.md, and any specific runbook/protocol docs relevant to the task.

Do not guess EBRAINS commands. Do not upload or require controlled_test_output/.
Do not treat prepared packages as hardware evidence. Do not treat CRA like a
transformer/backprop project. Preserve failures. Update docs and validation
exactly as the contract requires.

First, summarize:
1. current repo state,
2. current frozen baseline,
3. active roadmap step,
4. what files you consulted,
5. what you believe the next task is,
6. what you will not claim.

Then proceed only with the smallest auditable step.
```

### 27.2 First 30 Minutes Protocol

A new agent should spend its first working block doing orientation, not editing.

Required first actions:

1. Confirm repo root.
2. Read `codebasecontract.md`.
3. Read `README.md` start-here/current status.
4. Read current roadmap section.
5. Read current controlled test-plan section.
6. If EBRAINS/hardware is involved, read the EBRAINS runbook and active job
   README.
7. If custom runtime is involved, read `PROTOCOL_SPEC.md`, runtime README, and
   custom-runtime guide.
8. Check whether `/Users/james/Downloads` contains newly returned files only if
   the operator says it does.
9. Produce a short orientation summary before making changes.

If the agent starts editing before this orientation, it is not following the
contract.

### 27.3 First Response Shape For A New Agent

The first useful response should look like this:

```text
Repo root:
Files consulted:
Current baseline:
Current active tier:
Current evidence status:
Current claim boundary:
Next smallest auditable step:
Validation expected:
Risks / unknowns:
```

This lets the operator catch misorientation immediately.

### 27.4 Task-Type Operating Modes

Before acting, choose the mode:

| Mode | Use When | First Move |
| --- | --- | --- |
| `orientation` | New session, unclear task, roadmap question. | Read contract, README, roadmap, test plan. |
| `ingest` | User downloaded JobManager/results files. | Inspect Downloads and classify returned artifacts. |
| `diagnosis` | Something failed or results are surprising. | Preserve artifacts and identify failure stage. |
| `repair` | Failure mode is known. | Make smallest fix and local/preflight test. |
| `mechanism` | Adding/testing new CRA capability. | Fill tier design template and predeclare controls. |
| `hardware` | Preparing/running EBRAINS/SpiNNaker. | Use prepared folder and exact job README command. |
| `custom_runtime` | Changing C runtime/protocol. | Update C, host controller, protocol, tests together. |
| `documentation` | Updating docs/roadmap/contract. | Use Documentation Update SOP. |
| `freeze` | Promotion/regression gate passed. | Create baseline lock and update generated evidence. |

If the mode is wrong, the work will probably be wrong.

### 27.5 Definition Of Done By Task Type

| Task Type | Done Means |
| --- | --- |
| Documentation-only | Correct docs updated, no stale cross-reference, validation/audit pass. |
| Local experiment | Artifacts preserved, criteria reported, docs updated if status changed, validation pass. |
| Failed run diagnosis | Exact failure stage identified, artifacts ingested/preserved, meaning/nonmeaning stated, next repair clear. |
| EBRAINS hardware pass | Returned files ingested, criteria checked, runbook/job README updated, claim boundary stated, validation pass. |
| EBRAINS hardware fail | Returned files ingested, failure stage classified, platform lesson documented, no science overclaim. |
| New mechanism | Controls/ablations/baselines/regression passed before promotion; otherwise parked or repaired. |
| Baseline freeze | Baseline lock created, roadmap/test plan/README updated, generated docs refreshed, validation pass. |
| Custom runtime change | Protocol/source/controller/tests/docs updated together, host tests and validation pass. |

Do not call a task done if its task-type definition is not satisfied.
