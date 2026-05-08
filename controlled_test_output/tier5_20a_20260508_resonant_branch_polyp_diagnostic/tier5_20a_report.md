# Tier 5.20a - Resonant Branch Polyp Internal-Model Diagnostic

- Generated: `2026-05-08T21:49:59+00:00`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier5_20a_20260508_resonant_branch_polyp_diagnostic`
- Outcome: `resonant_branch_not_promoted`

## Claim Boundary

Tier 5.20a is a software-only diagnostic for an optional polyp internal model. It keeps the current 16-excitatory-neuron budget as 16 resonant LIF-style branches and compares against v2.3, v2.2, lag/reservoir/ESN controls, and branch shams. It is not a canonical organism change, not hardware evidence, and not a baseline freeze.

## Summary

- Recommendation: Do not integrate into the core organism; either park it or redesign the branch objective/tasks.
- Wins versus v2.3: `2`
- Sham-separated tasks: `2`
- Material regressions versus v2.3: `4`
- All-task resonant geomean MSE: `0.4152508773763422`
- All-task v2.3 geomean MSE: `0.2610804850928049`
- All-task resonant/v2.3 margin: `0.6287295206752507`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier5_20a_resonant_branch_polyp_diagnostic_20260508_0001` | expected current source | yes |
| all tasks known | `['mackey_glass', 'lorenz', 'narma10', 'variable_delay_multi_cue', 'hidden_context_reentry', 'anomaly_detection_stream']` | subset of standard/Tier 6.2a diagnostics | yes |
| same branch budget declared | `16` | == 16 current excitatory neurons | yes |
| all required models present | `['fixed_esn_train_prefix_ridge_baseline', 'fixed_random_reservoir_online_control', 'lag_only_online_lms_control', 'resonant_branch_polyp_candidate', 'resonant_flat_tau_sham', 'resonant_rate_only_sham', 'resonant_shuffled_branch_state_sham', 'v2_2_fading_memory_reference', 'v2_3_generic_bounded_recurrent_state']` | all present | yes |
| all runs completed | `162/162` | all pass | yes |
| resonant shams present | `['resonant_flat_tau_sham', 'resonant_rate_only_sham', 'resonant_shuffled_branch_state_sham']` | all present | yes |
| v2.3 reference present | `True` | == true | yes |
| public standard tasks included | `['mackey_glass', 'lorenz', 'narma10']` | all included | yes |
| targeted temporal/anomaly task included | `True` | == true | yes |
| classification produced | `resonant_branch_not_promoted` | non-empty | yes |
| software only | `no PyNN/SpiNNaker calls` | true | yes |

## Per-Task Diagnostic

| Task | Resonant MSE | v2.3 MSE | Margin vs v2.3 | Sham separated |
| --- | ---: | ---: | ---: | --- |
| mackey_glass | `0.21511077053226083` | `0.1453460894726496` | `0.6756802047289938` | no |
| lorenz | `0.1953691106309355` | `0.04513029824387598` | `0.2310001724332458` | no |
| narma10 | `0.44584224223392366` | `0.3975134504355782` | `0.8916011377562819` | no |
| variable_delay_multi_cue | `0.5370030651631308` | `0.6018249561593203` | `1.1207104674095256` | yes |
| hidden_context_reentry | `0.6600379342053403` | `0.28923555697135966` | `0.4382105057637148` | yes |
| anomaly_detection_stream | `0.8497340287266496` | `0.8679964915748696` | `1.0214919754073952` | no |

## Artifacts

- `tier5_20a_results.json`
- `tier5_20a_summary.csv`
- `tier5_20a_aggregate.csv`
- `tier5_20a_timeseries.csv` if `--no-timeseries` was not used
- `tier5_20a_branch_contract.json`
