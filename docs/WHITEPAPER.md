# Coral Reef Architecture Whitepaper

## Document Status

This whitepaper is a technical overview of the implementation and evidence in
this repository. It is not a peer-reviewed paper. All claims are bounded by the
canonical evidence registry in `controlled_test_output/STUDY_REGISTRY.json`, the
frozen baseline locks in `baselines/`, and the tier definitions in
`CONTROLLED_TEST_PLAN.md`.

## Executive Summary

Coral Reef Architecture (CRA) is a neuromorphic local-learning research platform.
It explores whether populations of small spiking agents can learn and adapt using
local plasticity, delayed consequence signals, trophic selection, lifecycle
pressure, and hardware-compatible state machines rather than global
backpropagation.

The project contains three integrated layers:

1. A Python/PyNN research implementation of the organism, task adapters,
   learning, energy, lifecycle, and backend integrations.
2. A custom SpiNNaker C runtime used to migrate selected mechanisms into native
   hardware-executed state, routing, memory, and learning cores.
3. A staged evidence system that records canonical results, failed diagnostics,
   frozen baselines, and claim boundaries.

As of the current registry, CRA has 115 canonical evidence bundles with zero
missing expected artifacts and zero failed criteria in canonical entries. The
software program has validated negative controls, positive learning controls,
architecture ablations, external-baseline comparisons, delayed-credit repairs,
lifecycle/self-scaling, lifecycle sham controls, circuit-motif causality, and
bounded host-side mechanisms for memory, replay/consolidation, predictive
context, composition/routing, working-memory diagnostics, temporal spike coding,
neuron-parameter sensitivity, predictive binding, self-evaluation, and
fading-memory temporal state.

The hardware program has progressed from PyNN/SpiNNaker capsule execution to a
custom native runtime. The native runtime has passed bounded SpiNNaker hardware
checks for four-core MCPL task execution, keyed memory, routing/composition,
predictive binding, confidence-gated learning, host-scheduled
replay/consolidation, and lifecycle static-pool/sham/task-bridge evidence. Tier
4.30g-hw froze the lifecycle-native baseline v0.4 with a host-ferried bridge
boundary. Tier 4.31a then passed local readiness for the next v2.2 temporal-state
migration, defining seven causal fixed-point EMA traces before any C/runtime or
EBRAINS package. Tier 4.31b passed the local fixed-point reference gate for that subset, matching
the v2.2 fading-memory reference with zero selected saturations and separated
destructive controls. Tier 4.31c then passed local source/runtime audit with
C-owned temporal state, compact 48-byte readback, command codes 39-42,
behavior-backed shams, profile ownership guards, and local C host tests. Tier
4.31d-hw passed the first one-board SpiNNaker hardware smoke for that temporal
subset with compact payload length 48 and enabled/zero/frozen/reset controls.
Tier 4.31e then passed a replay/eligibility decision closeout, deferring native
replay buffers, sleep-like replay, and native macro eligibility until measured
blockers justify them, and authorizing Tier 4.32 mapping/resource modeling. Tier
4.32 passed that local resource model: MCPL is the scale data plane and returned
profile builds have positive ITCM/DTCM headroom. Tier 4.32a then passed the
local single-chip scale-stress preflight, authorizing only the 4/5-core
single-shard hardware stress points and blocking replicated 8/12/16-core stress
until shard-aware MCPL routing exists. Tier 4.32a-r0 then blocked the planned
MCPL-first hardware package: confidence-gated learning still used transitional
SDP, MCPL replies dropped confidence/hit status, MCPL receive hardcoded
confidence=1.0, and the MCPL key lacked shard identity. Tier 4.32a-r1 repaired
that blocker locally with value/meta MCPL reply packets, shard-aware keys,
cross-shard controls, and full/zero/half-confidence learning controls over the
repaired MCPL path. Static partitioning, replicated stress, multi-chip work, and
native-scale baseline freeze remain blocked until single-shard hardware stress
passes.

The current evidence supports a bounded research claim: CRA is a reproducible
neuromorphic platform with demonstrated local learning, mechanism sensitivity,
selected software capability upgrades, and repeatable SpiNNaker execution for
constrained task capsules and native-runtime mechanism bridges. The evidence does
not establish general intelligence, universal superiority over baselines,
production readiness, full multi-chip scaling, autonomous lifecycle-to-learning
MCPL, repeatable/full native v2.2 temporal dynamics beyond the one-board
seven-EMA smoke, single-shard/repeated confidence-bearing MCPL scale stress on
hardware, native replay/sleep or native macro eligibility, or fully autonomous
on-chip implementations of all promoted software mechanisms.

## Motivation

Most modern machine-learning systems are optimized through global differentiable
objectives. Biological nervous systems use additional mechanisms: local
plasticity, modulatory signals, temporal spike structure, metabolic constraints,
structural adaptation, and population-level selection. CRA investigates whether
those mechanisms can be turned into a computational substrate that is testable,
falsifiable, and compatible with neuromorphic hardware.

