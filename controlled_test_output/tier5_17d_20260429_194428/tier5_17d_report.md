# Tier 5.17d Predictive Preexposure Binding/Sham Repair Findings

- Generated: `2026-04-29T19:44:32+00:00`
- Status: **FAIL**
- Output directory: `<repo>/controlled_test_output/tier5_17d_20260429_194428`
- Tasks: `masked_code_binding, cross_modal_binding, reentry_binding`
- Seeds: `[42, 43, 44]`

Tier 5.17d repairs the 5.17c sham-separation failure by testing target/domain binding on held-out ambiguous episodes after context cues fade.

## Claim Boundary

- Noncanonical software diagnostic evidence only.
- Non-oracle variants receive no labels, reward, correctness feedback, or dopamine during preexposure.
- Hidden labels are used only after representations are generated, for held-out ambiguous-episode probes.
- This is not SpiNNaker hardware evidence, native/custom-C on-chip representation learning, full world modeling, language, planning, AGI, or a v2.0 freeze.

## Summary

- expected_runs: `90`
- observed_runs: `90`
- candidate_min_ridge_probe_accuracy: `0.76873`
- candidate_min_knn_probe_accuracy: `0.818548`
- non_oracle_label_leakage_runs: `0`
- reward_leakage_runs: `0`
- max_abs_raw_dopamine_non_oracle: `0`
- min_candidate_probe_rows: `248`
- sample_efficiency_wins: `3`

## Comparisons

| Task | Candidate | No preexposure | Target shuffled | Wrong domain | Fixed history | Reservoir | STDP-only | Best non-oracle edge |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cross_modal_binding | 0.853915 | 0.40344 | 0.512528 | 0.478793 | 0.410625 | 0.40845 | 0.557967 | 0.295948 |
| masked_code_binding | 1 | 0.327409 | 0.938222 | 0.981955 | 0.28951 | 0.310408 | 0.982929 | 0.0170706 |
| reentry_binding | 0.939516 | 0.302419 | 0.317204 | 0.0658602 | 0.375 | 0.283602 | 0.80914 | 0.130376 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| task/variant/seed matrix completed | 90 | == 90 | yes |  |
| non-oracle exposure has no hidden-label leakage | 0 | == 0 | yes |  |
| exposure has no reward visibility | 0 | == 0 | yes |  |
| pre-reward raw dopamine remains zero | 0 | <= 1e-12 | yes |  |
| held-out ambiguous probe rows available | 248 | >= 70 | yes |  |
| candidate reaches minimum ridge-probe accuracy | 0.76873 | >= 0.76 | yes |  |
| candidate reaches minimum kNN-probe accuracy | 0.818548 | >= 0.64 | yes |  |
| candidate beats no-preexposure control | 0.450475 | >= 0.1 | yes |  |
| target-shuffled binding loses | 0.0617783 | >= 0.08 | no |  |
| wrong-domain binding loses | 0.0180452 | >= 0.08 | no |  |
| fixed-history baseline does not explain result | 0.44329 | >= 0.05 | yes |  |
| reservoir baseline does not explain result | 0.445465 | >= 0.05 | yes |  |
| STDP-only baseline does not explain result | 0.0170706 | >= 0.04 | no |  |
| candidate beats best non-oracle control | 0.0170706 | >= 0.03 | no |  |
| downstream sample-efficiency improves | 3 | >= 2 | yes |  |

Failure: Failed criteria: target-shuffled binding loses, wrong-domain binding loses, STDP-only baseline does not explain result, candidate beats best non-oracle control

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
