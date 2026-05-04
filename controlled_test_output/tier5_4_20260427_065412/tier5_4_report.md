# Tier 5.4 Delayed-Credit Confirmation Findings

- Generated: `2026-04-27T11:11:14+00:00`
- Status: **PASS**
- CRA backend: `nest`
- Seeds: `42, 43, 44`
- Run lengths: `960, 1500`
- Tasks: `delayed_cue,hard_noisy_switching`
- Candidate: `cra_delayed_lr_0_20`
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier5_4_20260427_065412`

Tier 5.4 confirms whether the Tier 5.3 delayed-credit candidate survives a direct comparison against current CRA and the external baselines at 960 and 1500 steps.

## Claim Boundary

- This is controlled software evidence, not hardware evidence.
- Passing confirms the delayed-credit candidate under these tasks/run lengths; it does not automatically authorize a superiority claim.
- Superiority over external baselines may be claimed only where the candidate also beats the best external baseline, not merely the median.
- If this passes, the next hardware step is Tier 4.16 using the confirmed delayed-credit setting.

## Task Findings

| Task | Classification | Min candidate tail | Final candidate tail | Min delta vs current | Min delta vs median | Min delta vs best | Max seed std |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| delayed_cue | `confirmed` | 1 | 1 | 0.275362 | 0 | 0 | 0 |
| hard_noisy_switching | `confirmed_vs_median` | 0.515723 | 0.515723 | 0.0691824 | 0.0157233 | -0.0490196 | 0.0898544 |

## Confirmation Rows

| Steps | Task | Current CRA tail | Candidate tail | External median | Best external | Best model | Delta vs current | Delta vs median | Delta vs best |
| ---: | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 960 | delayed_cue | 0.555556 | 1 | 1 | 1 | `echo_state_network` | 0.444444 | 0 | 0 |
| 1500 | delayed_cue | 0.724638 | 1 | 1 | 1 | `echo_state_network` | 0.275362 | 0 | 0 |
| 960 | hard_noisy_switching | 0.45098 | 0.539216 | 0.47549 | 0.588235 | `random_sign` | 0.0882353 | 0.0637255 | -0.0490196 |
| 1500 | hard_noisy_switching | 0.446541 | 0.515723 | 0.5 | 0.553459 | `online_perceptron` | 0.0691824 | 0.0157233 | -0.0377358 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| full delayed-credit confirmation matrix completed | 120 | == 120 | yes |  |
| all aggregate cells produced | 40 | == 40 | yes |  |
| all requested run lengths represented | [960, 1500] | == [960, 1500] | yes |  |
| confirmation rows generated | 4 | == 4 | yes |  |
| delayed_cue stays near 1.0 tail accuracy | 1 | >= 0.95 | yes |  |
| hard_noisy_switching beats external median | 0.0157233 | >= -0 | yes |  |
| candidate does not regress versus current CRA | 0.0691824 | >= -0.02 | yes |  |
| variance across seeds acceptable | 0.0898544 | <= 0.18 | yes |  |

## Artifacts

- `tier5_4_results.json`: machine-readable manifest.
- `tier5_4_summary.csv`: aggregate task/model/run-length metrics.
- `tier5_4_confirmation.csv`: current CRA, candidate, median external, and best external comparison rows.
- `tier5_4_findings.csv`: task-level confirmation findings.
- `tier5_4_confirmation.png`: confirmation curves and deltas.
- `tier5_4_seed_variance.png`: CRA seed variance summary.
- `*_timeseries.csv`: per-run-length/per-task/per-model/per-seed online traces.

## Plots

![confirmation](tier5_4_confirmation.png)

![seed_variance](tier5_4_seed_variance.png)
