# Tier 4.30e Multi-Core Lifecycle Hardware Smoke

- Generated: `2026-05-05T22:20:02+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Upload package: `cra_430e`

## Claim Boundary

Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.

## Summary

- job_command: `cra_430e/experiments/tier4_30e_multicore_lifecycle_hardware_smoke.py --mode run-hardware --output-dir tier4_30e_hw_job_output`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| reference scenarios generated | `["canonical_32", "boundary_64"]` | canonical_32 and boundary_64 | yes |
| lifecycle split host tests pass | `"pass"` | == pass | yes |
| main.c host syntax check pass | `"pass"` | == pass | yes |
| upload bundle created | `"controlled_test_output/tier4_30e_hw_20260505_prepared/ebrains_upload_bundle/cra_430e"` | exists | yes |
| stable upload folder created | `"/Users/james/JKS:CRA/ebrains_jobs/cra_430e"` | exists | yes |
| run-hardware command emitted | `"cra_430e/experiments/tier4_30e_multicore_lifecycle_hardware_smoke.py --mode run-hardware --output-dir tier4_30e_hw_job_output"` | contains --mode run-hardware | yes |
