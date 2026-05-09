# Tier 7.8 Polyp Morphology / Template Variability Plan

Status: queued planning contract, not the current active repair tier.

Last updated: 2026-05-09T18:35:00+00:00.

Current sequencing note:

```text
Tier 7.7 remains active until the low-rank state bottleneck is repaired,
bounded, or formally routed to morphology. Use
docs/TIER_7_7_LOW_RANK_REPAIR_PLAN.md as the current active plan.
```

## Purpose

Tier 7.8 exists because the standardized benchmark chain found a specific
failure class: CRA improved on Mackey-Glass, but Lorenz reconstruction exposed a
low-effective-dimensionality state bottleneck. Increasing nominal capacity and
adding temporal-basis utilities helped, but strong generic controls still
explained too much of the gain.

Tier 7.8 asks whether population-level diversity can come from the organism
itself rather than from an external/random feature basis.

The short version:

```text
Can a reef made of heterogeneous polyps form a richer state geometry than a reef
made of repeated identical polyps, without the result being explained by generic
random projection, nonlinear lag features, or extra capacity?
```

Tier 7.8 is deliberately not the full lifecycle/evolution tier. It is the
static substrate test that should come before evolution:

```text
7.8 = do different polyp templates create useful diversity at all?
7.9 = if useful diversity exists, can lifecycle/evolution select, maintain, or
      improve it under task pressure?
```

Do not combine both questions in one scoring run. If morphology and evolution
are introduced simultaneously, a reviewer can no longer tell whether the result
came from template diversity, selection pressure, random turnover, extra
capacity, or benchmark leakage.

## Current Evidence Feeding This Tier

Tier 7.8 must treat these as source facts:

```text
Tier 7.7j: low-rank collapse confirmed on Lorenz diagnostics.
Tier 7.7l: partitioned drivers improved task score but did not sufficiently fix dimensionality.
Tier 7.7n: generic random projection / nonlinear-lag controls explained the gain.
Tier 7.7q: CRA-native temporal interface helped current CRA but still lost to strong generic controls.
Tier 7.7s: temporal-basis interface is promoted only as bounded engineering utility, not as a CRA-specific mechanism.
Tier 5.20a-e: resonant branch polyp replacements are parked; they are not promoted core replacements.
```

## Main Question

```text
Do heterogeneous polyp internal templates increase usable state diversity and
benchmark performance beyond current CRA, while surviving capacity-matched,
random-projection, nonlinear-lag, morphology-shuffle, and leakage controls?
```

## Hypothesis

A heterogeneous reef of same-budget polyp templates can increase population-level
state diversity because different polyps contribute different timescales,
inhibitory gates, internal sparse wiring, and response profiles. If that is true,
Lorenz should improve because the state geometry becomes richer, not merely
because a generic random basis has been added.

## Null Hypotheses

Tier 7.8 should be designed to distinguish several null explanations:

```text
1. Extra-capacity null:
   Any gain comes from more parameters/features, not morphology diversity.

2. Generic-basis null:
   Random projection or nonlinear-lag controls explain the gain as well as or
   better than CRA morphology.

3. Readout-only null:
   The recurrent/polyp state remains low-rank and the readout is simply fitting
   a better transformed input.

4. Task-local null:
   The candidate helps only one benchmark while damaging Mackey-Glass, repaired
   NARMA10, context-memory, or prior regression guards.

5. Leakage null:
   The candidate benefits from target leakage, time-order leakage, task-name
   shortcuts, or non-causal feature construction.
```

## Claim Boundary

Tier 7.8 contract documentation authorizes only planning and pre-registration.
It does not authorize:

```text
mechanism promotion
baseline freeze
public usefulness claim
external-baseline superiority claim
hardware/native transfer
language, AGI, or ASI claims
```

Even a good Tier 7.8 score is not enough to freeze a baseline. A baseline freeze
requires a later promotion/regression gate.

## Candidate Design Space

Use the smallest design that tests morphology diversity without confounding the
result.

### Primary Candidate: Same-Budget Heterogeneous Templates

Keep the total compute/state budget matched to current CRA first. The first
candidate should vary internal template type while keeping the population-level
budget auditable.

Candidate template dimensions:

```text
E/I ratio within a fixed total polyp budget
membrane/synaptic timescale bands
sparse internal connectivity masks
feedback/recurrent density
inhibitory gate strength
readout exposure pattern
input-channel specialization
```

Recommended first template bank:

