# Tier 7.1b NASA C-MAPSS Source/Data Preflight

- Generated: `2026-05-08T20:59:45+00:00`
- Runner revision: `tier7_1b_cmapss_source_data_preflight_20260508_0001`
- Status: **PASS**
- Criteria: `16/16`

## Source

- Dataset page: https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data
- Download URL: https://data.nasa.gov/docs/legacy/CMAPSSData.zip
- NASA PCoE page: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
- DASHlink page: https://c3.ndc.nasa.gov/dashlink/resources/139/
- ZIP SHA256: `74bef434a34db25c7bf72e668ea4cd52afe5f2cf8e44367c55a82bfd91a5a34f`
- ZIP bytes: `12425978`

## FD001 Profile

- Train rows: `20631`
- Test rows: `13096`
- Train units: `100`
- Test units: `100`
- RUL labels: `100`
- Column count: `26`

## Leakage Boundary

- Normalization stats are computed from `train_FD001.txt` only.
- Smoke stream rows do not include RUL labels.
- Offline scoring labels are written separately from the smoke stream.
- This tier performs no CRA scoring and no baseline scoring.

## Claim Boundary

Tier 7.1b verifies source access, checksums, schema, split/normalization policy, and a tiny leakage-safe stream smoke. It is not C-MAPSS scoring, not a public usefulness claim, not a baseline freeze, and not hardware/native transfer evidence.

## Next Step

Tier 7.1c may run the first compact C-MAPSS FD001 scoring gate only after this preflight passes. Tier 7.1c must score v2.2/v2.3 and fair baselines on the same rows with leakage controls preserved.
