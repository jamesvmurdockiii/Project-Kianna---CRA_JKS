# Tier 5.19 / 7.0e Continuous Temporal Dynamics Substrate Contract

Last updated: 2026-05-05.

Status: contract complete. Tier 5.19a has run as a local software reference and
the current active step is Tier 5.19b.

Tier 5.19a result:

```text
Output: controlled_test_output/tier5_19a_20260505_temporal_substrate_reference/
Criteria: 12/12
Classification: fading_memory_ready_but_recurrence_not_yet_specific
Boundary: noncanonical local reference only; no baseline freeze and no hardware
migration.
```

## Purpose

Tier 7.0 through Tier 7.0d showed a clean limitation:

```text
The current CRA v2.1 interface is not competitive on the tested continuous-
valued standard dynamical benchmarks, and the best candidate repairs are
explained by causal lag regression or shuffled residual controls.
```

Tier 5.19 / 7.0e exists to define a general mechanism response before any code
is written. The response is not a benchmark-specific trick. The proposed missing
substrate is:

```text
continuous temporal dynamics / fading memory / bounded recurrent state / local
continuous prediction interface
```

The goal is to test whether CRA can carry useful temporal state that is not
reducible to a fixed lag window.

## Claim Boundary

If the contract and later implementation pass, the strongest possible claim is:

```text
CRA has a bounded continuous temporal-state substrate that improves selected
stateful sequence tasks beyond lag-only and sham controls while preserving the
existing v2.1 guardrails.
```

This would not prove:

```text
general intelligence
language
full world modeling
full policy learning
universal benchmark superiority
hardware transfer
multi-chip scaling
native on-chip temporal dynamics
```

Hardware migration remains blocked until a software mechanism earns promotion.

## Mechanism Scope

Do not overload one polyp with every future capability.

The temporal substrate may use:

```text
per-polyp traces
population-level temporal summaries
readout/interface temporal state
runtime-level compact state
```

Each implementation must declare where the state lives. A polyp should remain a
small specialist. Larger temporal capability should emerge from controlled reef
machinery: many polyps, shared state summaries, routing, readout interfaces, and
eventually native runtime primitives.

## Required Scientific Question

Question:

```text
Can a CRA-native temporal substrate exploit useful hidden sequence state where
simple lag regression is insufficient?
```

Hypothesis:

```text
Multi-timescale fading state plus bounded nonlinear recurrence and a local
continuous prediction interface will improve stateful sequence tasks, separate
from lag-only and sham controls, and preserve existing CRA guardrails.
```

Null hypothesis:

```text
Any observed improvement is explained by lag-only regression, fixed/random
reservoir dynamics, frozen/shuffled temporal state, target leakage, or
benchmark-specific tuning.
```

## Required Mechanism Definition

Any further Tier 5.19 implementation may not start until the implementation
proposal explicitly defines:

```text
state variables
state location: per-polyp, population, readout/interface, or runtime
decay timescales
state update equations
nonlinear recurrent update equations
plasticity/update rule, if any
continuous prediction/readout rule
normalization rules
parameter budget
reset policy between tasks/seeds
readback/provenance fields
artifact schema
promotion and parking rule
```

The candidate must be bounded. It must not become an unconstrained supervised
model hiding inside CRA.

## Tier 5.19b Additional Requirements

Tier 5.19a proved a narrower point:

```text
Fading-memory state is useful on the held-out long-memory diagnostic.
```

It did not prove:

```text
Bounded nonlinear recurrence is the causal ingredient.
```

Tier 5.19b therefore must add sharper recurrence-specific controls:

```text
fading-memory-only ablation
recurrent-hidden-only ablation
state-reset ablation that periodically destroys long recurrent continuity
recurrent-weight shuffle or sign-permutation sham
no-plasticity readout ablation
frozen temporal-state ablation
shuffled temporal-state sham
lag-only control with the same causal lag budget
fixed/random reservoir controls
```

Tier 5.19b must also include at least one recurrence-pressure diagnostic where a
linear fading-memory trace should be weaker than a bounded nonlinear recurrent
state. If recurrence-specific value still does not separate, the correct claim
is:

```text
CRA currently benefits from fading memory, but nonlinear recurrence is not yet
proven necessary.
```

That outcome may still justify a fading-memory mechanism, but not a stronger
recurrent-substrate claim.

## Anti-Benchmark-Chasing Rules

The implementation must obey these rules:

```text
Use one predeclared parameter family across Mackey-Glass, Lorenz, NARMA10, and
the held-out temporal-state diagnostic, unless the contract explicitly declares
a tiny hyperparameter budget and applies the same budget to baselines.

Do not tune on held-out rows.

Do not add benchmark-name conditionals to the mechanism.

Do not use future targets, future observations, or target-derived hidden
features.

Do not promote if improvement appears only on one benchmark family.

Do not call a lag-only win a CRA temporal-state win.
```

## Testing Ladder

Tier 5.19 uses this ladder:

