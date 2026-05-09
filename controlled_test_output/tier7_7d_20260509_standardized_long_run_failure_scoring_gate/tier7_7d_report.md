# Tier 7.7d Standardized Long-Run / Failure-Localization Scoring Gate

- Generated: `2026-05-09T14:02:25+00:00`
- Status: **PASS**
- Criteria: `12/12`
- Outcome: `benchmark_stream_invalid`
- Recommendation: Do not cite a long-run scoreboard; repair/preflight the finite NARMA10 long-run stream before scoring.

## Claim Boundary

Tier 7.7d scores the Tier 7.7c locked long-run/failure-localization contract. It may localize whether the 7.7b signal persists, grows, or collapses, but it does not freeze a new baseline, does not authorize hardware/native transfer, does not retune benchmarks after seeing results, and does not claim language, broad reasoning, AGI, or ASI.

## Length Summary

| Length | v2.5 MSE | v2.3 MSE | v2.3/v2.5 | Best external | v2.5 beats external | Outcome |
| ---: | ---: | ---: | ---: | --- | --- | --- |
| 8000 | 0.07354147408230836 | 0.09510713419835835 | 1.293244871484538 | fixed_esn_train_prefix_ridge_baseline | False | standardized_progress_pass |
| 16000 | 0.0602815095693387 | 0.07755622154747024 | 1.286567342150935 | fixed_esn_train_prefix_ridge_baseline | False | standardized_progress_pass |
| 32000 | 0.05576412828630235 | 0.07346274285537276 | 1.3173835064398884 | fixed_esn_train_prefix_ridge_baseline | False | standardized_progress_pass |

## Failure Decomposition

| Question | Answer | Evidence |
| --- | --- | --- |
| `mackey_signal_persistence` | `persists` | 8000:2.174136418713504;16000:2.1789436619366334;32000:2.2014559852150453 |
| `lorenz_state_reconstruction_gap` | `flat_or_negative` | 8000:0.9757367616924804;16000:0.9374655074272541;32000:1.045581301598168 |
| `narma_memory_depth_gap` | `invalid_nonfinite_stream` | 8000:0.9988366153400716;16000:None;32000:None |
| `external_baseline_gap` | `persists` | 8000:fixed_esn_train_prefix_ridge_baseline=0.01956749387082184;16000:fixed_esn_train_prefix_ridge_baseline=0.01698223410990479;32000:fixed_esn_train_prefix_ridge_baseline=0.014061445583241032 |
| `sham_specificity` | `separated` | 8000:target=14.145808812963091,time=14.206095620975516;16000:target=17.675414851130338,time=17.031595919037027;32000:target=18.322812430276535,time=17.967710931067813 |

## Nonclaims

- not a new baseline freeze
- not hardware/native evidence
- not public-usefulness superiority over ESN/ridge/online baselines unless the table shows it
- not a complete long-run scoreboard if any required benchmark stream is non-finite
- not a license to tune benchmarks after seeing long-run results
- not language, AGI, or ASI evidence
