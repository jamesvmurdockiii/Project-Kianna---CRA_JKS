# Tier 4.16a Delayed Cue Metric / Task Repair

- Generated: `2026-04-27T14:53:36+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_16a_fix_20260427_143252`

This local-only repair keeps `delayed_lr_0_20` fixed and increases delayed-cue run length so the tail metric has enough evaluation events.

## Diagnosis

- diagnosis: `longer_delayed_cue_local_pass`
- next_step: `run one-seed delayed_cue seed43 hardware probe`
- min_tail_event_count: `46`
- tail_threshold: `0.85`

## Backend Summary

| Steps | Backend | Runs | Tail Acc Mean | Tail Acc Min | Tail Events Min | Failed Seeds | Runtime Mean |
| ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1500 | brian2 | 3 | 1 | 1 | 46 | [] | 363.802 |
| 1500 | nest | 3 | 1 | 1 | 46 | [] | 50.5591 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| software matrix completed | 6 | == 6 | yes |
| no backend execution failures | 0 | == 0 | yes |
| zero fallback/failure counters | 0 | == 0 | yes |
| minimum tail event count | 46 | >= 30 | yes |
| minimum tail accuracy | 1 | >= 0.85 | yes |
| confirmed delayed-credit setting used | 0.2 | == 0.2 | yes |

## Artifacts

- `summary_csv`: `<repo>/controlled_test_output/tier4_16a_fix_20260427_143252/tier4_16a_fix_summary.csv`
- `backend_summary_csv`: `<repo>/controlled_test_output/tier4_16a_fix_20260427_143252/tier4_16a_fix_backend_summary.csv`
- `tail_events_csv`: `<repo>/controlled_test_output/tier4_16a_fix_20260427_143252/tier4_16a_fix_tail_events.csv`
- `summary_png`: `<repo>/controlled_test_output/tier4_16a_fix_20260427_143252/tier4_16a_fix_summary.png`
- `manifest_json`: `<repo>/controlled_test_output/tier4_16a_fix_20260427_143252/tier4_16a_fix_results.json`
- `report_md`: `<repo>/controlled_test_output/tier4_16a_fix_20260427_143252/tier4_16a_fix_report.md`
