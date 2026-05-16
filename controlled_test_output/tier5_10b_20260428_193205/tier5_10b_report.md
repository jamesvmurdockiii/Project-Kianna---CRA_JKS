# Tier 5.10b Memory-Pressure Task Validation Findings

- Generated: `2026-04-28T23:32:05+00:00`
- Status: **FAIL**
- Steps: `180`
- Seeds: `42`
- Tasks: `delayed_context_cue,hidden_context_recurrence`
- Selected standard baselines: `sign_persistence,online_perceptron`
- Smoke mode: `True`
- Output directory: `<repo>/controlled_test_output/tier5_10b_20260428_193205`

Tier 5.10b validates whether repaired recurrence/context tasks actually require remembered context before CRA memory mechanisms are tested.

## Claim Boundary

- This is task-validation evidence, not CRA capability evidence.
- Oracle/context-memory controls are included to prove the task is solvable if the missing memory exists.
- A pass authorizes Tier 5.10c mechanism testing; it does not promote sleep/replay or any CRA memory mechanism.

## Task Pressure Comparisons

| Task | Sign persistence tail | Context memory tail | Oracle tail | Shuffled tail | Reset tail | Wrong-context tail | Best standard model | Best standard tail | Memory edge vs sign | Memory edge vs failure control | Ambiguous cues | Decisions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| delayed_context_cue | 1 | 1 | 1 | 0 | 1 | 0 | `sign_persistence` | 1 | 0 | 0 | 1 | 7 |
| hidden_context_recurrence | 1 | 1 | 1 | 1 | 1 | 0 | `online_perceptron` | 1 | 0 | 0 | 0 | 14 |

## Aggregate Matrix

| Task | Model | Family | Tail acc | All acc | Corr | Runtime s |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| delayed_context_cue | `memory_reset` | context_control | 1 | 0.571429 | 0.353553 | 0.000981292 |
| delayed_context_cue | `online_perceptron` | linear | 0 | 0.571429 | -0.240386 | 0.00153783 |
| delayed_context_cue | `oracle_context` | context_control | 1 | 1 | 1 | 0.000695625 |
| delayed_context_cue | `shuffled_context` | context_control | 0 | 0.142857 | -0.645497 | 0.00068725 |
| delayed_context_cue | `sign_persistence` | rule | 1 | 0.571429 | 0.353553 | 0.00153563 |
| delayed_context_cue | `stream_context_memory` | context_control | 1 | 1 | 1 | 0.000665625 |
| delayed_context_cue | `wrong_context` | context_control | 0 | 0 | -1 | 0.000714667 |
| hidden_context_recurrence | `memory_reset` | context_control | 1 | 1 | 1 | 0.00135692 |
| hidden_context_recurrence | `online_perceptron` | linear | 1 | 0.857143 | 0.886322 | 0.001115 |
| hidden_context_recurrence | `oracle_context` | context_control | 1 | 1 | 1 | 0.000905041 |
| hidden_context_recurrence | `shuffled_context` | context_control | 1 | 1 | 1 | 0.00074275 |
| hidden_context_recurrence | `sign_persistence` | rule | 1 | 1 | 1 | 0.00103408 |
| hidden_context_recurrence | `stream_context_memory` | context_control | 1 | 1 | 1 | 0.000809 |
| hidden_context_recurrence | `wrong_context` | context_control | 0 | 0 | -1 | 0.000875416 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| full task/model/seed matrix completed | 14 | == 14 | yes |  |
| feedback timing has no leakage violations | 0 | == 0 | yes |  |
| same current input supports opposite labels | False | == True | no |  |

Failure: Failed criteria: same current input supports opposite labels

## Artifacts

- `tier5_10b_results.json`: machine-readable manifest.
- `tier5_10b_report.md`: human findings and claim boundary.
- `tier5_10b_summary.csv`: aggregate task/model metrics.
- `tier5_10b_comparisons.csv`: task-pressure comparison table.
- `tier5_10b_fairness_contract.json`: predeclared comparison/leakage rules.
- `tier5_10b_task_pressure.png`: task-pressure plot.
- `*_timeseries.csv`: per-task/per-model/per-seed traces.

![task_pressure](tier5_10b_task_pressure.png)
