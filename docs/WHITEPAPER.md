# Coral Reef Architecture Whitepaper

## Status

This whitepaper summarizes the implementation and evidence currently present in
this repository. It is an internal technical whitepaper, not a peer-reviewed
paper. Claims are bounded by the canonical evidence registry in
`controlled_test_output/STUDY_REGISTRY.json`.

## Executive Summary

The Coral Reef Architecture (CRA) is a neuromorphic learning architecture built
around a colony metaphor. Instead of training one monolithic differentiable model
with global error gradients, CRA uses many small neural agents, called polyps,
that learn locally, compete for trophic support, and undergo lifecycle pressure.
The system is intended to test whether useful primitive learning can emerge from
biologically inspired mechanisms: local spiking dynamics, dopamine-modulated
plasticity, delayed credit assignment, energy-based survival, reproduction,
apoptosis, and graph-mediated mutual support.

The repository now contains three things that should be considered together:

1. A source implementation of the CRA organism and backend integrations.
2. A staged controlled-test suite that tests negative controls, learning proof,
   mechanism ablations, scaling, domain transfer, backend parity, and hardware
   execution.
3. A registry-driven evidence system that identifies canonical result bundles and
   prevents old probes or failed attempts from being cited as current evidence.

As of the current registry, all canonical evidence entries pass. The strongest
hardware-learning result is the Tier 4.13 minimal SpiNNaker hardware capsule
plus the Tier 4.15 three-seed repeat of that same capsule. Together, those
results support a narrow but important claim: a minimal fixed-pattern CRA
capsule can execute through `pyNN.spiNNaker` with real spike readback, zero
synthetic fallback, learning metrics above threshold, and repeatability across
seeds `42`, `43`, and `44`. Tier 4.14 separately characterizes where the
Tier 4.13 wall-clock runtime went. Tier 5.4 separately confirms the leading
software delayed-credit fix, `delayed_lr_0_20`, across 960 and 1500 steps before
harder hardware migration. The first Tier 4.16 hardware attempt executed cleanly
but failed the delayed-cue learning criterion; local NEST/Brian2 replay
reproduced the same seed pattern, so the blocker was the delayed-cue
task/config/metric rather than the hardware execution path itself. Local repair
diagnostics showed that a 1200-step delayed-cue probe passes in NEST and Brian2
with 37 tail events while preserving `delayed_lr_0_20`. Tier 4.17b then locally
validated the chunked-runtime mechanics needed before rerunning that longer
hardware probe: scheduled input, per-step binned spike readback, and host replay
match the step reference on NEST/Brian2 with exact spike-bin and prediction
parity. The repaired Tier 4.16a hardware repeat now passes for `delayed_cue`,
seeds `42`, `43`, and `44`, 1200 steps, `chunked + host`, and
`chunk_size_steps=25`: 48 hardware `sim.run` calls per seed, minimum 94976 real
spikes, zero fallback/failures, mean tail accuracy 1.0, mean tail
prediction-target correlation 0.9999999999999997, and mean all accuracy
0.9933333333333333. The subsequent Tier 4.16b hard-switch hardware run also
completed cleanly, but failed the learning gate on the worst seed. The latest
aligned Tier 4.16b bridge-repair diagnostics fix the local host-replay ordering
and stale task defaults, pass on NEST and Brian2, and the repaired three-seed
hard-switch hardware repeat now passes. This is a repaired delayed-cue and
hard-switch hardware-transfer pass sequence under chunked host replay, not
hardware scaling, native on-chip learning, or external-baseline superiority.

The result does not yet support a full hardware-scaling claim. It does not prove
that the full dynamic lifecycle, all population-scaling tests, or the
experimental C runtime are production-ready on hardware. Those remain future
work.

## Research Motivation

Most machine-learning systems optimize a global objective by propagating error
through a static parameter graph. Biological systems do something different:
neurons and microcircuits learn through local plasticity, receive modulatory
signals, compete for metabolic resources, and survive inside changing ecological
constraints. CRA explores whether those biological design principles can be
turned into a computational substrate with measurable primitive learning.

The motivating question is:

```text
Can a population of local spiking agents learn, adapt, and transfer across tasks
without relying on global backpropagation as the organizing principle?
```

CRA does not attempt to replace modern deep learning in this repository. It tests
a smaller, sharper claim: whether a biologically structured neuromorphic
primitive can pass controls that distinguish real learning from artifacts.

## Core Architecture

A CRA organism consists of these conceptual layers:

| Layer | Role | Main implementation |
| --- | --- | --- |
| Configuration | Single source of parameters | `coral_reef_spinnaker/config.py` |
| Neural substrate | Polyps, populations, STDP, backend projections | `polyp_state.py`, `polyp_population.py`, `polyp_plasticity.py`, `reef_network.py` |
| Energy economy | Trophic health, maternal reserve, sensory/outcome/retrograde support | `energy_manager.py` |
| Learning | Dopamine, RPE, STDP updates, delayed horizons, readout | `learning_manager.py` |
| Lifecycle | Birth, death, lineage, juvenile/adult state | `lifecycle.py` |
| Task interface | Domain-neutral outcomes and adapters | `signals.py`, `task_adapter.py` |
| Finance adapter | Paper trader and signed-return bridge | `trading_bridge.py` |
| Orchestration | Main training loop and backend calls | `organism.py` |
| Backends | Mock, NEST, Brian2, SpiNNaker PyNN | `backend_factory.py`, `mock_simulator.py`, `spinnaker_compat.py` |
| Evidence | Controlled experiments and registry | `experiments/`, `controlled_test_output/STUDY_REGISTRY.json` |

## Biological Design Principles

CRA is organized around several biological analogies. These analogies are not
claimed to be literal neuroscience models. They are engineering constraints that
shape the learning system.

| Principle | CRA interpretation |
| --- | --- |
| Local plasticity | Synaptic changes are driven by local spike timing and modulatory signals. |
| Dopamine modulation | Reward prediction error gates or scales plasticity. |
| Trophic economy | Polyps survive by earning energy from sensory information, outcomes, and retrograde support. |
| Delayed credit | Pending consequence records mature after a horizon and then shape learning. |
| Lifecycle pressure | Polyps can be protected, become autonomous, reproduce, or die. |
| Population ecology | Useful specialists persist; weak or harmful agents lose support. |
| Domain neutrality | The core organism should operate on signed task consequences, not only trading fields. |

## SNN Literature Alignment

SNN reviewers commonly evaluate systems across more than task accuracy. The
important dimensions include neuron model choice, spike encoding, temporal
information processing, synaptic learning rules, circuit motifs, unsupervised
organization, strong SNN/ANN-to-SNN baselines, and neuromorphic deployment
constraints.

CRA already has evidence in part of that space:

```text
local learning without global backprop
reward-modulated plasticity and delayed credit
recurrent/adaptive dynamics
lateral inhibition / WTA-style readout behavior
domain transfer and backend parity
real SpiNNaker execution with no synthetic fallback
```

Tier 5.15 now supplies the first explicit software temporal-code diagnostic:
latency, burst, and temporal-interval encodings carry task-relevant information
on fixed_pattern, delayed_cue, and sensor_control, and time-shuffle/rate-only
controls lose on the successful temporal cells. Tier 5.16 now supplies the
first NEST neuron-parameter sensitivity diagnostic: 66/66 runs across 11 LIF
variants remain functional with zero fallback/failure counters, zero parameter
propagation failures, zero collapse rows, and monotonic direct LIF response
probes. Tier 5.17d now supplies bounded software predictive-binding evidence
after the broader Tier 5.17/Tier 5.17c representation attempts failed their
promotion gates, and Tier 5.17e freezes that bounded result as v2.0 after
compact guardrails stay green. The remaining SNN-native review targets stay on
the roadmap:

```text
circuit-motif ablations
broader unsupervised representation / concept formation
triplet/richer eligibility-trace comparisons
surrogate-gradient and ANN-to-SNN baselines where fair
sample-efficiency metrics across hard/adaptive tasks
```

Tier 5.15 is still software-only and noncanonical; hardware/on-chip temporal
coding, neuron robustness, general reward-free concept learning, and
hardware/on-chip representation learning require their own later tiers before
the paper can make those stronger claims.

## Implementation Overview

### Configuration

`ReefConfig` aggregates energy, lifecycle, learning, network, SpiNNaker, and
measurement settings. `config_adapters.py` keeps legacy consumers aligned with
that single source of truth. This matters because earlier drift in BDNF constants,
SDRAM estimates, neuron thresholds, dopamine gain, and horizon constants would
make experimental interpretation unreliable.

### Polyps and Reef Graph

Polyps are represented by state objects and populations. The reef graph holds
inter-polyp edges with motif types and backend projections. The implementation
supports host-side graph state and backend-specific projection setup. The
hardware-aware path respects SpiNNaker constraints such as atoms-per-core limits,
weight clipping, and fixed-point compatibility.

### Learning Manager

The learning manager is the canonical dopamine producer inside the organism
training path. It computes signed reward information, maintains delayed horizon
records, produces learning results, and updates local plasticity/readout state.
This choice prevents double-counting dopamine between task adapters and learning
results. Task bridges may expose diagnostic reward surfaces, but the canonical
organism path delivers `learning_result.raw_dopamine` to backend STDP.

### Energy and Lifecycle

The energy manager computes trophic support from sensory information, outcomes,
and retrograde support. Lifecycle code turns energy and internal state into
birth/death/lineage events. A key integrity fix preserves lifecycle-created
`polyp_id` and `lineage_id` when allocating population slots, which keeps the
biological lineage story consistent with the hardware population representation.

### Task Adapters

The system includes a trading bridge and domain-neutral task adapters. Tier 4.11
uses a non-finance `sensor_control` adapter to test whether the organism is a
substrate-level learner rather than merely a trading-shaped learner. The current
organism still has finance-heavy historical seams, but the controlled evidence
shows the core machinery can run without the trading bridge.

### Backend Integrations

The project currently supports:

| Backend | Current role |
| --- | --- |
| MockSimulator | Fast deterministic smoke/negative-control backend. |
| NEST | Main controlled learning and ablation backend. |
| Brian2 | Backend parity target for fixed-pattern learning. |
| pyNN.spiNNaker | SpiNNaker prep and minimal hardware capsule execution. |
| Custom C runtime | Experimental sidecar for dynamic birth/death research. |

The Python/PyNN path is the mainline research implementation. The custom C
runtime is not the source of current learning claims.

## Evidence Program

The validation plan is sequential. If a tier fails, the project should stop,
debug, rerun from the failing tier, and refresh the registry. The expanded suite
contains 27 tracked evidence entries:

```text
3 sanity + 3 learning + 3 architecture + 1 baseline scaling
+ 1 hard-scaling addendum + 1 domain transfer + 1 backend parity
+ 1 hardware capsule + 1 runtime characterization + 1 hardware repeat
+ 1 external-baseline comparison + 1 learning-curve sweep
+ 1 failure-analysis diagnostic + 1 delayed-credit confirmation
+ 1 repaired delayed-cue hardware repeat + 1 repaired hard-switch hardware repeat
+ 1 v0.7 chunked hardware runtime baseline + 1 expanded baseline suite
+ 1 tuned-baseline fairness audit + 1 compact regression guardrail
+ 1 software lifecycle/self-scaling benchmark + 1 lifecycle sham-control suite
+ 1 predictive task-pressure validation + 1 predictive-context sham repair
+ 1 predictive-context compact-regression gate
+ 1 circuit-motif causality suite
+ 1 four-core distributed context/route/memory/learning smoke
= 27 tracked entries including reviewer-defense/guardrail bundles
```

The registry evidence is grouped into 26 canonical bundles. The broader ladder below also includes baseline-frozen mechanism evidence and selected diagnostics so the narrative does not hide non-registry proof gates or failures.

