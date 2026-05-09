# Reviewer Defense Plan

Generated: 2026-04-27

This document lists the attacks a skeptical reviewer should be expected to make
against CRA, and the evidence we need before the paper can make a strong claim.
It is intentionally adversarial. The goal is not to win by rhetoric; the goal is
to make the obvious critiques empirically boring because the repo already
answers them.

## Current Position

The current strongest claim after the v2.5 freeze is:

```text
CRA is a validated neuromorphic research system with strict controls,
mechanism ablations, backend parity, external-baseline diagnostics,
repeatable fixed-pattern SpiNNaker hardware evidence, repaired delayed-cue and
hard_noisy_switching SpiNNaker transfer across seeds 42, 43, and 44 under
chunked host replay, and controlled software lifecycle/self-scaling evidence
with clean lineage and hard_noisy_switching advantage regimes. The locked CRA
configuration also completed expanded and tuned-baseline software audits with
robust/non-dominated hard-adaptive regimes. Tier 6.4 adds controlled software
circuit-motif causality: seeded motif-diverse graphs log pre-reward motif
activity, selected motif ablations cause predicted losses, and random/monolithic
controls do not dominate when recovery and active-population efficiency are
included. Tier 5.10d/5.10e add noncanonical internal host-side memory evidence:
the context-memory mechanism now lives inside `Organism`, survives longer gaps,
denser distractors, and hidden recurrence stress, and remains bounded as
software memory rather than sleep/replay or native on-chip memory. Tier 5.10f
then cleanly failed under capacity/interference stress, narrowing that memory
claim. Tier 5.10g repaired that measured single-slot failure with bounded
keyed/multi-slot context memory inside `Organism`, matched the oracle-key
scaffold on the tested stress tasks, beat v1.5 single-slot memory and slot
ablations, and preserved compact regression. This is still host-side memory, not
native on-chip memory, sleep/replay, compositionality, module routing, or
general working memory. Tier 5.11a now adds a noncanonical need diagnostic:
v1.6 no-replay degrades under silent reentry stressors while unbounded keyed and
oracle controls solve them, yielding the predeclared decision
`replay_or_consolidation_needed`. Tier 5.11b and Tier 5.11c then block the
narrower priority-specific replay claim because shuffled/shuffled-order replay
comes too close. Tier 5.11d promotes the broader, defensible claim:
correct-binding replay/consolidation repairs the silent-reentry failure with
zero leakage, separates from wrong-key/key-label/priority-only/no-consolidation
controls, and preserves compact regression. Tier 5.12a validates predictive
task pressure, Tier 5.12b records the failed first predictive-context sham
contract, Tier 5.12c repairs that sham contract, and Tier 5.12d preserves old
guardrails while freezing v1.8 as bounded host-side visible predictive-context
software evidence. Tier 5.13c then internalizes composition/routing into the
CRA host loop and freezes v1.9 after a fresh full compact regression. Tier 5.14
adds noncanonical diagnostic coverage showing that v1.9 context/cue memory and
delayed module-state routing survive broader working-memory pressure. Tier 5.15
adds noncanonical software temporal-code coverage showing that latency, burst,
and temporal-interval spike structure can carry task-relevant information under
time-shuffle and rate-only controls. Tier 5.17d repairs the narrower
predictive-binding failure mode after broad reward-free representation failed,
and Tier 5.17e freezes v2.0 after v1.8 compact regression, v1.9
composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d
predictive-binding guardrails all pass. Tier 5.18c then froze bounded v2.1 self-evaluation evidence, Tier 5.19c froze bounded v2.2 fading-memory temporal-state evidence, Tier 7.0j froze bounded v2.3 generic recurrent-interface evidence, Tier 7.4c froze bounded v2.4 cost-aware policy/action evidence, and Tier 7.6e froze bounded v2.5 reduced-feature planning/subgoal-control evidence after Tier 7.6d repaired the feature-alignment blocker and full NEST compact regression passed. This does not prove priority weighting,
hidden-regime inference, broad unsupervised concept learning, full world
modeling, language, planning, hardware prediction, hardware scaling, native
on-chip learning, hardware/on-chip composition, routing, temporal coding,
representation learning, or external baseline superiority.
```

The current claim is not yet:

```text
CRA is universally superior.
CRA has proven full adult birth/death turnover, hardware lifecycle, or external-baseline superiority for lifecycle/self-scaling.
CRA has proven hard_noisy_switching superiority over the best external baseline.
CRA has proven hardware transfer beyond N=8 chunked-host capsules.
CRA has proven continuous/on-chip learning.
CRA has proven hardware motif execution, hardware/on-chip compositionality, or world modeling.
CRA has proven native/on-chip replay, hardware memory transfer, or biological sleep.
CRA has proven priority weighting is essential to replay.
CRA has proven unbounded/general working memory, hardware/on-chip memory, or robust real-world memory transfer.
CRA has proven broad real-world usefulness.
```

## Reviewer Attack Matrix

