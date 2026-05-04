# Tier 4.22i Custom Runtime Board Round-Trip Smoke

- Generated: `2026-04-30T20:26:52+00:00`
- Mode: `ingest`
- Status: **FAIL**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_fail`

Tier 4.22i tests the custom C runtime itself on hardware: build/load the tiny `.aplx`, send `CMD_READ_STATE`, and validate the compact state packet after simple command mutations.

## Claim Boundary

- `PREPARED` means the source bundle and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means board load plus `CMD_READ_STATE` round-trip worked on real SpiNNaker.
- This is not full CRA learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- aplx_build_status: `fail`
- command_roundtrip_status: `not_attempted`
- next_step_if_passed: `Regenerate cra_422i from fixed source and rerun Tier 4.22i.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| downloaded latest manifest exists | `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_fail/tier4_22i_latest_manifest.json` | `exists` | yes |
| custom runtime .aplx build pass | `fail` | `== pass` | no |
| CMD_READ_STATE roundtrip attempted | `not_attempted` | `== pass` | no |
| synthetic fallback zero | `0` | `== 0` | yes |

## Artifacts

- `latest_manifest`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_fail/tier4_22i_latest_manifest.json`
- `aplx_build_stderr`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_fail/tier4_22i_aplx_build_stderr.txt`
- `environment_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_fail/tier4_22i_environment.json`
- `roundtrip_result_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_fail/tier4_22i_roundtrip_result.json`
