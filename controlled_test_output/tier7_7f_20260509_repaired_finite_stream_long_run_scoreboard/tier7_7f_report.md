# Tier 7.7f Repaired Finite-Stream Long-Run Scoreboard

- Generated: `2026-05-09T14:30:32+00:00`
- Status: **PASS**
- Criteria: `16/16`
- Outcome: `mackey_only_localized`
- Recommendation: The signal remains localized to Mackey-Glass; prioritize failure-specific diagnostics before adding mechanisms.
- Repaired generator: `narma10_reduced_input_u02`

## Claim Boundary

Tier 7.7f reruns the locked long-run scoreboard after the Tier 7.7e repaired NARMA stream preflight. It may classify whether the v2.5 signal is long-run confirmed, Mackey-only localized, baseline-gap limited, collapsed, or stop/narrow, but it does not freeze a baseline, does not authorize hardware/native transfer, and does not permit repaired U(0,0.2) NARMA results to be silently mixed with prior U(0,0.5) NARMA scores.

## Length Summary

| Length | v2.5 MSE | v2.3 MSE | v2.3/v2.5 | Best external | v2.5 beats external | Outcome |
| ---: | ---: | ---: | ---: | --- | --- | --- |
| 8000 | 0.07883788661755275 | 0.10212220538862919 | 1.2953442788748264 | fixed_esn_train_prefix_ridge_baseline | False | standardized_progress_pass |
| 16000 | 0.06742211156054204 | 0.08617445900899577 | 1.2781334938110767 | fixed_esn_train_prefix_ridge_baseline | False | standardized_progress_pass |
| 32000 | 0.06348488921920546 | 0.0843176664528898 | 1.3281533210485936 | fixed_esn_train_prefix_ridge_baseline | False | standardized_progress_pass |

## Failure Decomposition

| Question | Answer | Evidence |
| --- | --- | --- |
| `mackey_signal_persistence` | `persists` | 8000:2.174136418713504;16000:2.1789436619366334;32000:2.2014559852150453 |
| `lorenz_state_reconstruction_gap` | `flat_or_negative` | 8000:0.9757367616924804;16000:0.9374655074272541;32000:1.045581301598168 |
| `narma_memory_depth_gap` | `flat_or_negative` | 8000:1.0037286721080247;16000:1.005431889410481;32000:1.0060811257251472 |
| `external_baseline_gap` | `persists` | 8000:fixed_esn_train_prefix_ridge_baseline=0.01854979357974845;16000:fixed_esn_train_prefix_ridge_baseline=0.016937159264644727;32000:fixed_esn_train_prefix_ridge_baseline=0.013594601360987484 |
| `sham_specificity` | `separated` | 8000:target=13.051573831446873,time=13.103437902681176;16000:target=15.232871472258834,time=14.619404456137536;32000:target=16.312294506439212,time=15.962588986319375 |

## Nonclaims

- not a new baseline freeze
- not hardware/native evidence
- not public-usefulness superiority over ESN/ridge/online baselines unless the table shows it
- not a complete long-run scoreboard if any required benchmark stream is non-finite
- not a license to tune benchmarks after seeing long-run results
- not language, AGI, or ASI evidence
