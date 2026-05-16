# Coral Reef Architecture (CRA)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Evidence](https://img.shields.io/badge/canonical%20evidence-157%20bundles-blue.svg)](STUDY_EVIDENCE_INDEX.md)

Coral Reef Architecture (CRA) is an experimental neuromorphic research platform
for studying local-learning spiking systems. The project asks whether small
spiking agents, delayed credit assignment, population/lifecycle pressure,
context memory, and SpiNNaker-native runtime mechanisms can support useful
adaptive behavior without global backpropagation as the organizing learning
rule.

This repository is not presented as a finished model, a production system, or an
AGI claim. It is a reproducible evidence ladder: each claim is tied to a tier,
predeclared pass/fail criteria, controls or ablations, baseline comparisons,
artifacts, and an explicit boundary on what the result does not prove.

## Current Public Claim

Current evidence supports this bounded claim:

> CRA is a controlled neuromorphic research platform with demonstrated local
> learning, delayed-credit handling, mechanism sensitivity, selected software
> capability gates, and bounded SpiNNaker/custom-runtime transfer evidence for
> specific task capsules and native mechanism bridges.

Current evidence does not prove:

- general intelligence, consciousness, language understanding, or broad
  autonomous reasoning;
- universal superiority over external baselines;
- state-of-the-art performance on public benchmarks;
- production readiness;
- full autonomous on-chip implementation of every software mechanism;
- broad multi-chip learning/lifecycle scaling beyond the tested native-runtime
  substrate smokes.

## Current Status

| Area | Status | Boundary |
| --- | --- | --- |
| Canonical evidence registry | `157` canonical bundles, generated from `experiments/evidence_registry.py`. | Registry status is evidence bookkeeping, not peer review. |
| Software predictive baseline | `v2.6`, frozen by the Tier 7.7z-r0 predictive benchmark line. | Not a broad SOTA claim. |
| Organism-development diagnostics | `v2.7`, a healthy-NEST diagnostic snapshot. | Does not supersede `v2.6` for predictive benchmark usefulness. |
| Native hardware/runtime line | `CRA_NATIVE_SCALE_BASELINE_v0.5`, a bounded native-scale substrate baseline. | Not speedup, benchmark superiority, or full organism autonomy. |
| Active gate | Tier 5.45a healthy-NEST rebaseline scoring, currently `21/204` organism cells complete. | No new mechanism promotion or paper-facing claim until the gate completes and is merged. |

## What CRA Implements

CRA models an organism as a population of small spiking agents called polyps. The
biological terms are engineering abstractions, not literal biological claims.
The implementation includes:

- LIF-based spiking substrates with mock, NEST, Brian2, and SpiNNaker-oriented
  execution paths.
- Dopamine-modulated local plasticity and delayed consequence handling.
- Context memory, replay/consolidation diagnostics, predictive/context binding,
  routing/composition, confidence-gated learning, and policy/action diagnostics.
- Trophic energy, lifecycle pressure, lineage tracking, and population-level
  selection experiments.
- A custom SpiNNaker C runtime used to test chip-owned state, routing, memory,
  learning, lifecycle metadata, and inter-core MCPL communication.
- Evidence tooling for registries, paper tables, repository audits, frozen
  baselines, and claim-boundary documentation.

## Evidence Structure

| Evidence class | Meaning |
| --- | --- |
| Canonical registry evidence | Paper-table evidence listed in `controlled_test_output/STUDY_REGISTRY.json`. |
| Baseline-frozen evidence | A promoted mechanism or runtime line with a frozen lock under `baselines/`. |
| Noncanonical diagnostic evidence | Useful design evidence that does not by itself support a paper claim. |
| Failed/parked evidence | Negative evidence retained to avoid p-hacking and explain why a mechanism was not promoted. |
| Hardware prepare/probe evidence | Operational packages or probes; not hardware claims until returned artifacts are ingested and promoted. |

The human-readable evidence index is [`STUDY_EVIDENCE_INDEX.md`](STUDY_EVIDENCE_INDEX.md).
The generated paper table is [`docs/PAPER_RESULTS_TABLE.md`](docs/PAPER_RESULTS_TABLE.md).
The public artifact policy is [`ARTIFACTS.md`](ARTIFACTS.md).

