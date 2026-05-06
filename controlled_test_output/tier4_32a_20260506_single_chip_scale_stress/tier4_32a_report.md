# Tier 4.32a Single-Chip Multi-Core Scale-Stress Preflight

- Generated: `2026-05-06T22:17:01+00:00`
- Runner revision: `tier4_32a_single_chip_scale_stress_20260506_0001`
- Status: **PASS**
- Criteria: `18/18`
- Recommended next step: Prepare and run Tier 4.32a-hw EBRAINS single-chip MCPL-first scale stress.

## Claim Boundary

Tier 4.32a is a local scale-stress preflight over the Tier 4.32 resource model. It is not a SpiNNaker hardware run, not a speedup claim, not a multi-chip claim, not a static reef partition proof, not benchmark/superiority evidence, and not a native-scale baseline freeze.

## Final Decision

- `status`: `pass`
- `tier4_32a_hw`: `authorized_next`
- `tier4_32b`: `blocked_until_4_32a_hw_passes`
- `tier4_32c`: `blocked_until_4_32b_passes`
- `tier4_32d`: `blocked_until_4_32c_passes`
- `tier4_32e`: `blocked_until_4_32d_passes`
- `native_scale_baseline_freeze`: `not_authorized`
- `claim_boundary`: `local single-chip scale-stress preflight only`

## Scale Points

| Point | Status | Cores | Shards | Events | Schedule/Core | Context Slots/Core | Pending | MCPL Bytes | SDP Bytes If Fallback | Readback/Snapshot | Failure Class |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `point_04c_reference` | `eligible_for_hardware_stress` | 4 | 1 | 48 | 48 | 48 | 10 | 2304 | 7776 | 420 | `none_projected_preflight` |
| `point_05c_lifecycle` | `eligible_for_hardware_stress` | 5 | 1 | 96 | 96 | 96 | 10 | 4608 | 15552 | 593 | `none_projected_preflight` |
| `point_08c_dual_shard` | `eligible_for_hardware_stress` | 8 | 2 | 192 | 96 | 96 | 20 | 9216 | 31104 | 888 | `none_projected_preflight` |
| `point_12c_triple_shard` | `eligible_for_hardware_stress` | 12 | 3 | 384 | 128 | 128 | 30 | 18432 | 62208 | 1308 | `none_projected_preflight` |
| `point_16c_quad_shard` | `eligible_for_hardware_stress` | 16 | 4 | 512 | 128 | 128 | 32 | 24576 | 82944 | 1728 | `none_projected_preflight` |

## Profile Allocation

