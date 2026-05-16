# Tier 4.30-Readiness Lifecycle-Native Audit

- Generated: `2026-05-05T19:31:07+00:00`
- Runner revision: `tier4_30_readiness_audit_20260505_0001`
- Status: **PASS**
- Criteria: `16/16`

## Claim Boundary

Tier 4.30-readiness is a local engineering audit. It does not implement lifecycle hardware, does not run EBRAINS/SpiNNaker, does not prove native lifecycle, does not migrate v2.2 temporal state, and does not freeze a new lifecycle or native baseline.

## Layering Decision

- Decision: `layer_initial_lifecycle_native_work_on_native_mechanism_bridge_v0_3_with_v2_2_as_software_reference_only`
- Rationale: Lifecycle/self-scaling is an organism/ecology mechanism. The existing native bridge already owns context, route, memory, prediction, confidence, replay, pending maturation, and MCPL-distributed lookup primitives. v2.2 adds useful host-side fading-memory temporal state, but it is not yet native/on-chip and should not be smuggled into the first lifecycle hardware gate.

In scope for the first lifecycle-native path:

- static preallocated lifecycle pool
- active/inactive masks
- lineage IDs and parent links
- trophic-health counters
- birth/cleavage/death event telemetry
- fixed-pool and sham controls
- compact readback and local fixed-point parity

Out of scope for the first lifecycle-native path:

- dynamic PyNN population creation mid-run
- legacy SDRAM malloc/free neuron_birth/neuron_death as the lifecycle proof
- native v2.2 temporal fading-memory state
- native nonlinear recurrence
- multi-chip scaling
- speedup claims
- paper-level lifecycle superiority

## Static-Pool Contract

- Initial pool slots: `8`
- Initial active slots: `2`
- Capacity rule: fixed compile-time pool; events toggle/assign slots rather than allocate/free graph objects
- Runtime owner: new lifecycle state path or lifecycle profile layered beside existing state/context/route/memory/learning cores

## Lifecycle Fields

| Field | Type | Owner | Required For | Initial Value | Readback |
| --- | --- | --- | --- | --- | --- |
| `slot_id` | `uint16` | `lifecycle_core` | stable static-pool index | `0..pool_size-1` | yes |
| `active_mask` | `uint8` | `lifecycle_core` | activate/silence preallocated units | `founder slots active only` | yes |
| `polyp_id` | `uint32` | `lifecycle_core` | auditable identity | `stable deterministic id` | yes |
| `lineage_id` | `uint32` | `lifecycle_core` | lineage accounting | `founder lineage id` | yes |
| `parent_slot` | `int16` | `lifecycle_core` | birth/cleavage provenance | `-1 for founders` | yes |
| `generation` | `uint16` | `lifecycle_core` | cleavage/birth depth | `0` | yes |
| `age_steps` | `uint32` | `lifecycle_core` | maturity / juvenile gates | `0` | yes |
| `trophic_health` | `s16.15` | `lifecycle_core` | survival/reproduction gates | `initial trophic seed` | yes |
| `cyclin_d` | `s16.15` | `lifecycle_core` | reproduction gate | `0` | yes |
| `bax` | `s16.15` | `lifecycle_core` | death gate | `0` | yes |
| `last_event_type` | `uint8` | `lifecycle_core` | event audit | `none` | yes |
| `event_count` | `uint32` | `lifecycle_core` | lifecycle telemetry | `0` | yes |

## Controls

