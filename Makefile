.PHONY: test registry paper-table clean-transients audit validate tier1 tier2 tier3 tier4 tier4-10b tier4-11 tier4-12 tier4-13-prepare tier4-14 tier4-14-prepare tier4-15-prepare tier4-16-prepare tier4-16a-chunked-prepare tier4-16a-chunked-full-prepare tier4-16b-chunked-prepare tier4-16b-repaired-probe-prepare tier4-16a-debug tier4-16a-fix tier4-16b-debug tier4-17 tier4-17b tier4-18a-prepare tier4-20a tier4-20a-smoke tier4-20b-prepare tier4-20b-preflight tier4-20b-smoke tier4-20c-prepare tier4-20c-smoke tier4-21a-prepare tier4-21a-local tier4-21a-smoke tier4-22a tier4-22a0 tier4-22b tier4-22b-prepare tier4-22c tier4-22d tier4-22e tier4-22f0 tier4-22g tier4-22h tier4-22i-prepare tier4-22j-prepare tier4-22k-prepare tier4-22l-local tier4-22l-prepare tier4-22m-local tier4-22m-prepare tier4-22n-local tier4-22n-prepare tier4-22o-local tier4-22o-prepare tier4-22p-local tier4-22p-prepare tier4-22q-local tier4-22q-prepare tier4-30-readiness tier4-30-contract tier4-30a tier4-30b tier4-30b-hw-prepare tier4-30c tier4-30d tier4-30e-prepare tier4-31a tier4-31b tier4-31c tier4-31d-prepare tier4-31d-ingest tier4-32 tier4-32a tier4-32f tier4-32g-r0 tier5-1 tier5-2 tier5-3 tier5-4 tier5-5 tier5-5-smoke tier5-6 tier5-6-smoke tier5-7 tier5-7-smoke tier5-9a tier5-9a-smoke tier5-9b tier5-9b-smoke tier5-9c tier5-9c-smoke tier5-10 tier5-10-smoke tier5-10b tier5-10b-smoke tier5-10c tier5-10c-smoke tier5-10d tier5-10d-smoke tier5-10e tier5-10e-smoke tier5-10f tier5-10f-smoke tier5-10g tier5-10g-smoke tier5-11a tier5-11a-smoke tier5-11b tier5-11b-smoke tier5-11c tier5-11c-smoke tier5-11d tier5-11d-smoke tier5-12a tier5-12a-smoke tier5-12b tier5-12b-smoke tier5-12c tier5-12c-smoke tier5-13 tier5-13-smoke tier5-13b tier5-13b-smoke tier5-13c tier5-14 tier5-14-smoke tier5-15 tier5-15-smoke tier5-16 tier5-16-smoke tier5-17 tier5-17-smoke tier5-17b tier5-17b-smoke tier5-17c tier5-17c-smoke tier5-17d tier5-17d-smoke tier5-17e tier5-17e-smoke tier5-18 tier5-18-smoke tier5-18c tier5-18c-smoke tier5-20a tier5-20b tier5-20c tier5-20d tier5-20e tier6-1 tier6-1-smoke tier6-2a tier6-2a-smoke tier6-3 tier6-3-smoke tier6-4 tier6-4-smoke tier7-1a tier7-1b tier7-1c tier7-1d tier7-1e tier7-1f tier7-1g tier7-1h tier7-1i tier7-1j tier7-1k tier7-1l tier7-1m tier7-4a tier7-4b tier7-4c tier7-4d tier7-4e tier7-4f

test:
	python3 -m pytest -p no:cacheprovider coral_reef_spinnaker/tests

registry:
	python3 experiments/evidence_registry.py

paper-table:
	python3 experiments/export_paper_results_table.py

clean-transients:
	find . -name '.DS_Store' -print -delete

audit: clean-transients
	python3 experiments/repo_audit.py

validate: test registry paper-table audit

tier1:
	python3 experiments/tier1_sanity.py --tests all --stop-on-fail

tier2:
	python3 experiments/tier2_learning.py --tests all --stop-on-fail

tier3:
	python3 experiments/tier3_ablation.py --tests all --stop-on-fail

tier4:
	python3 experiments/tier4_scaling.py --stop-on-fail

tier4-10b:
	python3 experiments/tier4_hard_scaling.py --stop-on-fail

tier4-11:
	python3 experiments/tier4_domain_transfer.py --stop-on-fail

tier4-12:
	python3 experiments/tier4_backend_parity.py --stop-on-fail

tier4-13-prepare:
	python3 experiments/tier4_spinnaker_hardware_capsule.py --mode prepare

