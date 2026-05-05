# Tier 4.30b-hw Lifecycle Hardware Smoke

- Generated: `2026-05-05T20:39:00+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Upload package: `cra_430b`

## Claim Boundary

Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.

## Summary


## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| reference scenarios generated | `["canonical_32", "boundary_64"]` | canonical_32 and boundary_64 | yes |
| lifecycle host tests pass | `"pass"` | == pass | yes |
| main.c host syntax check pass | `"pass"` | == pass | yes |
| upload bundle created | `"controlled_test_output/tier4_30b_hw_20260505_prepared/ebrains_upload_bundle/cra_430b"` | exists | yes |
| stable upload folder created | `"/Users/james/JKS:CRA/ebrains_jobs/cra_430b"` | exists | yes |
| run-hardware command emitted | `"cra_430b/experiments/tier4_30b_lifecycle_hardware_smoke.py --mode run-hardware --output-dir tier4_30b_hw_job_output"` | contains --mode run-hardware | yes |
