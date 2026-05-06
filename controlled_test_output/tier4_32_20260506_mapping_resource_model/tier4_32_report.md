# Tier 4.32 Native Runtime Mapping/Resource Model

- Generated: `2026-05-06T21:42:20+00:00`
- Runner revision: `tier4_32_mapping_resource_model_20260506_0001`
- Status: **PASS**
- Criteria: `23/23`
- Recommended next step: Tier 4.32a single-chip multi-core scale stress with MCPL-first messaging and compact readback.

## Claim Boundary

Tier 4.32 is a local mapping/resource model over measured Tier 4.27-4.31 evidence. It is not a new SpiNNaker run, not a speedup claim, not a multi-chip claim, not a benchmark/superiority claim, not a full organism autonomy claim, and not a baseline freeze.

## Final Decision

- `status`: `pass`
- `tier4_32a`: `authorized_next`
- `tier4_32b`: `blocked_until_4_32a_passes`
- `tier4_32c`: `blocked_until_4_32b_passes`
- `tier4_32d`: `blocked_until_4_32c_passes`
- `tier4_32e`: `blocked_until_4_32d_passes`
- `native_scale_baseline_freeze`: `not_authorized`
- `mcpl_policy`: `mcpl_first_for_scale_sdp_fallback_control_only`
- `claim_boundary`: `local resource/mapping model over measured evidence only`

## Evidence Inputs

| Source | Status | Role | Extracted Signal | Path |
| --- | --- | --- | --- | --- |
| `tier4_27g_mcpl_vs_sdp_model` | `pass` | protocol byte/latency model | SDP round trip 54 bytes; MCPL round trip 16 bytes; 48-event MCPL total 2304 bytes | `controlled_test_output/tier4_27g_20260502_local_pass/tier4_27g_results.json` |
| `tier4_28e_pointC_four_core_pressure` | `pass` | measured four-core event/slot/lookup pressure | 43 events; context slots 43; max pending 10; learning lookups 129 | `controlled_test_output/tier4_28e_pointC_20260503_hardware_pass_ingested/tier4_28e_hardware_results.json` |
| `tier4_29f_native_mechanism_regression` | `pass` | canonical mechanism-regression prerequisite | 113/113 criteria complete | `controlled_test_output/tier4_29f_20260505_native_mechanism_regression/tier4_29f_results.json` |
| `tier4_30g_lifecycle_hardware_bridge` | `pass` | measured five-core lifecycle bridge | task status pass; profiles context,learning,lifecycle,memory,route; runtime 1.8654s | `controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/tier4_30g_hw_results.json` |
| `tier4_31d_native_temporal_hardware_smoke` | `pass` | measured temporal compact readback smoke | payload 48 bytes; board 10.11.216.121; scenarios {'enabled': 'pass', 'frozen_state': 'pass', 'reset_each_update': 'pass', 'zero_state': 'pass'} | `controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested/returned_artifacts/tier4_31d_hw_results.json` |
| `tier4_31e_decision_closeout` | `pass` | replay/eligibility closeout prerequisite | 4.32 decision = authorized_next | `controlled_test_output/tier4_31e_20260506_native_replay_eligibility_decision_closeout/tier4_31e_results.json` |

## Profile Budget

| Profile | Text | Data | BSS | ITCM Headroom | DTCM Estimate | DTCM Headroom | Source |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `context_core` | 11432 | 20 | 8429 | 21336 | 8449 | 57087 | `controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/returned_artifacts/tier4_30g_hw_context_build.json` |
| `route_core` | 11464 | 20 | 8429 | 21304 | 8449 | 57087 | `controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/returned_artifacts/tier4_30g_hw_route_build.json` |
| `memory_core` | 11464 | 20 | 8429 | 21304 | 8449 | 57087 | `controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/returned_artifacts/tier4_30g_hw_memory_build.json` |
| `learning_core` | 13280 | 24 | 23573 | 19488 | 23597 | 41939 | `controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/returned_artifacts/tier4_30g_hw_learning_build.json` |
| `lifecycle_core` | 14744 | 20 | 22773 | 18024 | 22793 | 42743 | `controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/returned_artifacts/tier4_30g_hw_lifecycle_build.json` |

## Resource Envelope

