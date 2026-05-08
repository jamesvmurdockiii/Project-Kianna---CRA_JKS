# Tier 7.1c Compact C-MAPSS FD001 Scoring Gate

- Generated: `2026-05-08T21:15:57+00:00`
- Runner revision: `tier7_1c_cmapss_fd001_scoring_gate_20260508_0001`
- Status: **PASS**
- Criteria: `12/12`
- Outcome: `v2_3_no_public_adapter_advantage`

## Key Metrics

- Best model: `monotone_age_to_rul_ridge` RMSE `46.10944999532139`
- v2.3 rank: `5`
- v2.3 RMSE: `49.4908802462679`
- v2.2 RMSE: `48.739451335025144`
- Best external baseline: `monotone_age_to_rul_ridge` RMSE `46.10944999532139`
- v2.3 sham separations: `3`

## Boundary

Tier 7.1c is compact software scoring on NASA C-MAPSS FD001 using a train-only PCA1 scalar stream and train-prefix readouts. It is not a full C-MAPSS benchmark, not a new baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.

## Next Step

Run Tier 7.1d C-MAPSS failure analysis / adapter repair before adding mechanisms or moving hardware. Localize whether the compact gap comes from scalar PCA1 compression, train-prefix readout policy, target/reset policy, a missing multichannel CRA adapter interface, or a real v2.3 limitation on this public adapter.