| Attack | What They Will Say | Defense Required Before Paper |
| --- | --- | --- |
| Leakage | The task leaks future labels or target signs. | zero-signal, shuffled-label, lag/audit tests, temporal-only splits, adapter leakage review. |
| Cherry-picking | You picked lucky seeds or favorable horizons. | predeclared seed sets, 10+ software seeds for key claims, per-seed tables, min/median/mean/std. |
| P-hacking | You tuned until it worked and forgot failures. | frozen baselines, retained failure bundles, preregistered pass/fail rules before final matrices. |
| Weak baselines | Baselines were under-tuned or unfair. | equal task streams, matched visibility, hyperparameter budget, strong online/RL/reservoir/SNN baselines. |
| No sample-efficiency advantage | CRA only matches baselines after seeing too much data. | steps-to-threshold, reward-events-to-threshold, switch-recovery, area-under-learning-curve metrics. |
| Toy-task overfit | CRA only wins on tasks shaped for CRA. | hidden/holdout synthetic tasks, real-ish adapters, public datasets, no CRA-only task hints. |
| Mechanism theater | Biology words are decorative. | causal ablations, dopamine time-shift/shuffle, delayed-credit disable, lifecycle sham controls, lineage logs. |
| Mean hides collapse | Averages look good but some seeds fail. | worst-case metrics, median, variance, bootstrap intervals, collapse/recovery plots. |
| Hardware theater | It runs, but hardware is just a slow host loop. | chunk/runtime characterization, spike/readback/provenance/resource accounting, no synthetic fallback, clear host/chip boundary. |
| Bridge mismatch | Chunked host replay is not equivalent to full CRA dynamics. | step-vs-chunked parity by task, full-CRA-vs-bridge comparisons, delayed-credit maturity traces, one-seed probes only after local bridge repair. |
| Scaling theater | Manual N-scaling is not self-scaling. | fixed-N versus lifecycle-enabled, preallocated pool, active/inactive masks, lineage integrity, efficiency per active polyp. |
| Catastrophic forgetting | The organism adapts by overwriting old regimes. | A-B-A and A-B-C-A recurrence tests, fast/slow/structural memory ablations, replay/no-replay controls, reacquisition-speed metrics. |
| Host-led delayed credit | The delayed reward mechanism is Python bookkeeping, not neuromorphic learning. | macro eligibility trace comparisons, delay sweeps, trace ablations, hybrid/native trace roadmap, explicit host/chip boundary. |
| Spike transport only | Spikes are just a transport layer; timing carries no information. | Tier 5.15 now passes as noncanonical software temporal-code evidence: latency, burst, and temporal-interval codes support task learning on fixed_pattern, delayed_cue, and sensor_control, while time-shuffle and rate-only controls lose. This is still software-only and not hardware/on-chip temporal coding. |
| Fragile neuron model | CRA only works for one hand-tuned LIF parameter setting. | Tier 5.16 now passes as noncanonical NEST neuron-parameter sensitivity evidence: 11 LIF threshold/tau/refractory/capacitance/synaptic-tau variants remain functional with zero fallback/failure counters and monotonic direct LIF response probes. Adaptive-LIF/Izhikevich checks remain future optional robustness work. |
| Decorative circuit motifs | Reef motifs, WTA, inhibition, and feedback are labels around a readout learner. | motif ablations, same-capacity random/monolithic graph controls, motif activity traces. |
| No unsupervised structure | CRA only learns when reward labels are supplied. | unlabeled preexposure tests, shuffled-preexposure controls, downstream sample-efficiency comparison. |
| Reactive learner | CRA is Pavlovian reward chasing, not predictive/contextual learning. | next-state/masked-input prediction tests, predictive-error ablations, feedback/context-path controls, real-ish event-stream adapters. |
| No compositionality | CRA learns isolated reflexes but cannot reuse learned skills as subroutines. | Tier 5.13 passes an explicit reusable-module scaffold and Tier 5.13c now passes internal host-side CRA composition/routing with module shams and reusable-module traces; broader claims still need harder composition, policy, and real-ish tasks. |
| No working memory/context | CRA cannot hold context, subgoals, or recent cue history. | Tier 5.14 now passes as a noncanonical v1.9 software diagnostic: context/cue memory and delayed module-state routing both reach `1.0` task accuracy, with reset/shuffle/no-write/random shams and sign-persistence/routing-off controls losing. This is still host-side software evidence, not hardware/on-chip working memory, planning, language, or AGI. |
| No self-evaluation/metacognition | CRA cannot estimate confidence, uncertainty, novelty, or failure risk before feedback. | calibrated confidence/OOD/error-prediction tests, random/always-confidence controls, post-outcome leakage controls, monitor-trigger traces. |
| No real policy loop | CRA predicts signs but does not learn action selection. | delayed-reward control tasks, action-value/exploration traces, bandit/RL baselines, causal state-action-consequence checks. |
| Hand-built curriculum | CRA only works on manually designed tasks. | generated task families, difficulty schedules, held-out generator modes, identical generated streams for baselines. |
| No long-horizon planning | CRA reacts locally but cannot pursue multi-step subgoals. | subgoal-chain tasks, reward-time shuffles, subgoal reset/order-shuffle controls, planning/RL baselines, oracle-subgoal upper bounds. |
| Novelty challenge | This is just reward-modulated STDP/reservoir/evolutionary SNNs. | literature mapping with primary sources, component comparison table, fair baseline implementations. |
| Missing strong SNN baselines | CRA avoided surrogate-gradient or ANN-to-SNN comparisons. | surrogate-gradient SNN, ANN-trained readout, ANN-to-SNN conversion where task-compatible; explicit non-applicability rationale where not fair. |
| Reproducibility | Nobody else can rerun it. | one-command reproduction, environment lock, artifact manifests, data/version hashes, raw provenance kept or regenerable. |
| Overclaiming | Results do not justify paradigm-shift language. | claim-level ladder, final v1.4-or-later lock, limitations and failed results in paper. |

## Mandatory Paper-Grade Safeguards

### 1. Preregistration For Final Matrices

Before final Tier 5.5, Tier 6.1, Tier 7, and Tier 8 runs, write down:

```text
tasks
seeds
run lengths
metrics
baseline list
hyperparameter budget
pass/fail criteria
stop/debug rules
claim supported if pass
claim narrowed if fail
```

Changing these after seeing results must create a new diagnostic tier, not edit
the old one.

### 2. Statistical Standards

For every paper-critical comparison export:

```text
mean
median
std
min
max
95% bootstrap confidence interval or comparable interval
effect size versus strongest baseline
paired per-seed deltas where applicable
collapse/recovery statistics
steps to threshold
tail/reward events to threshold
area under learning curve
runtime/resource confidence intervals for hardware
```

Do not use mean accuracy alone as a claim driver.

### 3. Baseline Fairness Contract

Every baseline comparison must use:

```text
same task stream
same train/evaluation windows
same delayed reward visibility
same seed set
same normalization
same leakage restrictions
same online/causal information boundary
reasonable hyperparameter sweep budget
reported best, median, and default baseline performance
```

If CRA gets a tuning sweep, baselines get a comparable sweep. If baselines get a
larger sweep, say so and report it.

### 4. Regression Ladder After Feature Work

Do not rerun the entire paper matrix after every exploratory tweak. Use a
staged regression ladder:

```text
Exploratory tweak:
  focused diagnostic only
  no baseline rewrite

Candidate mechanism:
  targeted head-to-head against frozen v0.7 on the tasks it should improve
  direct ablation of the new mechanism
  per-seed deltas and variance

Promoted mechanism:
  compact regression before becoming a new baseline
  combination tests only after single-feature wins are established
  keep A+B only if it beats or complements A alone and B alone

Paper-lock mechanism:
  full final matrix against external baselines, holdouts, and the selected
  hardware subset
```

Strategic mechanisms may be necessary for the long-term substrate claim, but
their implementations still have to earn promotion. Give each mechanism a fair
bounded development cycle:

```text
prototype
instrument
targeted test
bounded debug
ablation/control
promote, redesign, or archive
```

Debug a failed mechanism when traces suggest an implementation bug, metric/task
mismatch, or a small repair would make the test fair. Redesign or archive it
when it only wins through task-specific hacks, repeatedly hurts hard tasks, adds
complexity with no ablation-proven benefit, or remains dominated by fair
external baselines.

Any promoted CRA learning-rule/config change must rerun at least:

```text
Tier 1 zero/shuffle controls
Tier 2 fixed/delayed/switch learning proof
Tier 3 dopamine/plasticity/trophic ablations
one delayed_cue and one hard_noisy_switching smoke
```

This prevents a tuned setting from silently reintroducing fake learning or
breaking a core mechanism.

### 5. Leakage And Oracle Defense

Before real-ish or real tasks count, add:

```text
future-label audit
lag-leakage sweep
label shuffle
time reversal / phase-randomized controls where appropriate
zero-input and noise-only controls
adapter field audit proving no trading-only fields leak into non-finance tasks
```

If any adapter depends on future values or task-specific shortcuts, the claim is
not paper-ready.

### 6. Mechanism Interpretability

For lifecycle/ecology claims, log and plot:

```text
dopamine traces
delayed-credit maturity counts
readout weight movement
birth/death events
lineage IDs
active/inactive polyps
trophic health
specialist turnover
collapse/recovery dynamics
```

Required sham controls:

