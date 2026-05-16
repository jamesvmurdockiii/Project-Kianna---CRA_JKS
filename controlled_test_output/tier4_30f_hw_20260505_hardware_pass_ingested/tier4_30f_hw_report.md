# Tier 4.30f Lifecycle Sham-Control Hardware Subset

- Generated: `2026-05-06T02:04:44+00:00`
- Mode: `ingest`
- Status: **PASS**
- Upload package: `cra_430f`

## Claim Boundary

Ingest confirms returned EBRAINS run-hardware artifacts only; no new claim beyond Tier 4.30f lifecycle sham-control hardware subset.

## Summary

- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.227.9`
- profile_builds_passed: `True`
- profile_loads_passed: `True`
- task_status: `pass`
- raw_remote_status: `pass`
- corrected_ingest_status: `pass`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| hardware results json exists | `"<downloads>/tier4_30f_hw_results.json"` | exists | yes |
| hardware mode was run-hardware | `"run-hardware"` | == run-hardware | yes |
| hardware status pass | `"pass"` | == pass | yes |
| runner revision current | `"tier4_30f_lifecycle_sham_hardware_subset_20260505_0001"` | == tier4_30f_lifecycle_sham_hardware_subset_20260505_0001 | yes |
| returned artifacts preserved | `35` | > 0 | yes |
