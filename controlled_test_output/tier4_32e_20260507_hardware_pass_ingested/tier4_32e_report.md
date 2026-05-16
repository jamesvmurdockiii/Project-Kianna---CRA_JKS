# Tier 4.32e - Multi-Chip Learning Micro-Task

- Generated: `2026-05-07T17:31:28+00:00`
- Mode: `ingest`
- Status: **PASS**
- Runner revision: `tier4_32e_multichip_learning_microtask_20260507_0001`

## Claim Boundary

Ingest confirms returned EBRAINS run-hardware artifacts only; baseline decisions remain separate.

## Summary

- raw_remote_status: `pass`
- learning_microtask_status: `pass`
- returned_artifact_count: `42`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| hardware results json exists | `"<downloads>/tier4_32e_results.json"` | exists | yes |
| hardware mode was run-hardware | `"run-hardware"` | == run-hardware | yes |
| raw hardware status pass | `"pass"` | == pass | yes |
| learning microtask pass | `"pass"` | == pass | yes |
| enabled case present | `true` | present | yes |
| no-learning case present | `true` | present | yes |
| returned artifacts preserved | `42` | >= 1 | yes |
| true two-partition learning not attempted | `false` | == False | yes |
| synthetic fallback zero | `false` | == False | yes |

## Next

Ingest returned artifacts before authorizing the next multi-chip native-runtime gate.