```text
canonical_template:
  current 32-neuron budget and current E/I/readout structure

slow_context_template:
  same budget, slower recurrent/internal timescales, context-retention bias

fast_transient_template:
  same budget, faster timescales, event/change sensitivity

inhibitory_gate_template:
  same budget, stronger inhibitory gating / WTA pressure

sparse_recurrent_template:
  same budget, sparse recurrent mask and lower synchronizing drive
```

The exact counts should be locked in the Tier 7.8 contract runner before scoring.
Do not tune counts after seeing benchmark results.

### Secondary Candidate: Limited Polyp Size Variability

Polyp size variability is plausible but more confounded. It should not be the
first promotion claim.

Use only after the same-budget template gate is clear:

```text
small / medium / large static template classes
same total neuron/state/readout budget at the reef level
same readout parameter budget
same active-polyp budget
explicit capacity-matched fixed-template control
```

No dynamic population creation is allowed. Use static pools and active masks.

### What Not To Do

Do not:

```text
combine morphology with new replay, sleep, eligibility, lifecycle, or planning changes
silently increase total feature/readout budget
reuse parked resonant branches as if they were promoted
use task-name-specific template selection
move to hardware/native C before software usefulness and controls pass
claim biology from parameter heterogeneity alone
```

## Relationship To Lifecycle / Evolution

The full lifestyle/lifecycle system is strategically important. It is the route
by which CRA can eventually test organism-style adaptation instead of static
model selection. But it belongs in its own follow-on tier after static
morphology is measured.

Why:

```text
morphology diversity = available variation
lifecycle/evolution = selection and turnover over that variation
```

You need both for a serious organism/evolution story, but they answer different
questions.

Tier 7.8 should define and score the template bank while lifecycle remains off
or fixed. Then the next lifecycle/evolution tier can ask whether selection over
those templates adds value beyond the static heterogeneous pool.

Recommended follow-on:

```text
Tier 7.9 - Morphology-Aware Lifecycle / Evolution Contract
```

Question:

```text
Can lifecycle selection over a predeclared heterogeneous template pool improve
adaptation, retention, or benchmark performance beyond fixed heterogeneous CRA,
random matched lifecycle events, and capacity-matched controls?
```

Candidate mechanism:

```text
static max pool
fixed predeclared template genotypes
active masks
trophic health / survival pressure
cleavage / adult birth / death decisions at evaluation boundaries
bounded mutation only after a separate mutation contract
lineage and genotype IDs tracked in every artifact
```

Tier 7.9 must not introduce dynamic population allocation. Use static pools and
active masks.

Tier 7.9 controls:

```text
fixed homogeneous CRA
fixed heterogeneous CRA from Tier 7.8
lifecycle-enabled morphology CRA
random event-count matched birth/death
template-label shuffle
lineage-ID shuffle
no trophic pressure
no dopamine / no plasticity where relevant
oracle template selector upper bound
same-capacity fixed active pool
```

Tier 7.9 metrics:

```text
task score and geomean MSE
adaptation/recovery after regime changes
template survival distribution
lineage stability and lineage corruption checks
template turnover rate
active-population efficiency
seed variance
collapse/recovery dynamics
resource/runtime overhead
```

Tier 7.9 pass criteria:

```text
lifecycle-enabled morphology beats fixed heterogeneous CRA on the intended
adaptive/nonstationary pressure, not just on one lucky seed
random matched events and shuffled lineage/template controls lose
capacity-matched fixed pools do not explain the gain
lineage/genotype accounting remains clean
prior regression guards do not break
```

If Tier 7.8 fails to find useful static morphology, Tier 7.9 can still run as a
diagnostic, but the claim must be narrower:

```text
testing whether lifecycle selection can discover useful template mixtures where
the hand-designed static template bank did not
```

That version requires even stricter controls because it is easier to overfit.

## Required Controls

Tier 7.8a scoring must include these controls unless the contract explicitly
explains why one is impossible:

```text
current CRA v2.5 baseline
current CRA plus bounded temporal-basis utility reference
same-capacity fixed-template control
same E/I histogram with shuffled template assignment
same internal template bank with morphology labels shuffled
same budget random-template control
same-feature random projection control
nonlinear-lag control
no-heterogeneity ablation
no-template-specific-learning ablation if template learning differs
target-shuffle leakage guard
time-shuffle temporal-order guard
state-reset / state-scramble guard where applicable
```

