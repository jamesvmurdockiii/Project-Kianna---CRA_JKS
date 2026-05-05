# Tier 4.30b-hw Lifecycle Hardware Smoke

- Generated: `2026-05-05T20:49:02+00:00`
- Mode: `run-hardware`
- Status: **FAIL**
- Upload package: `cra_430b`

## Claim Boundary

Single-core lifecycle metadata/readback smoke only; not lifecycle task benefit, not multi-core lifecycle migration, not speedup, and not a lifecycle baseline freeze.

## Summary

- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.226.17`
- selected_dest_cpu: `4`
- runtime_profile: `decoupled_memory_route`
- aplx_build_status: `pass`
- app_load_status: `pass`
- task_status: `fail`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `"tier4_30b_lifecycle_hardware_smoke_20260505_0001"` | expected current source | yes |
| lifecycle host tests pass | `"pass"` | == pass | yes |
| main.c host syntax check pass | `"pass"` | == pass | yes |
| hardware runtime profile selected | `"decoupled_memory_route"` | == decoupled_memory_route | yes |
| custom runtime .aplx build pass | `"pass"` | == pass | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spy...` | status == pass and hostname acquired | yes |
| custom runtime app load pass | `"pass"` | == pass | yes |
| lifecycle hardware task pass | `"fail"` | == pass | no |
| canonical_32 scenario executed | `"fail"` | == pass | no |
| boundary_64 scenario executed | `"fail"` | == pass | no |
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
| canonical_32 compact lifecycle readback bytes | `2312` | == 68 | no |
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
| boundary_64 compact lifecycle readback bytes | `4488` | == 68 | no |
| synthetic fallback zero | `0` | == 0 | yes |
