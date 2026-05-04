# Tier 2 Controlled Learning Findings

- Generated: `2026-04-26T19:26:26+00:00`
- Backend: `nest`
- Overall status: **PASS**
- Steps per run: `180`
- Base seed: `42`
- Fixed population: `True`
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier2_20260426_152616`

Tier 2 is a positive-control tier. These tests check whether the organism can learn causal cue/outcome structure, delayed consequence, and a switched rule after Tier 1 ruled out obvious fake learning.

## Artifact Index

- JSON manifest: `tier2_results.json`
- Summary CSV: `tier2_summary.csv`

## Summary

| Test | Status | Key metric | Notes |
| --- | --- | --- | --- |
| `fixed_pattern` | **PASS** | tail_acc=0.822222, weight=-0.196321 | criteria satisfied |
| `delayed_reward` | **PASS** | tail_cue_acc=1, matured=175 | criteria satisfied |

## fixed_pattern

Status: **PASS**

Criteria:

| Criterion | Value | Rule | Pass |
| --- | ---: | --- | --- |
| tail strict accuracy | 0.822222 | >= 0.8 | yes |
| tail prediction/target correlation | 0.735131 | >= 0.7 | yes |
| learned inverse readout weight | -0.196321 | <= -0.05 | yes |

Artifacts:

- `timeseries_csv`: `fixed_pattern_timeseries.csv`
- `plot_png`: `fixed_pattern_timeseries.png`

![fixed_pattern plot](fixed_pattern_timeseries.png)


## delayed_reward

Status: **PASS**

Criteria:

| Criterion | Value | Rule | Pass |
| --- | ---: | --- | --- |
| tail cue-time strict accuracy | 1 | >= 0.65 | yes |
| matured delayed horizons | 175 | >= 1 | yes |
| delayed inverse readout weight | -0.255492 | <= -0.05 | yes |
| tail prediction/target correlation | 0.972326 | >= 0.5 | yes |

Artifacts:

- `timeseries_csv`: `delayed_reward_timeseries.csv`
- `plot_png`: `delayed_reward_timeseries.png`

![delayed_reward plot](delayed_reward_timeseries.png)