| Bundle / diagnostic | Evidence category | Current claim |
| --- | --- | --- |
| Tier 1 sanity | Core tests 1-3 | Negative controls do not fake learning. |
| Tier 2 learning | Core tests 4-6 | Fixed pattern, delayed reward, and switch tasks learn. |
| Tier 3 architecture | Core tests 7-9 | Dopamine, plasticity, and trophic selection matter. |
| Tier 4.10 scaling | Core test 10 | Population sizes N=4..64 remain stable on baseline stressor. |
| Tier 4.10b hard scaling | Addendum | Harder scaling shows value in correlation/recovery/variance. |
| Tier 4.11 domain transfer | Core test 11 | Same core transfers to non-finance sensor_control adapter. |
| Tier 4.12 backend parity | Core test 12 | NEST/Brian2 parity holds with zero synthetic fallback. |
| Tier 4.13 hardware capsule | Hardware addendum | Minimal SpiNNaker hardware capsule passes. |
| Tier 4.14 runtime characterization | Post-v0.1 addendum | Hardware runtime/provenance overhead is characterized. |
| Tier 4.15 hardware repeat | Hardware repeatability addendum | Minimal SpiNNaker hardware capsule repeats across three seeds. |
| Tier 5.1 external baselines | Post-hardware comparison | CRA has a hard-task median-baseline edge, while simpler learners win the easy delayed-cue task. |
| Tier 5.2 learning curves | Post-v0.2 comparison addendum | CRA's Tier 5.1 edge does not strengthen at 1500 steps under the tested settings. |
| Tier 5.3 failure analysis | Post-Tier-5.2 diagnostic | Stronger delayed credit is the leading candidate fix; hard switching still trails the best external baseline. |
| Tier 5.4 delayed-credit confirmation | Post-Tier-5.3 confirmation | `delayed_lr_0_20` confirms versus current CRA and external medians at 960 and 1500 steps; hard switching still trails the best external baseline. |
| Tier 4.16a delayed-cue hardware repeat | Hardware transfer addendum | Repaired delayed_cue transfers across seeds 42, 43, and 44 using chunked host replay. |
| Tier 4.16b hard-switch hardware repeat | Hardware transfer addendum | Repaired hard_noisy_switching transfers across seeds 42, 43, and 44 using chunked host replay. |
| Tier 4.18a chunked runtime baseline | Runtime/resource addendum | Chunk sizes 10, 25, and 50 preserve observed v0.7 task metrics on seed 42; chunk 50 is the fastest viable default. |
| Tier 4.20a v2.1 hardware-transfer audit | Engineering transfer audit | v2.1 mechanisms are classified by chunked-host readiness versus future hybrid/custom-C/on-chip blockers. This is not hardware evidence; it plans the next one-seed v2.1 chunked hardware probe without macro eligibility. |
| Tier 4.20b v2.1 one-seed hardware probe | Bridge/transport hardware pass | Returned EBRAINS artifacts passed for seed 42, delayed_cue plus hard_noisy_switching, 1200 steps, N=8, chunk 50, macro disabled, real pyNN.spiNNaker execution, zero fallback, zero sim.run/readback failures, and nonzero spike readback. This is not native/on-chip v2.1 mechanism evidence. |
| Tier 5.5 expanded baselines | Software comparison addendum | Locked CRA v0.8 completes the 1,800-run expanded baseline matrix, showing robust/non-dominated hard-adaptive regimes while documenting ties and best-baseline losses. |
| Tier 5.6 tuned-baseline fairness audit | Reviewer-defense addendum | Locked CRA survives a 990-run external-baseline retuning audit with four surviving target regimes, while still documenting no universal or best-baseline superiority. |
| Tier 5.7 compact regression | Guardrail addendum | Promoted delayed-credit setting still passes compact controls, positive learning, architecture ablations, and delayed_cue/hard_noisy_switching smokes before Tier 6 lifecycle work. |
| Tier 5.9c macro-eligibility v2.1 recheck | Failed/parked mechanism diagnostic | The full v2.1 guardrail passes, but residual macro eligibility still fails trace-ablation specificity because normal, shuffled, zero-trace, and no-macro paths remain indistinguishable. Macro eligibility remains parked and is not hardware/custom-C eligible. |
| Tier 5.10g keyed context memory | Baseline-frozen memory addendum | Bounded keyed/multi-slot host memory repairs the single-slot interference failure and freezes v1.6, but is not native memory or replay. |
| Tier 5.11a replay need test | Noncanonical memory diagnostic | v1.6 no-replay fails silent-reentry tails while unbounded/oracle controls solve them, justifying replay/consolidation testing. |
| Tier 5.11b prioritized replay intervention | Failed/parked mechanism diagnostic | Prioritized replay repairs the silent-reentry failure, but shuffled replay comes too close on partial-key reentry, so replay is not promoted. |
| Tier 5.11c replay sham separation | Failed/parked mechanism diagnostic | Sharper shams still block the narrower priority-specific replay claim because shuffled-order replay remains too close. |
| Tier 5.11d generic replay/consolidation | Baseline-frozen memory addendum | Correct-binding replay/consolidation repairs the silent-reentry failure, separates from wrong-memory/no-write controls, preserves compact regression, and freezes v1.7; priority weighting and hardware replay remain unproven. |
| Tier 5.12a predictive task-pressure validation | Predictive task diagnostic | Predictive-pressure streams defeat current-reflex, sign-persistence, wrong-horizon, and shuffled-target shortcuts while causal predictive-memory controls solve them; authorizes Tier 5.12b but is not world-model evidence. |
| Tier 5.12b internal predictive-context diagnostic | Failed mechanism diagnostic | Internal predictive context matches the external scaffold but fails because wrong-sign context is a learnable alternate code and the first sham contract is too blunt. |
| Tier 5.12c predictive-context sham repair | Predictive mechanism diagnostic | Host-side visible predictive-context binding passes against v1.7, shuffled/permuted/no-write shams, shortcut controls, and selected external baselines. |
| Tier 5.12d predictive-context compact regression | Predictive promotion guardrail | Six child checks pass and freeze v1.8 as bounded host-side visible predictive-context software evidence; not hidden inference, world modeling, language, planning, hardware prediction, hardware scaling, native on-chip learning, compositionality, or external-baseline superiority. |
| Tier 5.13 compositional skill reuse | Compositionality diagnostic | Explicit host-side reusable-module composition solves held-out skill combinations with 1.0 first-heldout/total heldout accuracy across three tasks, while raw v1.8, combo memorization, module shams, and selected standard baselines fail to close the gap; not native CRA composition or hardware evidence. |
| Tier 5.13b module routing/contextual gating | Routing diagnostic | Explicit host-side contextual routing selects the correct module before feedback under delayed-context, distractor, and reentry pressure; raw v1.8, the CRA router-input bridge, routing shams, and selected baselines do not close the first-heldout gap. |
| Tier 5.13c internal composition/routing | Baseline-frozen internal mechanism gate | Internal host-side CRA composition/routing completes 243/243 cells with zero leakage, 1.0 minimum held-out composition/routing accuracy and router accuracy, separation from internal shams, and fresh full compact regression; freezes v1.9 as host-side software composition/routing evidence, not hardware/on-chip routing, language, planning, AGI, or external-baseline superiority. |
| Tier 5.14 working memory/context binding | Noncanonical working-memory diagnostic | Frozen v1.9 passes context/cue-memory and delayed module-state routing pressure: context-memory and routing candidates reach 1.0 task accuracy, reset/shuffle/no-write/random shams lose, and selected sequence baselines do not close the gap; software diagnostic only, not a v2.0 freeze, hardware/on-chip working memory, language, planning, AGI, or external-baseline superiority. |
| Tier 5.15 spike encoding/temporal code | Noncanonical temporal-code diagnostic | A 540-run software matrix shows latency, burst, and temporal-interval spike codes can carry task-relevant information on fixed_pattern, delayed_cue, and sensor_control; time-shuffle and rate-only controls lose on the successful temporal cells. This is not hardware/on-chip temporal coding, not a v2.0 freeze, and not hard-switch temporal superiority. |
| Tier 5.16 neuron model / parameter sensitivity | Noncanonical NEST robustness diagnostic | A 66-run NEST matrix across threshold, membrane-tau, refractory, capacitance, and synaptic-tau LIF variants keeps all 33 task/variant cells functional with zero fallback/failure counters, zero parameter-propagation failures, zero collapse rows, and monotonic direct LIF response probes; not hardware/custom-C/on-chip neuron evidence or a v2.0 freeze. |
| Tier 5.17e predictive-binding compact regression | Baseline-frozen predictive-binding gate | v1.8 compact regression, v1.9 composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d predictive-binding guardrails all pass; freezes v2.0 as bounded host-side software predictive-binding evidence, not hardware/on-chip representation learning, broad unsupervised concept learning, world modeling, language, planning, AGI, or external-baseline superiority. |
| Tier 5.18 self-evaluation / metacognitive monitoring | Software reliability-monitoring diagnostic | A 150-run matrix over frozen v2.0 passes zero-leakage/pre-feedback monitor checks; confidence predicts primary-path errors and hazard/OOD/mismatch state, passes Brier/ECE calibration gates, and confidence-gated behavior beats v2.0 no-monitor, monitor-only, random, time-shuffled, disabled, anti-confidence, and best non-oracle controls. Tier 5.18c then freezes v2.1 after the full v2.0 compact gate and Tier 5.18 guardrail pass. This is not consciousness, self-awareness, hardware evidence, language, planning, AGI, or external-baseline superiority. |
| Tier 6.1 lifecycle/self-scaling | Organism/lifecycle addendum | Lifecycle-enabled CRA expands with clean lineage and shows hard_noisy_switching advantage regimes versus same-initial fixed-N controls; event analysis is cleavage-dominated and not full adult turnover. |
| Tier 6.3 lifecycle sham controls | Organism reviewer-defense addendum | Intact lifecycle beats fixed max-pool, event-count replay, no-trophic, no-dopamine, and no-plasticity shams on hard_noisy_switching with clean actual-run lineage and detected lineage-ID shuffle corruption. |
| Tier 6.4 circuit motif causality | Organism/circuit reviewer-defense addendum | Seeded motif-diverse CRA logs pre-reward motif activity; motif ablations cause predicted losses, while motif-label shuffle and random/monolithic controls do not explain the adaptive effect. |

## Key Results

### Tier 1: Negative Controls

Tier 1 tests zero signal, shuffled labels, and repeated random seeds. Passing
Tier 1 means the system does not appear to learn when there is no usable signal
or labels are broken. This does not prove positive learning. It removes common
failure modes: leakage, accidental reward shaping, lucky seeds, or metric
artifacts.

### Tier 2: Learning Proof