```text
random birth/death with same event count
fixed-N with same max pool
active-mask shuffle
lineage ID shuffle
no trophic pressure
no dopamine
no plasticity
```

A lifecycle win is only convincing if it beats these controls on a predeclared
metric.

### 7. Hardware Resource Accounting

Every hardware tier should export:

```text
wall time
simulated biological time
wall/sim ratio
sim.run calls
chunk size
spike count
readback volume if available
buffer extraction time
provenance/report size
cores/chips used if available
SDRAM usage if available
energy if available
performance per active polyp
failure/fallback counters
```

Hardware evidence must always distinguish:

```text
step + host
chunked + host
hybrid
on_chip
continuous
```

No continuous/on-chip claim is allowed until that path is implemented and passes
parity against the chunked reference.

### 8. Memory, Eligibility, Prediction, And Composition Safeguards

Any future claim that CRA has solved forgetting, delayed credit, predictive
context, or compositional reuse must export the mechanism state directly.

For memory/forgetting claims:

```text
fast weight state
slow weight state
structural/calcified weight state
regime labels or context signatures
replay buffer contents or hashes
old-regime reacquisition metrics
no-replay and shuffled-replay controls
```

For delayed-credit claims:

```text
eligibility trace values
trace increment events
trace decay parameters
reward/dopamine binding events
delay-length sweep results
PendingHorizon versus trace comparison
pair-style versus macro eligibility versus triplet-style eligibility comparison
host, hybrid, or native implementation boundary
```

For spike-coding / temporal-code claims:

```text
input spike trains
encoding metadata for rate, latency, burst, population, and temporal interval codes
time-shuffle and rate-only controls
per-polyp spike-timing histograms
decoded readout bins and sparsity
```

For neuron-model robustness claims:

```text
neuron model and parameter manifest
threshold/tau/refractory sweep tables
spike-rate and sparsity bands
runtime/resource impact by model
failure regions documented, not hidden
```

For circuit-motif claims:

```text
reef graph and motif masks
feedforward/feedback/lateral/WTA ablation rows
same-capacity random and monolithic graph controls
per-motif activity before outcome feedback
motif-specific effect sizes
```

For unsupervised representation claims:

```text
preexposure stream manifest
proof that labels/reward are hidden during preexposure
representation state before downstream training
downstream sample-efficiency curves
shuffled-preexposure and no-preexposure controls
```

For predictive/world-model claims:

```text
next-state prediction error
masked-input prediction accuracy
prediction-error-to-learning coupling
feedback/context-path ablations
reward-only versus predictive-learning comparison
```

For compositionality claims:

```text
learned module/subgraph identifiers
module activation/routing traces
held-out A/B/C task-composition splits
from-scratch versus reused-module learning curves
module-shuffle and irrelevant-module controls
evidence that reuse is causal, not post hoc labeling
```

For working-memory/context claims:

```text
context-state traces
reset-memory controls
shuffled-context controls
same-input/different-context task results
delayed context-cue alignment before reward arrives
capacity/interference stressors
multi-slot/keyed-memory ablations
old-context reentry metrics
```

For policy/action-selection claims:

```text
action logits/values or action-selection traces
exploration versus exploitation logs
state-action-consequence records
delayed reward assignment records
bandit/RL/recurrent baseline comparisons
```

For curriculum/environment-generator claims:

```text
task generator seed and configuration manifest
difficulty schedule
held-out generator modes
task-family leakage checks
identical generated task streams for CRA and baselines
```

No mechanism should be promoted if its ablation does not reduce the claimed
benefit.

### 9. Reproducibility Package

Before paper submission, provide:

```text
one-command validation for software tiers
exact Python dependency lock or environment export
artifact manifest with hashes where practical
raw hardware provenance pointers
paper table generated from registry
frozen v1.1 registry snapshot
instructions for reproducing figures
known-failure and limitation notes
```

### 10. Literature And Novelty Mapping

The paper should compare CRA against:

```text
reward-modulated STDP
three-factor Hebbian learning
liquid-state machines / reservoir computing
spiking reinforcement learning
evolving spiking networks
structural plasticity
neuromorphic robotics/control
online adaptive filters and contextual bandits
```

The defensible novelty target is not "nobody has done anything similar." The
stronger and safer target is:

```text
CRA combines local reward-modulated plasticity, delayed-credit handling,
population ecology, lifecycle pressure, domain-adapter validation, strict
controls/ablations, external baselines, and real neuromorphic hardware transfer
inside one auditable evidence ladder.
```

The actual paper must use primary sources for this section.

## Additional Proof Targets Worth Adding

### Tier 5.6: Baseline Hyperparameter Fairness Audit

Purpose:

```text
prove the Tier 5.5 result is not caused by under-tuned baselines
```

Precondition:

```bash
make tier5-5
```

Executable audit:

```bash
make tier5-6
```

Smoke:

```bash
make tier5-6-smoke
```

Tier 5.5 must produce `tier5_5_fairness_contract.json`,
`tier5_5_per_seed.csv`, paired confidence intervals, paired effect sizes,
sample-efficiency metrics, and explicit best/median baseline comparisons before
Tier 5.6 begins. Reviewer-defense baselines that are not implemented in Tier
5.5 must be listed as deferred rather than implied as evidence.

Tier 5.6 has passed and is canonical v1.0 evidence. It kept CRA locked and
retuned only external baselines under a documented candidate budget, exporting
`tier5_6_candidate_budget.csv`, `tier5_6_best_profiles.csv`,
`tier5_6_per_seed.csv`, and `tier5_6_fairness_contract.json`.

Observed result:

```text
990/990 runs completed
32 candidate profiles
48 best/median profile groups
4 surviving target regimes after retuning
```

Pass:

```text
baseline sweep budgets documented
best and median baseline performance reported
CRA has at least one target-regime edge after retuning
CRA has at least one surviving target regime:
  robust versus the tuned external median
  not dominated by the best tuned external candidate
```

Fail:

```text
retuned baselines remove every CRA advantage
CRA wins only against weak/default settings
CRA settings change during the fairness audit
candidate-budget or best-profile artifacts are missing
```

### Tier 5.7: Compact Regression After Tuning

Purpose:

```text
prove the carried-forward CRA setting still passes controls and ablations
```

Status: **passed and canonical v1.1 evidence**.

Observed result:

```text
Tier 1 controls passed
Tier 2 learning proof passed
Tier 3 architecture ablations passed
delayed_cue/hard_noisy_switching smoke matrix passed
```

Pass:

```text
controls stay negative
positive learning still works
mechanism ablation gaps remain
```

### Tier 6.1: Software Lifecycle / Self-Scaling

Purpose:

```text
test whether lifecycle-enabled CRA adds value beyond same-initial fixed-N CRA
```

Status: **passed and canonical v1.2 evidence**.

Observed result:

```text
36/36 runs completed
fixed controls had 0 births and 0 deaths
lifecycle cases produced 75 new-polyp events
event analysis = 74 cleavage, 1 adult birth, 0 deaths
lineage integrity failures = 0
advantage regimes = 2, both hard_noisy_switching
```

Reviewer-safe boundary:

