# Tier 6.3 Lifecycle Sham-Control Findings

- Generated: `2026-04-28T16:50:41+00:00`
- Backend: `nest`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier6_3_20260428_121504`

Tier 6.3 defends the Tier 6.1 lifecycle/self-scaling result against capacity, random-event, bookkeeping, trophic, dopamine, and plasticity sham explanations.

## Claim Boundary

- PASS supports a software-only claim that lifecycle dynamics add value beyond the tested sham explanations.
- PASS is not hardware lifecycle evidence, not on-chip birth/death, not custom-C runtime evidence, and not AGI/compositionality evidence.
- Replay/shuffle controls are audit artifacts, not independently learning biological mechanisms.
- FAIL means the organism/ecology claim must narrow or the lifecycle mechanism needs repair before promotion.

## Summary

- expected_actual_runs: `36`
- actual_runs: `36`
- intact_non_handoff_lifecycle_events_sum: `26`
- fixed_non_handoff_lifecycle_events_sum: `0`
- actual_lineage_integrity_failures: `0`
- performance_control_win_count: `10`
- fixed_max_win_count: `2`
- random_event_replay_win_count: `2`
- lineage_shuffle_detected_count: `6`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | ---: | --- | --- |
| actual-run matrix completed | 36 | == 36 | yes |
| intact lifecycle produces events | 26 | >= 1 | yes |
| fixed capacity controls have no lifecycle events | 0 | == 0 | yes |
| actual-run lineage integrity remains clean | 0 | == 0 | yes |
| no actual-run aggregate extinction | 0 | == 0 | yes |
| all performance sham comparisons emitted | 10 | >= 10 | yes |
| intact beats performance shams | 10 | >= 8 | yes |
| intact beats fixed max-pool capacity controls | 2 | >= 2 | yes |
| event-count replay does not explain advantage | 2 | >= 2 | yes |
| lineage-ID shuffle is detected | 6 | >= 1 | yes |
| active-mask shuffle audit emitted | True | is True | yes |

## Case Aggregates

| Task | Regime | Control | Group | Tail Acc | Abs Corr | Recovery | Events | Mean Alive | Lineage Fails |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `hard_noisy_switching` | `life4_16` | `active_mask_shuffle` | `telemetry_shuffle` | 0.539216 | 0.0749826 | 30.6377 | 14 | 8.53437 | 0 |
| `hard_noisy_switching` | `life4_16` | `fixed_initial` | `capacity_control` | 0.470588 | 0.063205 | 39.3478 | 0 | 4 | 0 |
| `hard_noisy_switching` | `life4_16` | `fixed_max` | `capacity_control` | 0.5 | 0.0695225 | 29.2319 | 0 | 16 | 0 |
| `hard_noisy_switching` | `life4_16` | `intact` | `intact` | 0.539216 | 0.0749826 | 30.6377 | 14 | 8.53437 | 0 |
| `hard_noisy_switching` | `life4_16` | `lineage_id_shuffle` | `lineage_shuffle` | 0.539216 | 0.0749826 | 30.6377 | 14 | 8.53437 | 3 |
| `hard_noisy_switching` | `life4_16` | `no_dopamine` | `mechanism_ablation` | 0.519608 | 0.0340968 | 21.6812 | 18 | 9.39687 | 0 |
| `hard_noisy_switching` | `life4_16` | `no_plasticity` | `mechanism_ablation` | 0.519608 | 0.0340968 | 21.6812 | 15 | 8.77743 | 0 |
| `hard_noisy_switching` | `life4_16` | `no_trophic` | `mechanism_ablation` | 0.470588 | 0.063205 | 39.3478 | 0 | 4 | 0 |
| `hard_noisy_switching` | `life4_16` | `random_event_replay` | `event_replay_sham` | 0.470588 | 0.063205 | 39.3478 | 14 | 4 | 0 |
| `hard_noisy_switching` | `life8_32` | `active_mask_shuffle` | `telemetry_shuffle` | 0.519608 | 0.0768039 | 28 | 12 | 11.4601 | 0 |
| `hard_noisy_switching` | `life8_32` | `fixed_initial` | `capacity_control` | 0.480392 | 0.0650302 | 30.4783 | 0 | 8 | 0 |
| `hard_noisy_switching` | `life8_32` | `fixed_max` | `capacity_control` | 0.470588 | 0.0620372 | 32.9275 | 0 | 32 | 0 |
| `hard_noisy_switching` | `life8_32` | `intact` | `intact` | 0.519608 | 0.0768039 | 28 | 12 | 11.4601 | 0 |
| `hard_noisy_switching` | `life8_32` | `lineage_id_shuffle` | `lineage_shuffle` | 0.519608 | 0.0768039 | 28 | 12 | 11.4601 | 3 |
| `hard_noisy_switching` | `life8_32` | `no_dopamine` | `mechanism_ablation` | 0.519608 | 0.0340968 | 21.6812 | 12 | 11.5694 | 0 |
| `hard_noisy_switching` | `life8_32` | `no_plasticity` | `mechanism_ablation` | 0.519608 | 0.0340968 | 21.6812 | 12 | 11.8267 | 0 |
| `hard_noisy_switching` | `life8_32` | `no_trophic` | `mechanism_ablation` | 0.480392 | 0.0650302 | 30.4783 | 0 | 8 | 0 |
| `hard_noisy_switching` | `life8_32` | `random_event_replay` | `event_replay_sham` | 0.480392 | 0.0650302 | 30.4783 | 12 | 8 | 0 |

## Intact Lifecycle vs Sham Controls

| Task | Regime | Control | Tail Delta | Corr Delta | Recovery Improvement | Efficiency Delta | Advantage | Reason |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `hard_noisy_switching` | `life4_16` | `active_mask_shuffle` | 0 | 0 | 0 | -0.000173415 | no | `` |
| `hard_noisy_switching` | `life4_16` | `fixed_initial` | 0.0686275 | 0.0117776 | 8.71014 | -0.0111071 | yes | `tail_accuracy,switch_recovery` |
| `hard_noisy_switching` | `life4_16` | `fixed_max` | 0.0392157 | 0.00546008 | -1.4058 | 0.00382194 | yes | `tail_accuracy,active_population_efficiency` |
| `hard_noisy_switching` | `life4_16` | `lineage_id_shuffle` | 0 | 0 | 0 | 0 | no | `` |
| `hard_noisy_switching` | `life4_16` | `no_dopamine` | 0.0196078 | 0.0408858 | -8.95652 | 0.00194295 | yes | `all_accuracy,prediction_correlation` |
| `hard_noisy_switching` | `life4_16` | `no_plasticity` | 0.0196078 | 0.0408858 | -8.95652 | 0.00121978 | yes | `all_accuracy,prediction_correlation` |
| `hard_noisy_switching` | `life4_16` | `no_trophic` | 0.0686275 | 0.0117776 | 8.71014 | -0.0111071 | yes | `tail_accuracy,switch_recovery` |
| `hard_noisy_switching` | `life4_16` | `random_event_replay` | 0.0686275 | 0.0117776 | 8.71014 | -0.0111071 | yes | `tail_accuracy,switch_recovery` |
| `hard_noisy_switching` | `life8_32` | `active_mask_shuffle` | 0 | 0 | 0 | 0.000259844 | no | `` |
| `hard_noisy_switching` | `life8_32` | `fixed_initial` | 0.0392157 | 0.0117738 | 2.47826 | -0.00266864 | yes | `tail_accuracy,switch_recovery` |
| `hard_noisy_switching` | `life8_32` | `fixed_max` | 0.0490196 | 0.0147668 | 4.92754 | 0.0045483 | yes | `tail_accuracy,switch_recovery,active_population_efficiency` |
| `hard_noisy_switching` | `life8_32` | `lineage_id_shuffle` | 0 | 0 | 0 | 0 | no | `` |
| `hard_noisy_switching` | `life8_32` | `no_dopamine` | 1.11022e-16 | 0.0427071 | -6.31884 | 0.000835757 | yes | `all_accuracy,prediction_correlation` |
| `hard_noisy_switching` | `life8_32` | `no_plasticity` | 1.11022e-16 | 0.0427071 | -6.31884 | 0.00116406 | yes | `all_accuracy,prediction_correlation` |
| `hard_noisy_switching` | `life8_32` | `no_trophic` | 0.0392157 | 0.0117738 | 2.47826 | -0.00266864 | yes | `tail_accuracy,switch_recovery` |
| `hard_noisy_switching` | `life8_32` | `random_event_replay` | 0.0392157 | 0.0117738 | 2.47826 | -0.00266864 | yes | `tail_accuracy,switch_recovery` |

## Artifacts

- `tier6_3_results.json`: machine-readable manifest.
- `tier6_3_summary.csv`: aggregate intact/control metrics.
- `tier6_3_comparisons.csv`: intact-vs-sham deltas.
- `tier6_3_lifecycle_events.csv`: birth/death/handoff/sham event log.
- `tier6_3_lineage_final.csv`: final lineage audit table.
- `tier6_3_sham_manifest.json`: control definitions and claim boundaries.
- `*_timeseries.csv`: per-task/per-regime/per-control/per-seed traces.

## Plots

![summary](tier6_3_sham_summary.png)

![alive](tier6_3_alive_population.png)