| Category | Metric | Value | Unit | Evidence | Interpretation |
| --- | --- | ---: | --- | --- | --- |
| `protocol` | `sdp_round_trip_bytes` | `54` | bytes | `tier4_27g` | Transitional SDP lookup round trip byte cost. |
| `protocol` | `mcpl_round_trip_bytes` | `16` | bytes | `tier4_27g` | Target MCPL lookup round trip byte cost. |
| `protocol` | `mcpl_byte_reduction_ratio_vs_sdp` | `0.296296` | ratio | `tier4_27g` | MCPL is the scale path; SDP is a transitional/fallback control channel. |
| `protocol` | `lookup_messages_per_event` | `6` | messages/event | `tier4_27g` | Three lookup types times request/reply. |
| `protocol` | `sdp_total_bytes_48event` | `8064` | bytes | `tier4_27g` | Modeled SDP pressure for a 48-event reference. |
| `protocol` | `mcpl_total_bytes_48event` | `2304` | bytes | `tier4_27g` | Modeled MCPL pressure for a 48-event reference. |
| `protocol` | `mcpl_router_entries_required` | `4` | router entries | `tier4_27g` | Minimum intra-chip routing entries for context/route/memory request and learning reply paths. |
| `four_core_pressure` | `tier4_28e_event_count` | `43` | events | `tier4_28e_pointC` | Measured four-core pressure event count. |
| `four_core_pressure` | `tier4_28e_schedule_uploads` | `43` | uploads | `tier4_28e_pointC` | One schedule upload per compact event in this run. |
| `four_core_pressure` | `tier4_28e_context_slots_used` | `43` | slots | `tier4_28e_pointC` | Measured context-slot pressure. |
| `four_core_pressure` | `tier4_28e_max_pending` | `10` | pending horizons | `tier4_28e_pointC` | Measured delayed-credit pending pressure. |
| `four_core_pressure` | `tier4_28e_lookup_requests` | `129` | requests | `tier4_28e_pointC` | Learning-core lookup requests. |
| `four_core_pressure` | `tier4_28e_lookup_replies` | `129` | replies | `tier4_28e_pointC` | Learning-core lookup replies. |
| `four_core_pressure` | `tier4_28e_stale_duplicate_timeout_total` | `0` | events | `tier4_28e_pointC` | No stale, duplicate, or timeout events were observed. |
| `readback` | `standard_payload_len` | `105` | bytes | `tier4_28e_pointC` | Standard compact state payload in the four-core run. |
| `readback` | `tier4_28e_learning_readback_bytes` | `5460` | bytes | `tier4_28e_pointC` | Measured cumulative learning readback bytes. |
| `readback` | `tier4_28e_context_readback_bytes` | `105` | bytes | `tier4_28e_pointC` | Measured context readback bytes. |
| `five_core_lifecycle` | `active_profiles` | `5` | profiles | `tier4_30g_hw` | Measured five-profile single-chip task bridge. |
| `five_core_lifecycle` | `enabled_task_schedule_uploads` | `24` | uploads | `tier4_30g_hw` | Lifecycle enabled task schedule length. |
| `five_core_lifecycle` | `enabled_learning_lookup_requests` | `72` | requests | `tier4_30g_hw` | Lifecycle enabled task lookup pressure. |
| `five_core_lifecycle` | `enabled_learning_readback_bytes` | `210` | bytes | `tier4_30g_hw` | Lifecycle enabled task learning readback bytes. |
| `five_core_lifecycle` | `lifecycle_payload_len` | `68` | bytes | `tier4_30g_hw` | Lifecycle compact payload length. |
| `five_core_lifecycle` | `lifecycle_readback_bytes` | `2380` | bytes | `tier4_30g_hw` | Lifecycle cumulative readback bytes per mode. |
| `five_core_lifecycle` | `enabled_task_runtime_seconds` | `0.2652983949519694` | seconds | `tier4_30g_hw` | Measured lifecycle enabled task roundtrip time. |
| `temporal` | `temporal_payload_len` | `48` | bytes | `tier4_31d_hw` | Measured native temporal compact payload length. |
| `limits` | `max_context_slots` | `128` | slots | `config.h` | Compiled context-slot capacity. |
| `limits` | `max_route_slots` | `8` | slots | `config.h` | Compiled route-slot capacity. |
| `limits` | `max_memory_slots` | `8` | slots | `config.h` | Compiled memory-slot capacity. |
| `limits` | `max_pending_horizons` | `128` | pending horizons | `config.h` | Compiled delayed-credit capacity. |
| `limits` | `max_lifecycle_slots` | `8` | slots | `config.h` | Compiled lifecycle static-pool capacity. |
| `limits` | `max_schedule_entries` | `512` | schedule entries | `config.h` | Compiled host-supplied schedule capacity. |
| `limits` | `max_lookup_replies` | `32` | entries | `state_manager.h` | Compiled lookup reply table capacity. |
| `profile_budget` | `max_profile_text_bytes` | `14744` | bytes | `tier4_30g_build_profiles` | Largest measured profile text section. |
| `profile_budget` | `max_profile_dtcm_estimate_bytes` | `23597` | bytes | `tier4_30g_build_profiles` | Largest measured data+bss estimate. |
| `profile_budget` | `min_itcm_headroom_bytes` | `18024` | bytes | `tier4_30g_build_profiles` | Smallest measured ITCM headroom among returned profile builds. |
| `profile_budget` | `min_dtcm_headroom_bytes` | `41939` | bytes | `tier4_30g_build_profiles` | Smallest measured DTCM estimate headroom among returned profile builds. |
| `five_core_final_reads` | `context_readback_bytes` | `210` | bytes | `tier4_30g_hw` | Final compact readback accounting for context. |
| `five_core_final_reads` | `learning_readback_bytes` | `315` | bytes | `tier4_30g_hw` | Final compact readback accounting for learning. |
| `five_core_final_reads` | `lifecycle_readback_bytes` | `2485` | bytes | `tier4_30g_hw` | Final compact readback accounting for lifecycle. |
| `five_core_final_reads` | `memory_readback_bytes` | `210` | bytes | `tier4_30g_hw` | Final compact readback accounting for memory. |
| `five_core_final_reads` | `route_readback_bytes` | `210` | bytes | `tier4_30g_hw` | Final compact readback accounting for route. |

