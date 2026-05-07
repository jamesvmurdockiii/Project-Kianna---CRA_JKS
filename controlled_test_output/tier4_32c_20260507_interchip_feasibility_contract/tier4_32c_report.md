# Tier 4.32c Inter-Chip Feasibility Contract

- Generated: `2026-05-07T02:27:43+00:00`
- Runner revision: `tier4_32c_interchip_feasibility_contract_20260507_0001`
- Status: **PASS**
- Criteria: `19/19`
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_32c_20260507_interchip_feasibility_contract`

## Claim Boundary

Tier 4.32c is a local inter-chip feasibility contract over the measured single-chip static partition map. It is not a SpiNNaker hardware run, not multi-chip execution evidence, not speedup evidence, not learning-scale evidence, not benchmark superiority, and not a native-scale baseline freeze.

## Contract Summary

- First smoke target: `point_2chip_2partition_lookup_smoke`
- Chips: `2`
- Static partitions: `2`
- Total cores: `8`
- Events per partition: `32`
- Expected lookups per partition: `96`
- Remote paths: `2`
- Recommended next step: Tier 4.32d first two-chip/two-partition MCPL lookup smoke package, only after source/package QA.

## Identity Contract

| Field | Location | Type/Bits | Owner | Required | Failure If Missing |
| --- | --- | --- | --- | --- | --- |
| `logical_board_id` | host manifest and returned compact readback | string/integer metadata; not packed into MCPL key | host placement manifest | yes | returned artifacts cannot prove which board executed each partition |
| `chip_x` | host placement manifest and per-core readback | integer chip coordinate metadata; not packed into MCPL key | host placement manifest plus SpiNNaker placement/readback | yes | same-core-id replies from different chips become ambiguous |
| `chip_y` | host placement manifest and per-core readback | integer chip coordinate metadata; not packed into MCPL key | host placement manifest plus SpiNNaker placement/readback | yes | same-core-id replies from different chips become ambiguous |
| `p_core` | per-core profile/readback | integer processor id metadata | runtime profile and host loader | yes | role ownership cannot be reconstructed |
| `role` | profile name and compact readback | context|route|memory|learning | runtime profile | yes | readback payload cannot be interpreted safely |
| `partition_id` | host manifest, compact readback, and evidence tables | reef_partition_N | Tier 4.32b static map | yes | cross-chip message cannot be traced to a semantic reef partition |
| `shard_id` | MCPL key bits plus readback | 0..MCPL_KEY_SHARD_MASK | runtime key contract | yes | identical seq/type messages can cross-talk across partitions |
| `seq_id` | MCPL key bits and pending lookup table | bounded sequence field | learning/lookup sender | yes | stale/duplicate replies cannot be classified |

## First Cross-Chip Smoke Placement

| Target | Board | Chip | Partition | Shard | Slots | Cores C/R/M/L | Events | Lookups | Rule |
| --- | --- | --- | --- | ---: | --- | --- | ---: | ---: | --- |
| `point_2chip_2partition_lookup_smoke` | `allocated_board_0` | `(0,0)` | `reef_partition_0` | 0 | `0,1` | `1/2/3/4` | 32 | 96 | source partition; local self-lookups plus remote lookup probes to reef_partition_1 |
| `point_2chip_2partition_lookup_smoke` | `allocated_board_0` | `(1,0)` | `reef_partition_1` | 1 | `2,3` | `1/2/3/4` | 32 | 96 | remote partition; must produce distinguishable chip/partition readback |

## Message Paths

| Path | Source | Destination | Transport | Key Fields | Expected | Failure If |
| --- | --- | --- | --- | --- | ---: | --- |
| `local_partition0_self_lookup` | `reef_partition_0` `(0,0)` learning_core | `reef_partition_0` `(0,0)` context/route/memory cores | MCPL/multicast lookup request plus value/meta reply | `app_id,msg_type,lookup_type,shard_id=0,seq_id` | 96 | local parity regresses before cross-chip comparison |
| `remote_partition0_to_partition1_lookup_probe` | `reef_partition_0` `(0,0)` learning_core | `reef_partition_1` `(1,0)` context/route/memory cores | MCPL/multicast lookup request routed across chip boundary plus value/meta reply | `app_id,msg_type,lookup_type,shard_id=1,seq_id` | 96 | remote parity fails, replies are stale/duplicate, or readback cannot prove destination chip |
| `remote_partition1_to_partition0_lookup_probe` | `reef_partition_1` `(1,0)` learning_core | `reef_partition_0` `(0,0)` context/route/memory cores | MCPL/multicast lookup request routed across chip boundary plus value/meta reply | `app_id,msg_type,lookup_type,shard_id=0,seq_id` | 96 | bidirectional route asymmetry or stale replies |

## Required Readback

| Field | Producer | Scope | Rule | Why |
| --- | --- | --- | --- | --- |
| `runner_revision` | host | artifact | `== tier4_32c_interchip_feasibility_contract_20260507_0001 or later 4.32d runner` | bind evidence to runner contract |
| `board_id` | host/placement | per run and per partition | `non-empty` | disambiguate allocation |
| `chip_x` | host/placement/runtime readback | per core | `matches placement table` | prove cross-chip source/destination identity |
| `chip_y` | host/placement/runtime readback | per core | `matches placement table` | prove cross-chip source/destination identity |
| `p_core` | runtime readback | per core | `matches role map` | reconstruct ownership |
| `role` | runtime readback | per core | `context/route/memory/learning` | decode payload safely |
| `partition_id` | host/runtime readback | per core and aggregate | `reef_partition_0/1 for 4.32d` | bind state to reef partition |
| `shard_id` | runtime readback | per lookup and aggregate | `0 or 1 for 4.32d` | prove shard-aware routing |
| `lookup_requests` | learning/runtime | per path | `== expected_messages` | prove request schedule consumed |
| `reply_value_packets` | runtime | per path | `== expected_messages` | prove value packet returned |
| `reply_meta_packets` | runtime | per path | `== expected_messages` | prove confidence/hit/status packet returned |
| `stale_replies` | runtime | per path and aggregate | `== 0` | classify stale lookup failures |
| `duplicate_replies` | runtime | per path and aggregate | `== 0` | classify duplicate lookup failures |
| `timeouts` | runtime | per path and aggregate | `== 0` | classify delivery failure |
| `route_mismatch_count` | runtime or host ingest | per path | `== 0` | catch wrong-chip or wrong-partition replies |
| `payload_len` | runtime readback | per core | `<= compact readback contract` | prevent readback bloat |

## Failure Classes

| Failure | Detection | Required Response | Blocks |
| --- | --- | --- | --- |
| `target_or_machine_allocation` | pyNN.spiNNaker target or board/chip placement unavailable | preserve prepared artifacts; do not mark hardware fail | 4.32d hardware evidence |
| `placement_ambiguity` | returned artifacts lack board/chip/core/role/partition fields | repair placement/readback before rerun | all multi-chip claims |
| `router_table_or_multicast_path` | local parity passes but remote path parity fails | inspect routing table construction and key masks | 4.32d and 4.32e |
| `cross_chip_key_collision` | wrong shard, wrong partition, stale reply, or duplicate reply appears | repair key/seq/shard contract before rerun | learning scale |
| `metadata_value_split` | value packets return without matching metadata packets | repair value/meta pair handling | confidence-gated learning |
| `readback_bloat` | payload length expands beyond compact readback contract | reduce readback before larger runs | speed/resource claims |
| `environment_or_runner` | command/path/import failure before target execution | repair package/runbook; preserve failure as noncanonical | hardware evidence |
| `overclaim_boundary` | report claims speedup, benchmark superiority, or baseline freeze | correct docs and rerun audit before commit | paper readiness |

## Next Gates

| Gate | Decision | Question | Claim Boundary |
| --- | --- | --- | --- |
| `Tier 4.32d` | `authorize_after_4_32c_pass` | Can the smallest two-chip, two-partition MCPL lookup smoke execute with reconstructable readback? | first cross-chip communication/readback smoke only; not learning scale or speedup |
| `Tier 4.32e` | `blocked_until_4_32d_passes` | Can a tiny cross-chip native learning micro-task preserve parity after communication is proven? | tiny multi-chip learning evidence only |
| `CRA_NATIVE_SCALE_BASELINE_v0.5` | `not_authorized` | Is the native runtime stable enough to freeze as the scale baseline? | baseline freeze decision is separate from this contract |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.32b prerequisite passed | `pass` | == pass | yes |
| 4.32b canonical layout is quad mechanism map | `quad_mechanism_partition_v0` | == quad_mechanism_partition_v0 | yes |
| 4.32b authorized 4.32c | `authorized_next_contract` | == authorized_next_contract | yes |
| source supports shard-aware MCPL lookup | `[]` | empty | yes |
| first smoke uses two chips | `2` | == 2 | yes |
| first smoke uses two static partitions | `2` | == 2 | yes |
| first smoke stays within one-chip-per-partition core envelope | `8` | <= 2 * 16 | yes |
| first smoke shard ids fit MCPL mask | `1` | <= 15 | yes |
| events per partition fit schedule limit | `32` | <= 512 | yes |
| identity fields include board/chip/core/role/partition/shard/seq | `["logical_board_id", "chip_x", "chip_y", "p_core", "role", "partition_id", "shard_id", "seq_id"]` | contains required fields | yes |
| readback fields include delivery counters | `["runner_revision", "board_id", "chip_x", "chip_y", "p_core", "role", "partition_id", "shard_id", "lookup_requests", "reply_value_packets", "reply_meta_packets", "stale_replies", "duplicate_replies", "timeouts", "route_mismatch_count", "payload_len"]` | contains stale/duplicate/timeouts/route_mismatch | yes |
| contract includes bidirectional remote paths | `2` | >= 2 | yes |
| remote paths use different source and destination chips | `["remote_partition0_to_partition1_lookup_probe", "remote_partition1_to_partition0_lookup_probe"]` | source_chip != destination_chip | yes |
| message paths preserve value/meta distinction | `["local_partition0_self_lookup", "remote_partition0_to_partition1_lookup_probe", "remote_partition1_to_partition0_lookup_probe"]` | all paths | yes |
| failure classes include placement ambiguity | `["target_or_machine_allocation", "placement_ambiguity", "router_table_or_multicast_path", "cross_chip_key_collision", "metadata_value_split", "readback_bloat", "environment_or_runner", "overclaim_boundary"]` | contains placement_ambiguity | yes |
| failure classes include cross-chip key collision | `["target_or_machine_allocation", "placement_ambiguity", "router_table_or_multicast_path", "cross_chip_key_collision", "metadata_value_split", "readback_bloat", "environment_or_runner", "overclaim_boundary"]` | contains cross_chip_key_collision | yes |
| next gate is 4.32d hardware smoke | `Tier 4.32d` | == Tier 4.32d | yes |
| 4.32e remains blocked | `blocked_until_4_32d_passes` | == blocked_until_4_32d_passes | yes |
| native scale baseline freeze remains blocked | `not_authorized` | == not_authorized | yes |
