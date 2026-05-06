# Tier 4.31c Native Temporal-Substrate Runtime Source Audit

- Generated: `2026-05-06T15:44:12+00:00`
- Runner revision: `tier4_31c_native_temporal_runtime_source_audit_20260506_0001`
- Mode: `local-source-audit`
- Status: **PASS**
- Criteria: `17/17`

## Claim Boundary

Tier 4.31c is local source/runtime host evidence only. It proves the custom C runtime owns the seven-EMA fixed-point temporal subset from Tier 4.31b with compact readback and behavior-backed shams. It is not EBRAINS hardware evidence, not speedup, not nonlinear recurrence, not native replay/sleep, not native macro eligibility, and not benchmark superiority.

## Source Contract

```json
{
  "compact_readback_len": 48,
  "non_owner_profiles": [
    "context_core",
    "route_core",
    "memory_core",
    "lifecycle_core"
  ],
  "owner_profile": "learning_core plus monolithic/decoupled local surfaces",
  "sham_modes": [
    "enabled",
    "zero_state",
    "frozen_state",
    "reset_each_update"
  ],
  "temporal_input_bound_raw": 98304,
  "temporal_timescale_checksum": 1811900589,
  "temporal_trace_bound_raw": 65536,
  "temporal_trace_count": 7
}
```

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| Tier 4.31a readiness passed | `"pass"` | == pass | yes |  |
| Tier 4.31a criteria complete | `"24/24"` | == 24/24 | yes |  |
| Tier 4.31b fixed-point reference passed | `"pass"` | == pass | yes |  |
| Tier 4.31b criteria complete | `"16/16"` | == 16/16 | yes |  |
| temporal command codes match contract | `{"CMD_TEMPORAL_INIT": 39, "CMD_TEMPORAL_READ_STATE": 41, "CMD_TEMPORAL_SHAM_MODE": 42, "CMD_TEMPORAL_UPDATE": 40}` | 39,40,41,42 | yes |  |
| command code collision scan | `{}` | no duplicate CMD_* numeric values | yes |  |
| fixed-point timescale table matches 4.31b | `{"alpha": [12893, 7248, 3850, 1985, 1008, 508, 255], "decay": [19874, 25519, 28917, 30782, 31759, 32259, 32512]}` | all raw constants present | yes |  |
| selected trace range remains +/-2 | `"TEMPORAL_TRACE_BOUND"` | == FP_FROM_FLOAT(2.0f) | yes |  |
| source surface tokens present | `[{"file": "coral_reef_spinnaker/spinnaker_runtime/src/config.h", "present": true, "purpose": "temporal init command code", "token": "CMD_...` | all source checks present | yes |  |
| EMA update is C-owned | `"g_temporal_traces + alpha/decay + FP_MUL"` | state_manager.c owns update equation | yes |  |
| compact temporal readback length | `"required_len = 48"` | host_if_pack_temporal_summary uses 48 bytes | yes |  |
| temporal host surface is ownership guarded | `"CRA_RUNTIME_PROFILE_TEMPORAL_HOST_SURFACE"` | learning/full/decoupled only | yes |  |
| runtime test-temporal-state passed | `true` | returncode == 0 | yes |  |
| runtime test-profiles passed | `true` | returncode == 0 | yes |  |
| runtime test passed | `true` | returncode == 0 | yes |  |
| lifecycle tests preserved | `{"test-lifecycle": true, "test-lifecycle-split": true}` | both returncode == 0 | yes |  |
| no EBRAINS package generated | `"local-source-audit"` | mode is local only | yes |  |

## Source Checks

| File | Token | Present | Purpose |
| --- | --- | --- | --- |
| `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `CMD_TEMPORAL_INIT            39` | yes | temporal init command code |
| `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `CMD_TEMPORAL_UPDATE          40` | yes | temporal update command code |
| `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `CMD_TEMPORAL_READ_STATE      41` | yes | temporal readback command code |
| `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `CMD_TEMPORAL_SHAM_MODE       42` | yes | temporal sham command code |
| `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `TEMPORAL_TRACE_BOUND         FP_FROM_FLOAT(2.0f)` | yes | Tier 4.31b selected trace range |
| `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `TEMPORAL_TIMESCALE_CHECKSUM  1811900589U` | yes | tau/alpha checksum |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `cra_temporal_summary_t` | yes | versioned temporal summary struct |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `cra_temporal_update` | yes | temporal update API |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `cra_temporal_get_trace` | yes | local host trace parity API |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `g_temporal_decay_raw` | yes | decay table owned by C runtime |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `g_temporal_alpha_raw` | yes | alpha table owned by C runtime |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `FP_MUL(g_temporal_decay_raw[i], g_temporal_traces[i])` | yes | fixed-point EMA decay equation |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `FP_MUL(g_temporal_alpha_raw[i], x)` | yes | fixed-point EMA input equation |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `TEMPORAL_SHAM_ZERO_STATE` | yes | zero-state sham behavior |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `TEMPORAL_SHAM_FROZEN_STATE` | yes | frozen-state sham behavior |
| `coral_reef_spinnaker/spinnaker_runtime/src/host_interface.h` | `host_if_pack_temporal_summary` | yes | compact temporal readback declaration |
| `coral_reef_spinnaker/spinnaker_runtime/src/host_interface.c` | `CRA_RUNTIME_PROFILE_TEMPORAL_HOST_SURFACE` | yes | temporal host-surface ownership guard |
| `coral_reef_spinnaker/spinnaker_runtime/src/host_interface.c` | `case CMD_TEMPORAL_READ_STATE` | yes | temporal readback dispatch |
| `coral_reef_spinnaker/spinnaker_runtime/src/host_interface.c` | `const uint8_t required_len = 48;` | yes | compact temporal payload length |
| `coral_reef_spinnaker/spinnaker_runtime/Makefile` | `test-temporal-state` | yes | local temporal C host test target |
| `coral_reef_spinnaker/spinnaker_runtime/tests/test_runtime.c` | `CMD_TEMPORAL_SHAM_MODE == 42` | yes | full runtime command constant test |
| `coral_reef_spinnaker/spinnaker_runtime/tests/test_profiles.c` | `CMD_TEMPORAL_READ_STATE` | yes | profile ownership guard tests |
| `coral_reef_spinnaker/spinnaker_runtime/tests/test_temporal_state.c` | `temporal fixed-point mirror updates` | yes | 4.31c direct fixed-point parity test |
| `coral_reef_spinnaker/spinnaker_runtime/tests/test_temporal_state.c` | `temporal compact host readback` | yes | 4.31c compact readback test |

## Next Step

Tier 4.31d native temporal-substrate hardware smoke: prepare and run a one-board/one-seed compact hardware probe only after this local source audit remains green.
