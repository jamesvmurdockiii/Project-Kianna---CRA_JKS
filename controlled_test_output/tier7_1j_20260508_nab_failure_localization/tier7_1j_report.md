# Tier 7.1j NAB Failure/Localization Analysis

- Generated: `2026-05-08T23:30:24+00:00`
- Runner revision: `tier7_1j_nab_failure_localization_20260508_0001`
- Status: **PASS**
- Criteria: `12/12`
- Failure class: `threshold_or_fp_penalty_sensitive`

## Key Findings

- Default best model: `rolling_zscore_detector` score `0.140951459207744`
- v2.3 default rank: `3` score `0.09880252815842962`
- v2.3 policy-grid wins: `3` / `15`
- v2.3 beats rolling z-score cells: `5` / `15`
- v2.3 default category wins: `['realAdExchange']`
- v2.3 default stream wins: `['realAWSCloudwatch/ec2_disk_write_bytes_c0d644.csv', 'realAdExchange/exchange-2_cpm_results.csv', 'realKnownCause/ambient_temperature_system_failure.csv']`
- Component deltas vs rolling z-score: `{'event_f1_delta_vs_rolling_zscore': 0.021302626282845488, 'window_recall_delta_vs_rolling_zscore': 0.20583333333333342, 'nab_style_delta_vs_rolling_zscore': -1.1513368486050855, 'fp_per_1000_delta_vs_rolling_zscore': 8.088190784286144}`

## Boundary

Tier 7.1j is software failure/localization analysis over the Tier 7.1i broader NAB subset. It is not public usefulness proof, not a promoted mechanism, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.

## Next Step

If the failure localizes to scoring/threshold policy, repair the adapter/readout contract before mechanisms. If simple residual baselines dominate across policy variants, narrow the NAB claim or return to planned general mechanisms only with a predeclared failure hypothesis.
