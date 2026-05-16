# Abstract

Coral Reef Architecture (CRA) is an experimental neuromorphic research platform
for testing whether local-learning spiking systems can support useful adaptive
behavior under delayed credit, nonstationarity, memory pressure, lifecycle
pressure, and SpiNNaker hardware constraints. CRA represents an organism as a
reef graph of small spiking agents called polyps. The biological terminology is
used as an engineering abstraction: polyps maintain local state, receive sensory
and consequence signals, update through local plasticity and modulatory signals,
and participate in explicit population-level selection and lifecycle dynamics.

The repository implements CRA as a Python/PyNN research system with mock, NEST,
Brian2, and SpiNNaker-oriented paths, plus a custom SpiNNaker C runtime for
chip-owned state, routing, memory, learning, lifecycle metadata, and inter-core
communication experiments. The project is organized as an evidence ladder rather
than a single demonstration. Each tier is expected to define the question,
hypothesis, null hypothesis, controls or ablations, metrics, pass/fail criteria,
artifacts, and claim boundary before results are interpreted.

As of the current registry, CRA contains 157 canonical evidence bundles. The
software evidence includes negative controls, positive learning controls,
architecture ablations, delayed-credit diagnostics, external-baseline studies,
compact regressions, lifecycle/self-scaling tests, circuit-motif causality,
memory and replay/consolidation diagnostics, predictive/context binding,
composition/routing, working-memory diagnostics, temporal coding, neuron-
parameter sensitivity, self-evaluation, policy/action diagnostics, planning
scaffolds, and standardized benchmark failure analyses. The hardware evidence
includes bounded PyNN/SpiNNaker capsules and a custom-runtime progression through
continuous execution, distributed state, MCPL communication, native mechanism
bridges, lifecycle metadata, and native-scale substrate smokes.

The current bounded claim is that CRA is a reproducible neuromorphic research
platform with demonstrated local learning, mechanism sensitivity, selected
software capability gates, and bounded SpiNNaker/custom-runtime transfer for
specific task capsules and native mechanism bridges. The evidence does not yet
establish general intelligence, broad benchmark superiority, production
readiness, full autonomous on-chip implementation of every software mechanism,
or broad multi-chip learning/lifecycle scaling. Those remain explicit future
research targets and must be earned through the roadmap before any paper claim
uses them.