Tier 2 tests fixed pattern learning, delayed reward learning, and nonstationary
adaptation. Passing Tier 2 supports the claim that the organism can learn simple
predictable structure, assign delayed credit, and adapt after a rule switch.

### Tier 3: Architecture Ablations

Tier 3 compares intact organisms against targeted ablations. The canonical
bundle reports that dopamine ablation, plasticity ablation, and trophic-selection
ablation each change behavior in the expected direction. This matters because it
separates named architecture mechanisms from decorative biological language.

### Tier 4.10 and 4.10b: Scaling

Baseline population scaling passes as stability, not strong scaling advantage.
The baseline task saturates: all population sizes can solve it. Tier 4.10b makes
the task harder with noise, delayed reward, frequent switches, and multiple
population sizes. The hard-scaling result does not show a dramatic raw-accuracy
jump, but passes through stability plus non-accuracy scaling signals such as
correlation, recovery, and variance.

### Tier 4.11: Domain Transfer

Tier 4.11 tests finance/signed-return and non-finance sensor-control tasks under
the same CRA core and NEST backend. The result supports the claim that CRA is not
only trading-shaped. The boundary is important: this is domain transfer across
controlled adapters, not proof of arbitrary domain generalization.

### Tier 4.12: Backend Parity

Tier 4.12 compares NEST and Brian2 on the same fixed-pattern task. Synthetic
fallbacks, `sim.run` failures, and summary-read failures remain zero. This
supports local backend portability for the controlled fixed-pattern result.

Tier 4.12 also includes SpiNNaker PyNN prep, but that item is not a hardware
learning claim.

### Tier 4.13: SpiNNaker Hardware Capsule

Tier 4.13 is the first real hardware-capsule claim. The canonical pass has:

| Metric | Value |
| --- | ---: |
| Backend | `pyNN.spiNNaker` |
| Seed | `42` |
| Population | `N=8` fixed |
| Steps | `120` |
| Synthetic fallbacks | `0` |
| `sim.run` failures | `0` |
| Summary-read failures | `0` |
| Total spike readback | `283903` |
| Overall strict accuracy | `0.9747899159663865` |
| Tail strict accuracy | `1.0` |
| Overall prediction-target correlation | `0.8917325875598855` |
| Tail prediction-target correlation | `0.9999839178111984` |
| Runtime seconds | `858.6201063019689` |

This supports the claim that the minimal fixed-pattern capsule executes on real
SpiNNaker hardware and preserves expected behavior. It does not prove full
hardware scaling or full CRA hardware deployment.

### Tier 4.14: Hardware Runtime Characterization

Tier 4.14 characterizes the canonical Tier 4.13 pass using its result manifest,
per-step time series, and sPyNNaker `global_provenance.sqlite3` timers. It is
not a new learning result. It answers the runtime question raised by the first
hardware pass.

| Metric | Value |
| --- | ---: |
| Source bundle | `tier4_13_20260427_011912_hardware_pass` |
| Runtime seconds | `858.6201063019689` |
| Simulated biological seconds | `6.0` |
| Wall-to-simulated-time ratio | `143.10335105032814` |
| Mean wall time per 50 ms step | `7.155167552516407` |
| Dominant category | `Running Stage` |
| Dominant category seconds | `637.741974` |
| Dominant algorithm | `Application runner` |
| Application-runner seconds | `87.375508` |
| Application-runner seconds per step | `0.7281292333333333` |
| Buffer-extractor seconds | `32.786108999999996` |

The interpretation is direct: the hardware result is real, but the current
closed-loop host/PyNN/hardware harness pays heavy repeated orchestration and
readback cost for short 50 ms runs. That overhead is valid empirical engineering
data for the study. It should not be framed as evidence that the neural
substrate itself is slow.

### Tier 4.15: SpiNNaker Hardware Multi-Seed Repeat

Tier 4.15 repeats the same minimal fixed-pattern hardware capsule across seeds
`42`, `43`, and `44`. It is repeatability evidence, not a harder task and not
hardware scaling.

| Metric | Value |
| --- | ---: |
| Backend | `pyNN.spiNNaker` |
| Seeds | `42`, `43`, `44` |
| Population | `N=8` fixed |
| Steps | `120` |
| Synthetic fallbacks | `0` |
| `sim.run` failures | `0` |
| Summary-read failures | `0` |
| Total spike readback min / mean / max | `284154 / 291103.6666666667 / 295521` |
| Overall strict accuracy mean / min | `0.9747899159663865 / 0.9747899159663865` |
| Tail strict accuracy mean / min | `1.0 / 1.0` |
| Prediction-target correlation mean | `0.915035900980274` |
| Tail prediction-target correlation mean / min | `0.9999901037892215 / 0.9999839178111984` |
| Runtime seconds min / mean / max | `865.3982471250929 / 873.6344163606409 / 884.8983335739467` |

This upgrades the hardware claim from "the minimal capsule passed once" to "the
minimal capsule passed repeatably across three seeds." It still does not prove
harder hardware tasks, population scaling on hardware, dynamic lifecycle
deployment on hardware, or a full CRA hardware migration.

### Tier 5.1: External Baselines

Tier 5.1 compares CRA against simpler learners under identical online task
streams. The external set includes random/sign persistence, online perceptron,
online logistic regression, echo-state network, small GRU readout, STDP-only
SNN, and a simple evolutionary population. Every model predicts before seeing
the label, and delayed tasks only update when feedback matures.

| Metric | Value |
| --- | ---: |
| CRA backend | `NEST` |
| Seeds | `42`, `43`, `44` |
| Tasks | `fixed_pattern`, `delayed_cue`, `sensor_control`, `hard_noisy_switching` |
| Matrix completion | `108 / 108` runs |
| Hard advantage tasks | `sensor_control`, `hard_noisy_switching` |
| Fixed-pattern CRA tail / best external tail | `1.0 / 1.0` |
| Delayed-cue CRA tail / best external tail | `0.4761904761904762 / 1.0` |
| Sensor-control CRA tail / external median tail | `1.0 / 0.8166666666666667` |
| Hard-switch CRA tail / external median tail | `0.5833333333333334 / 0.5416666666666666` |
| Hard-switch CRA recovery / external median recovery | `15.066666666666666 / 32.33333333333333` steps |

This is not a "CRA wins everything" result. It is more useful than that. The
delayed-cue task is easy for simple online learners once feedback matures, and
they beat CRA clearly. CRA's comparative value appears on the non-finance
sensor_control task and the harder noisy switching task, where it improves over
the external median and recovers faster after switches. The claim is therefore
specific: CRA has a defensible advantage under some adaptive/nonstationary
conditions, not universal superiority over simpler baselines.

### Tier 5.2: Learning Curve / Run-Length Sweep

Tier 5.2 repeats the Tier 5.1 comparison across 120, 240, 480, 960, and 1500
steps on `sensor_control`, `hard_noisy_switching`, and `delayed_cue`. The full
matrix completed: `405 / 405` runs across three seeds, nine models, three tasks,
and five run lengths.

| Metric | Value |
| --- | ---: |
| CRA backend | `NEST` |
| Run lengths | `120`, `240`, `480`, `960`, `1500` |
| Matrix completion | `405 / 405` runs |
| Final advantage tasks at 1500 steps | `0` |
| Delayed-cue CRA final tail / best external tail | `0.7246376811594203 / 1.0` |
| Sensor-control CRA final tail / best external tail | `1.0 / 1.0` |
| Hard-switch CRA final tail / best external tail | `0.4465408805031446 / 0.5534591194968553` |

