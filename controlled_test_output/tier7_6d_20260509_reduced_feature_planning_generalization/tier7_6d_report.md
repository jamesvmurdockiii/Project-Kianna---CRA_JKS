# Tier 7.6d Reduced-Feature Planning Generalization / Task Repair

- Generated: `2026-05-09T04:40:13+00:00`
- Runner revision: `tier7_6d_reduced_feature_planning_generalization_20260509_0001`
- Status: **PASS**
- Criteria: `18/18`
- Outcome: `reduced_feature_planning_signal_supported_requires_promotion_gate`
- Next gate: `Tier 7.6e - Planning/Subgoal-Control Promotion + Compact Regression Gate`

## Criteria

| Criterion | Value | Rule | Pass | Details |
| --- | --- | --- | --- | --- |
| tier7_6c_prerequisite_exists | `<repo>/controlled_test_output/tier7_6c_20260509_long_horizon_planning_attribution_closeout/tier7_6c_results.json` | exists | yes |  |
| tier7_6c_prerequisite_passed | `PASS` | == PASS | yes |  |
| families_scored | `5` | == 5 | yes |  |
| seeds_scored | `[42, 43, 44]` | == [42, 43, 44] | yes |  |
| reduced_feature_claim_splits_present | `['planning_hidden_holdout', 'planning_ood_holdout']` | hidden and ood | yes |  |
| model_inventory_complete | `19` | >= 19 | yes |  |
| direct_raw_key_access_blocked | `True` | must be true | yes |  |
| score_metrics_finite | `all claim returns finite` | all finite | yes |  |
| candidate_beats_best_non_oracle | `4.490606060606061` | > 0 | yes | best=dyna_q_model_based_baseline |
| candidate_best_non_oracle_ci_positive | `3.354848484848485` | > 0 | yes |  |
| candidate_beats_best_sham | `3.9866666666666672` | > 0 | yes | best_sham=self_evaluation_disabled |
| candidate_best_sham_ci_positive | `2.860909090909091` | > 0 | yes |  |
| family_signals_supported | `4` | >= 4 | yes | two_stage_delayed_goal_chain,resource_budget_route_plan,blocked_subgoal_recovery,hierarchical_composition_holdout |
| prior_weak_families_repaired | `True` | blocked + hierarchical supported | yes |  |
| not_degenerate_action_spam | `3.812121212121212` | 2.5 <= mean action count <= 4.5 | yes |  |
| oracle_remains_upper_bound | `2.1393939393939387` | > 0 | yes |  |
| no_freeze_or_hardware_transfer | `{'tier': 'Tier 7.6d - Reduced-Feature Planning Generalization / Task Repair', 'status': 'PASS', 'outcome': 'reduced_feature_planning_signal_supported_requires_promotion_gate', 'reduced_feature_signal_authorized': True, 'promotion_gate_authorized': True, 'supported_family_count': 4, 'supported_families': ['two_stage_delayed_goal_chain', 'resource_budget_route_plan', 'blocked_subgoal_recovery', 'hierarchical_composition_holdout'], 'repaired_prior_weak_families_supported': True, 'candidate_return_mean': 11.460606060606061, 'candidate_success_rate': 0.806060606060606, 'best_non_oracle_model': 'dyna_q_model_based_baseline', 'best_non_oracle_return_mean': 6.97, 'best_sham_or_ablation': 'self_evaluation_disabled', 'best_sham_return_mean': 7.473939393939394, 'support_vs_best_non_oracle': {'candidate': 'cra_reduced_feature_subgoal_controller', 'baseline': 'dyna_q_model_based_baseline', 'paired_episodes': 165, 'mean_return_delta': 4.49060606060606, 'median_return_delta': 7.45, 'return_delta_ci_low': 3.354848484848485, 'return_delta_ci_high': 5.587575757575758, 'return_effect_size': 0.5988598586869635, 'positive_return_fraction': 0.5454545454545454, 'mean_success_delta': 0.41818181818181815, 'mean_completion_delta': 0.1196969696969697}, 'support_vs_best_sham': {'candidate': 'cra_reduced_feature_subgoal_controller', 'baseline': 'self_evaluation_disabled', 'paired_episodes': 165, 'mean_return_delta': 3.986666666666667, 'median_return_delta': 0.0, 'return_delta_ci_low': 2.860909090909091, 'return_delta_ci_high': 5.073030303030303, 'return_effect_size': 0.5380848323955474, 'positive_return_fraction': 0.4727272727272727, 'mean_success_delta': 0.3515151515151515, 'mean_completion_delta': 0.11212121212121212}, 'freeze_authorized': False, 'hardware_transfer_authorized': False, 'broad_planning_claim_authorized': False, 'next_gate': 'Tier 7.6e - Planning/Subgoal-Control Promotion + Compact Regression Gate'}` | both false | yes |  |
| next_gate_selected | `Tier 7.6e - Planning/Subgoal-Control Promotion + Compact Regression Gate` | == Tier 7.6e - Planning/Subgoal-Control Promotion + Compact Regression Gate | yes |  |

# Tier 7.6d Claim Boundary

- Outcome: `reduced_feature_planning_signal_supported_requires_promotion_gate`
- Reduced-feature signal authorized: `True`
- Promotion gate authorized: `True`
- Freeze authorized: `False`
- Hardware transfer authorized: `False`

## Authorized Claim

The planning/subgoal-control signal survives a reduced-feature, aliased-context diagnostic with stricter blocked-subgoal and hierarchical-composition pressure.

## Nonclaims

- Not a promoted planning mechanism by itself.
- Not a v2.5 baseline freeze.
- Not public usefulness proof.
- Not hardware/native transfer evidence.
- Not general planning, language reasoning, open-ended agency, AGI, or ASI.