The random-projection and nonlinear-lag controls are mandatory because prior
tiers showed they can explain apparent gains.

## Required Tasks

The first scoring gate should stay compact but meaningful.

Primary standardized tasks:

```text
Lorenz: primary state-geometry pressure
Mackey-Glass: positive regression guard where CRA already has signal
repaired NARMA10 u02: nonlinear memory/fading-memory guard
```

Suggested first run:

```text
length = 8000
horizon = 8
seeds = 42, 43, 44
chronological split = match Tier 7.7 contract
```

Do not start with the full 8000/16000/32000 long-run matrix. Use compact 8000
first. Expand only if the candidate survives controls.

Optional later guards after a compact pass:

```text
hidden context / reentry memory guard
C-MAPSS/NAB held-out adapter guard only after standardized signals justify it
```

## Required Metrics

Score metrics:

```text
geomean MSE
task-level MSE
correlation / shape agreement where already used
tail MSE where applicable
candidate/current ratio
candidate/temporal-utility-reference ratio
candidate/random-projection ratio
candidate/nonlinear-lag ratio
```

State-geometry metrics:

```text
participation ratio
rank-95
rank-99
top-PC variance fraction
covariance spectrum
state norm and variance over time
state-kernel alignment
readout concentration
per-template state contribution
per-template activity / silence rate
```

Audit metrics:

```text
feature count
readout parameter count
state dimension budget
runtime and memory footprint
seed variance
shuffle-control margins
regression guard deltas
```

## Preliminary Pass Criteria For Tier 7.8a

Exact thresholds should be locked in the contract runner, but the intended gate
is:

```text
1. Candidate improves Lorenz versus current CRA and temporal-utility reference.
2. Candidate improves or matches aggregate standardized score.
3. Candidate does not materially regress Mackey-Glass or repaired NARMA10.
4. Candidate increases effective state dimensionality relative to current CRA.
5. Candidate separates from morphology-shuffle and no-heterogeneity ablations.
6. Candidate is not explained by same-feature random projection or nonlinear-lag controls.
7. Target/time shuffles fail strongly.
8. Results survive seeds 42, 43, 44.
```

A useful working threshold is:

```text
>=10% score improvement on Lorenz or aggregate
<=10% material regression on guard tasks
>=25% participation-ratio increase or rank-95 improvement for state-diversity claims
candidate better than morphology shams and no-heterogeneity ablation
```

If random projection or nonlinear-lag still wins, Tier 7.8 may still be useful as
engineering evidence, but it is not a CRA-specific morphology mechanism.

## Outcome Classes

Tier 7.8 should predeclare outcome classes like these:

```text
morphology_mechanism_candidate:
  Score improves, state dimensionality improves, shams lose, strong generic
  controls do not explain the gain. Eligible for promotion/regression gate.

bounded_morphology_utility_only:
  Score improves without regressions, but strong controls still explain or beat
  the gain. Carry as utility only; no CRA-specific mechanism claim.

state_diversity_without_task_gain:
  PR/rank improves but task score does not. Useful diagnostic; no promotion.

task_gain_without_state_diversity:
  Score improves but low-rank state remains. Do not claim state-geometry repair.

generic_projection_explains_gain:
  Random projection or nonlinear-lag controls beat or match the candidate. No
  mechanism promotion.

capacity_confounded:
  Candidate wins only when given more feature/readout/parameter budget. Redesign
  with matched capacity.

regression_or_leakage_blocked:
  Shuffles fail incorrectly, guard tasks regress, or artifacts are incomplete.
  Stop and repair before any further claim.

inconclusive:
  Margins conflict or seed variance is too high.
```

## When To Run More Baselines

Do not run the full public baseline matrix at the contract stage.

Use this escalation ladder:

```text
Tier 7.8 contract:
  no scoring, no external baseline expansion

Tier 7.8a compact scoring:
  include current CRA, temporal-utility reference, random projection,
  nonlinear-lag, morphology shams, and a small external context set such as ESN
  and online ridge/lag where already implemented

Tier 7.8b expanded standardized confirmation, only if 7.8a passes or has a
bounded utility signal:
  rerun Mackey-Glass, Lorenz, repaired NARMA10 across longer lengths and seeds;
  include ESN/reservoir, online ridge/lag, online linear/logistic where relevant,
  small GRU if available, and any standardized SNN reviewer-defense baseline
  already supported by the repo

Tier 7.8c promotion/regression, only if 7.8b survives controls:
  run compact regression, mechanism ablations, no-leakage guards, and freeze a
  new software baseline only if the promoted claim is real

Post-freeze public confirmation:
  rerun the locked public/real-ish benchmark adapters only after a new baseline
  exists; do not use public adapters to rescue a failed standardized core gate
```

