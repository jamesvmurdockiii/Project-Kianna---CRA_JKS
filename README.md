# Coral Reef Architecture (CRA)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-147%20passing-brightgreen.svg)]()
[![Evidence](https://img.shields.io/badge/canonical%20evidence-41%20bundles-blue.svg)]()

> A biologically-inspired neuromorphic learning system that replaces global backpropagation with local spiking plasticity, trophic energy economies, and population-level selection — running on Python/PyNN and bare-metal SpiNNaker.

## What is CRA?

The Coral Reef Architecture (CRA) is a research platform for neuromorphic learning built around a colony of **polyps** — leaky integrate-and-fire (LIF) neural agents connected by a directed **reef graph**. Each polyp:

- Earns or loses **trophic support** through three-channel energy capture
- Modifies synapses via **dopamine-modulated STDP** (no backpropagation)
- Survives or dies under **BAX-driven apoptosis** and **cyclin-D-gated reproduction**
- Computes locally with **s16.15 fixed-point arithmetic** on custom SpiNNaker runtime

The system is designed as a controlled research prototype with explicit claim boundaries, reproducible evidence bundles, and hardware execution on real SpiNNaker boards.

## Key Features

| Feature | Implementation | Evidence |
|---------|---------------|----------|
| **Multi-backend learning** | NEST, Brian2, PyNN-SpiNNaker, MockSimulator | Tiers 1–3, 5.1–5.6 |
| **Dopamine-modulated STDP** | Winner-take-all readout, delayed matured credit | Tiers 3–5.4 |
| **Trophic energy economy** | Three-channel (sensory/outcome/retrograde), pro-rata allocation | Tiers 3, 6.1–6.3 |
| **Lifecycle dynamics** | Cyclin-D reproduction, BAX apoptosis, lineage tracking | Tiers 6.1–6.3 |
| **Custom C runtime** | Bare-metal SpiNNaker, four-core distributed scaffold | Tiers 4.22–4.29 |
| **Hardware-native memory/mechanisms** | Keyed context/route/memory slots, composition, predictive binding, confidence gating, replay bridge pending | Tiers 4.29a–4.29e |
| **Evidence discipline** | 41 canonical bundles, frozen baselines, ablations, sham controls | Registry v2.1 |

## Hardware Evidence Summary

| Tier | What Was Proven | Result | Seeds |
|------|----------------|--------|-------|
| **4.28a** | Four-core MCPL repeatability (fixed-pattern) | 38/38 criteria, weight=32768, bias=0 | 42/43/44 |
| **4.28b** | Delayed-cue task on MCPL scaffold | 38/38 criteria, weight=-32769, bias=-1 | 42 |
| **4.28c** | Delayed-cue three-seed repeatability | 38/38 per seed, zero variance | 42/43/44 |
| **4.28d** | Hard noisy switching with oracle context | 38/38 per seed, weight=34208, bias=-1440 | 42/43/44 |
| **4.29a** | Native keyed-memory overcapacity gate | 10/10 per seed, context hits=24, misses=4 | 42/43/44 |
| **4.29b** | Native routing/composition (context × route × cue) | **52/52 per seed**, exact parity, zero variance | 42/43/44 |
| **4.29c** | Native predictive binding (prediction before reward) | **24/24 per seed**, weight=30912, bias=-1856 | 42/43/44 |
| **4.29d** | Native self-evaluation (confidence-gated learning) | **30/30 per seed**, zero-confidence exact weight=0 | 42/43/44 |
| **4.29e** | Native replay/consolidation bridge | Local pass; `cra_429o` submitted, hardware pending | 42/43/44 planned |

> **Claim boundary:** These prove that narrow fixed-pattern, delayed-credit, hard-switch, distributed custom-runtime, keyed-memory, routing/composition, predictive-binding, and confidence-gated-learning capsules can execute on SpiNNaker hardware and preserve expected behavior repeatably. They are **not** evidence of full hardware scaling, dynamic lifecycle on hardware, external-baseline superiority, or native on-chip replay buffers.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/jamesvmurdockiii/Project-Kianna---CRA_JKS.git
cd Project-Kianna---CRA_JKS

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install numpy scipy matplotlib
pip install sPyNNaker  # for SpiNNaker backend
# OR
pip install nest-simulator  # for NEST backend
```

### Run Smoke Test

```bash
# Run validation suite
make validate

# Run a single smoke test with mock backend
python3 experiments/tier1_sanity.py --backend mock

# Run Tier 2 learning controls on NEST
python3 experiments/tier2_learning.py --backend nest --seed 42
```

### Run External Baseline Comparison

```bash
# Compare CRA against 8 external baselines on 4 tasks
python3 experiments/tier5_external_baselines.py \
  --backend nest \
  --seed-count 3 \
  --steps 240 \
  --models all \
  --tasks all
```

## Project Structure

```
coral_reef_spinnaker/          # Main Python package
├── config.py                  # All CRA parameters with provenance tags
├── organism.py                # Top-level orchestrator
├── reef_network.py            # Graph topology, motifs, structural dynamics
├── polyp_state.py             # LIF neuron with trophic/bax/cyclin-D state
├── polyp_population.py        # PyNN population management
├── learning_manager.py        # Dopamine STDP, no backprop
├── energy_manager.py          # Three-channel trophic economy
├── lifecycle.py               # Birth/death/reproduction
├── measurement.py             # KSG MI, GCMI, BOCPD
├── backend_factory.py         # NEST/Brian2/SpiNNaker/Mock backends
├── spinnaker_runner.py        # Execution harness
├── trading_bridge.py          # Finance-specific task adapter
└── spinnaker_runtime/         # Custom bare-metal C runtime
    ├── src/                   # C source (main.c, neuron_manager.c, etc.)
    ├── tests/                 # Host-side C unit tests
    ├── PROTOCOL_SPEC.md       # Host↔runtime wire protocol
    └── Makefile               # Build system for .aplx images

experiments/                   # Tier runners and tooling
├── evidence_registry.py       # Canonical evidence registry
├── repo_audit.py              # Repository hygiene validation
├── export_paper_results_table.py
├── EVIDENCE_SCHEMA.md         # Artifact schema documentation
└── tier*.py                   # 90+ tier runners

controlled_test_output/        # Reproducible evidence trail
├── STUDY_REGISTRY.json        # Machine-readable evidence index
├── PAPER_RESULTS_TABLE.csv    # Paper-facing results
└── tier*_*_*/                 # Per-tier artifact bundles

baselines/                     # Frozen evidence baseline locks
├── CRA_EVIDENCE_BASELINE_v2.1.md
├── CRA_EVIDENCE_BASELINE_v2.1.json
└── ...

docs/                          # Research documentation
├── PAPER_READINESS_ROADMAP.md
├── MASTER_EXECUTION_PLAN.md
├── REVIEWER_DEFENSE_PLAN.md
├── CODEBASE_MAP.md
├── SPINNAKER_EBRAINS_RUNBOOK.md
├── ABSTRACT.md
├── WHITEPAPER.md
└── FULL_PROJECT_STATUS.md     # Complete tier-by-tier narrative

ebrains_jobs/                  # Self-contained EBRAINS upload packages
└── cra_*/                     # Per-tier source-only packages
```

## Documentation

| Document | Purpose |
|----------|---------|
| [`codebasecontract.md`](codebasecontract.md) | Operating contract for all contributors |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Three-column implementation truth matrix |
| [`CONTROLLED_TEST_PLAN.md`](CONTROLLED_TEST_PLAN.md) | Staged tiers, pass/fail criteria, boundaries |
| [`docs/REVIEWER_DEFENSE_PLAN.md`](docs/REVIEWER_DEFENSE_PLAN.md) | Adversarial reviewer attacks and empirical responses |
| [`docs/PUBLIC_REPO_HYGIENE.md`](docs/PUBLIC_REPO_HYGIENE.md) | Public-repo artifact, ignore, security, EBRAINS-package, and clean/commit policy |
| [`docs/SPINNAKER_EBRAINS_RUNBOOK.md`](docs/SPINNAKER_EBRAINS_RUNBOOK.md) | Hardware upload/run/ingest operations |
| [`coral_reef_spinnaker/spinnaker_runtime/PROTOCOL_SPEC.md`](coral_reef_spinnaker/spinnaker_runtime/PROTOCOL_SPEC.md) | Host↔runtime wire protocol (schema v2, 105 bytes) |
| [`STUDY_EVIDENCE_INDEX.md`](STUDY_EVIDENCE_INDEX.md) | 41-entry canonical evidence registry (human-readable) |
| [`docs/FULL_PROJECT_STATUS.md`](docs/FULL_PROJECT_STATUS.md) | Complete tier-by-tier narrative (1,500+ lines) |

## Validation

```bash
make validate
```

Runs:
- 147 pytest unit tests
- Evidence registry build (41 entries, 0 failures)
- Paper results table export
- Repository audit (paperwork alignment)

## Evidence Philosophy

CRA is built on an unusually explicit evidence discipline:

1. **No hidden failures** — failed tiers are preserved as noncanonical diagnostics
2. **Claim boundaries are mandatory** — every result states what it does **not** prove
3. **Frozen baselines** — historical evidence locks are never rewritten
4. **Hardware first** — real SpiNNaker execution, zero synthetic fallback
5. **Sham controls** — every mechanism is tested against leakage artifacts

See [`codebasecontract.md`](codebasecontract.md) Section 2 for the full thinking contract.

## Current Status

- **Software baseline:** v2.1 frozen (host-side self-evaluation / reliability-monitoring)
- **Hardware baseline:** `CRA_NATIVE_TASK_BASELINE_v0.2` frozen (Tiers 4.22i–4.28e)
- **Latest ingested hardware pass:** Tier 4.29d — native self-evaluation / confidence-gated learning, 30/30 criteria per seed, 3 seeds
- **Active hardware run:** Tier 4.29e `cra_429o` — native replay/consolidation bridge submitted, hardware pending
- **Registry:** 41 canonical bundles, 0 missing artifacts, 0 failed criteria

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening issues or PRs. Key rules:

- Evidence first — no claim without pass criteria declared upfront
- One mechanism at a time — add, test, ablate, compare, regress, then freeze
- Local before hardware — `make validate` must pass before EBRAINS runs
- Update docs immediately — stale docs are bugs

## Citation

If you use CRA in your research, please cite the canonical evidence registry:

```bibtex
@software{cra_2026,
  title={Coral Reef Architecture: A Biologically-Inspired Neuromorphic Learning System},
  author={Murdock, James V. and CRA Contributors},
  year={2026},
  url={https://github.com/jamesvmurdockiii/Project-Kianna---CRA_JKS},
  note={41 canonical evidence bundles. Hardware validated on SpiNNaker.}
}
```

## License

Apache 2.0 — see [`LICENSE`](LICENSE).

---

**Built for review by serious neuromorphic, SNN, and machine-learning researchers.**