```text
This supports software lifecycle expansion/self-scaling with clean lineage and
hard-switch advantage regimes. It does not prove full adult turnover, hardware
lifecycle, or external-baseline superiority. Tier 6.3 now supplies the separate
sham-control robustness evidence.
```

### Tier 5.9: Macro Eligibility Trace Confirmation

Status:

```text
Tier 5.9a completed as a noncanonical diagnostic failure.
Tier 5.9b residual repair completed as a noncanonical diagnostic failure.
Tier 5.9c v2.1-era recheck completed as a noncanonical diagnostic failure.
The mechanism is parked and not promoted.
```

Purpose:

```text
prove delayed credit is not only a blunt host ledger by comparing PendingHorizon
against auditable macro eligibility traces
```

Observed Tier 5.9a:

```text
108/108 NEST runs completed
feedback timing leakage violations = 0
macro trace active steps = 11520
macro matured updates = 8536
failed gates = delayed_cue nonregression, variable_delay_cue benefit,
trace-ablation specificity
```

Pass:

```text
trace-based credit matches or improves delayed/hard-switch performance, survives delay sweeps, and degrades under trace ablation
```

Reviewer-safe boundary:

```text
The first macro trace is active but not causally specific enough. Normal and
shuffled traces matched on multiple tasks, and replacing the v1.4
PendingHorizon feature damaged delayed_cue. This is negative mechanism evidence,
not a regression of the v1.4 baseline. The Tier 5.9b residual repair preserved
delayed_cue but still failed trace-ablation specificity and slightly regressed
hard_noisy_switching. Tier 5.9c reran the question after v2.1; v2.1 guardrails
remained green, but macro still failed because normal/shuffled/zero/no-macro
paths were indistinguishable on the delayed-credit harness. Any future
macro-credit claim requires a new targeted failure mode, a repaired mechanism,
ablations, and compact regression. It should not be moved to hardware/custom C.
```

### Tier 5.10: Multi-Timescale Memory And Forgetting

Status:

```text
Tier 5.10 completed as a noncanonical diagnostic failure.
The proxy memory-timescale candidate is not promoted.
Output: controlled_test_output/tier5_10_20260428_181322/
Tier 5.10b completed as a noncanonical task-validation pass.
Output: controlled_test_output/tier5_10b_20260428_193639/
Tier 5.10c completed as a noncanonical software mechanism pass.
Output: controlled_test_output/tier5_10c_20260428_201314/
Tier 5.10d completed as a noncanonical internal software-memory pass.
Output: controlled_test_output/tier5_10d_20260428_212229/
Tier 5.10e completed as a noncanonical internal memory-retention pass.
Output: controlled_test_output/tier5_10e_20260428_220316/
Tier 5.10f completed as a noncanonical capacity/interference stress failure.
Output: controlled_test_output/tier5_10f_20260428_224805/
Tier 5.10g completed as baseline-frozen keyed-memory repair evidence.
Output: controlled_test_output/tier5_10g_20260428_232844/
```

Purpose:

```text
test whether CRA retains or rapidly reacquires old regimes rather than overwriting them
```

Pass:

```text
A-B-A and A-B-C-A recurrence tests show faster old-regime reacquisition or better retained accuracy versus current CRA
```

Observed:

```text
99/99 NEST runs completed
feedback leakage violations = 0
candidate failed tail nonregression, recurrence/recovery benefit, and
memory-ablation specificity
overrigid_memory was the strongest CRA ablation
sign_persistence was the strongest external return-phase baseline
```

Reviewer-safe boundary:

```text
The first memory-timescale proxy is negative evidence, not a promoted memory
claim. It also exposed that the first recurrence tasks are not yet strong
enough to defend memory, because a reflexive sign-persistence baseline can solve
the return phase. Tier 5.10b has now hardened the recurrence/context task
surface, but it remains task-validation evidence rather than CRA memory evidence.
```

### Tier 5.10b: Memory-Pressure Task Validation

Status:

```text
Tier 5.10b completed as a noncanonical task-validation pass.
It authorizes Tier 5.10c mechanism testing, not a memory claim.
```

Purpose:

```text
prove the repaired recurrence/context tasks require remembered context before
CRA memory mechanisms are evaluated
```

Observed:

```text
99/99 task/model/seed runs completed
feedback leakage violations = 0
same current input supports opposite labels = True
sign_persistence max accuracy = 0.5333333333333333
oracle context min accuracy = 1.0
stream context memory min accuracy = 1.0
context-memory edge versus sign_persistence min = 0.4666666666666667
shuffled/reset/wrong-memory control edge min = 0.4642857142857143
best standard baseline max accuracy = 0.8154761904761904
```

Reviewer-safe boundary:

```text
Tier 5.10b does not show that CRA remembers anything. It shows the evaluation
surface is now memory-pressure-valid: context matters, wrong context fails, and
simple sign persistence no longer dominates. Because online_perceptron
partially solves hidden_context_recurrence, Tier 5.10c included strong
baselines and did not claim victory merely by beating sign_persistence.
```

### Tier 5.10c: Explicit Context-Memory Mechanism Diagnostic

Status:

```text
Tier 5.10c completed as a noncanonical software mechanism pass.
It authorizes compact regression and internal-memory design, not hardware or
sleep/replay claims.
```

Purpose:

```text
test whether CRA can use explicit context binding on the repaired memory-pressure
tasks, and whether memory shams remove the benefit
```

Observed:

```text
144/144 NEST task/model/seed runs completed
feedback leakage violations = 0
candidate feature-active steps = 303
candidate context-memory updates = 147
candidate all accuracy = 1.0 on all repaired tasks
minimum edge versus v1.4 raw CRA = 0.4666666666666667
minimum edge versus best memory ablation = 0.3555555555555556
minimum edge versus sign_persistence = 0.4666666666666667
minimum edge versus best standard baseline = 0.18452380952380965
```

Reviewer-safe boundary:

```text
This is the first positive memory-mechanism result after the Tier 5.10 failure,
but it is deliberately bounded. The winning feature is an explicit host-side
context-binding scaffold. Reviewers should not read this as native on-chip
memory, sleep/replay, or solved catastrophic forgetting. Tier 5.10d has since
internalized this mechanism and run full compact regression.
```

### Tier 5.10d: Internal Context-Memory Implementation Diagnostic

Status:

```text
Tier 5.10d completed as a noncanonical internal software-memory pass.
Compact regression smoke also passed.
```

Purpose:

```text
test whether the Tier 5.10c scaffold can be moved inside CRA so the organism
receives raw observations and performs context binding internally
```

Observed:

```text
153/153 NEST task/model/seed runs completed
feedback leakage violations = 0 across 5151 checked feedback rows
internal candidate feature-active steps = 303
internal candidate context-memory updates = 147
internal candidate all accuracy = 1.0 on all repaired tasks
external scaffold all accuracy = 1.0 on all repaired tasks
minimum edge versus v1.4 raw CRA = 0.4666666666666667
minimum edge versus external scaffold = 0.0
minimum edge versus best memory ablation = 0.4666666666666667
minimum edge versus sign_persistence = 0.4666666666666667
minimum edge versus best standard baseline = 0.18452380952380965
full compact regression = PASS
```

Reviewer-safe boundary:

