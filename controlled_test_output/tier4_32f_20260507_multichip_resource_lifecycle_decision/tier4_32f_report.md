# Tier 4.32f Multi-Chip Resource/Lifecycle Decision Contract

- Generated: `2026-05-07T19:04:46+00:00`
- Runner revision: `tier4_32f_multichip_resource_lifecycle_decision_20260507_0001`
- Status: **PASS**
- Criteria: `22/22`
- Output directory: `<repo>/controlled_test_output/tier4_32f_20260507_multichip_resource_lifecycle_decision`

## Claim Boundary

Tier 4.32f is a local decision/contract gate after the first two-chip learning-bearing hardware micro-task. It does not run SpiNNaker hardware, does not claim speedup, does not claim benchmark superiority, does not claim true two-partition learning, does not claim lifecycle scaling, does not claim multi-shard learning, and does not freeze a native-scale baseline.

## Decision

- Selected direction: `multi_chip_lifecycle_traffic_with_resource_counters`
- Selected next gate: `tier4_32g_r0_multichip_lifecycle_route_source_repair_audit`
- Hardware package status: `blocked_until_4_32g_r0_passes`
- Lifecycle inter-chip routes source-proven now: `False`
- True partition learning: `blocked_until_origin_target_shard_semantics`
- Native scale baseline freeze: `not_authorized`

## Why

Tier 4.32d proved two-chip communication/readback. Tier 4.32e proved a
tiny two-chip learning-bearing micro-task with enabled-vs-no-learning
separation. The next organism-scale question is lifecycle traffic across
chips, but lifecycle inter-chip route entries are not source-proven yet.
So 4.32f authorizes a local 4.32g-r0 source/route repair audit and blocks
the 4.32g hardware package until that audit passes.

## 4.32e Learning Case Summary

| Case | Kind | Events | Lookups | Stale | Duplicate | Timeouts | Pending | Readout | Payload |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |
| `enabled_lr_0_25` | `enabled` | 32 | 96/96 | 0 | 0 | 0 | `32/32/0` | `32768/0` | 105 |
| `no_learning_lr_0_00` | `no_learning` | 32 | 96/96 | 0 | 0 | 0 | `32/32/0` | `0/0` | 105 |

## Candidate Directions

| Direction | Decision | Reason | Required Before Hardware | Boundary |
| --- | --- | --- | --- | --- |
| `multi_chip_lifecycle_traffic` | `selected_but_requires_4_32g_r0_source_repair` | The organism/self-scaling claim needs lifecycle traffic to move across chips after lookup/learning already passed. | Add/prove explicit inter-chip lifecycle route entries and lifecycle readback counters before EBRAINS hardware. | Lifecycle traffic/resource smoke only; not full lifecycle scaling or autonomous growth. |
| `resource_timing_characterization` | `include_inside_lifecycle_smoke_not_standalone_next` | Resource/timing counters are necessary, but a timing-only run would not advance the organism-scale mechanism path. | Predeclare payload length, message count, stale/duplicate/timeout counters, wall/runtime fields, and per-role compact readback. | Engineering measurement only, not speedup. |
| `true_two_partition_cross_chip_learning` | `blocked` | Current evidence still uses one shard field and one source/remote partition; origin/target shard semantics are not defined. | Define origin shard, target shard, role ownership, and cross-partition credit semantics before attempting this. | No true two-partition learning claim. |
| `benchmarks_or_speedup` | `blocked` | Benchmark/speedup claims require stable native scale mechanics and fair software baselines first. | Complete native scale/lifecycle gates and freeze a justified native-scale baseline. | No benchmark or speedup claim from 4.32f. |
| `CRA_NATIVE_SCALE_BASELINE_v0_5` | `not_authorized` | 4.32e is a major pass but still tiny and single-shard; lifecycle/resource and multi-shard semantics remain open. | At minimum, pass a contract-backed lifecycle/resource gate and decide true partition semantics. | No native-scale baseline freeze. |

## Next Gates