## Repository Layout

| Path | Purpose |
| --- | --- |
| [`coral_reef_spinnaker/`](coral_reef_spinnaker) | Main Python package, backend integration, task adapters, and custom SpiNNaker runtime source. |
| [`experiments/`](experiments) | Tier runners, evidence registry tooling, audits, and benchmark harnesses. |
| [`baselines/`](baselines) | Frozen software and native-runtime baseline locks. |
| [`docs/`](docs) | Abstract, whitepaper, roadmap, reviewer-defense plan, codebase map, EBRAINS runbooks, and hygiene policy. |
| [`controlled_test_output/`](controlled_test_output) | Compact generated evidence summaries, registry files, and selected canonical artifacts. Raw hardware downloads are ignored/externalized by policy. |
| [`ebrains_jobs/`](ebrains_jobs) | Source-only EBRAINS JobManager package references and templates. Raw upload bundles are not evidence by themselves. |

## Quick Start

```bash
git clone https://github.com/jamesvmurdockiii/Project-Kianna---CRA_JKS.git
cd Project-Kianna---CRA_JKS
python3 -m venv .venv
source .venv/bin/activate
pip install numpy scipy matplotlib pytest
```

Optional backends depend on the experiment:

```bash
pip install nest-simulator   # local NEST experiments, if available for your platform
pip install sPyNNaker        # SpiNNaker/PyNN experiments, if available in your environment
```

Run the validation suite:

```bash
make validate
```

Run a small local smoke test:

```bash
python3 experiments/tier1_sanity.py --backend mock
```

Check the active Tier 5.45a shard state:

```bash
make tier5-45a-shard-status
make tier5-45a-shard-plan
```

## How To Read The Project

Start here:

1. [`docs/ABSTRACT.md`](docs/ABSTRACT.md) for the concise claim boundary.
2. [`docs/WHITEPAPER.md`](docs/WHITEPAPER.md) for the technical overview.
3. [`docs/PAPER_READINESS_ROADMAP.md`](docs/PAPER_READINESS_ROADMAP.md) for the remaining gates before a paper claim.
4. [`docs/MASTER_EXECUTION_PLAN.md`](docs/MASTER_EXECUTION_PLAN.md) for the current execution sequence.
5. [`docs/REVIEWER_DEFENSE_PLAN.md`](docs/REVIEWER_DEFENSE_PLAN.md) for expected reviewer attacks and required safeguards.
6. [`docs/CODEBASE_MAP.md`](docs/CODEBASE_MAP.md) for source and experiment orientation.
7. [`docs/SPINNAKER_EBRAINS_RUNBOOK.md`](docs/SPINNAKER_EBRAINS_RUNBOOK.md) for EBRAINS/SpiNNaker operation.
8. [`docs/PUBLIC_REPO_HYGIENE.md`](docs/PUBLIC_REPO_HYGIENE.md) for artifact and public-repo policy.

## Reproducibility And Artifact Policy

The repo keeps source, compact reports, manifests, registries, paper tables, and
selected canonical artifacts in Git. Raw EBRAINS downloads, provenance databases,
stack traces, generated upload bundles, compiled binaries, and bulky scratch
artifacts are ignored and should be archived externally with hashes when needed.

If a paper or reviewer needs raw artifacts, cite the manifest/hash and the exact
commit. Do not treat unreviewed files from a local Downloads folder or EBRAINS
JobManager return as canonical evidence until they are ingested and documented.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening issues or pull requests.
Any change that affects a claim must include a tier definition or update,
controls/ablations where appropriate, reproducible artifacts, and documentation
updates. Failed diagnostics should be preserved when they affect the scientific
claim boundary.

## Citation

If you use this repository, cite the exact commit and the evidence registry used.
A placeholder software citation is:

```bibtex
@software{cra_2026,
  title        = {Coral Reef Architecture: A Neuromorphic Local-Learning Research Platform},
  author       = {Murdock, James V. and CRA Contributors},
  year         = {2026},
  url          = {https://github.com/jamesvmurdockiii/Project-Kianna---CRA_JKS},
  note         = {Experimental research platform; claims bounded by the committed evidence registry}
}
```

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
