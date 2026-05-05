# Coral Reef Architecture (CRA)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-147%20passing-brightgreen.svg)](#validation)
[![Evidence](https://img.shields.io/badge/canonical%20evidence-47%20bundles-blue.svg)](STUDY_EVIDENCE_INDEX.md)

Coral Reef Architecture (CRA) is a neuromorphic learning research platform for
studying local spiking plasticity, delayed credit assignment, population-level
selection, and SpiNNaker hardware execution without relying on global
backpropagation as the organizing learning rule.

The repository is structured as a reproducible research artifact. Claims are tied
to predeclared tiers, generated evidence registries, pass/fail criteria,
controlled ablations, baseline comparisons, and explicit claim boundaries.

## Current Status

| Area | Current state |
| --- | --- |
| Software baseline | `v2.1`, frozen after bounded host-side self-evaluation / reliability-monitoring evidence. |
| Native hardware baseline | `CRA_NATIVE_MECHANISM_BRIDGE_v0.3`, frozen after Tier 4.29f audited the 4.29a-e native mechanism hardware passes. |
| Latest ingested hardware pass | Tier 4.29e, native host-scheduled replay/consolidation bridge, `38/38` criteria per seed across seeds `42`, `43`, and `44`. |
| Latest software benchmark diagnostic | Tier 7.0d showed the current standard dynamical benchmark path is explained by causal lag regression, not a promoted CRA state-specific mechanism. |
| Active next gate | Return to the native roadmap: Tier 4.30 lifecycle-native contract with static preallocated pool, lifecycle masks, lineage telemetry, and sham controls. |
| Canonical registry | 47 evidence bundles, 0 missing expected artifacts, 0 failed criteria. |
| Validation suite | 147 pytest tests plus registry, paper-table, and repository-audit generation. |

## What CRA Implements

CRA models a population of small spiking agents called polyps. The biological
terminology is used as an engineering abstraction, not as a claim of biological
realism.

Core implementation areas:

- Leaky integrate-and-fire neural substrate with NEST, Brian2, mock, and
  SpiNNaker-oriented backends.
- Dopamine-modulated local plasticity and delayed consequence handling.
- Trophic energy accounting, lifecycle pressure, lineage tracking, and
  population-level selection.
- Domain-neutral task adapters plus historical finance/trading adapters.
- A custom SpiNNaker C runtime for native state, routing, memory, learning, and
  mechanism-transfer experiments.
- A tiered experiment suite with canonical and noncanonical evidence tracking.

## Evidence Highlights

| Tier | Evidence | Boundary |
| --- | --- | --- |
| 1-3 | Negative controls, positive learning controls, and architecture ablations. | Software controls; not hardware evidence. |
| 4.13-4.18a | PyNN/SpiNNaker hardware capsule, repeatability, harder-task transfer, and chunked-runtime characterization. | Real hardware evidence for bounded capsules; not full hardware scaling. |
| 5.1-5.7 | External baselines, learning curves, failure analysis, delayed-credit confirmation, fairness audit, compact regression. | Software evidence; not universal superiority. |
| 5.10-5.18 | Memory, replay/consolidation, predictive context, composition/routing, working memory diagnostics, temporal coding, neuron-parameter sensitivity, predictive binding, and self-evaluation gates. | Mostly host-side software mechanisms unless explicitly migrated to hardware. |
| 6.1-6.4 | Lifecycle/self-scaling, lifecycle sham controls, and circuit-motif causality. | Software organism/ecology evidence; not hardware lifecycle. |
| 4.22-4.29 | Custom SpiNNaker runtime progression from roundtrip/load tests to four-core MCPL tasks, keyed memory, routing/composition, predictive binding, confidence-gated learning, host-scheduled replay/consolidation, and the 4.29f evidence-regression freeze gate. | Native hardware mechanism evidence for the tested capsules only; 4.29f is an audit over hardware passes, not a new hardware execution. |
| 7.0-7.0d | Standard dynamical benchmarks and failure analysis: Mackey-Glass, Lorenz, NARMA10, aggregate geometric-mean MSE, CRA state/readout probes, bounded online readout repair, and state-specific claim narrowing. | Software diagnostics only; CRA v2.1 underperformed simple continuous-regression sequence baselines. 7.0d showed lag regression explains this benchmark path under the current interface, so no mechanism promotion or hardware migration is claimed. |

The most current paper-facing evidence index is generated at
[`STUDY_EVIDENCE_INDEX.md`](STUDY_EVIDENCE_INDEX.md). The machine-readable
registry is [`controlled_test_output/STUDY_REGISTRY.json`](controlled_test_output/STUDY_REGISTRY.json).

## Claim Boundary

Current evidence supports this bounded claim:

> CRA is a controlled neuromorphic research platform that demonstrates local
> learning, delayed credit, mechanism sensitivity, backend portability, selected
> software capability upgrades, and repeatable SpiNNaker hardware execution for
> bounded task capsules and native-runtime mechanism bridges.

Current evidence does not prove:

- General intelligence or broad autonomous reasoning.
- Universal superiority over external baselines.
- Competitive performance on the Tier 7.0 continuous-valued standard dynamical
  benchmark suite; Tier 7.0d narrows that path to a lag-regression-explained
  limitation under the current interface.
- Full organism lifecycle running natively on hardware.
- Multi-chip scaling.
- Production readiness.
- Native on-chip replay buffers or fully autonomous on-chip learning for all
  promoted software mechanisms.

## Repository Layout

| Path | Purpose |
| --- | --- |
| [`coral_reef_spinnaker/`](coral_reef_spinnaker) | Main Python package, task adapters, backend integration, and custom SpiNNaker runtime. |
| [`experiments/`](experiments) | Tier runners, evidence registry tooling, audit tooling, and paper-table export. |
| [`controlled_test_output/`](controlled_test_output) | Reproducible evidence bundles, generated registry, paper table CSV, and noncanonical audit history. |
| [`baselines/`](baselines) | Frozen baseline locks for software and native-runtime evidence states. |
| [`docs/`](docs) | Research documentation, roadmap, reviewer-defense plan, runbooks, whitepaper, and codebase map. |
| [`ebrains_jobs/`](ebrains_jobs) | Source-only EBRAINS JobManager upload packages preserving what was sent to hardware. |

## Quick Start

```bash
git clone https://github.com/jamesvmurdockiii/Project-Kianna---CRA_JKS.git
cd Project-Kianna---CRA_JKS
python3 -m venv .venv
source .venv/bin/activate
pip install numpy scipy matplotlib
```

Optional backend dependencies depend on the experiment being run:

```bash
pip install nest-simulator   # NEST-backed local experiments, if available
pip install sPyNNaker        # SpiNNaker/PyNN experiments, if available
```

Run the standard validation suite:

```bash
make validate
```

Run a small local smoke test:

```bash
python3 experiments/tier1_sanity.py --backend mock
```

Run a baseline comparison example:

```bash
python3 experiments/tier5_external_baselines.py \
  --backend nest \
  --seed-count 3 \
  --steps 240 \
  --models all \
  --tasks all
```

## Validation

`make validate` currently runs:

- 147 pytest unit tests.
- Evidence registry generation: 47 canonical bundles, 0 failed criteria.
- Paper results table export.
- Repository audit.

Generated outputs include:

- [`STUDY_EVIDENCE_INDEX.md`](STUDY_EVIDENCE_INDEX.md)
- [`docs/PAPER_RESULTS_TABLE.md`](docs/PAPER_RESULTS_TABLE.md)
- [`docs/RESEARCH_GRADE_AUDIT.md`](docs/RESEARCH_GRADE_AUDIT.md)
- [`controlled_test_output/README.md`](controlled_test_output/README.md)

## Documentation Map

| Document | Purpose |
| --- | --- |
| [`docs/ABSTRACT.md`](docs/ABSTRACT.md) | Concise project abstract and current evidence boundary. |
| [`docs/WHITEPAPER.md`](docs/WHITEPAPER.md) | Technical overview of architecture, evidence, limitations, and roadmap. |
| [`docs/PAPER_READINESS_ROADMAP.md`](docs/PAPER_READINESS_ROADMAP.md) | Strategic roadmap toward paper-ready claims. |
| [`docs/MASTER_EXECUTION_PLAN.md`](docs/MASTER_EXECUTION_PLAN.md) | Operational execution sequence from the current state. |
| [`CONTROLLED_TEST_PLAN.md`](CONTROLLED_TEST_PLAN.md) | Tier definitions, hypotheses, controls, pass/fail criteria, and claim boundaries. |
| [`docs/REVIEWER_DEFENSE_PLAN.md`](docs/REVIEWER_DEFENSE_PLAN.md) | Reviewer attack matrix and planned safeguards. |
| [`docs/CODEBASE_MAP.md`](docs/CODEBASE_MAP.md) | File-by-file map of source, experiments, runtime code, and evidence areas. |
| [`docs/SPINNAKER_EBRAINS_RUNBOOK.md`](docs/SPINNAKER_EBRAINS_RUNBOOK.md) | EBRAINS/SpiNNaker upload, run, ingest, and troubleshooting guide. |
| [`docs/PUBLIC_REPO_HYGIENE.md`](docs/PUBLIC_REPO_HYGIENE.md) | Public repository artifact policy, security checks, and clean/commit SOP. |
| [`codebasecontract.md`](codebasecontract.md) | Maintainer operating contract for evidence discipline and repository updates. |

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening issues or pull requests.
Changes that affect claims must include explicit pass/fail criteria, controls or
ablations, reproducible artifacts, and documentation updates. Generated registry
and paper-table files should be regenerated through tooling rather than edited by
hand.

## Citation

If you use this repository in research, cite the evidence registry and the exact
commit used. A placeholder software citation is:

```bibtex
@software{cra_2026,
  title        = {Coral Reef Architecture: A Neuromorphic Local-Learning Research Platform},
  author       = {Murdock, James V. and CRA Contributors},
  year         = {2026},
  url          = {https://github.com/jamesvmurdockiii/Project-Kianna---CRA_JKS},
  note         = {47 canonical evidence bundles; bounded SpiNNaker hardware validation}
}
```

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
