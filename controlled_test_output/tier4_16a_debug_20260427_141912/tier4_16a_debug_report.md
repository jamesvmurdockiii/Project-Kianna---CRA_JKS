# Tier 4.16a Delayed Cue Hardware Failure Analysis

- Generated: `2026-04-27T14:20:06+00:00`
- Status: **PASS**
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16a_debug_20260427_141912`

This diagnostic replays the exact Tier 4.16 `delayed_cue` config on local software backends and compares it to the failed hardware run.

## Diagnosis

- diagnosis: `software_config_or_metric_issue`
- next_step: `debug locally before another hardware run`
- metric_brittle: `True`
- min_tail_event_count: `3`
- tail_threshold: `0.85`

## Summary Rows

| Source | Backend | Seed | Tail Acc | Tail Corr | Tail Events | All Acc | Runtime |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| software | nest | 42 | 1 | 0.998203 | 3 | 0.933333 | 3.16559 |
| software | nest | 43 | 0.333333 | -0.322103 | 3 | 0.733333 | 3.11563 |
| software | nest | 44 | 0.666667 | 0.441613 | 3 | 0.8 | 3.07309 |
| software | brian2 | 42 | 1 | 0.998203 | 3 | 0.933333 | 13.7739 |
| software | brian2 | 43 | 0.333333 | -0.322103 | 3 | 0.733333 | 14.2998 |
| software | brian2 | 44 | 0.666667 | 0.441613 | 3 | 0.8 | 14.9288 |
| hardware_failed_4_16 | spinnaker | 42 | 1 | 0.998203 | 3 | 0.933333 | 842.672 |
| hardware_failed_4_16 | spinnaker | 43 | 0.333333 | -0.322103 | 3 | 0.733333 | 810.671 |
| hardware_failed_4_16 | spinnaker | 44 | 0.666667 | 0.441613 | 3 | 0.8 | 859.76 |

## Aggregate Rows

| Source | Backend | Runs | Tail Acc Mean | Tail Acc Min | Failed Seeds |
| --- | --- | ---: | ---: | ---: | --- |
| hardware_failed_4_16 | spinnaker | 3 | 0.666667 | 0.333333 | [43, 44] |
| software | brian2 | 3 | 0.666667 | 0.333333 | [43, 44] |
| software | nest | 3 | 0.666667 | 0.333333 | [43, 44] |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| software matrix completed | 6 | == 6 | yes |
| hardware failure artifact loaded | 3 | > 0 | yes |
| confirmed delayed-credit setting used | 0.2 | == 0.2 | yes |
| diagnosis generated | True | == True | yes |

## Artifacts

- `summary_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16a_debug_20260427_141912/tier4_16a_debug_summary.csv`
- `backend_summary_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16a_debug_20260427_141912/tier4_16a_debug_backend_summary.csv`
- `tail_events_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16a_debug_20260427_141912/tier4_16a_debug_tail_events.csv`
- `summary_png`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16a_debug_20260427_141912/tier4_16a_debug_summary.png`
- `hardware_fail_dir`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_124916_hardware_fail`
- `manifest_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16a_debug_20260427_141912/tier4_16a_debug_results.json`
- `report_md`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16a_debug_20260427_141912/tier4_16a_debug_report.md`