| Gate | Status | Question | Pass | Fail |
| --- | --- | --- | --- | --- |
| `Tier 4.32g-r0 - Multi-Chip Lifecycle Route/Source Repair Audit` | `authorized_next` | Can lifecycle MCPL event/trophic/mask-sync traffic be made chip/shard explicit enough for a two-chip lifecycle smoke? | All lifecycle route/source checks pass locally and the 4.32g hardware package is authorized. | Do not package EBRAINS; repair route/key/readback/counter semantics first. |
| `Tier 4.32g - Two-Chip Lifecycle Traffic/Resource Hardware Smoke` | `blocked_until_4_32g_r0_passes` | Can lifecycle event/trophic/mask-sync traffic cross the chip boundary with compact resource counters? | Canonical lifecycle events and at least one control return exact counters, compact payload, and zero fallback. | Classify as route, key, ack, readback, source/package, allocation, or lifecycle semantics failure. |
| `Tier 4.32h - True Partition Semantics Contract` | `blocked_until_lifecycle_resource_gate` | What origin/target shard semantics are required before true two-partition cross-chip learning? | Authorizes a true two-partition local reference/repair tier. | Keep claims to single-shard split-role hardware evidence. |

## Required Readback For Next Hardware Work

| Field | Producer | Required For | Rule | Why |
| --- | --- | --- | --- | --- |
| `board_id` | host/placement | all later multi-chip tiers | `non-empty and preserved in returned artifacts` | tie evidence to EBRAINS allocation |
| `chip_x/chip_y/p_core/role` | host/runtime | all role cores | `matches placement table` | reconstruct ownership |
| `partition_id/shard_id` | host/runtime/MCPL key | all lifecycle and lookup messages | `matches selected static reef partition` | prevent cross-talk |
| `lifecycle_event_requests_sent` | source/runtime | 4.32g-r0 and 4.32g | `> 0 for lifecycle smoke` | prove event traffic was emitted |
| `lifecycle_trophic_requests_sent` | source/runtime | 4.32g-r0 and 4.32g | `> 0 when trophic updates are scheduled` | prove trophic traffic was emitted |
| `lifecycle_event_acks_received` | source/runtime | 4.32g-r0 and 4.32g | `== expected lifecycle mutating events` | prove event requests were accepted |
| `lifecycle_mask_syncs_sent` | lifecycle core | 4.32g-r0 and 4.32g | `> 0 after active-mask mutation` | prove mask sync broadcast |
| `lifecycle_mask_syncs_received` | learning/consumer core | 4.32g-r0 and 4.32g | `== expected sync packets` | prove consumer saw mask sync |
| `lifecycle_duplicate_events` | lifecycle core | 4.32g-r0 and 4.32g | `== 0 in canonical case; >0 in duplicate-control if used` | classify duplicate failures |
| `lifecycle_stale_events` | lifecycle core | 4.32g-r0 and 4.32g | `== 0 in canonical case; >0 in stale-control if used` | classify stale failures |
| `lifecycle_missing_acks` | source/runtime | 4.32g-r0 and 4.32g | `== 0` | catch lost lifecycle packets |
| `payload_len` | all compact readbacks | all later hardware tiers | `within compact schema limit` | avoid readback bloat |

## Source Checks

