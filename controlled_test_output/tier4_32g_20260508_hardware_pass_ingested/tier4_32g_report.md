# Tier 4.32g - Two-Chip Lifecycle Traffic/Resource Hardware Smoke

- Generated: `2026-05-08T17:09:21+00:00`
- Mode: `ingest`
- Status: **PASS**
- Runner revision: `tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003`

## Claim Boundary

Ingest confirms returned EBRAINS run-hardware artifacts only; baseline decisions remain separate.

## Summary

- raw_remote_status: `pass`
- hardware_runner_revision: `tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003`
- ingest_runner_revision: `tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003`
- stale_package_detected: `False`
- lifecycle_traffic_status: `pass`
- traffic_counter_core_pass: `True`
- traffic_failure_classes: `[]`
- returned_artifact_count: `30`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| hardware results json exists | `"<downloads>/tier4_32g_results (2).json"` | exists | yes |
| hardware mode was run-hardware | `"run-hardware"` | == run-hardware | yes |
| raw hardware status pass | `"pass"` | == pass | yes |
| lifecycle traffic smoke pass | `"pass"` | == pass | yes |
| traffic counters internally passed | `true` | == True | yes |
| returned artifacts preserved | `30` | >= 1 | yes |
| synthetic fallback zero | `false` | == False | yes |

## Next

Ingest returned artifacts before authorizing the next multi-chip native-runtime gate.
