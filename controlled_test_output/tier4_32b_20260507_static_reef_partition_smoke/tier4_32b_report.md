# Tier 4.32b Static Reef Partition Smoke/Resource Mapping

- Generated: `2026-05-07T01:44:19+00:00`
- Runner revision: `tier4_32b_static_reef_partition_smoke_20260507_0001`
- Status: **PASS**
- Criteria: `25/25`
- Recommended next step: Tier 4.32c inter-chip feasibility contract: define board/chip/shard key fields, readback ownership, and first cross-chip smoke target.

## Claim Boundary

Tier 4.32b is local static reef partition/resource evidence over the measured single-chip replicated-shard envelope. It is not a new SpiNNaker hardware run, not speedup evidence, not one-polyp-one-chip evidence, not multi-chip evidence, not benchmark superiority, and not a native-scale baseline freeze.

## Final Decision

- `status`: `pass`
- `canonical_static_layout`: `quad_mechanism_partition_v0`
- `tier4_32c`: `authorized_next_contract`
- `tier4_32d`: `blocked_until_4_32c_passes`
- `tier4_32e`: `blocked_until_4_32d_passes`
- `multi_chip_scaling`: `blocked_until_4_32c_contract_and_4_32d_smoke`
- `speedup_claims`: `not_authorized`
- `native_scale_baseline_freeze`: `not_authorized`
- `claim_boundary`: `local static reef partition mapping only`

## Canonical Static Partition Map

| Partition | Shard | Polyp Slots | Context | Route | Memory | Learning | Events | Lookups | Status |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `reef_partition_0` | 0 | `0,1` | 1 | 2 | 3 | 4 | 128 | 384 | `single_writer_per_module_family` |
| `reef_partition_1` | 1 | `2,3` | 5 | 6 | 7 | 8 | 128 | 384 | `single_writer_per_module_family` |
| `reef_partition_2` | 2 | `4,5` | 9 | 10 | 11 | 12 | 128 | 384 | `single_writer_per_module_family` |
| `reef_partition_3` | 3 | `6,7` | 13 | 14 | 15 | 16 | 128 | 384 | `single_writer_per_module_family` |

## Candidate Layouts

| Layout | Cores | Partitions | Lifecycle Cores | Slots | Status | Decision | Blocker |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| `quad_mechanism_partition_v0` | 16 | 4 | 0 | 8 | `eligible_static_mapping_reference` | canonical_4_32b_static_map | dedicated lifecycle core is not included in this exact 16-core envelope |
| `triple_partition_plus_lifecycle_v0` | 13 | 3 | 1 | 8 | `eligible_for_future_local_contract` | reserve_as_lifecycle_including_single_chip_layout | combined 12-core plus lifecycle layout has not been hardware-smoked as a single package |
| `quad_partition_plus_dedicated_lifecycle_v0` | 17 | 4 | 1 | 8 | `blocked_on_single_chip_budget` | requires multi-chip or distributed lifecycle ownership | 17 cores exceeds conservative single-chip app-core budget |
| `one_polyp_one_chip` | 8 | 8 | 0 | 8 | `rejected_claim` | do_not_use_as_claim | conceptual mapping is unsupported by current runtime/evidence |

## Replicated Hardware Envelope

