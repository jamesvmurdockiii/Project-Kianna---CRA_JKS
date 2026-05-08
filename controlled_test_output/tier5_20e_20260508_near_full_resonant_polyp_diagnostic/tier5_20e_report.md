# Tier 5.20e - Near-Full Resonant Hybrid LIF Polyp Diagnostic

- Generated: `2026-05-08T22:23:58+00:00`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier5_20e_20260508_near_full_resonant_polyp_diagnostic`
- Outcome: `near_full_resonant_not_promoted`

## Claim Boundary

Tier 5.20e is a software-only near-full resonant diagnostic after 5.20a/5.20b. It tests a same-budget 2 LIF / 14 resonant branch internal-polyp proxy against v2.3, v2.2, full-resonant, lag/reservoir/ESN controls, and 2/14 shams. It is not a canonical organism change, not hardware evidence, and not a baseline freeze.

## Summary

- Recommendation: Do not integrate the 2/14 resonant variant into the core organism.
- All-task candidate geomean MSE: `0.30374770797663714`
- All-task v2.3 geomean MSE: `0.2610804850928049`
- Margin vs v2.3: `0.8595307165672045`
- Wins vs v2.3: `3`
- Material regressions vs v2.3: `3`
- Sham-separated tasks: `2`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier5_20e_near_full_resonant_polyp_diagnostic_20260508_0001` | expected current source | yes |
| Tier 5.20b hybrid diagnostic present | `tier5_20b` | results exist | yes |
| same budget 2/14 variant declared | `2 LIF + 14 resonant` | sum == 16 excitatory units | yes |
| all required models present | `['fixed_esn_train_prefix_ridge_baseline', 'fixed_random_reservoir_online_control', 'full_16_resonant_reference', 'hybrid_2_lif_14_flat_tau_sham', 'hybrid_2_lif_14_rate_only_sham', 'hybrid_2_lif_14_resonant', 'hybrid_2_lif_14_shuffled_branch_sham', 'lag_only_online_lms_control', 'v2_2_fading_memory_reference', 'v2_3_generic_bounded_recurrent_state']` | all present | yes |
| all runs completed | `180/180` | all pass | yes |
| 2/14 shams present | `['hybrid_2_lif_14_flat_tau_sham', 'hybrid_2_lif_14_rate_only_sham', 'hybrid_2_lif_14_shuffled_branch_sham']` | all present | yes |
| public standard tasks included | `['mackey_glass', 'lorenz', 'narma10']` | all included | yes |
| targeted anomaly task included | `True` | == true | yes |
| classification produced | `near_full_resonant_not_promoted` | non-empty | yes |
| software only | `no PyNN/SpiNNaker calls` | true | yes |
