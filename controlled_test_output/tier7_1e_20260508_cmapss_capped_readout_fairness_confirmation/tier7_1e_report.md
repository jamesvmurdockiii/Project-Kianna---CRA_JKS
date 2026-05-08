# Tier 7.1e C-MAPSS Capped-RUL/Readout Fairness Confirmation

- Generated: `2026-05-08T21:28:37+00:00`
- Runner revision: `tier7_1e_cmapss_capped_readout_fairness_confirmation_20260508_0001`
- Status: **PASS**
- Criteria: `12/12`
- Outcome: `v2_2_capped_signal_not_statistically_confirmed`

## Primary Comparison

- Candidate: `scalar_pca1_v2_2_ridge_capped125`
- Baseline: `lag_multichannel_ridge_capped125`
- Mean delta RMSE, positive means candidate better: `-0.3690103080637045`
- Bootstrap 95% CI: `-1.4191012103865384` to `0.6704668696286052`
- Effect size d: `-0.06884079972999842`
- Better/worse units: `50` / `50`

## Boundary

Tier 7.1e is a statistical/fairness confirmation over Tier 7.1d per-unit results. It does not rerun or expand C-MAPSS, does not promote a mechanism, does not freeze a baseline, does not authorize hardware/native transfer, and does not prove public usefulness.

## Next Step

If the candidate is not confirmed, do not keep tuning C-MAPSS. Move to the next predeclared public benchmark family or a planned general mechanism with its own evidence contract. If confirmed in a later expanded gate, require full C-MAPSS FD001-FD004 and stronger external baselines before any paper usefulness claim.