tier4-14:
	python3 experiments/tier4_hardware_runtime_characterization.py --mode characterize-existing

tier4-14-prepare:
	python3 experiments/tier4_hardware_runtime_characterization.py --mode prepare

tier4-15-prepare:
	python3 experiments/tier4_spinnaker_hardware_repeat.py --mode prepare

tier4-16-prepare:
	python3 experiments/tier4_harder_spinnaker_capsule.py --mode prepare

tier4-16a-chunked-prepare:
	python3 experiments/tier4_harder_spinnaker_capsule.py --mode prepare --tasks delayed_cue --seeds 43 --steps 1200 --runtime-mode chunked --learning-location host --chunk-size-steps 25

tier4-16a-chunked-full-prepare:
	python3 experiments/tier4_harder_spinnaker_capsule.py --mode prepare --tasks delayed_cue --seeds 42,43,44 --steps 1200 --runtime-mode chunked --learning-location host --chunk-size-steps 25

tier4-16b-chunked-prepare:
	python3 experiments/tier4_harder_spinnaker_capsule.py --mode prepare --tasks hard_noisy_switching --seeds 42,43,44 --steps 1200 --runtime-mode chunked --learning-location host --chunk-size-steps 25

tier4-16b-repaired-probe-prepare:
	python3 experiments/tier4_harder_spinnaker_capsule.py --mode prepare --tasks hard_noisy_switching --seeds 44 --steps 1200 --runtime-mode chunked --learning-location host --chunk-size-steps 25

tier4-16a-debug:
	python3 experiments/tier4_16a_delayed_cue_debug.py --backends nest,brian2 --seeds 42,43,44

tier4-16a-fix:
	python3 experiments/tier4_16a_delayed_cue_fix.py --run-lengths 1200 --backends nest,brian2 --seeds 42,43,44

tier4-16b-debug:
	python3 experiments/tier4_16b_hard_switch_debug.py --backends nest,brian2 --seeds 42,43,44 --steps 1200 --chunk-size-steps 25

tier4-17:
	python3 experiments/tier4_chunked_runtime.py --steps 1200 --chunk-sizes 1,5,10,25,50

tier4-17b:
	python3 experiments/tier4_17b_step_vs_chunked_parity.py --backends nest,brian2 --seed 42 --steps 120 --chunk-sizes 5,10,25,50

tier4-18a-prepare:
	python3 experiments/tier4_18a_chunked_runtime_baseline.py --mode prepare --tasks delayed_cue,hard_noisy_switching --seeds 42 --chunk-sizes 10,25,50 --steps 1200 --population-size 8 --delayed-readout-lr 0.20

tier4-20a:
	python3 experiments/tier4_20a_hardware_transfer_audit.py

tier4-20a-smoke:
	python3 experiments/tier4_20a_hardware_transfer_audit.py --total-steps 120 --chunk-size-steps 25

tier4-20b-prepare:
	python3 experiments/tier4_20b_v2_1_hardware_probe.py --mode prepare --tasks delayed_cue,hard_noisy_switching --seeds 42 --steps 1200 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20

tier4-20b-preflight:
	python3 experiments/tier4_20b_sim_preflight.py


tier4-20b-smoke:
	python3 experiments/tier4_20b_v2_1_hardware_probe.py --mode prepare --tasks delayed_cue --seeds 42 --steps 120 --population-size 8 --chunk-size-steps 25 --delayed-readout-lr 0.20

tier4-20c-prepare:
	python3 experiments/tier4_20c_v2_1_hardware_repeat.py --mode prepare --tasks delayed_cue,hard_noisy_switching --seeds 42,43,44 --steps 1200 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20

tier4-20c-smoke:
	python3 experiments/tier4_20c_v2_1_hardware_repeat.py --mode prepare --tasks delayed_cue,hard_noisy_switching --seeds 42,43,44 --steps 120 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20

tier4-21a-prepare:
	python3 experiments/tier4_21a_keyed_context_memory_bridge.py --mode prepare --tasks context_reentry_interference --variants keyed_context_memory,slot_reset_ablation,slot_shuffle_ablation,wrong_key_ablation --seeds 42 --steps 720 --population-size 8 --chunk-size-steps 50 --context-memory-slot-count 4 --delayed-readout-lr 0.20

tier4-21a-local:
	python3 experiments/tier4_21a_keyed_context_memory_bridge.py --mode local-bridge --tasks context_reentry_interference --variants keyed_context_memory,slot_reset_ablation,slot_shuffle_ablation,wrong_key_ablation --seeds 42 --steps 180 --population-size 8 --chunk-size-steps 50 --context-memory-slot-count 4 --delayed-readout-lr 0.20

