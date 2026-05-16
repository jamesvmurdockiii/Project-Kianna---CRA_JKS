# Public Release Readiness Report

Generated: 2026-05-16

## Purpose

This report summarizes how the public repository should be read by reviewers,
collaborators, grant/credit reviewers, and neuromorphic researchers. It is a
plain-language companion to the stricter artifact policy and roadmap docs.

## Correct Current Framing

CRA is currently a neuromorphic research platform and evidence ladder. It is not
a finished AI system, a production runtime, or a proven general-intelligence
architecture.

The strongest current public framing is:

```text
CRA tests whether local-learning spiking populations, delayed credit,
lifecycle/ecology pressure, context memory, and SpiNNaker-native runtime
mechanisms can become useful and reproducible under strict controls.
```

The public claim should remain bounded:

```text
CRA has demonstrated controlled local learning, mechanism sensitivity, selected
software capability gates, and bounded SpiNNaker/custom-runtime transfer for
specific task capsules and native mechanism bridges.
```

The public claim should not say:

```text
CRA is AGI.
CRA is production ready.
CRA is universally better than baselines.
CRA has fully autonomous on-chip versions of every software mechanism.
CRA has solved broad multi-chip organism scaling.
```

## What Reviewers Should See

Reviewers should see:

- clean source code;
- tiered experiment runners;
- compact reports, manifests, and summaries;
- frozen baselines;
- generated registry/table/audit files;
- clear pass/fail criteria;
- explicit nonclaims;
- EBRAINS/SpiNNaker runbooks;
- negative and parked evidence when it matters scientifically.

## What Reviewers Should Not See By Default

Reviewers should not have to read or clone:

- raw EBRAINS returned zip files;
- SpiNNaker provenance SQLite databases;
- stack traces and marker files;
- local Downloads intake folders;
- nested generated upload bundles inside result directories;
- compiled SpiNNaker binaries;
- private AI handoff notes;
- stale scratch output roots.

Those files can remain locally or in external archives when needed, but they are
not normal public source.

## Biggest Current Value To The Community

The current value of the codebase is not a single benchmark win. Its strongest
contribution is a rigorous, auditable research harness for neuromorphic local-
learning systems:

- it preserves claim boundaries and negative results;
- it ties results to reproducible tier artifacts;
- it gives SpiNNaker/EBRAINS operational lessons and package discipline;
- it separates software mechanism claims from hardware-transfer claims;
- it provides a platform for testing delayed credit, lifecycle/ecology,
  composition/routing, predictive binding, and native runtime migration.

## Current Active Work

The active software gate is Tier 5.45a healthy-NEST rebaseline scoring. The gate
is intentionally slow and strict because it decides whether the organism-
development mechanisms are actually useful under corrected NEST scoring. Current
progress is tracked in `docs/TIER5_45A_SHARD_EXECUTION_PLAN.md` and summarized in
`docs/MASTER_EXECUTION_PLAN.md`.

No new organism mechanism or paper-facing usefulness claim should be promoted
until Tier 5.45a is complete, merged, and reviewed.

## Public Hygiene Changes Required Going Forward

- Keep `.gitignore` aligned with `ARTIFACTS.md`.
- Use `git rm --cached` for raw artifacts that should remain local but leave Git.
- Keep README concise and sober.
- Keep detailed execution history in roadmap/status docs, not the landing page.
- Run `make validate` before public-facing commits.
- Treat raw JobManager returns as intake, not evidence.
- If raw data is needed, store it externally with hashes and cite it from a
  manifest.
