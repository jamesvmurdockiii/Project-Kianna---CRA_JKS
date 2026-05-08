# Tier 5.20d - Resonant-Heavy Hybrid LIF Polyp Diagnostic

- Generated: `2026-05-08T22:22:18+00:00`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier5_20d_20260508_resonant_heavy_polyp_diagnostic`
- Outcome: `resonant_heavy_not_promoted`

## Claim Boundary

Tier 5.20d is a software-only resonant-heavy diagnostic after 5.20a/5.20b. It tests a same-budget 4 LIF / 12 resonant branch internal-polyp proxy against v2.3, v2.2, full-resonant, lag/reservoir/ESN controls, and 4/12 shams. It is not a canonical organism change, not hardware evidence, and not a baseline freeze.

## Summary

- Recommendation: Do not integrate the 4/12 resonant variant into the core organism.
- All-task candidate geomean MSE: `0.29289224348599796`
- All-task v2.3 geomean MSE: `0.2610804850928049`
- Margin vs v2.3: `0.8913875013739861`
- Wins vs v2.3: `3`
- Material regressions vs v2.3: `2`
- Sham-separated tasks: `2`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier5_20d_resonant_heavy_polyp_diagnostic_20260508_0001` | expected current source | yes |
| Tier 5.20b hybrid diagnostic present | `tier5_20b` | results exist | yes |
| same budget 4/12 variant declared | `4 LIF + 12 resonant` | sum == 16 excitatory units | yes |
| all required models present | `['fixed_esn_train_prefix_ridge_baseline', 'fixed_random_reservoir_online_control', 'full_16_resonant_reference', 'hybrid_4_lif_12_flat_tau_sham', 'hybrid_4_lif_12_rate_only_sham', 'hybrid_4_lif_12_resonant', 'hybrid_4_lif_12_shuffled_branch_sham', 'lag_only_online_lms_control', 'v2_2_fading_memory_reference', 'v2_3_generic_bounded_recurrent_state']` | all present | yes |
| all runs completed | `180/180` | all pass | yes |
| 4/12 shams present | `['hybrid_4_lif_12_flat_tau_sham', 'hybrid_4_lif_12_rate_only_sham', 'hybrid_4_lif_12_shuffled_branch_sham']` | all present | yes |
| public standard tasks included | `['mackey_glass', 'lorenz', 'narma10']` | all included | yes |
| targeted anomaly task included | `True` | == true | yes |
| classification produced | `resonant_heavy_not_promoted` | non-empty | yes |
| software only | `no PyNN/SpiNNaker calls` | true | yes |
