# Tier 5.18 Self-Evaluation / Metacognitive Monitoring Findings

- Generated: `2026-04-29T22:36:19+00:00`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail`
- Tasks: `ambiguous_cue, ood_context_insertion, memory_corruption, hidden_regime_mismatch, module_routing_uncertainty`
- Seeds: `[42, 43, 44]`

Tier 5.18 tests whether a CRA monitor can estimate reliability before feedback and whether using that signal improves behavior under ambiguity, OOD insertion, memory corruption, hidden-regime mismatch, and routing uncertainty.

## Claim Boundary

- Noncanonical software diagnostic evidence only.
- Non-oracle monitors do not use outcomes/rewards before emitting confidence or uncertainty.
- This is operational reliability monitoring, not consciousness, self-awareness, introspection, language, planning, AGI, hardware evidence, or a v2.1 freeze.
- A future Tier 5.18c promotion/regression gate is required before any v2.1 baseline lock.

## Summary

- expected_runs: `150`
- observed_runs: `150`
- candidate_min_primary_error_auroc: `0.986637`
- candidate_min_hazard_detection_auroc: `0.999055`
- candidate_max_brier_primary_correct: `0.0604305`
- candidate_max_ece_primary_correct: `0.152803`
- candidate_min_uncertainty_hazard_minus_normal: `0.274334`
- candidate_min_bad_action_avoidance: `0.763434`
- min_accuracy_edge_vs_v2_0: `0.253241`
- min_accuracy_edge_vs_monitor_only: `0.253241`
- min_accuracy_edge_vs_best_non_oracle: `0.250463`
- outcome_leakage_runs: `0`
- pre_feedback_monitor_failures: `0`

## Comparisons

| Task | Candidate acc | v2.0 acc | Monitor-only acc | Random acc | Shuffled acc | Best non-oracle edge | Error AUROC | Hazard AUROC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ambiguous_cue | 0.920833 | 0.667593 | 0.667593 | 0.669907 | 0.67037 | 0.250463 | 0.991547 | 0.999453 |
| hidden_regime_mismatch | 0.999537 | 0.668056 | 0.668056 | 0.66713 | 0.673611 | 0.325926 | 0.99102 | 1 |
| memory_corruption | 1 | 0.667593 | 0.667593 | 0.669907 | 0.669907 | 0.330093 | 0.9923 | 1 |
| module_routing_uncertainty | 0.999537 | 0.668056 | 0.668056 | 0.66713 | 0.673611 | 0.325926 | 0.990916 | 1 |
| ood_context_insertion | 1 | 0.667593 | 0.667593 | 0.669907 | 0.669907 | 0.330093 | 0.99226 | 1 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| task/variant/seed matrix completed | `150` | `== 150` | yes |  |
| frozen v2.0 baseline artifact exists | `/Users/james/JKS:CRA/baselines/CRA_EVIDENCE_BASELINE_v2.0.json` | `exists True` | yes |  |
| non-oracle monitors do not use outcomes | `0` | `== 0` | yes |  |
| monitor values are computed before feedback | `0` | `== 0` | yes |  |
| candidate predicts primary-path future errors | `0.986637` | `>= 0.78` | yes |  |
| candidate detects hazard/OOD/mismatch state | `0.999055` | `>= 0.78` | yes |  |
| candidate confidence is calibrated by Brier score | `0.0604305` | `<= 0.2` | yes |  |
| candidate confidence calibration error is bounded | `0.152803` | `<= 0.16` | yes |  |
| candidate uncertainty rises under hazard | `0.274334` | `>= 0.2` | yes |  |
| candidate avoids bad primary-path actions under detected risk | `0.763434` | `>= 0.7` | yes |  |
| candidate improves behavior vs v2.0 no-monitor | `0.253241` | `>= 0.06` | yes |  |
| monitor must be behaviorally used, not just reported | `0.253241` | `>= 0.06` | yes |  |
| confidence-disabled control loses | `0.253241` | `>= 0.06` | yes |  |
| random-confidence control loses | `0.250926` | `>= 0.03` | yes |  |
| time-shuffled confidence control loses | `0.250463` | `>= 0.03` | yes |  |
| anti-confidence control loses | `0.279167` | `>= 0.08` | yes |  |
| candidate beats best non-oracle control | `0.250463` | `>= 0.02` | yes |  |
| candidate calibration beats random/shuffled monitors | `0.247087` | `>= 0.04` | yes |  |
| candidate AUROC beats random/shuffled monitors | `0.470451` | `>= 0.12` | yes |  |

## Artifacts

- `ambiguous_cue_v2_0_no_monitor_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/ambiguous_cue_v2_0_no_monitor_seed42_timeseries.csv`
- `ambiguous_cue_self_eval_gated_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/ambiguous_cue_self_eval_gated_seed42_timeseries.csv`
- `ambiguous_cue_time_shuffled_confidence_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/ambiguous_cue_time_shuffled_confidence_seed42_timeseries.csv`
- `ood_context_insertion_v2_0_no_monitor_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/ood_context_insertion_v2_0_no_monitor_seed42_timeseries.csv`
- `ood_context_insertion_self_eval_gated_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/ood_context_insertion_self_eval_gated_seed42_timeseries.csv`
- `ood_context_insertion_time_shuffled_confidence_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/ood_context_insertion_time_shuffled_confidence_seed42_timeseries.csv`
- `memory_corruption_v2_0_no_monitor_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/memory_corruption_v2_0_no_monitor_seed42_timeseries.csv`
- `memory_corruption_self_eval_gated_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/memory_corruption_self_eval_gated_seed42_timeseries.csv`
- `memory_corruption_time_shuffled_confidence_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/memory_corruption_time_shuffled_confidence_seed42_timeseries.csv`
- `hidden_regime_mismatch_v2_0_no_monitor_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/hidden_regime_mismatch_v2_0_no_monitor_seed42_timeseries.csv`
- `hidden_regime_mismatch_self_eval_gated_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/hidden_regime_mismatch_self_eval_gated_seed42_timeseries.csv`
- `hidden_regime_mismatch_time_shuffled_confidence_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/hidden_regime_mismatch_time_shuffled_confidence_seed42_timeseries.csv`
- `module_routing_uncertainty_v2_0_no_monitor_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/module_routing_uncertainty_v2_0_no_monitor_seed42_timeseries.csv`
- `module_routing_uncertainty_self_eval_gated_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/module_routing_uncertainty_self_eval_gated_seed42_timeseries.csv`
- `module_routing_uncertainty_time_shuffled_confidence_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/module_routing_uncertainty_time_shuffled_confidence_seed42_timeseries.csv`
- `summary_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/tier5_18_summary.csv`
- `aggregates_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/tier5_18_aggregates.csv`
- `comparisons_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/tier5_18_comparisons.csv`
- `fairness_contract_json`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/tier5_18_fairness_contract.json`
- `accuracy_edges_png`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/tier5_18_accuracy_edges.png`
- `monitor_auroc_matrix_png`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/tier5_18_monitor_auroc_matrix.png`
- `results_json`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18c_20260429_221045/tier5_18_self_evaluation_guardrail/tier5_18_results.json`
