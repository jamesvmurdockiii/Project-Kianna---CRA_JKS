# Tier 5.17d Predictive Preexposure Binding/Sham Repair Findings

- Generated: `2026-05-09T01:52:27+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier7_4c_20260509_cost_aware_policy_action_promotion_gate/compact_regression_full_nest/v2_0_compact_regression_gate/predictive_binding_guardrail`
- Tasks: `cross_modal_binding, reentry_binding`
- Seeds: `[42, 43, 44]`

Tier 5.17d repairs the 5.17c sham-separation failure by testing target/domain binding on held-out ambiguous episodes after context cues fade.

## Claim Boundary

- Noncanonical software diagnostic evidence only.
- Non-oracle variants receive no labels, reward, correctness feedback, or dopamine during preexposure.
- Hidden labels are used only after representations are generated, for held-out ambiguous-episode probes.
- This is not SpiNNaker hardware evidence, native/custom-C on-chip representation learning, full world modeling, language, planning, AGI, or a v2.0 freeze.

## Summary

- expected_runs: `60`
- observed_runs: `60`
- candidate_min_ridge_probe_accuracy: `0.785714`
- candidate_min_knn_probe_accuracy: `0.77381`
- non_oracle_label_leakage_runs: `0`
- reward_leakage_runs: `0`
- max_abs_raw_dopamine_non_oracle: `0`
- min_candidate_probe_rows: `176`
- sample_efficiency_wins: `2`

## Comparisons

| Task | Candidate | No preexposure | Target shuffled | Wrong domain | Fixed history | Reservoir | STDP-only | Best non-oracle edge |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_modal_binding | 0.875874 | 0.364436 | 0.432141 | 0.391047 | 0.365915 | 0.333395 | 0.469668 | 0.406206 |
| reentry_binding | 1 | 0.253788 | 0.450758 | 0.215909 | 0.251894 | 0.248106 | 0.857955 | 0.142045 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| task/variant/seed matrix completed | 60 | == 60 | yes |  |
| non-oracle exposure has no hidden-label leakage | 0 | == 0 | yes |  |
| exposure has no reward visibility | 0 | == 0 | yes |  |
| pre-reward raw dopamine remains zero | 0 | <= 1e-12 | yes |  |
| held-out ambiguous probe rows available | 176 | >= 70 | yes |  |
| candidate reaches minimum ridge-probe accuracy | 0.785714 | >= 0.76 | yes |  |
| candidate reaches minimum kNN-probe accuracy | 0.77381 | >= 0.64 | yes |  |
| candidate beats no-preexposure control | 0.511438 | >= 0.1 | yes |  |
| target-shuffled binding loses | 0.443733 | >= 0.08 | yes |  |
| wrong-domain binding loses | 0.484827 | >= 0.08 | yes |  |
| fixed-history baseline does not explain result | 0.50996 | >= 0.05 | yes |  |
| reservoir baseline does not explain result | 0.54248 | >= 0.05 | yes |  |
| STDP-only baseline does not explain result | 0.142045 | >= 0.04 | yes |  |
| candidate beats best non-oracle control | 0.142045 | >= 0.03 | yes |  |
| downstream sample-efficiency improves | 2 | >= 2 | yes |  |

## Artifacts

- `tier5_17d_results.json`: machine-readable manifest.
- `tier5_17d_report.md`: human findings and claim boundary.
- `tier5_17d_runs.csv`: per-task/variant/seed probe rows.
- `tier5_17d_summary.csv`: aggregate probe metrics.
- `tier5_17d_comparisons.csv`: candidate-control edges.
- `tier5_17d_fairness_contract.json`: predeclared no-label/no-reward binding contract.
- `tier5_17d_representation_matrix.png`: ridge-probe accuracy heatmap.
- `tier5_17d_control_edges.png`: binding-control edge plot.

![tier5_17d_representation_matrix](tier5_17d_representation_matrix.png)

![tier5_17d_control_edges](tier5_17d_control_edges.png)
