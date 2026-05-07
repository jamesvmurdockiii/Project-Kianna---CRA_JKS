# Tier 4.32a-hw-replicated - Replicated-Shard MCPL-First EBRAINS Scale Stress

- Generated: `2026-05-07T01:14:36+00:00`
- Mode: `ingest`
- Status: **PASS**
- Runner revision: `tier4_32a_hw_replicated_shard_stress_20260507_0001`

## Claim Boundary

Ingest confirms returned EBRAINS run-hardware artifacts only; baseline decisions remain separate.

## Summary

- raw_remote_status: `pass`
- point08_status: `pass`
- point12_status: `pass`
- point16_status: `pass`
- returned_artifact_count: `80`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| hardware results json exists | `"/tmp/tier4_32a_hw_replicated_return_20260507/tier4_32a_hw_replicated_results.json"` | exists | yes |
| hardware mode was run-hardware | `"run-hardware"` | == run-hardware | yes |
| raw hardware status pass | `"pass"` | == pass | yes |
| point08 pass | `"pass"` | == pass | yes |
| point12 pass | `"pass"` | == pass | yes |
| point16 pass | `"pass"` | == pass | yes |
| returned artifacts preserved | `80` | >= 1 | yes |
| single-chip replicated-shard only | `true` | == True | yes |
| synthetic fallback zero | `false` | == False | yes |

## Next

Ingest returned artifacts before authorizing Tier 4.32b static reef partitioning/resource mapping.
