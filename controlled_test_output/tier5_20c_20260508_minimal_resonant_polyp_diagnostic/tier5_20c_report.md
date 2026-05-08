# Tier 5.20c - Minimal Hybrid Resonant/LIF Polyp Diagnostic

- Generated: `2026-05-08T22:20:19+00:00`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier5_20c_20260508_minimal_resonant_polyp_diagnostic`
- Outcome: `minimal_resonant_not_promoted`

## Claim Boundary

Tier 5.20c is a software-only minimal-dose diagnostic after 5.20a/5.20b. It tests a same-budget 14 LIF / 2 resonant branch internal-polyp proxy against v2.3, v2.2, full-resonant, lag/reservoir/ESN controls, and 14/2 shams. It is not a canonical organism change, not hardware evidence, and not a baseline freeze.

## Summary

- Recommendation: Do not integrate the 14/2 resonant variant into the core organism.
- All-task candidate geomean MSE: `0.2777975100580056`
- All-task v2.3 geomean MSE: `0.2610804850928049`
- Margin vs v2.3: `0.9398229848722902`
- Wins vs v2.3: `0`
- Material regressions vs v2.3: `1`
- Sham-separated tasks: `0`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier5_20c_minimal_resonant_polyp_diagnostic_20260508_0001` | expected current source | yes |
| Tier 5.20b hybrid diagnostic present | `tier5_20b` | results exist | yes |
| same budget 14/2 variant declared | `14 LIF + 2 resonant` | sum == 16 excitatory units | yes |
| all required models present | `['fixed_esn_train_prefix_ridge_baseline', 'fixed_random_reservoir_online_control', 'full_16_resonant_reference', 'hybrid_14_lif_2_flat_tau_sham', 'hybrid_14_lif_2_rate_only_sham', 'hybrid_14_lif_2_resonant', 'hybrid_14_lif_2_shuffled_branch_sham', 'lag_only_online_lms_control', 'v2_2_fading_memory_reference', 'v2_3_generic_bounded_recurrent_state']` | all present | yes |
| all runs completed | `180/180` | all pass | yes |
| 14/2 shams present | `['hybrid_14_lif_2_flat_tau_sham', 'hybrid_14_lif_2_rate_only_sham', 'hybrid_14_lif_2_shuffled_branch_sham']` | all present | yes |
| public standard tasks included | `['mackey_glass', 'lorenz', 'narma10']` | all included | yes |
| targeted anomaly task included | `True` | == true | yes |
| classification produced | `minimal_resonant_not_promoted` | non-empty | yes |
| software only | `no PyNN/SpiNNaker calls` | true | yes |
