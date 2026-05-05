# Tier 4.30 Lifecycle-Native Static-Pool Contract

- Generated: `2026-05-05T19:41:04+00:00`
- Runner revision: `tier4_30_lifecycle_native_contract_20260505_0001`
- Status: **PASS**
- Criteria: `14/14`

## Claim Boundary

Tier 4.30 is a local engineering contract. It does not implement the C runtime lifecycle surface, does not run hardware, does not prove lifecycle/self-scaling, does not freeze a lifecycle baseline, does not migrate v2.2 temporal state, and does not claim speedup or multi-chip scaling.

## Contract Decision

- Base native line: `CRA_NATIVE_MECHANISM_BRIDGE_v0.3`
- Software reference line: `v2.2`
- Pool size: `8`
- Founder count: `2`
- Capacity model: fixed compile-time pool; lifecycle events activate, silence, or reassign slots

Forbidden for Tier 4.30:

- dynamic PyNN population creation mid-run
- legacy SDRAM malloc/free neuron_birth/neuron_death as lifecycle proof
- host-only lifecycle decisions without readback
- unscoped native v2.2 fading-memory migration
- multi-chip or speedup claims

## Command Schema

| Command | Owner | Phase | Payload Fields | Deterministic Rule | Required Ack | Forbidden Behavior |
| --- | --- | --- | --- | --- | --- | --- |
| `CMD_LIFECYCLE_INIT` | host -> lifecycle core | setup before run | pool_size, founder_count, seed, trophic_seed_raw, generation_seed | initial active slots are 0..founder_count-1; all other slots inactive | pool_size, active_count, inactive_count, lineage_checksum | no dynamic allocation, no graph rebuild, no implicit extra founders |
| `CMD_LIFECYCLE_EVENT` | host/reference -> lifecycle core | local reference and first hardware smoke | event_index, event_type, parent_slot, target_slot, child_slot, trophic_delta_raw, reward_raw | event is applied only if invariants hold; invalid events increment invalid_event_count | event_index, last_event_type, event_count, active_mask_checksum | no silent overwrite of active child slot, no lineage mutation without event telemetry |
| `CMD_LIFECYCLE_TROPHIC_UPDATE` | learning core -> lifecycle core | after lifecycle smoke, before task-effect claims | slot_id, reward_raw, activity_raw, prediction_error_raw, decay_raw | trophic_health, cyclin_d, and bax update in fixed-point with explicit clipping | slot_id, trophic_health_raw, cyclin_d_raw, bax_raw | no float-only host trophic decision in hardware claim |
| `CMD_LIFECYCLE_READ_STATE` | host <- lifecycle core | debug, ingest, and paper audit | read_scope, start_slot, slot_count, schema_version | readback schema is stable and versioned; compact summary always available | schema_version, pool_summary, per-slot compact rows or declared truncation | no paper claim from unversioned or partial lifecycle state |
| `CMD_LIFECYCLE_SHAM_MODE` | host -> lifecycle core | sham-control runs | control_mode, event_budget, shuffle_seed, disable_trophic, disable_plasticity | control perturbation is seeded and reproduced exactly by local reference | control_mode, shuffle_seed, event_budget, sham_counter | no post-hoc relabeling of failed lifecycle runs as controls |

## Readback Schema

