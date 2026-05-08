# Tier 7.1g NAB Source/Data/Scoring Preflight

- Generated: `2026-05-08T22:39:03+00:00`
- Runner revision: `tier7_1g_nab_source_data_scoring_preflight_20260508_0001`
- Status: **PASS**
- Criteria: `24/24`

## Source Pin

- Official repository: https://github.com/numenta/NAB
- Pinned commit: `ea702d75cc2258d9d7dd35ca8e5e2539d71f3140`
- Remote HEAD observed: `ea702d75cc2258d9d7dd35ca8e5e2539d71f3140`
- Cached source files: `13`

## Selected Streams

- Selected files: `5`
- Total selected rows: `40526`
- Smoke stream rows: `400`
- Label-window rows: `12`

## Leakage Boundary

- Smoke stream rows contain values and timestamps only; labels/windows are not present in detector rows.
- Anomaly windows are emitted separately in `tier7_1g_label_windows.csv` for offline scoring only.
- The prefix z-score score file is only a scoring-interface smoke, not a detector result or claim.
- This tier performs no CRA scoring and no baseline scoring.

## Claim Boundary

Tier 7.1g verifies official NAB source pinning/cache, selected data/label parsing, label-separated online stream smoke rows, and scoring-interface feasibility. It is not NAB scoring, not public usefulness evidence, not a baseline freeze, and not hardware/native transfer evidence.

## Next Step

Tier 7.1h may run a compact NAB scoring gate only after this preflight passes. Tier 7.1h must compare CRA v2.2/v2.3 against fair online anomaly baselines, sham controls, and predeclared thresholds/metrics without label leakage.
