# Tier 4.31d Native Temporal-Substrate Hardware Smoke

- Generated: `2026-05-06T17:56:56+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Runner revision: `tier4_31d_native_temporal_hardware_smoke_20260506_0001`

## Claim Boundary

Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.

## Summary

- upload_package: `cra_431d`
- upload_bundle: `/Users/james/JKS:CRA/controlled_test_output/tier4_31d_hw_20260506_prepared/ebrains_upload_bundle/cra_431d`
- stable_upload_folder: `/Users/james/JKS:CRA/ebrains_jobs/cra_431d`
- job_command: `cra_431d/experiments/tier4_31d_native_temporal_hardware_smoke.py --mode run-hardware --output-dir tier4_31d_hw_job_output`
- what_i_need_from_user: `Upload `cra_431d` to EBRAINS/JobManager and run the emitted command.`
- claim_boundary: `Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.31c prerequisite passed | `pass` | == pass | yes |
| runtime temporal/profile host checks pass | `pass` | == pass | yes |
| runner py_compile pass | `0` | == 0 | yes |
| upload bundle created | `/Users/james/JKS:CRA/controlled_test_output/tier4_31d_hw_20260506_prepared/ebrains_upload_bundle/cra_431d` | exists | yes |
| stable upload folder created | `/Users/james/JKS:CRA/ebrains_jobs/cra_431d` | exists | yes |
| run-hardware command emitted | `cra_431d/experiments/tier4_31d_native_temporal_hardware_smoke.py --mode run-hardware --output-dir tier4_31d_hw_job_output` | contains --mode run-hardware | yes |
| bundle controller includes temporal parser | `parse_temporal_payload` | present | yes |

## Artifacts

- `results_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_31d_hw_20260506_prepared/tier4_31d_hw_results.json`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_31d_hw_20260506_prepared/tier4_31d_hw_report.md`
- `summary_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier4_31d_hw_20260506_prepared/tier4_31d_hw_summary.csv`
