# Tier 7.4a Cost-Aware Policy/Action Selection Contract

- Generated: `2026-05-09T00:13:11+00:00`
- Runner revision: `tier7_4a_cost_aware_policy_action_contract_20260509_0001`
- Status: **PASS**
- Criteria: `13/13`
- Next gate: `Tier 7.4b - Cost-Aware Policy/Action Local Diagnostic`

## Question

Can CRA learn a general policy/action layer that converts internal state, confidence, memory, and prediction error into actions under asymmetric costs, instead of relying on adapter-specific thresholds?

## Pass Criteria

- policy/action gate improves expected utility versus fixed thresholds and trivial policies
- benefit survives seeds and at least two task families
- confidence/memory/recurrent ablations lose when used by the policy
- shuffled reward/cost and wrong-context controls do not match intact CRA
- no test-label threshold tuning or leakage
- compact regression over v2.3 guardrails stays green before promotion

## Baselines

- always_abstain
- always_act
- fixed_train_only_threshold
- rolling_zscore_cost_threshold
- online_logistic_policy
- online_perceptron_policy
- reservoir_policy_readout
- random_policy
- oracle_policy_upper_bound_nonclaim

## Controls And Ablations

- shuffled_reward_cost
- random_confidence
- confidence_disabled
- memory_disabled
- recurrent_state_disabled
- policy_learning_disabled
- wrong_context_key
- label_leakage_guard

## Boundary

Tier 7.4a is a contract-only gate for a general cost-aware policy/action mechanism. It is not a scoring run, not a promoted mechanism, not a baseline freeze, and not hardware/native transfer.
