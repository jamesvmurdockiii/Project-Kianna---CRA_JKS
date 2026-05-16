# Tier 4.22a Custom / Hybrid On-Chip Runtime Contract

- Generated: `2026-04-30T17:32:07+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_22a_20260430_custom_runtime_contract`

Tier 4.22a is the auditable migration contract from the proven chunked-host hardware bridge toward a custom/hybrid/on-chip runtime. It is a design gate, not a hardware pass.

## Why This Exists

- Tier 4.20c proved repeatable v2.1 chunked-host bridge transport on real SpiNNaker.
- Tier 4.21a proved one stateful v2 mechanism, keyed context memory, can ride that bridge.
- Tier 4.21a also took nearly one hour for one seed and four variants, so exhaustive bridge matrices are not the right architecture path.
- Tier 4.22a defines what moves on-chip/hybrid next and how parity will be judged.

## Claim Boundary

- `PASS` means the custom-runtime migration contract is explicit and references real evidence.
- This is not custom C, not native/on-chip CRA, not continuous execution, and not a speedup claim.
- Future speed claims require measured runtime/readback/provenance reductions.

## Reference Evidence

- Tier 4.20c status: `pass`
- Tier 4.20c manifest: `<repo>/controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_hardware_pass_ingested/tier4_20c_results.json`
- Tier 4.20c child runs: `6`
- Tier 4.20c minimum real spike readback: `94727`
- Tier 4.21a status: `pass`
- Tier 4.21a manifest: `<repo>/controlled_test_output/tier4_21a_20260430_keyed_context_memory_seed42_hardware_pass_ingested/tier4_21a_results.json`
- Tier 4.21a runs: `4`
- Tier 4.21a minimum real spike readback: `714601`
- Tier 4.21a runtime: `3522.71` seconds

## Runtime Target

- Current chunked reference calls per `1200`-step case at chunk `50`: `24`
- Continuous target calls per case: `1`
- The target is fewer host interventions and compact readback, not blind speed claims.

## State Ownership

| Subsystem | Current | Tier 4.22 target | Later target | Main risk |
| --- | --- | --- | --- | --- |
| experiment orchestration | host | host | host | none; moving this on-chip would reduce auditability rather than improve runtime |
| input/event scheduling | host chunk scheduler | hybrid: host sends compact scheduled event streams, chip consumes continuously | mostly on-chip event/state machine for repeated tasks | event timing drift or hidden future/context leakage |
| spike dynamics | SpiNNaker/PyNN cell dynamics | chip | chip | readback volume can erase runtime gains |
| delayed credit / reward state | host PendingHorizon / host replay | hybrid first: chip stores compact eligibility/recent activity; host may send sparse reward events | on-chip local eligibility/reward update when fixed-point parity passes | per-synapse trace memory or per-ms trace sweeps exceed chip resources |
| keyed context memory | host keyed-memory scheduler | hybrid/on-chip preallocated slots with host-readable counters | chip-local fixed-size slot table and routing masks | dynamic Python dictionaries do not map directly to chip memory; slot count must be bounded |
| replay / consolidation | host offline replay loop | host-led replay window or hybrid scheduled replay, not first on-chip target | chip-assisted replay after compact memory-store design exists | replay can fabricate training exposure unless phase boundaries are explicit |
| composition / routing / self-evaluation | host mechanism tables and monitor | host/hybrid summary-driven control after lower-level state is stable | bounded chip-local router/monitor counters where useful | high-level mechanism appears to work through host hints rather than hardware state |
| readback/provenance | full or frequent spike/readback extraction | compact end-of-run summaries plus optional debug windows | compact summaries by default; full readback only for diagnostics | too little readback makes failures uninterpretable; too much readback kills speed |

## Runtime Stages