tier4-21a-smoke:
	python3 experiments/tier4_21a_keyed_context_memory_bridge.py --mode prepare --tasks context_reentry_interference --variants keyed_context_memory,slot_reset_ablation --seeds 42 --steps 120 --population-size 8 --chunk-size-steps 50 --context-memory-slot-count 4 --delayed-readout-lr 0.20

tier4-22a:
	python3 experiments/tier4_22a_custom_runtime_contract.py

tier4-22a0:
	python3 experiments/tier4_22a0_spinnaker_constrained_preflight.py --output-dir controlled_test_output/tier4_22a0_20260430_spinnaker_constrained_preflight

tier4-22b:
	python3 experiments/tier4_22b_continuous_transport_scaffold.py --mode local --tasks delayed_cue,hard_noisy_switching --seeds 42 --steps 1200 --output-dir controlled_test_output/tier4_22b_20260430_continuous_transport_local

tier4-22b-prepare:
	python3 experiments/tier4_22b_continuous_transport_scaffold.py --mode prepare --tasks delayed_cue,hard_noisy_switching --seeds 42 --steps 1200 --population-size 8 --output-dir controlled_test_output/tier4_22b_20260430_prepared

tier4-22c:
	python3 experiments/tier4_22c_persistent_state_scaffold.py --output-dir controlled_test_output/tier4_22c_20260430_persistent_state_scaffold

tier4-22d:
	python3 experiments/tier4_22d_reward_plasticity_scaffold.py --output-dir controlled_test_output/tier4_22d_20260430_reward_plasticity_scaffold

tier4-22e:
	python3 experiments/tier4_22e_local_learning_parity.py --output-dir controlled_test_output/tier4_22e_20260430_local_learning_parity

tier4-22f0:
	python3 experiments/tier4_22f0_custom_runtime_scale_audit.py --output-dir controlled_test_output/tier4_22f0_20260430_custom_runtime_scale_audit

tier4-22g:
	python3 experiments/tier4_22g_event_indexed_trace_runtime.py --output-dir controlled_test_output/tier4_22g_20260430_event_indexed_trace_runtime

tier4-22h:
	python3 experiments/tier4_22h_compact_readback_acceptance.py --output-dir controlled_test_output/tier4_22h_20260430_compact_readback_acceptance

tier4-22i-prepare:
	python3 experiments/tier4_22i_custom_runtime_roundtrip.py --mode prepare --output-dir controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared

tier4-22j-prepare:
	python3 experiments/tier4_22j_minimal_custom_runtime_learning.py --mode prepare --output-dir controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_prepared

tier4-22k-prepare:
	python3 experiments/tier4_22k_spin1api_event_discovery.py --mode prepare --output-dir controlled_test_output/tier4_22k_20260430_spin1api_event_discovery_prepared

tier4-22l-local:
	python3 experiments/tier4_22l_custom_runtime_learning_parity.py --mode local --output-dir controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_local

tier4-22l-prepare:
	python3 experiments/tier4_22l_custom_runtime_learning_parity.py --mode prepare --output-dir controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared

tier4-22m-local:
	python3 experiments/tier4_22m_custom_runtime_task_micro_loop.py --mode local --output-dir controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_local

tier4-22m-prepare:
	python3 experiments/tier4_22m_custom_runtime_task_micro_loop.py --mode prepare --output-dir controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_prepared

tier4-22n-local:
	python3 experiments/tier4_22n_delayed_cue_micro_task.py --mode local --output-dir controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_local

tier4-22n-prepare:
	python3 experiments/tier4_22n_delayed_cue_micro_task.py --mode prepare --output-dir controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_prepared

tier4-22o-local:
	python3 experiments/tier4_22o_noisy_switching_micro_task.py --mode local --output-dir controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_local

tier4-22o-prepare:
	python3 experiments/tier4_22o_noisy_switching_micro_task.py --mode prepare --output-dir controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_prepared

tier4-22p-local:
	python3 experiments/tier4_22p_reentry_micro_task.py --mode local --output-dir controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_local

tier4-22p-prepare:
	python3 experiments/tier4_22p_reentry_micro_task.py --mode prepare --output-dir controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_prepared

tier4-22q-local:
	python3 experiments/tier4_22q_integrated_v2_bridge_smoke.py --mode local --output-dir controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_local

tier4-22q-prepare:
	python3 experiments/tier4_22q_integrated_v2_bridge_smoke.py --mode prepare --output-dir controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_prepared

