# Tier 4.31d Native Temporal-Substrate Hardware Smoke

- Generated: `2026-05-06T18:39:35+00:00`
- Mode: `ingest`
- Status: **FAIL**
- Runner revision: `tier4_31d_native_temporal_hardware_smoke_20260506_0003`

## Claim Boundary

Ingest only preserves returned artifacts; it cannot create hardware evidence without run-hardware results.

## Summary

- ingest_dir: `/Users/james/Downloads`
- returned_artifact_count: `2`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| hardware results json exists | `/Users/james/Downloads` | contains tier4_31d_hw_results.json | no |
| partial returned artifacts preserved | `2` | > 0 when partial artifacts exist | yes |

## Artifacts

- `results_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_31d_hw_20260506_incomplete_return/tier4_31d_hw_results.json`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_31d_hw_20260506_incomplete_return/tier4_31d_hw_report.md`
- `summary_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier4_31d_hw_20260506_incomplete_return/tier4_31d_hw_summary.csv`
