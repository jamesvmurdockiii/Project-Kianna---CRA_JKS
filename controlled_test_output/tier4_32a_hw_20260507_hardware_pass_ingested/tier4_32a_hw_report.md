# Tier 4.32a-hw - Single-Shard MCPL-First EBRAINS Scale Stress

- Generated: `2026-05-07T00:28:48+00:00`
- Mode: `ingest`
- Status: **PASS**
- Runner revision: `tier4_32a_hw_single_shard_scale_stress_20260506_0001`

## Claim Boundary

Ingest confirms returned EBRAINS run-hardware artifacts only; baseline decisions remain separate.

## Summary

- raw_remote_status: `pass`
- point04_status: `pass`
- point05_status: `pass`
- returned_artifact_count: `63`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| hardware results json exists | `"/tmp/tier4_32a_hw_return_20260507/tier4_32a_hw_results.json"` | exists | yes |
| hardware mode was run-hardware | `"run-hardware"` | == run-hardware | yes |
| raw hardware status pass | `"pass"` | == pass | yes |
| point04 pass | `"pass"` | == pass | yes |
| point05 pass | `"pass"` | == pass | yes |
| returned artifacts preserved | `63` | >= 1 | yes |
| single-shard only | `true` | == True | yes |
| synthetic fallback zero | `false` | == False | yes |

## Next

Ingest returned artifacts before authorizing replicated 8/12/16-core stress.