tier4-30-readiness:
	python3 experiments/tier4_30_readiness_audit.py

tier4-30-contract:
	python3 experiments/tier4_30_lifecycle_native_contract.py

tier4-30a:
	python3 experiments/tier4_30a_static_pool_lifecycle_reference.py

tier4-30b:
	python3 experiments/tier4_30b_lifecycle_source_audit.py

tier4-30b-hw-prepare:
	python3 experiments/tier4_30b_lifecycle_hardware_smoke.py --mode prepare --output-dir controlled_test_output/tier4_30b_hw_20260505_prepared

tier4-30c:
	python3 experiments/tier4_30c_multicore_lifecycle_split.py

tier4-30d:
	python3 experiments/tier4_30d_lifecycle_runtime_source_audit.py

tier4-30e-prepare:
	python3 experiments/tier4_30e_multicore_lifecycle_hardware_smoke.py --mode prepare --output-dir controlled_test_output/tier4_30e_hw_20260505_prepared

tier4-31a:
	python3 experiments/tier4_31a_native_temporal_substrate_readiness.py

tier4-31b:
	python3 experiments/tier4_31b_native_temporal_fixed_point_reference.py

tier4-31c:
	python3 experiments/tier4_31c_native_temporal_runtime_source_audit.py

tier4-31d-prepare:
	python3 experiments/tier4_31d_native_temporal_hardware_smoke.py --mode prepare

tier4-31d-ingest:
	python3 experiments/tier4_31d_native_temporal_hardware_smoke.py --mode ingest

tier4-32:
	python3 experiments/tier4_32_mapping_resource_model.py

tier4-32a:
	python3 experiments/tier4_32a_single_chip_scale_stress.py

tier4-32f:
	python3 experiments/tier4_32f_multichip_resource_lifecycle_decision.py

tier4-32g-r0:
	python3 experiments/tier4_32g_r0_multichip_lifecycle_route_source_audit.py

tier5-1:
	python3 experiments/tier5_external_baselines.py --backend nest --seed-count 3 --steps 240 --models all --tasks all

tier5-2:
	python3 experiments/tier5_learning_curve.py --backend nest --seed-count 3 --run-lengths 120,240,480,960,1500 --tasks sensor_control,hard_noisy_switching,delayed_cue --models all --stop-on-fail

tier5-3:
	python3 experiments/tier5_cra_failure_analysis.py --backend nest --seed-count 3 --steps 960 --tasks delayed_cue,hard_noisy_switching --variants core --stop-on-fail

tier5-4:
	python3 experiments/tier5_delayed_credit_confirmation.py --backend nest --seed-count 3 --run-lengths 960,1500 --tasks delayed_cue,hard_noisy_switching --stop-on-fail

tier5-5:
	python3 experiments/tier5_expanded_baselines.py --backend nest --seed-count 10 --run-lengths 120,240,480,960,1500 --tasks fixed_pattern,delayed_cue,hard_noisy_switching,sensor_control --models all --cra-variants v0_8 --stop-on-fail

tier5-5-smoke:
	python3 experiments/tier5_expanded_baselines.py --backend mock --seed-count 1 --run-lengths 120 --tasks delayed_cue,hard_noisy_switching --models random_sign,sign_persistence --cra-variants v0_8 --bootstrap-reps 50 --min-advantage-regimes 0 --allowed-dominated-hard-regimes 99

tier5-6:
	python3 experiments/tier5_baseline_fairness_audit.py --backend nest --seed-count 5 --run-lengths 960,1500 --tasks delayed_cue,hard_noisy_switching,sensor_control --models all --cra-variants v0_8 --budget standard --stop-on-fail

tier5-6-smoke:
	python3 experiments/tier5_baseline_fairness_audit.py --backend mock --seed-count 1 --run-lengths 120 --tasks hard_noisy_switching --models online_perceptron,online_logistic_regression --cra-variants v0_8 --budget smoke --bootstrap-reps 50 --min-retuned-robust-regimes 0 --min-surviving-advantage-regimes 0

tier5-7:
	python3 experiments/tier5_compact_regression.py --backend nest --readout-lr 0.10 --delayed-readout-lr 0.20 --stop-on-fail

tier5-7-smoke:
	python3 experiments/tier5_compact_regression.py --backend mock --tier1-steps 80 --tier1-seeds 3 --tier2-steps 120 --tier3-steps 180 --tier3-ecology-steps 220 --tier3-seed-count 3 --smoke-steps 80 --smoke-seed-count 1 --bootstrap-reps 20 --readout-lr 0.10 --delayed-readout-lr 0.20 --stop-on-fail

