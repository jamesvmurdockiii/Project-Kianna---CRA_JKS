# Tier 2 Controlled Learning Findings

- Generated: `2026-05-05T18:37:21+00:00`
- Backend: `nest`
- Overall status: **PASS**
- Steps per run: `180`
- Base seed: `42`
- Fixed population: `True`
- Output directory: `<repo>/controlled_test_output/tier5_19c_20260505_fading_memory_regression/v2_1_compact_regression_full/v2_0_compact_regression_gate/v1_8_compact_regression/tier2_learning`

Tier 2 is a positive-control tier. These tests check whether the organism can learn causal cue/outcome structure, delayed consequence, and a switched rule after Tier 1 ruled out obvious fake learning.

## Artifact Index

- JSON manifest: `tier2_results.json`
- Summary CSV: `tier2_summary.csv`

## Summary

| Test | Status | Key metric | Notes |
| --- | --- | --- | --- |
| `fixed_pattern` | **PASS** | tail_acc=1, weight=-15.5361 | criteria satisfied |
| `delayed_reward` | **PASS** | tail_cue_acc=1, matured=175 | criteria satisfied |
| `nonstationary_switch` | **PASS** | pre=1, post_final=1, recovery=38 | criteria satisfied |

## fixed_pattern

Status: **PASS**

Criteria:

| Criterion | Value | Rule | Pass |
| --- | ---: | --- | --- |
| tail strict accuracy | 1 | >= 0.8 | yes |
| tail prediction/target correlation | 1 | >= 0.7 | yes |
| learned inverse readout weight | -15.5361 | <= -0.05 | yes |

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
| delayed inverse readout weight | -1.20456 | <= -0.05 | yes |
| tail prediction/target correlation | 0.984794 | >= 0.5 | yes |

Artifacts:

- `timeseries_csv`: `delayed_reward_timeseries.csv`
- `plot_png`: `delayed_reward_timeseries.png`

![delayed_reward plot](delayed_reward_timeseries.png)


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