```text
This closes the "only works as an external adapter" objection for the repaired
memory-pressure tasks. The mechanism now lives inside Organism and is controlled
by explicit config flags with reset, shuffled, and wrong-memory ablations. It
is still host-side software memory, not native SpiNNaker/on-chip state, not
sleep/replay consolidation, not broad catastrophic-forgetting proof, and not a
general working-memory or AGI claim.
```

### Tier 5.10e: Internal Memory Retention Stressor

Reviewer attack:

```text
The internal memory only works on short, clean context tasks. It may collapse
once gaps are longer, distractors are denser, or regimes recur after delay.
```

Defense evidence:

```text
output = controlled_test_output/tier5_10e_20260428_220316/
status = PASS
backend = NEST
steps = 960
seeds = 42,43,44
tasks = delayed_context_cue, distractor_gap_context, hidden_context_recurrence
expected/observed runs = 153/153
feedback-leakage violations = 0 across 2448 checked feedback rows
internal feature-active steps = 144
internal context-memory updates = 60
internal all accuracy = 1.0 on all retention-stress tasks
minimum edge versus v1.4 raw CRA = 0.33333333333333337
minimum edge versus external scaffold = 0.0
minimum edge versus best memory ablation = 0.33333333333333337
minimum edge versus sign_persistence = 0.33333333333333337
minimum edge versus best standard baseline = 0.33333333333333337
```

Reviewer-safe boundary:

```text
This defends the current internal host-side memory mechanism against the tested
retention stressors. It is not native on-chip memory, not hardware memory
transfer, not sleep/replay consolidation, not capacity-limited memory, and not
broad catastrophic-forgetting proof. Since no retention decay was observed, it
does not justify sleep/replay as a required repair yet.
```

### Tier 5.10f: Memory Capacity / Interference Stressor

Reviewer attack:

```text
The internal memory only works when context capacity is effectively unlimited
and cues do not interfere. It may fail when similar or overlapping contexts
compete, or when an old context returns after intervening regimes.
```

Defense evidence:

```text
output = controlled_test_output/tier5_10f_20260428_224805/
status = FAIL
backend = NEST
steps = 720
seeds = 42,43,44
tasks = intervening_contexts, overlapping_contexts, context_reentry_interference
expected/observed runs = 153/153
feedback-leakage violations = 0 across 1938 checked feedback rows
internal feature-active steps = 114
internal context-memory updates = 121
minimum all accuracy = 0.25
minimum edge versus v1.4 raw CRA = -0.25
minimum edge versus external scaffold = 0.0
minimum edge versus best memory ablation = -0.5
minimum edge versus sign_persistence = -0.25
minimum edge versus best standard baseline = -0.25
```

Reviewer-safe boundary:

```text
This is a clean negative stress result, not a runtime failure. The internal
memory path is active and leakage-free, but the current single-slot binding is
not sufficient for capacity/interference pressure. The v1.5 memory claim is
narrowed to repaired context tasks and retention stress. Tier 5.10g now supplies
the multi-slot/keyed repair gate with reset/shuffle/wrong-key ablations; do not
promote sleep/replay or hardware memory transfer from the 5.10f result alone.
```

### Tier 5.10g: Multi-Slot / Keyed Context-Memory Repair

Reviewer attack:

```text
The v1.5 memory path is only a single-slot scratchpad. It cannot defend
capacity, binding, or interference claims unless keyed slots beat single-slot
memory and slot shams under the exact stressors that broke 5.10f.
```

Defense evidence:

```text
output = controlled_test_output/tier5_10g_20260428_232844/
status = PASS
backend = NEST
steps = 720
seeds = 42,43,44
tasks = intervening_contexts, overlapping_contexts, context_reentry_interference
expected/observed runs = 171/171
feedback-leakage violations = 0 across 2166 checked feedback rows
candidate feature-active steps = 114.0
candidate context-memory updates = 121.0
candidate all accuracy = 1.0 on all three stress tasks
minimum edge versus v1.4 raw CRA = 0.5
minimum edge versus v1.5 single-slot memory = 0.33333333333333337
minimum edge versus oracle-key scaffold = 0.0
minimum edge versus best memory ablation = 0.33333333333333337
minimum edge versus sign_persistence = 0.5
minimum edge versus best standard baseline = 0.5
compact regression after keyed-memory addition = PASS
```

Reviewer-safe boundary:

```text
This repairs the measured Tier 5.10f single-slot capacity/interference failure.
It shows bounded keyed context binding inside Organism on the tested tasks. It
does not show native on-chip memory, hardware memory transfer, sleep/replay
consolidation, compositional skill reuse, module routing, broad catastrophic
forgetting resolution, or general working memory. The oracle-key scaffold is an
upper-bound reference, not the promoted mechanism.
```

### Tier 5.11: Replay / Consolidation

Purpose:

```text
test whether offline replay/consolidation repairs the Tier 5.11a silent-reentry failure without leaking future labels into online evaluation
```

Current evidence:

```text
Tier 5.11a passed as a need diagnostic.
v1.6 no-replay min accuracy = 0.6086956521739131.
unbounded keyed and oracle scaffold min accuracy = 1.0.
decision = replay_or_consolidation_needed.
Tier 5.11b failed the first priority-specific shuffled-control gate.
Tier 5.11c failed the sharper priority-specific shuffled-order gate.
Tier 5.11d passed the broader correct-binding replay/consolidation gate.
candidate replay min all/tail accuracy = 1.0 / 1.0.
candidate replay all/tail gap closure = 1.0 / 1.0.
feedback/replay leakage = 0 / 0.
candidate replay events/consolidations = 1185 / 1185.
minimum candidate tail edge versus wrong-key = 0.5555555555555556.
minimum candidate tail edge versus key-label, priority-only, no-consolidation = 1.0.
compact regression after replay = PASS.
baseline freeze = v1.7.
```

Pass:

```text
correct-binding replay closes the v1.6 versus unbounded-keyed gap
correct-binding replay beats no-replay, wrong-key, key-label-permuted, priority-only, and no-consolidation controls
compact regression still passes
replay logs identify what was replayed and why
```

Reviewer-safe boundary:

```text
Tier 5.11a only proves replay/consolidation has a measured job. Tier 5.11b and
Tier 5.11c block the narrower claim that priority weighting itself is proven.
Tier 5.11d promotes only the broader, host-side correct-binding
replay/consolidation mechanism. It is not biological sleep proof, hardware
replay, native on-chip memory, compositionality, or world modeling.
```

### Tier 5.12a: Predictive Task-Pressure Validation

Purpose:

```text
prove the predictive benchmark is not solvable by current-value reflexes,
sign-persistence, rolling-majority, wrong-horizon leakage, or shuffled targets
before testing a CRA predictive mechanism
```

Observed result:

```text
PASS; 144/144 software cells completed; 0 feedback leakage violations across
10044 checked rows; predictive_memory solved all four tasks at 1.0; max reflex
or sign-persistence accuracy stayed at 0.5649717514124294; max wrong/shuffled
control accuracy stayed at 0.5444444444444444.
```

Reviewer defense:

```text
This is task-validation evidence only. It does not prove CRA predictive coding,
world modeling, language, planning, or hardware prediction. It only shows that
Tier 5.12b/5.12c had a fair predictive-pressure battery to test against.
```