tier5-9a:
	python3 experiments/tier5_macro_eligibility.py --backend nest --tasks delayed_cue,hard_noisy_switching,variable_delay_cue,aba_recurrence --steps 960 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,stdp_only_snn --variants all --stop-on-fail

tier5-9a-smoke:
	python3 experiments/tier5_macro_eligibility.py --backend mock --tasks delayed_cue,variable_delay_cue --steps 160 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-9b:
	python3 experiments/tier5_macro_eligibility_repair.py --backend nest --tasks delayed_cue,hard_noisy_switching,variable_delay_cue,aba_recurrence --steps 960 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,stdp_only_snn --variants all --stop-on-fail

tier5-9b-smoke:
	python3 experiments/tier5_macro_eligibility_repair.py --backend mock --tasks delayed_cue,variable_delay_cue --steps 160 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-9c:
	python3 experiments/tier5_macro_eligibility_v2_1_recheck.py --backend nest --tasks delayed_cue,hard_noisy_switching,variable_delay_cue,aba_recurrence --steps 960 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,stdp_only_snn --stop-on-fail

tier5-9c-smoke:
	python3 experiments/tier5_macro_eligibility_v2_1_recheck.py --smoke --stop-on-fail

tier5-10:
	python3 experiments/tier5_multi_timescale_memory.py --backend nest --tasks aba_recurrence,abca_recurrence,hidden_regime_switching --steps 960 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,stdp_only_snn --variants all --stop-on-fail

tier5-10-smoke:
	python3 experiments/tier5_multi_timescale_memory.py --backend mock --tasks aba_recurrence,abca_recurrence --steps 160 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-10b:
	python3 experiments/tier5_memory_pressure_tasks.py --backend mock --tasks delayed_context_cue,distractor_gap_context,hidden_context_recurrence --steps 720 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --stop-on-fail

tier5-10b-smoke:
	python3 experiments/tier5_memory_pressure_tasks.py --backend mock --tasks delayed_context_cue,hidden_context_recurrence --steps 180 --seed-count 1 --models sign_persistence,online_perceptron --smoke

tier5-10c:
	python3 experiments/tier5_context_memory_mechanism.py --backend nest --tasks delayed_context_cue,distractor_gap_context,hidden_context_recurrence --steps 720 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-10c-smoke:
	python3 experiments/tier5_context_memory_mechanism.py --backend mock --tasks delayed_context_cue,hidden_context_recurrence --steps 180 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-10d:
	python3 experiments/tier5_internal_context_memory.py --backend nest --tasks delayed_context_cue,distractor_gap_context,hidden_context_recurrence --steps 720 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-10d-smoke:
	python3 experiments/tier5_internal_context_memory.py --backend mock --tasks delayed_context_cue,hidden_context_recurrence --steps 180 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-10e:
	python3 experiments/tier5_memory_retention_stressor.py --backend nest --tasks delayed_context_cue,distractor_gap_context,hidden_context_recurrence --steps 960 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-10e-smoke:
	python3 experiments/tier5_memory_retention_stressor.py --backend mock --tasks delayed_context_cue,hidden_context_recurrence --steps 240 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-10f:
	python3 experiments/tier5_memory_capacity_interference.py --backend nest --tasks intervening_contexts,overlapping_contexts,context_reentry_interference --steps 720 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-10f-smoke:
	python3 experiments/tier5_memory_capacity_interference.py --backend mock --tasks intervening_contexts,overlapping_contexts --steps 240 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-10g:
	python3 experiments/tier5_keyed_context_memory.py --backend nest --tasks intervening_contexts,overlapping_contexts,context_reentry_interference --steps 720 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-10g-smoke:
	python3 experiments/tier5_keyed_context_memory.py --backend mock --tasks intervening_contexts,overlapping_contexts --steps 240 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-11a:
	python3 experiments/tier5_sleep_replay_need.py --backend nest --tasks silent_context_reentry,long_gap_silent_reentry,partial_key_reentry --steps 960 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-11a-smoke:
	python3 experiments/tier5_sleep_replay_need.py --backend mock --tasks silent_context_reentry --steps 240 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-11b:
	python3 experiments/tier5_sleep_replay_intervention.py --backend nest --tasks silent_context_reentry,long_gap_silent_reentry,partial_key_reentry --steps 960 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-11b-smoke:
	python3 experiments/tier5_sleep_replay_intervention.py --backend mock --tasks silent_context_reentry --steps 240 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-11c:
	python3 experiments/tier5_replay_sham_separation.py --backend nest --tasks silent_context_reentry,long_gap_silent_reentry,partial_key_reentry --steps 960 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-11c-smoke:
	python3 experiments/tier5_replay_sham_separation.py --backend mock --tasks silent_context_reentry --steps 240 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-11d:
	python3 experiments/tier5_generic_replay_confirmation.py --backend nest --tasks silent_context_reentry,long_gap_silent_reentry,partial_key_reentry --steps 960 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-11d-smoke:
	python3 experiments/tier5_generic_replay_confirmation.py --backend mock --tasks silent_context_reentry --steps 240 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-12a:
	python3 experiments/tier5_predictive_task_pressure.py --backend mock --tasks hidden_regime_switching,masked_input_prediction,event_stream_prediction,sensor_anomaly_prediction --steps 720 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --stop-on-fail