This is the most important post-baseline correction in the repo. The Tier 5.1
edge is real at the 240-step condition, but it does not become stronger as the
stream gets longer under this configuration. `sensor_control` saturates for both
CRA and simpler baselines, `delayed_cue` remains externally dominated, and
`hard_noisy_switching` becomes mixed/negative for CRA at the 1500-step horizon.
That does not invalidate the earlier comparison; it narrows the claim and points
the next work toward either CRA tuning, sharper hard-task probes, or a better
definition of the niche where the ecology actually helps.

### Tier 5.3: CRA Failure Analysis / Learning Dynamics Debug

Tier 5.3 stops before more hardware and asks why the long-run comparative edge
fades. It runs CRA-only variants at 960 steps on `delayed_cue` and
`hard_noisy_switching`, using Tier 5.2 external baselines as references. The
full matrix completed: `78 / 78` runs across three seeds, two tasks, and 13
variants.

| Metric | Value |
| --- | ---: |
| CRA backend | `NEST` |
| Steps | `960` |
| Seeds | `42`, `43`, `44` |
| Matrix completion | `78 / 78` runs |
| Delayed-cue best variant | `delayed_lr_0_20` |
| Delayed-cue tail current / tuned | `0.5555555555555556 / 1.0` |
| Hard-switch best tail variant | `delayed_lr_0_20` |
| Hard-switch tail current / tuned | `0.45098039215686275 / 0.5392156862745098` |
| Hard-switch tuned delta vs external median | `+0.06372549019607848` |
| Hard-switch tuned delta vs best external | `-0.0490196078431373` |
| Best switch-recovery variant | `horizon_3` at `24.34285714285714` steps |

The diagnosis is useful but bounded. Stronger delayed credit is the leading
candidate fix: `delayed_lr_0_20` fully restores delayed_cue at 960 steps and
improves hard noisy switching above the external median. But it does not yet
beat the best hard-switching external baseline, and it has not been confirmed at
the 1500-step horizon. Therefore Tier 5.3 supports targeted software
confirmation before a harder SpiNNaker capsule, not immediate hardware
migration.

### Tier 5.4: Delayed-Credit Confirmation

Tier 5.4 runs only the candidate fix from Tier 5.3, `cra_delayed_lr_0_20`,
against current CRA and the same external baselines. It uses `delayed_cue` and
`hard_noisy_switching`, run lengths `960` and `1500`, and seeds `42`, `43`, and
`44`. The full matrix completed: `120 / 120` runs.

| Metric | Value |
| --- | ---: |
| CRA backend | `NEST` |
| Run lengths | `960`, `1500` |
| Seeds | `42`, `43`, `44` |
| Matrix completion | `120 / 120` runs |
| Candidate | `cra_delayed_lr_0_20` |
| Delayed-cue candidate tail at 960 / 1500 | `1.0 / 1.0` |
| Delayed-cue minimum delta vs current CRA | `+0.2753623188405797` |
| Hard-switch candidate tail at 960 / 1500 | `0.5392156862745098 / 0.5157232704402516` |
| Hard-switch minimum delta vs current CRA | `+0.06918238993710696` |
| Hard-switch minimum delta vs external median | `+0.01572327044025157` |
| Hard-switch minimum delta vs best external | `-0.0490196078431373` |
| Maximum candidate seed standard deviation | `0.089854425391291` |

This confirms the delayed-credit fix versus the predeclared criteria: delayed
cue stays at 1.0 tail accuracy, hard noisy switching beats the external median
at both lengths, there is no regression versus current CRA, and variance across
seeds is acceptable. It does not authorize a hard-switching superiority claim,
because the best external baseline still wins that task. It does authorize
designing Tier 4.16 as a harder SpiNNaker capsule using `delayed_lr_0_20`.

## Hardware Engineering Notes

Two hardware blockers were resolved before the Tier 4.13 pass:

1. sPyNNaker neuromodulation row limit: a single dopamine source row attempted to
   fan out to 256 target atoms, exceeding a 255-synapse implementation cap. The
   fix shards neuromodulation across source neurons.
2. NumPy 2 and sPyNNaker integer casting: neuromodulation flags and hardware word
   byte views could overflow scalar `uint8` paths. The fix applies narrow runtime
   compatibility patches for neuromodulation flags and spinnman memory-write
   behavior.

The hardware run has significant wall-clock overhead relative to biological
simulation time. That overhead is a measurement target, not a contradiction. It
reflects setup, graph generation, data loading, buffer extraction, JobManager
execution, and repeated short-run synchronization. Future hardware scaling work
should batch longer runs and reduce host/device round trips.

Tier 4.17b is the first local batching gate. It compares a one-step-per-run
reference against chunked PyNN runs with `StepCurrentSource` schedules,
per-original-step spike binning, and host delayed-credit replay. On NEST and
Brian2, chunk sizes `5`, `10`, `25`, and `50` match the step reference exactly
for evaluation targets, tail/all accuracy, host replay predictions, and per-bin
spike totals, while reducing `sim.run` calls by `5x` to `40x`. This validates
the local mechanics and gates the Tier 4.16 chunked hardware probe, but does
not itself prove SpiNNaker chunked hardware learning.

## Experimental C Runtime

The custom C runtime under `coral_reef_spinnaker/spinnaker_runtime/` is an
experimental sidecar. It implements a single-core dynamic LIF runtime with SDP
commands for birth, death, dopamine, spike readback, synapse creation, synapse
removal, and reset. It is useful for exploring dynamic birth/death beyond what
standard sPyNNaker fixed populations allow.

However, it is not the source of the current learning evidence. Promotion would
require real hardware build/load, command round-trip validation, spike readback,
closed-loop learning, and acceptance tests that distinguish transport failures
from model failures.

## Evidence Categories

This repo uses five evidence labels so paper claims stay clean:

- **Canonical registry evidence**: entries in `controlled_test_output/STUDY_REGISTRY.json`; these populate the paper-facing results table and require all registered criteria/artifacts to pass.
- **Baseline-frozen mechanism evidence**: a mechanism diagnostic or promotion gate that passed its predeclared gate, preserved compact regression, and has a frozen `baselines/CRA_EVIDENCE_BASELINE_vX.Y.*` lock, but is not necessarily listed as a canonical registry bundle yet.
- **Noncanonical diagnostic evidence**: useful pass/fail diagnostic work that answers a design question but does not by itself freeze a new baseline or enter the canonical paper table.
- **Failed/parked diagnostic evidence**: clean negative evidence retained to prevent p-hacking and explain why a mechanism was not promoted.
- **Hardware prepare/probe evidence**: prepared capsules and one-off probes; these are not hardware claims until returned artifacts are reviewed and explicitly promoted.

In short: `noncanonical` does not mean worthless. It means "not a formal registry/paper-table claim by itself." A frozen baseline such as v1.6, v1.7, v1.9, v2.0, or v2.1 is stronger than an ordinary diagnostic even when its source bundle remains outside the canonical registry.

## Evidence Registry and Reproducibility

The project uses a registry system to avoid confusing generated artifacts with
canonical evidence. The key files are:

| File | Purpose |
| --- | --- |
| `controlled_test_output/STUDY_REGISTRY.json` | Machine-readable canonical evidence ledger. |
| `controlled_test_output/STUDY_REGISTRY.csv` | Compact table of canonical bundles. |
| `controlled_test_output/README.md` | Generated evidence directory overview. |
| `STUDY_EVIDENCE_INDEX.md` | Source-facing evidence summary. |
| `experiments/EVIDENCE_SCHEMA.md` | Schema and citation rules. |
| `experiments/evidence_registry.py` | Registry generator and validator. |

The registry currently reports:

