# Tier 7.7 Low-Rank State Repair Campaign Plan

Status: current active execution plan.

Last updated: 2026-05-09T18:35:00+00:00.

## Purpose

Tier 7.7 remains active until CRA's low-effective-dimensionality state bottleneck
is either repaired, bounded as an irreducible limitation of the current
architecture, or formally routed to a next mechanism family such as polyp
morphology/template variability.

The current blocker is not simply that CRA loses to ESN on Lorenz. The sharper
finding is:

```text
CRA state remains dynamic but effectively low-rank, with participation ratio
near ~2 even as nominal capacity increases.
```

That means more units have mostly increased movement along the same few state
directions instead of creating enough independent state geometry for Lorenz-like
multi-variable attractor reconstruction.

## Current Evidence Feeding This Plan

Tier 7.7 must treat these as locked source facts:

```text
7.7b: v2.5 improved over v2.3 on the standardized suite, driven mainly by Mackey-Glass.
7.7d/f: long-run scoring preserved the Mackey signal and repaired NARMA stream stability.
7.7h: capacity helped but was sham/overfit blocked.
7.7j: low-rank collapse confirmed; PR stayed around ~2 and readout collapse did not explain it.
7.7l: partitioned-driver repair improved task score but did not sufficiently increase dimensionality.
7.7n: generic random projection / nonlinear-lag controls explained the partitioned-driver gain.
7.7q: CRA-native temporal interface helped current CRA but still lost to strong generic controls.
7.7s: temporal-basis interface promoted only as bounded engineering utility, not a CRA-specific mechanism.
```

## Correct Roadmap Position

The order from here is:

```text
1. Continue Tier 7.7 until the low-rank state bottleneck is repaired or formally bounded.
2. Run standardized baselines/benchmarks only after a 7.7 repair candidate survives controls.
3. Move to Tier 7.8 morphology/template variability only if 7.7 routes there as the next repair hypothesis.
4. Move to Tier 7.9 lifecycle/evolution only after static morphology is tested or explicitly selected as the substrate.
```

Tier 7.8 and Tier 7.9 are not canceled. They are queued behind the 7.7 state
repair campaign.

## What Counts As Fixed

Tier 7.7 is not fixed merely because one task score improves. A real repair
needs both geometry and usefulness.

Minimum repair target for a candidate:

```text
state geometry:
  participation ratio materially increases versus the current ~2 baseline
  rank-95 / rank-99 improve
  top-PC dominance decreases
  state covariance spectrum broadens

usefulness:
  Lorenz MSE improves versus current CRA and temporal-utility reference
  aggregate standardized score improves or stays stable
  Mackey-Glass and repaired NARMA10 do not materially regress

attribution:
  candidate separates from its own ablations
  candidate is not explained by random projection or nonlinear-lag controls
  target/time shuffles fail strongly
```

Suggested contract thresholds to lock before scoring:

```text
PR increase: >=25% over current reference for diagnostic progress
strong repair candidate: PR >=4.0 or >=2x current PR at 128-state budget
Lorenz improvement: >=10% versus current CRA and temporal-utility reference
material regression guard: no >10% regression on Mackey-Glass or repaired NARMA10
strong-control requirement: random projection/nonlinear-lag must not beat the claimed mechanism
```

These are starting thresholds for the next contract. The runner must lock exact
numbers before scoring.

## Scientific Guardrail

"Hammer 7.7 until fixed" does not mean endless post-hoc tuning. It means a
controlled repair campaign:

```text
one hypothesis at a time
predeclared mechanism and null
same locked tasks and seeds
same strong controls
same state-geometry metrics
same leakage guards
clear pass/fail/outcome class
no baseline freeze until promotion/regression
```

If a candidate helps a little and does not hurt, preserve it as bounded utility
or diagnostic evidence. Do not promote it as a CRA mechanism unless it fixes the
predeclared failure class and survives controls.

## Suspected Failure Modes To Test

Tier 7.7 should explicitly localize which mechanism is causing the ~2D collapse.

Candidate causes:

```text
1. shared-driver synchronization:
   common input drive forces units into the same principal modes

2. plasticity homogenization:
   learning dynamics make many units converge to similar filters

3. inhibitory/normalization compression:
   WTA or inhibition collapses state into a small number of dominant modes

4. input-encoder bottleneck:
   state never receives enough independent causal channels

5. recurrent topology bottleneck:
   eigen spectrum / sparse graph structure supports only a few useful modes

6. trophic or energy pressure:
   survival/selection pressure suppresses diverse but initially weak states

7. readout interface bottleneck:
   recurrent state may be richer internally than the readout exposes

8. clipping / saturation / quantization:
   activity is dynamic but constrained to a narrow manifold by numerical bounds
```

## Next Tier: 7.7t Contract / Campaign Lock

Create the next gate as:

```text
Tier 7.7t - Low-Rank State Repair Campaign Contract
```

Question:

```text
Which measured failure mode should the next repair target, and what would count
as a real state-dimensionality repair rather than another generic feature win?
```

Contract artifacts should include:

```text
tier7_7t_results.json
tier7_7t_contract.json
tier7_7t_summary.csv
tier7_7t_failure_modes.csv
tier7_7t_candidate_repair_queue.csv
tier7_7t_controls.csv
tier7_7t_metrics.csv
tier7_7t_outcome_classes.csv
tier7_7t_baseline_escalation.csv
tier7_7t_claim_boundary.md
tier7_7t_report.md
```

Claim boundary:

```text
contract only; no score, no mechanism promotion, no baseline freeze, no public
usefulness claim, no hardware/native transfer
```

## Tier 7.7u: State-Collapse Causal Localization

After 7.7t locks the campaign, run a localization gate before implementing a
large repair.

Question:

```text
Where does the low-rank collapse enter: input encoding, recurrent dynamics,
plasticity, inhibition/normalization, trophic pressure, readout exposure, or
numerical saturation?
```

Required probes:

```text
state PR before learning
state PR during learning
state PR after learning
per-neuron activity variance
pairwise state correlation matrix
covariance eigen spectrum over time
per-input-channel contribution
per-template/per-partition contribution where applicable
E/I balance and inhibition activity
weight/filter similarity over time
state norm and clipping/saturation rate
readout concentration and observability
```

Controls:

```text
current CRA
current CRA plus temporal-basis utility
random projection
nonlinear-lag
no-plasticity
no-inhibition / reduced-inhibition diagnostic
frozen random recurrent state
state-reset / state-scramble
input-channel shuffle
target shuffle
time shuffle
```

Outcome classes:

```text
input_bottleneck_confirmed
plasticity_homogenization_confirmed
inhibition_compression_confirmed
recurrent_topology_bottleneck_confirmed
trophic_selection_compression_confirmed
readout_exposure_bottleneck_confirmed
numeric_saturation_confirmed
mixed_or_inconclusive
```

## Tier 7.7v+ Repair Queue

Only one repair family should be implemented at a time. The exact order should
follow 7.7u localization, but the predeclared candidate queue is:

### Repair Family A: Diversity-Preserving State Dynamics

Goal:

```text
prevent units from collapsing into the same dominant modes
```

Possible mechanisms:

```text
activity decorrelation pressure
homeostatic target-rate diversity
anti-synchrony penalty or local inhibitory balancing
per-partition activity quotas
state whitening/normalization diagnostic only, then organism-native approximation
```

Required controls:

```text
no-diversity-pressure ablation
shuffled-diversity-pressure sham
global-whitening oracle upper bound
random projection
nonlinear-lag
```

### Repair Family B: Independent Causal Subspace Drivers

Goal:

```text
give recurrent units independent causal views without relying on external random projection
```

Possible mechanisms:

```text
orthogonalized input projections
channel-specialized polyp partitions
multi-timescale causal trace banks
delay-line diversity with same feature budget
input dropout / channel masking during training to force specialization
```

Required controls:

```text
same-feature random projection
nonlinear-lag
channel-shuffle
no-delay-line ablation
single-driver ablation
```

### Repair Family C: Recurrent Topology / Spectrum Repair

Goal:

```text
make the recurrent graph support more useful independent temporal modes
```

Possible mechanisms:

```text
spectral-radius-controlled recurrent initialization
block-sparse recurrent modules with weak cross-links
winnerless competition / balanced ring motifs
diverse recurrent time constants
eigen-spectrum matched controls
```

Required controls:

```text
permuted recurrence
orthogonal recurrence
block recurrence
state reset
same-edge-count random graph
```

### Repair Family D: Plasticity Anti-Homogenization

Goal:

```text
keep learning from making every unit converge to the same filter
```

Possible mechanisms:

```text
novelty-preserving plasticity gates
weight/filter similarity penalty diagnostic
specialist protection / anti-collapse trophic pressure
slower plasticity for minority modes
diversity-aware consolidation
```

Required controls:

```text
no-plasticity
no-diversity-gate
shuffled-specialist-protection
same-budget fixed plasticity
```

### Repair Family E: Morphology / Template Variability Route

Goal:

```text
create state diversity through heterogeneous polyp templates
```

This is the Tier 7.8 route. It should be activated only if 7.7u/7.7v evidence
shows that the next best repair hypothesis is heterogeneous polyp morphology.

## Benchmark / Baseline Escalation Rule

Do not run the full benchmark/public baseline matrix after every micro-repair.
Use the ladder:

```text
7.7t contract:
  no scoring

7.7u localization:
  diagnostics only, minimal task scoring for measurement

7.7v repair candidate compact score:
  Mackey-Glass, Lorenz, repaired NARMA10 at 8000 steps, seeds 42/43/44
  current CRA, temporal-utility reference, repair candidate, ablations,
  random projection, nonlinear-lag, target/time shuffle, ESN/ridge if cheap

7.7w expanded standardized confirmation, only if compact repair passes:
  longer lengths 8000/16000/32000, more seeds if feasible, ESN/reservoir,
  online lag/ridge, small GRU if available, and SNN reviewer-defense baselines
  already supported by the repo

7.7x promotion/regression, only if expanded confirmation survives:
  compact regression, mechanism ablations, leakage guards, freeze decision

post-freeze public confirmation:
  C-MAPSS/NAB/other real-ish adapters only after a new baseline exists
```

## When To Move To Tier 7.8

Move to Tier 7.8 only if at least one of these is true:

```text
1. 7.7u localizes the bottleneck to lack of intrinsic unit/template diversity.
2. Repair families A-D fail cleanly and morphology is the next best hypothesis.
3. A 7.7 closeout contract explicitly routes the low-rank repair campaign to
   morphology/template variability.
```

If 7.7 produces a repair before morphology, run benchmarks and promotion gates
there first. Do not jump to lifecycle/evolution before resolving or bounding the
state-geometry problem.

## When To Move To Tier 7.9 Lifecycle / Evolution

Move to lifecycle/evolution only after:

```text
1. 7.7 low-rank repair is fixed or formally routed to morphology;
2. 7.8 static morphology is tested or formally bypassed;
3. the template/substrate being selected over is frozen enough to audit;
4. lifecycle controls are predeclared.
```

Lifecycle can meaningfully help against baselines, but probably on adaptive and
nonstationary tasks more than stable Lorenz reconstruction. The hypothesis is:

```text
state repair creates useful geometry;
morphology creates useful variation;
lifecycle/evolution selects useful variation over time.
```

That sequence is the defensible path.