| Field | Type | Owner | When Read | Purpose | Pass Rule |
| --- | --- | --- | --- | --- | --- |
| `schema_version` | `uint16` | host_interface | every read | detect stale parser/report mismatch | matches contract version |
| `pool_size` | `uint16` | lifecycle_core | every read | prove fixed capacity | equals declared static pool |
| `active_count` | `uint16` | lifecycle_core | every read | prove mask state | matches popcount(active_mask) |
| `inactive_count` | `uint16` | lifecycle_core | every read | capacity accounting | active + inactive == pool_size |
| `active_mask_bits` | `uint32` | lifecycle_core | every read | compact active/inactive proof | matches reference bitmask |
| `lineage_checksum` | `uint32` | lifecycle_core | every read | compact lineage integrity | matches local reference |
| `trophic_checksum` | `int32` | lifecycle_core | every read | compact trophic integrity | within fixed-point tolerance |
| `event_count` | `uint32` | lifecycle_core | every read | event accounting | matches accepted events |
| `cleavage_count` | `uint32` | lifecycle_core | every read | reproduction accounting | matches reference |
| `birth_count` | `uint32` | lifecycle_core | every read | adult birth accounting | matches reference |
| `death_count` | `uint32` | lifecycle_core | every read | death accounting | matches reference |
| `invalid_event_count` | `uint32` | lifecycle_core | every read | invariant failure accounting | zero in canonical pass |
| `slot_id` | `uint16` | lifecycle_core | debug/full read | stable static-pool index | 0 <= slot_id < pool_size |
| `active_mask` | `uint8` | lifecycle_core | debug/full read | per-slot active flag | matches reference |
| `polyp_id` | `uint32` | lifecycle_core | debug/full read | auditable identity | stable unless slot is reassigned by accepted event |
| `lineage_id` | `uint32` | lifecycle_core | debug/full read | lineage audit | matches reference lineage tree |
| `parent_slot` | `int16` | lifecycle_core | debug/full read | birth provenance | -1 for founders or valid parent slot |
| `generation` | `uint16` | lifecycle_core | debug/full read | lifecycle depth | increments only on accepted child event |
| `age_steps` | `uint32` | lifecycle_core | debug/full read | maturity gates | monotonic while active |
| `trophic_health_raw` | `s16.15` | lifecycle_core | debug/full read | survival/reproduction pressure | clipped and matches fixed-point reference |
| `cyclin_d_raw` | `s16.15` | lifecycle_core | debug/full read | reproduction gate | clipped and matches fixed-point reference |
| `bax_raw` | `s16.15` | lifecycle_core | debug/full read | death gate | clipped and matches fixed-point reference |
| `last_event_type` | `uint8` | lifecycle_core | debug/full read | event audit | matches final accepted event for slot |

## Event Semantics

| Event | Trigger Inputs | State Updates | Required Invariants | Sham Control |
| --- | --- | --- | --- | --- |
| `trophic_update` | slot activity/reward/error summary | trophic_health, cyclin_d, bax, age_steps | slot active; fixed-point values clipped; no lineage mutation | `no_trophic_pressure_control` |
| `cleavage` | parent active, inactive child slot available, cyclin gate passes | child active, child parent_slot, child generation, child lineage_id, cleavage_count | parent remains active; child was inactive; event increments exactly once | `random_event_replay_control` |
| `adult_birth` | adult parent active, inactive child slot available, trophic and maturity gates pass | child active, child lineage_id/parent/generation, birth_count | adult gate explicit; no dynamic allocation; no hidden extra capacity | `fixed_static_pool_control` |
| `death` | active slot, bax/death gate passes or explicit reference event | slot inactive, death_count, final lineage telemetry preserved | active_count decreases by one; lineage remains readable after death | `active_mask_shuffle_control` |
| `maturity_handoff` | age threshold or trophic threshold reached | last_event_type, maturity marker encoded through cyclin/trophic state | no active-mask change unless paired with accepted birth/cleavage/death | `lineage_id_shuffle_control` |

## Gate Sequence

1. **Tier 4.30 contract** (local engineering): command/readback schema and invariant specification
   Pass: all readiness inputs pass; command/readback/event/gate/failure schemas complete
   Fail: ambiguous ownership, missing shams, dynamic allocation dependency, or unscoped v2.2 migration
   Artifacts: results JSON, report MD, command/readback/event/gate/failure CSVs
2. **Tier 4.30a local static-pool reference** (local deterministic reference): 8-slot pool, 2 founders, 32-64 lifecycle events, no hardware
   Pass: exact active mask/lineage/event/checksum parity and all controls precomputed
   Fail: any nondeterminism, hidden capacity growth, invalid events in canonical pass
   Artifacts: local reference JSON, per-event CSV, final state CSV, control summaries
3. **Tier 4.30b single-core hardware smoke** (EBRAINS/SpiNNaker): active-mask and lineage telemetry only, one seed first
   Pass: real hardware, zero fallback, compact readback matches local reference within fixed-point tolerance
   Fail: readback schema mismatch, stale state, dynamic allocation, timeout, or lineage checksum mismatch
   Artifacts: hardware results JSON, report MD, board/core info, compact readback, ingest report