Lifecycle/evolution baseline escalation:

```text
Do not run lifecycle/evolution baselines inside Tier 7.8a.

Run Tier 7.9 lifecycle baselines only after:
  1. Tier 7.8 contract is locked;
  2. Tier 7.8a static morphology scoring is complete;
  3. the result identifies whether static morphology is useful, blocked, or
     generic-control explained.

For Tier 7.9, use the same standardized tasks first, then add explicit
nonstationary/adaptive pressure:
  Mackey-Glass / Lorenz / repaired NARMA10 for standardized continuity
  hard noisy switching / hidden regime recurrence for adaptation pressure
  selected public adapter only after standardized/adaptive gates justify it
```

Could lifecycle/evolution meaningfully help against baselines? Yes, but likely
not for every benchmark. Static ESN/reservoir baselines are strong on stable
state-reconstruction tasks like Lorenz. Lifecycle/evolution should be expected
to matter most where the environment changes, where capacity allocation matters,
or where specialists need to be selected and retired over time. It may still
help the standardized suite, but the stronger hypothesis is:

```text
morphology helps state geometry;
lifecycle helps adaptive selection over morphology;
the combination matters most under nonstationarity, recurrence, interference,
and long-run regime change.
```

## Baseline Freeze Rule

No baseline freeze is allowed from:

```text
Tier 7.8 contract
Tier 7.8a compact score alone
single-task Lorenz improvement
state-dimensionality improvement without task improvement
bounded utility where generic controls still win
```

A new software baseline, likely v2.6, is only eligible if:

```text
mechanism candidate passes shams and strong controls
expanded standardized baselines confirm the signal
compact regression passes
claim boundary is updated
registry and paper tables are regenerated
```

If the result is useful but generic controls still win, create a bounded utility
record instead of a core CRA mechanism freeze.

## Hardware / Native Transfer Rule

Tier 7.8 is software-first. Hardware/native transfer is blocked until:

```text
1. software usefulness survives controls;
2. the mechanism is promoted or utility-carried with a clear scaling need;
3. a separate native/hardware transfer contract is written;
4. resource, mapping, and SpiNNaker constraints are predeclared.
```

Do not port morphology variability to C or SpiNNaker merely because it is on the
roadmap.

## What To Look For While Interpreting Results

Strong result:

```text
Lorenz improves, aggregate improves, PR/rank rises, morphology shams lose,
random projection/nonlinear-lag do not explain the gain, and guard tasks stay
stable.
```

Useful but bounded result:

```text
Score improves and nothing breaks, but generic controls still win. Carry only as
engineering utility or external-control insight.
```

Architecture warning:

```text
More templates or parameters increase amplitude/norm but PR remains near 2.
That means morphology did not repair the low-rank bottleneck.
```

Capacity warning:

```text
Variable-size polyps win only because they add more state or readout budget.
That is not a morphology claim.
```

Overfitting warning:

```text
Lorenz improves but Mackey/NARMA or prior compact regression guards regress.
No promotion.
```

Reviewer-defense warning:

```text
If ESN or random projection still wins, say so plainly. The result may still be
progress over CRA, but it is not external-baseline superiority.
```

## Immediate Next Documentation/Execution Step

The next code step should be a contract runner only:

```text
experiments/tier7_8_polyp_morphology_template_variability_contract.py
make tier7-8
```

That runner should emit:

```text
tier7_8_results.json
tier7_8_contract.json
tier7_8_summary.csv
tier7_8_candidate_templates.csv
tier7_8_controls.csv
tier7_8_tasks.csv
tier7_8_metrics.csv
tier7_8_outcome_classes.csv
tier7_8_baseline_escalation.csv
tier7_8_expected_artifacts.csv
tier7_8_claim_boundary.md
tier7_8_report.md
```

After the contract runner passes, update:

```text
experiments/evidence_registry.py
experiments/repo_audit.py
README.md
CONTROLLED_TEST_PLAN.md
docs/PAPER_READINESS_ROADMAP.md
docs/MASTER_EXECUTION_PLAN.md
docs/MECHANISM_STATUS.md
codebasecontract.md
```

Then run `make validate` and commit the contract evidence.
