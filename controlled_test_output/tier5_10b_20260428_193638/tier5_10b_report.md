# Tier 5.10b Memory-Pressure Task Validation Findings

- Generated: `2026-04-28T23:36:38+00:00`
- Status: **PASS**
- Steps: `180`
- Seeds: `42`
- Tasks: `delayed_context_cue,hidden_context_recurrence`
- Selected standard baselines: `sign_persistence,online_perceptron`
- Smoke mode: `True`
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier5_10b_20260428_193638`

Tier 5.10b validates whether repaired recurrence/context tasks actually require remembered context before CRA memory mechanisms are tested.

## Claim Boundary

- This is task-validation evidence, not CRA capability evidence.
- Oracle/context-memory controls are included to prove the task is solvable if the missing memory exists.
- A pass authorizes Tier 5.10c mechanism testing; it does not promote sleep/replay or any CRA memory mechanism.

## Task Pressure Comparisons

| Task | Sign persistence acc | Context memory acc | Oracle acc | Shuffled acc | Reset acc | Wrong-context acc | Best standard model | Best standard acc | Memory edge vs sign | Memory edge vs failure control | Ambiguous cues | Decisions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| delayed_context_cue | 0.571429 | 1 | 1 | 0.428571 | 0.571429 | 0 | `online_perceptron` | 0 | 0.428571 | 0.571429 | 2 | 7 |
| hidden_context_recurrence | 0.5 | 1 | 1 | 0.5 | 0.5 | 0 | `online_perceptron` | 0.25 | 0.5 | 0.5 | 2 | 12 |

## Aggregate Matrix

| Task | Model | Family | Tail acc | All acc | Corr | Runtime s |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| delayed_context_cue | `memory_reset` | context_control | 0 | 0.571429 | 0.166667 | 0.000750375 |
| delayed_context_cue | `online_perceptron` | linear | 0 | 0 | -0.674088 | 0.00121796 |
| delayed_context_cue | `oracle_context` | context_control | 1 | 1 | 1 | 0.00160467 |
| delayed_context_cue | `shuffled_context` | context_control | 0 | 0.428571 | None | 0.000718042 |
| delayed_context_cue | `sign_persistence` | rule | 0 | 0.571429 | 0.166667 | 0.00157554 |
| delayed_context_cue | `stream_context_memory` | context_control | 1 | 1 | 1 | 0.000822916 |
| delayed_context_cue | `wrong_context` | context_control | 0 | 0 | -1 | 0.000872 |
| hidden_context_recurrence | `memory_reset` | context_control | 0 | 0.5 | 0 | 0.00143425 |
| hidden_context_recurrence | `online_perceptron` | linear | 0.333333 | 0.25 | -0.359172 | 0.001107 |
| hidden_context_recurrence | `oracle_context` | context_control | 1 | 1 | 1 | 0.0007775 |
| hidden_context_recurrence | `shuffled_context` | context_control | 0.333333 | 0.5 | 0.125 | 0.00072125 |
| hidden_context_recurrence | `sign_persistence` | rule | 0 | 0.5 | 0 | 0.00108317 |
| hidden_context_recurrence | `stream_context_memory` | context_control | 1 | 1 | 1 | 0.000875333 |
| hidden_context_recurrence | `wrong_context` | context_control | 0 | 0 | -1 | 0.000792417 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| full task/model/seed matrix completed | 14 | == 14 | yes |  |
| feedback timing has no leakage violations | 0 | == 0 | yes |  |
| same current input supports opposite labels | True | == True | yes |  |

## Artifacts

- `tier5_10b_results.json`: machine-readable manifest.
- `tier5_10b_report.md`: human findings and claim boundary.
- `tier5_10b_summary.csv`: aggregate task/model metrics.
- `tier5_10b_comparisons.csv`: task-pressure comparison table.
- `tier5_10b_fairness_contract.json`: predeclared comparison/leakage rules.
- `tier5_10b_task_pressure.png`: task-pressure plot.
- `*_timeseries.csv`: per-task/per-model/per-seed traces.

![task_pressure](tier5_10b_task_pressure.png)
