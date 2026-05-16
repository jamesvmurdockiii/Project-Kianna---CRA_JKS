# Tier 7.5c Curriculum / Environment Generator Scoring Gate

- Generated: `2026-05-09T03:48:19+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier7_5c_20260509_curriculum_environment_scoring_gate`
- Runner revision: `tier7_5c_curriculum_environment_scoring_gate_20260509_0001`

## Boundary

Software generated-task scoring only. Hidden labels are opened only inside offline scoring. This gate does not freeze a new baseline or authorize hardware/native transfer.

## Summary

- criteria_passed: `17/17`
- outcome: `generated_family_signal_confirmed_requires_attribution_gate`
- confirmed_generated_families: `6`
- next_gate: `Tier 7.5d - Curriculum / Environment Score Attribution + Promotion Decision`

## Family Decisions

| Family | Signal Confirmed | Candidate MSE | Best External | Best External MSE | Best Sham | Best Sham MSE |
| --- | --- | ---: | --- | ---: | --- | ---: |
| generated_compositional_reuse | True | 6.315816584181984e-08 | online_logistic_or_perceptron | 1.5307603053664254 | no_key_ablation | 0.995672382918088 |
| generated_delayed_credit | True | 7.976200093199989e-08 | lag_ridge_or_ar | 1.1959849180606592 | target_shuffle_sham | 3.633602188436202 |
| generated_hidden_context_reentry | True | 7.16904797315816e-08 | online_logistic_or_perceptron | 1.3560483055364048 | key_shuffle_sham | 2.6822101446914584 |
| generated_nonstationary_switching | True | 4.53962574088991e-08 | online_logistic_or_perceptron | 1.458368206824871 | no_key_ablation | 1.3012653043156435 |
| generated_policy_action_cost | True | 2.2472470121056717e-08 | lag_ridge_or_ar | 1.4329507515050182 | no_key_ablation | 1.0081263175608837 |
| generated_predictive_binding | True | 3.6516177224237455e-08 | lag_ridge_or_ar | 1.204803181791696 | no_key_ablation | 1.2326965325884607 |

## Criteria

| Criterion | Value | Rule | Pass | Details |
| --- | --- | --- | --- | --- |
| tier7_5b_prerequisite_exists | `True` | must exist | yes | <repo>/controlled_test_output/tier7_5b_20260509_curriculum_environment_preflight/tier7_5b_results.json |
| tier7_5b_prerequisite_passed | `PASS` | case-insensitive == PASS | yes |  |
| stream_rows_loaded | `384` | == 384 | yes |  |
| split_manifest_loaded | `24` | >= 24 | yes |  |
| baseline_compatibility_loaded | `54` | >= 50 | yes |  |
| offline_hashes_match_preflight | `384` | == stream rows | yes |  |
| score_rows_written | `2720` | > 0 | yes |  |
| summary_rows_written | `136` | > 0 | yes |  |
| family_decisions_written | `6` | == 6 | yes |  |
| statistical_support_written | `18` | >= 18 | yes |  |
| sample_efficiency_written | `120` | > 0 | yes |  |
| sham_controls_written | `18` | >= 18 | yes |  |
| hidden_label_opening_offline_only | `1632` | > 0 | yes |  |
| generated_family_signal_count | `6` | >= 1 for generated-family signal | yes |  |
| broad_public_claim_blocked | `False` | must be False | yes |  |
| freeze_blocked | `False` | must be False | yes |  |
| hardware_transfer_blocked | `False` | must be False | yes |  |
