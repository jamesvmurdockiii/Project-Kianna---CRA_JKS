# Tier 6.2a Targeted Hard-Task Validation Over v2.3

- Generated: `2026-05-08T20:29:19+00:00`
- Runner revision: `tier6_2a_targeted_usefulness_validation_20260508_0001`
- Status: **PASS**
- Criteria: `12/12`
- Outcome: `v2_3_partial_regime_signal_next_needs_failure_specific_mechanism_or_7_1_probe`

## Claim Boundary

Tier 6.2a is a software-only targeted diagnostic over frozen v2.3. It tests harder controlled regimes to select the next mechanism or real-ish adapter direction. It is not public usefulness proof, not a baseline freeze, not hardware/native transfer, not topology-specific recurrence, and not AGI/ASI evidence.

## Classification

- v2.3 best task count: `1`
- v2.3 beats v2.2 task count: `1`
- v2.3 beats simple online controls task count: `1`
- v2.3 sham-separated task count: `3`
- ESN-dominated task count: `0`
- Aggregate v2.3 geomean MSE: `0.17604715537423876`
- Aggregate v2.2 geomean MSE: `0.15892013746238234`
- Aggregate ESN geomean MSE: `0.4224303829071217`
- Recommendation: Use the per-task failures to choose one next general mechanism or a narrow Tier 7.1 adapter; keep v2.3 as the frozen baseline.

## Per-Task Profile

| Task | Best model | v2.3 rank | v2.3 MSE | v2.2/v2.3 | lag/v2.3 | reservoir/v2.3 | ESN/v2.3 | sham-min/v2.3 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| variable_delay_multi_cue | v2_3_generic_bounded_recurrent_state | 1 | 0.5090571841935101 | 1.0478091792629616 | 1.0884811650271147 | 1.332978344270883 | 1.5972381154852222 | 1.0193455645320633 |
| hidden_context_reentry | fixed_random_reservoir_online_control | 4 | 0.13114242720796349 | 0.9553021591540483 | 2.4651089754948736 | 0.45675574996700385 | 7.966557140717083 | 0.9780025799500737 |
| concept_drift_stream | v2_2_fading_memory_reference | 4 | 0.3461047991105859 | 0.7455138119160603 | 1.538000210040463 | 0.8966871156795898 | 2.682769532134505 | 0.9931418365626785 |
| anomaly_detection_stream | fixed_random_reservoir_online_control | 4 | 0.6734007962411387 | 0.9711841508423017 | 1.1835741131364041 | 0.8165406539608763 | 0.8798940249239252 | 1.0103979845108382 |
| delayed_control_proxy | lag_only_online_lms_control | 3 | 0.01116466689409419 | 0.8191565642095788 | 0.4385418567692262 | 7.413914960058495 | 2.6094298114320793 | 1.0096382903575274 |

## Aggregate Summary

| Model | Rank | Geomean MSE mean | Geomean NMSE mean | Worst seed geomean MSE |
| --- | ---: | ---: | ---: | ---: |
| v2_2_fading_memory_reference | 1 | 0.15892013746238234 | 0.16215136255400575 | 0.16535851958290065 |
| v2_3_generic_bounded_recurrent_state | 2 | 0.17604715537423876 | 0.179783551797055 | 0.18885489161996596 |
| v2_3_state_reset_ablation | 3 | 0.17626969871692108 | 0.1800053587230217 | 0.1889271158630906 |
| lag_only_online_lms_control | 4 | 0.2055968384080941 | 0.20939300510827777 | 0.21687209087981454 |
| fixed_random_reservoir_online_control | 5 | 0.22089786655426447 | 0.2257803411810787 | 0.24437200396467706 |
| fixed_esn_train_prefix_ridge_baseline | 6 | 0.4224303829071217 | 0.4300306294729567 | 0.4511888384728922 |
| v2_3_shuffled_state_sham | 7 | 0.9704802050983504 | 0.9884264679021232 | 0.9969860025919512 |
| v2_3_no_update_ablation | 8 | 0.9899925447331018 | 1.007774683178406 | 1.0174528952166229 |
| v2_3_shuffled_target_control | 9 | 1.0154879736291191 | 1.0334672068184265 | 1.0481035423422875 |

## Interpretation Rule

- This tier cannot make a paper usefulness claim by itself.
- It cannot freeze a new baseline and cannot authorize hardware transfer.
- If v2.3 shows a regime-specific signal, validate that regime in Tier 7.1.
- If v2.3 loses broadly, select the next planned general mechanism from the measured failure class.