### Tier 5.12b: Predictive Coding / World-Model Mechanism Prototype

Purpose:

```text
test whether internal predictive-context binding improves hard/adaptive behavior beyond reward-only reactivity
```

Observed Tier 5.12b diagnostic:

```text
FAIL; 162/162 NEST cells completed with zero leakage and the internal
predictive-context candidate matched the external scaffold, but wrong-sign
context behaved like an alternate learnable code and the absolute masked-input
accuracy/tail gates failed. This is not a promoted pass.
```

Reviewer defense:

```text
We did not retroactively pass 5.12b. We kept the failure and used it to repair
the sham contract. Stable sign inversion is information-preserving, so it
should be reported as an alternate-code diagnostic rather than treated as an
information-destroying ablation.
```

### Tier 5.12c: Predictive Context Sham-Separation Repair

Purpose:

```text
rerun the internal predictive-context mechanism with shuffled/permuted/no-write
information-destroying shams and wrong-sign reported separately
```

Observed result:

```text
PASS; 171/171 NEST cells completed; 0 leakage violations; candidate
predictive-context writes/active decisions = 570/570; candidate matched the
external scaffold exactly; minimum all/tail accuracy = 0.8444444444444444 /
0.888888888888889; minimum edge vs v1.7 = 0.8444444444444444; minimum edge vs
information-destroying shams = 0.3388888888888889; minimum edge vs shortcut
controls = 0.3; minimum edge vs best selected external baseline =
0.31666666666666665.
```

Reviewer defense:

```text
This supports only bounded host-side visible predictive-context binding. It
does not prove hidden-regime inference, full world modeling, language, planning,
hardware prediction, or v1.8. Promotion still requires compact regression.
```

### Tier 5.13: Compositional Skill Reuse

Purpose:

```text
test whether CRA can reuse learned modules/subgraphs as subroutines for novel
task combinations, rather than learning every new task from scratch
```

Pass:

```text
composed CRA beats from-scratch CRA on sample efficiency or robustness, module
shuffle/irrelevant-module controls hurt performance, and reuse traces identify
which learned substructure was reused
```

Observed result:

```text
status = PASS
output = controlled_test_output/tier5_13_20260429_075539/
matrix cells = 126 / 126
feedback leakage violations = 0
candidate first-heldout accuracy min = 1.0
candidate total heldout accuracy min = 1.0
raw v1.8 first-heldout accuracy = 0.0 on all tasks
combo memorization first-heldout accuracy = 0.0 on all tasks
best module-sham first-heldout accuracy max = 0.2916666666666667
best selected standard-baseline first-heldout accuracy max = 0.8333333333333334
```

Reviewer defense:

```text
Tier 5.13 directly attacks the "collection of reflexes" critique. It uses
held-out skill compositions, same-current-input/opposite-label pressure, module
reset/shuffle/order-shuffle controls, combo memorization, oracle composition,
and selected standard baselines. The result supports only explicit host-side
module-composition scaffolding and authorizes internal composition/routing work;
it does not yet prove native CRA compositionality, module routing, hardware
composition, language, planning, or AGI.
```

### Tier 5.13b: Module Routing / Contextual Gating

Purpose:

```text
test whether CRA can select, suppress, or retrieve the correct learned module for
the current context
```

Pass:

```text
learned routing beats always-on and random-router controls, and routing traces
select the relevant module before outcome feedback
```

Observed result:

```text
status = PASS
output = controlled_test_output/tier5_13b_20260429_121615/
matrix cells = 126 / 126
feedback leakage violations = 0 / 11592 checked rows
candidate first-heldout routing accuracy min = 1.0
candidate heldout routing accuracy min = 1.0
candidate router accuracy min = 1.0
pre-feedback route selections = 276
raw v1.8 first-heldout accuracy = 0.0 on all tasks
CRA router-input bridge first-heldout accuracy = 0.0 on all tasks
best routing-sham first-heldout accuracy max = 0.625
best selected standard-baseline first-heldout accuracy max = 0.5416666666666666
```

Reviewer defense:

```text
Tier 5.13b shows that explicit contextual routing can select the correct
reusable module before outcome feedback under delayed context, distractor, and
reentry pressure. It separates from always-on, random-router, reset, and
context-shuffle shams. The bridge failure is important: the result authorizes
internal CRA routing/gating work but does not prove native CRA routing yet.
```

### Tier 5.13c: Internal Composition / Routing Promotion Gate

Purpose:

```text
test whether composition/routing can live inside CRA's host loop rather than
remaining an external diagnostic scaffold
```

Observed result:

```text
status = PASS
output = controlled_test_output/tier5_13c_20260429_160142/
matrix cells = 243 / 243
feedback leakage violations = 0 / 22941 checked rows
pre-feedback feature selections = 6096
module updates = 192
router updates = 88
composition first-heldout/heldout accuracy min = 1.0
routing first-heldout/heldout/router accuracy min = 1.0
edge versus raw CRA min = 1.0
edge versus best internal sham min = 0.5
full compact regression = PASS
baseline freeze = baselines/CRA_EVIDENCE_BASELINE_v1.9.md
```

Reviewer defense:

```text
Tier 5.13c addresses the "external scaffold" attack. The internal host-side
CRA pathway learns primitive module tables and context-router scores from
arrived feedback, selects routed/composed features before feedback, and loses
when no-write/reset/shuffle/random/always-on controls remove the mechanism.
After a fresh full compact regression, v1.9 freezes this as bounded host-side
software composition/routing evidence. It is still not SpiNNaker hardware
routing, native/custom-C on-chip routing, language, planning, AGI, or
external-baseline superiority.
```

### Tier 5.14: Working Memory / Context Binding

Purpose:

```text
test whether CRA can hold recent context, cue history, active module state, or
pending subgoal information across time
```

Pass:

```text
working-memory CRA beats current CRA on same-input/different-context tasks, and
reset-memory plus shuffled-context controls remove the benefit
```

Observed:

```text
status = PASS
output = controlled_test_output/tier5_14_20260429_165409/
memory/context-binding subsuite = PASS
module-state/routing subsuite = PASS
context-memory task accuracy = 1.0 on all three memory-pressure tasks
routing first-heldout/heldout/router accuracy = 1.0 on all three routing tasks
minimum edge vs best memory sham = 0.5
minimum edge vs sign persistence = 0.5
minimum edge vs routing-off CRA = 1.0
minimum edge vs best routing sham = 0.5
```

Reviewer boundary:

```text
software diagnostic only
host-side working-memory/context-binding only
not hardware/on-chip working memory
not language
not planning
not AGI
not a v2.0 freeze by itself
```

Promotion note: Tier 5.14b is only needed if v2.0 will be frozen or the paper
will make working-memory/context-binding a standalone formal claim. Otherwise
Tier 5.14 is sufficient diagnostic coverage over v1.9.

### Tier 5.15: Spike Encoding / Temporal Code Suite

Status: **passed as noncanonical software temporal-code diagnostic evidence**.

Purpose:

```text
test whether CRA can learn from spike timing, latency, burst, population, or
temporal interval codes rather than only scalar/rate-like input
```