tier5-12a-smoke:
	python3 experiments/tier5_predictive_task_pressure.py --backend mock --tasks hidden_regime_switching,event_stream_prediction --steps 180 --seed-count 1 --models sign_persistence,online_perceptron --smoke

tier5-12b:
	python3 experiments/tier5_predictive_context_mechanism.py --backend nest --tasks masked_input_prediction,event_stream_prediction,sensor_anomaly_prediction --steps 720 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-12b-smoke:
	python3 experiments/tier5_predictive_context_mechanism.py --backend mock --tasks masked_input_prediction,event_stream_prediction --steps 180 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-12c:
	python3 experiments/tier5_predictive_context_sham_repair.py --backend nest --tasks masked_input_prediction,event_stream_prediction,sensor_anomaly_prediction --steps 720 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-12c-smoke:
	python3 experiments/tier5_predictive_context_sham_repair.py --backend mock --tasks masked_input_prediction,event_stream_prediction --steps 180 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-12d:
	python3 experiments/tier5_predictive_context_compact_regression.py --backend nest --readout-lr 0.10 --delayed-readout-lr 0.20 --stop-on-fail

tier5-12d-smoke:
	python3 experiments/tier5_predictive_context_compact_regression.py --backend mock --tier1-steps 80 --tier1-seeds 3 --tier2-steps 120 --tier3-steps 180 --tier3-ecology-steps 220 --tier3-seed-count 3 --smoke-steps 80 --smoke-seed-count 1 --bootstrap-reps 20 --memory-backend mock --memory-tasks silent_context_reentry --memory-steps 180 --memory-seed-count 1 --memory-models sign_persistence,online_perceptron --memory-smoke --predictive-backend mock --predictive-tasks masked_input_prediction,event_stream_prediction --predictive-steps 180 --predictive-seed-count 1 --predictive-models sign_persistence,online_perceptron --predictive-smoke --readout-lr 0.10 --delayed-readout-lr 0.20 --stop-on-fail

tier5-13:
	python3 experiments/tier5_compositional_skill_reuse.py --backend mock --tasks heldout_skill_pair,order_sensitive_chain,distractor_skill_chain --steps 720 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-13-smoke:
	python3 experiments/tier5_compositional_skill_reuse.py --backend mock --tasks heldout_skill_pair,order_sensitive_chain --steps 360 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-13b:
	python3 experiments/tier5_module_routing.py --backend mock --tasks heldout_context_routing,distractor_router_chain,context_reentry_routing --steps 960 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --variants all --stop-on-fail

tier5-13b-smoke:
	python3 experiments/tier5_module_routing.py --backend mock --tasks heldout_context_routing,distractor_router_chain --steps 760 --seed-count 1 --models sign_persistence,online_perceptron --variants all --smoke

tier5-13c:
	python3 experiments/tier5_internal_composition_routing.py --backend mock --composition-tasks heldout_skill_pair,order_sensitive_chain,distractor_skill_chain --routing-tasks heldout_context_routing,distractor_router_chain,context_reentry_routing --composition-steps 720 --routing-steps 960 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --stop-on-fail

tier5-13c-smoke:
	python3 experiments/tier5_internal_composition_routing.py --backend mock --smoke --stop-on-fail

tier5-14:
	python3 experiments/tier5_working_memory_context_binding.py --backend mock --memory-tasks intervening_contexts,overlapping_contexts,context_reentry_interference --routing-tasks heldout_context_routing,distractor_router_chain,context_reentry_routing --memory-steps 720 --routing-steps 960 --seed-count 3 --models sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --stop-on-fail

tier5-14-smoke:
	python3 experiments/tier5_working_memory_context_binding.py --backend mock --smoke --stop-on-fail

