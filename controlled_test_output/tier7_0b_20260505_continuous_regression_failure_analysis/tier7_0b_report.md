# Tier 7.0b Continuous-Regression Failure Analysis

- Generated: `2026-05-05T13:57:35+00:00`
- Status: **PASS**
- Criteria: `10/10`
- Failure class: `recoverable_state_signal_default_readout_failure`

## Claim Boundary

Tier 7.0b is software diagnostic evidence only. It localizes the Tier 7.0 continuous-regression benchmark gap using leakage-safe readout/state probes. It is not a tuning run, not a promoted mechanism, not hardware evidence, and not a new baseline freeze.

## Aggregate Probe Summary

| Model / Probe | Rank | Geomean MSE mean | Geomean NMSE mean |
| --- | ---: | ---: | ---: |
| cra_state_plus_lag_probe | 1 | 0.054439372091655114 | 0.08273535520582824 |
| cra_prediction_plus_observed_probe | 2 | 0.41305684397840264 | 0.6235137319245091 |
| cra_internal_state_ridge_probe | 3 | 0.44329167010892245 | 0.6703807752277052 |
| cra_prediction_affine_probe | 4 | 0.6431554514667271 | 0.9710164711953562 |
| cra_internal_state_shuffled_target_control | 5 | 0.7532851635211467 | 1.1469709787960432 |
| cra_online_raw | 6 | 1.223255942741316 | 1.8493192262308755 |

## Failure Classification

- Class: `recoverable_state_signal_default_readout_failure`
- Raw CRA geomean MSE: `1.223255942741316`
- State-probe geomean MSE: `0.44329167010892245`
- State+lag geomean MSE: `0.054439372091655114`
- State improvement over raw: `2.759483259499883`
- State vs shuffled-control advantage: `1.6992991619627207`
- Recommendation: Design a bounded continuous readout/interface repair before adding new organism mechanisms.

## Interpretation Rule

- This tier diagnoses the Tier 7.0 gap; it does not tune CRA.
- Diagnostic ridge probes are not promoted mechanisms.
- No benchmark migration to hardware is justified until a repair tier passes.