| Control | Purpose | Expected Effect |
| --- | --- | --- |
| `fixed_static_pool_control` | Shows any benefit is not just the preallocated max capacity. | Lifecycle-enabled path must beat or differ from fixed active mask only on lifecycle-pressure tasks. |
| `random_event_replay_control` | Matches event count while destroying event causality. | Random matched events should not reproduce lineage/trophic/task benefit. |
| `active_mask_shuffle_control` | Destroys identity-to-slot binding while preserving active count. | Mask shuffle should break lineage-specific or specialist reuse claims. |
| `lineage_id_shuffle_control` | Checks whether lineage bookkeeping is causal or decorative. | Lineage shuffle should damage lineage-dependent claims without changing raw capacity. |
| `no_trophic_pressure_control` | Removes ecology pressure while leaving state machinery alive. | No-trophic path should lose lifecycle selection-specific effects. |
| `no_dopamine_or_plasticity_control` | Separates lifecycle bookkeeping from actual learning/reward coupling. | No learning/plasticity should not pass task-effect gates. |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| v2.2 baseline exists and is frozen | `v2.2` | `== v2.2 and status frozen` | yes |  |
| v2.2 registry stayed green | `pass` | `== pass` | yes |  |
| v2.2 boundary excludes hardware/on-chip temporal claim | `['v2.2 is host-side software evidence for bounded multi-timescale fading-memory temporal state.', 'v2.2 does not prove bounded nonlinear recurrence; Tier 5.19b/5.19c explicitly leave recurrence unproven.', 'v2.2 does not prove hardware transfer or native on-chip temporal dynamics.', 'v2.2 does not prove universal superiority on Mackey-Glass, Lorenz, NARMA10, or external baselines; lag-only remains stronger on the standard-three geomean in this gate.', 'v2.2 does not prove language, long-horizon planning, AGI, or ASI.']` | `mentions no hardware/on-chip temporal dynamics` | yes |  |
| native mechanism bridge v0.3 exists | `CRA_NATIVE_MECHANISM_BRIDGE_v0.3` | `== CRA_NATIVE_MECHANISM_BRIDGE_v0.3` | yes |  |
| native bridge registry stayed green | `pass` | `== pass` | yes |  |
| Tier 4.29f evidence regression passed | `113/113` | `== 113/113 and status pass` | yes |  |
| runtime source tree exists | `<repo>/coral_reef_spinnaker/spinnaker_runtime/src` | `config/state/host/neuron source files present` | yes |  |
| static state capacity exists | `{'MAX_NEURONS': 1024, 'MAX_CONTEXT_SLOTS': 128, 'MAX_ROUTE_SLOTS': 8, 'MAX_MEMORY_SLOTS': 8, 'MAX_PENDING_HORIZONS': 128, 'MAX_SCHEDULE_ENTRIES': 512}` | `context>=16 route>=4 memory>=4 pending>=32 schedule>=128` | yes |  |
| MCPL data plane available for native scaling path | `True` | `== true` | yes |  |
| compact readback path available | `True` | `== true` | yes |  |
| legacy dynamic birth/death identified | `True` | `== true and excluded from initial lifecycle-native proof` | yes | Existing neuron_birth/death uses SDRAM allocation/free and must not be treated as the static-pool lifecycle proof. |
| lifecycle static-pool fields are not already implemented | `False` | `== false; blocker explicitly declared` | yes | This is expected at readiness stage; Tier 4.30 must add a bounded lifecycle state surface before hardware. |
| layering decision explicit | `layer_initial_lifecycle_native_work_on_native_mechanism_bridge_v0_3_with_v2_2_as_software_reference_only` | `non-empty with out-of-scope list` | yes |  |
| static-pool contract fields declared | `12` | `>= 10 readback fields` | yes |  |
| lifecycle sham controls declared | `6` | `>= 6 controls` | yes |  |
| artifact expectations declared | `7` | `>= 6 artifacts` | yes |  |

## Recommended Sequence

1. Tier 4.30 contract: formalize static-pool lifecycle surface and command/readback schema.
2. Tier 4.30a local reference: deterministic static-pool event stream and fixed-point parity.
3. Tier 4.30b single-core hardware smoke: active-mask and lineage telemetry only.
4. Tier 4.30c multi-core lifecycle state split if 4.30b passes.
5. Tier 4.30d lifecycle sham-control hardware subset before any lifecycle-native baseline freeze.
6. Separate native temporal-readiness tier only if v2.2 fading-memory state is selected for hardware migration.
