# Tier 5.18 Self-Evaluation / Metacognitive Monitoring Findings

- Generated: `2026-04-29T23:04:44+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail`
- Tasks: `ambiguous_cue, memory_corruption`
- Seeds: `[42]`

Tier 5.18 tests whether a CRA monitor can estimate reliability before feedback and whether using that signal improves behavior under ambiguity, OOD insertion, memory corruption, hidden-regime mismatch, and routing uncertainty.

## Claim Boundary

- Noncanonical software diagnostic evidence only.
- Non-oracle monitors do not use outcomes/rewards before emitting confidence or uncertainty.
- This is operational reliability monitoring, not consciousness, self-awareness, introspection, language, planning, AGI, hardware evidence, or a v2.1 freeze.
- A future Tier 5.18c promotion/regression gate is required before any v2.1 baseline lock.

## Summary

- expected_runs: `12`
- observed_runs: `12`
- candidate_min_primary_error_auroc: `1`
- candidate_min_hazard_detection_auroc: `1`
- candidate_max_brier_primary_correct: `0.033625`
- candidate_max_ece_primary_correct: `0.111867`
- candidate_min_uncertainty_hazard_minus_normal: `0.279092`
- candidate_min_bad_action_avoidance: `0.695652`
- min_accuracy_edge_vs_v2_0: `0.133333`
- min_accuracy_edge_vs_monitor_only: `0.133333`
- min_accuracy_edge_vs_best_non_oracle: `0.133333`
- outcome_leakage_runs: `0`
- pre_feedback_monitor_failures: `0`

## Comparisons

| Task | Candidate acc | v2.0 acc | Monitor-only acc | Random acc | Shuffled acc | Best non-oracle edge | Error AUROC | Hazard AUROC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ambiguous_cue | 0.941667 | 0.808333 | 0.808333 | 0.675 | 0.7875 | 0.133333 | 1 | 1 |
| memory_corruption | 1 | 0.808333 | 0.808333 | 0.675 | 0.766667 | 0.191667 | 1 | 1 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| task/variant/seed matrix completed | `12` | `== 12` | yes |  |
| frozen v2.0 baseline artifact exists | `<repo>/baselines/CRA_EVIDENCE_BASELINE_v2.0.json` | `exists True` | yes |  |
| non-oracle monitors do not use outcomes | `0` | `== 0` | yes |  |
| monitor values are computed before feedback | `0` | `== 0` | yes |  |

## Artifacts

- `ambiguous_cue_v2_0_no_monitor_seed42_timeseries_csv`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/ambiguous_cue_v2_0_no_monitor_seed42_timeseries.csv`
- `ambiguous_cue_self_eval_gated_seed42_timeseries_csv`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/ambiguous_cue_self_eval_gated_seed42_timeseries.csv`
- `ambiguous_cue_time_shuffled_confidence_seed42_timeseries_csv`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/ambiguous_cue_time_shuffled_confidence_seed42_timeseries.csv`
- `memory_corruption_v2_0_no_monitor_seed42_timeseries_csv`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/memory_corruption_v2_0_no_monitor_seed42_timeseries.csv`
- `memory_corruption_self_eval_gated_seed42_timeseries_csv`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/memory_corruption_self_eval_gated_seed42_timeseries.csv`
- `memory_corruption_time_shuffled_confidence_seed42_timeseries_csv`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/memory_corruption_time_shuffled_confidence_seed42_timeseries.csv`
- `summary_csv`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/tier5_18_summary.csv`
- `aggregates_csv`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/tier5_18_aggregates.csv`
- `comparisons_csv`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/tier5_18_comparisons.csv`
- `fairness_contract_json`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/tier5_18_fairness_contract.json`
- `accuracy_edges_png`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/tier5_18_accuracy_edges.png`
- `monitor_auroc_matrix_png`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/tier5_18_monitor_auroc_matrix.png`
- `results_json`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/v2_1_guardrail/tier5_18_self_evaluation_guardrail/tier5_18_results.json`
