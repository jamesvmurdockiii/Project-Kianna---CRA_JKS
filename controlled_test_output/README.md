# Controlled Test Output Registry

This directory is generated evidence, not source code. The canonical study
ledger is `STUDY_REGISTRY.json`; the compact table is `STUDY_REGISTRY.csv`.
Older reruns, prepared capsules, debug probes, and baseline-frozen
mechanism bundles outside the formal registry are preserved for audit.

- Generated: `2026-05-08T18:43:47.205987+00:00`
- Registry status: **PASS**
- Canonical evidence entries: `81`
- Expanded test-entry count: `81`; see the canonical evidence table below for the exact current tier list.

## Evidence Categories

- Canonical registry evidence: rows in this registry and the paper-facing table.
- Baseline-frozen mechanism evidence: passed mechanism/promotion diagnostics with compact regression and a frozen `baselines/CRA_EVIDENCE_BASELINE_vX.Y.*` lock, even when the source bundle is not a canonical registry row.
- Noncanonical diagnostic evidence: useful pass/fail diagnostics that answer a design question but do not freeze a baseline by themselves.
- Failed/parked diagnostic evidence: clean negative evidence retained to prevent p-hacking and explain why a mechanism was not promoted.
- Hardware prepare/probe evidence: run packages and one-off probes that are not hardware claims until reviewed and promoted.

## Canonical Evidence

