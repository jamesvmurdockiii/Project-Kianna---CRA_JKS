# Tier 7.0d State-Specific Continuous Interface / Claim-Narrowing

- Generated: `2026-05-05T16:42:42+00:00`
- Status: **PASS**
- Criteria: `10/10`
- Outcome: `lag_regression_explains_benchmark`

## Claim Boundary

Tier 7.0d is software diagnostic evidence only. It tests whether CRA state adds value beyond causal lag regression on the Tier 7 standard dynamical benchmark suite. It is not hardware evidence, not a baseline freeze, not a tuning loop, and not proof of superiority over external baselines.

## Aggregate Summary

| Model | Rank | Geomean MSE mean | Geomean NMSE mean |
| --- | ---: | ---: | ---: |
| train_prefix_ridge_lag_upper_bound | 1 | 0.044288645167134134 | 0.0669212173981317 |
| train_prefix_ridge_lag_plus_orthogonal_state_upper_bound | 2 | 0.05474449238029897 | 0.08317162100933008 |
| train_prefix_ridge_lag_plus_state_upper_bound | 3 | 0.055062195137692116 | 0.08369424365693838 |
| two_stage_shuffled_residual_control | 4 | 0.14087562509364157 | 0.21209179145578835 |
| two_stage_lag_residual_state_online_repair | 5 | 0.14545708938088173 | 0.2188734032499806 |
| lag_only_online_lms_control | 6 | 0.1514560842638888 | 0.22797373549106173 |
| state_plus_lag_online_lms_reference | 7 | 0.19040922596175056 | 0.2866382945160751 |
| lag_plus_shuffled_orthogonal_state_control | 8 | 0.23690708905018254 | 0.3563681482907377 |
| lag_plus_orthogonal_state_online_repair | 9 | 0.24075702898872342 | 0.361684316934416 |
| state_only_online_lms_control | 10 | 0.3747367253327713 | 0.5645696468077211 |
| orthogonal_state_only_online_control | 11 | 0.6171295249260879 | 0.9317320829658889 |
| lag_plus_orthogonal_state_shuffled_target_control | 12 | 0.7104502065052625 | 1.0751129109318651 |
| frozen_lag_plus_state_control | 13 | 0.744299442671371 | 1.1243682956201968 |
| train_prefix_ridge_orthogonal_state_only_probe | 14 | 0.8074214142965711 | 1.2206018081819996 |
| raw_cra_v2_1_online | 15 | 1.223255942741316 | 1.8493192262308755 |

## Classification

- Outcome: `lag_regression_explains_benchmark`
- Raw CRA geomean MSE: `1.223255942741316`
- Lag-only online geomean MSE: `0.1514560842638888`
- Best state-specific online model: `two_stage_lag_residual_state_online_repair`
- Best state-specific online geomean MSE: `0.14545708938088173`
- Margin versus lag-only: `1.041242368512535`
- Margin versus best sham: `0.9685029838920843`
- Train-prefix ridge state margin versus lag: `0.8090064085254427`
- Recommendation: Narrow the Tier 7 continuous-regression claim; do not move this benchmark path to hardware yet.

## Interpretation Rule

- If state-specific online candidates do not beat lag-only, do not promote a continuous readout mechanism.
- If train-prefix upper bounds show state value but online candidates fail, this is still an online-interface problem.
- If lag-only remains the best explanation, narrow the benchmark claim instead of tuning blindly.