The central research question is:

```text
Can a population of local spiking agents learn, adapt, retain useful state, and
transfer selected mechanisms to SpiNNaker hardware under strict controls?
```

The project does not claim to replace deep learning. It tests a narrower and more
scientifically useful question: whether a biologically structured local-learning
system can pass controls that distinguish real mechanism behavior from leakage,
shortcuts, lucky seeds, and implementation artifacts.

## Architecture Overview

A CRA organism is represented as a directed reef graph of small neural agents
called polyps. The biological terms are engineering abstractions. They define a
structured set of mechanisms to test, not a claim that the model is biologically
literal.

| Layer | Role | Main files |
| --- | --- | --- |
| Configuration | Central parameter source | `coral_reef_spinnaker/config.py`, `config_adapters.py` |
| Neural substrate | Polyps, populations, graph motifs, backend projections | `polyp_state.py`, `polyp_population.py`, `polyp_plasticity.py`, `reef_network.py` |
| Learning | Dopamine/RPE, delayed credit, readout updates | `learning_manager.py` |
| Energy economy | Sensory, outcome, and retrograde trophic accounting | `energy_manager.py` |
| Lifecycle | Birth, death, lineage, juvenile/adult state | `lifecycle.py` |
| Task interface | Domain-neutral consequences and adapters | `signals.py`, `task_adapter.py`, `trading_bridge.py` |
| Backends | Mock, NEST, Brian2, PyNN/SpiNNaker compatibility | `backend_factory.py`, `mock_simulator.py`, `spinnaker_compat.py` |
| Custom runtime | Native SpiNNaker state, routing, memory, learning cores | `coral_reef_spinnaker/spinnaker_runtime/` |
| Evidence | Tier runners, registry, paper table, audit | `experiments/`, `controlled_test_output/` |

## Biological Design Principles

CRA uses the following biological ideas as engineering constraints:

| Principle | CRA interpretation | Evidence status |
| --- | --- | --- |
| Local plasticity | Synaptic/readout changes are driven by local state and modulatory signals. | Tiers 2-5.7, custom runtime 4.22-4.29. |
| Delayed credit | Pending consequence records mature after a horizon and update learning. | Tiers 5.3-5.4, 4.16, 4.22, 4.28. |
| Trophic selection | Polyps gain or lose support based on information and outcomes. | Tiers 3, 6.1, 6.3. |
| Lifecycle pressure | Population expansion and lineage are measurable and ablatable. | Tiers 6.1, 6.3. |
| Circuit motifs | Graph motifs and edge roles are tested causally, not treated as decoration. | Tier 6.4. |
| Context and memory | Bounded keyed memory, replay, and context routing are tested with shams. | Tiers 5.10-5.14, 4.29a-b. |
| Prediction and reliability | Predictive binding and confidence-gated learning are tested before reward. | Tiers 5.12, 5.17, 5.18, 4.29c-d. |

These mechanisms remain bounded by their evidence tier. Biological inspiration is
not treated as proof.

## Evidence Methodology

CRA uses a staged evidence ladder. Each tier is expected to define:

- The exact question being tested.
- Hypothesis and null hypothesis.
- Mechanism under test.
- Controls, shams, ablations, seeds, and metrics.
- Pass/fail criteria.
- Expected artifacts.
- Claim boundary and nonclaims.

Results are classified as canonical, baseline-frozen, noncanonical diagnostic,
failed/parked diagnostic, or prepared hardware evidence. Failed and ambiguous
runs are preserved so that later claims are not cherry-picked.

The canonical registry is generated by `experiments/evidence_registry.py` and
written to:

- `controlled_test_output/STUDY_REGISTRY.json`
- `controlled_test_output/STUDY_REGISTRY.csv`
- `controlled_test_output/README.md`
- `STUDY_EVIDENCE_INDEX.md`

The paper-facing table is generated by
`experiments/export_paper_results_table.py`.

## Evidence Summary

| Evidence area | Current result | Boundary |
| --- | --- | --- |
| Negative controls | Zero-signal and shuffled-label controls do not fake learning. | Does not prove positive learning by itself. |
| Positive learning | Fixed pattern, delayed reward, and nonstationary switching learn in controlled software tasks. | Controlled task families only. |
| Architecture ablations | Dopamine, plasticity, and trophic selection matter. | Software ablation evidence. |
| Scaling and domain transfer | Population stressors, harder scaling, and non-finance sensor-control transfer are documented. | Not arbitrary domain generalization. |
| Backend parity | NEST/Brian2 parity holds for selected fixed-pattern conditions. | Not universal backend equivalence. |
| PyNN/SpiNNaker hardware | Minimal and repaired task capsules run on real SpiNNaker with real spike readback and zero synthetic fallback. | Chunked/host-assisted capsule evidence. |
| External baselines | CRA has bounded hard/adaptive advantage regimes and documented best-baseline losses. | Not universal superiority. |
| Lifecycle and motifs | Lifecycle and motif structure pass targeted software controls and shams. | Not hardware lifecycle. |
| Host-side capability mechanisms | Memory, replay, prediction, routing, temporal coding, and self-evaluation pass selected gates. | Mostly software-only unless migrated. |
| Native custom runtime | Four-core MCPL tasks, keyed memory, routing/composition, predictive binding, and confidence-gated learning pass bounded hardware gates. | Single-chip bounded task capsules, not full runtime autonomy. |