4. **Tier 4.30c multi-core lifecycle split** (EBRAINS/SpiNNaker): lifecycle state split from learning/context/route/memory cores
   Pass: no stale replies, no mask corruption, local parity preserved across cores
   Fail: cross-core stale reply, timeout, corrupted lineage, or unmatched event count
   Artifacts: core map, message counters, compact readback, local/hardware diff
5. **Tier 4.30d lifecycle sham-control subset** (local then hardware subset): fixed pool, random events, mask shuffle, lineage shuffle, no trophic, no dopamine/plasticity
   Pass: lifecycle-enabled path separates from shams on a predeclared lifecycle-pressure task
   Fail: shams match lifecycle, no task effect, or lineage telemetry is decorative
   Artifacts: control matrix CSV, effect sizes, per-seed rows, failure classification

## Failure Classes

| Failure Class | Meaning | Required Response |
| --- | --- | --- |
| `contract_gap` | A command, field, control, artifact, or claim boundary is not specified. | Do not implement runtime code; repair the contract first. |
| `dynamic_allocation_dependency` | The proposed lifecycle proof depends on dynamic graph creation or malloc/free neuron birth/death. | Reject as noncanonical for Tier 4.30; redesign as static pool/mask. |
| `local_reference_mismatch` | C/local candidate does not match the deterministic Python reference. | Debug locally; no EBRAINS upload. |
| `readback_schema_mismatch` | Hardware emits a state schema the ingest/parser cannot verify. | Stop and repair schema/versioning; no scientific claim. |
| `lineage_or_mask_corruption` | Active mask, lineage checksum, parent links, or event counters diverge. | Classify as lifecycle-state failure and debug before controls. |
| `sham_explains_effect` | Fixed capacity, random events, shuffled masks, shuffled lineage, or no-trophic controls match the enabled path. | Do not promote lifecycle-native baseline; narrow organism claim or redesign mechanism. |
| `unsupported_claim_jump` | A report claims lifecycle superiority, multi-chip scaling, speedup, or native v2.2 temporal state from this contract. | Reject report wording and correct source-of-truth docs. |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| readiness audit passed | `pass` | `== pass` | yes |  |
| readiness audit criteria complete | `16/16` | `== 16/16` | yes |  |
| layering decision imported | `layer_initial_lifecycle_native_work_on_native_mechanism_bridge_v0_3_with_v2_2_as_software_reference_only` | `uses native mechanism bridge with v2.2 software reference only` | yes |  |
| static runtime capacity sufficient for first reference | `{'MAX_NEURONS': 1024, 'MAX_CONTEXT_SLOTS': 128, 'MAX_ROUTE_SLOTS': 8, 'MAX_MEMORY_SLOTS': 8, 'MAX_PENDING_HORIZONS': 128, 'MAX_SCHEDULE_ENTRIES': 512}` | `MAX_NEURONS>=8 and schedule>=64` | yes |  |
| legacy dynamic birth/death excluded | `True` | `identified and excluded` | yes | The legacy path exists but is explicitly not the Tier 4.30 proof. |
| lifecycle surface not already silently present | `False` | `== false before implementation` | yes |  |
| command schema declared | `5` | `>= 5 commands` | yes |  |
| readback schema declared | `23` | `>= 20 fields` | yes |  |
| event semantics declared | `5` | `>= 5 lifecycle event types` | yes |  |
| gate sequence declared | `5` | `>= 5 gates` | yes |  |
| failure classes declared | `7` | `>= 6 classes` | yes |  |
| static-pool contract declares bounded pool | `8` | `== 8 with 2 founders` | yes |  |
| local reference required before hardware | `contract pass, local reference pass, source audit pass, generated package contains source only` | `mentions contract/local/source audit before package` | yes |  |
| claim boundary forbids unsupported jumps | `['dynamic PyNN population creation mid-run', 'legacy SDRAM malloc/free neuron_birth/neuron_death as lifecycle proof', 'host-only lifecycle decisions without readback', 'unscoped native v2.2 fading-memory migration', 'multi-chip or speedup claims']` | `>= 5 forbidden behaviors` | yes |  |

## Next Step

Tier 4.30a local static-pool lifecycle reference