| Point | Status | Shards | Cores | Events | Events/Shard | Lookups/Shard | Stale/Dup/Timeout |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `point_08c_dual_shard` | `pass` | 2 | 8 | 192 | 96 | 288 | 0/0/0 |
| `point_12c_triple_shard` | `pass` | 3 | 12 | 384 | 128 | 384 | 0/0/0 |
| `point_16c_quad_shard` | `pass` | 4 | 16 | 512 | 128 | 384 | 0/0/0 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.32 prerequisite passed | `pass` | == pass | yes |
| Tier 4.32a preflight passed | `pass` | == pass | yes |
| Tier 4.32a-r1 MCPL repair passed | `pass` | == pass | yes |
| Tier 4.32a-hw-replicated ingest passed | `pass` | == pass | yes |
| raw replicated hardware pass | `pass` | == pass | yes |
| raw final decision authorized 4.32b | `authorized_next` | == authorized_next | yes |
| replicated stress points all passed | `{"point_08c_dual_shard": "pass", "point_12c_triple_shard": "pass", "point_16c_quad_shard": "pass"}` | point08/12/16 all pass | yes |
| canonical point16 criteria all passed | `71/71` | all pass | yes |
| canonical point has four reef partitions | `4` | == 4 | yes |
| canonical point uses conservative 16 app-core envelope | `16` | <= 16 | yes |
| partition core ownership unique | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]` | 16 unique cores | yes |
| partition polyp slots cover static pool exactly | `[0, 1, 2, 3, 4, 5, 6, 7]` | == 0..7 | yes |
| polyp slots fit lifecycle source limit | `8` | <= MAX_LIFECYCLE_SLOTS | yes |
| shard ids fit MCPL key mask | `3` | <= 15 | yes |
| source tokens support shard-aware partitioning | `[{"file": "coral_reef_spinnaker/spinnaker_runtime/src/config.h", "present": true, "purpose": "MCPL keys reserve shard identity bits.", "token": "MCPL_KEY_SHARD_SHIFT"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/config.h", "present": true, "purpose": "Shard id mask is source-declared.", "token": "MCPL_KEY_SHARD_MASK"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/config.h", "present": true, "purpose": "Static partitions can map to explicit shard ids.", "token": "MAKE_MCPL_KEY_SHARD"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/config.h", "present": true, "purpose": "Receivers can decode partition/shard identity.", "token": "EXTRACT_MCPL_SHARD_ID"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/config.h", "present": true, "purpose": "Static polyp/lifecycle pool limit is source-declared.", "token": "MAX_LIFECYCLE_SLOTS"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h", "present": true, "purpose": "Lookup table tracks shard-specific pending entries.", "token": "cra_state_lookup_send_shard"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h", "present": true, "purpose": "Shard-specific lookup readback is testable.", "token": "cra_state_lookup_get_result_shard"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c", "present": true, "purpose": "Lookup entries store shard identity.", "token": "g_lookup_entries[i].shard_id"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c", "present": true, "purpose": "Runtime images can be compiled per static shard.", "token": "CRA_MCPL_SHARD_ID"}]` | all present | yes |
| lookup parity holds for every partition | `{"reef_partition_0": "384/384", "reef_partition_1": "384/384", "reef_partition_2": "384/384", "reef_partition_3": "384/384"}` | requests == replies == expected | yes |
| no stale/duplicate/timeouts in replicated envelope | `[["point_08c_dual_shard", 0, 0, 0], ["point_12c_triple_shard", 0, 0, 0], ["point_16c_quad_shard", 0, 0, 0]]` | all zero | yes |
| event schedule per partition within source limit | `128` | <= MAX_SCHEDULE_ENTRIES | yes |
| lookup count per partition matches three lookup types per event | `{"reef_partition_0": 384, "reef_partition_1": 384, "reef_partition_2": 384, "reef_partition_3": 384}` | event_count * 3 | yes |
| dedicated lifecycle plus quad partition correctly blocked | `17` | > 16 | yes |
| one-polyp-one-chip claim rejected | `rejected_claim` | == rejected_claim | yes |
| ownership invariants cover lifecycle boundary | `["single_context_owner", "single_route_owner", "single_memory_owner", "single_learning_owner", "static_polyp_slot_owner", "lifecycle_boundary_explicit"]` | contains lifecycle_boundary_explicit | yes |
| failure classes include multi-chip ambiguity | `["static_partition_overlap", "shard_key_exhaustion", "lookup_parity_regression", "lifecycle_core_budget_overflow", "one_polyp_one_chip_overclaim", "static_readback_ambiguity", "multi_chip_route_ambiguity"]` | contains multi_chip_route_ambiguity | yes |
| next gate is 4.32c contract, not hardware jump | `Tier 4.32c` | == Tier 4.32c | yes |
| native scale baseline freeze remains blocked | `not_authorized` | == not_authorized | yes |