| Point | Profile | Copies | Text/Core | DTCM/Core | ITCM Headroom/Core | DTCM Headroom/Core | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `point_04c_reference` | `context_core` | 1 | 11432 | 8449 | 21336 | 57087 | `profile_headroom_positive` |
| `point_04c_reference` | `route_core` | 1 | 11464 | 8449 | 21304 | 57087 | `profile_headroom_positive` |
| `point_04c_reference` | `memory_core` | 1 | 11464 | 8449 | 21304 | 57087 | `profile_headroom_positive` |
| `point_04c_reference` | `learning_core` | 1 | 13280 | 23597 | 19488 | 41939 | `profile_headroom_positive` |
| `point_05c_lifecycle` | `context_core` | 1 | 11432 | 8449 | 21336 | 57087 | `profile_headroom_positive` |
| `point_05c_lifecycle` | `route_core` | 1 | 11464 | 8449 | 21304 | 57087 | `profile_headroom_positive` |
| `point_05c_lifecycle` | `memory_core` | 1 | 11464 | 8449 | 21304 | 57087 | `profile_headroom_positive` |
| `point_05c_lifecycle` | `learning_core` | 1 | 13280 | 23597 | 19488 | 41939 | `profile_headroom_positive` |
| `point_05c_lifecycle` | `lifecycle_core` | 1 | 14744 | 22793 | 18024 | 42743 | `profile_headroom_positive` |
| `point_08c_dual_shard` | `context_core` | 2 | 11432 | 8449 | 21336 | 57087 | `profile_headroom_positive` |
| `point_08c_dual_shard` | `route_core` | 2 | 11464 | 8449 | 21304 | 57087 | `profile_headroom_positive` |
| `point_08c_dual_shard` | `memory_core` | 2 | 11464 | 8449 | 21304 | 57087 | `profile_headroom_positive` |
| `point_08c_dual_shard` | `learning_core` | 2 | 13280 | 23597 | 19488 | 41939 | `profile_headroom_positive` |
| `point_12c_triple_shard` | `context_core` | 3 | 11432 | 8449 | 21336 | 57087 | `profile_headroom_positive` |
| `point_12c_triple_shard` | `route_core` | 3 | 11464 | 8449 | 21304 | 57087 | `profile_headroom_positive` |
| `point_12c_triple_shard` | `memory_core` | 3 | 11464 | 8449 | 21304 | 57087 | `profile_headroom_positive` |
| `point_12c_triple_shard` | `learning_core` | 3 | 13280 | 23597 | 19488 | 41939 | `profile_headroom_positive` |
| `point_16c_quad_shard` | `context_core` | 4 | 11432 | 8449 | 21336 | 57087 | `profile_headroom_positive` |
| `point_16c_quad_shard` | `route_core` | 4 | 11464 | 8449 | 21304 | 57087 | `profile_headroom_positive` |
| `point_16c_quad_shard` | `memory_core` | 4 | 11464 | 8449 | 21304 | 57087 | `profile_headroom_positive` |
| `point_16c_quad_shard` | `learning_core` | 4 | 13280 | 23597 | 19488 | 41939 | `profile_headroom_positive` |

## Failure Classes

| Failure Class | Preflight Status | Detection Rule | Hardware Measurement Required | Next Gate |
| --- | --- | --- | --- | --- |
| `schedule_length_overflow` | `bounded_by_preflight` | schedule_entries_per_learning_core <= MAX_SCHEDULE_ENTRIES | hardware run must return accepted schedule count and reject overflow cleanly | `Tier 4.32a-hw` |
| `context_slot_exhaustion` | `bounded_by_preflight` | context_slots_per_context_core <= MAX_CONTEXT_SLOTS | hardware run must report context slot high-water mark | `Tier 4.32a-hw` |
| `route_memory_slot_exhaustion` | `bounded_by_preflight` | route/memory slots per core <= source limits | hardware run must report route/memory slot high-water marks | `Tier 4.32a-hw` |
| `pending_horizon_or_lookup_reply_overflow` | `bounded_by_preflight` | max pending and in-flight replies <= min(MAX_PENDING_HORIZONS, MAX_LOOKUP_REPLIES) | hardware run must report pending high-water mark, lookup replies, and overflow counters | `Tier 4.32a-hw` |
| `mcpl_delivery_integrity_failure` | `not_measured_by_preflight` | preflight can only declare MCPL-first message counts | hardware run must return request/reply parity, stale, duplicate, timeout, and drop counters | `Tier 4.32a-hw` |
| `compact_readback_growth` | `projected_by_preflight` | compact_readback_bytes_per_snapshot is projected for each point | hardware run must return per-core payload lengths and cumulative readback bytes | `Tier 4.32a-hw` |
| `profile_itcm_dtcm_exhaustion` | `bounded_by_returned_profile_sizes` | all replicated profile copies use profiles with positive per-core headroom | any new profile build must return size/headroom before promotion | `Tier 4.32a-hw` |
| `multi_chip_routing_failure` | `out_of_scope` | single-chip only | must be handled by a separate inter-chip contract before first multi-chip smoke | `Tier 4.32c` |

## Next Gate Plan