## Failure Classes

| Failure Class | Status | Evidence | Next Detection Gate |
| --- | --- | --- | --- |
| `ITCM overflow` | measured historically, not active in 4.30g profiles | 4.22w had an unprofiled overflow; 4.30g returned five profiled builds with positive ITCM headroom. | Tier 4.32a profile-size sweep and any new runtime-profile build. |
| `DTCM/state-slot exhaustion` | not yet stressed to limit | 4.28e used 43/128 context slots and 10/128 pending horizons; 4.30g used 1 active lifecycle bridge slot, not lifecycle-pool stress. | Tier 4.32a single-chip scale stress with slot/schedule sweeps. |
| `lookup stale/duplicate/timeout` | zero observed in measured gates | 4.28e and 4.30g returned zero stale replies and zero timeouts under current pressure. | Tier 4.32a and 4.32c must preserve stale/duplicate/timeout counters. |
| `SDP overhead bottleneck` | architecturally deprecated | 4.27g model shows MCPL round-trip bytes are 16 vs SDP 54 and avoids monitor involvement. | Tier 4.32a should stay MCPL-first; SDP remains only fallback/control. |
| `readback/provenance blowup` | partially measured | 4.28e standard readback reached 5460 learning bytes; 4.30g lifecycle readback reached 2380 bytes per mode; temporal compact payload is 48 bytes. | Tier 4.32a compact-readback cadence sweep. |
| `multi-chip routing/latency` | unmeasured | All current 4.27-4.31 evidence is single-chip/same-board scoped. | Tier 4.32c contract then Tier 4.32d first multi-chip smoke. |
| `static reef partition correctness` | unmeasured | Current gates split profiles, not reef module/polyps across partitions. | Tier 4.32b static reef partition smoke. |
| `benchmark/large-task performance` | unmeasured by this tier | 4.32 is a resource model, not MackeyGlass/Lorenz/NARMA or external-baseline evidence. | Return to benchmark matrix after native scale gates stabilize. |

## Next Gate Plan

