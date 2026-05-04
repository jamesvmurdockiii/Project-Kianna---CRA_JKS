# Tier 4.22h Compact Readback / Build-Command Readiness

- Generated: `2026-04-30T23:43:56+00:00`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_22h_20260430_compact_readback_acceptance`

Tier 4.22h adds compact custom-runtime state readback and records build-command readiness. It does not claim a board load or hardware command round-trip unless those are actually run.

## Summary

- Tier 4.22g latest status: `pass`
- Host C tests passed: `True`
- Static readback checks passed: `30` / `30`
- Compact readback payload bytes: `73`
- APLX build status: `not_attempted_spinnaker_tools_missing`
- Board load/command roundtrip status: `not_attempted`
- Custom-runtime learning hardware allowed: `False`
- Next gate: `Tier 4.22i tiny EBRAINS/board custom-runtime load + CMD_READ_STATE round-trip smoke, then minimal closed-loop learning only if that passes.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22h_compact_readback_acceptance_20260430_0006` | `expected current source` | yes |
| Tier 4.22g optimization pass exists | `pass` | `== pass` | yes |
| custom C host tests pass | `0` | `returncode == 0 and ALL TESTS PASSED` | yes |
| all static readback checks pass | `30/30` | `all pass` | yes |
| compact readback schema <= SDP payload | `73` | `<= 255 bytes` | yes |
| APLX build status recorded honestly | `not_attempted_spinnaker_tools_missing` | `pass or not_attempted_spinnaker_tools_missing` | yes |
| board load/command roundtrip not overclaimed | `not_attempted` | `not_attempted locally` | yes |
| custom-runtime learning hardware remains blocked | `False` | `False until board command roundtrip passes` | yes |

## Readback Schema

| Offset | Field | Type | Meaning |
| --- | --- | --- | --- |
| `0` | `cmd` | `u8` | CMD_READ_STATE |
| `1` | `status` | `u8` | 0 = ok |
| `2` | `schema_version` | `u8` | 1 |
| `3` | `reserved` | `u8` | reserved/alignment |
| `4` | `timestep` | `u32` | runtime timestep |
| `8` | `neuron_count` | `u32` | live neurons |
| `12` | `synapse_count` | `u32` | live synapses |
| `16` | `active_trace_count` | `u32` | active eligibility traces |
| `20` | `active_slots` | `u32` | active context slots |
| `24` | `slot_writes` | `u32` | context writes |
| `28` | `slot_hits` | `u32` | context hits |
| `32` | `slot_misses` | `u32` | context misses |
| `36` | `slot_evictions` | `u32` | context evictions |
| `40` | `decisions` | `u32` | readout decisions |
| `44` | `reward_events` | `u32` | reward events |
| `48` | `pending_created` | `u32` | pending horizons created |
| `52` | `pending_matured` | `u32` | pending horizons matured |
| `56` | `pending_dropped` | `u32` | pending horizons dropped |
| `60` | `active_pending` | `u32` | active pending horizons |
| `64` | `readout_weight` | `s32` | s16.15 readout weight |
| `68` | `readout_bias` | `s32` | s16.15 readout bias |
| `72` | `flags` | `u8` | reserved |

## Claim Boundary

- This is local compact-readback and build-command readiness evidence.
- It is not a hardware run, board load, command round-trip, speedup result, or custom-runtime learning pass.
- If local `spinnaker_tools` are missing, `.aplx` build is recorded as not attempted rather than treated as failure or success.
- The next hardware-facing gate must run a tiny board load/command round-trip before any custom-runtime learning job.
