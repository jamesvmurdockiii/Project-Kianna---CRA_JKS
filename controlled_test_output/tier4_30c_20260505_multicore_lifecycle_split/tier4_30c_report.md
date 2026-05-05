# Tier 4.30c Multi-Core Lifecycle State Split

- Generated: `2026-05-05T21:23:33+00:00`
- Runner revision: `tier4_30c_multicore_lifecycle_split_20260505_0001`
- Status: **PASS**
- Criteria: `22/22`

## Claim Boundary

Tier 4.30c is a local multi-core lifecycle split contract/reference. It proves ownership, message semantics, failure classes, and deterministic split-reference parity against Tier 4.30a plus the ingested 4.30b-hw smoke. It is not C implementation, not hardware evidence, not task-benefit evidence, not multi-chip scaling, not speedup, not v2.2 temporal migration, and not a lifecycle baseline freeze.

## Core Ownership Contract

| Role | Proposed core | Owns | Accepts | Emits | Forbidden |
| --- | --- | --- | --- | --- | --- |
| `context_core` | `4` | context slots and context confidence | active-mask snapshot for optional future context gating | context lookup replies | must not mutate lifecycle slots, lineage, trophic state, or active masks |
| `route_core` | `5` | route slots and route confidence | active-mask snapshot for optional future route gating | route lookup replies | must not mutate lifecycle slots, lineage, trophic state, or active masks |
| `memory_core` | `6` | memory slots, replay/consolidation keys, memory confidence | active-mask snapshot for optional future memory-slot gating | memory lookup replies | must not mutate lifecycle slots, lineage, trophic state, or active masks |
| `learning_core` | `7` | pending horizons, readout weight/bias, confidence-gated reward updates | lifecycle event ack, active-mask snapshot, compact lifecycle summary | trophic update request, lifecycle event request, lifecycle read request | must not directly write lifecycle slot state or fabricate lineage |
| `lifecycle_core` | `8` | fixed slot pool, active masks, lineage IDs, trophic health, event counters, sham mode | init, trophic/event requests, sham mode, readback request | event ack, active-mask sync, compact summary, optional full-slot rows | must not run task readout learning or rewrite context/route/memory tables |

## Message Contract

| Message | Transport | Source | Destination | Payload | Ack/Readback | Failure If |
| --- | --- | --- | --- | --- | --- | --- |
| `LIFE_INIT_CONTROL` | host SDP control | `host` | `lifecycle_core` | pool_size, founder_count, seed, trophic_seed_raw, generation_seed | compact lifecycle summary with payload_len=68 | wrong pool size, nonzero invalid events, missing compact summary |
| `LIFE_EVENT_REQUEST` | inter-core event packet; MCPL/multicast target, SDP permitted only in local transitional tests | `learning_core` | `lifecycle_core` | event_index, event_type, target_slot, parent_slot, child_slot, trophic_delta_raw, reward_raw | event_count, active_mask_bits, lineage_checksum, trophic_checksum | duplicate event, stale event, invalid event hidden, or checksum mismatch |
| `LIFE_TROPHIC_UPDATE` | inter-core event packet; MCPL/multicast target | `learning_core` | `lifecycle_core` | slot_id, trophic_delta_raw, reward_raw, confidence_raw, source_timestep | slot status and compact trophic checksum | inactive slot silently accepted or lineage changes on trophic-only event |
| `LIFE_ACTIVE_MASK_SYNC` | inter-core broadcast; MCPL/multicast target | `lifecycle_core` | `context_core, route_core, memory_core, learning_core` | event_count, active_mask_bits, active_count, lineage_checksum | receiving cores expose last_seen_lifecycle_event_count in later source audits | consumer sees stale active mask after cleavage, birth, or death |
| `LIFE_SUMMARY_READBACK` | host SDP readback | `host` | `lifecycle_core` | read_scope, start_slot, slot_count, schema_version | compact summary, optional full-slot rows in later tiers | unversioned readback, cumulative byte counter used as payload-size proof |

## Scenario Results

