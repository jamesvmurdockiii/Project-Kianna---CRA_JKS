# Tier 4.30g Lifecycle Task-Benefit / Resource Bridge Hardware Findings

- Generated: `2026-05-06T03:09:59+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Runner revision: `tier4_30g_lifecycle_task_benefit_resource_bridge_20260506_0001`

## Claim Boundary

Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.

## Summary

- upload_package: `cra_430g`
- upload_bundle: `controlled_test_output/tier4_30g_hw_20260506_prepared/ebrains_upload_bundle/cra_430g`
- stable_upload_folder: `<repo>/ebrains_jobs/cra_430g`
- job_command: `cra_430g/experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py --mode run-hardware --output-dir tier4_30g_hw_job_output`
- what_i_need_from_user: `Upload `cra_430g` to EBRAINS/JobManager and run the emitted command.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| local 4.30g contract pass | `"pass"` | == pass | yes |
| runtime source checks pass | `"pass"` | == pass | yes |
| main.c syntax check pass | `"pass"` | == pass | yes |
| runner py_compile pass | `0` | == 0 | yes |
| upload bundle created | `"controlled_test_output/tier4_30g_hw_20260506_prepared/ebrains_upload_bundle/cra_430g"` | exists | yes |
| stable upload folder created | `"<repo>/ebrains_jobs/cra_430g"` | exists | yes |
| run-hardware command emitted | `"cra_430g/experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py --mode run-hardware --output-dir tier4_30g_hw_job_output"` | contains --mode run-hardware | yes |
