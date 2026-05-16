# Tier 7.5d Curriculum / Environment Score Attribution Closeout

- Generated: `2026-05-09T04:01:53+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier7_5d_20260509_curriculum_environment_attribution_closeout`
- Runner revision: `tier7_5d_curriculum_environment_attribution_closeout_20260509_0001`

## Summary

- criteria_passed: `18/18`
- outcome: `synthetic_mechanism_attribution_supported_no_freeze`
- mechanism_attribution_supported_families: `6/6`
- next_gate: `Tier 7.6a - Long-Horizon Planning / Subgoal Control Contract`
- freeze_authorized: `False`
- hardware_transfer_authorized: `False`

## Attribution Checks

| Family | Attribution Supported | Near Oracle | Reference CI Low | External CI Low | Best Sham CI Low |
| --- | --- | --- | ---: | ---: | ---: |
| generated_compositional_reuse | True | True | 0.7545077433148737 | 0.9958145696199165 | 0.7455575449926468 |
| generated_delayed_credit | True | True | 1.7609931197893223 | 0.8859858702265521 | 2.2389388358451594 |
| generated_hidden_context_reentry | True | True | 1.4418185046849912 | 0.8825835842437567 | 1.3720789787134622 |
| generated_nonstationary_switching | True | True | 0.8718215960835644 | 0.9253527617344292 | 0.8758472445256261 |
| generated_policy_action_cost | True | True | 0.7866130946719733 | 0.8878459195554992 | 0.7876172246103693 |
| generated_predictive_binding | True | True | 0.8342200601622676 | 0.65911512856936 | 0.8442101592510199 |

## Claim Decisions

| Claim | Authorized | Boundary |
| --- | --- | --- |
| Generated-family synthetic keyed/compositional mechanism signal | True | Synthetic generated-family software evidence only; requires public/real-ish confirmation before usefulness claims. |
| New software baseline freeze | False | Keep CRA_EVIDENCE_BASELINE_v2.4 as the current software baseline. |
| Broad public usefulness | False | Not authorized. |
| Hardware/native transfer | False | Not authorized. |
| AGI/ASI, language, or broad planning | False | Not authorized. |

## Route Decisions

| Route | Selected | Reason |
| --- | --- | --- |
| preserve_generated_family_signal | True | The 7.5c signal separates from external baselines, v2.2 reference, and shams on locked synthetic families. |
| do_not_freeze_v2_5 | True | No new mechanism was introduced; v2.4 remains the current frozen software baseline. |
| do_not_transfer_7_5c_to_hardware | True | The gate is synthetic software attribution, not a native mechanism migration target. |
| start_tier_7_6a_long_horizon_planning_contract | True | After curriculum/environment generation, the roadmap's next unclosed capability is long-horizon planning/subgoal control. |
| return_to_generator_tuning | False | Changing generated tasks after scoring would contaminate the locked 7.5a/7.5b evidence chain. |

## Risks

| Risk | Level | Mitigation |
| --- | --- | --- |
| generator_feature_alignment | high | Do not freeze or claim public usefulness; require public/real-ish confirmation or a harder hidden generator before stronger claims. |
| synthetic_holdout_is_not_public_benchmark | high | Use this only as mechanism-pressure evidence; route public claims through real-ish adapters and standardized benchmarks. |
| mechanism_shortcut_overclaim | medium | Carry claim as keyed/compositional attribution only; require future black-box/held-out task families before promotion. |

## Criteria

| Criterion | Value | Rule | Pass | Details |
| --- | --- | --- | --- | --- |
| tier7_5c_results_exist | `True` | must exist | yes | <repo>/controlled_test_output/tier7_5c_20260509_curriculum_environment_scoring_gate/tier7_5c_results.json |
| tier7_5c_status_pass | `PASS` | case-insensitive == PASS | yes |  |
| tier7_5c_signal_count | `6` | == 6 | yes |  |
| attribution_rows_written | `6` | == 6 | yes |  |
| all_families_attribution_supported | `6` | == attribution rows | yes |  |
| reference_separation_preserved | `6` | == 6 | yes |  |
| external_separation_preserved | `6` | == 6 | yes |  |
| sham_separation_preserved | `6` | == 6 | yes |  |
| feature_ablation_loss_preserved | `6` | == 6 | yes |  |
| near_oracle_risk_documented | `6` | == 6 and blocks overclaim | yes |  |
| risk_register_written | `3` | >= 3 | yes |  |
| claim_rows_written | `5` | >= 5 | yes |  |
| route_rows_written | `5` | >= 5 | yes |  |
| broad_public_claim_blocked | `False` | must be False | yes |  |
| freeze_blocked | `False` | must be False | yes |  |
| hardware_transfer_blocked | `False` | must be False | yes |  |
| next_gate_selected | `Tier 7.6a - Long-Horizon Planning / Subgoal Control Contract` | == Tier 7.6a - Long-Horizon Planning / Subgoal Control Contract | yes |  |
| sham_controls_source_loaded | `18` | >= 18 | yes |  |
