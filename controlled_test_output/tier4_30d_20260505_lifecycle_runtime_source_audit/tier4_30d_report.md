# Tier 4.30d Multi-Core Lifecycle Runtime Source Audit

- Generated: `2026-05-05T22:11:32+00:00`
- Runner revision: `tier4_30d_lifecycle_runtime_source_audit_20260505_0001`
- Mode: `local-source-audit`
- Status: **PASS**
- Criteria: `14/14`

## Claim Boundary

Tier 4.30d is local source/runtime host evidence only. It proves a dedicated lifecycle_core profile, lifecycle inter-core stubs/counters, active-mask/count/lineage sync bookkeeping, and local ownership guards against the Tier 4.30c contract. It is not EBRAINS hardware evidence, not task-benefit evidence, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not a lifecycle baseline freeze.

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| Tier 4.30b source audit passed | `"pass"` | == pass | yes |  |
| Tier 4.30b-hw corrected ingest passed | `"pass"` | == pass | yes |  |
| Tier 4.30c split contract passed | `"pass"` | == pass | yes |  |
| Tier 4.30c split criteria complete | `"22/22"` | == 22/22 | yes |  |
| source surface tokens present | `[{"file": "coral_reef_spinnaker/spinnaker_runtime/src/config.h", "present": true, "purpose": "dedicated lifecycle_core profile id", "toke...` | all source checks present | yes |  |
| runtime test-lifecycle passed | `true` | returncode == 0 | yes |  |
| runtime test-lifecycle-split passed | `true` | returncode == 0 | yes |  |
| runtime test-profiles passed | `true` | returncode == 0 | yes |  |
| runtime test passed | `true` | returncode == 0 | yes |  |
| dedicated lifecycle_core profile id | `"PROFILE_LIFECYCLE_CORE=7"` | declared and locally tested | yes |  |
| non-lifecycle profiles reject direct lifecycle writes | `"test_profiles"` | CMD_LIFECYCLE_INIT/READ_STATE NAK outside lifecycle_core | yes |  |
| active-mask sync uses MCPL/multicast-target stub | `"spin1_send_mc_packet mask+lineage packets"` | present in lifecycle sync path | yes |  |
| payload length rule preserved | `"host_if_pack_lifecycle_summary required_len = 68"` | compact payload_len=68 unchanged | yes |  |
| no EBRAINS package generated | `"local-source-audit"` | mode is local only | yes |  |

## Source Checks

| File | Token | Present | Purpose |
| --- | --- | --- | --- |
| `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `PROFILE_LIFECYCLE_CORE` | yes | dedicated lifecycle_core profile id |
| `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `MCPL_MSG_LIFECYCLE_EVENT_REQUEST` | yes | event request MCPL message id |
| `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE` | yes | trophic update MCPL message id |
| `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC` | yes | active-mask sync MCPL message id |
| `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `MCPL_LIFECYCLE_SYNC_LINEAGE` | yes | lineage checksum sync subtype |
| `coral_reef_spinnaker/spinnaker_runtime/Makefile` | `RUNTIME_PROFILE),lifecycle_core` | yes | hardware/local build profile |
| `coral_reef_spinnaker/spinnaker_runtime/Makefile` | `test-lifecycle-split` | yes | local split host test target |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `cra_lifecycle_handle_event_request` | yes | lifecycle-core event request API |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `cra_lifecycle_receive_active_mask_sync` | yes | consumer active-mask sync API |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `lifecycle_duplicate_events` | yes | duplicate event counter |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `lifecycle_stale_events` | yes | stale event counter |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `lifecycle_missing_acks` | yes | missing-ack counter |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `cra_lifecycle_send_event_request_stub` | yes | learning-side event request stub |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `cra_lifecycle_send_trophic_update_stub` | yes | learning-side trophic request stub |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `spin1_send_mc_packet` | yes | MCPL/multicast-target send surface |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `_lifecycle_broadcast_active_mask_sync` | yes | active-mask sync broadcast stub |
| `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `_lifecycle_reject_duplicate_or_stale` | yes | duplicate/stale failure guard |
| `coral_reef_spinnaker/spinnaker_runtime/src/host_interface.c` | `CRA_RUNTIME_PROFILE_LIFECYCLE_HOST_SURFACE` | yes | direct lifecycle host surface guard |
| `coral_reef_spinnaker/spinnaker_runtime/src/host_interface.c` | `!defined(CRA_RUNTIME_PROFILE_LIFECYCLE_CORE)` | yes | decoupled catch-all excludes lifecycle_core |
| `coral_reef_spinnaker/spinnaker_runtime/tests/test_profiles.c` | `CMD_LIFECYCLE_INIT` | yes | non-lifecycle profile ownership guard test |
| `coral_reef_spinnaker/spinnaker_runtime/tests/test_lifecycle_split.c` | `active-mask/count/lineage sync send/receive bookkeeping` | yes | 4.30d split host test |
| `coral_reef_spinnaker/spinnaker_runtime/stubs/spin1_api.h` | `g_test_last_mc_key` | yes | host-side MCPL packet inspection |
| `coral_reef_spinnaker/spinnaker_runtime/stubs/spin1_api.h` | `g_test_mc_packet_count` | yes | host-side multi-packet MCPL inspection |

## Next Step

Tier 4.30e multi-core lifecycle hardware smoke package/run: package the 4.30d runtime source surface and prove real SpiNNaker execution/readback before any lifecycle sham-control hardware subset.
