# Contributing to Coral Reef Architecture

Thank you for your interest in CRA. This is a controlled research engineering
project, and contributions are welcome under the same evidence discipline that
governs the core team.

## Before You Start

Read these documents in order:

1. `codebasecontract.md` - the operating contract for this repo
2. `README.md` - current status and start-here index
3. `ARCHITECTURE.md` - three-column implementation truth matrix
4. `docs/CODEBASE_MAP.md` - where everything lives
5. `docs/REVIEWER_DEFENSE_PLAN.md` - how claims are defended

## Evidence Discipline (Non-Negotiable)

CRA does not accept unsupported claim-based contributions. Every change that affects a claim
must be accompanied by:

1. **Explicit claim boundary** - what it proves and what it does not prove
2. **Pass/fail criteria** - declared before looking at results
3. **Controls or ablations** - showing the effect is causal, not leakage
4. **Reproducible artifacts** - JSON/CSV/MD outputs with timestamps
5. **Registry update** - if adding a new evidence tier, update
   `experiments/evidence_registry.py`

## How to Contribute

### Bug Reports

Open an issue with:
- Exact reproduction steps
- Expected vs actual behavior
- Relevant tier runner and commit hash
- Any error logs or crash reports

### Code Contributions

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-mechanism`)
3. Make your changes
4. Run validation: `make validate`
5. Add or update tests in `coral_reef_spinnaker/tests/` or `spinnaker_runtime/tests/`
6. Update documentation (README, architecture docs, test plan as needed)
7. Commit with clear messages explaining the "why", not just the "what"
8. Open a pull request with a clear claim boundary

### Documentation Contributions

Docs are first-class citizens. Fix stale claims, improve explanations, add
diagrams, or clarify boundaries. Generated docs (STUDY_EVIDENCE_INDEX.md,
PAPER_RESULTS_TABLE.md) should be regenerated via tooling, not hand-edited.

### Hardware/Runtime Contributions

Custom SpiNNaker C runtime work has additional rules:
- Local compile and host tests must pass before hardware runs
- `experiments/tier4_*` runners follow the template in `CONTROLLED_TEST_PLAN.md`
- EBRAINS packages must be source-only and follow Rule 10 (fresh names after failures)
- See `docs/SPINNAKER_EBRAINS_RUNBOOK.md` for lessons learned

## Code Style

- Python: explicit, deterministic, typed where practical
- C runtime: follow existing patterns, preserve deterministic behavior
- Experiments: explicit tier runners with JSON/CSV/MD artifact emission
- No hidden global state, no private manual steps

## Questions?

- For architecture questions: check `docs/CODEBASE_MAP.md` first
- For evidence questions: check `STUDY_EVIDENCE_INDEX.md` and `experiments/EVIDENCE_SCHEMA.md`
- For hardware questions: check `docs/SPINNAKER_EBRAINS_RUNBOOK.md`
- For roadmap questions: check `docs/MASTER_EXECUTION_PLAN.md`

## License

By contributing, you agree that your contributions will be licensed under the
Apache License 2.0. See `LICENSE`.
