# Coral Reef Architecture (CRA)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-151%20passing-brightgreen.svg)](#validation)
[![Evidence](https://img.shields.io/badge/canonical%20evidence-68%20bundles-blue.svg)](STUDY_EVIDENCE_INDEX.md)

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
| Software baseline | `v2.2`, frozen after bounded host-side fading-memory temporal-state evidence plus full NEST compact regression. |
| Native hardware baseline | `CRA_LIFECYCLE_NATIVE_BASELINE_v0.4`, frozen after Tier 4.30g-hw passed lifecycle telemetry, sham controls, resource accounting, and a bounded hardware task-effect bridge. |
| Latest ingested hardware pass | Tier 4.30g-hw lifecycle task-benefit/resource bridge passed on board `10.11.242.97`: raw remote status `pass`, ingest `pass`, `285/285` hardware criteria, `5/5` ingest criteria, `36` returned artifacts preserved, enabled lifecycle opened the bounded task gate, all five predeclared controls closed it, and resource/readback accounting returned cleanly. |
| Latest lifecycle task bridge | Tier 4.30g local contract passed `9/9`, then Tier 4.30g-hw passed on real SpiNNaker: enabled lifecycle bridge gate `1`, controls bridge gate `0`, enabled reference tail accuracy `1.0`, control reference tail accuracy `0.375`, compact lifecycle payload `68`, and zero stale replies/timeouts. |
| Latest software benchmark diagnostic | Tier 5.19c fading-memory narrowing gate passed and froze v2.2: fading-memory temporal state is promoted, while bounded nonlinear recurrence and universal benchmark superiority remain unproven. |
| Latest engineering audit | Tier 4.30-readiness passed `16/16`, selecting a static-pool lifecycle-native path layered on `CRA_NATIVE_MECHANISM_BRIDGE_v0.3` with v2.2 as software reference only. |
| Latest engineering contract | Tier 4.30 passed `14/14`, defining lifecycle init/event/trophic/readback/sham commands, `23` readback fields, event invariants, gates, and failure classes. |
| Latest local lifecycle reference | Tier 4.30a passed `20/20`: deterministic 8-slot / 2-founder static-pool state, canonical 32-event trace, boundary 64-event trace, and lifecycle shams. |
| Latest lifecycle runtime source audit | Tier 4.30b passed `13/13`: runtime lifecycle static-pool surface, exact 4.30a checksum parity, lifecycle SDP readback, and existing runtime/profile tests preserved. |
| Latest multi-core lifecycle split | Tier 4.30c passed `22/22`: five-core lifecycle ownership contract, MCPL/multicast-target message semantics, final active-mask sync, exact canonical/boundary parity, and distributed failure classes. |
| Latest multi-core lifecycle runtime source audit | Tier 4.30d passed `14/14`: dedicated `lifecycle_core` runtime profile, lifecycle inter-core stubs/counters, active-mask/count/lineage sync bookkeeping, ownership guards, and local C host tests against the 4.30c contract. |
| Latest temporal hardware pass | Tier 4.31d-hw passed and was ingested from [`controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested`](controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested): board `10.11.216.121`, runner revision `tier4_31d_native_temporal_hardware_smoke_20260506_0003`, `59/59` remote hardware criteria, `5/5` ingest criteria, compact temporal payload length `48`, enabled/zero/frozen/reset controls all passed, and `21` structured returned artifacts preserved. |
| Latest temporal decision closeout | Tier 4.31e passed `15/15` from [`controlled_test_output/tier4_31e_20260506_native_replay_eligibility_decision_closeout`](controlled_test_output/tier4_31e_20260506_native_replay_eligibility_decision_closeout): native replay buffers, sleep-like replay, and native macro eligibility are deferred until measured blockers exist; Tier 4.31f is deferred; Tier 4.32 mapping/resource modeling is authorized next; no baseline freeze. |
| Latest native resource model | Tier 4.32 passed `23/23` from [`controlled_test_output/tier4_32_20260506_mapping_resource_model`](controlled_test_output/tier4_32_20260506_mapping_resource_model): MCPL is the scale data plane (`16` bytes round trip vs SDP `54`), measured profile builds retain positive ITCM/DTCM headroom, 4.32a single-chip scale stress is authorized next, and no native-scale baseline freeze is authorized yet. |
| Latest single-chip scale preflight | Tier 4.32a passed `19/19` from [`controlled_test_output/tier4_32a_20260506_single_chip_scale_stress`](controlled_test_output/tier4_32a_20260506_single_chip_scale_stress): 4/5-core single-shard MCPL-first stress is authorized next, while replicated 8/12/16-core stress is blocked until Tier 4.32a-r1 adds shard-aware MCPL routing because the current key has no shard/group field and `dest_core` is reserved/ignored. |
| Latest protocol truth audit | Tier 4.32a-r0 passed `10/10` from [`controlled_test_output/tier4_32a_r0_20260506_protocol_truth_audit`](controlled_test_output/tier4_32a_r0_20260506_protocol_truth_audit): the MCPL-first 4.32a-hw package is blocked because confidence-gated learning still uses transitional SDP, MCPL replies drop confidence, MCPL receive hardcodes confidence `1.0`, and the MCPL key lacks shard identity. Tier 4.32a-r1 is now required before MCPL-first scale stress. |
| Latest MCPL protocol repair | Tier 4.32a-r1 passed `14/14` from [`controlled_test_output/tier4_32a_r1_20260506_mcpl_lookup_repair`](controlled_test_output/tier4_32a_r1_20260506_mcpl_lookup_repair): MCPL lookup replies now carry value plus confidence/hit/status metadata, keys carry shard identity, identical seq/type cross-shard controls pass, and full/zero/half-confidence learning controls pass through the repaired MCPL path. |
| Latest temporal-native readiness | Tier 4.31a passed `24/24`, scoping the first native v2.2 temporal migration to seven causal fixed-point EMA traces. Tier 4.31b passed `16/16` with fixed/float ratio `0.9987474666079806` and zero selected saturations. Tier 4.31c passed `17/17`, adding C-owned temporal state, command codes `39-42`, compact temporal readback length `48`, behavior-backed shams, profile ownership guards, and local C host tests. |
| Latest temporal hardware return | First Tier 4.31d EBRAINS return was incomplete: only `tier4_31d_test_profiles_stdout.txt` and `coral_reef (26).elf` came back, with no `tier4_31d_hw_results.json`. This is not hardware evidence; it only shows profile host tests passed and an ARM ELF linked before structured finalization. The incomplete return is preserved at [`controlled_test_output/tier4_31d_hw_20260506_incomplete_return`](controlled_test_output/tier4_31d_hw_20260506_incomplete_return). |
| Active next gate | Tier 4.32a-hw single-shard EBRAINS scale stress: prepare and run only the eligible 4/5-core single-shard stress points with the repaired MCPL protocol, compact per-core readback, lookup parity, stale/duplicate/timeout counters, and no native-scale baseline freeze. Replicated 8/12/16-core stress remains blocked until this hardware stress passes. |
| Canonical registry | 70 evidence bundles, 0 missing expected artifacts, 0 failed criteria. |
| Validation suite | 151 pytest tests plus registry, paper-table, and repository-audit generation. |

## What CRA Implements

CRA models a population of small spiking agents called polyps. The biological
terminology is used as an engineering abstraction, not as a claim of biological
realism.

Planned capabilities are not intended to make every polyp into a large
all-purpose model. Polyps remain small specialists; larger capabilities are
tested as distributed substrate mechanisms across population state, routing,
memory, lifecycle machinery, readout interfaces, and the custom runtime.

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
| 4.22-4.30g | Custom SpiNNaker runtime progression from roundtrip/load tests to four-core MCPL tasks, keyed memory, routing/composition, predictive binding, confidence-gated learning, host-scheduled replay/consolidation, lifecycle static-pool metadata, multi-core lifecycle source/runtime gates, five-profile lifecycle hardware smoke, lifecycle sham-control hardware subset, and lifecycle task-benefit/resource bridge hardware pass. | Native hardware mechanism evidence for tested capsules only. Tier 4.30g-hw proves a bounded host-ferried lifecycle-to-task bridge with resource accounting; it does not prove autonomous lifecycle-to-learning MCPL, speedup, multi-chip scaling, v2.2 temporal migration, or full organism autonomy. |
| 4.31a-4.31d | Native temporal-substrate readiness, fixed-point reference, local C runtime source audit, and one-board SpiNNaker hardware smoke. | Defines the seven-EMA fixed-point trace subset, proves local fixed-point parity against the v2.2 fading-memory reference with destructive controls, implements/tests C-owned temporal state, and shows one-board build/load/command/readback. Not repeatability, speedup, benchmark superiority, multi-chip scaling, nonlinear recurrence, native replay/sleep, or full v2.2 hardware transfer. |
| 7.0-7.0d | Standard dynamical benchmarks and failure analysis: Mackey-Glass, Lorenz, NARMA10, aggregate geometric-mean MSE, CRA state/readout probes, bounded online readout repair, and state-specific claim narrowing. | Software diagnostics only; CRA v2.1 underperformed simple continuous-regression sequence baselines. 7.0d showed lag regression explains this benchmark path under the prior interface, so no direct benchmark-superiority claim was made. |
| 5.19a-5.19c | Continuous temporal-dynamics repair path: local temporal substrate reference, recurrence sham gate, then narrowed fading-memory compact-regression promotion. | v2.2 supports bounded host-side fading-memory temporal state. It does not prove nonlinear recurrence, hardware/on-chip temporal dynamics, universal benchmark superiority, language, planning, AGI, or ASI. |

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
  benchmark suite; Tier 5.19c promotes a bounded fading-memory substrate but
  standard-three lag-only remains stronger under the tested metrics.
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

Current execution queue:
[`docs/MASTER_EXECUTION_PLAN.md`](docs/MASTER_EXECUTION_PLAN.md). The completed
Tier 5.19 temporal-dynamics contract is preserved at
[`docs/TIER5_19_CONTINUOUS_TEMPORAL_DYNAMICS_CONTRACT.md`](docs/TIER5_19_CONTINUOUS_TEMPORAL_DYNAMICS_CONTRACT.md).

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

- 151 pytest unit tests.
- Evidence registry generation: 70 canonical bundles, 0 failed criteria.
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
  note         = {70 canonical evidence bundles; bounded SpiNNaker hardware validation}
}
```

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