tier5-15:
	python3 experiments/tier5_spike_encoding_temporal_code.py --backend mock --tasks fixed_pattern,delayed_cue,hard_noisy_switching,sensor_control --encodings rate,latency,burst,population,temporal_interval --steps 720 --seed-count 3 --models temporal_cra,time_shuffle_control,rate_only_control,sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn --stop-on-fail

tier5-15-smoke:
	python3 experiments/tier5_spike_encoding_temporal_code.py --backend mock --smoke --stop-on-fail

tier5-16:
	python3 experiments/tier5_neuron_model_sensitivity.py --backend nest --tasks fixed_pattern,delayed_cue,sensor_control --variants default,v_thresh_low,v_thresh_high,tau_m_fast,tau_m_slow,tau_refrac_short,tau_refrac_long,cm_low,cm_high,tau_syn_fast,tau_syn_slow --steps 180 --seed-count 2 --cra-readout-lr 0.10 --cra-delayed-readout-lr 0.20 --stop-on-fail

tier5-16-smoke:
	python3 experiments/tier5_neuron_model_sensitivity.py --backend mock --smoke --stop-on-fail

tier5-17:
	python3 experiments/tier5_unsupervised_representation.py --tasks latent_cluster_sequence,temporal_motif_sequence,ambiguous_reentry_context --variants all --steps 520 --seed-count 3 --seeds 42,43,44 --stop-on-fail

tier5-17-smoke:
	python3 experiments/tier5_unsupervised_representation.py --smoke --stop-on-fail

tier5-17b:
	python3 experiments/tier5_pre_reward_representation_failure_analysis.py --stop-on-fail

tier5-17b-smoke:
	python3 experiments/tier5_pre_reward_representation_failure_analysis.py --smoke --stop-on-fail

tier5-17c:
	python3 experiments/tier5_intrinsic_predictive_preexposure.py

tier5-17c-smoke:
	python3 experiments/tier5_intrinsic_predictive_preexposure.py --smoke --stop-on-fail

tier5-17d:
	python3 experiments/tier5_predictive_binding_repair.py --stop-on-fail

tier5-17d-smoke:
	python3 experiments/tier5_predictive_binding_repair.py --smoke --stop-on-fail

tier5-17e:
	python3 experiments/tier5_predictive_binding_compact_regression.py --backend nest --readout-lr 0.10 --delayed-readout-lr 0.20 --stop-on-fail

tier5-17e-smoke:
	python3 experiments/tier5_predictive_binding_compact_regression.py --smoke --backend mock --stop-on-fail

tier5-18:
	python3 experiments/tier5_self_evaluation_metacognition.py --stop-on-fail

tier5-18-smoke:
	python3 experiments/tier5_self_evaluation_metacognition.py --smoke --stop-on-fail

tier5-18c:
	python3 experiments/tier5_self_evaluation_compact_regression.py --backend nest --readout-lr 0.10 --delayed-readout-lr 0.20 --stop-on-fail

tier5-18c-smoke:
	python3 experiments/tier5_self_evaluation_compact_regression.py --smoke --backend mock --stop-on-fail

tier5-20a:
	python3 experiments/tier5_20a_resonant_branch_polyp_diagnostic.py --no-timeseries

tier5-20b:
	python3 experiments/tier5_20b_hybrid_resonant_polyp_diagnostic.py --no-timeseries

tier5-20c:
	python3 experiments/tier5_20c_minimal_resonant_polyp_diagnostic.py --no-timeseries

tier5-20d:
	python3 experiments/tier5_20d_resonant_heavy_polyp_diagnostic.py --no-timeseries

tier5-20e:
	python3 experiments/tier5_20e_near_full_resonant_polyp_diagnostic.py --no-timeseries

tier6-1:
	python3 experiments/tier6_lifecycle_self_scaling.py --backend nest --tasks hard_noisy_switching,delayed_cue --cases fixed4,fixed8,fixed16,life4_16,life8_32,life16_64 --steps 960 --seed-count 3 --cra-readout-lr 0.10 --cra-delayed-readout-lr 0.20 --stop-on-fail

tier6-1-smoke:
	python3 experiments/tier6_lifecycle_self_scaling.py --backend mock --tasks hard_noisy_switching --cases smoke --steps 160 --seed-count 1 --min-advantage-regimes 0 --stop-on-fail

tier6-2a:
	python3 experiments/tier6_2a_targeted_usefulness_validation.py

tier6-2a-smoke:
	python3 experiments/tier6_2a_targeted_usefulness_validation.py --smoke --output-dir controlled_test_output/tier6_2a_smoke

