# Coral Reef Architecture Technical Whitepaper

## Document Status

This document is a technical overview of the CRA repository. It is not a
peer-reviewed paper and should not be read as a final claim of model superiority.
All claims are bounded by the committed evidence registry, frozen baselines,
controlled test definitions, and artifact policy.

Primary sources of truth:

- `controlled_test_output/STUDY_REGISTRY.json`
- `STUDY_EVIDENCE_INDEX.md`
- `docs/PAPER_RESULTS_TABLE.md`
- `baselines/`
- `CONTROLLED_TEST_PLAN.md`
- `docs/MASTER_EXECUTION_PLAN.md`
- `docs/PAPER_READINESS_ROADMAP.md`

## Executive Summary

Coral Reef Architecture (CRA) is a neuromorphic local-learning research platform.
It investigates whether populations of small spiking agents can learn and adapt
through local plasticity, delayed consequence signals, population dynamics,
context memory, and hardware-compatible state machines rather than global
backpropagation as the organizing learning rule.

CRA is best understood as a research scaffold with three integrated layers:

| Layer | Purpose |
| --- | --- |
| Python/PyNN organism | Implements polyps, reef graph state, learning, energy, lifecycle, task adapters, and backend integrations. |
| Custom SpiNNaker runtime | Migrates selected mechanisms into native C state, routing, memory, learning, lifecycle, and MCPL communication experiments. |
| Evidence system | Records tiered tests, pass/fail criteria, controls, shams, baselines, frozen states, and claim boundaries. |

The current evidence supports a bounded platform claim: CRA has demonstrated
controlled local learning, mechanism sensitivity, selected software capability
gates, and bounded SpiNNaker/custom-runtime transfer for specific task capsules
and native mechanism bridges. The evidence does not prove general intelligence,
production readiness, broad external-baseline superiority, or full autonomous
on-chip implementation of all software mechanisms.

## Research Question

The central question is:

```text
Can a population of local spiking agents learn, adapt, retain useful state, and
transfer selected mechanisms to SpiNNaker hardware under strict controls?
```

The project is not trying to win by rhetoric or biological metaphor. A mechanism
only becomes part of the claim if it survives controls, ablations, baselines
where relevant, compact regression, and documentation.

## Architecture

A CRA organism is represented as a directed reef graph of small neural agents
called polyps. Biological terms are used as engineering abstractions. They define
mechanisms to test, not literal biological claims.

| Component | Role | Representative files |
| --- | --- | --- |
| Configuration | Central parameter and feature-gate surface | `coral_reef_spinnaker/config.py`, `config_adapters.py` |
| Neural substrate | Polyps, populations, graph motifs, backend projections | `polyp_state.py`, `polyp_population.py`, `polyp_plasticity.py`, `reef_network.py` |
| Learning | Dopamine/RPE, delayed credit, readout updates | `learning_manager.py` |
| Energy and lifecycle | Trophic accounting, active masks, lineage, birth/death pressure | `energy_manager.py`, `lifecycle.py` |
| Task interface | Domain-neutral signals and adapters | `signals.py`, `task_adapter.py`, `trading_bridge.py` |
| Backends | Mock, NEST, Brian2, SpiNNaker compatibility | `backend_factory.py`, `mock_simulator.py`, `spinnaker_compat.py` |
| Custom runtime | Native SpiNNaker state, MCPL, learning, lifecycle, readback | `coral_reef_spinnaker/spinnaker_runtime/` |
| Evidence | Tier runners, registry, paper table, audit | `experiments/`, `controlled_test_output/` |

## Mechanism Philosophy

CRA does not assume that biologically inspired mechanisms are useful merely
because they are biologically named. Each mechanism is treated as a hypothesis.
Examples include:

| Mechanism | Evidence expectation |
| --- | --- |
| Local plasticity | Must outperform no-plasticity and shuffled/incorrect-credit controls where the task requires learning. |
| Delayed credit | Must mature consequences without same-step leakage and must beat weaker delayed-credit variants. |
| Context memory | Must solve same-input/different-context tasks and lose under reset, wrong-key, or shuffle controls. |
| Replay/consolidation | Must help bounded-memory stress while wrong-binding controls fail. |
| Predictive/context binding | Must improve adaptation without feedback leakage or shuffled-target shortcuts. |
| Composition/routing | Must reuse modules on held-out combinations and fail under module/router shams. |
| Lifecycle/ecology | Must beat fixed-capacity, random-event, mask-shuffle, no-trophic, and no-dopamine controls. |
| Native runtime transfer | Must preserve compact reference behavior with zero synthetic fallback and explicit host/chip boundaries. |

## Evidence Methodology

Every major tier is expected to define:

- exact question;
- hypothesis and null hypothesis;
- mechanism under test;
- controls, shams, ablations, seeds, and metrics;
- pass/fail criteria;
- expected artifacts;
- claim supported if it passes;
- claim narrowed if it fails.

