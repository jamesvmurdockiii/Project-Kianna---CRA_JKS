# Tier 4.32g-r0 Multi-Chip Lifecycle Route/Source Repair Audit

- Generated: `2026-05-07T19:40:24+00:00`
- Runner revision: `tier4_32g_r0_lifecycle_route_source_audit_20260507_0001`
- Status: **PASS**
- Criteria: `14/14`
- Output directory: `<repo>/controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit`

## Claim Boundary

Tier 4.32g-r0 is local source/route QA only. It source-proves lifecycle event/trophic/mask-sync inter-chip MCPL route support before a hardware package. It is not SpiNNaker hardware evidence, not lifecycle scaling, not speedup evidence, not benchmark superiority, not true two-partition learning, not multi-shard learning, and not a native-scale baseline freeze.

## Decision

- 4.32g hardware prepare: `authorized_next`
- Next gate: `tier4_32g_two_chip_lifecycle_traffic_resource_hardware_smoke`
- True partition semantics: `blocked_until_4_32g_hardware_result`
- Native scale baseline freeze: `not_authorized`

## Route Contract

| Route | Profile | Key | Mask | Route | Purpose |
| --- | --- | --- | --- | --- | --- |
| `learning_local_mask_sync_consumer` | `learning_core` | `MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC, 0, 0)` | `0xFFF0F000 (match app/msg/shard; ignore lifecycle subtype and seq)` | `MC_CORE_ROUTE(learning_core)` | learning/consumer core receives lifecycle active-mask and lineage sync packets |
| `learning_outbound_lifecycle_event` | `learning_core` | `MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0)` | `0xFFF0F000 (match app/msg/shard; ignore lifecycle subtype and seq)` | `CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE` | event requests leave source chip over explicit link route |
| `learning_outbound_lifecycle_trophic` | `learning_core` | `MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0)` | `0xFFF0F000 (match app/msg/shard; ignore lifecycle subtype and seq)` | `CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE` | trophic update requests leave source chip over explicit link route |
| `lifecycle_local_event_request` | `lifecycle_core` | `MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0)` | `0xFFF0F000 (match app/msg/shard; ignore lifecycle subtype and seq)` | `MC_CORE_ROUTE(lifecycle_core)` | destination lifecycle core receives event requests locally |
| `lifecycle_local_trophic_request` | `lifecycle_core` | `MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0)` | `0xFFF0F000 (match app/msg/shard; ignore lifecycle subtype and seq)` | `MC_CORE_ROUTE(lifecycle_core)` | destination lifecycle core receives trophic requests locally |
| `lifecycle_outbound_mask_sync` | `lifecycle_core` | `MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC, 0, 0)` | `0xFFF0F000 (match app/msg/shard; ignore lifecycle subtype and seq)` | `CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE` | active-mask/lineage sync leaves lifecycle chip over explicit link route |

## Source Findings

| Finding | File | Token | Present | Purpose |
| --- | --- | --- | --- | --- |
| `event_msg_type` | `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `MCPL_MSG_LIFECYCLE_EVENT_REQUEST` | yes | Lifecycle event request message type exists. |
| `trophic_msg_type` | `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE` | yes | Lifecycle trophic update message type exists. |
| `sync_msg_type` | `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC` | yes | Lifecycle active-mask/lineage sync message type exists. |
| `request_route_macro` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE` | yes | Learning/source core can install outbound lifecycle request link routes. |
| `sync_route_macro` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE` | yes | Lifecycle core can install outbound active-mask sync link routes. |
| `event_route_install` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0` | yes | Route install code references lifecycle event request keys. |
| `trophic_route_install` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0` | yes | Route install code references lifecycle trophic update keys. |
| `sync_route_install` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC, 0, 0` | yes | Route install code references active-mask sync keys. |
| `duplicate_counter` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `lifecycle_duplicate_events` | yes | Duplicate lifecycle events are counted. |
| `stale_counter` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `lifecycle_stale_events` | yes | Stale lifecycle events are counted. |
| `missing_ack_counter` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `lifecycle_missing_acks` | yes | Missing lifecycle acks are counted. |
| `route_contract_test` | `coral_reef_spinnaker/spinnaker_runtime/tests/test_mcpl_lifecycle_interchip_route_contract.c` | `Tier 4.32g-r0 lifecycle MCPL inter-chip route contract tests` | yes | Local C route contract test exists. |
| `make_target` | `coral_reef_spinnaker/spinnaker_runtime/Makefile` | `test-mcpl-lifecycle-interchip-route-contract` | yes | Runtime Makefile exposes the lifecycle route contract test. |

## Local Test Commands