| Integrity item | Value |
| --- | ---: |
| Canonical evidence bundles | `26` |
| Expanded evidence entries | `28` |
| Missing expected artifacts | `0` |
| Failed canonical criteria | `0` |
| Registry status | `pass` |

## Limitations

The project has meaningful evidence, but it also has important limits:

1. Hardware evidence is still narrow N=8 capsule evidence, not full-scale
   hardware learning.
2. Tier 4.15 repeats the minimal capsule across three seeds, while Tier 4.16a
   and Tier 4.16b extend to delayed_cue and hard_noisy_switching under chunked
   host replay; none of these are hardware population-scaling or on-chip-learning
   claims.
3. Tier 4.10 baseline scaling saturates, so it proves stability more than raw
   scaling benefit.
4. Tier 4.10b hard scaling shows value in correlation/recovery/variance, not a
   large raw-accuracy jump.
5. The organism still has finance-shaped historical seams even though domain
   transfer has been demonstrated through controlled adapters.
6. The custom C runtime is host-test validated only and remains experimental.
7. SpiNNaker timing overhead is characterized for the minimal capsule, and local
   chunked parity plus harder-task hardware transfer have passed. Tier 4.18a
   now characterizes the v0.7 chunked-host path and recommends chunk `50`, but
   scaling claims still require lifecycle/hardware feasibility tests and larger
   or self-scaling populations.
8. Tier 5.1 shows that simpler online learners can dominate CRA on linearly easy
   delayed-cue tasks; CRA's comparative claim is narrower and task-dependent.
9. Tier 5.4 confirms the delayed-credit fix versus current CRA and external
   medians, but hard noisy switching still trails the best external baseline.
10. Current tasks are controlled synthetic tasks. More realistic domains will
   require additional controls.

## Roadmap

The next research steps should be staged, not blended:

1. Keep v0.6 frozen as the post-Tier-4.16a delayed-cue hardware-repeat baseline.
2. Freeze v0.7 as the post-Tier-4.16b hard-switch hardware-repeat baseline.
3. Freeze v0.8 as the post-Tier-4.18a chunked-runtime hardware baseline.
4. Tier 4.17: keep the chunked-runtime contract inventory as the runtime contract.
5. Tier 4.17b: local step-vs-chunked parity has passed; preserve it as the hardware gate.
6. Repaired 1200-step delayed-cue hardware repeat across seeds `42`, `43`, and
   `44` passed using `chunk_size_steps=25`.
7. Repaired Tier 4.16b hard_noisy_switching hardware repeat across seeds `42`, `43`, and `44` passes, superseding the earlier noncanonical hard-switch failure/probe sequence.
8. Tier 4.18a v0.7 chunked runtime baseline passed and recommends
   `chunk_size_steps=50` for the current hardware bridge.
9. Tier 5.10e internal memory-retention passed as a noncanonical software
   stressor and is frozen as v1.5 before capacity/interference or sleep/replay
   work.
10. Tier 5.10f memory capacity/interference stress completed as noncanonical
   failure evidence: the full 153-run NEST matrix completed with zero leakage
   and active memory updates, but the single-slot internal memory candidate
   failed promotion under overlapping-context and context-reentry pressure.
   This narrowed v1.5 memory to retention/distractor stress.
11. Tier 5.10g keyed context-memory repair passed as baseline-frozen software
   evidence: bounded keyed slots inside `Organism` completed 171/171 NEST runs,
   kept zero leakage across 2166 checked rows, reached `1.0` all accuracy on all
   capacity/interference tasks, matched the oracle-key scaffold, beat v1.5
   single-slot memory and slot ablations, and preserved compact regression. This
   is frozen as v1.6 before sleep/replay, routing/compositionality, or hardware
   memory work.
12. Tier 5.11a sleep/replay need diagnostic passed without implementing replay:
   the full 171-run NEST matrix completed with zero leakage, v1.6 no-replay
   minimum accuracy was `0.6086956521739131`, unbounded keyed and oracle
   scaffold controls reached `1.0`, and the predeclared decision was
   `replay_or_consolidation_needed`. This authorizes Tier 5.11b, but does not
   prove replay/consolidation or freeze v1.7.
13. Tier 5.11b prioritized replay/consolidation intervention failed the strict
   promotion gate despite strong repair signal: the corrected 162-run NEST
   matrix completed with zero feedback/replay leakage, prioritized replay
   reached `1.0` minimum all/tail accuracy and full gap closure, and
   no-consolidation wrote zero slots, but shuffled replay came too close on
   `partial_key_reentry` (`0.4444444444444444` tail edge versus a `0.5`
   threshold). Priority-specific replay remains unpromoted.
14. Tier 5.11c repeats the stricter sham-separation matrix and again blocks the
   narrower priority-weighting claim because shuffled-order replay remains too
   close (`0.40740740740740733 < 0.5`), despite strong separation from
   wrong-key, key-label-permuted, priority-only, and no-consolidation controls.
15. Tier 5.11d promotes the broader correct-binding replay/consolidation claim:
   the full 189-run NEST matrix completes with zero leakage, candidate replay
   reaches `1.0` minimum all/tail accuracy and full gap closure, separates from
   wrong-memory/no-write controls, and compact regression passes afterward. This
   freezes v1.7 as host-side software replay/consolidation evidence, not
   priority-weighting proof, native/on-chip replay, hardware memory transfer,
   routing, composition, or world modeling.
16. Tier 5.12a validates the predictive-pressure task battery: the full
   144-cell software matrix completes with zero leakage, causal predictive
   memory solves all four tasks at `1.0`, and current-reflex, sign-persistence,
   wrong-horizon, and shuffled-target controls fail under the predeclared
   ceilings. This authorized the Tier 5.12b/5.12c mechanism sequence but is not
   CRA predictive coding, world modeling, language, planning, hardware
   prediction, or a v1.8 freeze.
17. Tier 5.12b remains a failed diagnostic: the candidate path is active and
   scaffold-matching, but wrong-sign context is an alternate learnable code.
   Tier 5.12c repairs the sham contract and passes a 171-cell NEST matrix with
   zero leakage, 570 writes/active decision uses, exact scaffold match,
   minimum edge `0.8444444444444444` versus v1.7, `0.3388888888888889` versus
   shuffled/permuted/no-write shams, `0.3` versus shortcut controls, and
   `0.31666666666666665` versus the best selected external baseline. Tier
   5.12d then passes compact regression across Tier 1 controls, Tier 2
   learning, Tier 3 ablations, hard-task smokes, v1.7 replay/consolidation, and
   compact predictive-context sham separation. This freezes v1.8 as bounded
   host-side visible predictive-context binding only, not hidden-regime
   inference, full world modeling, language, planning, hardware prediction,
   hardware scaling, native on-chip learning, compositionality, or
   external-baseline superiority.
18. Tier 5.13 now passes as a bounded compositionality diagnostic: the full
   126-cell mock matrix completes with zero leakage, explicit host-side
   reusable-module composition reaches `1.0` first-heldout and total heldout
   accuracy on all three held-out composition tasks, raw v1.8 and combo
   memorization remain at `0.0` first-heldout accuracy, module
   reset/shuffle/order-shuffle shams are materially worse, and selected
   standard baselines do not close the first-heldout gap. This authorizes
   internal composition/routing work, but is not native CRA compositionality,
   hardware composition, language, planning, AGI, or a v1.9 freeze.
