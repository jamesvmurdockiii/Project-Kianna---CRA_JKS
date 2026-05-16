# Tier 4.32g - Two-Chip Lifecycle Traffic/Resource Hardware Smoke

- Generated: `2026-05-08T02:59:39+00:00`
- Mode: `ingest`
- Status: **FAIL**
- Runner revision: `tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260507_0002`

## Claim Boundary

Ingest confirms returned EBRAINS run-hardware artifacts only; baseline decisions remain separate.

## Summary

- raw_remote_status: `fail`
- lifecycle_traffic_status: `fail`
- traffic_counter_core_pass: `True`
- traffic_failure_classes: `['pause_control_surface']`
- returned_artifact_count: `30`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| hardware results json exists | `"<downloads>/tier4_32g_results.json"` | exists | yes |
| hardware mode was run-hardware | `"run-hardware"` | == run-hardware | yes |
| raw hardware status pass | `"fail"` | == pass | no |
| lifecycle traffic smoke pass | `"fail"` | == pass | no |
| traffic counters internally passed | `true` | == True | yes |
| returned artifacts preserved | `30` | >= 1 | yes |
| synthetic fallback zero | `false` | == False | yes |

## Next

Classify failed criteria before rerunning or scaling.