| Stage | Purpose | Pass gate | Claim if passed |
| --- | --- | --- | --- |
| 4.22a0 constrained-NEST + sPyNNaker mapping preflight | catch hardware-transfer failures before expensive EBRAINS runs | constrained-NEST parity passes, unsupported PyNN features are absent, no dynamic graph mutation is required, and sPyNNaker can build/map or complete a tiny smoke run in the target environment | pre-hardware transfer risk is reduced; final hardware evidence is still required |
| 4.22b continuous no-learning scaffold | prove a one-call or near-one-call hardware run can execute scheduled input and return compact summaries | real hardware run, no synthetic fallback, <= 1 sim.run per task/variant, compact summary readback, spike totals within predeclared tolerance | continuous hardware scaffold works for CRA-compatible scheduled streams; no learning claim |
| 4.22c persistent local state scaffold | prove chip/hybrid state persists across internal decisions without host replay after every chunk | state counters/slots persist, reset only on declared reset, and match bridge reference qualitatively | persistent hardware/hybrid state scaffold exists; still no full on-chip learning claim |
| 4.22d reward/plasticity on-chip or hybrid | move the delayed-credit bottleneck out of per-step host replay | learning metric matches chunked reference qualitatively, weight summaries are bounded, and fixed-point traces pass range/decay checks | hybrid/native reward-plasticity path works on a minimal CRA capsule |
| 4.22e keyed memory / routing state integration | move the first stateful v2 mechanism from bridge adapter toward persistent chip/hybrid state | keyed candidate keeps bridge-level behavior while slot-reset/shuffle/wrong-key controls still separate | bounded keyed memory/routing state survives the custom/hybrid runtime |
| 4.23 continuous / stop-batching parity | prove the custom runtime can replace the chunked bridge reference | accuracy/correlation/recovery/state counters within tolerance; runtime/readback reduction documented; repeatable across seeds | custom/hybrid continuous runtime is a valid replacement for the chunked proof bridge |

## Parity Contract

| Reference | Candidate | Metric | Rule | Failure interpretation |
| --- | --- | --- | --- | --- |
| Tier 4.20c chunked bridge | 4.22a0 constrained-NEST preflight | hardware-legal model subset | same task/stream contracts pass without unsupported PyNN features, dynamic graph mutation, unbounded host state, or future-information leakage | software mechanism is not yet hardware-compatible enough to justify EBRAINS runtime |
| Tier 4.20c chunked bridge | 4.22b continuous scaffold | spike-count summary | same order of magnitude and no silent zero-spike collapse; exact equality not required | transport/scheduling problem before learning can be judged |
| Tier 4.20c chunked bridge | 4.22d reward/plasticity | delayed_cue tail accuracy and hard-switch qualitative behavior | delayed_cue remains near 1.0; hard-switch remains above declared transfer threshold or failure is diagnosed | credit/plasticity implementation bug or resource-constrained narrowing of claim |
| Tier 4.21a keyed-memory bridge | 4.22e keyed memory/routing state | keyed-vs-ablation separation | keyed candidate beats wrong-key/slot-shuffle and is not worse than slot-reset; slot telemetry active | keyed state is not represented correctly in custom runtime |
| Tier 5 software guardrails | 4.23 continuous custom runtime | no-leakage and sham-control preservation | control failures remain failures; no future context/reward is visible before decision | runtime is leaking information or task contract changed |
| Tier 4.18a/4.21a runtime observations | 4.23 continuous custom runtime | runtime/readback cost | sim.run calls reduced toward 1 per case and readback volume reduced; exact wall-time speedup must be measured | custom runtime may be correct but not yet useful as a scaling path |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22a_custom_runtime_contract_20260430_0000` | `expected current source` | yes |
| Tier 4.20c reference pass exists | `pass` | `== pass` | yes |
| Tier 4.21a reference pass exists | `pass` | `== pass` | yes |
| Tier 4.20c had zero child sim/readback/fallback failures | `{"fallback": 0, "readback": 0, "sim": 0}` | `all == 0` | yes |
| Tier 4.21a had zero sim/readback/fallback failures | `{"fallback": 0, "readback": 0, "sim": 0}` | `all == 0` | yes |
| state ownership table covers core subsystems | `8` | `>= 6` | yes |
| runtime stage plan defines staged gates | `6` | `>= 5` | yes |
| parity contract defines reference/candidate checks | `6` | `>= 4` | yes |
| memory/resource budget risks documented | `6` | `>= 5` | yes |
| no exhaustive per-mechanism bridge mandate | `Do not run exhaustive per-mechanism hardware bridge matrices by default.` | `explicitly avoid default exhaustive hardware matrices` | yes |
| pre-hardware constrained emulation/mapping gate declared | `Implement constrained-NEST plus sPyNNaker mapping preflight before any further expensive hardware allocation.` | `constrained-NEST plus sPyNNaker preflight before more hardware` | yes |
| continuous target is not marked implemented | `False` | `False until custom runtime exists` | yes |

## Recommended Sequence

1. Use Tier 4.20c and Tier 4.21a as chunked-host reference traces.
2. Do not run exhaustive per-mechanism hardware bridge matrices by default.
3. Implement constrained-NEST plus sPyNNaker mapping preflight before any further expensive hardware allocation.
4. Implement 4.22b continuous no-learning scaffold first.
5. Add 4.22c persistent local state only after 4.22b returns auditable summaries.
6. Add 4.22d reward/plasticity/eligibility with fixed-point/resource logs.
7. Add 4.22e keyed memory/routing state after lower-level state is stable.
8. Run 4.23 continuous parity against chunked reference before any final hardware claim.
