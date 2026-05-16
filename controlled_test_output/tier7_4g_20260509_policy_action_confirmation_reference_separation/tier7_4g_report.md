# Tier 7.4g Held-Out Policy/Action Confirmation + Reference Separation

- Generated: `2026-05-09T03:03:34+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier7_4g_20260509_policy_action_confirmation_reference_separation`
- Runner revision: `tier7_4g_policy_action_confirmation_reference_separation_20260509_0001`

## Claim Boundary

- This is a software held-out action-cost confirmation gate.
- It reuses the locked Tier 7.4f cost model, policies, score rows, baselines, and shams.
- It does not tune costs, thresholds, policies, or held-out splits.
- It does not authorize a new baseline freeze, hardware/native transfer, broad public usefulness, planning, language, AGI, or ASI claims.

## Summary

- criteria_passed: `20/20`
- outcome: `cmapss_external_signal_confirmed_reference_not_separated_nab_failed`
- narrow_cmapss_external_signal_authorized: `True`
- incremental_v2_4_reference_claim_authorized: `False`
- broad_public_usefulness_authorized: `False`
- freeze_authorized: `False`
- hardware_transfer_authorized: `False`
- next_gate: `Tier 7.4h - Policy/Action Attribution Closeout / Mechanism Return Decision`

## Confirmation Checks

| Comparison | CI low | CI high | Mean delta | Positive CI confirmed |
| --- | ---: | ---: | ---: | --- |
| cmapss_candidate_vs_best_external | 56.89735573832698 | 159.83190533971052 | 107.24571221002218 | True |
| cmapss_candidate_vs_v2_2_reference | -12.387676684452819 | 16.42514109274918 | 2.46990147262258 | False |
| cmapss_candidate_vs_best_sham | 373.38894337405304 | 593.2954387836684 | 479.96795608024513 | True |
| nab_candidate_vs_best_external | -2.477512243261454 | 1.6136596936133127 | -0.4077008431630544 | False |
| nab_candidate_vs_v2_2_reference | -1.6771667545028228 | 1.4595147482102973 | -0.021051688597168067 | False |

## NAB Failure Analysis

- failure_class_vs_ewma: `event_coverage_gap_vs_ewma`
- failure_class_vs_v2_2: `event_coverage_gap_vs_v2_2`
- candidate_minus_ewma: `-0.407700843163056`
- candidate_minus_v2_2: `-0.02105168859716855`
- heldout_tuning_performed: `False`

## Criteria

| Criterion | Value | Rule | Pass | Details |
| --- | --- | --- | --- | --- |
| tier7_4f_results_exist | `True` | must exist | yes | <repo>/controlled_test_output/tier7_4f_20260509_cost_aware_policy_action_heldout_scoring_gate/tier7_4f_results.json |
| tier7_4f_status_pass | `pass` | case-insensitive == PASS | yes |  |
| score_rows_present | `3360` | > 0 | yes | <repo>/controlled_test_output/tier7_4f_20260509_cost_aware_policy_action_heldout_scoring_gate/tier7_4f_score_rows.csv |
| model_summary_present | `20` | > 0 | yes | <repo>/controlled_test_output/tier7_4f_20260509_cost_aware_policy_action_heldout_scoring_gate/tier7_4f_model_summary.csv |
| family_decisions_present | `2` | >= 2 | yes | <repo>/controlled_test_output/tier7_4f_20260509_cost_aware_policy_action_heldout_scoring_gate/tier7_4f_family_decisions.csv |
| locked_cost_model_present | `10` | > 0 | yes | <repo>/controlled_test_output/tier7_4f_20260509_cost_aware_policy_action_heldout_scoring_gate/tier7_4f_cost_model.csv |
| heldout_tuning_performed | `False` | must remain False | yes | 7.4g only reuses locked 7.4f scores. |
| cmapss_candidate_rank_first | `1` | == 1 | yes |  |
| cmapss_family_previously_confirmed | `True` | == True | yes |  |
| cmapss_external_positive_ci | `56.89735573832698` | > 0 | yes |  |
| cmapss_sham_positive_ci | `373.38894337405304` | > 0 | yes |  |
| cmapss_reference_separation_evaluated | `300` | > 0 | yes |  |
| cmapss_reference_overclaim_blocked | `False` | must be False for no incremental claim | yes |  |
| cmapss_partition_checks_written | `16` | > 0 | yes |  |
| nab_family_nonconfirmation_preserved | `False` | == False | yes |  |
| nab_external_failure_confirmed_or_preserved | `-0.4077008431630544` | <= 0 or CI not positive | yes |  |
| nab_failure_classified | `event_coverage_gap_vs_ewma` | non-empty | yes |  |
| nab_category_analysis_written | `6` | > 0 | yes |  |
| freeze_not_authorized | `False` | must remain False | yes |  |
| hardware_transfer_not_authorized | `False` | must remain False | yes |  |

## Interpretation

Tier 7.4g confirms the narrow C-MAPSS external/sham action-cost signal from Tier 7.4f, but it also preserves the most important limit: the v2.4 candidate still does not separate from the prior v2.2 CRA reference with a positive paired confidence interval. NAB remains a non-confirmation, with the failure analysis pointing to event-coverage and utility tradeoff gaps rather than a held-out scoring bug. The correct next move is attribution/closeout, not a freeze or hardware transfer.
