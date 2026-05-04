# Tier 5.18 Self-Evaluation / Metacognitive Monitoring Findings

- Generated: `2026-04-29T21:27:23+00:00`
- Status: **FAIL**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721`
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
- candidate_min_hazard_detection_auroc: `0.995377`
- candidate_max_brier_primary_correct: `0.129963`
- candidate_max_ece_primary_correct: `0.287761`
- candidate_min_uncertainty_hazard_minus_normal: `0.265778`
- candidate_min_bad_action_avoidance: `0.130774`
- min_accuracy_edge_vs_v2_0: `0.0435185`
- min_accuracy_edge_vs_monitor_only: `0.0435185`
- min_accuracy_edge_vs_best_non_oracle: `-0.0921296`
- outcome_leakage_runs: `0`
- pre_feedback_monitor_failures: `0`

## Comparisons

| Task | Candidate acc | v2.0 acc | Monitor-only acc | Random acc | Shuffled acc | Best non-oracle edge | Error AUROC | Hazard AUROC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ambiguous_cue | 0.711111 | 0.667593 | 0.667593 | 0.744907 | 0.672222 | -0.0921296 | 0.988404 | 0.996375 |
| hidden_regime_mismatch | 0.899537 | 0.668056 | 0.668056 | 0.744444 | 0.709722 | 0.087963 | 0.99102 | 1 |
| memory_corruption | 0.866667 | 0.667593 | 0.667593 | 0.744907 | 0.696759 | 0.0634259 | 0.9923 | 1 |
| module_routing_uncertainty | 0.879167 | 0.668056 | 0.668056 | 0.744444 | 0.707407 | 0.0675926 | 0.990916 | 1 |
| ood_context_insertion | 0.865278 | 0.667593 | 0.667593 | 0.744907 | 0.701852 | 0.062037 | 0.99226 | 1 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| task/variant/seed matrix completed | `150` | `== 150` | yes |  |
| frozen v2.0 baseline artifact exists | `/Users/james/JKS:CRA/baselines/CRA_EVIDENCE_BASELINE_v2.0.json` | `exists True` | yes |  |
| non-oracle monitors do not use outcomes | `0` | `== 0` | yes |  |
| monitor values are computed before feedback | `0` | `== 0` | yes |  |
| candidate predicts primary-path future errors | `0.986637` | `>= 0.78` | yes |  |
| candidate detects hazard/OOD/mismatch state | `0.995377` | `>= 0.78` | yes |  |
| candidate confidence is calibrated by Brier score | `0.129963` | `<= 0.2` | yes |  |
| candidate confidence calibration error is bounded | `0.287761` | `<= 0.16` | no |  |
| candidate uncertainty rises under hazard | `0.265778` | `>= 0.2` | yes |  |
| candidate avoids bad primary-path actions | `0.130774` | `>= 0.7` | no |  |
| candidate improves behavior vs v2.0 no-monitor | `0.0435185` | `>= 0.06` | no |  |
| monitor must be behaviorally used, not just reported | `0.0435185` | `>= 0.06` | no |  |
| confidence-disabled control loses | `0.0435185` | `>= 0.06` | no |  |
| random-confidence control loses | `-0.0337963` | `>= 0.03` | no |  |
| time-shuffled confidence control loses | `0.0388889` | `>= 0.03` | yes |  |
| anti-confidence control loses | `0.0583333` | `>= 0.08` | no |  |
| candidate beats best non-oracle control | `-0.0921296` | `>= 0.02` | no |  |
| candidate calibration beats random/shuffled monitors | `0.112421` | `>= 0.04` | yes |  |
| candidate AUROC beats random/shuffled monitors | `0.467308` | `>= 0.12` | yes |  |

## Artifacts

- `ambiguous_cue_v2_0_no_monitor_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/ambiguous_cue_v2_0_no_monitor_seed42_timeseries.csv`
- `ambiguous_cue_self_eval_gated_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/ambiguous_cue_self_eval_gated_seed42_timeseries.csv`
- `ambiguous_cue_time_shuffled_confidence_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/ambiguous_cue_time_shuffled_confidence_seed42_timeseries.csv`
- `ood_context_insertion_v2_0_no_monitor_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/ood_context_insertion_v2_0_no_monitor_seed42_timeseries.csv`
- `ood_context_insertion_self_eval_gated_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/ood_context_insertion_self_eval_gated_seed42_timeseries.csv`
- `ood_context_insertion_time_shuffled_confidence_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/ood_context_insertion_time_shuffled_confidence_seed42_timeseries.csv`
- `memory_corruption_v2_0_no_monitor_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/memory_corruption_v2_0_no_monitor_seed42_timeseries.csv`
- `memory_corruption_self_eval_gated_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/memory_corruption_self_eval_gated_seed42_timeseries.csv`
- `memory_corruption_time_shuffled_confidence_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/memory_corruption_time_shuffled_confidence_seed42_timeseries.csv`
- `hidden_regime_mismatch_v2_0_no_monitor_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/hidden_regime_mismatch_v2_0_no_monitor_seed42_timeseries.csv`
- `hidden_regime_mismatch_self_eval_gated_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/hidden_regime_mismatch_self_eval_gated_seed42_timeseries.csv`
- `hidden_regime_mismatch_time_shuffled_confidence_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/hidden_regime_mismatch_time_shuffled_confidence_seed42_timeseries.csv`
- `module_routing_uncertainty_v2_0_no_monitor_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/module_routing_uncertainty_v2_0_no_monitor_seed42_timeseries.csv`
- `module_routing_uncertainty_self_eval_gated_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/module_routing_uncertainty_self_eval_gated_seed42_timeseries.csv`
- `module_routing_uncertainty_time_shuffled_confidence_seed42_timeseries_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/module_routing_uncertainty_time_shuffled_confidence_seed42_timeseries.csv`
- `summary_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/tier5_18_summary.csv`
- `aggregates_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/tier5_18_aggregates.csv`
- `comparisons_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/tier5_18_comparisons.csv`
- `fairness_contract_json`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/tier5_18_fairness_contract.json`
- `accuracy_edges_png`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/tier5_18_accuracy_edges.png`
- `monitor_auroc_matrix_png`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/tier5_18_monitor_auroc_matrix.png`
- `results_json`: `/Users/james/JKS:CRA/controlled_test_output/tier5_18_20260429_212721/tier5_18_results.json`
