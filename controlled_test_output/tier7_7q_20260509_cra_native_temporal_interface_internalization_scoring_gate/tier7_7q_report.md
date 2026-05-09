# Tier 7.7q CRA-Native Temporal-Interface Internalization Scoring Gate

- Generated: `2026-05-09T17:34:02+00:00`
- Status: **PASS**
- Criteria: `14/14`
- Outcome: `external_controls_still_win`
- Recommendation: External controls still beat the native candidate; do not promote.

## Boundary

Tier 7.7q scores the locked 7.7p CRA-native temporal-interface internalization candidate. It may support or block the candidate diagnostically, but it does not freeze a baseline, promote a mechanism, authorize hardware/native transfer, or claim broad public usefulness.

## Diagnostics

- native_lorenz_128_geomean_mse: `0.002256771889253472`
- random_projection_lorenz_128_geomean_mse: `0.0016704454054783221`
- nonlinear_lag_lorenz_128_geomean_mse: `0.0019527710201000855`
- current_lorenz_128_geomean_mse: `0.0065086835955742274`
- no_nonlinearity_lorenz_128_geomean_mse: `0.0029142496565643717`
- no_delay_lorenz_128_geomean_mse: `0.005898442417964284`
- random_projection_divided_by_native: `0.7401924020025331`
- nonlinear_lag_divided_by_native: `0.865293931300275`
- current_divided_by_native: `2.884068002870802`
- no_nonlinearity_divided_by_native: `1.2913355002522606`
- no_delay_divided_by_native: `2.613663545727458`
- target_shuffle_divided_by_native: `447.07332395817457`
- time_shuffle_divided_by_native: `434.9311263486088`
- useful_vs_current: `True`
- beats_random_projection: `False`
- beats_nonlinear_lag: `False`
- matches_strong_controls: `False`
- ablations_hurt: `True`
- guards_ok: `True`
- regressions_ok: `True`

## Nonclaims

- not a baseline freeze
- not a mechanism promotion
- not hardware/native transfer
- not external-baseline superiority
- not broad public usefulness
- not language, AGI, or ASI evidence
