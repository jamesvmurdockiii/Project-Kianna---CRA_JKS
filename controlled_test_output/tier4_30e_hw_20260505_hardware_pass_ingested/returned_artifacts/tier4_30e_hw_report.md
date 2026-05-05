# Tier 4.30e Multi-Core Lifecycle Hardware Smoke

- Generated: `2026-05-05T22:45:30+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Upload package: `cra_430e`

## Claim Boundary

Multi-core lifecycle smoke only; not lifecycle task benefit, not sham-control success, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not a lifecycle baseline freeze.

## Summary

- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.226.145`
- profile_builds_passed: `True`
- profile_loads_passed: `True`
- task_status: `pass`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `"tier4_30e_multicore_lifecycle_hardware_smoke_20260505_0001"` | expected current source | yes |
| lifecycle split host tests pass | `"pass"` | == pass | yes |
| main.c host syntax check pass | `"pass"` | == pass | yes |
| all five profile builds pass | `{"context": "pass", "learning": "pass", "lifecycle": "pass", "memory": "pass", "route": "pass"}` | all == pass | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spy...` | status == pass and hostname acquired | yes |
| all five profile loads pass | `{"context": "pass", "learning": "pass", "lifecycle": "pass", "memory": "pass", "route": "pass"}` | all == pass | yes |
| lifecycle multi-core task pass | `"pass"` | == pass | yes |
| context profile read success | `true` | == True | yes |
| context profile id | `4` | == 4 | yes |
| context final profile read success | `true` | == True | yes |
| route profile read success | `true` | == True | yes |
| route profile id | `5` | == 5 | yes |
| route final profile read success | `true` | == True | yes |
| memory profile read success | `true` | == True | yes |
| memory profile id | `6` | == 6 | yes |
| memory final profile read success | `true` | == True | yes |
| learning profile read success | `true` | == True | yes |
| learning profile id | `3` | == 3 | yes |
| learning final profile read success | `true` | == True | yes |
| lifecycle profile read success | `true` | == True | yes |
| lifecycle profile id | `7` | == 7 | yes |
| lifecycle final profile read success | `true` | == True | yes |
| context rejects direct lifecycle read | `false` | == False | yes |
| route rejects direct lifecycle read | `false` | == False | yes |
| memory rejects direct lifecycle read | `false` | == False | yes |
| learning rejects direct lifecycle read | `false` | == False | yes |
| duplicate probe reset acknowledged | `true` | == True | yes |
| duplicate probe init succeeded | `true` | == True | yes |
| duplicate probe first event succeeded | `true` | == True | yes |
| duplicate probe duplicate event rejected | `false` | == False | yes |
| duplicate probe later event succeeded | `true` | == True | yes |
| duplicate probe stale event rejected | `false` | == False | yes |
| duplicate probe lifecycle_event_count | `2` | == 2 | yes |
| duplicate probe invalid_event_count | `2` | == 2 | yes |
| duplicate probe compact lifecycle payload length | `68` | == 68 | yes |
| canonical_32 reset acknowledged | `true` | == True | yes |
| canonical_32 lifecycle init succeeded | `true` | == True | yes |
| canonical_32 all lifecycle event commands succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true...` | all True | yes |
| canonical_32 lifecycle readback success | `true` | == True | yes |
| canonical_32 lifecycle schema version | `1` | == 1 | yes |
| canonical_32 pool size | `8` | == 8 | yes |
| canonical_32 founder count | `2` | == 2 | yes |
| canonical_32 active count | `6` | == 6 | yes |
| canonical_32 inactive count | `2` | == 2 | yes |
| canonical_32 active mask bits | `63` | == 63 | yes |
| canonical_32 attempted event count | `32` | == 32 | yes |
| canonical_32 lifecycle event count | `32` | == 32 | yes |
| canonical_32 cleavage count | `4` | == 4 | yes |
| canonical_32 adult birth count | `4` | == 4 | yes |
| canonical_32 death count | `4` | == 4 | yes |
| canonical_32 invalid event count | `0` | == 0 | yes |
| canonical_32 lineage checksum | `105428` | == 105428 | yes |
| canonical_32 trophic checksum | `466851` | == 466851 | yes |
| canonical_32 compact lifecycle payload length | `68` | == 68 | yes |
| boundary_64 reset acknowledged | `true` | == True | yes |
| boundary_64 lifecycle init succeeded | `true` | == True | yes |
| boundary_64 all lifecycle event commands succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true...` | all True | yes |
| boundary_64 lifecycle readback success | `true` | == True | yes |
| boundary_64 lifecycle schema version | `1` | == 1 | yes |
| boundary_64 pool size | `8` | == 8 | yes |
| boundary_64 founder count | `2` | == 2 | yes |
| boundary_64 active count | `7` | == 7 | yes |
| boundary_64 inactive count | `1` | == 1 | yes |
| boundary_64 active mask bits | `127` | == 127 | yes |
| boundary_64 attempted event count | `64` | == 64 | yes |
| boundary_64 lifecycle event count | `64` | == 64 | yes |
| boundary_64 cleavage count | `8` | == 8 | yes |
| boundary_64 adult birth count | `5` | == 5 | yes |
| boundary_64 death count | `8` | == 8 | yes |
| boundary_64 invalid event count | `0` | == 0 | yes |
| boundary_64 lineage checksum | `18496` | == 18496 | yes |
| boundary_64 trophic checksum | `761336` | == 761336 | yes |
| boundary_64 compact lifecycle payload length | `68` | == 68 | yes |
| no unhandled hardware exception | `true` | == True | yes |
| synthetic fallback zero | `0` | == 0 | yes |