## Hardware Runtime Progression

The hardware program has two lines of evidence.

First, the PyNN/SpiNNaker path established that bounded CRA capsules can execute
on real SpiNNaker hardware with real spike readback and zero synthetic fallback.
This includes the Tier 4.13 hardware capsule, Tier 4.15 repeatability, repaired
Tier 4.16 delayed-cue and hard-switch transfer, and Tier 4.18 chunked runtime
characterization.

Second, the custom runtime path migrates selected state and learning mechanisms
into native SpiNNaker C code. This line includes:

| Tier range | Result |
| --- | --- |
| 4.22i-4.22x | Custom runtime build/load/roundtrip, learning micro-loops, decoupled state, and compact v2 bridge smoke tests. |
| 4.23-4.24 | Continuous runtime parity and resource/build-size characterization. |
| 4.25-4.26 | Two-core and four-core state/learning split hardware passes. |
| 4.27-4.28 | MCPL migration, harder native task capsules, and native task baseline v0.2. |
| 4.29a | Native keyed-memory overcapacity gate, three-seed hardware pass. |
| 4.29b | Native routing/composition gate, three-seed hardware pass. |
| 4.29c | Native predictive binding bridge, three-seed hardware pass. |
| 4.29d | Native self-evaluation / confidence-gated learning bridge, three-seed hardware pass. |
| 4.29e | Native host-scheduled replay/consolidation bridge, three-seed hardware pass after `cra_429p` repair. |

The current custom runtime remains a research runtime, not a production runtime.
Its purpose is to make mechanism transfer testable under SpiNNaker constraints.

## Baselines And Fairness

CRA is compared against simple and stronger external learners where appropriate.
The comparison program includes random/sign persistence, online perceptron,
online logistic regression, reservoir/echo-state style baselines, small recurrent
baselines, STDP-only controls, and evolutionary population controls in selected
suites.

The project does not require CRA to win every task. A useful result can be:

- CRA wins under delay, noise, switching, recurrence, or adaptation pressure.
- CRA loses on easy tasks where simpler learners are sufficient.
- A proposed mechanism fails to separate from shams and is parked.
- A hardware bridge passes a transfer gate without making a speedup claim.

This distinction is central to the paper strategy. The strongest claim is not
that CRA is universally superior. The stronger defensible claim is that its
mechanisms can be isolated, ablated, transferred, and evaluated under conditions
where local learning and neuromorphic constraints matter.

## Current Limitations

The current repository does not yet prove:

1. Full multi-chip scaling.
2. Fully autonomous on-chip execution of all promoted software mechanisms.
3. Native hardware lifecycle, reproduction, and apoptosis.
4. Hardware replay buffers or biological sleep.
5. General reward-free concept learning.
6. Broad real-world task competence.
7. Universal superiority over external baselines.
8. Language, long-horizon planning, or general intelligence.
9. Production readiness.

These limitations are not incidental. They define the remaining roadmap and keep
paper claims bounded.

## Roadmap To Paper Readiness

The forward plan is maintained in `docs/MASTER_EXECUTION_PLAN.md` and
`docs/PAPER_READINESS_ROADMAP.md`. The high-level sequence is:

1. Run Tier 4.30-readiness audit to decide how lifecycle-native work layers on
   v2.2 software evidence and the existing native mechanism bridge.
2. Define and run Tier 4.30 lifecycle-native static-pool gates with lineage,
   masks, trophic state, sham controls, and compact hardware readback.
3. Define any future native temporal-state migration separately; v2.2 does not
   by itself prove on-chip temporal dynamics.
4. Add resource, timing, and scalability characterization before larger hardware
   claims.
5. Re-run final software and hardware matrices against fair baselines.
6. Produce a reproduction package with environment locks, artifact manifests,
   exact commands, and claim-boundary tables.
7. Write the paper from the evidence level actually earned.

## Conclusion

CRA is best understood as a controlled research system for neuromorphic local
learning and hardware mechanism transfer. Its value is not a single benchmark
number. Its value is the combination of explicit mechanisms, controlled
ablation/sham tests, external baselines, reproducible evidence artifacts, frozen
baselines, and real SpiNNaker execution.

The current evidence is substantial but bounded. CRA has demonstrated multiple
software mechanisms and several native SpiNNaker mechanism bridges. The remaining
work is to continue migrating mechanisms to hardware, characterize scalability,
strengthen external comparisons, and preserve the same audit discipline through
final paper lock.