| Scenario | Events | Acks | Mask Syncs | Final Mask | Lineage | Trophic | Match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `canonical_32` | `32` | `32` | `13` | `63` | `105428` | `466851` | `True` |
| `boundary_64` | `64` | `64` | `22` | `127` | `18496` | `761336` | `True` |

## Failure Classes

| Failure | Detection | Meaning | Required Response |
| --- | --- | --- | --- |
| `duplicate_event` | same event_index accepted twice | event replay/transport defect | fail gate; add dedup counter before hardware |
| `stale_event` | event_index lower than lifecycle event counter | out-of-order lifecycle mutation risk | fail gate; add stale counter/readback |
| `missing_ack` | learning_core request has no lifecycle ack | inter-core timeout or routing failure | fail gate; no inferred success |
| `mask_desync` | consumer active mask differs from lifecycle_core | distributed state corruption | fail gate; require active-mask sync readback |
| `checksum_mismatch` | lineage/trophic checksum differs from reference | lifecycle state corruption | fail gate; inspect event trace |
| `invalid_event_hidden` | invalid event not counted | invariant audit broken | fail gate; invalid_event_count must be explicit |
| `wrong_owner_write` | non-lifecycle core writes slot fields | architecture boundary violation | fail gate; reject implementation |
| `payload_schema_drift` | payload_len/schema version mismatch | host/runtime parser drift | fail gate; update protocol/tests before EBRAINS |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| Tier 4.30a reference passed | `"pass"` | == pass | yes |  |
| Tier 4.30b source audit passed | `"pass"` | == pass | yes |  |
| Tier 4.30b-hw corrected ingest passed | `"pass"` | == pass | yes |  |
| Tier 4.30b-hw raw remote failure preserved | `"fail"` | == fail with correction | yes |  |
| five-core role map declared | `["context_core", "route_core", "memory_core", "learning_core", "lifecycle_core"]` | includes lifecycle core plus 4.29 bridge cores | yes |  |
| lifecycle fields single-owned | `{"active masks": 1, "event counters": 1, "fixed slot pool": 1, "lineage IDs": 1, "sham mode": 1, "trophic health": 1}` | all lifecycle fields owned once | yes |  |
| learning core cannot write lifecycle slots | `["must not directly write lifecycle slot state or fabricate lineage"]` | forbidden direct slot writes | yes |  |
| host limited to control/readback | `["LIFE_INIT_CONTROL", "LIFE_SUMMARY_READBACK"]` | host only init/readback | yes |  |
| inter-core lifecycle messages declared | `["LIFE_EVENT_REQUEST", "LIFE_TROPHIC_UPDATE", "LIFE_ACTIVE_MASK_SYNC"]` | event, trophic, mask sync present | yes |  |
| MCPL/multicast target explicit | `["host SDP control", "inter-core event packet; MCPL/multicast target, SDP permitted only in local transitional tests", "inter-core event ...` | inter-core transport names MCPL/multicast target | yes |  |
| canonical split matches artifact reference | `true` | == true | yes |  |
| boundary split matches artifact reference | `true` | == true | yes |  |
| canonical split matches regenerated reference | `true` | == true | yes |  |
| boundary split matches regenerated reference | `true` | == true | yes |  |
| canonical event ack count | `32` | == 32 | yes |  |
| boundary event ack count | `64` | == 64 | yes |  |
| canonical consumers receive final active mask | `true` | == true | yes |  |
| boundary consumers receive final active mask | `true` | == true | yes |  |
| payload length requirement explicit | `"payload_len=68"` | not cumulative readback_bytes | yes |  |
| failure classes cover distributed lifecycle risks | `["duplicate_event", "stale_event", "missing_ack", "mask_desync", "checksum_mismatch", "invalid_event_hidden", "wrong_owner_write", "paylo...` | >= 8 classes | yes |  |
| no EBRAINS package generated | `"local-contract-reference"` | mode is local only | yes |  |
| claim boundary excludes hardware/task/speedup/baseline | `"bounded local contract"` | explicit exclusions | yes |  |

## Next Step

Tier 4.30d multi-core lifecycle runtime source audit/local C host test: implement the lifecycle-core profile and inter-core message/readback stubs against this contract before any EBRAINS package.