| Check | File | Token | Present | Implication |
| --- | --- | --- | --- | --- |
| `lifecycle_event_msg_type` | `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `MCPL_MSG_LIFECYCLE_EVENT_REQUEST` | yes | Lifecycle event request packet type exists. |
| `lifecycle_trophic_msg_type` | `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE` | yes | Lifecycle trophic update packet type exists. |
| `lifecycle_mask_sync_msg_type` | `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC` | yes | Lifecycle active-mask sync packet type exists. |
| `lifecycle_event_sender` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `cra_lifecycle_send_event_request_stub` | yes | Lifecycle event request sender is declared. |
| `lifecycle_trophic_sender` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `cra_lifecycle_send_trophic_update_stub` | yes | Lifecycle trophic update sender is declared. |
| `lifecycle_event_handler` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `cra_lifecycle_handle_event_request` | yes | Lifecycle event receiver/handler is declared. |
| `lifecycle_trophic_handler` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `cra_lifecycle_handle_trophic_request` | yes | Lifecycle trophic receiver/handler is declared. |
| `lifecycle_mask_receiver` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `cra_lifecycle_receive_active_mask_sync` | yes | Lifecycle mask-sync receiver is declared. |
| `lifecycle_duplicate_counter` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `lifecycle_duplicate_events` | yes | Duplicate lifecycle events are counted. |
| `lifecycle_stale_counter` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `lifecycle_stale_events` | yes | Stale lifecycle events are counted. |
| `lifecycle_missing_ack_counter` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h` | `lifecycle_missing_acks` | yes | Missing lifecycle acks are counted. |
| `lookup_interchip_request_route` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE` | yes | Lookup route repair has explicit source-chip request-link routing. |
| `lookup_interchip_reply_route` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE` | yes | Lookup route repair has explicit state-chip reply-link routing. |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| Tier 4.30g lifecycle native baseline evidence passed | `pass` | == pass | yes |  |
| Tier 4.32b static partition map passed | `pass` | == pass | yes |  |
| Tier 4.32d two-chip lookup smoke passed | `pass` | == pass | yes |  |
| Tier 4.32e two-chip learning micro-task passed | `pass` | == pass | yes |  |
| Tier 4.32e raw remote status passed | `pass` | == pass | yes |  |
| Tier 4.32e preserved returned artifacts | `42` | >= 40 | yes |  |
| Tier 4.32e task result passed | `pass` | == pass | yes |  |
| Tier 4.32e contains enabled and no-learning cases | `["enabled_lr_0_25", "no_learning_lr_0_00"]` | contains enabled_lr_0_25 and no_learning_lr_0_00 | yes |  |
| Tier 4.32e lookup cases clean | `true` | all requests==replies and zero stale/duplicate/timeouts | yes |  |
| enabled learning moved readout | `32768` | == 32768 | yes |  |
| no-learning control stayed zero | `0` | == 0 | yes |  |
| runtime lifecycle source primitives exist | `[]` | empty | yes |  |
| lifecycle inter-chip route gap classified | `false` | False is acceptable only if next hardware is blocked | yes | Current source lacks explicit lifecycle inter-chip route installs; 4.32g-r0 is required. |
| next direction selects lifecycle traffic | `multi_chip_lifecycle_traffic` | == multi_chip_lifecycle_traffic | yes |  |
| next direction blocks immediate lifecycle hardware | `blocked_until_4_32g_r0_passes` | == blocked_until_4_32g_r0_passes | yes |  |
| true two-partition learning remains blocked | `blocked` | == blocked | yes |  |
| speedup and benchmarks remain blocked | `blocked` | == blocked | yes |  |
| native scale baseline freeze not authorized | `not_authorized` | == not_authorized | yes |  |
| 4.32g-r0 authorized next | `authorized_next` | == authorized_next | yes |  |
| lifecycle readback requires duplicate/stale/missing-ack counters | `["board_id", "chip_x/chip_y/p_core/role", "partition_id/shard_id", "lifecycle_event_requests_sent", "lifecycle_trophic_requests_sent", "lifecycle_event_acks_received", "lifecycle_mask_syncs_sent", "lifecycle_mask_syncs_received", "lifecycle_duplicate_events", "lifecycle_stale_events", "lifecycle_missing_acks", "payload_len"]` | contains lifecycle_duplicate_events/lifecycle_stale_events/lifecycle_missing_acks | yes |  |
| compact payload remains required | `["board_id", "chip_x/chip_y/p_core/role", "partition_id/shard_id", "lifecycle_event_requests_sent", "lifecycle_trophic_requests_sent", "lifecycle_event_acks_received", "lifecycle_mask_syncs_sent", "lifecycle_mask_syncs_received", "lifecycle_duplicate_events", "lifecycle_stale_events", "lifecycle_missing_acks", "payload_len"]` | contains payload_len | yes |  |
| lifecycle pool fits current static native pool | `8` | >= 8 | yes |  |