| Gate | Decision | Question | Prerequisites | Pass Boundary | Fail Boundary | Claim Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| `Tier 4.32a-hw` | `authorize if this preflight passes` | Do the predeclared 4/5/8/12/16-core single-chip stress points execute with MCPL-first integrity and compact readback? | Use the 4.32a preflight scale-point table; no SDP core-to-core fallback unless documented as a control. | zero stale/duplicate/timeout/drop counters, lookup request/reply parity, compact readback returned, profile builds returned, and no schedule/slot overflow. | localize to schedule, slot, MCPL delivery, readback, profile, or EBRAINS environment class before adding more mechanics. | single-chip hardware stress only; not multi-chip, not speedup, not baseline freeze. |
| `Tier 4.32b` | `blocked until 4.32a-hw passes` | Can static reef partitioning map groups/modules/polyps to the measured single-chip runtime envelope? | 4.32a-hw pass with measured resource envelope. | static partition smoke preserves ownership, compact readback, and measured failure counters. | publish measured single-chip runtime boundary; do not proceed to multi-chip. | static partition smoke only; not one-polyp-per-chip and not organism-scale proof. |
| `CRA_NATIVE_SCALE_BASELINE_v0.5` | `not authorized` | Is native scaling stable enough to freeze as a paper baseline? | 4.32a-hw, 4.32b, first inter-chip feasibility, and first multi-chip smoke must pass. | freeze only after single-chip and first multi-chip evidence are clean. | keep v0.4 as latest native baseline and publish limits honestly. | not considered by this preflight. |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| Tier 4.32 prerequisite passed | `pass` | `== pass` | yes |  |
| Tier 4.32 authorized 4.32a | `authorized_next` | `== authorized_next` | yes |  |
| no native scale baseline freeze inherited | `not_authorized` | `== not_authorized` | yes |  |
| MCPL-first policy inherited | `mcpl_first_for_scale_sdp_fallback_control_only` | `contains mcpl_first` | yes |  |
| five ordered scale points declared | `['point_04c_reference', 'point_05c_lifecycle', 'point_08c_dual_shard', 'point_12c_triple_shard', 'point_16c_quad_shard']` | `== 4/5/8/12/16 core points` | yes |  |
| scale points remain within conservative single-chip app-core budget | `16` | `<= 16` | yes |  |
| scale points are eligible for hardware stress | `['eligible_for_hardware_stress', 'eligible_for_hardware_stress', 'eligible_for_hardware_stress', 'eligible_for_hardware_stress', 'eligible_for_hardware_stress']` | `all eligible` | yes |  |
| schedule pressure within current source limit | `128` | `<= 512` | yes |  |
| context slot pressure within current source limit | `128` | `<= 128` | yes |  |
| route slot pressure within current source limit | `4` | `<= 8` | yes |  |
| memory slot pressure within current source limit | `4` | `<= 8` | yes |  |
| lifecycle slot pressure within current source limit | `8` | `<= 8` | yes |  |
| pending/reply pressure within lookup reply window | `32` | `<= 32` | yes |  |
| MCPL projected bytes cheaper than SDP fallback for every point | `[0.296296, 0.296296, 0.296296, 0.296296, 0.296296]` | `< 1.0 each` | yes |  |
| profile allocation headroom positive | `21` | `all profile allocations positive` | yes |  |
| failure classes cover hardware-only measurements | `['schedule_length_overflow', 'context_slot_exhaustion', 'route_memory_slot_exhaustion', 'pending_horizon_or_lookup_reply_overflow', 'mcpl_delivery_integrity_failure', 'compact_readback_growth', 'profile_itcm_dtcm_exhaustion', 'multi_chip_routing_failure']` | `>= 8 classes` | yes |  |
| next gate is hardware stress, not 4.32b jump | `Tier 4.32a-hw` | `== Tier 4.32a-hw` | yes |  |
| baseline freeze remains blocked | `not authorized` | `== not authorized` | yes |  |
