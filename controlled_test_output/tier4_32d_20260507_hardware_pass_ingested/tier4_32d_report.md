# Tier 4.32d - Two-Chip Split-Role Single-Shard MCPL Lookup Smoke

- Generated: `2026-05-07T08:03:40+00:00`
- Mode: `ingest`
- Status: **PASS**
- Runner revision: `tier4_32d_interchip_mcpl_smoke_20260507_0001`

## Claim Boundary

Ingest confirms returned EBRAINS run-hardware artifacts only; baseline decisions remain separate.

## Summary

- raw_remote_status: `pass`
- interchip_smoke_status: `pass`
- returned_artifact_count: `40`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| hardware results json exists | `"<downloads>/tier4_32d_results.json"` | exists | yes |
| hardware mode was run-hardware | `"run-hardware"` | == run-hardware | yes |
| raw hardware status pass | `"pass"` | == pass | yes |
| interchip smoke pass | `"pass"` | == pass | yes |
| returned artifacts preserved | `40` | >= 1 | yes |
| true two-partition learning not attempted | `false` | == False | yes |
| synthetic fallback zero | `false` | == False | yes |

## Next

Ingest returned artifacts before authorizing Tier 4.32e multi-chip learning micro-task.