19. Tier 5.13b now passes as a bounded routing/contextual-gating diagnostic:
   the full 126-cell mock matrix completes with zero leakage across 11592
   checked feedback rows, explicit host-side routing reaches `1.0`
   first-heldout, heldout, and router accuracy on three delayed-context routing
   tasks, and route selection occurs before feedback 276 times. Raw v1.8 and
   the CRA router-input bridge remain at `0.0` first-heldout accuracy, routing
   shams are materially worse, and selected standard baselines do not close the
   first-heldout gap. This authorizes internal routing/gating work, but is not
   native CRA routing, successful bridge integration, hardware routing,
   language, planning, AGI, or a v1.9 freeze.
20. Tier 5.13c now passes as an internal host-side composition/routing
   promotion gate: the full 243-cell mock matrix completes with zero leakage
   across 22941 checked feedback rows, the internal path learns module/router
   state, selects routed/composed features before feedback, reaches `1.0`
   minimum held-out composition/routing and router accuracy, separates from
   internal shams, and is followed by a fresh full compact-regression pass at
   `controlled_test_output/tier5_12d_20260429_122720/`. This freezes v1.9 as
   bounded host-side software composition/routing evidence, not hardware
   evidence, native/custom-C on-chip routing, language, planning, AGI, or
   external-baseline superiority.
21. Tier 5.14 now passes as a noncanonical working-memory/context-binding
   diagnostic over frozen v1.9: both memory/context-binding and delayed
   module-state routing subsuites pass, context-memory reaches `1.0` accuracy
   on all three memory-pressure tasks with `0.5` minimum edge versus the best
   memory sham and sign persistence, and routing reaches `1.0`
   first-heldout/heldout/router accuracy on all three delayed module-state
   tasks with `1.0` edge versus routing-off CRA and `0.5` versus the best
   routing sham. This strengthens the host-side software substrate claim, but
   does not freeze v2.0 by itself and is not hardware/on-chip working memory,
   language, planning, AGI, or external-baseline superiority.
22. Tier 5.15 now passes as noncanonical software temporal-code diagnostic
   evidence: the full 540-run matrix completes with 60 sampled spike traces, 60
   encoding-metadata artifacts, 9 successful genuinely temporal cells, and 3
   successful non-finance temporal cells. Latency, burst, and temporal-interval
   codes work on fixed_pattern, delayed_cue, and sensor_control while
   time-shuffle and rate-only controls lose on the successful temporal cells.
   This supports the bounded claim that spike timing can carry task-relevant
   information in the software diagnostic. It is not SpiNNaker/custom-C on-chip
   temporal coding, not a v2.0 freeze, not hard_noisy_switching temporal
   superiority, and not neuron-model robustness.
23. Tier 4.18b expanded runtime characterization is optional only if hardware
   budget justifies chunk `100` or additional seeds.
24. Tier 5.5/Tier 5.6 expanded baseline suite and hyperparameter fairness audit:
   Tier 5.5 now passes for locked CRA v0.8 against the implemented external
   baselines with paired deltas, confidence intervals, effect sizes, runtime,
   recovery, sample-efficiency metrics, and a fairness contract. It supports
   robust/non-dominated hard-adaptive regimes but not universal or
   best-baseline superiority. Tier 5.6 now passes as the v1.0 tuned-baseline
   fairness audit: CRA remains locked, implemented external baselines receive a
   documented tuning budget, and four target regimes survive retuning. Future
   reviewer-defense baselines such as surrogate-gradient SNNs and ANN-to-SNN or
   ANN-trained baselines remain planned additions where task-compatible.
25. Tier 5.7 compact regression now passes after promoted tuning: controls,
   positive learning, core ablations, and target-task smokes survive the
   promoted delayed-credit setting. Exploratory feature tweaks still get
   focused diagnostics; candidates get targeted v0.7/v1.1 head-to-heads; only
   paper-lock candidates get full final matrices.
26. Tier 6.1 lifecycle/self-scaling now passes as the first direct software
   organism-lifecycle benchmark: fixed controls stay fixed, lifecycle cases
   produce 75 auditable new-polyp events with clean lineage, and two
   hard_noisy_switching lifecycle regimes beat same-initial fixed controls.
   Event analysis is explicit: 74 cleavage events, 1 adult birth event, and 0
   deaths. This is not full adult turnover, hardware lifecycle, or
   external-baseline superiority.
27. Tier 6.3 lifecycle sham controls now pass as the reviewer-defense gate:
   intact lifecycle beats all 10 requested performance-sham comparisons,
   including fixed max-pool capacity, event-count replay, no-trophic,
   no-dopamine, and no-plasticity controls, with clean actual-run lineage and
   detected lineage-ID shuffle corruption. This is still software-only and not
   hardware lifecycle or adult turnover.
28. Tier 5.9 through Tier 5.18 architecture mechanisms: macro eligibility,
   multi-timescale memory, sleep/replay, predictive coding, compositional
   skill reuse, module routing/gating, working memory/context binding, spike
   encoding/temporal coding, neuron-model sensitivity, and unsupervised
   representation formation, plus self-evaluation/metacognitive monitoring,
   each tested one mechanism at a time in software first. Tier 5.15 supplies
   the first software temporal-code diagnostic pass, and Tier 5.16 supplies the
   first NEST neuron-parameter sensitivity pass. Tier 5.17/Tier 5.17c failed
   broad reward-free representation gates; Tier 5.17d supplies bounded
   predictive-binding repair evidence on cross-modal and reentry binding tasks,
   and Tier 5.17e freezes that bounded repair as v2.0 after compact guardrails.
   Tier 5.18 adds software self-evaluation/metacognitive-monitoring evidence
   over v2.0, and Tier 5.18c freezes that bounded reliability-monitoring result
   as v2.1 after compact guardrails. General unsupervised concept formation,
   hardware/on-chip representation, and hardware/on-chip metacognitive
   monitoring remain pending. Tier 5.9c rechecks macro eligibility after v2.1:
   the v2.1 guardrail passes, but the residual macro trace still fails
   trace-ablation specificity, so macro eligibility remains parked and is not
   hardware/custom-C eligible.
   Tier 5.9a and Tier
   5.9b have already produced useful negative
   evidence: macro traces were active and leakage-free, but failed promotion
   because ablations did not support causal value. Tier 5.10 has also produced
   negative memory evidence: the first proxy memory-timescale candidate failed
   recurrence gates and exposed that sign-persistence solves the current return
   phases too well. Tier 5.10b then repaired the task surface: same-input /
   different-context streams now require remembered context, oracle/context
   memory solves, and wrong/reset/shuffled-memory controls fail. Tier 5.10c
   then produced the first positive memory-scaffold evidence: explicit
   host-side context binding reaches perfect accuracy on those repaired streams
   and survives reset/shuffle/wrong-memory ablations. Tier 5.10d then moved
   that capability inside `Organism`: internal host-side context memory receives
   raw observations, matches the external scaffold, beats v1.4/raw CRA and
   memory ablations, and preserves full compact regression. Tier 5.10e then
   stress-tested that internal memory under longer gaps, denser distractors,
   and hidden recurrence pressure: the internal candidate completed 153/153
   NEST runs, had zero leakage across 2448 checked feedback rows, reached
   `1.0` all accuracy on all stress tasks, matched the external scaffold, and
   kept a minimum `0.33333333333333337` all-accuracy edge versus v1.4/raw CRA,
   best memory ablation, sign persistence, and best standard baseline. This is
   still not native on-chip memory, sleep/replay, hardware memory transfer, or
   final catastrophic-forgetting evidence. Tier 5.10f then found the first
   concrete memory blocker: the same single-slot pathway completed the full
   matrix with zero leakage and matched the external single-slot scaffold, but
   failed under capacity/interference stress with minimum all accuracy `0.25`,
   minimum edge `-0.25` versus v1.4/raw CRA, and minimum edge `-0.5` versus best
   memory ablation. Tier 5.10g then repaired that measured blocker with bounded
   keyed/multi-slot memory: the candidate reached `1.0` all accuracy on all three
   stress tasks, matched oracle-key behavior, beat v1.5 single-slot memory and
   ablations, and preserved compact regression. Tier 5.11a then provided the
   need test for replay/consolidation: bounded v1.6 no-replay memory fails
   silent reentry tails while unbounded/oracle controls solve them, yielding
   `replay_or_consolidation_needed`. Tier 5.11b and Tier 5.11c then showed that
   priority-specific replay is not proven because shuffled/shuffled-order replay
   came too close. Tier 5.11d reframed the claim and passed the broader
   correct-binding replay/consolidation gate with zero leakage and compact
   regression preserved. This is v1.7 host-side replay/consolidation evidence,
   not biological sleep proof, native/on-chip replay, hardware memory transfer,
   routing, composition, or world modeling.