Latest evidence:

```text
controlled_test_output/tier5_15_20260429_135924/
expected_runs = observed_runs = 540
spike_trace_artifacts = 60
encoding_metadata_artifacts = 60
good_temporal_row_count = 9
nonfinance_good_temporal_row_count = 3
time_shuffle_loss_count = 9
rate_only_loss_count = 9
```

Reviewer-defense interpretation:

```text
This answers the basic "spikes are only transport" attack for the software
diagnostic path: timing/interval/burst structure is causally useful when
rate-only and time-shuffled controls are held constant. It does not answer
hardware/on-chip temporal coding, neuron-model robustness, or hard-switch
temporal superiority.
```

### Tier 5.16: Neuron Model / Parameter Sensitivity

Status: **passed as noncanonical NEST neuron-parameter sensitivity evidence**.

Purpose:

```text
test whether CRA's claims survive a reasonable LIF parameter band and optional
adaptive/Izhikevich-style software checks
```

Latest evidence:

```text
controlled_test_output/tier5_16_20260429_142647/
expected_runs = observed_runs = 66
aggregate_cells = 33
functional_cell_count = 33
functional_cell_fraction = 1.0
default_min_tail_accuracy = 0.8
collapse_count = 0
parameter_propagation_failures = 0
sim_run_failures = 0
summary_read_failures = 0
synthetic_fallbacks = 0
response_probe_monotonic_fraction = 1.0
```

Reviewer-defense interpretation:

```text
This answers the first fragile-LIF-parameter attack for the NEST software path:
the current CRA result does not depend on one exact threshold/tau/refractory/cm
setting, and parameter propagation is auditable. It does not answer
SpiNNaker/custom-C/on-chip neuron robustness or adaptive/Izhikevich robustness.
```

Pass:

```text
main claims remain functional across the predeclared parameter band, and failure
regions are documented rather than hidden
```

### Tier 5.17: Pre-Reward Representation Formation

Status: **failed / not promoted**.

Purpose:

```text
test whether reward-free stream exposure builds internal structure that improves
later delayed or nonstationary learning
```

Observed result:

```text
no-label/no-reward harness worked, but the strict scaffold failed probe,
sham-separation, and sample-efficiency promotion gates
```

Pass for a future Tier 5.17c repair:

```text
unlabeled preexposure improves downstream sample efficiency or stability, while
shuffled/no-preexposure/current-input controls remove the benefit
```

### Tier 5.18: Self-Evaluation / Metacognitive Monitoring

Status: **passed as noncanonical software diagnostic evidence** at
`controlled_test_output/tier5_18_20260429_213002/`.

Purpose:

```text
test whether CRA can estimate confidence, uncertainty, novelty, or likely failure
before outcome feedback and use that signal without leakage
```

Observed:

```text
150/150 rows completed
outcome_leakage_runs = 0
pre_feedback_monitor_failures = 0
candidate_min_primary_error_auroc = 0.986637
candidate_min_hazard_detection_auroc = 0.999055
candidate_max_brier_primary_correct = 0.0604305
candidate_max_ece_primary_correct = 0.152803
candidate_min_bad_action_avoidance = 0.763434
min_accuracy_edge_vs_best_non_oracle = 0.250463
```

Pass:

```text
monitor-enabled CRA is better calibrated than random/trivial confidence controls,
pre-feedback error/OOD predictions beat shams, and monitor-triggered adaptation
or abstention improves at least one predeclared task. Tier 5.18c later passed
the compact regression gate and freezes bounded v2.1 reliability-monitoring
evidence.
```

Reviewer-safe boundary:

```text
This supports operational pre-feedback reliability monitoring in software only.
It is not consciousness, self-awareness, introspection, hardware monitoring,
language, planning, AGI, or external-baseline superiority.
```

### Tier 5.18c: Self-Evaluation Compact Regression

Status: **passed and freezes v2.1** at
`controlled_test_output/tier5_18c_20260429_221045/`.

Observed:

```text
v2.0 compact regression gate remains green = pass
Tier 5.18 self-evaluation guardrail remains green = pass
children_passed = 2/2
criteria_passed = 4/4
```

Reviewer-safe boundary:

```text
v2.1 is bounded host-side software reliability-monitoring evidence only.
It is not consciousness, self-awareness, introspection, hardware/custom-C
self-monitoring, language, planning, AGI, or external-baseline superiority.
```

### Tier 4.20a: v2.1 Hardware-Transfer Readiness Audit

Status: **passed as engineering audit evidence** at
`controlled_test_output/tier4_20a_20260429_195403/`.

Reviewer-safe use:

```text
This is a transfer matrix, not a hardware run.
It classifies which v2.1 mechanisms can be probed through chunked host replay
and which require future hybrid/custom-C/on-chip work.
It explicitly excludes macro eligibility after the failed Tier 5.9c recheck.
```

Reviewer-safe boundary:

```text
Do not cite Tier 4.20a as SpiNNaker evidence, v2.1 hardware transfer, or
on-chip autonomy. The first v2.1 hardware claim starts with Tier 4.20b, which
has now returned real pyNN.spiNNaker artifacts with real spike readback, zero
fallback, and zero run/readback failures.
```

### Tier 4.20b: v2.1 One-Seed Chunked Hardware Probe

Status: **passed as one-seed bridge/transport hardware evidence** at
`controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass/`
and
`controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass_ingested/`.

Reviewer-safe use:

```text
This is the first v2.1 bridge/transport hardware probe. It uses seed 42,
delayed_cue plus hard_noisy_switching, N=8, 1200 steps,
chunk_size_steps=50, host learning, macro eligibility disabled, and the
in-process Tier 4.16 chunked-host child runner.
```

Reviewer-safe boundary:

```text
Do cite Tier 4.20b only as one-seed v2.1 chunked-host bridge/transport
evidence. Do not cite it as full native/on-chip v2.1 memory, replay, routing,
self-evaluation, custom C, language, planning, AGI, repeatability, or macro
eligibility evidence.
```

### Tier 6.3: Lifecycle Sham-Control Suite

Purpose:

```text
prove lifecycle/self-scaling value is not just random replacement, larger capacity, event count, or bookkeeping
```

Status: **passed and canonical v1.3 evidence**.

Observed result:

```text
36/36 actual runs completed
intact lifecycle events = 26 non-handoff events
fixed capacity-control lifecycle events = 0
actual-run lineage failures = 0
aggregate extinctions = 0
performance-sham wins = 10/10
fixed max-pool wins = 2/2
event-count replay wins = 2/2
lineage-ID shuffle detections = 6/6
```

Reviewer-safe boundary:

```text
This supports software sham-control robustness for the lifecycle/self-scaling
claim. Replay/shuffle controls are audit artifacts, not independent learners. It
does not prove hardware lifecycle, native on-chip lifecycle, full adult turnover,
external-baseline superiority, compositionality, or world modeling.
```

### Tier 6.4: Circuit Motif Causality

Status: **passed and canonical v1.4 evidence**.

Purpose:

```text
prove feedforward, feedback/recurrent, lateral-inhibition, mutual-inhibition/WTA,
and other implemented reef motifs causally affect behavior
```