tier6-3:
	python3 experiments/tier6_lifecycle_sham_controls.py --backend nest --tasks hard_noisy_switching --regimes life4_16,life8_32 --controls intact,fixed_initial,fixed_max,random_event_replay,active_mask_shuffle,lineage_id_shuffle,no_trophic,no_dopamine,no_plasticity --steps 960 --seed-count 3 --cra-readout-lr 0.10 --cra-delayed-readout-lr 0.20 --stop-on-fail

tier6-3-smoke:
	python3 experiments/tier6_lifecycle_sham_controls.py --backend mock --tasks hard_noisy_switching --regimes life4_16 --controls smoke --steps 160 --seed-count 1 --min-intact-lifecycle-events 0 --min-performance-control-wins 0 --min-fixed-max-wins 0 --min-random-replay-wins 0 --min-lineage-shuffle-detections 1 --stop-on-fail

tier6-4:
	python3 experiments/tier6_circuit_motif_causality.py --backend nest --tasks hard_noisy_switching --regimes life4_16,life8_32 --variants intact,no_feedforward,no_feedback,no_lateral,no_wta,random_graph_same_edge_count,motif_shuffled,monolithic_same_capacity --steps 960 --seed-count 3 --cra-readout-lr 0.10 --cra-delayed-readout-lr 0.20 --message-passing-steps 1 --message-context-gain 0.025 --message-prediction-mix 0.35 --stop-on-fail

tier6-4-smoke:
	python3 experiments/tier6_circuit_motif_causality.py --backend mock --tasks hard_noisy_switching --regimes life4_16 --variants smoke --steps 160 --seed-count 1 --min-intact-motif-active-steps 1 --min-motif-ablation-losses 0 --max-random-or-monolithic-dominations 1 --stop-on-fail

tier7-1a:
	python3 experiments/tier7_1a_realish_adapter_contract.py

tier7-1b:
	python3 experiments/tier7_1b_cmapss_source_data_preflight.py

tier7-1c:
	python3 experiments/tier7_1c_cmapss_fd001_scoring_gate.py

tier7-1d:
	python3 experiments/tier7_1d_cmapss_failure_analysis_adapter_repair.py

tier7-1e:
	python3 experiments/tier7_1e_cmapss_capped_readout_fairness_confirmation.py

tier7-1f:
	python3 experiments/tier7_1f_next_public_adapter_contract.py

tier7-1g:
	python3 experiments/tier7_1g_nab_source_data_scoring_preflight.py

tier7-1h:
	python3 experiments/tier7_1h_compact_nab_scoring_gate.py

tier7-1i:
	python3 experiments/tier7_1i_nab_fairness_confirmation.py

tier7-1j:
	python3 experiments/tier7_1j_nab_failure_localization.py

tier7-1k:
	python3 experiments/tier7_1k_nab_false_positive_repair.py

tier7-1l:
	python3 experiments/tier7_1l_nab_locked_policy_holdout_confirmation.py

tier7-1m:
	python3 experiments/tier7_1m_nab_closeout_mechanism_return_decision.py

tier7-4a:
	python3 experiments/tier7_4a_cost_aware_policy_action_contract.py

tier7-4b:
	python3 experiments/tier7_4b_cost_aware_policy_action_local_diagnostic.py

tier7-4c:
	python3 experiments/tier7_4c_cost_aware_policy_action_promotion_gate.py

tier7-4d:
	python3 experiments/tier7_4d_cost_aware_policy_action_heldout_contract.py

tier7-4e:
	python3 experiments/tier7_4e_cost_aware_policy_action_heldout_preflight.py

tier7-4f:
	python3 experiments/tier7_4f_cost_aware_policy_action_heldout_scoring_gate.py

tier7-4g:
	python3 experiments/tier7_4g_policy_action_confirmation_reference_separation.py

tier7-4h:
	python3 experiments/tier7_4h_policy_action_attribution_closeout.py

tier7-5a:
	python3 experiments/tier7_5a_curriculum_environment_contract.py

tier7-5b:
	python3 experiments/tier7_5b_curriculum_environment_preflight.py

tier7-5c:
	python3 experiments/tier7_5c_curriculum_environment_scoring_gate.py

tier7-5d:
	python3 experiments/tier7_5d_curriculum_environment_attribution_closeout.py

tier7-6a:
	python3 experiments/tier7_6a_long_horizon_planning_contract.py

tier7-6b:
	python3 experiments/tier7_6b_long_horizon_planning_local_diagnostic.py
