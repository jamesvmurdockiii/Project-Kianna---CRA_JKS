# Tier 7.1d C-MAPSS Failure Analysis / Adapter Repair

- Generated: `2026-05-08T21:20:55+00:00`
- Runner revision: `tier7_1d_cmapss_failure_analysis_adapter_repair_20260508_0001`
- Status: **PASS**
- Criteria: `14/14`
- Outcome: `compact_failure_partly_readout_or_target_policy`

## Key Metrics

- Best promotable model: `scalar_pca1_v2_2_ridge_capped125` RMSE `20.271418942340336`
- Best public baseline: `lag_multichannel_ridge_capped125` RMSE `20.305268771358435`
- Scalar v2.3 LMS uncapped RMSE: `49.4908802462679`
- Scalar v2.3 ridge uncapped RMSE: `43.435416241039015`
- Scalar v2.3 LMS capped RMSE: `26.32185603140849`
- Multichannel v2.3 ridge capped RMSE: `22.697166948526846`
- Multichannel sham separation delta RMSE: `12.995250110072181`

## Boundary

Tier 7.1d is software failure analysis / adapter repair only. It is not a full C-MAPSS benchmark, not a new CRA mechanism, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence. Continuous no-reset probes are diagnostic only and are not promotable C-MAPSS claims.

## Next Step

Use the localized factor result to define the next locked gate. If multichannel CRA state is sham-separated but still loses to fair baselines, design a stricter multichannel adapter/fairness gate. If no adapter factor repairs the gap, stop C-MAPSS promotion and move to the next predeclared public benchmark family or planned general mechanism without native transfer.