Pass:

```text
predeclared motif ablations cause predicted losses, same-capacity random or
monolithic controls do not explain the effect, and motif activity is logged before
outcome feedback
```

Observed canonical result:

```text
48/48 actual runs
2/2 intact motif-diverse aggregates
1920 pre-reward motif-active steps
4/8 motif-ablation losses
0/2 motif-label shuffle losses
0/4 random/monolithic dominations
0 lineage-integrity failures
```

Boundary:

```text
software motif structure/edge-role evidence only;
not hardware motif execution, custom-C/on-chip learning, compositionality,
world-modeling, real-world usefulness, or universal baseline superiority
```

### Tier 7.3: Holdout Task Challenge

Purpose:

```text
prove CRA is not overfit to hand-designed tasks
```

Pass:

```text
frozen CRA config performs competitively on at least one task family not used during tuning
```

### Tier 7.4: Delayed-Reward Policy / Action Selection

Purpose:

```text
test causal state -> action -> consequence learning beyond prediction/sign tasks
```

Pass:

```text
CRA policy layer improves reward or regret versus current prediction-style CRA,
with fair bandit/RL/recurrent baselines and auditable action traces
```

### Tier 7.5: Curriculum / Environment Generator

Purpose:

```text
test whether CRA improves across generated task families without hand-tuning each
task
```

Pass:

```text
CRA improves across generated families, remains useful on held-out generator
modes, and baselines receive the same generated streams
```

### Tier 7.6: Long-Horizon Planning / Subgoal Control

Purpose:

```text
test whether CRA can pursue delayed outcomes through bounded intermediate
subgoals rather than only one-step reactions
```

Pass:

```text
subgoal-enabled CRA beats reactive/no-subgoal CRA on held-out multi-step tasks,
subgoal ablations hurt, planning/RL baselines are reported fairly, and no future
reward leakage is detected
```

### Tier 0.9: Ongoing Reproduction Package

Purpose:

```text
start reproduction hygiene before the final paper capsule
```

Pass:

```text
fresh checkout can rerun software validation, regenerate registry/table/audit,
and map hardware outputs back into canonical evidence through documented ingest
instructions
```

### Tier 8.4: Independent Reproduction Capsule

Purpose:

```text
make the paper reproducible outside this working session
```

Pass:

```text
fresh checkout plus documented environment reproduces the software registry and paper figures
```

## Final Reviewer-Defense Gate

Before writing the paper, answer these in one table:

```text
What exactly did CRA beat?
What exactly beat CRA?
Where did CRA fail?
Which mechanisms caused the useful behavior?
Which claims are hardware-backed?
Which claims are software-only?
Which claims are still future work?
What would falsify the organism/ecology claim?
```

If any answer is vague, the paper is not ready.

## Tier 5.17 Pre-Reward Representation Defense Status

Current status: **failed / not promoted; Tier 5.17b failure analysis passed**.

Reviewer attack addressed:

> "Is CRA forming useful internal structure before reward, or only reacting after labels/reward arrive?"

What is now covered:

- a no-label/no-reward exposure harness exists
- non-oracle rows show zero hidden-label leakage
- exposure shows zero reward visibility and zero raw dopamine
- frozen/snapshotted representations are probed only after exposure
- no-state, time-shuffled, temporal-destroyed, input-only, history-only,
  random-projection, random-untrained, and oracle controls are exported

What failed:

- the strict no-history-input scaffold did not meet all probe, sham-separation,
  and downstream sample-efficiency promotion gates

What Tier 5.17b adds:

- the failure is now classified rather than hand-waved
- `ambiguous_reentry_context` is retained as a positive subcase
- `latent_cluster_sequence` is too input-encoded/easy
- `temporal_motif_sequence` is dominated by fixed-history controls
- the repair is routed to intrinsic predictive / MI-style preexposure
- Tier 5.9 delayed-credit work is not the next move unless future pre-reward
  structure exists but downstream reward cannot credit or preserve it

Reviewer-safe wording:

> Tier 5.17 currently shows an auditable pre-reward representation test harness,
> and Tier 5.17b explains the failure mode. It is not a promoted reward-free
> representation-learning mechanism.

Do not claim:

- unsupervised concept learning
- reward-free representation learning
- hardware/on-chip representation formation
- a v2.0 freeze

Next defense move: Tier 5.17c intrinsic predictive / MI-style preexposure with
sharper masked-channel, temporal-continuation, and same-visible-input/different
latent-state pressure where current-input/history controls cannot explain the
result.

Tier 5.17c outcome: **failed / not promoted**.

What it added:

- a concrete intrinsic predictive preexposure harness
- zero label leakage, zero reward visibility, and zero dopamine during
  non-oracle preexposure
- held-out episode probes to reduce time-index memorization
- no-preexposure, time-shuffled, target-shuffled, wrong-domain, fixed-history,
  random-projection, reservoir, STDP-only, and oracle controls

What blocks the claim:

- target-shuffled and wrong-domain controls did not reliably lose
- STDP-only was not cleanly separated
- candidate did not beat the best non-oracle control
- worst-case held-out episode probe accuracy was too low

Reviewer-safe wording:

> Intrinsic predictive preexposure remains a tested but non-promoted repair.
> CRA has not yet earned a reward-free representation-learning claim.

Next defense choice completed:

- Tier 5.17d ran the targeted sham/binding repair
- Tier 5.17e ran the compact promotion/regression gate and froze v2.0
- Tier 5.18 and Tier 5.18c ran the self-evaluation diagnostic plus compact
  regression gate and froze bounded v2.1 while keeping the broad reward-free
  representation claim narrowed

Tier 5.17d outcome: **passed as bounded predictive-binding evidence**.

What it adds:

- held-out ambiguous episode probes after visible cues fade
- a pre-target-update representation rule so intrinsic targets affect only
  future state, not same-step probes
- target-shuffled, wrong-domain, fixed-history, reservoir, STDP-only, and best
  non-oracle controls
- zero label leakage, zero reward visibility, and zero dopamine during
  preexposure

Reviewer-safe wording:

> Under tested cross-modal and reentry binding tasks, CRA-style predictive
> sensory binding can form useful pre-reward structure that survives
> target-shuffle, wrong-domain, history, reservoir, and STDP-only controls.

Do not claim:

- general unsupervised concept learning
- hardware/on-chip representation formation
- full world modeling
- language or planning
- v2.0 freeze without compact regression

Tier 5.17e outcome: **passed and froze v2.0**.

What it adds:

- v1.8 compact regression stayed green
- v1.9 composition/routing stayed green
- Tier 5.14 working-memory/context binding stayed green
- Tier 5.17d predictive-binding stayed green
- `baselines/CRA_EVIDENCE_BASELINE_v2.0.md` records the frozen claim boundary

Reviewer-safe wording:

> CRA has a bounded host-side software predictive-binding baseline: under tested
> cross-modal and reentry binding tasks, predictive sensory binding can form
> useful pre-reward structure while prior compact, composition/routing, and
> working-memory/context guardrails remain intact.

Do not claim:

- general unsupervised concept learning
- hardware/on-chip representation learning
- full world modeling
- language, planning, or AGI
- external-baseline superiority
