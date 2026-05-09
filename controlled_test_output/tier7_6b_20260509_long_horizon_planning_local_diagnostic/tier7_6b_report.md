# Tier 7.6b Long-Horizon Planning / Subgoal-Control Local Diagnostic

- Generated: `2026-05-09T04:16:19+00:00`
- Runner revision: `tier7_6b_long_horizon_planning_local_diagnostic_20260509_0001`
- Status: **PASS**
- Criteria: `19/19`
- Outcome: `subgoal_control_local_diagnostic_candidate_supported_requires_attribution`
- Next gate: `Tier 7.6c - Long-Horizon Planning / Subgoal-Control Attribution + Promotion Decision`

## Boundary

# Tier 7.6b Claim Boundary

- Outcome: `subgoal_control_local_diagnostic_candidate_supported_requires_attribution`
- Supported local diagnostic families: `['two_stage_delayed_goal_chain', 'key_door_goal_sequence', 'resource_budget_route_plan']`
- Local subgoal-control signal authorized: `True`
- Freeze authorized: `False`
- Hardware transfer authorized: `False`
- Broad planning claim authorized: `False`

## Authorized Claim

A bounded local software scaffold for subgoal control improved the locked Tier 7.6 planning diagnostics against reactive references, simple planning/RL baselines, sequence baselines, and destructive shams.

## Nonclaims

- This is not a promoted CRA mechanism.
- This is not a new frozen software baseline.
- This is not public usefulness proof.
- This is not hardware/native transfer evidence.
- This is not language reasoning, open-ended agency, AGI, or ASI evidence.
- This does not prove generic planning; it only supports a bounded local diagnostic and must go through attribution/promotion next.

## Reviewer-Risk Note

Because the candidate scaffold can read the synthetic context, route, memory, predictive, and confidence fields that define these generated planning tasks, a follow-up attribution gate is mandatory before promotion. The next tier must test whether the benefit survives route/key shams, reduced feature access, and held-out composition variants without smuggling terminal labels or subgoal score labels into the online policy.


## Result Snapshot

- Supported families: `3/5`
- Best non-oracle model: `dyna_q_model_based_baseline`
- Best non-oracle claim return mean: `8.232592592592592`
- Candidate claim return mean: `11.258148148148148`
- Candidate claim success mean: `0.8222222222222222`

## Criteria

| Criterion | Value | Rule | Pass | Details |
| --- | --- | --- | --- | --- |
| tier7_6a_contract_exists | `/Users/james/JKS:CRA/controlled_test_output/tier7_6a_20260509_long_horizon_planning_contract/tier7_6a_results.json` | exists | yes |  |
| tier7_6a_contract_passed | `PASS` | case-insensitive == PASS | yes |  |
| task_families_scored | `5` | == 5 | yes |  |
| seeds_scored | `[42, 43, 44]` | == [42, 43, 44] | yes |  |
| claim_splits_present | `['planning_hidden_holdout', 'planning_ood_holdout']` | hidden and ood claim splits | yes |  |
| model_inventory_complete | `19` | >= 18 | yes |  |
| baseline_inventory_complete | `10` | >= 9 including oracle | yes |  |
| sham_inventory_complete | `9` | >= 9 | yes |  |
| episode_scores_finite | `all returns/completions finite` | all finite | yes |  |
| no_future_or_subgoal_label_leakage | `0` | == 0 | yes |  |
| candidate_beats_best_non_oracle_claim_return | `3.025555555555556` | > 0 | yes | best_non_oracle=dyna_q_model_based_baseline |
| candidate_beats_best_external_with_positive_ci | `1.5796296296296297` | > 0 | yes |  |
| candidate_beats_reactive_references_by_family | `5` | >= 3 | yes | two_stage_delayed_goal_chain,key_door_goal_sequence,resource_budget_route_plan,blocked_subgoal_recovery,hierarchical_composition_holdout |
| candidate_beats_best_sham_with_positive_ci | `1.9507407407407407` | > 0 | yes |  |
| family_signals_supported | `3` | >= 3 | yes | two_stage_delayed_goal_chain,key_door_goal_sequence,resource_budget_route_plan |
| not_degenerate_action_spam | `3.7777777777777777` | 2.5 <= mean action count <= 4.5 | yes |  |
| oracle_remains_upper_bound | `2.3418518518518514` | > 0 | yes |  |
| no_freeze_or_hardware_or_broad_planning | `{'tier': 'Tier 7.6b - Long-Horizon Planning / Subgoal-Control Local Diagnostic', 'outcome': 'subgoal_control_local_diagnostic_candidate_supported_requires_attribution', 'local_subgoal_signal_authorized': True, 'supported_family_count': 3, 'supported_families': ['two_stage_delayed_goal_chain', 'key_door_goal_sequence', 'resource_budget_route_plan'], 'candidate_model': 'cra_subgoal_controller_local_scaffold', 'candidate_return_mean': 11.258148148148148, 'candidate_success_rate': 0.8222222222222222, 'best_non_oracle_model': 'dyna_q_model_based_baseline', 'best_non_oracle_return_mean': 8.232592592592592, 'best_sham_or_ablation': 'self_evaluation_disabled', 'best_sham_return_mean': 7.916666666666667, 'support_vs_best_non_oracle': {'candidate': 'cra_subgoal_controller_local_scaffold', 'baseline': 'dyna_q_model_based_baseline', 'paired_episodes': 135, 'mean_return_delta': 3.0255555555555556, 'median_return_delta': 0.0, 'return_delta_ci_low': 1.5796296296296297, 'return_delta_ci_high': 4.395925925925926, 'return_effect_size': 0.36499480490704084, 'positive_return_fraction': 0.4222222222222222, 'mean_success_delta': 0.3037037037037037, 'mean_completion_delta': 0.0734567901234568}, 'support_vs_best_sham': {'candidate': 'cra_subgoal_controller_local_scaffold', 'baseline': 'self_evaluation_disabled', 'paired_episodes': 135, 'mean_return_delta': 3.3414814814814813, 'median_return_delta': 0.0, 'return_delta_ci_low': 1.9507407407407407, 'return_delta_ci_high': 4.727777777777778, 'return_effect_size': 0.39814037804491315, 'positive_return_fraction': 0.42962962962962964, 'mean_success_delta': 0.32592592592592595, 'mean_completion_delta': 0.08456790123456791}, 'freeze_authorized': False, 'hardware_transfer_authorized': False, 'broad_planning_claim_authorized': False, 'next_gate': 'Tier 7.6c - Long-Horizon Planning / Subgoal-Control Attribution + Promotion Decision'}` | all false | yes |  |
| next_gate_selected | `Tier 7.6c - Long-Horizon Planning / Subgoal-Control Attribution + Promotion Decision` | == Tier 7.6c - Long-Horizon Planning / Subgoal-Control Attribution + Promotion Decision | yes |  |
