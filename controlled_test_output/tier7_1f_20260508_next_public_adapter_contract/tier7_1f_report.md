# Tier 7.1f Next Public Adapter Contract / Family Selection

- Generated: `2026-05-08T21:35:18+00:00`
- Runner revision: `tier7_1f_next_public_adapter_contract_20260508_0001`
- Status: **PASS**
- Criteria: `10/10`
- Selected adapter: `numenta_nab_streaming_anomaly`

## Why This Adapter

C-MAPSS behaved like a monotone remaining-useful-life regression problem, which is not the strongest pressure for CRA's memory/adaptation path. NAB is a public streaming anomaly benchmark with labeled anomaly windows, real-time scoring, false-positive pressure, and nonstationary time-series streams. It better targets online prediction error, surprise, adaptation, and recovery without moving hardware prematurely.

## Boundary

Tier 7.1f is a contract/family-selection gate only. It does not download NAB, score CRA, compare models, freeze a baseline, authorize hardware/native transfer, or prove public usefulness.

## Next Step

Tier 7.1g NAB source/data/scoring preflight: verify source access, source hash/commit, file/label parse, label-separated streams, tiny leakage-safe smoke rows, and scoring-interface feasibility before any full NAB scoring.