| Entry | Status | Canonical Directory | Claim Boundary |
| --- | --- | --- | --- |
| `tier1_sanity` | **PASS** | `controlled_test_output/tier1_20260426_155758` | Passing Tier 1 rules out obvious fake learning; it does not prove positive learning. |
| `tier2_learning` | **PASS** | `controlled_test_output/tier2_20260426_155821` | Positive-control learning evidence depends on the controlled synthetic task definitions. |
| `tier3_architecture` | **PASS** | `controlled_test_output/tier3_20260426_155852` | Ablation claims are scoped to the controlled tasks and seeds in this bundle. |
| `tier4_10_population_scaling` | **PASS** | `controlled_test_output/tier4_20260426_155103` | This baseline scaling task saturated; the honest claim is stability, not strong scaling advantage. |
| `tier4_10b_hard_population_scaling` | **PASS** | `controlled_test_output/tier4_10b_20260426_161251` | Hard-scaling accuracy is near baseline; the pass is based on stability plus non-accuracy scaling signals. |
| `tier4_11_domain_transfer` | **PASS** | `controlled_test_output/tier4_11_20260426_164655` | Domain transfer is proven for the controlled adapters here, not arbitrary domains. |
| `tier4_12_backend_parity` | **PASS** | `controlled_test_output/tier4_12_20260426_170808` | The SpiNNaker item in Tier 4.12 is readiness prep, not a hardware learning result. |
| `tier4_13_spinnaker_hardware_capsule` | **PASS** | `controlled_test_output/tier4_13_20260427_011912_hardware_pass` | Single-seed N=8 fixed-pattern capsule; not full hardware scaling or full CRA hardware deployment. |
| `tier4_14_hardware_runtime_characterization` | **PASS** | `controlled_test_output/tier4_14_20260426_213430` | Derived from the single-seed N=8 Tier 4.13 hardware pass unless rerun in run-hardware mode; not hardware repeatability or scaling evidence. |
| `tier4_15_spinnaker_hardware_multiseed_repeat` | **PASS** | `controlled_test_output/tier4_15_20260427_030501_hardware_pass` | Three-seed N=8 fixed-pattern capsule only; not a harder hardware task, hardware population scaling, or full CRA hardware deployment. |
| `tier5_1_external_baselines` | **PASS** | `controlled_test_output/tier5_1_20260426_232530` | Controlled software comparison only; not hardware evidence, not a claim that CRA wins every task, and not proof against all possible baselines. |
| `tier5_2_learning_curve_sweep` | **PASS** | `controlled_test_output/tier5_2_20260426_234500` | Controlled software learning-curve characterization only; not hardware evidence, not proof that CRA cannot improve under other tasks/tuning, and not a claim that Tier 5.1 was invalid. |
| `tier5_3_cra_failure_analysis` | **PASS** | `controlled_test_output/tier5_3_20260427_055629` | Controlled software diagnostic only; not hardware evidence, not final competitiveness evidence, and hard_noisy_switching still trails the best external baseline. |
| `tier5_4_delayed_credit_confirmation` | **PASS** | `controlled_test_output/tier5_4_20260427_065412` | Controlled software confirmation only; not hardware evidence and not a superiority claim because hard_noisy_switching still trails the best external baseline. |
| `tier4_16a_delayed_cue_hardware_repeat` | **PASS** | `controlled_test_output/tier4_16_20260427_184635_delayed_cue_3seed_hardware_pass` | Three-seed N=8 delayed_cue capsule only; not hard_noisy_switching hardware transfer, hardware scaling, on-chip learning, or a full Tier 4.16 pass. |
| `tier4_16b_hard_switch_hardware_repeat` | **PASS** | `controlled_test_output/tier4_16_20260427_230043_hard_noisy_switching_3seed_hardware_pass` | Three-seed N=8 hard_noisy_switching capsule only; close-to-threshold transfer, not hardware scaling, on-chip learning, lifecycle/self-scaling, or external-baseline superiority. |
| `tier4_18a_chunked_runtime_baseline` | **PASS** | `controlled_test_output/tier4_18a_20260428_012822_hardware_pass` | Single-seed N=8 runtime/resource characterization only; not hardware scaling, lifecycle/self-scaling, native on-chip dopamine/eligibility, continuous/custom-C runtime, or external-baseline superiority. |
| `tier4_26_four_core_distributed_smoke` | **PASS** | `controlled_test_output/tier4_26_20260502_pass_ingested` | Single-seed seed-42 smoke on one chip only; not speedup evidence, not multi-chip scaling, not a general multi-core framework, and not full native v2.1 autonomy. |
| `tier4_27a_four_core_characterization` | **PASS** | `controlled_test_output/tier4_27a_20260502_pass_ingested` | Single-seed seed-42 smoke on one chip only; not speedup evidence, not multi-chip scaling, not a general multi-core framework, not full native v2.1 autonomy, and not MCPL/multicast. SDP remains transitional. |
| `tier4_27e_two_core_mcpl_smoke` | **PASS** | `controlled_test_output/tier4_27e_20260502_local_pass` | Local build and wiring validation only. NOT hardware evidence. Router table behavior on actual SpiNNaker chip not yet validated. Multi-state-core (context+route+memory) MCPL routing not yet tested. |
| `tier4_27f_three_core_mcpl_smoke` | **PASS** | `controlled_test_output/tier4_27f_20260502_local_pass` | Local build and wiring validation only. NOT hardware evidence. Actual router table behavior with multiple state cores on a single chip not yet validated. SDP-vs-MCPL comparison not yet performed. |
| `tier4_27g_sdp_vs_mcpl_comparison` | **PASS** | `controlled_test_output/tier4_27g_20260502_local_pass` | Source-code analysis only. NOT hardware timing measurements. NOT router-table hardware validation. NOT multi-chip scaling evidence. |
| `tier4_28a_four_core_mcpl_repeatability` | **PASS** | `controlled_test_output/tier4_28a_20260502_mcpl_hardware_pass_ingested` | Single-chip four-core only; not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer, not continuous host-free operation. Host still required for setup and readback. SDP fallback code remains in source but is not the active data plane for v0.1 baseline. |
| `tier4_28b_delayed_cue_four_core_mcpl` | **PASS** | `controlled_test_output/tier4_28b_20260502_hardware_pass_ingested` | Single-seed probe (seed 42) on one chip only. Not three-seed repeatability, not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer. Host still required for setup and readback. |
| `tier4_28c_delayed_cue_repeatability` | **PASS** | `controlled_test_output/tier4_28c_20260503_hardware_pass_ingested` | Single-chip four-core only. Not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer. Host still required for setup and readback. |
| `tier4_28d_hard_noisy_switching` | **PASS** | `controlled_test_output/tier4_28d_20260503_hardware_pass_ingested` | Single-chip four-core only. Host-pre-written regime context; not autonomous regime detection. Not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer. Host still required for setup and readback. |
| `tier4_28e_failure_envelope_pointA` | **PASS** | `controlled_test_output/tier4_28e_pointA_20260503_hardware_pass_ingested` | Single-chip four-core only. Host-pre-written regime context. Not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer. Point A is one of three probe points (A/B/C) in the failure-envelope report. |
| `tier4_28e_failure_envelope_pointC` | **PASS** | `controlled_test_output/tier4_28e_pointC_20260503_hardware_pass_ingested` | Single-chip four-core only. Host-pre-written regime context. Not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer. Point C is one of three probe points (A/B/C) in the failure-envelope report. |
| `tier4_29a_native_keyed_memory_overcapacity` | **PASS** | `controlled_test_output/tier4_29a_20260503_hardware_pass_ingested` | Single-chip four-core only. Host-pre-written keyed context slots. Schedule-driven (not true continuous generation). Not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer. MAX_SCHEDULE_ENTRIES=512 allows longer task streams but still uses pre-loaded static schedule. |
| `tier5_5_expanded_baselines` | **PASS** | `controlled_test_output/tier5_5_20260427_222736` | Controlled software evidence only; not hardware evidence, not a hyperparameter fairness audit, not a universal superiority claim, and not proof that CRA beats the best external baseline at every horizon. |
| `tier5_6_baseline_hyperparameter_fairness_audit` | **PASS** | `controlled_test_output/tier5_6_20260428_001834` | Controlled software fairness audit only; not hardware evidence, not universal superiority, and not proof that CRA beats the best tuned external baseline at every metric or horizon. |
| `tier5_7_compact_regression` | **PASS** | `controlled_test_output/tier5_7_20260428_005723` | Controlled software regression evidence only; not a new capability claim, not hardware evidence, not lifecycle/self-scaling evidence, and not external-baseline superiority. |
| `tier5_12a_predictive_task_pressure` | **PASS** | `controlled_test_output/tier5_12a_20260429_054052` | Task-validation evidence only; not CRA predictive coding, world modeling, language, planning, hardware prediction, or a v1.8 freeze. |
| `tier5_12c_predictive_context_sham_repair` | **PASS** | `controlled_test_output/tier5_12c_20260429_062256` | Host-side software evidence only; Tier 5.12d provides the separate promotion gate. Not hidden-regime inference, full world modeling, language, planning, hardware prediction, hardware scaling, native on-chip learning, compositionality, or external-baseline superiority. |
| `tier5_12d_predictive_context_compact_regression` | **PASS** | `controlled_test_output/tier5_12d_20260429_070615` | Software-only promotion gate; v1.8 remains bounded to visible predictive-context tasks and is not hidden-regime inference, full world modeling, language, planning, hardware prediction, hardware scaling, native on-chip learning, compositionality, or external-baseline superiority. |
| `tier6_1_lifecycle_self_scaling` | **PASS** | `controlled_test_output/tier6_1_20260428_012109` | Controlled software lifecycle evidence only; growth is cleavage-dominated with one adult birth and zero deaths, so this is not full adult turnover, not sham-control proof, not hardware lifecycle evidence, and not external-baseline superiority. |
| `tier6_3_lifecycle_sham_controls` | **PASS** | `controlled_test_output/tier6_3_20260428_121504` | Controlled software sham-control evidence only; replay/shuffle controls are audit artifacts, not independent learners, and this is not hardware lifecycle evidence, full adult turnover, external-baseline superiority, or compositional/world-model evidence. |
| `tier6_4_circuit_motif_causality` | **PASS** | `controlled_test_output/tier6_4_20260428_144354` | Controlled software motif-causality evidence only; motif-diverse graph is seeded for this suite, motif-label shuffle shows labels alone are not causal, and this is not hardware motif evidence, custom-C/on-chip learning, compositionality, or full world-model evidence. |
| `tier4_29b_native_routing_composition_gate` | **PASS** | `controlled_test_output/tier4_29b_20260503_hardware_pass_ingested` | Native routing/composition hardware evidence only; not speedup evidence, not multi-chip scaling, not a general multi-core framework, not full native v2.1 autonomy, and not true continuous generation. |
| `tier4_29c_native_predictive_binding` | **PASS** | `controlled_test_output/tier4_29c_20260504_pass_ingested` | Native predictive binding hardware evidence only; not speedup evidence, not multi-chip scaling, not full native v2.1 autonomy, not continuous generation, and not general task learning. |
| `tier4_29d_native_self_evaluation` | **PASS** | `controlled_test_output/tier4_29d_20260504_pass_ingested` | Native confidence-gated learning hardware evidence only; not speedup evidence, not multi-chip scaling, not full native v2.1 autonomy, not continuous generation, not dynamic lifecycle, and not external-baseline superiority. |
| `tier4_29e_native_replay_consolidation` | **PASS** | `controlled_test_output/tier4_29e_20260505_pass_ingested` | Native host-scheduled replay/consolidation bridge evidence only; not native on-chip replay buffers, not biological sleep, not speedup evidence, not multi-chip scaling, not full native autonomy, and not external-baseline superiority. |
| `tier4_29f_compact_native_mechanism_regression` | **PASS** | `controlled_test_output/tier4_29f_20260505_native_mechanism_regression` | Evidence-regression gate over already-ingested real hardware passes; not a new hardware execution, not a single monolithic all-mechanism task, not lifecycle/self-scaling evidence, not multi-chip scaling, and not speedup evidence. |
| `tier7_0_standard_dynamical_benchmarks` | **PASS** | `controlled_test_output/tier7_0_20260505_standard_dynamical_benchmarks` | Software diagnostic evidence only; not hardware evidence, not a superiority claim, not a tuning run, not a new baseline freeze, and not evidence that CRA is generally weak outside these continuous-regression benchmarks. It triggers Tier 7.0b failure analysis before mechanism changes or hardware migration. |
| `tier7_0b_continuous_regression_failure_analysis` | **PASS** | `controlled_test_output/tier7_0b_20260505_continuous_regression_failure_analysis` | Software diagnostic evidence only; not a tuning run, not a promoted mechanism, not hardware evidence, not a new baseline freeze, and not proof that a repaired CRA will beat standard baselines. It authorizes a bounded continuous readout/interface repair tier before hardware migration. |
| `tier7_0c_continuous_readout_repair` | **PASS** | `controlled_test_output/tier7_0c_20260505_continuous_readout_repair` | Software repair-candidate evidence only; not hardware evidence, not a new baseline freeze, not a promoted CRA mechanism, and not a superiority claim. The correct next move is a stricter state-specific repair or claim narrowing, not hardware migration. |
| `tier7_0d_state_specific_continuous_interface` | **PASS** | `controlled_test_output/tier7_0d_20260505_state_specific_continuous_interface` | Software diagnostic evidence only; not hardware evidence, not a baseline freeze, not a promoted continuous-readout mechanism, and not a superiority claim. The Tier 7 continuous-regression benchmark path should be narrowed and not migrated to hardware unless a future mechanism changes the failure class. |
| `tier5_19a_temporal_substrate_reference` | **PASS** | `controlled_test_output/tier5_19a_20260505_temporal_substrate_reference` | Software local-reference evidence only; recurrence-specific value, hardware transfer, and benchmark superiority remain unproven. |
| `tier5_19b_temporal_substrate_gate` | **PASS** | `controlled_test_output/tier5_19b_20260505_temporal_substrate_gate` | Software diagnostic evidence only; does not freeze a baseline or prove native/on-chip temporal dynamics. |
| `tier5_19c_fading_memory_regression` | **PASS** | `controlled_test_output/tier5_19c_20260505_fading_memory_regression` | Software evidence only; not bounded nonlinear recurrence, native/on-chip temporal dynamics, universal benchmark superiority, language, planning, AGI, or ASI. |
| `tier4_30_readiness_lifecycle_native_audit` | **PASS** | `controlled_test_output/tier4_30_readiness_20260505_lifecycle_native_audit` | Engineering audit only; not lifecycle implementation, not hardware evidence, not speedup, not multi-chip scaling, and not native v2.2 temporal migration. |
| `tier4_30_lifecycle_native_contract` | **PASS** | `controlled_test_output/tier4_30_20260505_lifecycle_native_contract` | Local engineering contract only; not runtime implementation, not hardware evidence, not lifecycle/self-scaling proof, and not v2.2 temporal migration. |
| `tier4_30a_static_pool_lifecycle_reference` | **PASS** | `controlled_test_output/tier4_30a_20260505_static_pool_lifecycle_reference` | Local deterministic reference only; not runtime C, not hardware evidence, not task benefit, not lifecycle baseline freeze, and not v2.2 temporal-state migration. |
| `tier4_30b_lifecycle_runtime_source_audit` | **PASS** | `controlled_test_output/tier4_30b_20260505_lifecycle_source_audit` | Local source/runtime host evidence only; not hardware evidence, not task-effect evidence, not multi-core lifecycle migration, and not a baseline freeze. |
| `tier4_30b_hw_lifecycle_smoke` | **PASS** | `controlled_test_output/tier4_30b_hw_20260505_hardware_pass_ingested` | Hardware smoke only; not lifecycle task benefit, not multi-core lifecycle migration, not speedup, not multi-chip scaling, and not a lifecycle baseline freeze. |
| `tier4_30c_multicore_lifecycle_split` | **PASS** | `controlled_test_output/tier4_30c_20260505_multicore_lifecycle_split` | Local contract/reference evidence only; not C runtime implementation, not EBRAINS hardware evidence, not lifecycle task benefit, and not a lifecycle baseline freeze. |
| `tier4_30d_lifecycle_runtime_source_audit` | **PASS** | `controlled_test_output/tier4_30d_20260505_lifecycle_runtime_source_audit` | Local source/runtime host evidence only; not EBRAINS hardware evidence, not task benefit, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not a lifecycle baseline freeze. |
| `tier4_30e_multicore_lifecycle_hardware_smoke` | **PASS** | `controlled_test_output/tier4_30e_hw_20260505_hardware_pass_ingested` | Hardware smoke only; not lifecycle task benefit, not lifecycle sham-control success, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not a lifecycle baseline freeze. |
| `tier4_30f_lifecycle_sham_hardware_subset` | **PASS** | `controlled_test_output/tier4_30f_hw_20260505_hardware_pass_ingested` | Hardware sham-control subset only; not lifecycle task benefit, not autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not a lifecycle baseline freeze. |
| `tier4_30g_lifecycle_task_benefit_resource_bridge` | **PASS** | `controlled_test_output/tier4_30g_20260506_lifecycle_task_benefit_resource_bridge` | Local contract/reference evidence only; not a hardware task-benefit pass, not autonomous lifecycle-to-learning MCPL, not multi-chip scaling, and not a lifecycle baseline freeze. |
| `tier4_30g_lifecycle_task_benefit_hardware_bridge` | **PASS** | `controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested` | Hardware task-benefit/resource bridge only; host ferries the lifecycle gate into the task path. Not autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not full organism autonomy. |
| `tier4_31a_native_temporal_substrate_readiness` | **PASS** | `controlled_test_output/tier4_31a_20260506_native_temporal_substrate_readiness` | Local readiness/contract evidence only; not C runtime implementation, not SpiNNaker hardware evidence, not speedup, not multi-chip scaling, not nonlinear recurrence, not universal benchmark superiority, and not a new baseline freeze. |
| `tier4_31b_native_temporal_fixed_point_reference` | **PASS** | `controlled_test_output/tier4_31b_20260506_native_temporal_fixed_point_reference` | Local fixed-point reference/parity evidence only; not C runtime implementation, not SpiNNaker hardware evidence, not speedup, not multi-chip scaling, not nonlinear recurrence, not universal benchmark superiority, and not a new baseline freeze. |
| `tier4_31c_native_temporal_runtime_source_audit` | **PASS** | `controlled_test_output/tier4_31c_20260506_native_temporal_runtime_source_audit` | Local source/runtime host evidence only; not SpiNNaker hardware evidence, not speedup, not multi-chip scaling, not nonlinear recurrence, not native replay/sleep, not native macro eligibility, not universal benchmark superiority, and not a new baseline freeze. |
| `tier4_31d_native_temporal_hardware_smoke` | **PASS** | `controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested` | One-board hardware smoke only; not repeatability, not speedup, not benchmark superiority, not multi-chip scaling, not nonlinear recurrence, not native replay/sleep, not native macro eligibility, not full v2.2 hardware transfer, and not a baseline freeze. |
| `tier4_31e_native_replay_eligibility_decision_closeout` | **PASS** | `controlled_test_output/tier4_31e_20260506_native_replay_eligibility_decision_closeout` | Local documentation/decision evidence only; not a hardware run, not a new mechanism implementation, not speedup, not multi-chip scaling, not native replay/sleep proof, not native eligibility proof, not full v2.2 hardware transfer, and not a baseline freeze. |
| `tier4_32_native_runtime_mapping_resource_model` | **PASS** | `controlled_test_output/tier4_32_20260506_mapping_resource_model` | Local resource/mapping model only; not a new hardware run, not speedup evidence, not multi-chip scaling, not benchmark superiority, not full organism autonomy, and not a baseline freeze. |
| `tier4_32a_single_chip_scale_stress_preflight` | **PASS** | `controlled_test_output/tier4_32a_20260506_single_chip_scale_stress` | Local preflight/source-inspection evidence only; not a SpiNNaker hardware run, not speedup evidence, not replicated-shard scaling, not multi-chip scaling, not static reef partition proof, not benchmark superiority, and not a baseline freeze. |
| `tier4_32a_r0_protocol_truth_audit` | **PASS** | `controlled_test_output/tier4_32a_r0_20260506_protocol_truth_audit` | Local source/documentation audit only; not SpiNNaker hardware evidence, not speedup evidence, not multi-chip scaling, not static reef partition proof, and not a baseline freeze. |
| `tier4_32a_r1_mcpl_lookup_repair` | **PASS** | `controlled_test_output/tier4_32a_r1_20260506_mcpl_lookup_repair` | Local source/runtime evidence only; not SpiNNaker hardware evidence, not speedup evidence, not replicated-shard scaling, not multi-chip scaling, not static reef partitioning, and not a baseline freeze. |
| `tier4_32a_hw_replicated_shard_stress` | **PASS** | `controlled_test_output/tier4_32a_hw_replicated_20260507_hardware_pass_ingested` | Single-chip replicated-shard hardware stress only; not multi-chip evidence, not speedup evidence, not static reef partitioning, not benchmark superiority, and not a native-scale baseline freeze by itself. |
| `tier4_32b_static_reef_partition_smoke` | **PASS** | `controlled_test_output/tier4_32b_20260507_static_reef_partition_smoke` | Local static partition/resource evidence only; not a new SpiNNaker hardware run, not speedup evidence, not one-polyp-one-chip evidence, not multi-chip evidence, not benchmark superiority, and not a native-scale baseline freeze. |
| `tier4_32c_interchip_feasibility_contract` | **PASS** | `controlled_test_output/tier4_32c_20260507_interchip_feasibility_contract` | Local contract evidence only; not SpiNNaker hardware evidence, not multi-chip execution evidence, not true two-partition cross-chip learning evidence, not speedup evidence, not learning-scale evidence, not benchmark superiority, and not a native-scale baseline freeze. |
| `tier4_32d_r0_interchip_route_source_audit` | **PASS** | `controlled_test_output/tier4_32d_r0_20260507_interchip_route_source_audit` | Local audit evidence only; not SpiNNaker hardware evidence, not an EBRAINS package, not multi-chip execution evidence, not speedup evidence, not learning-scale evidence, not benchmark superiority, and not a native-scale baseline freeze. |
| `tier4_32d_r1_interchip_route_repair_local_qa` | **PASS** | `controlled_test_output/tier4_32d_r1_20260507_interchip_route_repair_local_qa` | Local source/runtime QA only; not SpiNNaker hardware evidence, not an EBRAINS package, not multi-chip execution evidence, not learning-scale evidence, not speedup evidence, not benchmark superiority, and not a native-scale baseline freeze. |
| `tier4_32d_two_chip_mcpl_lookup_hardware_smoke` | **PASS** | `controlled_test_output/tier4_32d_20260507_hardware_pass_ingested` | Two-chip communication/readback hardware smoke only; not learning-scale evidence, not speedup evidence, not benchmark superiority, not true two-partition cross-chip learning, not lifecycle scaling, not multi-shard learning, and not a native-scale baseline freeze. |
| `tier4_32e_multi_chip_learning_microtask` | **PASS** | `controlled_test_output/tier4_32e_20260507_hardware_pass_ingested` | Two-chip single-shard learning micro-task only; not speedup evidence, not benchmark superiority, not true two-partition cross-chip learning, not lifecycle scaling, not multi-shard learning, and not a native-scale baseline freeze. |
| `tier4_32f_multichip_resource_lifecycle_decision` | **PASS** | `controlled_test_output/tier4_32f_20260507_multichip_resource_lifecycle_decision` | Local decision/contract evidence only; not hardware evidence, not lifecycle scaling, not speedup evidence, not benchmark superiority, not true two-partition learning, not multi-shard learning, and not a native-scale baseline freeze. |
| `tier4_32g_r0_multichip_lifecycle_route_source_audit` | **PASS** | `controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit` | Local source/runtime QA only; not SpiNNaker hardware evidence, not lifecycle scaling, not speedup evidence, not benchmark superiority, not true two-partition learning, not multi-shard learning, and not a native-scale baseline freeze. |
| `tier4_32g_two_chip_lifecycle_traffic_resource_smoke` | **PASS** | `controlled_test_output/tier4_32g_20260508_hardware_pass_ingested` | Two-chip lifecycle traffic/resource smoke only; not lifecycle scaling, not speedup evidence, not benchmark superiority, not true partitioned ecology, not multi-shard learning, and not a native-scale baseline freeze by itself. |
| `tier4_32h_native_scale_evidence_closeout` | **PASS** | `controlled_test_output/tier4_32h_20260508_native_scale_evidence_closeout` | Local evidence closeout only; not a new hardware run, not speedup evidence, not benchmark evidence, not real-task usefulness, not true two-partition learning, not lifecycle scaling, not multi-shard learning, and not AGI/ASI evidence. |

