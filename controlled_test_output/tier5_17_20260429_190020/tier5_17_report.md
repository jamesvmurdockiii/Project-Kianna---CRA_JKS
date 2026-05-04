# Tier 5.17 Pre-Reward Representation Formation Findings

- Generated: `2026-04-29T19:00:40+00:00`
- Status: **FAIL**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier5_17_20260429_190020`
- Tasks: `latent_cluster_sequence, temporal_motif_sequence, ambiguous_reentry_context`
- Seeds: `[42, 43, 44]`

Tier 5.17 asks whether a CRA-compatible label-free state module can form useful latent structure before labels, reward, correctness feedback, or dopamine are introduced.

## Claim Boundary

- Noncanonical software diagnostic evidence only.
- Exposure is label-free and reward-free for all non-oracle rows.
- Hidden labels are used only after frozen/snapshotted representations are produced, for offline probes.
- This is not SpiNNaker hardware evidence, native/custom-C on-chip representation learning, language, planning, AGI, or a v2.0 freeze.
- The oracle row is an upper bound and is excluded from no-leakage promotion checks.

## Summary

- expected_runs: `81`
- observed_runs: `81`
- candidate_min_ridge_probe_accuracy: `0.591489`
- candidate_min_knn_probe_accuracy: `0.465812`
- non_oracle_label_leakage_runs: `0`
- reward_leakage_runs: `0`
- max_abs_raw_dopamine_non_oracle: `0`
- temporal_control_losses: `4`
- non_encoder_wins: `1`
- sample_efficiency_wins: `1`

## Comparisons

| Task | Candidate ridge | No-plasticity | Time-shuffled | Input-only | History-only | Random projection | Oracle | Edge vs best non-oracle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ambiguous_reentry_context | 0.987179 | 0.594017 | 0.621083 | 0.643875 | 0.673789 | 0.673789 | 1 | 0.31339 |
| latent_cluster_sequence | 0.998582 | 0.99572 | 0.995745 | 0.998582 | 0.998582 | 0.998582 | 1 | 0 |
| temporal_motif_sequence | 0.608844 | 0.544832 | 0.537698 | 0.568976 | 0.994308 | 0.994308 | 1 | -0.385464 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| task/variant/seed matrix completed | 81 | == 81 | yes |  |
| non-oracle exposure has no hidden-label leakage | 0 | == 0 | yes |  |
| exposure has no reward visibility | 0 | == 0 | yes |  |
| pre-reward raw dopamine remains zero | 0 | <= 1e-12 | yes |  |
| candidate reaches minimum ridge-probe accuracy | 0.591489 | >= 0.72 | no |  |
| candidate reaches minimum kNN-probe accuracy | 0.465812 | >= 0.7 | no |  |
| candidate beats no-state-plasticity control | 0.00286123 | >= 0.05 | no |  |
| candidate beats random untrained state | 0.339941 | >= 0.2 | yes |  |
| temporal shams lose on temporal-pressure tasks | 4 | >= 2 | yes |  |
| candidate beats current-input-only on temporal-pressure tasks | 1 | >= 2 | no |  |
| candidate improves downstream sample efficiency somewhere | 1 | >= 2 | no |  |

Failure: Failed criteria: candidate reaches minimum ridge-probe accuracy, candidate reaches minimum kNN-probe accuracy, candidate beats no-state-plasticity control, candidate beats current-input-only on temporal-pressure tasks, candidate improves downstream sample efficiency somewhere

## Artifacts

- `tier5_17_results.json`: machine-readable manifest.
- `tier5_17_report.md`: human findings and claim boundary.
- `tier5_17_summary.csv`: aggregate probe metrics by task and variant.
- `tier5_17_comparisons.csv`: candidate edges against controls.
- `tier5_17_fairness_contract.json`: no-label/no-reward exposure contract.
- `tier5_17_representation_matrix.png`: ridge-probe accuracy heatmap.
- `tier5_17_control_edges.png`: candidate-control edge plot.

![representation_matrix](tier5_17_representation_matrix.png)

![control_edges](tier5_17_control_edges.png)
