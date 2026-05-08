# Tier 7.1i NAB Fairness/Statistical Confirmation

- Generated: `2026-05-08T23:23:32+00:00`
- Runner revision: `tier7_1i_nab_fairness_confirmation_20260508_0001`
- Status: **PASS**
- Criteria: `18/18`
- Outcome: `v2_3_nab_signal_localized_not_confirmed`

## Key Metrics

- Streams: `20`
- Categories: `6`
- Best model: `rolling_zscore_detector` primary score `0.140951459207744`
- Best external baseline: `rolling_zscore_detector` primary score `0.140951459207744`
- v2.3 rank: `4`
- v2.3 primary score: `0.09880252815842962`
- v2.2 primary score: `0.08150013601217254`
- v2.3 sham separations: `3`
- Bootstrap mean delta vs best external: `-0.0421489310493144`
- Bootstrap 95% CI: `[-0.13027269733009264, 0.03602365729899069]`
- v2.3 category wins: `['realAdExchange']`
- v2.3 stream wins: `['realAdExchange/exchange-2_cpm_results.csv', 'realKnownCause/ambient_temperature_system_failure.csv']`

## Boundary

Tier 7.1i is broader NAB software confirmation/localization using label-separated online anomaly scores. It is not a full NAB benchmark claim by itself, not public usefulness proof unless confirmed by the predeclared statistical gate, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.

## Next Step

If v2.3 confirms on the broader subset, design the next holdout/public adapter gate before any transfer. If the signal localizes or collapses, debug the localized stream families or narrow the public usefulness claim before adding mechanisms.
