# Tier 2 Controlled Learning Findings

- Generated: `2026-04-26T19:37:54+00:00`
- Backend: `nest`
- Overall status: **PASS**
- Steps per run: `180`
- Base seed: `42`
- Fixed population: `True`
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier2_20260426_153749`

Tier 2 is a positive-control tier. These tests check whether the organism can learn causal cue/outcome structure, delayed consequence, and a switched rule after Tier 1 ruled out obvious fake learning.

## Artifact Index

- JSON manifest: `tier2_results.json`
- Summary CSV: `tier2_summary.csv`

## Summary

| Test | Status | Key metric | Notes |
| --- | --- | --- | --- |
| `nonstationary_switch` | **PASS** | pre=1, post_final=1, recovery=38 | criteria satisfied |

## nonstationary_switch

Status: **PASS**

Criteria:

| Criterion | Value | Rule | Pass |
| --- | ---: | --- | --- |
| pre-switch accuracy | 1 | >= 0.8 | yes |
| post-switch disruption | 0 | <= 0.9 | yes |
| final post-switch accuracy | 1 | >= 0.8 | yes |
| recovery time | 38 | <= 60 | yes |
| final inverse readout weight | -2.22428 | <= 0 | yes |

Artifacts:

- `timeseries_csv`: `nonstationary_switch_timeseries.csv`
- `plot_png`: `nonstationary_switch_timeseries.png`

![nonstationary_switch plot](nonstationary_switch_timeseries.png)