## Noncanonical Outputs

These are retained for audit/debug history. Some source bundles also back
baseline-frozen mechanism claims through `baselines/`; otherwise, do not
cite them as current study results unless promoted in `STUDY_REGISTRY.json`.

| Path | Role | Status | Generated |
| --- | --- | --- | --- |
| `controlled_test_output/_legacy_artifacts` | `legacy_generated_artifacts` | `unknown` | `None` |
| `controlled_test_output/_phase3_probe_ecology` | `probe_or_debug` | `fail` | `2026-04-26T19:26:53+00:00` |
| `controlled_test_output/_phase3_probe_noecology` | `probe_or_debug` | `fail` | `2026-04-26T19:27:15+00:00` |
| `controlled_test_output/_tier5_1_smoke` | `probe_or_debug` | `pass` | `2026-04-27T03:25:15+00:00` |
| `controlled_test_output/_tier5_2_smoke` | `probe_or_debug` | `pass` | `2026-04-27T03:44:52+00:00` |
| `controlled_test_output/_tier5_3_smoke` | `probe_or_debug` | `pass` | `2026-04-27T09:56:20+00:00` |
| `controlled_test_output/_tier5_4_smoke` | `probe_or_debug` | `pass` | `2026-04-27T10:53:59+00:00` |
| `controlled_test_output/test_prepare_debug` | `unclassified` | `unknown` | `None` |
| `controlled_test_output/tier1_20260426_150252` | `superseded_rerun` | `pass` | `2026-04-26T19:03:11+00:00` |
| `controlled_test_output/tier1_20260426_150944` | `superseded_rerun` | `pass` | `2026-04-26T19:10:00+00:00` |
| `controlled_test_output/tier1_20260426_152035` | `superseded_rerun` | `pass` | `2026-04-26T19:20:51+00:00` |
| `controlled_test_output/tier1_20260426_153453` | `superseded_rerun` | `pass` | `2026-04-26T19:35:16+00:00` |
| `controlled_test_output/tier1_20260426_153802` | `superseded_rerun` | `pass` | `2026-04-26T19:38:19+00:00` |
| `controlled_test_output/tier2_20260426_151539` | `superseded_rerun` | `unknown` | `None` |
| `controlled_test_output/tier2_20260426_151558` | `superseded_rerun` | `fail` | `2026-04-26T19:16:08+00:00` |
| `controlled_test_output/tier2_20260426_151659` | `superseded_rerun` | `fail` | `2026-04-26T19:17:08+00:00` |
| `controlled_test_output/tier2_20260426_151740` | `superseded_rerun` | `fail` | `2026-04-26T19:17:54+00:00` |
| `controlled_test_output/tier2_20260426_151847` | `superseded_rerun` | `fail` | `2026-04-26T19:18:52+00:00` |
| `controlled_test_output/tier2_20260426_151923` | `superseded_rerun` | `fail` | `2026-04-26T19:19:37+00:00` |
| `controlled_test_output/tier2_20260426_152011` | `superseded_rerun` | `pass` | `2026-04-26T19:20:25+00:00` |
| `controlled_test_output/tier2_20260426_152616` | `superseded_rerun` | `pass` | `2026-04-26T19:26:26+00:00` |
| `controlled_test_output/tier2_20260426_153522` | `superseded_rerun` | `fail` | `2026-04-26T19:35:42+00:00` |
| `controlled_test_output/tier2_20260426_153749` | `superseded_rerun` | `pass` | `2026-04-26T19:37:54+00:00` |
| `controlled_test_output/tier2_20260426_153824` | `superseded_rerun` | `pass` | `2026-04-26T19:38:40+00:00` |
| `controlled_test_output/tier3_20260426_153145` | `superseded_rerun` | `pass` | `2026-04-26T19:34:10+00:00` |
| `controlled_test_output/tier3_20260426_153850` | `superseded_rerun` | `fail` | `2026-04-26T19:40:42+00:00` |
| `controlled_test_output/tier3_20260426_154155` | `superseded_rerun` | `pass` | `2026-04-26T19:43:50+00:00` |
| `controlled_test_output/tier4_13_20260426_181357` | `superseded_rerun` | `prepared` | `2026-04-26T22:13:57+00:00` |
| `controlled_test_output/tier4_13_20260426_192413` | `superseded_rerun` | `prepared` | `2026-04-26T23:24:13+00:00` |
| `controlled_test_output/tier4_13_20260426_192455` | `superseded_rerun` | `prepared` | `2026-04-26T23:24:55+00:00` |
| `controlled_test_output/tier4_13_20260426_195400` | `superseded_rerun` | `prepared` | `2026-04-26T23:54:00+00:00` |
| `controlled_test_output/tier4_13_20260426_195507` | `superseded_rerun` | `prepared` | `2026-04-26T23:55:07+00:00` |
| `controlled_test_output/tier4_13_20260426_201136` | `superseded_rerun` | `prepared` | `2026-04-27T00:11:36+00:00` |
| `controlled_test_output/tier4_13_20260426_201430` | `superseded_rerun` | `prepared` | `2026-04-27T00:14:30+00:00` |
| `controlled_test_output/tier4_13_20260426_201508` | `superseded_rerun` | `prepared` | `2026-04-27T00:15:08+00:00` |
| `controlled_test_output/tier4_15_20260426_215658` | `superseded_rerun` | `prepared` | `2026-04-27T01:56:58+00:00` |
| `controlled_test_output/tier4_16_20260427_124916_hardware_fail` | `failed_hardware_run` | `fail` | `2026-04-27T13:12:59+00:00` |
| `controlled_test_output/tier4_16_20260427_131914_prepared` | `prepared_capsule` | `prepared` | `2026-04-27T17:19:14+00:00` |
| `controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass` | `hardware_probe_pass` | `pass` | `2026-04-27T17:40:46+00:00` |
| `controlled_test_output/tier4_16_20260427_194526_hard_noisy_switching_3seed_hardware_fail` | `failed_hardware_run` | `fail` | `2026-04-27T19:13:08+00:00` |
| `controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass` | `hardware_probe_pass` | `pass` | `2026-04-27T22:39:50+00:00` |
| `controlled_test_output/tier4_16a_debug_20260427_141912` | `debug_diagnostic` | `pass` | `2026-04-27T14:20:06+00:00` |
| `controlled_test_output/tier4_16a_fix_20260427_143252` | `fix_diagnostic` | `pass` | `2026-04-27T14:53:36+00:00` |
| `controlled_test_output/tier4_16a_fix_brian2_1200_20260427_145800` | `fix_diagnostic` | `pass` | `2026-04-27T15:11:07+00:00` |
| `controlled_test_output/tier4_16a_fix_nest_1200_20260427_145600` | `fix_diagnostic` | `pass` | `2026-04-27T14:58:54+00:00` |
| `controlled_test_output/tier4_16a_fix_nest_length_sweep_20260427_145400` | `fix_diagnostic` | `fail` | `2026-04-27T14:56:41+00:00` |
| `controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_brian2_20260427` | `fix_diagnostic` | `pass` | `2026-04-27T22:09:38+00:00` |
| `controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427` | `fix_diagnostic` | `pass` | `2026-04-27T21:47:01+00:00` |
| `controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch` | `debug_diagnostic` | `pass` | `2026-04-27T20:44:18+00:00` |
| `controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch_corrected` | `debug_diagnostic` | `pass` | `2026-04-27T20:48:54+00:00` |
| `controlled_test_output/tier4_17_20260427_171719_runtime_scaffold` | `runtime_contract_diagnostic` | `prepared` | `2026-04-27T17:17:19.311029+00:00` |
| `controlled_test_output/tier4_17b_20260427_164625_step_chunk_parity` | `runtime_parity_diagnostic` | `pass` | `2026-04-27T16:46:31+00:00` |
| `controlled_test_output/tier4_18a_20260427_203220_prepared` | `prepared_capsule` | `prepared` | `2026-04-28T00:32:20+00:00` |
| `controlled_test_output/tier4_20a_20260429_190239` | `hardware_transfer_readiness_audit` | `pass` | `2026-04-29T23:02:39+00:00` |
| `controlled_test_output/tier4_20a_20260429_190257` | `hardware_transfer_readiness_audit` | `pass` | `2026-04-29T23:02:57+00:00` |
| `controlled_test_output/tier4_20a_20260429_190503` | `hardware_transfer_readiness_audit` | `pass` | `2026-04-29T23:05:03+00:00` |
| `controlled_test_output/tier4_20a_20260429_195403` | `hardware_transfer_readiness_audit` | `pass` | `2026-04-29T23:54:03+00:00` |
| `controlled_test_output/tier4_20b_20260429_205214_prepared` | `v2_1_chunked_hardware_probe` | `prepared` | `2026-04-30T00:52:14+00:00` |
| `controlled_test_output/tier4_20b_20260429_221734_local_preflight` | `v2_1_chunked_hardware_probe` | `pass` | `2026-04-30T02:17:37+00:00` |
| `controlled_test_output/tier4_20b_20260430_empirical_run_no_machine_version_fail` | `v2_1_chunked_hardware_probe` | `unknown` | `None` |
| `controlled_test_output/tier4_20b_20260430_full_run_blocked_by_target_gate` | `v2_1_chunked_hardware_probe` | `unknown` | `None` |
| `controlled_test_output/tier4_20b_20260430_local_preflight_pass` | `v2_1_chunked_hardware_probe` | `pass` | `2026-04-30T02:13:38+00:00` |
| `controlled_test_output/tier4_20b_20260430_no_machine_target_check_fail` | `v2_1_chunked_hardware_probe` | `unknown` | `None` |
| `controlled_test_output/tier4_20b_20260430_no_machine_target_fail` | `v2_1_chunked_hardware_probe` | `unknown` | `None` |
| `controlled_test_output/tier4_20b_20260430_stale_wrapper_source_rerun` | `v2_1_chunked_hardware_probe` | `unknown` | `None` |
| `controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass` | `v2_1_chunked_hardware_probe` | `pass` | `2026-04-30T03:41:16+00:00` |
| `controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass_ingested` | `v2_1_chunked_hardware_probe` | `pass` | `2026-04-30T03:55:05+00:00` |
| `controlled_test_output/tier4_20b_prepare_smoke_after_target_gate_fix` | `fix_diagnostic` | `prepared` | `2026-04-30T02:57:00+00:00` |
| `controlled_test_output/tier4_20b_prepare_smoke_inprocess_no_baseline_required` | `v2_1_chunked_hardware_probe` | `prepared` | `2026-04-30T03:14:34+00:00` |
| `controlled_test_output/tier4_20b_prepare_smoke_inprocess_runner` | `v2_1_chunked_hardware_probe` | `prepared` | `2026-04-30T03:13:20+00:00` |
| `controlled_test_output/tier4_20b_prepare_smoke_revision_stamp` | `v2_1_chunked_hardware_probe` | `prepared` | `2026-04-30T03:24:41+00:00` |
| `controlled_test_output/tier4_20c_20260430_000428_prepared` | `v2_1_three_seed_hardware_repeat` | `prepared` | `2026-04-30T04:04:28+00:00` |
| `controlled_test_output/tier4_20c_20260430_000433_prepared` | `v2_1_three_seed_hardware_repeat` | `prepared` | `2026-04-30T04:04:33+00:00` |
| `controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_hardware_pass_ingested` | `v2_1_three_seed_hardware_repeat` | `pass` | `2026-04-30T04:36:48+00:00` |
| `controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_raw_false_fail` | `v2_1_three_seed_hardware_repeat` | `unknown` | `None` |
| `controlled_test_output/tier4_21a_20260430_keyed_context_memory_seed42_hardware_pass_ingested` | `keyed_context_memory_hardware_bridge` | `pass` | `2026-04-30T17:12:07+00:00` |
| `controlled_test_output/tier4_21a_20260430_prepared` | `keyed_context_memory_hardware_bridge` | `prepared` | `2026-04-30T15:52:15+00:00` |
| `controlled_test_output/tier4_21a_local_bridge_smoke` | `keyed_context_memory_hardware_bridge` | `pass` | `2026-04-30T15:52:04+00:00` |
| `controlled_test_output/tier4_22a0_20260430_spinnaker_constrained_preflight` | `spinnaker_constrained_preflight` | `pass` | `2026-04-30T17:47:50+00:00` |
| `controlled_test_output/tier4_22a_20260430_custom_runtime_contract` | `custom_runtime_contract` | `pass` | `2026-04-30T17:32:07+00:00` |
| `controlled_test_output/tier4_22b_20260430_continuous_transport_hardware_pass_ingested` | `continuous_transport_scaffold` | `pass` | `2026-04-30T18:14:15+00:00` |
| `controlled_test_output/tier4_22b_20260430_continuous_transport_local` | `continuous_transport_scaffold` | `pass` | `2026-04-30T18:08:05+00:00` |
| `controlled_test_output/tier4_22b_20260430_prepared` | `continuous_transport_scaffold` | `prepared` | `2026-04-30T17:59:06+00:00` |
| `controlled_test_output/tier4_22c_20260430_persistent_state_scaffold` | `persistent_custom_c_state_scaffold` | `pass` | `2026-04-30T18:45:11+00:00` |
| `controlled_test_output/tier4_22d_20260430_reward_plasticity_scaffold` | `custom_c_reward_plasticity_scaffold` | `pass` | `2026-04-30T18:45:12+00:00` |
| `controlled_test_output/tier4_22e_20260430_local_learning_parity` | `local_custom_c_learning_parity_scaffold` | `pass` | `2026-04-30T18:45:15+00:00` |
| `controlled_test_output/tier4_22f0_20260430_custom_runtime_scale_audit` | `custom_runtime_scale_readiness_audit` | `pass` | `2026-04-30T19:01:01+00:00` |
| `controlled_test_output/tier4_22g_20260430_event_indexed_trace_runtime` | `event_indexed_active_trace_runtime` | `pass` | `2026-04-30T19:10:43+00:00` |
| `controlled_test_output/tier4_22h_20260430_compact_readback_acceptance` | `compact_readback_build_readiness` | `pass` | `2026-04-30T23:43:56+00:00` |
| `controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared` | `custom_runtime_board_roundtrip` | `prepared` | `2026-04-30T23:44:08+00:00` |
| `controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_fail` | `custom_runtime_board_roundtrip` | `fail` | `2026-04-30T20:26:52+00:00` |
| `controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_pass_target_missing_fail` | `custom_runtime_board_roundtrip` | `fail` | `2026-04-30T22:59:15+00:00` |
| `controlled_test_output/tier4_22i_20260430_ebrains_aplx_load_pass_sdp_payload_short_fail` | `custom_runtime_board_roundtrip` | `fail` | `2026-04-30T23:24:00+00:00` |
| `controlled_test_output/tier4_22i_20260430_ebrains_manual_link_empty_elf_fail` | `custom_runtime_board_roundtrip` | `fail` | `2026-04-30T22:24:42+00:00` |
| `controlled_test_output/tier4_22i_20260430_ebrains_no_mc_event_build_fail` | `custom_runtime_board_roundtrip` | `fail` | `2026-04-30T20:36:25+00:00` |
| `controlled_test_output/tier4_22i_20260430_ebrains_official_mk_nested_object_dir_fail` | `custom_runtime_board_roundtrip` | `fail` | `2026-04-30T22:40:57+00:00` |
| `controlled_test_output/tier4_22i_20260430_ebrains_router_api_build_fail` | `custom_runtime_board_roundtrip` | `fail` | `2026-04-30T22:09:33+00:00` |
| `controlled_test_output/tier4_22i_20260430_ebrains_sdp_struct_build_fail` | `custom_runtime_board_roundtrip` | `fail` | `2026-04-30T21:37:40+00:00` |
| `controlled_test_output/tier4_22i_20260501_ebrains_board_roundtrip_pass` | `custom_runtime_board_roundtrip` | `pass` | `2026-05-01T00:53:20+00:00` |
| `controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested` | `minimal_custom_runtime_learning_smoke` | `pass` | `2026-05-01T01:25:45+00:00` |
| `controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_prepared` | `minimal_custom_runtime_learning_smoke` | `prepared` | `2026-05-01T01:33:03+00:00` |
| `controlled_test_output/tier4_22k_20260430_ebrains_event_symbol_discovery_pass` | `spin1api_event_symbol_discovery` | `pass` | `2026-04-30T21:02:05+00:00` |
| `controlled_test_output/tier4_22k_20260430_spin1api_event_discovery_prepared` | `spin1api_event_symbol_discovery` | `prepared` | `2026-04-30T20:54:08+00:00` |
| `controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_hardware_pass_ingested` | `custom_runtime_learning_parity` | `pass` | `2026-05-01T02:17:11+00:00` |
| `controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_local` | `custom_runtime_learning_parity` | `pass` | `2026-05-01T01:56:01+00:00` |
| `controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared` | `custom_runtime_learning_parity` | `prepared` | `2026-05-01T02:23:48+00:00` |
| `controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_hardware_pass_ingested` | `fixed_pattern_custom_runtime_task_micro_loop` | `pass` | `2026-05-01T02:44:10+00:00` |
| `controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_local` | `fixed_pattern_custom_runtime_task_micro_loop` | `pass` | `2026-05-01T02:41:02+00:00` |
| `controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_prepared` | `fixed_pattern_custom_runtime_task_micro_loop` | `prepared` | `2026-05-01T02:41:02+00:00` |
| `controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested` | `delayed_cue_custom_runtime_micro_task` | `pass` | `2026-05-01T03:03:01+00:00` |
| `controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_local` | `delayed_cue_custom_runtime_micro_task` | `pass` | `2026-05-01T02:57:13+00:00` |
| `controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_prepared` | `delayed_cue_custom_runtime_micro_task` | `prepared` | `2026-05-01T02:57:13+00:00` |
| `controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_overflow_fail_ingested` | `noisy_switching_custom_runtime_micro_task` | `fail` | `2026-05-01T03:20:50+00:00` |
| `controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested` | `noisy_switching_custom_runtime_micro_task` | `pass` | `2026-05-01T03:35:34+00:00` |
| `controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_local` | `noisy_switching_custom_runtime_micro_task` | `pass` | `2026-05-01T03:27:57+00:00` |
| `controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_prepared` | `noisy_switching_custom_runtime_micro_task` | `prepared` | `2026-05-01T03:32:37+00:00` |
| `controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_hardware_pass_ingested` | `aba_reentry_custom_runtime_micro_task` | `pass` | `2026-05-01T04:12:34+00:00` |
| `controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_local` | `aba_reentry_custom_runtime_micro_task` | `pass` | `2026-05-01T03:59:39+00:00` |
| `controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_prepared` | `aba_reentry_custom_runtime_micro_task` | `prepared` | `2026-05-01T03:59:39+00:00` |
| `controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_hardware_pass_ingested` | `integrated_v2_bridge_custom_runtime_smoke` | `pass` | `2026-05-01T06:59:01+00:00` |
| `controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_local` | `integrated_v2_bridge_custom_runtime_smoke` | `pass` | `2026-05-01T04:30:11+00:00` |
| `controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_prepared` | `integrated_v2_bridge_custom_runtime_smoke` | `prepared` | `2026-05-01T06:54:49+00:00` |
| `controlled_test_output/tier4_22r_20260501_native_context_state_smoke_hardware_pass_ingested` | `native_context_state_custom_runtime_smoke` | `pass` | `2026-05-01T07:23:03+00:00` |
| `controlled_test_output/tier4_22r_20260501_native_context_state_smoke_local` | `native_context_state_custom_runtime_smoke` | `pass` | `2026-05-01T07:16:34+00:00` |
| `controlled_test_output/tier4_22r_20260501_native_context_state_smoke_prepared` | `native_context_state_custom_runtime_smoke` | `prepared` | `2026-05-01T07:19:21+00:00` |
| `controlled_test_output/tier4_22s_20260501_native_route_state_smoke_hardware_pass_ingested` | `native_route_state_custom_runtime_smoke` | `pass` | `2026-05-01T07:46:44+00:00` |
| `controlled_test_output/tier4_22s_20260501_native_route_state_smoke_local` | `native_route_state_custom_runtime_smoke` | `pass` | `2026-05-01T07:41:15+00:00` |
| `controlled_test_output/tier4_22s_20260501_native_route_state_smoke_prepared` | `native_route_state_custom_runtime_smoke` | `prepared` | `2026-05-01T07:41:15+00:00` |
| `controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_hardware_pass_ingested` | `native_keyed_route_state_custom_runtime_smoke` | `pass` | `2026-05-01T08:16:19+00:00` |
| `controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_local` | `native_keyed_route_state_custom_runtime_smoke` | `pass` | `2026-05-01T08:05:40+00:00` |
| `controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_prepared` | `native_keyed_route_state_custom_runtime_smoke` | `prepared` | `2026-05-01T08:11:02+00:00` |
| `controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_hardware_pass_ingested` | `native_memory_route_state_custom_runtime_smoke` | `pass` | `2026-05-01T08:40:50+00:00` |
| `controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_local` | `native_memory_route_state_custom_runtime_smoke` | `pass` | `2026-05-01T08:34:13+00:00` |
| `controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_prepared` | `native_memory_route_state_custom_runtime_smoke` | `prepared` | `2026-05-01T08:34:21+00:00` |
| `controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested` | `native_memory_route_reentry_composition_custom_runtime_smoke` | `pass` | `2026-05-01T20:15:13+00:00` |
| `controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_local` | `native_memory_route_reentry_composition_custom_runtime_smoke` | `pass` | `2026-05-01T20:08:23+00:00` |
| `controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_prepared` | `native_memory_route_reentry_composition_custom_runtime_smoke` | `prepared` | `2026-05-01T20:08:38+00:00` |
| `controlled_test_output/tier4_22w_20260501_ebrains_itcm_overflow_fail_ingested` | `native_decoupled_memory_route_composition_custom_runtime_smoke` | `fail` | `2026-05-01T20:40:04+00:00` |
| `controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested` | `native_decoupled_memory_route_composition_custom_runtime_smoke` | `pass` | `2026-05-01T21:14:30+00:00` |
| `controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_local` | `native_decoupled_memory_route_composition_custom_runtime_smoke` | `pass` | `2026-05-01T20:31:55+00:00` |
| `controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_local_profiled` | `native_decoupled_memory_route_composition_custom_runtime_smoke` | `pass` | `2026-05-01T21:03:55+00:00` |
| `controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared` | `native_decoupled_memory_route_composition_custom_runtime_smoke` | `prepared` | `2026-05-01T20:32:16+00:00` |
| `controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared_profiled` | `native_decoupled_memory_route_composition_custom_runtime_smoke` | `prepared` | `2026-05-01T21:03:59+00:00` |
| `controlled_test_output/tier4_22x_20260501_compact_v2_bridge_decoupled_smoke_hardware_pass_ingested` | `hardware_probe_pass` | `pass` | `2026-05-01T22:23:01+00:00` |
| `controlled_test_output/tier4_22x_20260501_compact_v2_bridge_decoupled_smoke_local` | `superseded_rerun` | `pass` | `2026-05-01T22:13:54+00:00` |
| `controlled_test_output/tier4_22x_20260501_compact_v2_bridge_decoupled_smoke_prepared` | `prepared_capsule` | `prepared` | `2026-05-01T22:23:40+00:00` |
| `controlled_test_output/tier4_23a_20260501_continuous_local_reference` | `superseded_rerun` | `pass` | `None` |
| `controlled_test_output/tier4_23c_20260501_hardware_pass_ingested` | `continuous_hardware_smoke` | `pass` | `2026-05-02T01:15:49.141315+00:00` |
| `controlled_test_output/tier4_23c_local_test` | `continuous_hardware_smoke` | `pass` | `2026-05-02T01:11:01.588278+00:00` |
| `controlled_test_output/tier4_23c_prepare_test` | `continuous_hardware_smoke` | `prepared` | `2026-05-02T01:11:01.662879+00:00` |
| `controlled_test_output/tier4_24_20260501_resource_characterization` | `superseded_rerun` | `pass` | `2026-05-02T01:51:35.702561+00:00` |
| `controlled_test_output/tier4_24b_20260502_build_size_capture` | `superseded_rerun` | `unknown` | `2026-05-02T02:34:07.052515+00:00` |
| `controlled_test_output/tier4_24b_20260502_ebrains_build_size_capture` | `superseded_rerun` | `pass` | `2026-05-02T03:31:09.219725+00:00` |
| `controlled_test_output/tier4_25a_20260502_multicore_mapping_analysis` | `superseded_rerun` | `pass` | `2026-05-02T03:34:53.721897+00:00` |
| `controlled_test_output/tier4_25b_20260502_hardware_pass_ingested` | `two_core_state_learning_split_smoke` | `pass` | `2026-05-02T04:55:26.039936+00:00` |
| `controlled_test_output/tier4_25c_20260502_aggregate` | `two_core_state_learning_split_repeatability` | `pass` | `2026-05-02T16:08:27.368696+00:00` |
| `controlled_test_output/tier4_25c_seed42_hardware` | `two_core_state_learning_split_repeatability` | `pass` | `2026-05-02T16:02:32.703012+00:00` |
| `controlled_test_output/tier4_25c_seed42_ingested` | `two_core_state_learning_split_repeatability` | `pass` | `2026-05-02T16:05:35.351400+00:00` |
| `controlled_test_output/tier4_25c_seed42_local` | `two_core_state_learning_split_repeatability` | `unknown` | `2026-05-02T05:28:23.858951+00:00` |
| `controlled_test_output/tier4_25c_seed42_prepared` | `two_core_state_learning_split_repeatability` | `prepared` | `2026-05-02T15:53:02.602124+00:00` |
| `controlled_test_output/tier4_25c_seed43_hardware` | `two_core_state_learning_split_repeatability` | `pass` | `2026-05-02T16:03:33.741548+00:00` |
| `controlled_test_output/tier4_25c_seed43_ingested` | `two_core_state_learning_split_repeatability` | `pass` | `2026-05-02T16:06:41.680207+00:00` |
| `controlled_test_output/tier4_25c_seed44_hardware` | `two_core_state_learning_split_repeatability` | `pass` | `2026-05-02T16:03:43.466421+00:00` |
| `controlled_test_output/tier4_25c_seed44_ingested` | `two_core_state_learning_split_repeatability` | `pass` | `2026-05-02T16:07:28.401854+00:00` |
| `controlled_test_output/tier4_27d_20260502_local_pass` | `superseded_rerun` | `fail` | `2026-05-03T03:11:27.031328+00:00` |
| `controlled_test_output/tier4_28a_20260502_mcpl_seed43_hardware_pass_ingested` | `hardware_probe_pass` | `pass` | `2026-05-03T02:54:06.759459+00:00` |
| `controlled_test_output/tier4_28a_20260502_mcpl_seed44_hardware_pass_ingested` | `hardware_probe_pass` | `pass` | `2026-05-03T02:56:59.683133+00:00` |
| `controlled_test_output/tier4_28b_20260502_local_pass` | `superseded_rerun` | `pass` | `2026-05-03T03:35:53.501756+00:00` |
| `controlled_test_output/tier4_28b_20260502_local_pass_v2` | `superseded_rerun` | `pass` | `2026-05-03T03:45:38.005432+00:00` |
| `controlled_test_output/tier4_28b_20260502_prepared` | `prepared_capsule` | `pass` | `2026-05-03T03:37:34.516235+00:00` |
| `controlled_test_output/tier4_28b_20260502_prepared_v2` | `superseded_rerun` | `pass` | `2026-05-03T03:45:46.656948+00:00` |
| `controlled_test_output/tier4_28c_20260503_local_pass` | `superseded_rerun` | `pass` | `2026-05-03T04:11:53.525394+00:00` |
| `controlled_test_output/tier4_28c_20260503_prepared` | `prepared_capsule` | `pass` | `2026-05-03T04:13:48.915273+00:00` |
| `controlled_test_output/tier4_28e_pointB_20260503_boundary_confirmed` | `failure_envelope_boundary_diagnostic` | `boundary_confirmed` | `2026-05-03T19:29:00.000000+00:00` |
| `controlled_test_output/tier4_29b_20260503_hardware_fail_ingested` | `superseded_rerun` | `fail` | `None` |
| `controlled_test_output/tier4_29e_20260505_0758_local_audit` | `superseded_rerun` | `pass` | `None` |
| `controlled_test_output/tier4_29e_20260505_cra_429o_hardware_fail` | `failed_hardware_run` | `unknown` | `None` |
| `controlled_test_output/tier4_29e_20260505_cra_429p_local_repair` | `superseded_rerun` | `unknown` | `None` |
| `controlled_test_output/tier4_30b_hw_20260505_prepared` | `prepared_capsule` | `prepared` | `2026-05-05T20:39:00+00:00` |
| `controlled_test_output/tier4_30e_hw_20260505_prepared` | `prepared_capsule` | `prepared` | `2026-05-05T22:20:02+00:00` |
| `controlled_test_output/tier4_30f_hw_20260505_prepared` | `prepared_capsule` | `prepared` | `2026-05-06T01:27:19+00:00` |
| `controlled_test_output/tier4_30g_hw_20260506_prepared` | `prepared_capsule` | `prepared` | `2026-05-06T03:09:59+00:00` |
| `controlled_test_output/tier4_31d_hw_20260506_incomplete_return` | `superseded_rerun` | `fail` | `2026-05-06T18:39:35+00:00` |
| `controlled_test_output/tier4_31d_hw_20260506_prepared` | `prepared_capsule` | `prepared` | `2026-05-06T18:50:47+00:00` |
| `controlled_test_output/tier4_32a_hw_20260506_prepared` | `prepared_capsule` | `prepared` | `2026-05-06T23:37:49+00:00` |
| `controlled_test_output/tier4_32a_hw_20260507_hardware_pass_ingested` | `hardware_probe_pass` | `pass` | `2026-05-07T00:28:48+00:00` |
| `controlled_test_output/tier4_32a_hw_replicated_20260507_prepared` | `prepared_capsule` | `prepared` | `2026-05-07T00:45:04+00:00` |
| `controlled_test_output/tier4_32d_20260507_prepared` | `prepared_capsule` | `prepared` | `2026-05-07T03:27:14+00:00` |
| `controlled_test_output/tier4_32e_20260507_prepared` | `prepared_capsule` | `prepared` | `2026-05-07T17:02:16+00:00` |
| `controlled_test_output/tier4_32g_20260507_hardware_fail_ingested` | `superseded_rerun` | `fail` | `2026-05-08T02:59:39+00:00` |
| `controlled_test_output/tier4_32g_20260507_prepared` | `prepared_capsule` | `prepared` | `2026-05-07T20:34:53+00:00` |
| `controlled_test_output/tier4_32g_20260507_r1_prepared` | `prepared_capsule` | `prepared` | `2026-05-08T02:59:50+00:00` |
| `controlled_test_output/tier4_32g_20260508_old_package_return_ingested` | `superseded_rerun` | `fail` | `2026-05-08T03:31:39+00:00` |
| `controlled_test_output/tier4_32g_20260508_r2_prepared` | `prepared_capsule` | `prepared` | `2026-05-08T03:31:50+00:00` |
| `controlled_test_output/tier5_10_20260428_181304` | `superseded_rerun` | `pass` | `2026-04-28T22:13:10+00:00` |
| `controlled_test_output/tier5_10_20260428_181322` | `superseded_rerun` | `fail` | `2026-04-28T22:45:43+00:00` |
| `controlled_test_output/tier5_10b_20260428_193205` | `superseded_rerun` | `fail` | `2026-04-28T23:32:05+00:00` |
| `controlled_test_output/tier5_10b_20260428_193332` | `superseded_rerun` | `fail` | `2026-04-28T23:33:32+00:00` |
| `controlled_test_output/tier5_10b_20260428_193408` | `superseded_rerun` | `pass` | `2026-04-28T23:34:08+00:00` |
| `controlled_test_output/tier5_10b_20260428_193420` | `superseded_rerun` | `pass` | `2026-04-28T23:34:22+00:00` |
| `controlled_test_output/tier5_10b_20260428_193638` | `superseded_rerun` | `pass` | `2026-04-28T23:36:38+00:00` |
| `controlled_test_output/tier5_10b_20260428_193639` | `superseded_rerun` | `pass` | `2026-04-28T23:36:41+00:00` |
| `controlled_test_output/tier5_10c_20260428_201258` | `superseded_rerun` | `pass` | `2026-04-29T00:13:03+00:00` |
| `controlled_test_output/tier5_10c_20260428_201314` | `superseded_rerun` | `pass` | `2026-04-29T00:29:08+00:00` |
| `controlled_test_output/tier5_10d_20260428_212215` | `superseded_rerun` | `pass` | `2026-04-29T01:22:21+00:00` |
| `controlled_test_output/tier5_10d_20260428_212229` | `superseded_rerun` | `pass` | `2026-04-29T01:42:10+00:00` |
| `controlled_test_output/tier5_10e_20260428_220258` | `superseded_rerun` | `pass` | `2026-04-29T02:03:06+00:00` |
| `controlled_test_output/tier5_10e_20260428_220316` | `superseded_rerun` | `pass` | `2026-04-29T02:30:50+00:00` |
| `controlled_test_output/tier5_10f_20260428_224743` | `superseded_rerun` | `pass` | `2026-04-29T02:47:55+00:00` |
| `controlled_test_output/tier5_10f_20260428_224805` | `superseded_rerun` | `fail` | `2026-04-29T03:09:02+00:00` |
| `controlled_test_output/tier5_10g_20260428_232824` | `superseded_rerun` | `pass` | `2026-04-29T03:28:34+00:00` |
| `controlled_test_output/tier5_10g_20260428_232844` | `superseded_rerun` | `pass` | `2026-04-29T03:54:38+00:00` |
| `controlled_test_output/tier5_11a_20260429_004328` | `superseded_rerun` | `pass` | `2026-04-29T04:43:33+00:00` |
| `controlled_test_output/tier5_11a_20260429_004340` | `superseded_rerun` | `pass` | `2026-04-29T05:20:32+00:00` |
| `controlled_test_output/tier5_11b_20260429_014626` | `superseded_rerun` | `pass` | `2026-04-29T05:46:30.784965+00:00` |
| `controlled_test_output/tier5_11b_20260429_014637` | `superseded_rerun` | `pass` | `2026-04-29T06:19:27.117320+00:00` |
| `controlled_test_output/tier5_11b_20260429_022032` | `superseded_rerun` | `pass` | `2026-04-29T06:20:37.559312+00:00` |
| `controlled_test_output/tier5_11b_20260429_022048` | `superseded_rerun` | `fail` | `2026-04-29T06:54:22.530779+00:00` |
| `controlled_test_output/tier5_11c_20260429_031407` | `superseded_rerun` | `pass` | `2026-04-29T07:14:14.986139+00:00` |
| `controlled_test_output/tier5_11c_20260429_031427` | `superseded_rerun` | `fail` | `2026-04-29T08:02:20.343481+00:00` |
| `controlled_test_output/tier5_11d_20260429_041508` | `superseded_rerun` | `pass` | `2026-04-29T08:15:15.750853+00:00` |
| `controlled_test_output/tier5_11d_20260429_041524` | `superseded_rerun` | `pass` | `2026-04-29T09:05:07.124004+00:00` |
| `controlled_test_output/tier5_12a_20260429_054041` | `superseded_rerun` | `pass` | `2026-04-29T09:40:41+00:00` |
| `controlled_test_output/tier5_12b_20260429_055907` | `superseded_rerun` | `pass` | `None` |
| `controlled_test_output/tier5_12b_20260429_055923` | `superseded_rerun` | `fail` | `None` |
| `controlled_test_output/tier5_12c_20260429_062239` | `superseded_rerun` | `pass` | `None` |
| `controlled_test_output/tier5_12d_20260429_070531` | `superseded_rerun` | `pass` | `2026-04-29T11:06:08+00:00` |
| `controlled_test_output/tier5_12d_20260429_121121` | `superseded_rerun` | `pass` | `2026-04-29T16:11:54+00:00` |
| `controlled_test_output/tier5_12d_20260429_122720` | `superseded_rerun` | `pass` | `2026-04-29T16:32:39+00:00` |
| `controlled_test_output/tier5_13_20260429_075527` | `superseded_rerun` | `pass` | `2026-04-29T11:55:32+00:00` |
| `controlled_test_output/tier5_13_20260429_075539` | `superseded_rerun` | `pass` | `2026-04-29T11:56:47+00:00` |
| `controlled_test_output/tier5_13b_20260429_121214` | `superseded_rerun` | `blocked` | `2026-04-29T12:12:20+00:00` |
| `controlled_test_output/tier5_13b_20260429_121321` | `superseded_rerun` | `fail` | `2026-04-29T12:13:27+00:00` |
| `controlled_test_output/tier5_13b_20260429_121356` | `superseded_rerun` | `pass` | `2026-04-29T12:14:13+00:00` |
| `controlled_test_output/tier5_13b_20260429_121425` | `superseded_rerun` | `fail` | `2026-04-29T12:15:44+00:00` |
| `controlled_test_output/tier5_13b_20260429_121615` | `superseded_rerun` | `pass` | `2026-04-29T12:18:12+00:00` |
| `controlled_test_output/tier5_13c_20260429_154941` | `superseded_rerun` | `pass` | `2026-04-29T15:50:15+00:00` |
| `controlled_test_output/tier5_13c_20260429_155023` | `superseded_rerun` | `fail` | `2026-04-29T15:59:51+00:00` |
| `controlled_test_output/tier5_13c_20260429_160057` | `superseded_rerun` | `pass` | `2026-04-29T16:01:33+00:00` |
| `controlled_test_output/tier5_13c_20260429_160142` | `superseded_rerun` | `pass` | `2026-04-29T16:11:03+00:00` |
| `controlled_test_output/tier5_13c_20260429_201248` | `superseded_rerun` | `pass` | `2026-04-29T20:26:20+00:00` |
| `controlled_test_output/tier5_14_20260429_165213` | `superseded_rerun` | `blocked` | `2026-04-29T16:52:27+00:00` |
| `controlled_test_output/tier5_14_20260429_165253` | `superseded_rerun` | `fail` | `2026-04-29T16:53:06+00:00` |
| `controlled_test_output/tier5_14_20260429_165328` | `superseded_rerun` | `pass` | `2026-04-29T16:54:00+00:00` |
| `controlled_test_output/tier5_14_20260429_165409` | `superseded_rerun` | `pass` | `2026-04-29T17:04:57+00:00` |
| `controlled_test_output/tier5_15_20260429_135917` | `temporal_code_diagnostic` | `pass` | `2026-04-29T17:59:17+00:00` |
| `controlled_test_output/tier5_15_20260429_135924` | `temporal_code_diagnostic` | `pass` | `2026-04-29T18:00:03+00:00` |
| `controlled_test_output/tier5_16_20260429_142627` | `neuron_model_sensitivity_diagnostic` | `pass` | `2026-04-29T18:26:31+00:00` |
| `controlled_test_output/tier5_16_20260429_142647` | `neuron_model_sensitivity_diagnostic` | `pass` | `2026-04-29T18:34:02+00:00` |
| `controlled_test_output/tier5_17_20260429_185703` | `pre_reward_representation_diagnostic` | `pass` | `2026-04-29T18:57:03+00:00` |
| `controlled_test_output/tier5_17_20260429_185726` | `pre_reward_representation_diagnostic` | `pass` | `2026-04-29T18:57:27+00:00` |
| `controlled_test_output/tier5_17_20260429_185759` | `pre_reward_representation_diagnostic` | `fail` | `2026-04-29T18:58:02+00:00` |
| `controlled_test_output/tier5_17_20260429_185928` | `pre_reward_representation_diagnostic` | `fail` | `2026-04-29T18:59:36+00:00` |
| `controlled_test_output/tier5_17_20260429_190020` | `pre_reward_representation_diagnostic` | `fail` | `2026-04-29T19:00:40+00:00` |
| `controlled_test_output/tier5_17_20260429_190436` | `pre_reward_representation_diagnostic` | `pass` | `2026-04-29T19:04:37+00:00` |
| `controlled_test_output/tier5_17_20260429_190501` | `pre_reward_representation_diagnostic` | `fail` | `2026-04-29T19:05:07+00:00` |
| `controlled_test_output/tier5_17b_20260429_191512` | `pre_reward_representation_failure_analysis` | `pass` | `2026-04-29T19:15:13+00:00` |
| `controlled_test_output/tier5_17b_20260429_191950` | `pre_reward_representation_failure_analysis` | `pass` | `2026-04-29T19:19:51+00:00` |
| `controlled_test_output/tier5_17c_20260429_192900` | `intrinsic_predictive_preexposure_diagnostic` | `pass` | `2026-04-29T19:29:01+00:00` |
| `controlled_test_output/tier5_17c_20260429_192910` | `intrinsic_predictive_preexposure_diagnostic` | `fail` | `2026-04-29T19:29:14+00:00` |
| `controlled_test_output/tier5_17c_20260429_192956` | `intrinsic_predictive_preexposure_diagnostic` | `fail` | `2026-04-29T19:30:03+00:00` |
| `controlled_test_output/tier5_17c_20260429_193054` | `intrinsic_predictive_preexposure_diagnostic` | `fail` | `2026-04-29T19:30:58+00:00` |
| `controlled_test_output/tier5_17c_20260429_193147` | `intrinsic_predictive_preexposure_diagnostic` | `fail` | `2026-04-29T19:31:55+00:00` |
| `controlled_test_output/tier5_17c_20260429_193539` | `intrinsic_predictive_preexposure_diagnostic` | `pass` | `2026-04-29T19:35:39+00:00` |
| `controlled_test_output/tier5_17d_20260429_194414` | `predictive_binding_preexposure_diagnostic` | `pass` | `2026-04-29T19:44:14+00:00` |
| `controlled_test_output/tier5_17d_20260429_194428` | `predictive_binding_preexposure_diagnostic` | `fail` | `2026-04-29T19:44:32+00:00` |
| `controlled_test_output/tier5_17d_20260429_194522` | `predictive_binding_preexposure_diagnostic` | `fail` | `2026-04-29T19:45:25+00:00` |
| `controlled_test_output/tier5_17d_20260429_194552` | `predictive_binding_preexposure_diagnostic` | `pass` | `2026-04-29T19:45:54+00:00` |
| `controlled_test_output/tier5_17d_20260429_194613` | `predictive_binding_preexposure_diagnostic` | `pass` | `2026-04-29T19:46:15+00:00` |
| `controlled_test_output/tier5_17e_20260429_160245` | `predictive_binding_compact_regression_gate` | `fail` | `2026-04-29T20:26:21+00:00` |
| `controlled_test_output/tier5_17e_20260429_162729` | `predictive_binding_compact_regression_gate` | `pass` | `2026-04-29T20:30:44+00:00` |
| `controlled_test_output/tier5_17e_20260429_163058` | `predictive_binding_compact_regression_gate` | `pass` | `2026-04-29T21:06:01+00:00` |
| `controlled_test_output/tier5_18_20260429_212708` | `self_evaluation_metacognition_diagnostic` | `pass` | `2026-04-29T21:27:08+00:00` |
| `controlled_test_output/tier5_18_20260429_212721` | `self_evaluation_metacognition_diagnostic` | `fail` | `2026-04-29T21:27:23+00:00` |
| `controlled_test_output/tier5_18_20260429_212823` | `self_evaluation_metacognition_diagnostic` | `pass` | `2026-04-29T21:28:23+00:00` |
| `controlled_test_output/tier5_18_20260429_212830` | `self_evaluation_metacognition_diagnostic` | `fail` | `2026-04-29T21:28:33+00:00` |
| `controlled_test_output/tier5_18_20260429_212918` | `self_evaluation_metacognition_diagnostic` | `pass` | `2026-04-29T21:29:18+00:00` |
| `controlled_test_output/tier5_18_20260429_212926` | `self_evaluation_metacognition_diagnostic` | `fail` | `2026-04-29T21:29:28+00:00` |
| `controlled_test_output/tier5_18_20260429_213002` | `self_evaluation_metacognition_diagnostic` | `pass` | `2026-04-29T21:30:04+00:00` |
| `controlled_test_output/tier5_18c_20260429_220841` | `self_evaluation_compact_regression_gate` | `pass` | `2026-04-29T22:10:32+00:00` |
| `controlled_test_output/tier5_18c_20260429_221045` | `self_evaluation_compact_regression_gate` | `pass` | `2026-04-29T22:36:19+00:00` |
| `controlled_test_output/tier5_5_20260427_222527` | `superseded_rerun` | `pass` | `2026-04-28T02:25:28+00:00` |
| `controlled_test_output/tier5_6_20260428_001803` | `superseded_rerun` | `pass` | `2026-04-28T04:18:03+00:00` |
| `controlled_test_output/tier5_7_20260428_005610` | `superseded_rerun` | `fail` | `2026-04-28T04:56:21+00:00` |
| `controlled_test_output/tier5_7_20260428_005646` | `superseded_rerun` | `pass` | `2026-04-28T04:57:08+00:00` |
| `controlled_test_output/tier5_7_20260428_214229` | `superseded_rerun` | `pass` | `2026-04-29T01:42:51+00:00` |
| `controlled_test_output/tier5_7_20260428_214807` | `superseded_rerun` | `pass` | `2026-04-29T01:50:41+00:00` |
| `controlled_test_output/tier5_7_20260428_235507` | `superseded_rerun` | `pass` | `2026-04-29T03:57:44+00:00` |
| `controlled_test_output/tier5_7_20260429_050527` | `superseded_rerun` | `pass` | `2026-04-29T09:08:17+00:00` |
| `controlled_test_output/tier5_9a_20260428_162252` | `superseded_rerun` | `pass` | `2026-04-28T20:22:56+00:00` |
| `controlled_test_output/tier5_9a_20260428_162345` | `superseded_rerun` | `fail` | `2026-04-28T20:55:15+00:00` |
| `controlled_test_output/tier5_9b_20260428_171657` | `superseded_rerun` | `pass` | `2026-04-28T21:17:00+00:00` |
| `controlled_test_output/tier5_9b_20260428_171707` | `superseded_rerun` | `fail` | `2026-04-28T21:42:49+00:00` |
| `controlled_test_output/tier5_9b_20260428_174327` | `superseded_rerun` | `fail` | `2026-04-28T22:01:31+00:00` |
| `controlled_test_output/tier5_9c_20260429_190257` | `macro_eligibility_v2_1_recheck` | `pass` | `2026-04-29T23:04:49+00:00` |
| `controlled_test_output/tier5_9c_20260429_190503` | `macro_eligibility_v2_1_recheck` | `fail` | `2026-04-29T23:53:13+00:00` |
| `controlled_test_output/tier6_1_20260428_012026` | `superseded_rerun` | `pass` | `2026-04-28T05:20:27+00:00` |
| `controlled_test_output/tier6_1_20260428_012059` | `superseded_rerun` | `pass` | `2026-04-28T05:21:00+00:00` |
| `controlled_test_output/tier6_3_20260428_121049` | `superseded_rerun` | `pass` | `2026-04-28T16:10:50+00:00` |
| `controlled_test_output/tier6_3_20260428_121102` | `superseded_rerun` | `pass` | `2026-04-28T16:11:05+00:00` |
| `controlled_test_output/tier6_3_20260428_121138` | `superseded_rerun` | `pass` | `2026-04-28T16:11:40+00:00` |
| `controlled_test_output/tier6_3_20260428_121157` | `superseded_rerun` | `unknown` | `None` |
| `controlled_test_output/tier6_3_20260428_121452` | `superseded_rerun` | `pass` | `2026-04-28T16:14:54+00:00` |
| `controlled_test_output/tier6_4_20260428_131959` | `superseded_rerun` | `pass` | `2026-04-28T17:20:01+00:00` |
| `controlled_test_output/tier6_4_20260428_132009` | `superseded_rerun` | `fail` | `2026-04-28T18:31:46+00:00` |
| `controlled_test_output/tier6_4_20260428_143252` | `superseded_rerun` | `unknown` | `None` |
| `controlled_test_output/tier6_4_20260428_160526` | `superseded_rerun` | `pass` | `2026-04-28T20:05:28+00:00` |
| `controlled_test_output/tier7_0e_20260508_length_10000_scoreboard` | `superseded_rerun` | `fail` | `2026-05-08T18:32:32+00:00` |
| `controlled_test_output/tier7_0e_20260508_length_calibration` | `superseded_rerun` | `pass` | `2026-05-08T18:40:40+00:00` |

## Integrity

- Missing expected artifacts: `0`
- Failed criteria in canonical entries: `0`
- Latest manifest pointers are regenerated by `python3 experiments/evidence_registry.py`.
