# Tier 4.31d Native Temporal-Substrate Hardware Smoke

- Generated: `2026-05-06T20:10:50+00:00`
- Mode: `ingest`
- Status: **PASS**
- Runner revision: `tier4_31d_native_temporal_hardware_smoke_20260506_0003`

## Claim Boundary

Ingest confirms returned EBRAINS run-hardware artifacts only; baseline decisions remain separate.

## Summary

- source_results: `/tmp/tier4_31d_return_20260506_1501_public/tier4_31d_hw_results.json`
- returned_artifact_count: `21`
- hardware_status: `pass`
- scenario_statuses: `{'enabled': 'pass', 'frozen_state': 'pass', 'reset_each_update': 'pass', 'zero_state': 'pass'}`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| hardware results json exists | `/tmp/tier4_31d_return_20260506_1501_public/tier4_31d_hw_results.json` | exists | yes |
| hardware mode was run-hardware | `run-hardware` | == run-hardware | yes |
| hardware status pass | `pass` | == pass | yes |
| runner revision current | `tier4_31d_native_temporal_hardware_smoke_20260506_0003` | == tier4_31d_native_temporal_hardware_smoke_20260506_0003 | yes |
| returned artifacts preserved | `21` | > 0 | yes |

## Artifacts

- `results_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested/tier4_31d_hw_results.json`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested/tier4_31d_hw_report.md`
- `summary_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested/tier4_31d_hw_summary.csv`
