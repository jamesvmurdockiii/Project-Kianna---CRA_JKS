# Tier 4.16a Delayed Cue Metric / Task Repair

- Generated: `2026-04-27T14:56:41+00:00`
- Status: **FAIL**
- Output directory: `controlled_test_output/tier4_16a_fix_nest_length_sweep_20260427_145400`

This local-only repair keeps `delayed_lr_0_20` fixed and increases delayed-cue run length so the tail metric has enough evaluation events.

## Diagnosis

- diagnosis: `longer_delayed_cue_local_fail`
- next_step: `debug delayed_cue locally before hardware`
- min_tail_event_count: `7`
- tail_threshold: `0.85`

## Backend Summary

| Steps | Backend | Runs | Tail Acc Mean | Tail Acc Min | Tail Events Min | Failed Seeds | Runtime Mean |
| ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 240 | nest | 3 | 0.857143 | 0.714286 | 7 | [43] | 6.25853 |
| 480 | nest | 3 | 0.911111 | 0.8 | 15 | [44] | 12.8103 |
| 960 | nest | 3 | 0.944444 | 0.833333 | 30 | [43] | 28.1308 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| software matrix completed | 9 | == 9 | yes |
| no backend execution failures | 0 | == 0 | yes |
| zero fallback/failure counters | 0 | == 0 | yes |
| minimum tail event count | 7 | >= 30 | no |
| minimum tail accuracy | 0.714286 | >= 0.85 | no |
| confirmed delayed-credit setting used | 0.2 | == 0.2 | yes |

## Artifacts

- `summary_csv`: `controlled_test_output/tier4_16a_fix_nest_length_sweep_20260427_145400/tier4_16a_fix_summary.csv`
- `backend_summary_csv`: `controlled_test_output/tier4_16a_fix_nest_length_sweep_20260427_145400/tier4_16a_fix_backend_summary.csv`
- `tail_events_csv`: `controlled_test_output/tier4_16a_fix_nest_length_sweep_20260427_145400/tier4_16a_fix_tail_events.csv`
- `summary_png`: `controlled_test_output/tier4_16a_fix_nest_length_sweep_20260427_145400/tier4_16a_fix_summary.png`
- `manifest_json`: `controlled_test_output/tier4_16a_fix_nest_length_sweep_20260427_145400/tier4_16a_fix_results.json`
- `report_md`: `controlled_test_output/tier4_16a_fix_nest_length_sweep_20260427_145400/tier4_16a_fix_report.md`
