# Tier 7.4b Cost-Aware Policy/Action Local Diagnostic

- Generated: `2026-05-09T01:21:32+00:00`
- Runner revision: `tier7_4b_cost_aware_policy_action_local_diagnostic_20260509_0001`
- Status: **PASS**
- Criteria: `15/15`
- Outcome: `cost_aware_policy_candidate_requires_regression`
- Next gate: `Tier 7.4c - Cost-Aware Policy/Action Promotion + Compact Regression Gate`

## Claim Boundary

Tier 7.4b is a local software diagnostic for the predeclared cost-aware policy/action gate. It can justify a compact promotion and regression gate, but it is not a promoted mechanism, not a baseline freeze, not public usefulness proof, and not hardware/native transfer.

## Result Snapshot

- v2.3 expected utility mean: `18.046296296296294`
- v2.3 window recall mean: `0.9865196078431373`
- v2.3 FP cost / 1000 mean: `3.489715986424665`
- Best non-oracle model: `v2_3_cost_aware_policy`
- Best external baseline: `fixed_train_only_threshold`
- Task-family wins versus best external baseline: `2`

## Method Note

The diagnostic uses a conservative action-confidence floor because the measured failure after the NAB chain was false-positive/action cost pressure. A permissive point-utility-only action threshold over-acted during local runner shakeout; the final audited gate therefore requires high-confidence action before spending an alert/act decision.

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 7.4a exists | `/Users/james/JKS:CRA/controlled_test_output/tier7_4a_20260509_cost_aware_policy_action_contract/tier7_4a_results.json` | exists | yes |
| Tier 7.4a passed | `pass` | == pass | yes |
| task families covered | `['synthetic_alarm_cost_stream', 'delayed_action_consequence', 'hidden_context_action_switch']` | >= 3 | yes |
| seeds covered | `[42, 43, 44]` | == [42, 43, 44] | yes |
| external baselines covered | `['fixed_train_only_threshold', 'rolling_zscore_cost_threshold', 'always_abstain', 'always_act', 'online_logistic_policy', 'online_perceptron_policy', 'reservoir_policy_readout', 'random_policy']` | >= 8 | yes |
| shams and ablations covered | `['confidence_disabled_ablation', 'random_confidence_ablation', 'memory_disabled_ablation', 'recurrent_state_disabled_ablation', 'policy_learning_disabled_ablation', 'shuffled_reward_cost_control', 'wrong_context_key_control']` | >= 7 | yes |
| no test-label threshold tuning | `fixed baseline uses train-only threshold calibration; v2.3 uses a locked conservative action floor plus online delayed feedback only` | documented | yes |
| metrics finite | `all scored rows finite` | all finite | yes |
| v2.3 policy is best non-oracle | `v2_3_cost_aware_policy` | == v2_3_cost_aware_policy | yes |
| v2.3 beats best external baseline | `12.121913580246913` | > 0 | yes |
| v2.3 wins at least two task families | `2` | >= 2 | yes |
| v2.3 beats shams and ablations | `2.9435185185185144` | > 0 | yes |
| not degenerate no-action | `{'action_rate': 0.0837962962962963, 'window_recall': 0.9865196078431373}` | 0.01 <= action_rate <= 0.35 and recall >= 0.65 | yes |
| oracle remains upper bound nonclaim | `4.638888888888889` | > 0 | yes |
| no freeze or hardware transfer authorized | `{'outcome': 'cost_aware_policy_candidate_requires_regression', 'best_non_oracle_model': 'v2_3_cost_aware_policy', 'best_non_oracle_expected_utility_mean': 18.046296296296294, 'best_external_baseline': 'fixed_train_only_threshold', 'best_external_expected_utility_mean': 5.924382716049381, 'best_sham_or_ablation': 'random_confidence_ablation', 'best_sham_expected_utility_mean': 15.10277777777778, 'task_family_wins_vs_external': 2, 'next_gate': 'Tier 7.4c - Cost-Aware Policy/Action Promotion + Compact Regression Gate', 'freeze_authorized': False, 'hardware_transfer_authorized': False}` | both false | yes |

## Boundary

This local diagnostic can authorize a compact promotion/regression gate, but it does not freeze a new baseline and does not authorize hardware transfer.
