# Tier 7.7a - v2.5 Standardized Benchmark / Usefulness Scoreboard Contract

- Generated: `2026-05-09T12:13:13+00:00`
- Runner revision: `tier7_7a_v2_5_standardized_scoreboard_contract_20260509_0001`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier7_7a_20260509_v2_5_standardized_scoreboard_contract`

## Question

Does frozen v2.5 improve CRA's public/standardized usefulness posture beyond bounded synthetic planning diagnostics?

## Locked Primary Scoreboard

Mackey-Glass + Lorenz + NARMA10, length=8000, horizon=8, seeds=42,43,44, chronological 65/35 split

## Secondary Public Confirmation

C-MAPSS FD001 and NAB held-out action-cost tracks are included as secondary confirmation only, not as replacements for the standardized core.

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| v2.5 baseline exists | `<repo>/baselines/CRA_EVIDENCE_BASELINE_v2.5.json` | exists | yes |
| Tier 7.6e prerequisite passed | `pass` | == pass | yes |
| Tier 7.0j reference passed | `pass` | == pass | yes |
| primary standardized tasks locked | `4` | >= 4 including aggregate | yes |
| Mackey/Lorenz/NARMA included | `mackey_glass_future_prediction,lorenz_future_prediction,narma10_memory_system_identification,standard_three_geomean,short_medium_calibration_sweeps,cmapss_fd001_maintenance_utility,nab_heldout_alarm_action_cost` | contains all three | yes |
| 8000-step finite protocol locked | `['8000']` | == 8000 | yes |
| three same seeds locked | `['42,43,44']` | contains 42,43,44 | yes |
| chronological split locked | `chronological train 65%, test 35%,chronological train 65%, test 35%,chronological train 65%, test 35%` | train 65%, test 35% | yes |
| v2.5 candidate baseline included | `['cra_v2_5_host_side_candidate', 'cra_v2_3_generic_recurrent_reference', 'cra_v2_4_cost_aware_policy_reference', 'persistence', 'online_lms', 'ridge_lag', 'echo_state_network', 'small_gru', 'rolling_or_ewma_threshold_policy', 'online_logistic_or_perceptron_policy', 'always_wait_or_abstain', 'oracle_upper_bound']` | contains cra_v2_5 | yes |
| prior CRA references included | `['cra_v2_5_host_side_candidate', 'cra_v2_3_generic_recurrent_reference', 'cra_v2_4_cost_aware_policy_reference', 'persistence', 'online_lms', 'ridge_lag', 'echo_state_network', 'small_gru', 'rolling_or_ewma_threshold_policy', 'online_logistic_or_perceptron_policy', 'always_wait_or_abstain', 'oracle_upper_bound']` | contains v2.3 and v2.4 | yes |
| external baseline coverage | `8` | >= 6 non-CRA non-oracle baselines | yes |
| ESN and lag/ridge included | `['cra_v2_5_host_side_candidate', 'cra_v2_3_generic_recurrent_reference', 'cra_v2_4_cost_aware_policy_reference', 'persistence', 'online_lms', 'ridge_lag', 'echo_state_network', 'small_gru', 'rolling_or_ewma_threshold_policy', 'online_logistic_or_perceptron_policy', 'always_wait_or_abstain', 'oracle_upper_bound']` | contains echo_state_network and ridge_lag | yes |
| mandatory shams included | `['target_shuffle', 'time_shuffle', 'lag_only_control', 'state_disabled', 'memory_disabled', 'replay_disabled', 'prediction_disabled', 'self_evaluation_disabled', 'composition_routing_disabled', 'policy_action_disabled', 'planning_disabled', 'future_label_leak_guard']` | contains target/time/future/planning shams | yes |
| real-ish adapter decision explicit | `['cmapss_fd001_maintenance_utility', 'nab_heldout_alarm_action_cost']` | >= 2 secondary public tracks | yes |
| pass/fail criteria locked | `5` | >= 5 outcome classes | yes |
| expected scoring artifacts locked | `10` | >= 8 artifacts | yes |
| contract does not score benchmark | `False` | must remain false | yes |
| claim boundary blocks public usefulness | `Tier 7.7a is a contract/pre-registration gate only. It performs no scoring, freezes no new baseline, claims no public usefulness, and authorizes no hardware/native transfer.` | contains no public usefulness | yes |
| hardware/native transfer blocked | `Tier 7.7a is a contract/pre-registration gate only. It performs no scoring, freezes no new baseline, claims no public usefulness, and authorizes no hardware/native transfer.` | contains no hardware/native transfer | yes |
| next scoring gate named | `Tier 7.7b - v2.5 Standardized Benchmark / Usefulness Scoreboard Scoring Gate` | starts with Tier 7.7b | yes |

## Pass/Fail Boundary

| Outcome | Rule | Claim Allowed |
| --- | --- | --- |
| `strong_pass` | v2.5 improves all-three 8000-step geomean MSE versus v2.3 by >= 10% and paired CI excludes zero, while at least one public/real-ish secondary family also supports v2.5 or v2.4+v2.5 utility without sham match | bounded usefulness candidate; still not AGI, language, hardware/native transfer, or universal superiority |
| `standardized_progress_pass` | v2.5 improves all-three 8000-step geomean MSE versus v2.3 by >= 10% with paired support, but does not beat ESN/ridge or lacks public/real-ish confirmation | software mechanism progress on standardized dynamical benchmarks only |
| `localized_pass` | v2.5 improves one or two standardized tasks or a secondary public adapter, but not the all-three aggregate | localized task-family signal only; no broad usefulness claim |
| `no_promotion` | v2.5 fails to improve v2.3 on the all-three aggregate or matches shams/lag-only controls | no usefulness upgrade; route to failure localization before further mechanism layering |
| `stop_or_narrow` | full planned mechanism stack still fails standardized/public scoreboards after fair tests | stop broad usefulness track and narrow the paper to architecture/evidence/hardware substrate |

## Claim Boundary

Tier 7.7a is a contract/pre-registration gate only. It performs no scoring, freezes no new baseline, claims no public usefulness, and authorizes no hardware/native transfer.

Nonclaims:
- not a benchmark score
- not a public usefulness claim
- not proof of ESN/ridge/GRU superiority
- not a new baseline freeze
- not hardware or native-on-chip evidence
- not language, broad planning, AGI, or ASI evidence

## Next Gate

`Tier 7.7b - v2.5 Standardized Benchmark / Usefulness Scoreboard Scoring Gate`
