# Tier 7.4d Cost-Aware Policy/Action Held-Out/Public Usefulness Contract

- Generated: `2026-05-09T02:11:26+00:00`
- Runner revision: `tier7_4d_cost_aware_policy_action_heldout_contract_20260509_0001`
- Status: **PASS**
- Criteria: `20/20`
- Next gate: `Tier 7.4e - Cost-Aware Policy/Action Held-Out Scoring Preflight`

## Boundary

Tier 7.4d is a pre-registration contract. It authorizes a later held-out scoring preflight/gate, but it does not score v2.4, freeze a new baseline, claim public usefulness, or authorize hardware/native policy transfer.

## Question

Does the frozen v2.4 cost-aware policy/action layer preserve a measurable utility advantage on external or held-out action-cost tasks without threshold tuning, leakage, or same-subset policy selection?

## Primary Held-Out Families

### nab_heldout_alarm_action_cost

- Kind: `public_realish_primary`
- Source: Numenta Anomaly Benchmark pinned by Tier 7.1g
- Held-out rule: use streams/categories not used to choose same-subset NAB policies
- Claim role: public streaming alarm/action usefulness candidate

### cmapss_maintenance_action_cost

- Kind: `public_realish_primary`
- Source: NASA C-MAPSS FD001 source audited by Tier 7.1b
- Held-out rule: train/calibrate on train units only; test actions emitted before RUL feedback
- Claim role: public predictive-maintenance action usefulness candidate

### standard_dynamical_action_cost

- Kind: `standardized_secondary`
- Source: locked Mackey-Glass, Lorenz, and NARMA10 streams from the Tier 7.0 scoreboard
- Held-out rule: use locked train/calibration/test windows; no retuning on test windows
- Claim role: standardized regression-to-action diagnostic, not public usefulness alone

### heldout_synthetic_policy_stress

- Kind: `diagnostic_only`
- Source: predeclared hidden-context/delayed-action local stressors
- Held-out rule: locked seeds and task parameters before scoring
- Claim role: mechanism localization only; cannot support public usefulness by itself

## Pass Criteria

- v2.4 beats or complements the strongest reproduced baseline on the primary utility metric for at least one public/real-ish held-out family.
- The result is not explained by fixed train-only thresholds, rolling z-score, reservoir/ESN policy, always-act, or always-abstain controls.
- Shuffled cost, random confidence, confidence-disabled, memory-disabled, and recurrent-state-disabled controls lose on the claimed family.
- No-action and always-action collapse are explicitly ruled out by action-rate and recall/precision guards.
- Bootstrap confidence intervals or paired effect sizes support the claimed utility delta on the held-out family.
- No leakage, same-subset policy selection, or test-label threshold tuning is detected.

## Fail Criteria

- A simple fixed threshold, rolling z-score, lag/ridge, or reservoir/ESN policy wins the held-out public family.
- v2.4 wins only on private/synthetic diagnostics and not on any public/real-ish held-out family.
- Any sham or ablation matches the intact v2.4 result on the claimed family.
- The policy collapses into abstain/wait or always-act behavior while gaming utility.
- The score requires threshold or cost tuning on the held-out/test subset.
- Public data, split, or label-separation artifacts are missing or unverifiable.

## Baselines

- always_abstain_or_wait
- always_act_or_alert
- fixed_train_only_threshold
- rolling_zscore_policy
- ewma_mad_residual_policy
- lag_ridge_policy
- online_logistic_policy
- online_perceptron_policy
- reservoir_or_esn_policy_readout
- small_gru_sequence_policy_if_budget_allows
- random_policy
- oracle_policy_upper_bound_nonclaim

## Shams And Ablations

- shuffled_cost_or_reward
- key_label_permuted_cost
- random_confidence
- confidence_disabled
- memory_disabled
- recurrent_state_disabled
- policy_learning_disabled
- wrong_context_key
- no_action_cost_ablation
- always_action_collapse_guard
- test_label_leakage_guard

## Nonclaims

- not a scoring run
- not public usefulness proof
- not broad anomaly or predictive-maintenance superiority
- not a baseline freeze
- not hardware/native transfer
- not long-horizon planning
- not language
- not AGI/ASI evidence