| Command | Return | Pass | Purpose | Logs |
| --- | ---: | --- | --- | --- |
| `make -C coral_reef_spinnaker/spinnaker_runtime test-mcpl-lifecycle-interchip-route-contract` | 0 | yes | Prove learning/lifecycle profile lifecycle inter-chip route entries locally. | `controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit/tier4_32g_r0_lifecycle_interchip_route_contract_stdout.txt`, `controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit/tier4_32g_r0_lifecycle_interchip_route_contract_stderr.txt` |
| `make -C coral_reef_spinnaker/spinnaker_runtime test-mcpl-interchip-route-contract` | 0 | yes | Ensure the existing 4.32d-r1 lookup route repair still passes. | `controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit/tier4_32g_r0_lookup_interchip_route_regression_stdout.txt`, `controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit/tier4_32g_r0_lookup_interchip_route_regression_stderr.txt` |
| `make -C coral_reef_spinnaker/spinnaker_runtime test-lifecycle-split` | 0 | yes | Ensure lifecycle duplicate/stale/mask-sync bookkeeping still passes. | `controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit/tier4_32g_r0_lifecycle_split_regression_stdout.txt`, `controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit/tier4_32g_r0_lifecycle_split_regression_stderr.txt` |

## Next Gates

| Gate | Decision | Question | Boundary |
| --- | --- | --- | --- |
| `Tier 4.32g - Two-Chip Lifecycle Traffic/Resource Hardware Smoke` | `authorized_next_prepare` | Can lifecycle event/trophic/mask-sync traffic cross the chip boundary with compact resource counters? | two-chip lifecycle traffic/resource smoke only; not full lifecycle scaling |
| `Tier 4.32h - True Partition Semantics Contract` | `blocked_until_4_32g_hardware_result` | What origin/target shard semantics are required before true two-partition cross-chip learning? | contract only; no hardware claim |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.32f prerequisite passed | `pass` | == pass | yes |
| 4.32f authorized 4.32g-r0 next | `tier4_32g_r0_multichip_lifecycle_route_source_repair_audit` | == tier4_32g_r0_multichip_lifecycle_route_source_repair_audit | yes |
| Tier 4.32e hardware learning prerequisite passed | `pass` | == pass | yes |
| source lifecycle route findings present | `[]` | empty | yes |
| route contract covers six required lifecycle paths | `6` | == 6 | yes |
| learning core has outbound event route | `["learning_local_mask_sync_consumer", "learning_outbound_lifecycle_event", "learning_outbound_lifecycle_trophic", "lifecycle_local_event_request", "lifecycle_local_trophic_request", "lifecycle_outbound_mask_sync"]` | contains learning_outbound_lifecycle_event | yes |
| learning core has outbound trophic route | `["learning_local_mask_sync_consumer", "learning_outbound_lifecycle_event", "learning_outbound_lifecycle_trophic", "lifecycle_local_event_request", "lifecycle_local_trophic_request", "lifecycle_outbound_mask_sync"]` | contains learning_outbound_lifecycle_trophic | yes |
| learning core has local mask-sync consumer route | `["learning_local_mask_sync_consumer", "learning_outbound_lifecycle_event", "learning_outbound_lifecycle_trophic", "lifecycle_local_event_request", "lifecycle_local_trophic_request", "lifecycle_outbound_mask_sync"]` | contains learning_local_mask_sync_consumer | yes |
| lifecycle core has local event route | `["learning_local_mask_sync_consumer", "learning_outbound_lifecycle_event", "learning_outbound_lifecycle_trophic", "lifecycle_local_event_request", "lifecycle_local_trophic_request", "lifecycle_outbound_mask_sync"]` | contains lifecycle_local_event_request | yes |
| lifecycle core has local trophic route | `["learning_local_mask_sync_consumer", "learning_outbound_lifecycle_event", "learning_outbound_lifecycle_trophic", "lifecycle_local_event_request", "lifecycle_local_trophic_request", "lifecycle_outbound_mask_sync"]` | contains lifecycle_local_trophic_request | yes |
| lifecycle core has outbound mask-sync route | `["learning_local_mask_sync_consumer", "learning_outbound_lifecycle_event", "learning_outbound_lifecycle_trophic", "lifecycle_local_event_request", "lifecycle_local_trophic_request", "lifecycle_outbound_mask_sync"]` | contains lifecycle_outbound_mask_sync | yes |
| local test commands passed | `[]` | empty | yes |
| 4.32g hardware prepare authorized | `authorized_next_prepare` | == authorized_next_prepare | yes |
| true partition semantics still blocked | `blocked_until_4_32g_hardware_result` | == blocked_until_4_32g_hardware_result | yes |