```text
1. Contract gate: this document plus CONTROLLED_TEST_PLAN.md alignment.
2. Local deterministic reference: pure Python/NumPy or fixed-point reference.
3. Software CRA integration: run the candidate in the CRA software path.
4. NEST guardrail: required if the mechanism changes spiking dynamics or claims
   backend-sensitive neural behavior.
5. Brian2 parity: required only if backend portability is part of the claim.
6. Compact regression: core CRA controls and current v2.1 guardrails.
7. Promotion/freeze decision.
8. Hardware/native migration only if promotion is earned.
```

SpiNNaker / sPyNNaker / custom-runtime testing is not run for unpromoted
mechanism candidates. Hardware time is reserved for promoted mechanisms or
explicit hardware-runtime gates.

## Required Tasks

Primary benchmark tasks:

```text
Mackey-Glass future prediction
Lorenz future prediction
NARMA10 nonlinear memory/system identification
aggregate geometric-mean MSE
```

CRA guardrail tasks:

```text
delayed_cue
hard_noisy_switching
memory/context pressure tasks
predictive/context binding guardrail
self-evaluation reliability guardrail
compact Tier 1/2/3 controls
```

Held-out temporal-state diagnostic:

```text
At least one predeclared task where the current observation and a short lag
window are insufficient, but a bounded recurrent/fading state should help.
```

The held-out diagnostic is required because Mackey-Glass, Lorenz, and NARMA10
may still be partly solvable by simple lag regression. If lag-only remains
dominant on the standard suite, the held-out task prevents false promotion.

## Required Comparisons

Minimum comparisons:

```text
current CRA v2.1
raw CRA continuous output from Tier 7.0
lag-only online LMS with identical causal lag budget
state-only online model
state plus lag online model
fixed ESN / reservoir baseline
random reservoir baseline
no-recurrence ablation
no-plasticity ablation
frozen temporal-state ablation
shuffled temporal-state sham
shuffled-target control
current Tier 7.0 baselines
```

Optional reviewer-defense comparisons if cheap:

```text
online ridge/RLS
small GRU
STDP-only temporal baseline
surrogate-gradient SNN baseline
```

Optional comparisons must not delay the core gate unless a reviewer-facing claim
depends on them.

## Pass Criteria

Tier 5.19a/b may pass only if all of these are true:

```text
No leakage or held-out-row fitting.

All required tasks, seeds, controls, and artifacts complete.

The temporal substrate improves raw v2.1 on stateful sequence tasks.

The temporal substrate beats lag-only by a predeclared meaningful margin on at
least one task where lag-only should be insufficient.

The temporal substrate separates from shuffled-state, frozen-state,
no-recurrence, no-plasticity, and shuffled-target controls.

The improvement is not isolated to a single benchmark family.

Existing CRA guardrails do not materially regress.

Artifacts are sufficient for paper-grade audit.
```

Default margin unless overridden by the runner contract:

```text
At least 10% lower MSE than lag-only on the held-out temporal-state diagnostic,
and no worse than 5% regression on existing CRA guardrail metrics.
```

If a stronger margin is predeclared in a runner, use the stronger margin.

## Fail Criteria

Classify as fail or park if any of these happen:

```text
Lag-only or fixed/random reservoirs explain the gain.

Shuffled or frozen temporal state performs similarly to the candidate.

The candidate helps only one benchmark after tuning.

The candidate regresses existing CRA claims.

The candidate requires task-name-specific code paths.

Any leakage is found.

The mechanism cannot be described as bounded CRA-native state.
```

Failure is useful evidence. Preserve it. Do not tune blindly.

## Promotion / Freeze Decision

Tier 5.19 / 7.0e itself does not freeze a baseline.

Promotion requires:

```text
Tier 5.19a local reference pass
Tier 5.19b benchmark/sham/regression pass
compact regression pass
updated evidence registry or explicit noncanonical freeze note
baseline document if a new software baseline is frozen
```

If promoted, freeze a new software baseline only after compact regression. If
not promoted, keep `v2.1` as the current software baseline and leave Tier 7.0
as an honest limitation.

## Hardware Migration Decision

Hardware migration is conditional:

```text
If Tier 5.19 promotes a temporal substrate:
  run Tier 4.30e native temporal-substrate readiness.
  define the smallest chip-owned temporal subset.
  build local fixed-point parity before EBRAINS.

If Tier 5.19 fails:
  do not move the Tier 7 benchmark path to hardware.
  keep lifecycle-native work queued on v2.1 or another promoted baseline.
```

No SpiNNaker run is allowed solely because a mechanism sounds biologically right.

## Expected Artifacts

Tier 5.19a/b outputs should include:

```text
tier5_19_results.json
tier5_19_summary.csv
tier5_19_report.md
tier5_19_timeseries.csv
tier5_19_fairness_contract.json
tier5_19_leakage_audit.json
tier5_19_controls.csv
tier5_19_manifest.json
```

If plots are generated, they must be secondary to machine-readable artifacts.

## Documentation Updates Required

After each Tier 5.19 step:

```text
codebasecontract.md Section 0
docs/MASTER_EXECUTION_PLAN.md
CONTROLLED_TEST_PLAN.md
docs/PAPER_READINESS_ROADMAP.md
experiments/README.md
docs/CODEBASE_MAP.md if a runner is added
STUDY_EVIDENCE_INDEX.md / registry only if ingested as canonical evidence
baseline document only if frozen
```

Run `make validate` before committing.
