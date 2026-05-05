# Tier 4.30e Multi-Core Lifecycle Hardware Smoke

- Generated: `2026-05-05T22:57:26+00:00`
- Mode: `ingest`
- Status: **PASS**
- Upload package: `cra_430e`

## Claim Boundary

Ingest confirms returned EBRAINS run-hardware artifacts only; no new claim beyond Tier 4.30e hardware smoke.

## Summary

- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.226.145`
- profile_builds_passed: `True`
- profile_loads_passed: `True`
- task_status: `pass`
- raw_remote_status: `pass`
- corrected_ingest_status: `pass`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| hardware results json exists | `"/Users/james/Downloads/tier4_30e_hw_results.json"` | exists | yes |
| hardware mode was run-hardware | `"run-hardware"` | == run-hardware | yes |
| hardware status pass | `"pass"` | == pass | yes |
| runner revision current | `"tier4_30e_multicore_lifecycle_hardware_smoke_20260505_0001"` | == tier4_30e_multicore_lifecycle_hardware_smoke_20260505_0001 | yes |
| returned artifacts preserved | `31` | > 0 | yes |
