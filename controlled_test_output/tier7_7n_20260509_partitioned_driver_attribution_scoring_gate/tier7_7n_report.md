# Tier 7.7n Partitioned-Driver Attribution Scoring Gate

- Generated: `2026-05-09T16:56:24+00:00`
- Status: **PASS**
- Criteria: `15/15`
- Outcome: `generic_projection_explains_gain`
- Recommendation: Useful gain remains generic-basis/interface explainable; do not promote.

## Boundary

Tier 7.7n scores the locked 7.7m partitioned-driver attribution contract. It may support or block attribution diagnostically, but it does not freeze a baseline, promote a mechanism, authorize hardware/native transfer, or claim broad public usefulness.

## Diagnostics

- prior_7_7l_lorenz_repair_128_geomean_mse: `0.003448530743487121`
- full_lorenz_128_geomean_mse: `0.003448530743487121`
- single_pool_lorenz_128_geomean_mse: `0.0065086835955742274`
- partition_shuffled_lorenz_128_geomean_mse: `0.003733946374059473`
- merged_lorenz_128_geomean_mse: `0.005645838388721277`
- nonlinear_lag_lorenz_128_geomean_mse: `0.0019527710201000855`
- linear_lag_lorenz_128_geomean_mse: `0.00508674022639791`
- diversity_disabled_lorenz_128_geomean_mse: `0.0035055406720889953`
- random_projection_lorenz_128_geomean_mse: `0.0016704454054783221`
- permuted_lorenz_128_geomean_mse: `0.006393303044993282`
- single_pool_divided_by_full: `1.8873787359635685`
- partition_control_min_divided_by_full: `1.0827644152836355`
- nonlinear_lag_divided_by_full: `0.5662617402463584`
- linear_lag_divided_by_full: `1.4750456367555094`
- diversity_disabled_divided_by_full: `1.0165316573469856`
- random_projection_divided_by_full: `0.48439336335716815`
- permuted_divided_by_full: `1.8539208493552346`
- target_shuffle_divided_by_full: `292.34720210742137`
- time_shuffle_divided_by_full: `285.3999658693415`
- driver_group_ablation_margins: `{'remove_fast_trace_drivers': 1.1922368140266182, 'remove_lag_drivers': 1.0, 'remove_nonlinear_drivers': 1.1698991260266132, 'remove_slow_trace_drivers': 1.0166629237434104}`
- full_useful: `True`
- partition_sep: `True`
- generic_sep: `False`
- coherent_ablation_loss: `True`
- guards_ok: `True`
- regressions_ok: `True`

## Nonclaims

- not a baseline freeze
- not a mechanism promotion
- not hardware/native transfer
- not external-baseline superiority
- not broad public usefulness
- not language, AGI, or ASI evidence