Results are classified as canonical registry evidence, baseline-frozen evidence,
noncanonical diagnostics, failed/parked diagnostics, or hardware prepare/probe
evidence. Negative results are kept because they are part of the scientific
record and prevent silent p-hacking.

## Current Evidence State

The current registry contains 157 canonical evidence bundles. The most important
current state is:

| Area | Current status | Boundary |
| --- | --- | --- |
| Software predictive line | `CRA_EVIDENCE_BASELINE_v2.6` remains the current predictive benchmark baseline. | It is not a broad SOTA or AGI claim. |
| Organism-development diagnostic | `v2.7` records healthy-NEST organism-development diagnostics. | It does not supersede v2.6 for predictive usefulness. |
| Active software gate | Tier 5.45a healthy-NEST rebaseline scoring is in progress, currently `21/204` cells complete. | No new organism-mechanism promotion until the full gate is merged. |
| Native hardware line | `CRA_NATIVE_SCALE_BASELINE_v0.5` freezes bounded native-scale substrate evidence. | It is not speedup, full multi-chip learning, or full organism autonomy. |
| Public benchmark usefulness | Standardized benchmark results remain mixed. CRA has shown internal progress, but strong baselines still block broad superiority claims. | Usefulness remains an active research question. |

## Hardware And SpiNNaker Progression

CRA has two hardware lines.

First, the PyNN/SpiNNaker path demonstrated bounded task capsules with real
hardware execution, real spike readback, and zero synthetic fallback for selected
runs. These are important but remain chunked or host-assisted where documented.

Second, the custom runtime path migrates selected mechanisms into native
SpiNNaker C code. This line has progressed through continuous execution,
distributed state, MCPL communication, keyed memory, routing/composition,
predictive binding, confidence-gated learning, replay/consolidation bridges,
lifecycle metadata, multi-core and selected two-chip smokes, and a bounded
native-scale substrate baseline.

The native-runtime evidence should be read narrowly: each hardware result proves
only the named subset, board/run conditions, and pass criteria. It does not imply
that every host-side software mechanism is already autonomous on chip.

## Benchmark And Baseline Position

CRA is compared against simple and stronger baselines where appropriate,
including random/sign controls, online linear models, reservoir/ESN-style
baselines, small recurrent baselines, STDP-only controls, evolutionary controls,
lag/ridge baselines, and task-specific public-data baselines.

The current benchmark picture is mixed and scientifically useful:

- Some CRA mechanisms improve over earlier CRA baselines on selected tasks.
- Some gains are localized and not yet externally dominant.
- Strong baselines remain ahead on several standardized continuous-valued tasks.
- Healthy-NEST rebaseline work is active because earlier organism-development
  comparisons needed a corrected, auditable scoring foundation.

This is why the repo frames CRA as a research platform rather than a completed
superiority claim.

## Artifact Policy

The public repository should keep source code, compact evidence summaries,
registry files, paper tables, frozen baselines, selected canonical reports, and
reproduction instructions. Raw EBRAINS downloads, provenance databases, stack
traces, compiled binaries, generated upload bundles, and bulky scratch outputs
are ignored or externalized by policy. If raw files are needed for a paper or
reviewer, they should be cited through manifests, hashes, releases, or external
archives rather than copied into the source tree by default.

See `ARTIFACTS.md` and `docs/PUBLIC_REPO_HYGIENE.md`.

## Limitations

CRA currently does not prove:

- general intelligence or broad autonomous reasoning;
- language understanding;
- consciousness or self-awareness;
- production readiness;
- universal external-baseline superiority;
- full native on-chip implementation of every host-side mechanism;
- broad multi-chip learning/lifecycle scaling;
- open-ended curriculum learning;
- long-horizon planning beyond bounded diagnostics;
- biological realism beyond engineering inspiration.

These are not hidden weaknesses; they are the roadmap. The project is valuable
only if those boundaries remain explicit.

## Path To A Paper-Ready Claim

The paper path is not “publish when there is a good curve.” It is:

1. Finish the Tier 5.45a healthy-NEST rebaseline matrix.
2. Promote only mechanisms that survive strict controls and regression.
3. Re-run standardized/public baselines after the software line stabilizes.
4. Migrate only promoted, well-understood subsets to hardware/native runtime.
5. Preserve failures, nonclaims, and baseline losses.
6. Produce a compact reproduction package with exact commits, manifests, and
   environment instructions.
7. Write the paper around the claim actually earned, not the claim hoped for.

## Conclusion

CRA is a serious neuromorphic research platform with a large and unusually
explicit evidence trail. Its strongest current contribution is methodological and
systems-oriented: it provides a reproducible way to test local-learning spiking
mechanisms, falsify attractive biological metaphors, and move selected mechanisms
toward SpiNNaker-native execution under documented constraints. Whether it
becomes a broadly useful learning substrate remains an active empirical question.
