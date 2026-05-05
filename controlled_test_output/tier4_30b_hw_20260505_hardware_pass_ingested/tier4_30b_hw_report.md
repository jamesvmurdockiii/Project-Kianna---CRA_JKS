# Tier 4.30b-hw Lifecycle Hardware Smoke

- Generated: `2026-05-05T21:01:28+00:00`
- Mode: `ingest`
- Status: **PASS**
- Upload package: ``

## Claim Boundary

Ingest confirms returned EBRAINS run-hardware artifacts only; no new claim beyond Tier 4.30b-hw. Raw remote status is preserved when a known runner criterion defect is corrected.

## Summary

- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.226.17`
- selected_dest_cpu: `4`
- runtime_profile: `decoupled_memory_route`
- aplx_build_status: `pass`
- app_load_status: `pass`
- task_status: `pass`
- raw_remote_status: `fail`
- corrected_ingest_status: `pass`
- false_fail_correction: `rev-0001 checked cumulative readback_bytes instead of compact payload_len; raw payload_len was 68 and lifecycle state matched reference`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| hardware results json exists | `"/Users/james/Downloads/tier4_30b_hw_results.json"` | exists | yes |
| hardware mode was run-hardware | `"run-hardware"` | == run-hardware | yes |
| hardware status pass or known false-fail corrected | `{"corrected_status": "pass", "correction_applied": true, "raw_status": "fail"}` | raw pass OR corrected known false fail | yes |
| runner revision recognized | `"tier4_30b_lifecycle_hardware_smoke_20260505_0001"` | == tier4_30b_lifecycle_hardware_smoke_20260505_0002 or known false-fail rev | yes |
| returned artifacts preserved | `17` | > 0 | yes |