28. Tier 6.4 circuit motif causality now passes as software organism/circuit
   reviewer-defense evidence: seeded motif-diverse intact graphs log 1920
   motif-active steps, motif ablations produce 4/8 predicted losses, and
   random/monolithic controls do not dominate under adaptive criteria. The
   motif-label shuffle behaving identically to intact is explicitly recorded:
   structure/edge roles matter here, not labels by themselves.
29. Adult-turnover stressor if the final organism claim needs explicit adult
   birth/death replacement beyond cleavage-dominated expansion.
30. Tier 7.4/Tier 7.5/Tier 7.6 capability expansion: delayed-reward
   policy/action selection, curriculum/environment generation, and bounded
   long-horizon planning/subgoal control before broad usefulness claims.
31. Ongoing reproduction hygiene: one-command software validation, registry/table
   regeneration, environment manifest, artifact hashes, and hardware ingest
   instructions before the final reproduction capsule.
32. Hardware parity beyond fixed pattern: compare NEST/Brian2/SpiNNaker on a
   harder task with identical metrics.
33. Full CRA hardware migration plan: decide which lifecycle/energy components
   remain host-side and which move on-chip.
34. Additional non-finance, holdout, and real-ish adapters: expand beyond sensor_control.
35. Reviewer-defense package: leakage checks, mechanism/sham controls, hardware
   resource accounting, literature/novelty mapping, and independent reproduction capsule.

## Conclusion

CRA is now more than an attractive biological metaphor. The repository contains
a working implementation, a controlled validation suite, an evidence registry,
and real SpiNNaker hardware-capsule evidence for fixed-pattern,
repaired-delayed-cue, and repaired hard_noisy_switching tasks under the current
chunked-host bridge. The honest current claim is that CRA demonstrates
controlled local learning, mechanism sensitivity, backend portability,
domain-transfer evidence, narrow repeatable hardware transfer, measured hardware
orchestration cost, bounded external-baseline advantage regimes, lifecycle and
circuit-motif causality in software, and several bounded host-side mechanism
upgrades for memory, replay/consolidation, predictive context,
composition/routing, working-memory diagnostics, temporal spike coding,
neuron-parameter sensitivity, and predictive-binding pre-reward structure.

The claim remains deliberately bounded. The hard-switch hardware pass is close
to threshold and does not establish external-baseline superiority. The newer
Tier 5 mechanism evidence is software-only unless explicitly promoted to
hardware. Tier 5.17d repairs one predictive-binding failure mode, but broad
reward-free concept learning remains unproven. The next paper-readiness work is
therefore not hype expansion; it is continuing the staged mechanism ladder,
running compact promotion gates where warranted, and only migrating mechanisms
back to SpiNNaker/custom runtime after their software shams and regressions are
clean.


## Tier 5.17 Pre-Reward Representation Status

Tier 5.17 currently remains failed/non-promoted diagnostic evidence. The
software harness completed the no-label/no-reward exposure matrix with zero
non-oracle label leakage, zero reward visibility, and zero raw dopamine during
exposure, but the strict no-history-input representation scaffold failed the
predeclared probe, sham-separation, and sample-efficiency promotion gates. This
keeps reward-free representation formation as a future repair obligation rather
than a current paper claim. Tier 5.17b now classifies the failure: the candidate
shows structure on `ambiguous_reentry_context`, `latent_cluster_sequence` is too
input-encoded/easy, and `temporal_motif_sequence` is dominated by fixed-history
controls. The next repair is intrinsic predictive / MI-style preexposure, not a
return to delayed-credit Tier 5.9 unless future evidence shows useful
pre-reward structure exists but downstream reward cannot credit or preserve it.

That repair has now been tested as Tier 5.17c and remains non-promoted. The
intrinsic predictive preexposure matrix preserved the zero-label, zero-reward,
zero-dopamine contract and showed partial gains against no-preexposure and
simple encoder/history controls. However, it did not separate cleanly from
target-shuffled, wrong-domain, STDP-only, and best non-oracle controls under
held-out episode probes. The current paper claim must therefore state that broad
reward-free representation / concept formation remains unsolved beyond any
later bounded repair that passes stricter controls.

Tier 5.17d then runs one focused repair cycle for that exact failure mode. It
narrows the task surface to cross-modal and reentry predictive-binding cases,
scores held-out ambiguous episodes after visible cues fade, and uses a
pre-target-update representation rule so intrinsic targets can influence future
state but not same-step probes. The 60-run diagnostic passes with zero hidden
label leakage, zero reward visibility, zero dopamine during non-oracle
preexposure, candidate minimum ridge/knn probe accuracy
`0.7857142857142857`/`0.7738095238095238`, and separation from
target-shuffled, wrong-domain, history/reservoir, STDP-only, and best
non-oracle controls. This supports only a bounded software pre-reward
predictive-binding claim. It does not promote general reward-free concept
learning, hardware/on-chip representation learning, full world modeling,
language, planning, AGI, or external-baseline superiority.

Tier 5.17e then runs the promotion/regression gate and freezes v2.0. The gate
passes all four child checks: v1.8 compact regression, v1.9 composition/routing,
Tier 5.14 working-memory/context binding, and Tier 5.17d predictive-binding.
The frozen baseline lives at `baselines/CRA_EVIDENCE_BASELINE_v2.0.md`. This
upgrades the 5.17d result from noncanonical diagnostic evidence to
baseline-frozen host-side software predictive-binding evidence, while preserving
the same boundaries: no hardware/on-chip representation learning, no broad
unsupervised concept learning, no full world modeling, no language/planning/AGI,
and no external-baseline superiority.

Tier 5.18 then tests self-evaluation/metacognitive monitoring as an operational
software diagnostic over frozen v2.0. The passing run at
`controlled_test_output/tier5_18_20260429_213002/` completes `150/150` rows
with zero outcome leakage and zero pre-feedback monitor failures. The candidate
confidence signal predicts primary-path error and hazard/OOD/mismatch state,
passes Brier/ECE calibration gates, and improves behavior via confidence-gated
fallback selection against no-monitor, monitor-only, random, time-shuffled,
disabled, anti-confidence, and best non-oracle controls. This is not
consciousness, self-awareness, introspection, hardware monitoring, language,
planning, or AGI. Tier 5.18c then runs the promotion/regression gate at
`controlled_test_output/tier5_18c_20260429_221045/`: the full v2.0 compact gate
and Tier 5.18 guardrail both pass, freezing v2.1 as bounded host-side software
self-evaluation / reliability-monitoring evidence. This remains outside
hardware/custom-C self-monitoring and external-baseline superiority claims.
