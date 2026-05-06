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

As of the current registry, CRA contains 63 canonical evidence bundles with zero
missing expected artifacts and zero failed criteria in canonical entries. The
software evidence includes negative controls, positive learning controls,
architecture ablations, external-baseline comparisons, delayed-credit repairs,
compact regressions, lifecycle/self-scaling tests, lifecycle sham controls,
circuit-motif causality, and bounded host-side mechanism gates for memory,
replay/consolidation, predictive context, composition/routing, working-memory
diagnostics, temporal spike coding, neuron-parameter sensitivity, predictive
binding, self-evaluation, and bounded fading-memory temporal state. The hardware evidence includes PyNN/SpiNNaker
capsule execution and repeatability, chunked-runtime characterization, a
custom-runtime progression through four-core MCPL task execution, keyed memory,
routing/composition, predictive binding, confidence-gated learning, host-
scheduled replay/consolidation, lifecycle static-pool/sham/task-bridge evidence
on real SpiNNaker boards, a local Tier 4.31a readiness contract for the next
v2.2 temporal-state migration, and Tier 4.31b local fixed-point parity for the
selected seven-EMA temporal subset before C/runtime implementation.

The current bounded claim is that CRA is a reproducible neuromorphic research
platform with demonstrated local learning, mechanism sensitivity, selected
software capability upgrades, and repeatable SpiNNaker execution for constrained
hardware capsules and native-runtime mechanism bridges. The evidence does not yet
establish general intelligence, universal superiority over baselines, full
multi-chip scaling, production readiness, autonomous native hardware lifecycle-
to-learning MCPL, native v2.2 temporal dynamics, or fully autonomous on-chip
implementations of every promoted software mechanism.
