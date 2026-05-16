# Tier 5.20b - Hybrid Resonant/LIF Polyp Diagnostic

- Generated: `2026-05-08T22:13:29+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier5_20b_20260508_hybrid_resonant_polyp_diagnostic`
- Outcome: `hybrid_resonant_not_promoted`
- Best candidate: `hybrid_8_lif_8_resonant`

## Claim Boundary

Tier 5.20b is a software-only repair diagnostic after 5.20a. It tests same-budget 8/8 and 12/4 hybrid LIF/resonant branch internal-polyp proxies against v2.3, v2.2, lag/reservoir/ESN controls, and hybrid shams. It is not a canonical organism change, not hardware evidence, and not a baseline freeze.

## Summary

- Recommendation: Do not integrate the hybrid resonant branch variants into the core organism.

## Candidate Rankings

| Candidate | All-task MSE | Margin vs v2.3 | Wins vs v2.3 | Regressions | Sham-separated tasks |
| --- | ---: | ---: | ---: | ---: | ---: |
| hybrid_8_lif_8_resonant | `0.2852846857844163` | `0.9151577287611505` | `2` | `2` | `1` |
| hybrid_12_lif_4_resonant | `0.270891573191636` | `0.963782232192618` | `1` | `1` | `1` |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier5_20b_hybrid_resonant_polyp_diagnostic_20260508_0001` | expected current source | yes |
| Tier 5.20a full-replacement diagnostic present | `tier5_20a` | results exist | yes |
| same budget 8/8 variant declared | `8 LIF + 8 resonant` | sum == 16 excitatory units | yes |
| same budget 12/4 variant declared | `12 LIF + 4 resonant` | sum == 16 excitatory units | yes |
| all required models present | `['fixed_esn_train_prefix_ridge_baseline', 'fixed_random_reservoir_online_control', 'full_16_resonant_reference', 'hybrid_12_lif_4_flat_tau_sham', 'hybrid_12_lif_4_rate_only_sham', 'hybrid_12_lif_4_resonant', 'hybrid_12_lif_4_shuffled_branch_sham', 'hybrid_8_lif_8_flat_tau_sham', 'hybrid_8_lif_8_rate_only_sham', 'hybrid_8_lif_8_resonant', 'hybrid_8_lif_8_shuffled_branch_sham', 'lag_only_online_lms_control', 'v2_2_fading_memory_reference', 'v2_3_generic_bounded_recurrent_state']` | all present | yes |
| all runs completed | `252/252` | all pass | yes |
| 8/8 shams present | `['hybrid_8_lif_8_flat_tau_sham', 'hybrid_8_lif_8_rate_only_sham', 'hybrid_8_lif_8_shuffled_branch_sham']` | all present | yes |
| 12/4 shams present | `['hybrid_12_lif_4_flat_tau_sham', 'hybrid_12_lif_4_rate_only_sham', 'hybrid_12_lif_4_shuffled_branch_sham']` | all present | yes |
| public standard tasks included | `['mackey_glass', 'lorenz', 'narma10']` | all included | yes |
| targeted anomaly task included | `True` | == true | yes |
| classification produced | `hybrid_resonant_not_promoted` | non-empty | yes |
| software only | `no PyNN/SpiNNaker calls` | true | yes |

## Artifacts

- `tier5_20b_results.json`
- `tier5_20b_summary.csv`
- `tier5_20b_aggregate.csv`
- `tier5_20b_aggregate_summary.csv`
- `tier5_20b_hybrid_contract.json`
- `tier5_20b_timeseries.csv` if `--no-timeseries` was not used
