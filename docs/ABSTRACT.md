# Abstract

Coral Reef Architecture (CRA) is a neuromorphic learning research platform for
studying whether local spiking plasticity, delayed credit assignment,
population-level selection, and lifecycle pressure can support useful adaptive
behavior without global backpropagation as the organizing learning rule. CRA
represents an organism as a directed reef graph of small leaky integrate-and-fire
agents called polyps. The biological terminology is used as an engineering
abstraction: each polyp maintains local state, receives sensory and consequence
signals, changes weights through dopamine-modulated local plasticity, and may be
selected, reproduced, or retired by explicit population dynamics.

The repository implements CRA as a Python/PyNN research system with NEST, Brian2,
mock, and SpiNNaker-oriented execution paths, plus a custom bare-metal SpiNNaker
C runtime used for native mechanism-transfer experiments. The project is built
around a staged validation program rather than isolated demonstrations. Evidence
is organized through predeclared tiers, generated registries, JSON/CSV/Markdown
artifacts, frozen baselines, controls, ablations, external baselines, and explicit
claim boundaries.

As of the current registry, CRA contains 119 canonical evidence bundles with zero
missing expected artifacts and zero failed criteria in canonical entries. The
software evidence includes negative controls, positive learning controls,
architecture ablations, external-baseline comparisons, delayed-credit repairs,
compact regressions, lifecycle/self-scaling tests, lifecycle sham controls,
circuit-motif causality, and bounded host-side mechanism gates for memory,
replay/consolidation, predictive context, composition/routing, working-memory
diagnostics, temporal spike coding, neuron-parameter sensitivity, predictive
binding, self-evaluation, bounded fading-memory temporal state, and a generated
curriculum/environment scoring gate that confirmed a synthetic generated-family
signal and a follow-up attribution closeout that supported keyed/compositional
mechanism attribution while documenting generator-feature alignment risk and
blocking public-usefulness, freeze, and hardware-transfer claims.
Tier 7.6a then locked the long-horizon planning/subgoal-control contract without
scoring, preserving the boundary that planning performance remains unproven.
The hardware evidence includes PyNN/SpiNNaker
capsule execution and repeatability, chunked-runtime characterization, a
custom-runtime progression through four-core MCPL task execution, keyed memory,
routing/composition, predictive binding, confidence-gated learning, host-
scheduled replay/consolidation, lifecycle static-pool/sham/task-bridge evidence
on real SpiNNaker boards, a local Tier 4.31a readiness contract for the next
v2.2 temporal-state migration, Tier 4.31b local fixed-point parity for the
selected seven-EMA temporal subset, Tier 4.31c local C/runtime ownership of
that subset, and Tier 4.31d-hw one-board hardware smoke for compact temporal
state readback and enabled/zero/frozen/reset controls. Tier 4.31e then closed
the native replay/eligibility decision gate by deferring native replay buffers,
sleep-like replay, and native macro eligibility until measured blockers exist,
and authorizing Tier 4.32 mapping/resource modeling. Tier 4.32 passed that
local resource model with positive measured profile headroom and MCPL-first
scale policy. Tier 4.32a then passed the local single-chip scale-stress
preflight, authorizing only 4/5-core single-shard hardware stress and blocking
replicated 8/12/16-core stress until shard-aware MCPL routing exists. Tier
4.32a-r0 then blocked the planned MCPL-first hardware package because the
promoted confidence-gated lookup path still used transitional SDP and the MCPL
helpers did not yet carry confidence/hit status or shard identity. Tier
4.32a-r1 repaired that blocker locally with value/meta MCPL reply packets,
shard-aware keys, cross-shard controls, and full/zero/half-confidence learning
controls over MCPL. Static reef partitioning, replicated stress, multi-chip
work, and native-scale baseline freeze remain blocked until single-shard
hardware stress passes.

The current bounded claim is that CRA is a reproducible neuromorphic research
platform with demonstrated local learning, mechanism sensitivity, selected
software capability upgrades, and repeatable SpiNNaker execution for constrained
hardware capsules and native-runtime mechanism bridges. The evidence does not yet
establish general intelligence, universal superiority over baselines, full
multi-chip scaling, production readiness, autonomous native hardware lifecycle-
to-learning MCPL, repeatable/full native v2.2 temporal dynamics beyond the
one-board seven-EMA smoke, single-shard/repeated confidence-bearing MCPL scale
stress on hardware, native replay/sleep or native macro eligibility,
native-scale baseline freeze, or fully autonomous on-chip implementations of every promoted software
mechanism.
