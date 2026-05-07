# Tier 4.32a-hw - Single-Shard MCPL-First EBRAINS Scale Stress

- Generated: `2026-05-07T00:24:55+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Runner revision: `tier4_32a_hw_single_shard_scale_stress_20260506_0001`

## Claim Boundary

Tier 4.32a-hw is a single-shard single-chip EBRAINS hardware stress over the repaired Tier 4.32a-r1 MCPL protocol. It is not replicated-shard stress, not multi-chip evidence, not speedup evidence, not static reef partitioning, not benchmark superiority evidence, and not a native-scale baseline freeze.

## Summary

- point04_status: `pass`
- point05_status: `pass`
- single_shard_only: `True`
- replicated_stress_attempted: `False`
- synthetic_fallback_used: `False`
- claim_boundary: `Tier 4.32a-hw is a single-shard single-chip EBRAINS hardware stress over the repaired Tier 4.32a-r1 MCPL protocol. It is not replicated-shard stress, not multi-chip evidence, not speedup evidence, not static reef partitioning, not benchmark superiority evidence, and not a native-scale baseline freeze.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `"tier4_32a_hw_single_shard_scale_stress_20260506_0001"` | expected | yes |
| synthetic fallback zero | `0` | == 0 | yes |
| scope limited to single-shard points | `["point_04c_reference", "point_05c_lifecycle"]` | == allowed points only | yes |
| point04 runner status | `"pass"` | == pass | yes |
| point04 pending_created | `48` | == 48 | yes |
| point04 pending_matured | `48` | == 48 | yes |
| point04 active_pending cleared | `0` | == 0 | yes |
| point04 lookup_requests | `144` | == 144 | yes |
| point04 lookup_replies | `144` | == 144 | yes |
| point04 stale_replies zero | `0` | == 0 | yes |
| point04 duplicate_replies zero | `0` | == 0 | yes |
| point04 timeouts zero | `0` | == 0 | yes |
| point05 host source checks pass | `"pass"` | == pass | yes |
| point05 main syntax check pass | `"pass"` | == pass | yes |
| point05 all five profile builds pass | `{"context": "pass", "learning": "pass", "lifecycle": "pass", "memory": "pass", "route": "pass"}` | all == pass | yes |
| point05 hardware target acquired | `"pass"` | == pass | yes |
| point05 all five profile loads pass | `{"context": "pass", "learning": "pass", "lifecycle": "pass", "memory": "pass", "route": "pass"}` | all == pass | yes |
| point05 enabled lifecycle bridge pass | `"pass"` | == pass | yes |
| point05 lifecycle readback compact | `68` | >= 68 | yes |
| point05 pending_created | `96` | == 96 | yes |
| point05 pending_matured | `96` | == 96 | yes |
| point05 active_pending cleared | `0` | == 0 | yes |
| point05 lookup_requests | `288` | == 288 | yes |
| point05 lookup_replies | `288` | == 288 | yes |
| point05 stale_replies zero | `0` | == 0 | yes |
| point05 duplicate_replies zero | `0` | == 0 | yes |
| point05 timeouts zero | `0` | == 0 | yes |
| point05 no unhandled hardware exception | `true` | == True | yes |
| point05 attempted after point04 pass | `"pass"` | attempted and pass | yes |
| replicated shard stress not attempted | `"not_attempted"` | == not_attempted | yes |
| native-scale baseline freeze not authorized | `"not_authorized"` | == not_authorized | yes |

## Next

Ingest returned artifacts before authorizing replicated 8/12/16-core stress.