| Gate | Decision | Question | Prerequisites | Pass Boundary | Fail Boundary | Claim Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| `Tier 4.32a` | `authorize next` | How far can the current single-chip multi-core runtime be stressed before schedule, slot, readback, or lookup pressure breaks? | 4.32 model passes; use MCPL-first runtime profiles and compact readback. | Passes predeclared sweeps with no stale replies, no timeouts, no fallback, positive profile headroom, and documented breakpoints. | Any overflow/timeout/stale reply/readback failure becomes the blocker to repair before static partitioning. | Single-chip scale-stress evidence only; no multi-chip, benchmark, or baseline-freeze claim. |
| `Tier 4.32b` | `blocked until 4.32a passes` | Can a static reef partition map modules/polyps to runtime profiles without corrupting state ownership? | 4.32a pass and a declared partition map. | Static partition smoke preserves state/readout parity and ownership guards. | Partition mismatch, owner leakage, or readback ambiguity blocks multi-chip work. | Static mapping smoke only; not dynamic growth or multi-chip scaling. |
| `Tier 4.32c` | `blocked until 4.32b passes` | What is the inter-chip MCPL/multicast contract for state, lifecycle, temporal, and learning messages? | 4.32b pass and exact key masks/payloads/cadence declared. | Contract defines routing keys, masks, failure counters, placement assumptions, and minimal readback. | Ambiguous key ownership or unmeasured route failure class blocks hardware smoke. | Contract evidence only; not hardware execution. |
| `Tier 4.32d` | `blocked until 4.32c passes` | Can the smallest cross-chip message/readback smoke execute with zero stale replies and correct ownership? | 4.32c contract and EBRAINS package prepared. | One cross-chip message path passes with real board readback and no fallback. | Any routing/load/message/readback failure becomes a repair tier. | First multi-chip smoke only; not learning scale. |
| `Tier 4.32e` | `blocked until 4.32d passes` | Can a tiny cross-chip learning micro-task preserve the native learning loop? | 4.32d pass and compact reference trace. | Cross-chip learning micro-task matches fixed-point reference within predeclared tolerance. | Mismatch or instability blocks larger native benchmarks. | Tiny multi-chip learning evidence only. |
| `native scale baseline freeze` | `not authorized` | Is the native runtime stable enough to freeze as a scale baseline? | 4.32a-e pass with stable resource model and documented failure envelope. | Freeze only after single-chip stress, partition smoke, inter-chip contract, cross-chip smoke, and cross-chip micro-learning are all clean. | Any unresolved scale or routing blocker prevents freeze. | Would be a native-runtime baseline, separate from software v2.x mechanism baselines. |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| Tier 4.27g protocol model passed | `pass` | `== pass` | yes |  |
| Tier 4.28e Point C hardware pressure passed | `pass` | `== pass` | yes |  |
| Tier 4.29f mechanism regression passed | `113/113` | `== 113/113` | yes |  |
| Tier 4.30g hardware lifecycle bridge passed | `pass` | `== pass` | yes |  |
| Tier 4.31d temporal hardware smoke passed | `pass` | `== pass` | yes |  |
| Tier 4.31e authorized 4.32 | `authorized_next` | `== authorized_next` | yes |  |
| runtime constants parsed | `{'max_context_slots': 128, 'max_route_slots': 8, 'max_memory_slots': 8, 'max_pending_horizons': 128, 'max_lifecycle_slots': 8, 'max_schedule_entries': 512, 'max_lookup_replies': 32}` | `== {'max_context_slots': 128, 'max_route_slots': 8, 'max_memory_slots': 8, 'max_pending_horizons': 128, 'max_lifecycle_slots': 8, 'max_schedule_entries': 512, 'max_lookup_replies': 32}` | yes |  |
| profile build artifacts parsed | `{'context_core': 'pass', 'route_core': 'pass', 'memory_core': 'pass', 'learning_core': 'pass', 'lifecycle_core': 'pass'}` | `all pass` | yes |  |
| profile ITCM headroom positive | `18024` | `> 0` | yes |  |
| profile DTCM estimate headroom positive | `41939` | `> 0` | yes |  |
| MCPL is byte-cheaper than SDP | `16 < 54` | `true` | yes |  |
| 4.28e event pressure recorded | `43` | `>= 43` | yes |  |
| 4.28e context slot pressure below limit | `43` | `< MAX_CONTEXT_SLOTS` | yes |  |
| 4.28e pending pressure below limit | `10` | `< MAX_PENDING_HORIZONS` | yes |  |
| 4.28e lookup request/reply parity | `129/129` | `equal` | yes |  |
| 4.28e stale/duplicate/timeouts absent | `0` | `== 0` | yes |  |
| 4.30g lifecycle modes all passed | `['pass', 'pass', 'pass', 'pass', 'pass', 'pass']` | `all pass` | yes |  |
| 4.30g lifecycle lookup parity | `72/72` | `equal` | yes |  |
| 4.30g stale/timeouts absent | `0` | `== 0` | yes |  |
| 4.31d temporal payload measured | `48` | `== 48` | yes |  |
| resource envelope rows cover required categories | `['five_core_final_reads', 'five_core_lifecycle', 'four_core_pressure', 'limits', 'profile_budget', 'protocol', 'readback', 'temporal']` | `contains protocol/four_core/readback/five_core/temporal/limits/profile` | yes |  |
| failure classes declared | `8` | `>= 8` | yes |  |
| next gate is 4.32a, not freeze | `Tier 4.32a` | `== Tier 4.32a` | yes |  |
