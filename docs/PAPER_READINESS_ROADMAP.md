# CRA Paper-Readiness Roadmap

Last updated: 2026-05-06

This document is the working plan from the current evidence state to a serious
paper-ready CRA claim. It is deliberately stricter than a speculative roadmap. The goal
is to know exactly what we are trying to prove, what would count as a pass, what
would count as a fail, and where the project would need to stop, debug, narrow
its claim, or change direction.

## North Star

The goal is not merely to show that CRA can produce a good curve on one toy
task. The paper-ready goal is:

```text
CRA is a useful, functional, neuromorphic organism-style learning architecture
whose core mechanisms provide measurable value under delayed reward,
nonstationarity, noise, domain transfer, and hardware constraints.
```

The word "paradigm shifting" has to be earned. In this repo, it would mean:

```text
1. CRA learns without global backpropagation on controlled tasks.
2. CRA does not fake learning on controls.
3. CRA mechanisms matter: dopamine, plasticity, ecology, lifecycle pressure.
4. CRA transfers across task adapters, not just trading-shaped inputs.
5. CRA survives neuromorphic backend movement and real SpiNNaker execution.
6. CRA is competitive against simpler learners where its design should matter.
7. CRA's organism/ecology features add value beyond fixed-N model behavior.
8. CRA can move toward lower-host-dependence hardware execution without losing behavior.
9. CRA resists catastrophic forgetting when regimes recur rather than only adapting once.
10. CRA can graduate from host-led delayed-credit bookkeeping toward hybrid or native eligibility traces.
11. CRA can move beyond reactive reward chasing toward predictive/context modeling where that improves hard tasks.
12. CRA can reuse learned structures compositionally rather than relearning every new task from scratch.
13. CRA can monitor uncertainty, novelty, or likely failure before outcome feedback and use that signal constructively.
14. CRA can pursue bounded multi-step objectives through subgoal structure rather than only one-step reactions.
```

If we cannot prove items 6 and 7 on meaningful tasks, the architecture may still
be interesting, but the paper claim must be narrowed. If item 12 fails, avoid
claiming reusable/substrate-level intelligence. If item 13 fails, avoid
metacognitive/self-monitoring language. If item 14 fails, avoid planning or
subgoal-control language and describe CRA as an adaptive local-learning organism
rather than a deliberative planner.

## Capability Ladder

Use this ladder to prevent claim jumps. A higher level is not considered earned
until its tier passes with controls, ablations, baselines, and artifacts.

```text
Level 0: Reflex adaptation
  Learns local cue/action or signal/prediction relationships.

Level 1: Delayed credit
  Handles delayed outcomes without fake same-step reward leakage.

Level 2: Nonstationary adaptation
  Recovers when rules/regimes change.

Level 3: Recurrent-regime memory
  Retains or rapidly reacquires old regimes instead of relearning from scratch.

Level 4: Lifecycle/self-scaling
  Uses ecology, birth/death, and active population control for measurable value.

Level 5: Compositional reuse
  Reuses learned modules/subgraphs as subroutines for held-out combinations.

Level 6: Working memory and contextual control
  Maintains task/regime/subgoal context so identical inputs can drive different actions.

Level 7: Predictive/context modeling
  Builds useful next-state/context predictions that improve adaptation or transfer.

Level 8: Policy/action selection
  Learns action choices in a causal state -> action -> consequence loop.

Level 9: Self-evaluation / metacognitive monitoring
  Estimates confidence, uncertainty, novelty, or likely failure before feedback.

Level 10: Long-horizon planning / subgoal control
  Uses bounded subgoals or action chains to pursue delayed outcomes.

Level 11: Hybrid/on-chip autonomy
  Reduces host dependence without losing the verified chunked-reference behavior.

Level 12: Open-ended curriculum learning
  Improves across generated task families without hand-tuning each task.
```

The current evidence supports only the lower part of this ladder. Higher levels
are planned research targets, not completed evidence.

SNN-native coverage boundary:

```text
Current evidence proves CRA can run and learn through spiking backends, including
real SpiNNaker capsules. `CRA_NATIVE_RUNTIME_BASELINE_v0.1` freezes a bounded
four-core MCPL distributed scaffold proven across three seeds. It does not yet
prove multi-chip scaling, speedup, full v2.1 mechanism transfer, or continuous
host-free operation. Tiers 5.15, 5.16, 5.17, and 6.4 exist to test software
mechanism claims directly before paper-lock.
```

Capability-monitoring boundary:

```text
Current evidence now includes a passed Tier 5.18 software
self-evaluation/metacognitive-monitoring diagnostic and a passed Tier 5.18c
promotion gate freezing bounded v2.1 reliability-monitoring evidence. It does
not prove consciousness, introspection, hardware self-monitoring, language,
planning, or AGI. Long-horizon planning/subgoal control remains unproven; Tier
7.6 is the explicit future gate for that reviewer attack.
```

## Current State

Already established:

```text
Tier 1 controls: passed
Tier 2 learning proof: passed
Tier 3 ablations: passed
Tier 4.10 scaling stability: passed
Tier 4.10b hard scaling: passed through stability/recovery/correlation metrics
Tier 4.11 domain transfer: passed
Tier 4.12 NEST/Brian2 backend parity: passed
Tier 4.13 minimal SpiNNaker hardware capsule: passed
Tier 4.14 hardware runtime characterization: passed
Tier 4.15 minimal hardware repeat across seeds 42,43,44: passed
Tier 4.28a four-core MCPL repeatability (native runtime v0.1): passed
Tier 4.28b delayed-cue four-core MCPL probe: passed (38/38; weight=-32769)
Tier 4.28c delayed-cue three-seed repeatability: passed (38/38 × 3 seeds; weight=-32769)
Tier 4.28d hard noisy switching four-core MCPL probe: passed (38/38 × 3 seeds; weight=34208; bias=-1440; zero variance)
Tier 4.28e native failure-envelope report: complete (Point A PASS 38/38; Point B boundary confirmed 64/78 events; Point C PASS 38/38)
Tier 5.1 external baselines: mixed, useful but not universal
Tier 5.2 learning curves: sobering, long-run edge did not strengthen
Tier 5.3 failure analysis: identified delayed_lr_0_20
Tier 5.4 delayed-credit confirmation: passed median criteria, not best-baseline hard-switch superiority
Tier 4.17b local chunked parity: passed
Tier 4.16a repaired delayed_cue hardware repeat across seeds 42,43,44: passed
Tier 4.16b hard_noisy_switching first attempt: failed learning gate, clean hardware path
Tier 4.16b repaired seed-44 hardware probe: passed narrowly, noncanonical one-seed probe
Tier 4.16b repaired three-seed hardware repeat: passed, canonical hard-switch transfer
Tier 4.18a v0.7 chunked hardware runtime baseline: passed
Tier 4.20a v2.1 hardware-transfer readiness audit: passed (engineering plan, not hardware evidence)
Tier 4.20b v2.1 one-seed chunked hardware probe: passed (bridge/transport evidence)
Tier 4.20c v2.1 three-seed chunked hardware repeat: passed (bridge/transport repeatability)
Tier 5.19c fading-memory compact-regression gate: passed and froze v2.2 (software only)
Tier 4.21a keyed context-memory hardware bridge probe: passed (one-seed bridge evidence)
Tier 4.22a custom runtime contract: passed (engineering contract)
Tier 4.22a0 SpiNNaker-constrained local preflight: passed (transfer-risk reduction)
Tier 4.22b continuous transport scaffold: passed (hardware transport, learning disabled)
Tier 4.22c persistent custom-C state scaffold: passed (local state ownership)
Tier 4.22d reward/plasticity runtime scaffold: passed (local C scaffold)
Tier 4.22e local continuous-learning parity: passed (local fixed-point parity)
Tier 4.22f0 custom runtime scale-readiness audit: passed (scale blockers identified)
Tier 4.22g event-indexed active-trace runtime: passed (local optimization)
Tier 4.22h compact readback/build readiness: passed (30/30 static checks)
Tier 4.22i custom runtime board round-trip: passed (build/load/CMD_READ_STATE)
Tier 4.22j minimal custom-runtime closed-loop learning: passed (one pending horizon)
Tier 4.22l tiny custom-runtime learning parity: passed (four-update fixed-point exact match)
Tier 4.22m minimal custom-runtime task micro-loop: passed (12-event fixed-pattern)
Tier 4.22n tiny delayed-cue custom-runtime micro-task: passed (12-event delayed-cue)
Tier 4.22o tiny noisy-switching custom-runtime micro-task: passed (14-event switch)
Tier 4.22p tiny A-B-A reentry custom-runtime micro-task: passed (30-event reentry)
Tier 4.22q tiny integrated v2 bridge custom-runtime smoke: passed (host-v2 + chip loop)
Tier 4.22r tiny native context-state custom-runtime smoke: passed (native keyed context)
Tier 4.22s tiny native route-state custom-runtime smoke: passed (native keyed route)
Tier 4.22t tiny native keyed route-state custom-runtime smoke: passed (keyed route slots)
Tier 4.22u native memory-route state custom-runtime smoke: passed (keyed memory + route)
Tier 4.22v native memory-route reentry/composition custom-runtime smoke: passed (48-event reentry)
Tier 4.22w native decoupled memory-route composition custom-runtime smoke: passed (decoupled keys)
Tier 4.22x compact v2 bridge decoupled smoke: passed (host-v2 decoupled bridge)
Tier 4.23a continuous fixed-point local reference: passed (21/21)
Tier 4.23b continuous custom-runtime host tests: passed (28/28)
Tier 4.23c continuous single-core hardware smoke: passed (22/22 + 15/15 ingest)
Tier 4.24 resource characterization: passed (16/16)
Tier 4.24b EBRAINS build/size pass: passed (10/10 + 11/11 ingest)
Tier 4.25B two-core state/learning split smoke: passed (23/23)
Tier 4.25C two-core state/learning split repeatability: passed (23/23 × 3 seeds)
Tier 4.26 four-core distributed context/route/memory/learning smoke: passed (30/30)
Tier 4.27a four-core SDP characterization: passed (38/38)
Tier 4.27d MCPL compile-time feasibility: passed (local)
Tier 4.27e two-core MCPL round-trip smoke: passed (local)
Tier 4.27f three-state-core MCPL lookup smoke: passed (local)
Tier 4.27g SDP-vs-MCPL comparison: passed (local)
Tier 4.28a four-core MCPL repeatability: passed (38/38 × 3 seeds; freezes native runtime v0.1)
Tier 4.28b delayed-cue four-core MCPL probe: passed (38/38; weight=-32769)
Tier 4.28c delayed-cue three-seed repeatability: passed (38/38 × 3 seeds; weight=-32769)
Tier 4.28d hard noisy switching four-core MCPL probe: passed (38/38 × 3 seeds; weight=34208; bias=-1440; zero variance)
Tier 4.28e native failure-envelope report: complete (local sweep 30 configs; predicted schedule_overflow at >64 events; Point A PASS 38/38; Point B boundary confirmed 64/78 events; Point C PASS 38/38)
Tier 5.5 expanded baseline/fairness suite: passed
Tier 5.6 tuned-baseline fairness audit: passed
Tier 5.7 compact regression guardrail: passed
Tier 5.12a predictive task-pressure validation: passed
Tier 5.12c predictive-context sham repair: passed
Tier 5.12d predictive-context compact regression: passed (freezes v1.8)
Tier 6.1 software lifecycle/self-scaling: passed
Tier 6.3 lifecycle sham controls: passed
Tier 6.4 circuit-motif causality: passed
```

Tier 4.16b diagnostic and pass frontier:

```text
Tier 4.16b first hard_noisy_switching attempt returned FAIL
seeds = 42,43,44
steps = 1200
runtime_mode = chunked
learning_location = host
chunk_size_steps = 25
hardware path = clean: zero fallback/failures, real spike readback
learning gate = failed: worst-seed tail accuracy 0.47619047619047616 < 0.5
superseded Tier 4.16b-debug classification = chunked_host_bridge_learning_failure
aligned bridge-repair classification = hardware_transfer_or_timing_failure
direct step-vs-chunked replay tail delta = 0.0
full step CRA tail min = 0.5476190476190477
direct chunked host tail min = 0.5238095238095238
hardware tail min = 0.47619047619047616
repaired seed-44 hardware tail accuracy = 0.5238095238095238
repaired seed-44 tail events = 22 / 42 correct
repaired seed-44 real spike readback = 94707
repaired 3-seed hard-switch tail accuracy mean = 0.5476190476190476
repaired 3-seed hard-switch tail accuracy min = 0.5238095238095238
repaired 3-seed hard-switch real spike readback min = 94707
```

Tier 4.16 now has two narrow repaired hardware-transfer passes: Tier 4.16a
for `delayed_cue` and Tier 4.16b for `hard_noisy_switching`, both across seeds
`42`, `43`, and `44` under `chunked + host`. Freeze the post-4.16b state as
`baselines/CRA_EVIDENCE_BASELINE_v0.7.*`. This still does not prove hardware
scaling, lifecycle/self-scaling, native on-chip dopamine/eligibility, or
external-baseline superiority.

## Evidence Standards

Every future tier must export:

```text
JSON manifest
CSV summary
per-seed/task CSV where relevant
Markdown findings report
PNG plots
exact pass/fail criteria
claim boundary
artifact paths
runtime/provenance where hardware is involved
```

Every future tier must answer:

```text
What claim does this support?
What claim does this not support?
What would make us stop?
What is the next tier only if this passes?
```

No result should be paper-cited unless it is either canonical or explicitly named
as a noncanonical diagnostic/probe with its boundary.

## Roadmap Change Control


Evidence categories:

```text
canonical registry evidence = listed in controlled_test_output/STUDY_REGISTRY.json and paper table eligible
baseline-frozen mechanism evidence = passed mechanism gate + compact regression + frozen vX.Y baseline lock, but not necessarily registry-canonical
noncanonical diagnostic evidence = useful diagnostic answer, not a new frozen baseline by itself
failed/parked diagnostic evidence = clean negative evidence retained for audit and anti-p-hacking
hardware prepare/probe evidence = run package or one-off probe until reviewed and promoted
```

`Noncanonical` means audit-relevant but not a formal registry/paper-table claim by itself. v1.6, v1.7, and v1.9 are baseline-frozen mechanism evidence even though their source experiment bundles are not all canonical registry entries.


This plan is allowed to move as evidence arrives. It is not allowed to quietly
rewrite history.

Rules:

```text
future tiers may be reordered when earlier results expose a better path
completed tiers keep their original pass/fail status and artifact bundle
failed tiers remain in the registry or documented as noncanonical diagnostics
new architecture ideas enter as planned tiers with explicit gates
exploratory feature tweaks use focused diagnostics, not the full suite
candidate mechanisms require targeted head-to-heads against the frozen baseline
promoted mechanisms require compact control/ablation regression before becoming baseline
paper-lock mechanisms require the full final matrix against external baselines
```

The practical meaning is:

```text
debug before surgery
add one major mechanism at a time
ablate every new mechanism
only promote mechanisms that survive controls, baselines, and repeatability
```

Regression policy:

```text
Exploratory tweak:
  run the smallest diagnostic that can falsify the idea
  do not rewrite baseline claims

Candidate mechanism:
  compare against v0.7 on the tasks it is supposed to improve
  include direct ablation of the new mechanism
  report per-seed deltas and variance

Promoted mechanism:
  rerun compact Tier 1/Tier 2/Tier 3 regression
  rerun focused delayed_cue and hard_noisy_switching smokes
  freeze a new baseline only if controls remain clean
  test combinations only after single-feature wins are established
  keep a combination only if A+B beats or complements A alone and B alone

Paper-lock mechanism:
  rerun expanded baselines, holdout tasks, and final hardware subset
  report failures and noncanonical diagnostics, not only wins
```

Strategic mechanism policy:

```text
Some mechanisms are likely necessary for the long-term substrate claim:
multi-timescale memory, replay/consolidation, macro/native eligibility,
predictive/context modeling, compositional reuse, lifecycle/self-scaling, and
hybrid/on-chip execution.

Necessary eventually does not mean a first implementation is automatically good.
Each mechanism gets a fair development cycle:
  prototype
  instrument
  targeted test
  bounded debug
  ablation/control
  promote, redesign, or archive

Debug when traces show an implementation bug, task/metric mismatch, or a small
repair would make the test fair.

Stop and redesign/archive when a mechanism only wins through task-specific
hacks, repeatedly hurts hard tasks, adds complexity with no ablation-proven
benefit, or remains dominated by external baselines after fair tuning.
```

## Reproduction Hygiene Starts Now

Do not wait until the final paper to make the project rerunnable. Tier 8.4 is
the final independent reproduction capsule, but the minimum reproduction
scaffold should be maintained continuously.

### Tier 0.9: Ongoing Reproduction Package

Required before paper-lock work:

```text
one command to rerun software validation
one command to regenerate registry, paper table, and audit
environment lock or documented dependency manifest
artifact hash/manifest file for canonical evidence
clear EBRAINS/JobManager ingest instructions for hardware-only runs
known hardware-only steps separated from software reproduction
```

Pass:

```text
fresh checkout can rerun software checks and regenerate paper-facing tables
canonical artifact paths and hashes are auditable
hardware ingest instructions are explicit enough for an external collaborator
```

Fail:

```text
paper figures require hidden local state
artifact identities cannot be verified
hardware outputs cannot be mapped back into canonical registry entries
```

## Reviewer-Defense Standards

The detailed reviewer-defense checklist lives in `docs/REVIEWER_DEFENSE_PLAN.md`.
Every paper-critical future tier must now include the following safeguards:

```text
predeclared pass/fail criteria before final matrices
mean, median, std, min/max, and confidence intervals where practical
per-seed tables and paired deltas versus baselines
effect size versus the strongest baseline, not just the median baseline
baseline fairness contract and comparable unsupported speculationrparameter budget
compact Tier 1/Tier 2/Tier 3 regression after promoted CRA tuning changes
leakage/oracle checks for every task adapter
mechanism traces for dopamine, delayed credit, trophic health, lifecycle, and lineage
memory traces for fast/slow/structural weights, replay events, and regime recurrence
eligibility traces for host macro-credit, hybrid credit, and any native C runtime credit
prediction-error traces for predictive-coding/world-model variants
composition traces for reused modules, subroutine gates, skill routing, and module-shuffle controls
hardware resource accounting: wall time, sim time, spike/readback volume, provenance, cores/SDRAM/energy if available
retained failures and noncanonical diagnostics, not silent deletion
literature/novelty mapping against reward-modulated STDP, reservoir computing, evolving SNNs, structural plasticity, and spiking RL
```

The paper is not ready until the final evidence table can answer:

```text
What did CRA beat?
What beat CRA?
Where did CRA fail?
Which mechanisms caused the useful behavior?
Which claims are hardware-backed versus software-only?
Which claims remain future work?
```

## Make-Or-Break Criteria

These are the points where the project changes direction.

### Make

CRA becomes paper-interesting if it shows:

```text
repeatable learning on controlled tasks
negative controls stay negative
mechanisms matter under ablation
hardware transfer works on at least delayed/adaptive tasks
self-scaling/lifecycle improves something measurable
real-ish tasks show at least one defensible advantage regime
baselines do not dominate CRA everywhere
```

Useful advantage does not have to mean best accuracy on every task. It can mean:

```text
faster recovery after rule switches
lower seed variance
better delayed-credit learning
less collapse under noise
better long-run adaptation
lower catastrophic forgetting
faster reacquisition when an old regime returns
stronger performance as reward delay lengthens
better prediction-error calibration before action/reward
better performance per active polyp
graceful degradation under hardware/runtime constraints
```

### Break

CRA is not paper-ready as a strong new architecture if:

```text
controls show false learning
ablation gaps disappear under stronger tests
external baselines dominate on all hard/adaptive/real-ish tasks
self-scaling adds no value or corrupts lineage/state
hardware transfer works only for fixed-pattern/easy tasks
real task adapters collapse or require task-specific hacks
on-chip/hybrid work cannot preserve the chunked reference behavior
recurring-regime tests show complete forgetting with no faster reacquisition
long-delay tests require opaque host ledgers and cannot be converted to auditable traces
predictive/world-model variants add complexity without improving robustness or transfer
```

If one break condition appears, stop and narrow the claim instead of stacking
more experiments on top of a weak foundation.

## Roadmap Overview

The remaining work is not one line. It is five tracks that have to converge:

```text
A. Hardware transfer of confirmed tasks
B. Expanded comparative baselines
C. Runtime engineering toward less host dependence
D. Organism/lifecycle/self-scaling proof
E. Hard synthetic and real-ish benchmark tasks
```

The paper should not be written as a strong claim until all five tracks have at
least a defensible pass or a documented limitation.

## Phase 1: Finish Confirmed Hardware Transfer

### Tier 4.16a: Repaired Delayed-Cue Hardware Repeat

Status: passed and promoted as a narrow canonical hardware-transfer result.

Returned hardware result:

```text
output = controlled_test_output/tier4_16_20260427_184635_delayed_cue_3seed_hardware_pass/
status = pass
runs = 3
seeds = 42,43,44
all_accuracy_mean = 0.9933333333333333
tail_accuracy_mean = 1.0
tail_prediction_target_corr_mean = 0.9999999999999997
synthetic_fallbacks_sum = 0
sim_run_failures_sum = 0
summary_read_failures_sum = 0
total_step_spikes_min = 94976
runtime_seconds_mean = 562.8373009915618
```

Protocol:

```text
task = delayed_cue
seeds = 42,43,44
steps = 1200
N = 8
runtime_mode = chunked
learning_location = host
chunk_size_steps = 25
delayed_readout_lr = 0.20
```

Pass:

```text
all 3 seeds complete
zero synthetic fallback
zero sim.run failures
zero summary-read failures
real spike readback > 0 for every seed
tail accuracy >= 0.85 for every seed or predeclared aggregate rule
tail prediction-target correlation documented
runtime documented
```

Fail:

```text
any backend fallback
any sim.run/readback failure
any seed has zero real spikes
tail accuracy instability returns
runtime/provenance artifacts missing
```

If pass:

```text
Claim achieved: repaired delayed-credit delayed_cue transfers to real SpiNNaker across seeds.
Next: Tier 4.16b hard_noisy_switching hardware.
```

If fail:

```text
Stop. Do not run hard_noisy_switching. Diagnose seed-level failure locally and against returned hardware traces.
```

### Tier 4.16b: Hard Noisy Switching Hardware

Status: repaired three-seed hardware repeat passed. The first attempt remains
noncanonical failure evidence because it completed cleanly but missed the
predeclared learning gate on the worst seed.

Historical failed hardware result:

```text
output = controlled_test_output/tier4_16_20260427_194526_hard_noisy_switching_3seed_hardware_fail/
status = fail
runs = 3
seeds = 42,43,44
tail_accuracy_mean = 0.5476190476190476
tail_accuracy_min = 0.47619047619047616
hardware path = clean: zero fallback/failures, real spike readback
```

Canonical repaired hardware result:

```text
output = controlled_test_output/tier4_16_20260427_230043_hard_noisy_switching_3seed_hardware_pass/
status = pass
runs = 3
seeds = 42,43,44
tail_accuracy_mean = 0.5476190476190476
tail_accuracy_min = 0.5238095238095238
tail_prediction_target_corr_mean = 0.04912970304751133
all_accuracy_mean = 0.5497076023391813
synthetic_fallbacks_sum = 0
sim_run_failures_sum = 0
summary_read_failures_sum = 0
total_step_spikes_min = 94707
runtime_seconds_mean = 385.21602948141907
```

Interpretation: this is repaired hard-switch hardware transfer under the
current `N=8`, `chunked + host`, `delayed_lr_0_20` path. It is close to the
threshold and does not prove hardware scaling, lifecycle/self-scaling,
native on-chip dopamine/eligibility, or external-baseline superiority.

Protocol:

```text
task = hard_noisy_switching
seeds = 42,43,44
N = 8
runtime_mode = chunked
learning_location = host
chunk_size_steps = 25 unless Tier 4.16a shows a reason to change
delayed_readout_lr = 0.20
```

Pass:

```text
all seeds complete
zero fallback/failures
real spike readback per seed
above predeclared hard-task threshold
recovery after switches documented
variance across seeds documented
runtime documented
```

Fail:

```text
hardware execution failure
collapse after switches
CRA below random or below its software expectation
metric too brittle or too sparse
```

If pass:

```text
Claim: confirmed delayed-credit/adaptive CRA regime transfers to real SpiNNaker on delayed and noisy switching tasks.
Next: runtime characterization, then expanded baselines.
```

If fail:

```text
Stop. Compare exact software config against NEST/Brian2. Decide whether failure is task design, chunked-host replay, hardware transfer, or CRA adaptive weakness.
```

Actual Tier 4.16b decision:

```text
The first full hard-switch hardware attempt is retained as noncanonical failure evidence.
Tier 4.16b-debug completed after corrected boolean parsing.
The first corrected bundle is superseded by aligned bridge-repair diagnostics.
Latest local diagnostic outputs:
controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427/
controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_brian2_20260427/
Direct step-vs-chunked replay is identical, so chunking itself was not the failure.
The local host-replay bridge clears the hard-switch tail gate on NEST and Brian2 after fixing replay ordering and task-default drift.
The repaired seed-44 hardware probe passed narrowly:
controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/
The repaired full three-seed hardware repeat then passed canonically:
controlled_test_output/tier4_16_20260427_230043_hard_noisy_switching_3seed_hardware_pass/
raw_dopamine = 0.0, expected for chunked host delayed-credit replay because same-step prediction and delayed feedback do not overlap.
Tier 4.18a then passed as v0.7 chunked runtime characterization:
controlled_test_output/tier4_18a_20260428_012822_hardware_pass/
Recommended current hardware chunk: `50`.
```

## Phase 2: Chunked Runtime Characterization

This is engineering, not a science claim, but it is necessary before we waste
more hardware time.

### Tier 4.18a: v0.7 Chunked Hardware Runtime Baseline

Protocol:

```text
tasks = delayed_cue, hard_noisy_switching
seed = 42
chunk_size_steps = 10,25,50
steps = 1200
N = 8
runtime_mode = chunked
learning_location = host
```

Prepare command:

```bash
make tier4-18a-prepare
```

Canonical result:

```text
controlled_test_output/tier4_18a_20260428_012822_hardware_pass/
status = pass
recommended_chunk_size = 50
```

Prepared output is still a run package only, not evidence.

Measure:

```text
wall-clock runtime
sim.run call count
readback time
buffer extraction time
spike totals
accuracy/tail accuracy
correlation
failure rate
provenance size
reports size
```

Pass:

```text
zero fallback/failures
real spike readback
learning metrics do not materially degrade versus v0.7 canonical behavior
runtime improves materially versus per-step mode
spike readback remains interpretable
default chunk-size recommendation is documented
```

Fail:

```text
larger chunks break learning/readback
runtime does not improve enough
provenance/readback becomes unreliable
```

Decision:

```text
Use chunk_size_steps=50 as the current v0.7 hardware default.
Do not stop batching until hybrid/on-chip parity exists.
```

### Tier 4.18b: Optional Expanded Runtime Characterization

Run only if the hardware budget makes sense. Tier 4.18a is already clean and
chunk `50` is the current default, so Tier 4.18b is optional rather than a
blocking step.

Protocol:

```text
tasks = delayed_cue, hard_noisy_switching
seeds = 42,43,44 where feasible
chunk_size_steps = best_4.18a_chunk plus optional 100
steps = 1200, optionally 2400 for one task/seed
```

Pass:

```text
larger chunk size does not corrupt learning/readback
runtime/resource savings are worth the accuracy/stability tradeoff
default hardware profile is documented for future promoted mechanisms
```

## Phase 3: Expanded Baseline Comparison

This must happen before a strong paper. The current baseline work is not enough
for a paradigm-shift claim.

### Tier 5.5: Expanded Baseline Suite

Executable harness:

```bash
make tier5-5
```

Smoke-test harness:

```bash
make tier5-5-smoke
```

Current implemented Tier 5.5 scope:

```text
CRA v0.8 delayed_lr_0_20
random/sign persistence
online perceptron
online logistic regression
echo-state network / reservoir
small GRU
STDP-only SNN
simple evolutionary population
```

Status: **passed and promoted as v0.9 canonical evidence**.

The executable harness exports paired seed deltas, bootstrap confidence
intervals, Cohen-style paired effect sizes, runtime, recovery, and
sample-efficiency metrics. Surrogate-gradient SNN, ANN-trained readout,
ANN-to-SNN conversion, contextual bandit/RL, and liquid-state variants remain
explicit Tier 5.6+ reviewer-defense additions until they are actually
implemented; do not cite them as completed Tier 5.5 evidence.

Observed canonical result:

```text
runs = 1800 / 1800
comparison rows = 20 / 20
robust advantage regimes = 18
not dominated hard/adaptive regimes = 15
hard_noisy_switching at 1500 steps:
  CRA tail = 0.5320754716981132
  external median tail = 0.4933962264150943
  best external tail = 0.5452830188679246 (online_perceptron)
```

Interpretation: CRA v0.8 shows robust/non-dominated hard-adaptive behavior and
beats the external median on hard_noisy_switching at 1500 steps, but it does not
beat the best external hard-switch tail score at that horizon. This is a useful
result, not a universal-superiority result.

Models:

```text
random/sign persistence
online perceptron
online logistic regression
echo-state network / reservoir
small GRU
STDP-only SNN
surrogate-gradient SNN where feasible
ANN-trained readout and ANN-to-SNN converted baseline where task-compatible
simple evolutionary population
simple contextual bandit / actor-critic where appropriate
liquid-state machine if implementation is stable
CRA fixed-N
CRA tuned delayed_lr_0_20
CRA lifecycle/self-scaling once implemented
```

Tasks:

```text
fixed_pattern
delayed_cue
hard_noisy_switching
sensor_control
nonstationary_switch
contextual_bandit
nonstationary_multiarmed_bandit
streaming classification with concept drift
sensor prediction / anomaly detection
small delayed-reward gridworld or navigation adapter
real financial stream only as one domain, not the core claim
```

Sweeps:

```text
steps = 120,240,480,960,1500,3000+
seeds = at least 10 in software
noise levels = low, medium, high
delay = short, medium, long
switch frequency = slow, medium, fast
```

Fairness and statistics:

```text
same task stream and causal information boundary for every model
same train/evaluation windows and delayed reward visibility
comparable unsupported speculationrparameter sweep budget
report best, median, and default baseline settings
mean, median, std, min, confidence interval, and paired per-seed deltas
effect size versus strongest baseline
steps to threshold
tail events to threshold
reward events to threshold
switch recovery steps
area under learning curve
```

Pass:

```text
CRA is not dominated everywhere.
CRA shows at least one robust advantage regime aligned with its design:
delayed credit, nonstationarity, noisy adaptation, recovery, variance, or active-population efficiency.
Results are repeatable across seeds.
Baseline wins are documented honestly.
```

Fail:

```text
simple baselines dominate across every hard/adaptive/real-ish task
CRA advantage appears only on custom toy tasks
CRA requires task-specific hacks not shared by baselines
variance makes results unreliable
```

Make-or-break:

```text
If Tier 5.5 had shown no robust advantage regime, the strong paradigm paper
would narrow or pause. It did show robust advantage regimes, so proceed to Tier
5.6. If Tier 5.6 retuning removes every advantage, narrow to "validated
neuromorphic ecological prototype" or redesign CRA learning dynamics.
```

### Tier 5.6: Baseline Hyperparameter Fairness Audit

Purpose:

```text
prove the expanded baseline result is not caused by under-tuned baselines
```

Executable harness:

```bash
make tier5-6
```

Smoke-test harness:

```bash
make tier5-6-smoke
```

Current implemented Tier 5.6 scope:

```text
CRA locked at v0.8/v1.0 delayed_lr_0_20 evidence setting
external baselines retuned under predeclared profile budgets
tasks = delayed_cue, hard_noisy_switching, sensor_control
run lengths = 960,1500
seeds = 5 for the first standard audit
```

Status: **passed and promoted as v1.0 canonical evidence**.

Observed standard audit:

```text
expected_runs = observed_runs = 990
candidate_count = 32
observed_profile_groups = 48
surviving_target_regime_count = 4
surviving regimes = hard_noisy_switching and sensor_control at 960 and 1500 steps
```

Boundary: Tier 5.6 is software-only reviewer-defense evidence. It shows that
reasonable retuning of implemented external baselines does not erase all CRA
target-regime evidence. It does not prove universal superiority,
all-possible-baselines coverage, or best-baseline dominance at every metric and
horizon.

Required artifacts:

```text
tier5_6_candidate_budget.csv
tier5_6_best_profiles.csv
tier5_6_fairness_contract.json
tier5_6_per_seed.csv
tier5_6_comparisons.csv
tier5_6_summary.csv
tier5_6_report.md
tier5_6_results.json
```

Pass:

```text
unsupported speculationrparameter budgets documented
best and median baseline settings reported
CRA has at least one target-regime edge after retuning
CRA has at least one surviving target regime:
  robust versus the tuned external median
  not dominated by the best tuned external candidate
```

Fail:

```text
baseline retuning removes every CRA advantage
CRA wins only against weak/default baselines
the audit silently changes CRA settings instead of keeping CRA locked
```

Reviewer-defense note:

```text
Surrogate-gradient SNNs and ANN-to-SNN converted models are not philosophically
the same as CRA because they usually rely on global differentiable training or
offline ANN training. They still matter as reviewer-defense baselines. Include
them where the task interface is fair and causal; explicitly mark tasks where
conversion baselines are not applicable.
```

### Tier 5.7: Compact Regression After Promoted Tuning

Any carried-forward CRA setting must rerun a compact regression:

```text
Tier 1 zero/shuffle controls
Tier 2 fixed/delayed/switch learning proof
Tier 3 dopamine/plasticity/trophic ablations
one delayed_cue smoke
one hard_noisy_switching smoke
```

Pass:

```text
controls remain negative
positive learning remains intact
mechanism ablation gaps remain meaningful
```

Fail:

```text
tuning reintroduces false learning
tuning breaks core mechanism evidence
```

Status: **passed and promoted as v1.1 canonical evidence**.

Observed canonical run:

```text
backend = nest
readout_lr = 0.10
delayed_readout_lr = 0.20
children_run = 4
children_passed = 4
criteria_passed = 4 / 4
```

Boundary: Tier 5.7 is a guardrail, not a new capability result. It authorizes
moving to Tier 6.1 lifecycle/self-scaling without rewriting the promoted
setting.

## Phase 3B: Architecture Failure-Mode Fixes

These tiers are planned eventual work. The corrected Tier 4.16b-debug step first
localized the immediate blocker to the chunked host-replay/macro-credit bridge;
the aligned bridge-repair diagnostics now pass locally on NEST and Brian2. Do
not jump straight to big architecture surgery. The repaired seed-44 probe and repaired three-seed repeat have passed. Activate the deeper mechanisms only if later expanded baselines, lifecycle tests, or harder task traces show the limitation is architectural.

Principle:

```text
prove the failure mode first
add one mechanism at a time
compare with and without the mechanism
rerun compact controls before promotion
```

### Tier 5.8: Hard-Switch Root-Cause Decision

Status: completed as corrected and then aligned noncanonical diagnostic through `experiments/tier4_16b_hard_switch_debug.py`.

Superseded corrected result:

```text
output = controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch_corrected/
classification = chunked_host_bridge_learning_failure
full_step_cra_tail_min = 0.5238095238095238
direct_step_host_tail_min = 0.42857142857142855
direct_chunked_host_tail_min = 0.42857142857142855
hardware_tail_min = 0.47619047619047616
max_bridge_tail_delta = 0.0
max_hardware_tail_delta = 0.09523809523809523
```

Latest aligned bridge-repair result:

```text
outputs = controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427/
          controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_brian2_20260427/
classification = hardware_transfer_or_timing_failure
full_step_cra_tail_min = 0.5476190476190477
direct_step_host_tail_min = 0.5238095238095238
direct_chunked_host_tail_min = 0.5238095238095238
hardware_tail_min = 0.47619047619047616
max_bridge_tail_delta = 0.0
max_hardware_tail_delta = 0.04761904761904767
```

Purpose:

```text
decide whether Tier 4.16b failed because of task design, chunked replay,
hardware transfer, or CRA adaptive dynamics
```

Protocol:

```text
task = hard_noisy_switching
seeds = 42,43,44
steps = 1200
backends = NEST,Brian2
compare step mode versus chunked+host replay
compare local traces against returned hardware traces
```

Required diagnostics:

```text
spike bins
prediction signs
evaluation targets
tail event counts
switch recovery windows
dopamine traces
readout weight movement
delayed-credit maturity counts
prediction-target correlation
```

Pass:

```text
failure class is assigned
next fix is narrow and testable
no new hardware is scheduled until the local diagnosis supports it
```

Decision reached:

```text
The immediate fix is not a full on-chip rewrite.
The direct host-replay bridge has been brought above threshold locally on hard_noisy_switching.
The seed-44 repaired hardware probe and the repaired three-seed hardware repeat
passed. Tier 4.18a then passed and recommends chunk `50` for the current v0.7
chunked-host hardware path. Tier 5.9a macro eligibility was later activated as
the first post-v1.4 mechanism gate and failed promotion cleanly, so the next
macro-credit step is repair/debug, not hardware migration.
```

Fail:

```text
local and hardware traces cannot be reconciled
metrics are too sparse to diagnose
hardware rerun is requested without a local decision
```

### Tier 5.8b: Host-Replay / Macro-Credit Bridge Repair

Purpose:

```text
repair the direct chunked host-replay path so it reproduces full step-mode CRA
behavior on hard_noisy_switching well enough to justify the repaired hardware
sequence that passed: first a one-seed probe, then the three-seed repeat
```

Why this comes before deeper architecture work:

```text
Tier 4.16b-debug shows direct step and direct chunked replay match exactly.
Therefore chunking alone is not the observed failure.
The weaker path was the simplified host-replay/macro-credit bridge plus stale
debug task defaults, not chunking itself.
```

Protocol:

```text
task = hard_noisy_switching
seeds = 42,43,44
steps = 1200
backends = NEST,Brian2
compare full_step_cra vs direct_step_host_replay vs direct_chunked_host_replay
keep delayed_lr_0_20 unless the diagnostic proves the credit path is wrong
```

Result:

```text
status = pass as local diagnostic
classification = hardware_transfer_or_timing_failure
direct_chunked_host_tail_min = 0.5238095238095238
max_bridge_tail_delta = 0.0
```

Required traces:

```text
evaluation targets and prediction signs
per-step binned spikes
pending and matured delayed-credit records
raw dopamine and smoothed dopamine if present
readout weight and bias trajectories
switch recovery windows
tail event table
full-CRA-vs-bridge deltas
```

Pass:

```text
direct chunked host tail min >= 0.5 across seeds
direct chunked host does not materially regress versus full step-mode CRA
step replay and chunked replay remain equivalent
NEST and Brian2 agree within tolerance
all artifacts export cleanly
```

Fail:

```text
bridge remains below threshold
bridge only passes by task-specific hacks
full CRA itself falls below threshold after the repair
trace evidence shows delayed-credit/memory architecture is insufficient
```

If pass:

```text
run the repaired three-seed hard-switch hardware repeat
```

If fail:

```text
repair the failing mechanism locally or activate Tier 5.10 memory-timescale
tests one mechanism at a time
```

### Tier 5.9: Macro Eligibility Trace Confirmation

Current status:

```text
Tier 5.9a implemented and run as a noncanonical diagnostic.
Result: FAIL, mechanism not promoted.
Output: controlled_test_output/tier5_9a_20260428_162345/
Tier 5.9b residual repair implemented and run as a noncanonical diagnostic.
Result: FAIL, mechanism parked.
Output: controlled_test_output/tier5_9b_20260428_174327/
Tier 5.9c v2.1-era recheck implemented and run as a noncanonical diagnostic.
Result: FAIL; v2.1 guardrail passed but macro residual still failed trace-ablation specificity.
Output: controlled_test_output/tier5_9c_20260429_190503/
```

Purpose:

```text
replace or complement blunt PendingHorizon-style delayed credit with an
auditable macro-timescale eligibility trace before attempting native C credit
```

Design:

```text
maintain per-polyp or per-readout eligibility traces in host software first
increment traces from causal spike/readout activity
decay traces by task step or chunk boundary
bind delayed dopamine to the remaining trace
compare against the current PendingHorizon learner
compare pair-style eligibility, macro-timescale eligibility, triplet-style
eligibility, and e-prop-inspired traces where practical
```

Protocol:

```text
tasks = delayed_cue, hard_noisy_switching, variable_delay_cue
delay sweep = 1,5,10,25,50,100 task steps where practical
seeds = at least 10 in software for paper-critical claims
backends = NEST,Brian2 before hardware
```

Pass:

```text
matches or beats PendingHorizon on delayed_cue
improves hard_noisy_switching or reduces variance
trace ablation hurts performance
delay sweep remains above controls for a predeclared range
trace state is exported and auditable
trace variant comparisons show whether the benefit is specific to causal
eligibility dynamics or just generic smoothing
```

Observed Tier 5.9a result:

```text
108 / 108 runs completed
feedback timing leakage violations = 0
macro trace active steps = 11520
macro matured updates = 8536
delayed_cue tail delta versus v1.4 = -0.6111111111111112
hard_noisy_switching tail delta versus v1.4 = -0.039215686274509776
hard_noisy_switching recovery delta versus v1.4 = +5.199999999999999
variable_delay_cue tail delta versus v1.4 = -0.3218390804597702
trace ablation specificity = failed
```

Interpretation:

```text
The macro trace is active, but the current implementation is not causal enough
to promote. Normal and shuffled traces matched on multiple tasks, and replacing
the PendingHorizon feature with the trace damaged the known delayed_cue regime.
This is a clean failed mechanism gate, not a failure of the v1.4 architecture
baseline.
```

Next macro-eligibility repair, only if this mechanism remains the priority:

```text
none active
Tier 5.9b already tested the residual/blended trace repair
the repair preserved delayed_cue but failed trace-ablation specificity
hard_noisy_switching slightly regressed versus v1.4 and zero-trace
Tier 5.9c reran the question after v2.1; v2.1 stayed green, but macro still
failed because normal/shuffled/zero/no-macro paths were identical
revive macro eligibility only if a later task exposes a specific PendingHorizon
failure that the trace can plausibly solve
```

Promotion rule:

```text
Do not promote macro eligibility from Tier 5.9a.
Do not promote macro eligibility from Tier 5.9b.
Do not promote macro eligibility from Tier 5.9c.
Do not move macro eligibility to SpiNNaker or custom C until a future repaired
variant passes software ablation gates and then Tier 5.7 compact regression.
```

Fail:

```text
trace behaves the same as random smoothing
PendingHorizon remains strictly better across all hard/delayed tasks
long-delay performance collapses with no interpretable trace dynamics
```

### Tier 5.10: Multi-Timescale Memory And Forgetting Test

Current status:

```text
Tier 5.10 implemented and run as a noncanonical diagnostic.
Result: FAIL, mechanism not promoted.
Output: controlled_test_output/tier5_10_20260428_181322/
Tier 5.10b implemented and run as a noncanonical task-validation gate.
Result: PASS, repaired tasks validated for memory-pressure testing.
Output: controlled_test_output/tier5_10b_20260428_193639/
Tier 5.10c implemented and run as a noncanonical software mechanism diagnostic.
Result: PASS, explicit host-side context-memory scaffold validated.
Output: controlled_test_output/tier5_10c_20260428_201314/
Tier 5.10d implemented and run as a noncanonical internal software-memory diagnostic.
Result: PASS, internalized scaffold and compact regression passed.
Output: controlled_test_output/tier5_10d_20260428_212229/
Tier 5.10e implemented and run as a noncanonical retention stressor.
Result: PASS, internal memory survived longer gaps/distractors/reentry pressure.
Output: controlled_test_output/tier5_10e_20260428_220316/
Tier 5.10f implemented and run as a noncanonical capacity/interference stressor.
Result: FAIL, single-slot memory failed under overlap/interference/reentry pressure.
Output: controlled_test_output/tier5_10f_20260428_224805/
Tier 5.10g implemented and run as baseline-frozen keyed-memory repair evidence.
Result: PASS, bounded keyed slots repaired the measured 5.10f failure and compact regression passed.
Output: controlled_test_output/tier5_10g_20260428_232844/
```

Purpose:

```text
determine whether CRA forgets prior regimes and whether fast/slow/structural
memory reduces that forgetting
```

Design candidates:

```text
fast weights for rapid adaptation
slow weights for consolidated recurring lessons
structural weights or calcification for protected memory
regime memory keyed by changepoint/context signatures
explicit fast-to-slow consolidation rule
```

Protocol:

```text
tasks = A-B-A regime recurrence, A-B-C-A recurrence, hidden-regime switching
compare current CRA versus multi-timescale CRA
include no-BOCPD, no-slow-memory, no-structural-memory ablations
measure first-learning speed, switch adaptation, old-regime reacquisition, and retained accuracy
```

Pass:

```text
old regimes are reacquired faster than from-scratch learning
retention improves without blocking adaptation to new regimes
fast/slow/structural ablations identify which memory layer matters
benefit survives multiple seeds and at least one external baseline comparison
```

Fail:

```text
multi-timescale memory only freezes bad behavior
adaptation slows with no retention benefit
recurrent-regime performance is indistinguishable from current CRA
```

Observed Tier 5.10 result:

```text
99 / 99 NEST runs completed
feedback timing leakage violations = 0
candidate tail deltas versus v1.4:
  aba_recurrence = -0.1777777777777778
  abca_recurrence = 0.0
  hidden_regime_switching = -0.15555555555555556
candidate return-regime deltas versus v1.4:
  aba_recurrence = -0.1999999999999999
  abca_recurrence = 0.0
  hidden_regime_switching = -0.19444444444444442
candidate recovery deltas versus v1.4:
  aba_recurrence = -101.33333333333331
  abca_recurrence = -40.888888888888886
  hidden_regime_switching = -42.66666666666667
best CRA ablation = overrigid_memory on all tasks
best external return-phase baseline = sign_persistence on all tasks
```

Interpretation:

```text
The first memory-timescale proxy is not promoted. It regressed ordinary tail
performance, did not improve recurrence/recovery, and lost to its own
ablations. The run also exposed that the first recurrence tasks are not yet
memory-specific enough, because sign_persistence solved the return phases too
well. The correct next step was Tier 5.10b recurrence-task repair / memory
pressure hardening before sleep/replay or explicit memory stores; that task
gate has now passed and shifts the active memory question to Tier 5.10c.
```

Tier 5.10b task repair result:

```text
99 / 99 task/model/seed runs completed
feedback timing leakage violations = 0
same current cue supports opposite labels = True
sign_persistence max accuracy = 0.5333333333333333
oracle context min accuracy = 1.0
stream context memory min accuracy = 1.0
context-memory edge versus sign_persistence min = 0.4666666666666667
shuffled/reset/wrong-control failure edge min = 0.4642857142857143
best standard baseline max accuracy = 0.8154761904761904
```

Interpretation:

```text
Tier 5.10b repaired the memory-test surface. The new streams require remembered
context, are solvable when context memory is available, and fail under wrong,
reset, or shuffled memory. This is not a CRA memory win by itself. It provided
the repaired surface that Tier 5.10c then used for explicit context-memory
mechanism testing.
```

### Tier 5.10c: Explicit Memory Mechanism Retry On Repaired Tasks

Current status:

```text
Tier 5.10c implemented and run.
Result: PASS as noncanonical software mechanism evidence.
Output: controlled_test_output/tier5_10c_20260428_201314/
```

Purpose:

```text
test whether CRA can use explicit context/memory state on tasks that now
actually require memory
```

Protocol:

```text
tasks = delayed_context_cue, distractor_gap_context, hidden_context_recurrence
seeds = at least 42,43,44; expand if a candidate passes
compare v1.4 CRA, explicit context-memory CRA, fast/slow memory CRA,
memory-reset ablation, shuffled-memory ablation, wrong-memory ablation
include external baselines, especially online_perceptron because it partially
solved hidden_context_recurrence in Tier 5.10b
```

Pass:

```text
candidate memory CRA beats v1.4 on repaired memory-pressure tasks
candidate beats or is non-dominated against strong baselines where CRA's
mechanism should matter
reset/shuffled/wrong-memory ablations remove the benefit
no feedback leakage
compact regression passes before any baseline promotion
```

Fail:

```text
candidate memory behaves like smoothing rather than context binding
candidate loses to v1.4 or to its own ablations
strong baselines solve the task with no CRA-specific benefit
memory helps one task only by exploiting task-specific leakage or shortcuts
```

Observed Tier 5.10c result:

```text
144 / 144 NEST task/model/seed runs completed
feedback timing leakage violations = 0
candidate feature-active steps = 303
candidate context-memory updates = 147
explicit_context_memory all accuracy = 1.0 on all repaired tasks
minimum all-accuracy edge versus v1.4 raw CRA = 0.4666666666666667
minimum all-accuracy edge versus best memory ablation = 0.3555555555555556
minimum all-accuracy edge versus sign_persistence = 0.4666666666666667
minimum all-accuracy edge versus best standard baseline = 0.18452380952380965
```

Interpretation:

```text
Explicit context binding works on the repaired memory-pressure streams. The
benefit survives reset, shuffled, and wrong-memory ablations and beats the
selected standard baselines in this diagnostic. This is still a host-side
context-memory scaffold. It is not native CRA memory, not sleep/replay, not
hardware evidence, and not final catastrophic-forgetting proof.
```

Next memory step:

```text
Tier 5.10d has now turned the host-side context-binding scaffold into an
internal CRA context-memory module and run full compact regression. Do not
jump to sleep/replay until internal memory still decays or forgets under a
recurrence stressor.
```

### Tier 5.10d: Internal Context-Memory Implementation

Current status:

```text
Tier 5.10d implemented and run.
Result: PASS as noncanonical internal software-memory evidence.
Output: controlled_test_output/tier5_10d_20260428_212229/
Full compact regression: PASS at controlled_test_output/tier5_7_20260428_214807/
```

Purpose:

```text
test whether the successful Tier 5.10c context-binding scaffold can live
inside CRA instead of preprocessing the observation stream outside the organism
```

Protocol:

```text
tasks = delayed_context_cue, distractor_gap_context, hidden_context_recurrence
seeds = 42,43,44
variants = v1_4_raw, external_context_memory_scaffold,
           internal_context_memory, memory_reset_ablation,
           shuffled_memory_ablation, wrong_memory_ablation
external baselines = sign_persistence, online_perceptron,
                     online_logistic_regression, echo_state_network,
                     small_gru, stdp_only_snn
context controls = oracle_context, stream_context_memory, shuffled_context,
                   memory_reset, wrong_context
```

Observed Tier 5.10d result:

```text
153 / 153 NEST task/model/seed runs completed
feedback timing leakage violations = 0 across 5151 checked rows
internal candidate feature-active steps = 303
internal candidate context-memory updates = 147
internal_context_memory all accuracy = 1.0 on all repaired tasks
external_context_memory_scaffold all accuracy = 1.0 on all repaired tasks
minimum all-accuracy edge versus v1.4 raw CRA = 0.4666666666666667
minimum all-accuracy edge versus external scaffold = 0.0
minimum all-accuracy edge versus best memory ablation = 0.4666666666666667
minimum all-accuracy edge versus sign_persistence = 0.4666666666666667
minimum all-accuracy edge versus best standard baseline = 0.18452380952380965
```

Interpretation:

```text
The memory capability no longer depends on an external preprocessing scaffold.
CRA can use an internal host-side context-memory path to bind visible context
to later visible decision cues on repaired memory-pressure tasks. Reset,
shuffled, and wrong-memory ablations remove the benefit, and compact
regression smoke remained green.
```

Boundary:

```text
This is not native on-chip memory, not sleep/replay, not hardware transfer of
the memory mechanism, not broad catastrophic-forgetting resolution, and not
general AGI-style working memory. Tier 5.10e then asks the next memory
question: does this internal memory remain useful when recurrence gaps,
distractors, and regime re-entry demands are made harder?
```

### Tier 5.10e: Internal Memory Retention Stressor

Status:

```text
passed as noncanonical software stress evidence
```

Observed result:

```text
output = controlled_test_output/tier5_10e_20260428_220316/
backend = NEST
tasks = delayed_context_cue, distractor_gap_context, hidden_context_recurrence
steps = 960
seeds = 42,43,44
expected/observed runs = 153/153
feedback leakage violations = 0 across 2448 checked feedback rows
candidate feature-active steps = 144
candidate context-memory updates = 60
internal_context_memory all accuracy = 1.0 on all retention-stress tasks
external_context_memory_scaffold all accuracy = 1.0 on all retention-stress tasks
minimum all-accuracy edge versus v1.4 raw CRA = 0.33333333333333337
minimum all-accuracy edge versus external scaffold = 0.0
minimum all-accuracy edge versus best memory ablation = 0.33333333333333337
minimum all-accuracy edge versus sign_persistence = 0.33333333333333337
minimum all-accuracy edge versus best standard baseline = 0.33333333333333337
```

Stress profile:

```text
context_gap = 48
context_period = 96
long_context_gap = 96
long_context_period = 160
distractor_density = 0.85
distractor_scale = 0.45
recurrence_phase_len = 240
recurrence_trial_gap = 24
recurrence_decision_gap = 64
```

Interpretation:

```text
The internal host-side context-memory mechanism survived longer context gaps,
denser distractors, and hidden recurrence pressure. Reset, shuffled, and
wrong-memory ablations still remove the benefit. Sleep/replay is not yet
justified as a repair for this stressor because no retention decay was observed.
```

Boundary:

```text
This is not native on-chip memory, not hardware memory transfer, not
sleep/replay consolidation, not capacity-limited memory, not broad
catastrophic-forgetting resolution, and not general working memory.
```

### Tier 5.10f: Memory Capacity / Interference Stressor

Status:

```text
failed cleanly as noncanonical software diagnostic evidence
```

Observed result:

```text
output = controlled_test_output/tier5_10f_20260428_224805/
backend = NEST
tasks = intervening_contexts, overlapping_contexts, context_reentry_interference
steps = 720
seeds = 42,43,44
expected/observed runs = 153/153
feedback leakage violations = 0 across 1938 checked feedback rows
candidate feature-active steps = 114
candidate context-memory updates = 121
minimum all-accuracy edge versus v1.4 raw CRA = -0.25
minimum all-accuracy edge versus external scaffold = 0.0
minimum all-accuracy edge versus best memory ablation = -0.5
minimum all-accuracy edge versus sign_persistence = -0.25
minimum all-accuracy edge versus best standard baseline = -0.25
```

Task-level result:

```text
intervening_contexts internal all accuracy = 0.6666666666666666
overlapping_contexts internal all accuracy = 0.5
context_reentry_interference internal all accuracy = 0.25
```

Interpretation:

```text
The v1.5 memory mechanism is not merely miswired; it exactly matches the
external single-slot scaffold. The failure is a measured capacity/interference
limit: intervening contexts, overlapping pending decisions, and reentry can
overwrite or misbind the retained context. This narrows the v1.5 claim and
justifies a targeted multi-slot/keyed-memory repair before sleep/replay is
claimed as the next fix.
```

Completed repair gate:

```text
Tier 5.10g - Multi-Slot / Keyed Context Memory Repair
compare v1.5 single-slot memory
versus bounded multi-slot/keyed memory
versus slot-reset, slot-shuffle, wrong-key, overcapacity, and oracle controls
on the exact Tier 5.10f tasks
```

Observed Tier 5.10g result:

```text
171 / 171 NEST variant/baseline/control/task/seed runs completed
feedback leakage violations = 0 across 2166 checked feedback rows
candidate feature-active steps = 114.0
candidate context-memory updates = 121.0
keyed_context_memory all accuracy = 1.0 on intervening_contexts
keyed_context_memory all accuracy = 1.0 on overlapping_contexts
keyed_context_memory all accuracy = 1.0 on context_reentry_interference
minimum all-accuracy edge versus v1.4 raw CRA = 0.5
minimum all-accuracy edge versus v1.5 single-slot memory = 0.33333333333333337
minimum all-accuracy edge versus oracle-key scaffold = 0.0
minimum all-accuracy edge versus best memory ablation = 0.33333333333333337
minimum all-accuracy edge versus sign_persistence = 0.5
minimum all-accuracy edge versus best standard baseline = 0.5
compact regression after keyed-memory addition = PASS
```

Interpretation:

```text
The 5.10f failure was not "CRA memory cannot work"; it was single-slot
overwrite/misbinding. Bounded keyed slots repair that measured failure under the
tested capacity/interference tasks and match the oracle-key upper bound. This
freezes v1.6 as internal host-side keyed-memory evidence. It is not sleep/replay,
native on-chip memory, hardware memory transfer, compositionality, module
routing, or general working memory.
```

### Tier 5.11a: Sleep/Replay Need Test

Purpose:

```text
prove whether replay/consolidation is needed before implementing it
```

Design:

```text
compare v1.6 no-replay keyed memory against unbounded keyed memory
compare against oracle context scaffold, overcapacity, slot reset, slot shuffle, wrong-key ablations, and standard baselines
use silent context reentry, long-gap silent reentry, and partial-key reentry
require zero feedback leakage and solved upper-bound controls before interpreting degradation
do not implement replay in this tier
```

Observed Tier 5.11a result:

```text
output = controlled_test_output/tier5_11a_20260429_004340/
status = PASS
backend = NEST
expected/observed matrix cells = 171 / 171
feedback leakage violations = 0
v1.6 no-replay minimum accuracy = 0.6086956521739131
unbounded keyed minimum accuracy = 1.0
oracle scaffold minimum accuracy = 1.0
max unbounded gap versus v1.6 no-replay = 0.3913043478260869
max oracle gap versus v1.6 no-replay = 0.3913043478260869
max tail unbounded gap versus v1.6 no-replay = 1.0
diagnostic decision = replay_or_consolidation_needed
```

Interpretation:

```text
v1.6 remains the frozen current memory baseline, but bounded no-replay memory
fails the silent reentry tail stressors while unbounded/oracle controls solve
them. Replay/consolidation now has a measured failure mode to address.
```

Boundary:

```text
Tier 5.11a is not replay success, not hardware evidence, not native memory, and
not a new frozen baseline. It authorizes Tier 5.11b.
```

### Tier 5.11b: Sleep/Replay Consolidation Intervention

Purpose:

```text
test whether prioritized offline replay/consolidation repairs the measured 5.11a silent-reentry failure without leakage
```

Design:

```text
store visible context episodes, successful decisions, high-surprise misses, and rare reentry contexts
rank replay examples by predeclared priority
run replay only outside online scoring windows
consolidate repeated successful associations into keyed slow memory
export replay event logs, selected episode hashes, before/after slot summaries, and online/offline phase labels
```

Pass:

```text
prioritized replay closes a meaningful fraction of the v1.6 versus unbounded-keyed gap
prioritized replay beats no-replay, shuffled replay, random replay, and no-consolidation replay
online evaluation remains causal and uncontaminated
replay logs explain what was consolidated
compact regression still passes
```

Fail:

```text
replay leaks future labels into online scoring
random/shuffled replay performs the same as prioritized replay
replay only increases capacity without interpretable consolidation
sleep/replay improves the stressor but regresses core controls or compact regression
```

Observed Tier 5.11b result:

```text
output = controlled_test_output/tier5_11b_20260429_022048/
status = FAIL
backend = NEST
expected/observed matrix cells = 162 / 162
feedback leakage violations = 0
replay future violations = 0
prioritized replay events = 1185
prioritized replay consolidations = 1185
prioritized minimum all accuracy = 1.0
prioritized minimum tail accuracy = 1.0
prioritized minimum tail delta versus no replay = 1.0
prioritized all/tail gap closure versus unbounded = 1.0 / 1.0
no-consolidation replay writes = 0
failed criterion = shuffled replay does not match prioritized tail
minimum prioritized tail edge versus shuffled = 0.4444444444444444
predeclared shuffled edge threshold = 0.5
```

Interpretation:

```text
prioritized offline replay is a strong repair signal for the measured v1.6
silent-reentry failure, but it did not clear the strict sham-control separation
gate because shuffled replay partially worked on partial_key_reentry. The
evidence system correctly blocks promotion.
```

Boundary:

```text
Tier 5.11b is not a replay/consolidation success claim, not hardware replay,
not native on-chip memory, and not a v1.7 freeze. v1.6 remains the current
memory baseline.
```

After pass:

```text
consider freeze v1.7 only if compact regression passes and ablations show replay is causal
then test routing/compositionality on top of the promoted memory stack
```

After fail:

```text
keep v1.6 as the memory baseline
run one sharper Tier 5.11c sham-separation repair before parking replay entirely
```

### Tier 5.11c: Replay Sham-Separation Repair

Purpose:

```text
test whether the narrower priority-specific replay claim survives sharper
wrong-memory and no-write shams after the Tier 5.11b shuffled-control failure
```

Observed Tier 5.11c result:

```text
output = controlled_test_output/tier5_11c_20260429_031427/
status = FAIL
backend = NEST
expected/observed matrix cells = 189 / 189
feedback leakage violations = 0
replay future violations = 0
candidate replay events = 1185
candidate replay consolidations = 1185
candidate minimum all accuracy = 1.0
candidate minimum tail accuracy = 1.0
candidate all/tail gap closure versus unbounded = 1.0 / 1.0
no-consolidation replay writes = 0
minimum tail edge versus shuffled-order replay = 0.40740740740740733
minimum tail edge versus random replay = 0.2962962962962963
minimum tail edge versus wrong-key replay = 0.5555555555555556
minimum tail edge versus key-label-permuted replay = 1.0
minimum tail edge versus priority-only ablation = 1.0
minimum tail edge versus no-consolidation replay = 1.0
failed criterion = shuffled-order replay does not match prioritized tail
```

Interpretation:

```text
Tier 5.11c blocks the narrower claim that priority weighting itself is proven.
However, correct-binding replay remains strongly separated from wrong-key,
key-label-permuted, priority-only, and no-consolidation controls. This motivates
one reframed Tier 5.11d gate for generic replay/consolidation rather than
priority-specific replay.
```

### Tier 5.11d: Generic Replay / Consolidation Confirmation

Purpose:

```text
test whether correct-binding replay/consolidation itself adds causal value,
while explicitly not claiming that priority weighting is essential
```

Design:

```text
same silent-reentry tasks, seeds 42/43/44, and selected external baselines
candidate replay still writes old/rare observed context episodes
shuffled-order and random replay are reported as replay-opportunity comparators
wrong-key, key-label-permuted, priority-only, and no-consolidation controls gate promotion
all replay events must use only observed past context episodes
compact regression must pass after the candidate gate
```

Observed Tier 5.11d result:

```text
output = controlled_test_output/tier5_11d_20260429_041524/
status = PASS
backend = NEST
expected/observed matrix cells = 189 / 189
feedback leakage violations = 0
replay future violations = 0
candidate replay events = 1185
candidate replay consolidations = 1185
candidate minimum all accuracy = 1.0
candidate minimum tail accuracy = 1.0
candidate minimum tail delta versus no replay = 1.0
candidate all/tail gap closure versus unbounded = 1.0 / 1.0
minimum tail edge versus wrong-key replay = 0.5555555555555556
minimum tail edge versus key-label-permuted replay = 1.0
minimum tail edge versus priority-only ablation = 1.0
minimum tail edge versus no-consolidation replay = 1.0
compact regression after replay = PASS at controlled_test_output/tier5_7_20260429_050527/
baseline freeze = baselines/CRA_EVIDENCE_BASELINE_v1.7.md
```

Interpretation:

```text
Tier 5.11d promotes host-side correct-binding replay/consolidation as a
software mechanism. It does not prove priority weighting is essential, native
on-chip replay, hardware memory transfer, compositional reuse, routing, world
modeling, or biological sleep. v1.7 remains the replay/consolidation baseline;
v1.8 is now the bounded visible predictive-context software baseline.
```

### Tier 5.12a: Predictive Task-Pressure Validation

Purpose:

```text
validate that the proposed predictive tasks actually require predictive/context
state before adding a CRA predictive head
```

Observed Tier 5.12a result:

```text
output = controlled_test_output/tier5_12a_20260429_054052/
status = PASS
matrix = 144 / 144 task-model-seed cells
feedback leakage violations = 0 across 10044 checked feedback rows
tasks = hidden_regime_switching, masked_input_prediction,
        event_stream_prediction, sensor_anomaly_prediction
seeds = 42, 43, 44
causal predictive_memory accuracy = 1.0 on all tasks
max current-reflex accuracy = 0.5393258426966292
max sign-persistence accuracy = 0.5649717514124294
max wrong/shuffled-target accuracy = 0.5444444444444444
minimum predictive edge vs best reflex = 0.4350282485875706
minimum predictive edge vs best wrong/shuffled sham = 0.4555555555555556
```

Interpretation:

```text
Tier 5.12a is task-validation evidence only. It proves the prediction battery
has causal pressure: current-value, sign-persistence, rolling-majority,
wrong-horizon, and shuffled-target shortcuts do not explain the solvable signal.
It authorized the Tier 5.12b/5.12c mechanism sequence, but it is not CRA
predictive coding, not a world model, not language, not planning, not hardware
prediction, and not a v1.8 freeze.
```

### Tier 5.12b: Internal Predictive Context Mechanism Diagnostic

Observed Tier 5.12b result:

```text
output = controlled_test_output/tier5_12b_20260429_055923/
status = FAIL
matrix = 162 / 162 NEST cells
feedback leakage violations = 0
candidate predictive-context writes / active decisions = 570 / 570
candidate matched external scaffold on all tasks
candidate accuracy = 1.0 on event_stream_prediction
candidate accuracy = 0.8444444444444444 on masked_input_prediction
candidate accuracy = 1.0 on sensor_anomaly_prediction
failed gates = absolute candidate accuracy, tail accuracy, ablation separation
```

Interpretation:

```text
Tier 5.12b is a useful failed diagnostic. The host-side predictive-context
pathway is active and matches the external scaffold, but the wrong-sign sham is
not an information-destroying control because stable sign inversion remains an
alternate learnable code. The masked-input task also shows a scaffold-limited
ceiling at 0.8444444444444444, so absolute >0.90 gating was too blunt.
```

Boundary:

```text
Do not cite Tier 5.12b as a predictive-context pass. Cite it only as the
diagnostic that forced the sham-separation repair in Tier 5.12c.
```

### Tier 5.12c: Predictive Context Sham-Separation Repair

Observed Tier 5.12c result:

```text
output = controlled_test_output/tier5_12c_20260429_062256/
status = PASS
matrix = 171 / 171 NEST cells
feedback leakage violations = 0
tasks = masked_input_prediction, event_stream_prediction,
        sensor_anomaly_prediction
seeds = 42, 43, 44
candidate predictive-context writes / active decisions = 570 / 570
candidate gap vs external scaffold = 0.0
candidate accuracy = 1.0 on event_stream_prediction
candidate accuracy = 0.8444444444444444 on masked_input_prediction
candidate accuracy = 1.0 on sensor_anomaly_prediction
minimum tail accuracy = 0.888888888888889
minimum edge vs v1.7 reactive CRA = 0.8444444444444444
minimum edge vs shuffled/permuted/no-write shams = 0.3388888888888889
minimum edge vs shortcut controls = 0.3
minimum edge vs best selected external baseline = 0.31666666666666665
```

Interpretation:

```text
Tier 5.12c promotes only the bounded mechanism that actually passed:
host-side visible predictive-context binding. CRA can store a visible causal
precursor before feedback arrives and use it later at decision time, and the
benefit separates from shuffled/permuted/no-write controls and selected
external baselines.
```

Boundary:

```text
Tier 5.12c is not hidden-regime inference, full world modeling, language,
planning, hardware prediction, hardware scaling, native on-chip learning,
compositionality, or external-baseline superiority. Tier 5.12d is the separate
compact-regression promotion gate.
```

### Tier 5.12d: Predictive-Context Compact Regression / v1.8 Freeze

Observed Tier 5.12d result:

```text
output = controlled_test_output/tier5_12d_20260429_070615/
status = PASS
children passed = 6 / 6
criteria passed = 6 / 6
runtime_seconds = 319.63600204200003
baseline freeze = baselines/CRA_EVIDENCE_BASELINE_v1.8.md
child checks = tier1_controls, tier2_learning, tier3_ablations,
               target_task_smokes, replay_consolidation_guardrail,
               predictive_context_guardrail
```

Interpretation:

```text
Tier 5.12d freezes v1.8 as bounded host-side visible predictive-context
software evidence. It proves the predictive-context mechanism did not break
old compact guardrails or v1.7 replay/consolidation while preserving compact
predictive sham separation.
```

Boundary:

```text
v1.8 is not hidden-regime inference, full world modeling, language, planning,
hardware prediction, hardware scaling, native on-chip learning,
compositionality, or external-baseline superiority.
```

### Tier 5.13: Compositional Skill Reuse

Purpose:

```text
test whether CRA can reuse learned substructures/modules rather than learning
every new task as an isolated reflex
```

Why this exists:

```text
A system can learn Task A and Task B while still failing to compose A as a
subroutine inside B for a novel Task C. If CRA wants a substrate-level claim,
it must eventually show deliberate structural reuse, not just adaptation by
input-space similarity.
```

Design candidates:

```text
skill/module registry for reusable polyp ensembles or readout subgraphs
module activation/routing gates keyed by context or task cue
frozen/reused module path versus newly learned path
composition traces showing which learned module contributed to the new task
```

Protocol:

```text
Train A: cue/regime detector
Train B: delayed action or control rule
Test C: novel combination requiring A then B
Use held-out A/B combinations not seen during training
Compare against from-scratch CRA, same-size monolithic CRA, shuffled-module CRA,
frozen irrelevant-module CRA, and external baselines
```

Pass:

```text
composed CRA learns Task C faster or more reliably than from-scratch CRA
identified modules/subgraphs are reused in the composed task
module shuffling or irrelevant-module substitution hurts performance
benefit survives held-out combinations and multiple seeds
external baselines do not explain the result as ordinary input similarity
```

Fail:

```text
no sample-efficiency or robustness gain over from-scratch CRA
module shuffle does not reduce performance
reuse traces are absent or post hoc
external baselines compose better under the same task stream
```

Current result:

```text
status = PASS
output = controlled_test_output/tier5_13_20260429_075539/
matrix cells = 126 / 126
feedback leakage violations = 0
tasks = heldout_skill_pair, order_sensitive_chain, distractor_skill_chain
seeds = 42, 43, 44
candidate first-heldout accuracy min = 1.0
candidate total heldout accuracy min = 1.0
edge versus raw v1.8 first-heldout min = 1.0
edge versus best module sham min = 0.7083333333333333
edge versus combo memorization min = 1.0
edge versus best selected standard baseline min = 0.16666666666666663
```

Interpretation:

```text
An explicit host-side reusable-module scaffold solves held-out skill
compositions that raw v1.8, combo memorization, module reset/shuffle/order
shams, and selected standard baselines do not solve under the same diagnostic
streams.
```

Claim boundary:

```text
This is software diagnostic evidence that reusable composition is a real,
testable capability target. It is not yet native/internal CRA composition, not
module routing, not hardware evidence, not language, not planning, and not a
new frozen baseline.
```

Next:

```text
Tier 5.13b routing/gating and Tier 5.13c internal composition/routing have now
passed as separate diagnostics. The remaining promotion step is the formal
post-v1.8 baseline freeze decision after full regression discipline.
```

### Tier 5.13b: Module Routing / Contextual Gating

Purpose:

```text
test whether CRA can decide which learned module/subgraph should be active for
the current context, rather than merely owning reusable modules
```

Why this is separate from compositionality:

```text
Compositionality asks whether learned skill A can be reused inside task C.
Routing asks how the organism knows when to use skill A, ignore skill B, or
retrieve a context-specific memory/module.
```

Protocol:

```text
train multiple reusable modules on distinct cue/rule/control subtasks
present mixed-context tasks where only one module is relevant at a time
compare contextual router versus always-on modules, random router, oracle router,
and monolithic same-capacity CRA
log module activation, suppression, confidence, and routing mistakes
```

Pass:

```text
contextual routing improves sample efficiency, accuracy, recovery, or variance
random-router and always-on controls perform worse
router traces identify the selected module before the outcome is known
benefit survives held-out context/module combinations
```

Fail:

```text
routing collapses to always-on behavior
oracle routing helps but learned routing does not
router only follows labels/outcomes after the fact
monolithic CRA or external baselines dominate under the same task stream
```

Current result:

```text
status = PASS
output = controlled_test_output/tier5_13b_20260429_121615/
matrix cells = 126 / 126
feedback leakage violations = 0 / 11592 checked rows
candidate first-heldout routing accuracy min = 1.0
candidate total heldout routing accuracy min = 1.0
candidate router accuracy min = 1.0
pre-feedback route selections = 276
edge versus raw v1.8 first-heldout min = 1.0
edge versus best routing sham min = 0.375
edge versus best selected standard baseline min = 0.45833333333333337
```

Interpretation:

```text
Explicit host-side contextual routing can select the correct reusable module
under delayed/mixed context pressure where current input/history, raw v1.8,
always-on/random/reset/shuffled routing shams, and selected standard baselines
do not close the gap.
```

Important boundary:

```text
The explicit router scaffold passed, but the CRA router-input bridge did not.
This is not native/internal CRA routing yet and not a baseline freeze.
```

Next:

```text
Tier 5.13c has implemented and passed the internal host-side CRA
composition/routing gate. Proceed to Tier 5.14 working-memory/context binding
or freeze the candidate as the next baseline only after the chosen full
regression/freeze checklist is complete.
```

### Tier 5.13c: Internal Composition / Routing Promotion Gate

Purpose:

```text
move reusable-module composition and contextual routing from external scaffolds
into the CRA host loop without losing auditability or sham controls
```

Why this exists:

```text
Tier 5.13 and 5.13b proved explicit host-side scaffolds can compose and route
modules. A reviewer could still say CRA itself did not own the mechanism. Tier
5.13c tests a bounded internal host-side pathway that learns primitive module
tables and context-to-module router scores after feedback, then selects
routed/composed features before later feedback.
```

Protocol:

```text
composition tasks = heldout_skill_pair, order_sensitive_chain,
                    distractor_skill_chain
routing tasks = heldout_context_routing, distractor_router_chain,
                context_reentry_routing
seeds = 42, 43, 44
backend = mock
composition steps = 720
routing steps = 960
candidate = internal_composition_routing
upper bounds = module_composition_scaffold, contextual_router_scaffold
controls = raw v1.8, no-write, reset, skill-shuffle, order-shuffle,
           router-reset, context-shuffle, random-router, always-on,
           selected external baselines
compact regression = full Tier 5.12d
```

Current result:

```text
status = PASS
output = controlled_test_output/tier5_13c_20260429_160142/
matrix cells = 243 / 243
feedback leakage violations = 0 / 22941 checked rows
pre-feedback feature selections = 6096
candidate module updates = 192
candidate router updates = 88
candidate pre-feedback route selections = 276
composition first-heldout accuracy min = 1.0
composition heldout accuracy min = 1.0
routing first-heldout accuracy min = 1.0
routing heldout accuracy min = 1.0
routing accuracy min = 1.0
edge versus raw CRA min = 1.0
edge versus best internal sham min = 0.5
selected-standard delta min = 0.0
selected-standard delta max = 0.5
full compact regression = PASS
compact regression output = controlled_test_output/tier5_12d_20260429_122720/
baseline freeze = baselines/CRA_EVIDENCE_BASELINE_v1.9.md
```

Interpretation:

```text
The internal host-side CRA composition/routing path matches the scaffold-level
capability on tested held-out composition and routing tasks, separates cleanly
from internal shams, selects before feedback, and does not regress selected
standard baselines. One composition task is saturated by an online logistic
baseline, so the fair standard-baseline claim is "no underperformance anywhere
and a meaningful edge somewhere," not "beats every baseline on every task."
```

Claim boundary:

```text
This is noncanonical software promotion evidence for internal host-side CRA
composition/routing. It is not SpiNNaker hardware evidence, not custom-C/on-chip
routing, not language, not long-horizon planning, not AGI, and not
external-baseline superiority.
```

Next:

```text
v1.9 is now frozen as the bounded host-side software composition/routing
baseline. Continue to Tier 5.14 working-memory/context binding against v1.9.
Hardware transfer waits until software utility and regression stability are
stronger.
```

### Tier 5.14: Working Memory / Context Binding

Purpose:

```text
test whether CRA can hold recent context, cue history, active module state, or
pending subgoal information across time
```

Protocol:

```text
same current input requires different action depending on previous context
delayed match/non-match style cue tasks
contextual bandit with hidden regime memory
module-routing task with delayed context cue
compare current CRA, working-memory CRA, reset-memory ablation, shuffled-context
control, and external sequence baselines
```

Pass:

```text
working-memory CRA beats current CRA when immediate input is ambiguous
reset-memory and shuffled-context controls lose the benefit
context traces are exported and align with task events before reward arrives
benefit survives multiple seeds and held-out context combinations
```

Fail:

```text
memory state behaves as smoothing rather than context binding
benefit disappears under context shuffle
sequence baselines dominate with comparable capacity and visibility
```

Status:

```text
PASS as noncanonical software diagnostic evidence.
output = controlled_test_output/tier5_14_20260429_165409/
memory/context-binding subsuite = PASS
module-state/routing subsuite = PASS
minimum context-memory edge vs best sham = 0.5
minimum context-memory edge vs sign persistence = 0.5
minimum routing edge vs best sham = 0.5
minimum routing edge vs routing-off CRA = 1.0
memory candidate accuracy = 1.0 on all memory-pressure tasks
routing first-heldout/heldout/router accuracy = 1.0 on all routing tasks
```

Interpretation:

```text
v1.9's host-side context-memory and module-routing state survives broader
working-memory pressure. The result strengthens the software substrate claim,
but it does not freeze v2.0 by itself.
```

Boundary:

```text
software diagnostic only
host-side working-memory/context-binding only
not SpiNNaker hardware evidence
not native/custom-C on-chip working memory
not language
not long-horizon planning
not AGI
not external-baseline superiority
```

Next:

```text
Tier 5.15 has now passed as noncanonical temporal-code coverage.
Tier 5.16 has now passed as noncanonical NEST neuron-parameter sensitivity
coverage.
Tier 5.17 failed cleanly and Tier 5.17b has now classified the failure; continue
to Tier 5.17c intrinsic predictive / MI-style preexposure repair.
```

### Optional Tier 5.14b: Working-Memory Promotion Gate

Run this only if the project wants to freeze a new v2.0 baseline or make
working-memory/context-binding a formal paper-table claim before moving on.
Tier 5.14 already passed as a coverage diagnostic over frozen v1.9; it did not
introduce a new mechanism by itself.

Promotion protocol:

```text
rerun the Tier 5.14 memory and routing tasks
add a compact Tier 1/Tier 2/Tier 3 regression guardrail
include delayed_cue and hard_noisy_switching smokes
confirm reset/shuffle/no-write/random shams still lose
confirm no feedback leakage and preserve per-step memory/router traces
freeze v2.0 only if all checks pass
```

Fail/skip rule:

```text
if no mechanism changed and v1.9 already supports the bounded claim needed for
Tier 5.15, skip 5.14b and keep Tier 5.14 as noncanonical diagnostic coverage.
This is what happened before the Tier 5.15 run.
```

### Tier 5.15: Spike Encoding / Temporal Code Suite

Status: **passed as noncanonical software temporal-code diagnostic evidence**.

Purpose:

```text
test whether CRA uses spike timing as an information channel rather than only
using spikes as a transport layer for scalar host summaries
```

Why this matters:

```text
SNN reviewers will ask whether temporal spike structure matters. A stronger SNN
claim requires showing that CRA can learn when the same task is encoded through
timing, latency, bursts, or population spike patterns rather than only input
amplitude/current.
```

Protocol:

```text
tasks = fixed_pattern, delayed_cue, hard_noisy_switching, sensor_control
encodings = rate, latency, burst, population, temporal interval
same task stream and labels across encodings
same causal reward visibility
compare CRA temporal variants against current amplitude/current encoding,
STDP-only SNN, reservoir/liquid-state, surrogate-gradient SNN where feasible
```

Required traces:

```text
input spike trains
per-polyp spike timing histograms
latency/burst/population code metadata
readout bins and decoded predictions
encoding-specific spike totals and sparsity
```

Pass:

```text
CRA learns above controls under at least one genuinely temporal encoding
temporal encoding is not explained by rate alone
encoding ablations or time-shuffle controls reduce performance
results survive multiple seeds and at least one non-finance adapter
```

Fail:

```text
CRA only works under scalar/rate-like encodings
time-shuffling spike trains does not hurt performance
external temporal SNN baselines dominate under the same task stream
```

Latest result:

```text
controlled_test_output/tier5_15_20260429_135924/
status = PASS
expected_runs = observed_runs = 540
spike trace artifacts = 60
encoding metadata artifacts = 60
good genuinely temporal rows = 9
non-finance good temporal rows = 3
time-shuffle losses = 9
rate-only losses = 9
```

Interpretation:

```text
Tier 5.15 supports the bounded claim that temporal spike structure can carry
task-relevant information in the current software diagnostic. The strongest
cells are fixed_pattern, delayed_cue, and sensor_control under latency, burst,
and temporal-interval encodings. hard_noisy_switching did not show a strong
temporal-code advantage here, so this tier should not be cited as hard-switch
temporal superiority.
```

Boundary:

```text
software-only numpy_temporal_code diagnostic
not SpiNNaker hardware evidence
not custom-C/on-chip temporal coding
not a v2.0 baseline freeze
not neuron-model robustness
not unsupervised representation learning
not language/planning/AGI evidence
```

Decision:

```text
Tier 5.17 failed cleanly and Tier 5.17b classified the failure; continue to
Tier 5.17c intrinsic predictive / MI-style preexposure repair
```

### Tier 5.16: Neuron Model / Parameter Sensitivity

Status: **passed as noncanonical NEST neuron-parameter sensitivity evidence**.

Purpose:

```text
prove CRA is not a fragile artifact of one exact LIF parameterization
```

Protocol:

```text
LIF default
LIF threshold sweep
LIF membrane/synaptic tau sweep
adaptive LIF if backend support is stable
Izhikevich-style software comparison if practical
do not chase Hodgkin-Huxley unless a very specific reviewer-critical reason appears
```

Metrics:

```text
tail accuracy
correlation
recovery after switches
variance across seeds
spike rate and sparsity
runtime/resource cost
parameter robustness band
```

Latest result:

```text
controlled_test_output/tier5_16_20260429_142647/
status = PASS
backend = nest
expected_runs = observed_runs = 66
aggregate cells = 33
functional cells = 33
functional cell fraction = 1.0
default minimum tail accuracy = 0.8
collapse count = 0
parameter propagation failures = 0
sim.run failures = 0
summary-read failures = 0
synthetic fallbacks = 0
LIF response probe monotonic fraction = 1.0
```

Interpretation:

```text
The current CRA NEST path is not brittle to the tested LIF threshold,
membrane-tau, refractory, capacitance, or synaptic-tau variants on
fixed_pattern, delayed_cue, and sensor_control. Parameter propagation is now
audited, and the direct current-response probe confirms the variants change
the backend LIF response monotonically with injected current.
```

Boundary:

```text
software NEST diagnostic only
not SpiNNaker hardware evidence
not custom-C/on-chip neuron-model evidence
not adaptive-LIF or Izhikevich evidence
not a v2.0 freeze by itself
not proof that richer neuron models are unnecessary for future capabilities
```

Pass:

```text
CRA remains functional across a predeclared reasonable LIF parameter band
best claims do not depend on one narrow fragile threshold/tau setting
more complex neuron models are documented as optional robustness checks, not required for the main claim
```

Fail:

```text
learning collapses under small plausible LIF parameter changes
claims depend on a hand-tuned neuron parameter with no robustness band
more complex neuron models expose a hidden instability in the learning rule
```

Decision:

```text
continue to Tier 5.17c intrinsic predictive / MI-style preexposure repair
```

### Tier 5.17: Pre-Reward Representation Formation

Purpose:

```text
test whether CRA can build useful internal structure from unlabeled/reward-free
stream exposure before consequence-driven learning begins
```

Protocol:

```text
phase A: expose organism to unlabeled input streams with reward and labels hidden
phase B: freeze or partially freeze early structure/readout features
phase C: train on downstream delayed/nonstationary task
compare no-preexposure CRA, shuffled-preexposure CRA, reward-pretrained CRA,
STDP-only unsupervised SNN, reservoir, and current CRA
```

Required traces:

```text
preexposure spike statistics
feature/readout state before downstream training
representation drift
sample-efficiency curves after exposure
shuffle/control exposure identity
```

Pass:

```text
unlabeled exposure improves downstream sample efficiency, recovery, variance, or stability
shuffle/control exposure removes the benefit
benefit transfers to at least one held-out stream or non-finance adapter
```

Fail:

```text
preexposure has no measurable downstream value
benefit only appears when labels/rewards leak into exposure
simple reservoirs or STDP-only unsupervised baselines dominate the same protocol
```

Current result:

```text
Tier 5.17 failed cleanly as noncanonical diagnostic evidence.
Tier 5.17b passed as failure-analysis coverage, not capability promotion.
The failure classification is:
- ambiguous_reentry_context: candidate_structure_present
- latent_cluster_sequence: input_encoded_too_easy
- temporal_motif_sequence: history_baseline_dominates
```

Next repair:

```text
Tier 5.17c - intrinsic predictive / MI-style preexposure objective
```

Tier 5.17c should give CRA a label-free reason to organize the stream before
reward arrives: masked-channel prediction, temporal continuation, latent-state
prediction without labels, mutual-information stabilization, or prediction-error
reduction. It should keep the zero-label/zero-reward exposure contract, retain
input-only/history/random-projection controls, and add same-visible-input with
different latent-state tasks so simple encoders cannot solve the claim.

Do not revisit Tier 5.9 yet. The revisit rule is: only return to
delayed-credit/eligibility if a future pre-reward mechanism forms useful
structure but downstream reward cannot credit, preserve, or use it.

Current Tier 5.17c result:

```text
failed / not promoted
```

The intrinsic predictive preexposure harness completed with zero label leakage,
zero reward visibility, and zero dopamine during preexposure. It produced useful
partial signals against no-preexposure and simple history/reservoir controls,
but it did not beat target-shuffled, wrong-domain, STDP-only, and best
non-oracle controls under held-out episode probes. Reward-free representation
formation remains unproven.

Decision:

```text
do not claim reward-free representation learning
Tier 5.17d repaired the narrower predictive-binding failure
Tier 5.17e froze v2.0 after compact promotion/regression passed
Tier 5.18c froze v2.1 after self-evaluation diagnostics and compact regression passed
```

Current Tier 5.17d result:

```text
passed as bounded noncanonical predictive-binding evidence
```

Tier 5.17d fixed the specific 5.17c sham-separation problem on two valid binding
tasks: `cross_modal_binding` and `reentry_binding`. The candidate preserved the
zero-label, zero-reward, zero-dopamine contract and separated target-shuffled,
wrong-domain, fixed-history, reservoir, STDP-only, and best non-oracle controls
on held-out ambiguous episodes after cues faded.

Claim boundary:

```text
CRA can form useful pre-reward structure under tested predictive sensory-binding pressure.
```

Do not claim:

```text
general unsupervised concept learning
hardware/on-chip representation learning
full world modeling
language
planning
v2.0 freeze from Tier 5.17d alone
```

Next:

```text
completed as Tier 5.17e; Tier 5.18 and Tier 5.18c subsequently froze bounded v2.1.
```

Current Tier 5.17e result:

```text
passed as baseline-frozen v2.0 predictive-binding compact regression
```

Tier 5.17e passed all four child guardrails:

```text
v1.8 compact regression
v1.9 composition/routing
Tier 5.14 working-memory/context binding
Tier 5.17d predictive-binding
```

This freezes:

```text
baselines/CRA_EVIDENCE_BASELINE_v2.0.md
```

Claim boundary:

```text
bounded host-side software predictive-binding pre-reward structure
```

Do not claim:

```text
hardware/on-chip representation learning
general unsupervised concept learning
full world modeling
language
planning
AGI
external-baseline superiority
```

### Tier 5.18: Self-Evaluation / Metacognitive Monitoring

Status: **passed as software diagnostic evidence** at
`controlled_test_output/tier5_18_20260429_213002/`.

Observed:

```text
150/150 task/variant/seed rows completed
outcome_leakage_runs = 0
pre_feedback_monitor_failures = 0
candidate_min_primary_error_auroc = 0.986637
candidate_min_hazard_detection_auroc = 0.999055
candidate_max_brier_primary_correct = 0.0604305
candidate_max_ece_primary_correct = 0.152803
candidate_min_bad_action_avoidance = 0.763434
min_accuracy_edge_vs_v2_0 = 0.253241
min_accuracy_edge_vs_best_non_oracle = 0.250463
```

Interpretation:

```text
CRA has bounded software diagnostic evidence for pre-feedback reliability
monitoring and confidence-gated adaptation over v2.0.
```

Boundary:

```text
not consciousness
not self-awareness
not introspection
not hardware evidence
not language/planning/AGI
v2.1 freeze handled separately by Tier 5.18c
```

### Tier 5.18c: Self-Evaluation Compact Regression / v2.1 Freeze

Status: **passed as baseline-freeze gate** at
`controlled_test_output/tier5_18c_20260429_221045/`.

Observed:

```text
children_passed = 2 / 2
criteria_passed = 4 / 4
v2.0 compact regression gate remains green = pass
Tier 5.18 self-evaluation guardrail remains green = pass
runtime_seconds = 1534.207275167
```

Interpretation:

```text
v2.1 is frozen as bounded host-side software self-evaluation / reliability-monitoring evidence.
```

Boundary:

```text
not consciousness
not self-awareness
not introspection
not hardware/custom-C self-monitoring
not language/planning/AGI
not external-baseline superiority
```

Purpose:

```text
test whether CRA can estimate its own reliability, uncertainty, novelty, or
likely failure state before outcome feedback arrives
```

Protocol:

```text
known-regime calibration tasks
held-out and OOD regime streams
hidden-regime transitions
noisy/adversarial perturbations
optional abstain/request-more-evidence action when the task supports it
monitor-triggered replay/plasticity/routing hooks only after monitor-only evidence passes
```

Required controls:

```text
monitor disabled
random confidence monitor
always-confident and always-uncertain monitors
shuffled confidence labels
post-outcome/delayed-confidence leakage control
OOD label permutation
simple uncertainty baselines
```

Metrics:

```text
calibration error
pre-feedback error prediction
OOD/novelty detection
bad-action avoidance or abstention quality
recovery after monitor-triggered intervention
variance across seeds
leakage-audit rows
```

Pass:

```text
confidence/error/OOD estimates are calibrated better than random or trivial controls
monitor predictions occur before reward/label feedback
using the monitor improves adaptation, recovery, abstention quality, replay triggering, routing, or bad-action avoidance
shuffled/post-outcome/disabled monitor controls lose
v2.1 promotion requirement: compact regression remained green in the Tier 5.18c gate
```

Fail:

```text
confidence only tracks outcomes after feedback
monitor benefit disappears under leakage-safe scoring
simple uncertainty baselines dominate all monitored tasks
monitor destabilizes v1.8 controls or hides failure behind abstention
```

Boundary:

```text
This is operational reliability monitoring only. It is not consciousness,
self-awareness, human-style introspection, AGI, or proof of general autonomous
judgment.
```

## Phase 4: Organism/Lifecycle/Self-Scaling Proof

This is the part that distinguishes CRA from a fixed model. Manual N-scaling is
not the organism claim. Self-scaling is.

### Tier 6.1: Software Lifecycle/Self-Scaling Benchmark

Status: **passed and promoted as v1.2 canonical evidence**.

Observed result:

```text
backend = NEST
tasks = delayed_cue, hard_noisy_switching
seeds = 42,43,44
steps = 960
fixed controls = fixed4, fixed8, fixed16
lifecycle cases = life4_16, life8_32, life16_64
expected/actual runs = 36/36
new-polyp events = 75
event types = 74 cleavage, 1 adult birth, 0 deaths
lineage integrity failures = 0
aggregate extinctions = 0
advantage regimes = 2, both hard_noisy_switching
```

Claim supported:

```text
software lifecycle/self-scaling can expand the active reef with clean lineage
tracking and can improve hard_noisy_switching versus same-initial fixed-N
controls under the tested settings.
```

Claim not supported:

```text
full adult birth/death turnover
sham-control proof
hardware lifecycle/self-scaling
external-baseline superiority
native on-chip lifecycle
compositionality or world modeling
```

Protocol:

```text
CRA fixed-N control
CRA lifecycle-enabled
same task, same seeds, same backend
initial N = 4,8,16
max pool = 16,32,64
birth/death enabled
lineage IDs tracked
ecology pressure varied
```

Tasks:

```text
hard_noisy_switching
nonstationary_switch
contextual_bandit
sensor_control with harder delayed reward
concept drift classification
```

Pass:

```text
no ID or lineage corruption
birth/death events are real and auditable
self-scaling improves at least one of:
accuracy, recovery, variance, active-population efficiency, collapse resistance
ecology-enabled beats or complements fixed-N on hard/adaptive tasks
```

Fail:

```text
birth/death is cosmetic
lineage corrupts
self-scaling collapses or adds noise
fixed-N dominates under all conditions
```

Make-or-break:

```text
If lifecycle/self-scaling never helps, the "organism" claim must be narrowed.
CRA may still be a neuromorphic learner, but not yet an ecological organism architecture.
```

### Tier 6.3: Lifecycle Sham-Control Suite

Status: **passed and promoted as v1.3 canonical evidence**.

Purpose:

```text
prove lifecycle value is not random replacement, larger capacity, event count, or bookkeeping
```

Controls:

```text
fixed-N with same maximum pool
event-count replay with matched lifecycle events
active-mask shuffle audit
lineage ID shuffle audit
no trophic pressure
no dopamine
no plasticity
```

Observed result:

```text
backend = NEST
task = hard_noisy_switching
regimes = life4_16, life8_32
seeds = 42,43,44
steps = 960
actual runs = 36/36
intact non-handoff lifecycle events = 26
fixed capacity-control lifecycle events = 0
actual-run lineage failures = 0
aggregate extinctions = 0
performance-sham wins = 10/10
fixed max-pool wins = 2/2
event-count replay wins = 2/2
lineage-ID shuffle detections = 6/6
```

Claim supported:

```text
software lifecycle/self-scaling advantage on the tested hard_noisy_switching
regimes is not explained by extra max-pool capacity, event count alone, trophic
pressure removal, dopamine removal, plasticity removal, or lineage/mask
bookkeeping artifacts.
```

Claim not supported:

```text
hardware lifecycle/self-scaling
native on-chip lifecycle
full adult birth/death turnover
external-baseline superiority
compositionality or world modeling
```

Fail condition for future reruns:

```text
fixed max-pool or event-count replay matches or beats intact lifecycle
mechanism ablations perform the same or better under predeclared criteria
lineage/mask bookkeeping corrupts or cannot be audited
```

### Tier 6.4: Circuit Motif Causality

Status: **passed and promoted as v1.4 canonical evidence**.

Purpose:

```text
prove CRA's reef/circuit motifs are causal contributors, not decorative labels
around a readout learner
```

Motifs to test:

```text
feedforward excitation
feedback/recurrent excitation
lateral inhibition
mutual inhibition / WTA
mutual excitation where implemented
gap-junction/electrical coupling where implemented
motif diversity versus motif collapse
```

Protocol:

```text
backend = NEST
task = hard_noisy_switching
regimes = life4_16, life8_32
seeds = 42, 43, 44
steps = 960
variants = intact, no_feedforward, no_feedback, no_lateral, no_wta,
           random_graph_same_edge_count, motif_shuffled,
           monolithic_same_capacity
seed motif-diverse graph before first outcome feedback
export reef graph, motif activity, lifecycle events, lineage audit, and
intact-vs-control deltas
```

Observed canonical result:

```text
actual_runs = 48 / 48
intact motif-diverse aggregates = 2 / 2
intact motif-active steps = 1920
motif-ablation losses = 4 / 8
motif-label shuffle losses = 0 / 2
random/monolithic dominations = 0 / 4
lineage-integrity failures = 0
```

Pass:

```text
at least one predeclared motif ablation causes a specific predicted loss
motif logs show the relevant path was active before outcome feedback
same-capacity random or monolithic controls do not explain the benefit
```

Fail:

```text
all motif ablations behave the same as intact CRA
random graph or monolithic same-capacity CRA dominates
motif labels cannot be mapped to actual runtime activity
```

Boundary:

```text
This is controlled software circuit-motif causality evidence.
It is not hardware motif execution, custom-C/on-chip learning,
compositionality, world-model evidence, real-world usefulness, or universal
external-baseline superiority.
```

### Tier 4.19: Hardware Lifecycle/Self-Scaling Feasibility

SpiNNaker constraint:

```text
Do not pretend PyNN dynamically creates new populations mid-run.
Use a preallocated max pool.
Activate/silence polyps.
Make host-side lifecycle decisions at chunk boundaries.
Track IDs/lineage.
Compare to fixed-N control.
```

Protocol:

```text
max pool = 16 or 32 initially
active initial N = 8
chunked + host
birth/death decisions at chunk boundaries
tasks = hard_noisy_switching and/or best Tier 6.1 lifecycle task
seeds = 3 initially
```

Pass:

```text
hardware run completes with zero fallback/failures
real spike readback
active/inactive mask behaves correctly
birth/death/lineage log is auditable
no fake births
no ID reuse corruption
performance at least matches fixed-N or improves a predeclared metric
```

Fail:

```text
masking breaks readback
host lifecycle cannot remain synchronized
lineage events corrupt
performance collapses versus fixed-N
```

## Phase 5: Hard Synthetic Benchmarks

These bridge controlled tasks and real tasks.

### Tier 6.2: Hard Synthetic Task Suite

Tasks:

```text
delayed noisy cue with variable delay
multi-cue delayed reward
nonstationary switch with hidden regimes
contextual bandit with delayed reward
multi-armed bandit with drifting arms
concept drift online classification
anomaly detection stream
small delayed-reward navigation/gridworld
```

Comparisons:

```text
CRA fixed-N
CRA self-scaling
external baselines from Tier 5.5
ablated CRA variants
```

Pass:

```text
CRA/self-scaling shows robust advantage on at least some hard/adaptive regimes
negative controls remain negative
task-specific leakage is ruled out
results hold across seeds and run lengths
```

Fail:

```text
CRA only wins on tasks designed around CRA internals
external baselines dominate
self-scaling does not help
```

## Phase 6: Real-ish and Real Task Adapters

The paper should include more than toy tasks if the claim is usefulness.

### Tier 7.1: Real-ish Benchmark Adapters

Candidate adapters:

```text
streaming sensor prediction
anomaly detection
online concept-drift classification
small control task similar to CartPole-style signals
event-stream prediction
robot/sensor delayed control simulation
```

Pass:

```text
same CRA core API works
no trading_bridge dependency unless finance task
baselines run under same data splits/streaming rules
CRA is useful on at least one real-ish task
```

Fail:

```text
adapter requires task-specific CRA hacks
CRA cannot beat or complement simple online baselines
results are not repeatable
```

### Tier 7.2: Holdout Task Challenge

Purpose:

```text
prove CRA is not overfit to task families used during tuning
```

Protocol:

```text
freeze CRA config before opening holdout results
run at least one held-out synthetic family and one real-ish adapter
use same baseline fairness contract
include zero/shuffle controls
```

Pass:

```text
frozen CRA config remains competitive or useful on at least one held-out regime
```

Fail:

```text
CRA advantage disappears outside tuned task families
```

### Tier 7.3: Real Data Tasks

Candidate real datasets:

```text
public sensor streams
machine/anomaly datasets
financial streams as one domain only
event prediction streams
small public control/simulation logs
```

Required controls:

```text
temporal split only
no leakage
shuffle-label control
zero-signal control
baseline parity
multi-seed repeat
run-length sweep
```

Pass:

```text
CRA has a defensible useful regime on at least one real dataset
self-scaling helps or reduces collapse/variance
external baselines do not dominate every metric
```

Fail:

```text
no real-ish or real task advantage
finance-only usefulness
leakage-sensitive results
```

Make-or-break:

```text
If CRA cannot show usefulness on any real-ish task, the paper must be framed as
a neuromorphic architecture/control study, not a broadly useful learning system.
```

### Tier 7.4: Delayed-Reward Policy / Action Selection

Purpose:

```text
move beyond prediction/sign tasks into causal state -> action -> consequence
learning with delayed reward
```

Protocol:

```text
multi-action delayed-reward control task
contextual bandit with changing reward map
small sensor-control environment with action costs
exploration versus exploitation logging
compare CRA policy layer against bandit/RL baselines, recurrent baselines, and
current prediction-style CRA
```

Pass:

```text
CRA policy layer improves reward or regret versus current prediction-style CRA
action-value uncertainty or exploration traces are auditable
delayed reward is handled causally with no future leakage
advantage survives at least one non-finance control task
```

Fail:

```text
policy layer is equivalent to sign prediction with extra steps
simple bandit/RL baselines dominate all tasks
exploration causes unstable collapse or unrecoverable drift
```

### Tier 7.5: Curriculum / Environment Generator

Purpose:

```text
prove CRA is not dependent on a small set of hand-built tasks and can improve
across generated task families
```

Design:

```text
automatic task generation
difficulty scheduling
novelty/regime variation
anti-overfitting task families
held-out task families
same generated streams for CRA and baselines
```

Pass:

```text
CRA improves across generated task families without per-task hand-tuning
held-out generated families remain above controls
difficulty schedule and task seeds are reproducible
baselines receive the same stream and comparable tuning budget
```

Fail:

```text
CRA only improves on generator modes seen during tuning
curriculum hides task leakage or implicit hints
external baselines adapt better under the same generated stream
```

### Tier 7.6: Long-Horizon Planning / Subgoal Control

Purpose:

```text
test whether CRA can use memory, routing, composition, and policy layers to
pursue delayed outcomes through bounded intermediate subgoals
```

Tasks:

```text
multi-step cue/action chains
delayed reward requiring 2-5 subgoals
distractor detours and partial observability
A -> B -> C task chains with held-out recombinations
resource/energy-budget planning
```

Baselines:

```text
reactive v1.8 CRA
current best CRA without subgoal state
sign persistence and online linear baselines where meaningful
GRU/RNN sequence baselines
tabular Q-learning or simple DQN where task-compatible
model-predictive or oracle-subgoal upper bound
```

Required controls:

```text
subgoal memory reset
subgoal order shuffle
reward-time shuffle
composition/routing disabled
oracle-subgoal upper bound
future-reward leakage audit
```

Pass:

```text
CRA with subgoal control beats reactive/no-subgoal CRA on held-out long-horizon tasks
subgoal ablations hurt
standard baselines and oracle upper bounds are reported fairly
no future reward or target leakage is detected
performance degrades gracefully as horizon length increases
```

Fail:

```text
success reduces to one-step/reflex versions of the task
planner advantage disappears on held-out chains
improvements are explained by leakage, oracle hints, or task-specific hand wiring
```

Boundary:

```text
Tier 7.6 is bounded subgoal-control evidence only. It is not general planning,
language reasoning, theorem proving, open-ended agency, or AGI.
```

## Phase 7: Hardware Subset Replication Of Useful Tasks

After Tier 6 and Tier 7 identify the strongest tasks, replicate a subset on
hardware.

### Tier 7.7: Hardware Replication Of Best Benchmark

Protocol:

```text
choose one strongest hard synthetic task
choose one strongest real-ish task if compatible
chunked + host first
seeds = 3
N or max pool = chosen from software evidence
```

Pass:

```text
software advantage survives hardware constraints qualitatively
zero fallback/failures
real readback
runtime/provenance documented
```

Fail:

```text
advantage disappears on hardware
readback/runtime constraints make task invalid
hardware-specific hacks are required
```

## Phase 8: Toward Less Host Dependence

Batching is not the final architecture. It is the bridge.

Do not rip out the Python/host path until the software mechanism being moved to
hardware has already passed local controls, baselines, and parity. The C runtime
is where proven mechanisms migrate, not where unproven learning rules are first
debugged.

### Tier 4.20: Hybrid Hardware Loop

Current prerequisite audit:

```text
Tier 4.20a v2.1 hardware-transfer readiness audit = PASS
output = controlled_test_output/tier4_20a_20260429_195403/
Tier 4.20b one-seed v2.1 chunked hardware probe = PASS
output = controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass_ingested/
Tier 4.20c three-seed v2.1 chunked hardware repeat = PASS
output = controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_hardware_pass_ingested/
raw false-fail preserved = controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_raw_false_fail/
Tier 4.21a keyed context-memory bridge = LOCAL-BRIDGE PASS + PREPARED
local = controlled_test_output/tier4_21a_local_bridge_smoke/
prepared = controlled_test_output/tier4_21a_20260430_prepared/
hardware pass = controlled_test_output/tier4_21a_20260430_keyed_context_memory_seed42_hardware_pass_ingested/
Tier 4.22a custom runtime contract = PASS
contract = controlled_test_output/tier4_22a_20260430_custom_runtime_contract/
```

Tier 4.20a is not hardware evidence. It says the transfer plan is explicit:
delayed credit is ready for a chunked-host probe; keyed context memory,
predictive binding, composition/routing, replay, self-evaluation, and temporal
coding need targeted bridge adapters or probe designs; continuous/on-chip
execution remains future custom-runtime work. Macro eligibility is excluded
because Tier 5.9c failed.

Goal:

```text
reduce host intervention while preserving chunked reference behavior
```

Immediate next hardware step:

```text
Tier 4.22a0 = constrained-NEST plus sPyNNaker mapping preflight
Tier 4.22b = continuous transport scaffold
preserve Tier 4.20c and Tier 4.21a as chunked-host reference traces
```

Tier 4.20b currently wraps the proven Tier 4.16 chunked-host runner and records
the v2.1 bridge profile explicitly. The returned pass should be cited only as
one-seed v2.1 bridge/transport hardware evidence, not full native/on-chip v2.1
execution. Keyed memory, replay, predictive binding, composition/routing, and
self-evaluation still require targeted adapters before hardware-specific claims
about those mechanisms. Tier 4.20c has now passed as the repeatability gate for
this bridge. Tier 4.21a has a passing local bridge smoke and a prepared
EBRAINS capsule for keyed context memory; it is not hardware evidence until the
returned `run-hardware` artifacts pass.

Protocol:

```text
longer chunks
sparse reward/lifecycle updates
less frequent full spike readback
on-device state persists longer
host reads summaries instead of every-step traces where possible
```

Pass:

```text
matches chunked reference within tolerance
runtime improves
less host readback
no hidden synthetic fallback
```

Fail:

```text
learning depends on per-step host replay
summary readback loses needed credit assignment information
hybrid loop diverges from chunked reference
```

### Tier 4.21a: Keyed Context-Memory Hardware Bridge Probe

Goal:

```text
prove the host-side keyed context-memory scheduler can be transported through
the chunked SpiNNaker path with real spike readback
```

Scope:

```text
task = context_reentry_interference
seed = 42
variants = keyed_context_memory, slot_reset_ablation, slot_shuffle_ablation, wrong_key_ablation
steps = 720
population = 8
chunk_size_steps = 50
learning_location = host
context_memory_slots = 4
```

Status:

```text
local bridge smoke = PASS
prepared capsule = controlled_test_output/tier4_21a_20260430_prepared/
hardware evidence = PASS, one seed
```

Observed hardware result:

```text
runs = 4 / 4
sim.run failures = 0
summary/readback failures = 0
synthetic fallback = 0
minimum real spike readback = 714601
keyed memory updates = 11
keyed feature-active decisions = 20
max keyed slots used = 4
keyed all/tail accuracy = 1.0 / 1.0
best-ablation all accuracy = 0.5
total runtime = 3522.7107 seconds
```

Pass:

```text
real pyNN.spiNNaker run-hardware status = pass
all four variants complete
zero sim.run/readback/fallback failures
nonzero real spike readback
keyed memory updates observed
keyed feature active at decisions
keyed memory retains more than one slot
keyed candidate not worse than best memory ablation
```

Fail:

```text
source cannot schedule keyed memory causally inside chunks
real spike readback fails
keyed-memory telemetry stays inactive
ablations reveal the bridge is not using keyed state
hardware run requires generated local controlled_test_output artifacts
```

Boundary: Tier 4.21a is one-seed keyed-memory bridge-adapter hardware evidence
only. It is not
native/on-chip memory, custom C, continuous execution, replay, predictive
binding, composition/routing, self-evaluation, language, planning, AGI, or
external-baseline superiority.

Operational conclusion: Tier 4.21a proves one stateful v2 mechanism can ride
the current chunked-host hardware bridge. Its nearly one-hour wall time also
shows that full per-mechanism hardware bridge matrices are not sustainable.
The next engineering move should use Tier 4.20c and 4.21a as references while
starting Tier 4.22 custom/hybrid on-chip runtime work, rather than repeating
every v2 mechanism across large hardware matrices.

### Tier 4.22a: Custom / Hybrid On-Chip Runtime Contract

Status: **passed as engineering contract evidence** at
`controlled_test_output/tier4_22a_20260430_custom_runtime_contract/`.

Purpose:

```text
define the exact audited path from chunked-host hardware evidence to custom /
hybrid / on-chip runtime work before writing or running custom C
```

Key contract:

```text
4.20c and 4.21a are reference traces
do not run exhaustive per-mechanism bridge matrices by default
before future expensive hardware, run constrained-NEST plus sPyNNaker mapping preflight
assign state ownership before implementation
define parity and failure gates before speed claims
```

Constrained-NEST / sPyNNaker preflight:

```text
NEST configured to SpiNNaker-like constraints:
  LIF/PyNN-compatible cell model
  1 ms timestep unless a target backend explicitly supports another step
  bounded current ranges
  quantized/fixed-point-like clipping where relevant
  no dynamic population creation mid-run
  preallocated pools and active masks
  chunk/event schedule equivalent to the hardware runner
  compact readback mode and full-debug mode separated

sPyNNaker/PyNN preflight:
  static unsupported-feature check
  StepCurrentSource / connector / recording compliance
  map/build or tiny smoke run when a target stack is available
  resource and provenance-size estimates before full allocation
```

Boundary: constrained-NEST and sPyNNaker preflight reduce hardware-transfer
risk but do not replace physical hardware evidence. A final hardware claim
still requires returned `pyNN.spiNNaker` artifacts with real spike readback,
zero fallback, and audited task metrics.

### Tier 4.22a0: SpiNNaker-Constrained Local Preflight

Status: **passed as local pre-hardware constrained-transfer evidence** at
`controlled_test_output/tier4_22a0_20260430_spinnaker_constrained_preflight/`.

Purpose:

```text
turn the Tier 4.22a contract into an executable local gate before more EBRAINS
time is spent
```

What passed:

```text
NEST/PyNN/sPyNNaker imports
sPyNNaker required PyNN primitive feature check
constrained PyNN/NEST StepCurrentSource smoke
one-call NEST scheduled-input run with binned readback
64 returned NEST spikes, zero sim/readback failures
static bridge-source compliance
bounded population / connection / keyed-slot resource checks
fixed-point quantization probe
custom C runtime host tests
```

Claim boundary:

```text
Tier 4.22a0 reduces transfer risk.
It does not replace real hardware evidence.
It does not prove custom C, native/on-chip learning, continuous runtime, or speedup.
```

Next gate:

```text
Tier 4.22b continuous transport scaffold
```

### Tier 4.22b: Continuous Transport Scaffold

Status: **passed locally as continuous transport scaffold evidence** at
`controlled_test_output/tier4_22b_20260430_continuous_transport_local/`.

Purpose:

```text
prove scheduled input and compact/binned spike readback can run as one
continuous simulation call per task/seed case before learning/plasticity is
added
```

Current local result:

```text
backend = pyNN.nest
tasks = delayed_cue, hard_noisy_switching
seed = 42
steps = 1200
population = 8
sim.run calls = 1 per task
sim.run failures = 0
readback failures = 0
synthetic fallback = 0
minimum per-case spike readback = 101056
learning_enabled = false by design
```

Returned hardware result:

```text
output = controlled_test_output/tier4_22b_20260430_continuous_transport_hardware_pass_ingested/
backend = pyNN.spiNNaker
tasks = delayed_cue, hard_noisy_switching
seed = 42
steps = 1200
population = 8
sim.run calls = 1 per task
sim.run failures = 0
readback failures = 0
synthetic fallback = 0
minimum per-case spike readback = 94896
runtime = 111.5257s and 109.3603s
learning_enabled = false by design
```

Why learning is disabled here:

```text
Tier 4.22b isolates transport.
If transport, timing, or readback fail, a learning-enabled runtime would be
uninterpretable.
Continuous learning begins after persistent state and transport are stable.
```

Boundary:

```text
4.22b is transport evidence only.
4.22b is not a learning result.
4.22b is not speedup evidence until hardware runtime/readback costs are measured.
```

### Tier 4.22c: Persistent Custom-C State Scaffold

Status: **passed as persistent custom-runtime state scaffold evidence** at
`controlled_test_output/tier4_22c_20260430_persistent_state_scaffold/`.

Purpose:

```text
move CRA state ownership into bounded custom C before reward/plasticity
migration
```

North star:

```text
full custom/on-chip CRA execution is the destination
hybrid host paths are transitional diagnostics only
```

Current result:

```text
custom C host tests = pass
static state checks = 12 / 12
state owner = custom_c_runtime
dynamic allocation inside state_manager.c = false
bounded context slots = MAX_CONTEXT_SLOTS
state contract = keyed slots, readout state, decision/reward counters, reset semantics
```

Pass:

```text
Tier 4.22b transport reference exists
custom C host tests pass
state manager source/header exist
context slots are statically bounded
state manager avoids dynamic allocation
runtime init/reset paths own state lifecycle
state contract is exported for later reward/plasticity work
```

Boundary:

```text
4.22c is custom-C state scaffold evidence only
4.22c is not a hardware run
4.22c is not on-chip reward/plasticity learning
4.22c is not speedup evidence
```

Next gate:

```text
Tier 4.22d reward/plasticity path must use this state causally and compare
against the chunked reference
```

### Tier 4.22d: Reward / Plasticity Runtime Scaffold

Status: **passed as local custom-C reward/plasticity scaffold evidence** at
`controlled_test_output/tier4_22d_20260430_reward_plasticity_scaffold/`.

Purpose:

```text
move the first reward/plasticity mechanism into the custom C runtime after
persistent state ownership is established
```

Current result:

```text
custom C host tests = pass
static plasticity checks = 11 / 11
reward/plasticity owner = custom_c_runtime
synaptic eligibility trace = implemented
trace-gated dopamine = implemented
fixed-point trace decay = implemented
signed one-shot dopamine = implemented
runtime-owned readout reward update = implemented
```

Pass:

```text
Tier 4.22c persistent state reference exists
custom C host tests pass
synapse_t carries eligibility_trace
trace increments on causal spike delivery
dopamine update is gated by eligibility_trace
dopamine is signed fixed-point and one-shot
trace decay is on the runtime timer path
readout reward update lives in state_manager
host C tests cover trace-gated dopamine and readout reward update
```

Boundary:

```text
4.22d is local custom-C scaffold evidence only
4.22d is not a hardware run
4.22d is not continuous-learning parity yet
4.22d is not speedup evidence
4.22d does not prove scale-ready all-synapse trace sweeps
```

Next gate:

```text
Tier 4.22e local continuous-learning parity must compare this runtime
reward/plasticity path against the chunked reference before another EBRAINS run
```

### Tier 4.22e: Local Continuous-Learning Parity Scaffold

Status: **passed as local minimal delayed-readout parity evidence** at
`controlled_test_output/tier4_22e_20260430_local_learning_parity/`.

Purpose:

```text
prove the custom-C fixed-point delayed-readout equations match a floating
reference before any hardware learning claim is attempted
```

Critical leakage rule:

```text
pending horizons store feature, prediction, and due timestep only
target/reward is supplied only when the horizon matures
```

Current result:

```text
tasks = delayed_cue, hard_noisy_switching
seed = 42
steps = 1200
fixed/float sign agreement = 1.0
max final weight delta ~= 4.14e-05
max final bias delta ~= 4.72e-05
delayed_cue fixed tail accuracy = 1.0
hard_noisy_switching fixed tail accuracy = 0.547619
no-pending ablation tail accuracy = 0.0
pending drops = 0
```

Boundary:

```text
4.22e is local minimal delayed-readout parity only
4.22e is not a hardware run
4.22e is not full CRA parity
4.22e is not lifecycle/replay/routing parity
4.22e is not speedup evidence
```

Next gate:

```text
Tier 4.22f0 custom-runtime scale-readiness audit before any direct
custom-runtime hardware learning claim
```

### Tier 4.22f0: Custom Runtime Scale-Readiness Audit

Status: **passed as custom-runtime scale-readiness audit evidence** at
`controlled_test_output/tier4_22f0_20260430_custom_runtime_scale_audit/`.

Purpose:

```text
audit the custom-C sidecar for scalable data-structure/readback blockers before
spending hardware time on custom-runtime learning
```

Architecture split:

```text
PyNN/sPyNNaker = normal hardware construction, mapping, run, and standard readback
custom C = only CRA-specific on-chip substrate mechanics PyNN cannot express or scale
```

This means:

```text
do not rewrite the whole organism in C
do not rewrite baselines/evidence/paper tooling in C
do move persistent state, delayed credit, plasticity, compact summaries, and
promoted lifecycle/routing kernels toward custom on-chip code when required
```

Current result:

```text
Tier 4.22e latest status = pass
host C tests = pass
static audit checks = 9/9
scale blockers detected = 7
high-severity blockers = 3
custom_runtime_scale_ready = false
direct_custom_runtime_hardware_learning_allowed = false
```

High-severity blockers:

```text
SCALE-001 synapse_deliver_spike scans all synapses per spike
SCALE-002 synapse_decay_traces_all sweeps all synapses every millisecond
SCALE-006 READ_SPIKES exposes count/timestep only
```

Required repairs:

```text
pre-indexed outgoing adjacency: pre_id -> outgoing event/synapse list
lazy timestamp decay or active-trace list for eligibility traces
compact/fragmented readback for spikes, reward, pending horizons, slots, weights
```

Boundary:

```text
4.22f0 is an audit pass, not a scale-ready pass
4.22f0 is not a hardware run
4.22f0 is not speedup evidence
4.22f0 blocks direct custom-runtime learning hardware claims until the high
severity blockers are repaired
```

Next gate:

```text
Tier 4.22g event-indexed spike delivery plus lazy/active eligibility traces
```

### Tier 4.22g: Event-Indexed Active-Trace Runtime

Status: **passed as local custom-C optimization evidence** at
`controlled_test_output/tier4_22g_20260430_event_indexed_trace_runtime/`.

Purpose:

```text
repair the first custom-runtime scale blockers before any custom-runtime
learning hardware claim
```

Current result:

```text
Tier 4.22f0 latest status = pass
host C tests = pass
static optimization checks = 12/12
repaired blockers = SCALE-001, SCALE-002, SCALE-003
open blockers = SCALE-004, SCALE-005, SCALE-006, SCALE-007
custom_runtime_hardware_learning_allowed = false
```

Complexity delta:

```text
synapse_deliver_spike:
  before = O(S) per incoming spike
  after  = O(out_degree(pre_id)) per incoming spike

synapse_decay_traces_all:
  before = O(S) per timer tick
  after  = O(active_traces) per timer tick

synapse_modulate_all:
  before = O(S) per dopamine event
  after  = O(active_traces) per dopamine event
```

Boundary:

```text
4.22g is local C optimization evidence
4.22g is not a hardware run
4.22g is not measured speedup evidence
4.22g is not full CRA parity or final on-chip learning proof
```

Next gate:

```text
Tier 4.22h compact state readback plus build/load/command acceptance
```

### Tier 4.22h: Compact Readback / Build-Command Readiness

Status: **passed as local compact-readback/build-readiness evidence** at
`controlled_test_output/tier4_22h_20260430_compact_readback_acceptance/`.

Purpose:

```text
add compact state observability before any custom-runtime board load or
closed-loop learning attempt
```

Current result:

```text
Tier 4.22g latest status = pass
host C tests = pass
static readback/callback/SARK-SDP/router-API/build-recipe checks = 30/30, including official callback constants and packed SARK SDP guards
compact readback command = CMD_READ_STATE
schema version = 1
payload bytes = 73
aplx build status = not_attempted_spinnaker_tools_missing
board load/command roundtrip = not_attempted
custom_runtime_learning_hardware_allowed = false
```

Readback fields:

```text
timestep
neuron_count
synapse_count
active_trace_count
context slot counters
decision/reward counters
pending horizon counters
readout_weight/readout_bias
```

Boundary:

```text
4.22h is local compact-readback/build-readiness evidence
4.22h is not hardware evidence
4.22h is not board-load or command round-trip evidence
4.22h is not speedup evidence
4.22h is not custom-runtime learning evidence
```

Completed gate:

```text
Tier 4.22i tiny EBRAINS/board custom-runtime load plus CMD_READ_STATE
round-trip smoke
```


### Tier 4.22i: Custom Runtime Board Round-Trip Smoke

Status: **passed EBRAINS board-load / command-roundtrip smoke** at
`controlled_test_output/tier4_22i_20260501_ebrains_board_roundtrip_pass/`.

Prepared package retained at
`controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared/`.

Purpose:

```text
prove the custom C sidecar can build, load, and answer CMD_READ_STATE on a real
SpiNNaker board before attempting custom-runtime closed-loop learning
```

Prepared upload folder:

```text
ebrains_jobs/cra_422r
```

EBRAINS command:

```text
cra_422r/experiments/tier4_22i_custom_runtime_roundtrip.py --mode run-hardware --output-dir tier4_22i_job_output
```

Pass case:

```text
target acquired through hostname/config or pyNN.spiNNaker/SpynnakerDataView probe
local main.c syntax/callback guard passes
SARK SDP packed-field guard passes
SDP command-header guard passes
official SARK router API guard passes
.aplx build passes
custom app loads on board
RESET/BIRTH/CREATE_SYN/DOPAMINE commands acknowledge
CMD_READ_STATE returns schema version 1 with 73-byte payload
post-command state shows >=2 neurons and >=1 synapse
synthetic fallback = 0
```

Fail case:

```text
missing board hostname/target
main.c callback guard fails
SARK SDP packed-field guard fails
router API guard fails
.aplx build fails
app load fails
CMD_READ_STATE times out or returns malformed payload
SDP replies are command/status only because host/runtime command-header layout is wrong
state mutations are not visible in compact readback
```

Returned failure already preserved:

```text
controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_fail
reason = EBRAINS Spin1API did not define MC_PACKET_RX
roundtrip = not_attempted / blocked_before_roundtrip
controlled_test_output/tier4_22i_20260430_ebrains_no_mc_event_build_fail
reason = EBRAINS image also did not expose the guessed compatibility MC event names
repair = stop guessing; run Tier 4.22k Spin1API event-symbol discovery
controlled_test_output/tier4_22i_20260430_ebrains_sdp_struct_build_fail
reason = EBRAINS SARK uses packed sdp_msg_t fields and sark_mem_cpy
repair = mirror official SARK SDP fields/API in source and local stubs
controlled_test_output/tier4_22i_20260430_ebrains_router_api_build_fail
reason = EBRAINS SARK exposes rtr_alloc/rtr_mc_set/rtr_free, not local sark_router_* helpers
repair = mirror official SARK router API in source and local stubs
controlled_test_output/tier4_22i_20260430_ebrains_manual_link_empty_elf_fail
reason = manual object-only link omitted official startup/build object and libspin1_api.a
repair = delegate hardware link/APLX creation to official spinnaker_tools.mk
controlled_test_output/tier4_22i_20260430_ebrains_official_mk_nested_object_dir_fail
reason = official spinnaker_tools.mk compile path reached but build/gnu/src/ was not created
repair = create nested object directories before official compile rules emit build/gnu/src/*.o
controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_pass_target_missing_fail
reason = .aplx build passed but raw custom loader did not discover hostname/transceiver/IP
repair = add automatic target acquisition via hostname or pyNN.spiNNaker/SpynnakerDataView probe
controlled_test_output/tier4_22i_20260430_ebrains_aplx_load_pass_sdp_payload_short_fail
reason = .aplx build, target acquisition, and app load passed, but host/runtime SDP command layout used data[0] instead of official cmd_rc/seq/arg1-3/data[] layout
repair = regenerate as cra_422r with official SDP command-header guards and command/reply parsing
```

Boundary:

```text
prepared output is not hardware evidence
run-hardware pass is board-load and command round-trip evidence only
not full CRA learning
not speedup evidence
not final on-chip autonomy
```

Next if passed:

```text
Tier 4.22j minimal custom-runtime closed-loop learning smoke
```

Current gate:

```text
Tier 4.22i passed with cra_422r after Spin1API, SARK SDP, SDP command-header,
SARK router API, official spinnaker_tools.mk build-recipe, nested
object-directory, and EBRAINS target-acquisition repairs. Returned artifacts
proved .aplx build, target acquisition, app load, CMD_READ_STATE round-trip,
and visible state mutation.
```

### Tier 4.22j: Minimal Custom-Runtime Closed-Loop Learning Smoke

Status: **passed after ingest correction** at
`controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/`.

Prepared source package retained at
`controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_prepared/`.

Purpose:

```text
prove one chip-owned delayed pending/readout update after Tier 4.22i proved the
custom runtime can build, load, accept commands, and return compact state
```

Prepared upload folder:

```text
ebrains_jobs/cra_422s
```

EBRAINS command:

```text
cra_422s/experiments/tier4_22j_minimal_custom_runtime_learning.py --mode run-hardware --output-dir tier4_22j_job_output
```

Pass case:

```text
target acquired through hostname/config or pyNN.spiNNaker/SpynnakerDataView probe
.aplx build passes
custom app loads on board
RESET acknowledges
CMD_SCHEDULE_PENDING acknowledges
state_after_schedule.pending_created >= 1
state_after_schedule.active_pending >= 1
state_after_schedule.decisions >= 1
CMD_MATURE_PENDING acknowledges
matured_count >= 1
state_after_mature.pending_matured >= 1
state_after_mature.active_pending = 0
state_after_mature.reward_events >= 1
state_after_mature.readout_weight_raw > 0
state_after_mature.readout_bias_raw > 0
synthetic fallback = 0
```

Fail case:

```text
stale package/revision runs
target acquisition/build/load fails
learning commands time out or return malformed payload
pending horizon is not visible after scheduling
no pending horizon matures after the delay
readout weight/bias do not move after maturity
synthetic fallback is used
```

Returned evidence:

```text
raw remote status = fail
raw failure reason = active pending cleared
ingest classification = hardware_pass_raw_false_fail
false-fail cause = runner used active_pending or -1, converting valid 0 to -1
target acquired through pyNN.spiNNaker/SpynnakerDataView
board IP = 10.11.196.177
selected core = (0,0,4)
.aplx build = pass
app load = pass
CMD_SCHEDULE_PENDING = pass
pending_created = 1
active_pending after schedule = 1
CMD_MATURE_PENDING = pass
matured_count = 1
pending_matured = 1
active_pending after mature = 0
reward_events = 1
readout_weight = 0.25
readout_bias = 0.25
synthetic fallback = 0
```

Boundary:

```text
prepared output is not hardware evidence
ingested run-hardware pass is one minimal delayed pending/readout update only
not full CRA task learning
not v2.1 mechanism transfer
not speedup evidence
not final on-chip autonomy
```

Next if passed:

```text
Tier 4.22l tiny custom-runtime learning parity against the Tier 4.22e local float/C-equation reference (now passed; see below)
```

### Tier 4.22l: Tiny Custom-Runtime Learning Parity

Status: **passed EBRAINS hardware after ingest** at
`controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_hardware_pass_ingested/`.

Local/prepared gates retained at
`controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_local/`
and
`controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/`.

Purpose:

```text
compare the custom runtime's chip-owned pending/readout update path against a
predeclared local s16.15 fixed-point reference over four signed updates before
attempting task-like custom-runtime learning
```

Prepared upload folder:

```text
ebrains_jobs/cra_422t
```

EBRAINS command:

```text
cra_422t/experiments/tier4_22l_custom_runtime_learning_parity.py --mode run-hardware --output-dir tier4_22l_job_output
```

Reference sequence:

```text
feature= 1.0 target= 1.0
feature= 1.0 target=-1.0
feature=-1.0 target=-1.0
feature=-1.0 target= 0.5
learning_rate=0.25
expected final readout_weight_raw=-4096
expected final readout_bias_raw=-4096
```

Pass case:

```text
target acquisition/build/load pass
all schedule and mature commands acknowledge
each mature command matures exactly one pending event
observed predictions match the local reference within raw_tolerance=1
observed readout weights/biases match the local reference within raw_tolerance=1
final pending_created = 4
final pending_matured = 4
final reward_events = 4
final active_pending = 0
synthetic fallback = 0
```

Boundary:

```text
prepared/local output is not hardware evidence
returned pass is tiny signed fixed-point learning parity only
not full CRA task learning
not v2.1 mechanism transfer
not speedup evidence
not multi-core scaling
not final on-chip autonomy
```

Returned evidence:

```text
target acquisition = pass via pyNN.spiNNaker_probe / SpynnakerDataView
board IP = 10.11.194.1
selected core = (0,0,4)
.aplx build = pass
app load = pass
schedule commands = 4/4 success
mature commands = 4/4 success
matured_count = [1, 1, 1, 1]
prediction raw deltas = [0, 0, 0, 0]
weight raw deltas = [0, 0, 0, 0]
bias raw deltas = [0, 0, 0, 0]
final pending_created = 4
final pending_matured = 4
final reward_events = 4
final active_pending = 0
final readout_weight_raw = -4096
final readout_bias_raw = -4096
```

Next active gate:

```text
Tier 4.22m minimal task micro-loop on the custom runtime, still tiny and audited
```

### Tier 4.22m: Minimal Custom-Runtime Task Micro-Loop

Current status: **passed EBRAINS hardware after ingest** at:

```text
controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_local/
controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_prepared/
controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_hardware_pass_ingested/
```

Prepared upload folder and command:

```text
ebrains_jobs/cra_422u
cra_422u/experiments/tier4_22m_custom_runtime_task_micro_loop.py --mode run-hardware --output-dir tier4_22m_job_output
```

Question:

```text
Can the custom runtime execute a tiny task-like learning loop, not just arbitrary parity rows?
```

Reference task:

```text
12 signed fixed-pattern events
feature alternates +1/-1
target equals feature
score pre-update prediction sign
learning_rate = 0.25
expected accuracy = 0.9166666667
expected tail accuracy = 1.0
expected final readout_weight_raw = 32256
expected final readout_bias_raw = 0
```

Returned result: PASS. The minimal fixed-pattern task micro-loop matched the local fixed-point reference on real hardware with observed accuracy `0.9166666667`, tail accuracy `1.0`, final `pending_created=pending_matured=reward_events=decisions=12`, final `readout_weight_raw=32256`, and final `readout_bias_raw=0`. This does not prove full CRA task learning, v2.1 transfer, speedup, multi-core scaling, or final autonomy. It authorized Tier 4.22n, which has now also passed as the delayed-cue-like pending-queue micro-task below.

### Tier 4.22n: Tiny Delayed-Cue Custom-Runtime Micro-Task

Current status: **passed EBRAINS hardware after ingest** at:

```text
controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_local/
controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_prepared/
controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/
```

Prepared upload folder and command:

```text
ebrains_jobs/cra_422v
cra_422v/experiments/tier4_22n_delayed_cue_micro_task.py --mode run-hardware --output-dir tier4_22n_job_output
```

Question:

```text
Can the custom runtime hold a small rolling pending queue across intervening cue decisions and mature delayed targets in order?
```

Reference task:

```text
12 signed cue/target events
feature alternates +1/-1
target equals feature
pending_gap_depth = 2
max_pending_depth = 3
score pre-update prediction sign
learning_rate = 0.125
expected accuracy = 0.8333333333
expected tail accuracy = 1.0
expected final readout_weight_raw = 30720
expected final readout_bias_raw = 0
```

Returned result: PASS. The tiny delayed-cue-like pending-queue micro-task
matched the local fixed-point reference on real hardware: board `10.11.205.1`,
selected core `(0,0,4)`, `.aplx` build/load pass, 12 delayed schedule/mature
events, max observed pending depth `3`, prediction/weight/bias raw deltas `0`,
observed accuracy `0.8333333333`, observed tail accuracy `1.0`, final
`pending_created=pending_matured=reward_events=decisions=12`,
`active_pending=0`, `readout_weight_raw=30720`, and `readout_bias_raw=0`.
This does not prove full CRA task learning, v2.1 transfer, speedup, multi-core
scaling, or final autonomy. It authorized Tier 4.22o, now passed on EBRAINS as
the tiny noisy-switching custom-runtime micro-task.

### Tier 4.22o: Tiny Noisy-Switching Custom-Runtime Micro-Task

Current status: **returned EBRAINS pass ingested** at:

```text
controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_local/
controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_prepared/
controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/
```

Prepared upload folder and command:

```text
ebrains_jobs/cra_422x
cra_422x/experiments/tier4_22o_noisy_switching_micro_task.py --mode run-hardware --output-dir tier4_22o_job_output
```

Diagnostic update:

```text
cra_422w returned fail
classification = custom-runtime fixed-point arithmetic bug
hardware target/build/load/command path = working
repaired package = cra_422x
repair = FP_MUL now uses int64_t intermediate
```

The failed `cra_422w` run is preserved at
`controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_overflow_fail_ingested/`.
It reached real hardware, built/loaded the app, scheduled and matured all 14
pending horizons, and then diverged from the local reference at the first
signed regime-switch update because a large negative s16.15 product overflowed
32-bit before shifting. This is not evidence against CRA's learning claim; it
is repaired custom-runtime arithmetic evidence.

Returned repaired `cra_422x` pass:

```text
board = 10.11.210.25
selected core = (0,0,4)
criteria = 44/44 passed
observed accuracy = reference accuracy = 0.7857142857
observed tail accuracy = reference tail accuracy = 1.0
observed max pending depth = 3
prediction/weight/bias raw deltas = all 0
final pending_created = pending_matured = reward_events = decisions = 14
final active_pending = 0
final readout_weight_raw = -48768
final readout_bias_raw = -1536
```

Question:

```text
Can the custom runtime match a tiny noisy-switching fixed-point reference while still holding pending decisions across intervening events?
```

Reference task:

```text
14 signed events
regime A maps feature -> target
regime B maps feature -> opposite target
one label-noise event in each regime
pending_gap_depth = 2
max_pending_depth = 3
score pre-update prediction sign
learning_rate = 0.375
expected accuracy = 0.7857142857
expected tail accuracy = 1.0
expected final readout_weight_raw = -48768
expected final readout_bias_raw = -1536
```

This returned pass means only that the tiny noisy-switching pending-queue
micro-task matched the local fixed-point reference on real hardware. It does
not prove full CRA hard_noisy_switching, v2.1 transfer, speedup, multi-core
scaling, or final autonomy.

### Tier 4.22p: Tiny A-B-A Reentry Custom-Runtime Micro-Task

Current status: **returned hardware pass ingested** at:

```text
controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_local/
controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_prepared/
controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_hardware_pass_ingested/
```

Prepared upload folder and command:

```text
ebrains_jobs/cra_422y
cra_422y/experiments/tier4_22p_reentry_micro_task.py --mode run-hardware --output-dir tier4_22p_job_output
```

Question:

```text
Can the custom runtime adapt through A -> reversed B -> A reentry while delayed decisions remain pending across intervening events?
```

Reference task:

```text
30 signed events
regime A initial maps feature -> target
regime B maps feature -> opposite target
regime A reentry maps feature -> target again
pending_gap_depth = 2
max_pending_depth = 3
score pre-update prediction sign
learning_rate = 0.5625
expected accuracy = 0.8666666667
expected tail accuracy = 1.0
expected second-half improvement = 0.2666666667
expected final readout_weight_raw = 30810
expected final readout_bias_raw = -1
```

Returned result:

```text
board = 10.11.222.17
selected core = (0,0,4)
criteria = 44/44
events = 30 schedule/mature pairs
prediction/weight/bias raw deltas = 0
observed accuracy = 0.8666666667
observed tail accuracy = 1.0
observed max pending depth = 3
final readout_weight_raw = 30810
final readout_bias_raw = -1
```

This means only that the tiny A-B-A pending-queue micro-task matched the local
fixed-point reference on real hardware. It does not prove full CRA recurrence,
v2.1 memory/replay/routing transfer, speedup, multi-core scaling, or final
autonomy.

### Tier 4.22q: Tiny Integrated V2 Bridge Custom-Runtime Smoke

Current status: **returned hardware pass ingested** at:

```text
controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_local/
controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_prepared/
controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_hardware_pass_ingested/
```

Prepared upload folder and command:

```text
ebrains_jobs/cra_422z
cra_422z/experiments/tier4_22q_integrated_v2_bridge_smoke.py --mode run-hardware --output-dir tier4_22q_job_output
```

Question:

```text
Can a tiny host-side keyed-context plus routing bridge feed a signed stream
into the custom runtime while the chip-owned pending/readout loop still matches
the local fixed-point reference?
```

Reference task:

```text
30 signed host-bridge events
context keys = ctx_A, ctx_B, ctx_C
context updates = 9
route updates = 9
max keyed slots = 3
feature source = host_keyed_context_route_transform
pending_gap_depth = 2
max_pending_depth = 3
learning_rate = 0.25
expected accuracy = 0.9333333333
expected tail accuracy = 1.0
expected second-half improvement = 0.1333333333
expected final readout_weight_raw = 32768
expected final readout_bias_raw = 0
```

Pass boundary:

```text
LOCAL/PREPARED = source bundle and local s16.15 reference are ready
PASS = returned EBRAINS artifacts show real board target, .aplx build/load,
       30 schedule/mature pairs, bridge metadata checks, raw parity, pending
       counters, and task metrics matching the local reference
```

Returned result:

```text
board = 10.11.236.65
selected core = (0,0,4)
remote criteria = 47/47
ingest criterion = pass
events = 30 schedule/mature pairs
prediction/weight/bias raw deltas = 0
observed accuracy = 0.9333333333
observed tail accuracy = 1.0
observed max pending depth = 3
bridge context/route updates = 9/9
bridge max keyed slots = 3
final readout_weight_raw = 32768
final readout_bias_raw = 0
```

This is intentionally not a native/on-chip v2 memory/routing claim. The host
still computes the tiny v2-style bridge feature stream; the custom runtime owns
pending horizons, pre-update prediction, delayed readout maturation, and compact
state reporting. This justifies only the next small custom-runtime integration
gate, not full CRA v2 transfer, speedup, scaling, or final autonomy.

### Tier 4.22k: Spin1API Event-Symbol Discovery

Status: **passed EBRAINS toolchain/header discovery** at
`controlled_test_output/tier4_22k_20260430_ebrains_event_symbol_discovery_pass/`.

Purpose:

```text
inspect the actual EBRAINS build-image headers and compile callback probes
before another raw custom-runtime board job
```

Prepared upload folder:

```text
ebrains_jobs/cra_422k
```

EBRAINS command:

```text
cra_422k/experiments/tier4_22k_spin1api_event_discovery.py --mode run-hardware --output-dir tier4_22k_job_output
```

Pass case:

```text
Spin1API headers are inspectable
spin1_callback_on is visible
TIMER_TICK callback probe compiles
SDP_PACKET_RX callback probe compiles
at least one real MC receive event candidate compiles
probe matrix and header inventory are returned
```

Returned result:

```text
include_dir = /home/jovyan/spinnaker/spinnaker_tools/include
compiler = /usr/bin/arm-none-eabi-gcc
MC_PACKET_RECEIVED = compile pass
MCPL_PACKET_RECEIVED = compile pass
MC_PACKET_RX = undeclared
MCPL_PACKET_RX = undeclared
```

Fail case:

```text
no direct custom-runtime learning hardware
no promotion of SDP-only buildability
repair receive path using returned headers and documented Spin1API/SCAMP semantics
```

Boundary:

```text
not board execution
not app load
not command round-trip
not learning
not speedup
not evidence that full custom runtime is ready
```

Next if passed:

```text
patch Tier 4.22i to the confirmed event symbol
rerun custom-runtime board load + CMD_READ_STATE smoke
only then attempt Tier 4.22j minimal custom-runtime closed-loop learning smoke
```

### Tier 4.22: Custom C / On-Chip Prototype

Goal:

```text
prove a minimal custom runtime/on-chip CRA capsule can maintain state,
plasticity/reward, and readback with minimal host intervention
```

Scope:

```text
minimal task first
fixed pool
on-chip spike state
native or hybrid eligibility traces
on-chip or near-chip reward/plasticity state
optional replay/consolidation state only after software replay passes
host sends compact commands
read back summaries/provenance
```

Native eligibility trace requirements:

```text
trace increments on causal spike/pre-post activity
trace decays by audited timestep or lazy timestamp update
dopamine binds to trace rather than blindly shifting every weight
negative and positive dopamine semantics are specified
fixed-point range and half-life quantization are tested
per-synapse versus per-neuron memory cost is measured
runtime avoids sweeping every synapse every millisecond unless scale limits are accepted
```

Sleep/replay hardware requirements:

```text
software replay must pass before hardware replay begins
replay input must be explicitly scheduled, not implied by a function call
replay windows must be separated from online evaluation
replay/consolidation logs must identify which memories were replayed and why
host-led replay, hybrid replay, and on-chip replay must be labeled separately
```

Pass:

```text
real hardware build/load/run
input stream handled on chip
state persists
native or hybrid trace behavior matches software reference qualitatively
learning metric matches chunked reference qualitatively
provenance distinguishes model failure from transport failure
```

Fail:

```text
cannot build/load reliably
cannot read back state
cannot preserve learning behavior
host still does the whole learning loop
trace/replay behavior cannot be audited
```

### Tier 4.23: Continuous / Stop-Batching Parity

Current status: **4.25B HARDWARE PASS - INGESTED (23/23 criteria)**.

Tier 4.23a local reference result:

```text
output = controlled_test_output/tier4_23a_20260501_continuous_local_reference/
status = pass
passed_count = 21 / 21
accuracy = 0.9583333333333334
tail_accuracy = 1.0
max_pending_depth = 3
final_readout_weight_raw = 32768
final_readout_bias_raw = 0
autonomous_timesteps = 50 (48 events + 2 gap drain)
host_intervention_count = 0
all feature/prediction/weight/bias raw deltas = 0
zero_synthetic_fallback = True
```

Claim boundary: LOCAL only. Proves continuous loop logic matches chunked 4.22x reference exactly. NOT hardware evidence, NOT full continuous on-chip learning, NOT speedup evidence.

Tier 4.23 is a contract/bridge gate, not a mechanism promotion. It defines
the scientifically auditable boundary for moving from per-step or chunked
host-command replay to a timer-driven autonomous event loop.

**Question:** Can the custom runtime preserve the same learning behavior
without per-step or frequent chunk-level host learning replay?

**Hypothesis:** A compact event schedule uploaded to chip-owned SDRAM/DTCM,
combined with a timer-driven event loop that autonomously schedules and
matures pending credit, can reproduce the chunked reference within
predeclared tolerance.

**Null hypothesis:** The chip cannot maintain correct pending-horizon order,
feature computation, or readout updates without host-per-step commands, OR
timing differences make parity impossible even if the logic is correct.

**Claim boundary:** A PASS proves the custom runtime can execute a bounded
event stream autonomously and match the chunked reference within tolerance.
It is NOT full continuous on-chip learning for arbitrary tasks, NOT full
v2.1 mechanism migration, NOT speedup evidence, NOT multi-core scaling,
and NOT final autonomy.

**Nonclaims:**
- Arbitrary-length continuous streams (bounded schedule first).
- Dynamic task generation on chip (static schedule first).
- Full CRA organism loop (only delayed-credit readout primitive).
- Host-less operation (host still loads, starts, and reads back).
- Generalization to new tasks without reload.

**Continuous event-loop contract summary (draft v0.1):**
- Host uploads a compact schedule to chip SDRAM via SDP bulk write or
  sequence of CMD_WRITE_SCHEDULE_ENTRY commands.
- Each schedule entry contains: timestep, context_key, route_key,
  memory_key, cue (s16.15), target (s16.15), delay (timesteps).
- Host sends CMD_RUN_CONTINUOUS (proposed) to start autonomous execution.
- Timer callback each tick:
    a. Check if current timestep matches next schedule entry.
    b. If yes: perform context/route/memory lookup, compute feature,
       schedule pending horizon with due_timestep = current + delay.
       Record pre-update prediction for scoring.
    c. Check if any pending horizon has due_timestep == current.
       If yes: mature oldest-first, update readout weight/bias.
    d. Increment decision/reward counters as appropriate.
- Run continues until schedule exhausted OR host sends CMD_PAUSE/CMD_RESET.
- Host reads back compact state via CMD_READ_STATE after run completes.

**Host command cadence:**
```text
1. CMD_RESET - once at start.
2. Schedule upload - once before run (may be multiple SDP packets).
3. CMD_RUN_CONTINUOUS - once to start autonomous execution.
4. CMD_READ_STATE - once at end (or optionally periodic during long runs).
5. CMD_RESET - once to clear before next run.
Total host commands per 48-event run: <= 5 (excluding schedule upload chunks).
```

**State ownership:**
```text
CHIP-OWNED:
    - context_slots, route_slots, memory_slots
    - pending_horizon queue
    - readout_weight, readout_bias
    - decision_counter, reward_counter
    - current schedule pointer/index
HOST-OWNED:
    - full event schedule (uploaded to chip SDRAM but owned by host)
    - task stream generation logic
    - reference comparison / scoring
    - provenance recording
SHARED (protocol-defined):
    - g_timestep (chip advances, host reads)
    - compact readback buffer
```

**Compact readback cadence:**
- Default: read back once at end of run.
- Optional: read back every N timesteps for long runs (N predeclared, e.g. 16).
- Fields required: decisions, rewards, pending_depth, readout_weight_raw,
  readout_bias_raw, last_prediction_raw, last_feature_raw, slot hit/miss counters.
- Format: reuse CMD_READ_STATE 73-byte payload where possible; add
  provenance fields if needed.

**Parity tolerance vs chunked reference:**
- feature raw delta: abs <= 1 for every event
- prediction raw delta: abs <= 1 for every event
- weight raw delta: abs <= 1 for every event
- bias raw delta: abs <= 1 for every event
- accuracy: within 0.01 of reference (0.958333 -> >= 0.948333)
- tail_accuracy: within 0.01 of reference (1.0 -> >= 0.99)

Rationale: timing differences in a continuous loop may cause minor fixed-point
shifts, but the learning trajectory must remain materially identical.

Tier 4.23 must proceed in order:

```text
4.23 contract definition  = COMPLETED
4.23a local fixed-point continuous reference = COMPLETED (21/21 criteria)
4.23b custom-runtime continuous/event-loop implementation = COMPLETED (28/28 host tests)
4.23c one-board hardware continuous smoke = COMPLETED (22/22 run-hardware + 15/15 ingest criteria)
4.24 resource characterization = COMPLETED (14/14 criteria local)
4.24b EBRAINS build/size capture = COMPLETED (10/10 run-hardware + 11/11 ingest criteria)
4.25a multi-core mapping feasibility analysis = COMPLETED (14/14 criteria)
4.25b two-core state/learning split smoke = COMPLETED (23/23 run-hardware + ingest criteria)
4.25c two-core state/learning split repeatability = COMPLETED (23/23 run-hardware + ingest criteria per seed, 3 seeds)
```

The contract predeclares:

```text
exact tiny task subset: 48-event signed delayed-cue stream (same as 4.22x)
reference traces: local fixed-point simulation, seed 42
chip-owned versus host-owned state: see State ownership above
maximum allowed host interventions: <= 5 commands per run (excluding upload chunks)
compact readback cadence: once at end; optionally every N timesteps
numeric parity tolerance: raw deltas abs <= 1; accuracy within 0.01
resource/runtime metrics: ITCM/DTCM/SDRAM/APLX size, timer tick, wall time
controls: chunked reference, zero-schedule, single-event, wrong-key
failure classes: build/load, upload, event-loop stall, feature divergence,
                 pending order wrong, readback mismatch, accuracy below tolerance,
                 host intervention too high
claim boundary and nonclaims: see above
```

Pass:

```text
continuous/hybrid run matches reference within numeric tolerance
fewer host learning interventions than chunked-host path
no synthetic shortcuts
valid compact readback/provenance
repeatable after initial smoke when promoted
```

Fail:

```text
continuous mode cannot preserve credit assignment
results cannot be audited
host must still intervene too often
state ownership is ambiguous
```

## Phase 9: Integrated Paper Suite

This is the paper-grade final matrix.

### Tier 8.1: Final Software Matrix

Minimum:

```text
CRA fixed-N
CRA self-scaling
ablation variants
expanded external baselines
hard synthetic tasks
real-ish tasks
steps = multiple horizons
seeds = at least 10 where practical
```

Pass:

```text
clear useful regime
self-scaling adds measurable value
baselines documented honestly
effect sizes and confidence intervals exported
```

### Tier 8.2: Final Hardware Matrix

Minimum:

```text
delayed_cue hardware repeat
hard_noisy_switching hardware repeat
best hard synthetic or real-ish task subset
runtime characterization
hardware lifecycle feasibility if Phase 4 passes
```

Pass:

```text
hardware supports the paper's core transfer claim
hardware limits are documented
no overclaiming full on-chip if not achieved
```

### Tier 8.3: Final Claim Lock

Before writing:

```text
freeze final evidence baseline; current latest historical lock is v1.8
lock registry
export paper table
rerun audit
produce figure set
write limitations
write failure results honestly
```

Required figures:

```text
architecture diagram
evidence ladder
controls/ablations summary
baseline comparison heatmap
learning curves
self-scaling lifecycle trace
hardware transfer traces
runtime characterization plot
claim-boundary table
```

### Tier 8.4: Independent Reproduction Capsule

Purpose:

```text
make the paper rerunnable outside this working session
```

Pass:

```text
fresh checkout plus documented environment reproduces software registry and paper figures
artifact manifests and hashes match where practical
known hardware-only steps have clear ingest/reproduction instructions
```

Fail:

```text
results require local hidden state or undocumented manual steps
figures cannot be regenerated from registry/artifacts
```

## Paper-Ready Claim Levels

### Weak Paper Claim

Acceptable if:

```text
controlled proof is strong
hardware transfer works for minimal and delayed tasks
baselines are mixed
self-scaling is not yet proven
```

Claim:

```text
CRA is a controlled neuromorphic ecological learning prototype with hardware
capsule evidence and clear future lifecycle work.
```

### Strong Paper Claim

Acceptable if:

```text
expanded baselines show a robust useful regime
self-scaling/lifecycle helps
hardware transfer works on delayed/adaptive tasks
catastrophic-forgetting tests show retained or faster-reacquired regimes
real-ish tasks show usefulness
```

Claim:

```text
CRA is a functional organism-style neuromorphic learning architecture whose
ecological mechanisms improve adaptation under delayed, noisy, or nonstationary
conditions and can transfer to SpiNNaker hardware.
```

### Paradigm-Shifting Claim

Only acceptable if:

```text
self-scaling is demonstrably useful
CRA beats or complements strong baselines on hard/real-ish tasks
multi-timescale memory and delayed eligibility mechanisms add measurable value
predictive/context modeling improves at least one hard nonstationary task
compositional skill reuse improves held-out task combinations
self-evaluation/metacognitive monitoring improves calibrated failure handling
long-horizon subgoal control improves bounded multi-step tasks
hardware transfer is repeatable
hybrid/on-chip path is credible
limitations are well characterized
```

Claim:

```text
CRA provides evidence for a post-backprop, organism-style neuromorphic learning
paradigm based on local plasticity, trophic ecology, delayed credit, and
lifecycle pressure, with explicit memory, prediction, and compositional reuse
mechanisms where they are empirically useful, plus bounded self-monitoring and
subgoal-control evidence only if those later gates pass.
```

Do not use this claim unless the evidence actually reaches it.

## Immediate Next Steps

From the exact current point:

```text
1. Freeze v0.7 as the post-4.16b harder-task hardware-transfer baseline.
2. Freeze v0.8 as the post-4.18a chunked-runtime hardware baseline.
3. Treat the first returned Tier 4.16b hard_noisy_switching attempt as noncanonical failure evidence superseded by the repaired pass.
4. Treat corrected Tier 4.16b-debug as superseded by aligned bridge-repair diagnostics.
5. Treat aligned Tier 4.16b bridge repair as locally passed on NEST/Brian2: classification `hardware_transfer_or_timing_failure`.
6. Treat repaired seed `44` hard-switch hardware as a noncanonical one-seed probe pass superseded by the three-seed repeat.
7. Treat repaired three-seed Tier 4.16b hardware as canonical hard-switch transfer evidence.
8. Treat Tier 4.18a as canonical runtime/resource evidence and use `chunk_size_steps=50` as the current v0.7 hardware default.
9. Keep Tier 0.9 reproduction hygiene current while all later work proceeds.
10. Run Tier 4.18b expanded runtime characterization only if chunk `100` or additional seeds are worth the hardware cost.
11. Promote Tier 5.5 expanded baselines as v0.9 controlled software evidence.
12. Promote Tier 5.6 baseline unsupported speculationrparameter fairness audit as v1.0 controlled software evidence.
13. Promote Tier 5.7 compact regression as v1.1 controlled software evidence.
14. Promote Tier 6.1 lifecycle/self-scaling as v1.2 controlled software evidence.
15. Promote Tier 6.3 lifecycle sham controls as v1.3 controlled software evidence.
16. Promote Tier 6.4 circuit motif causality as v1.4 controlled software evidence.
17. Add an adult-turnover stressor only if the organism claim needs explicit birth/death replacement rather than cleavage-dominated expansion.
18. Treat Tier 5.9a macro eligibility and Tier 5.9b residual repair as failed noncanonical diagnostics; revive macro credit only if a later measured blocker specifically requires it.
19. Treat Tier 5.10 multi-timescale memory as failed noncanonical mechanism evidence.
20. Treat Tier 5.10b as a passed noncanonical task-validation gate: repaired memory-pressure tasks are ready, but no CRA memory mechanism is promoted by 5.10b alone.
21. Treat Tier 5.10c as a passed noncanonical software mechanism diagnostic: explicit host-side context binding works on the repaired tasks, but it is not native/internal CRA memory yet.
22. Treat Tier 5.10d as a passed noncanonical internal software-memory diagnostic: internal host-side context memory matches the scaffold and survives ablations plus full compact regression, but it is not native on-chip memory, sleep/replay, hardware transfer, or solved catastrophic forgetting.
23. Treat Tier 5.10e as a passed noncanonical internal memory retention stressor: internal host-side context memory survives longer gaps, denser distractors, and recurrence pressure with `1.0` all accuracy on all stress tasks; by itself it did not justify sleep/replay, but Tier 5.11a later supplied a measured silent-reentry need.
24. Freeze v1.5 as the post-Tier-5.10e internal memory-retention baseline.
25. Treat Tier 5.10f as a failed noncanonical capacity/interference stressor: it narrows v1.5 by showing single-slot memory misbinds under overlapping/intervening/reentry pressure.
26. Treat Tier 5.10g as passed baseline-frozen keyed-memory repair evidence: bounded keyed slots repair the 5.10f failure, match oracle-key behavior on tested tasks, beat v1.5 single-slot memory and ablations, and preserve compact regression.
27. Freeze v1.6 as the post-Tier-5.10g internal keyed context-memory baseline.
28. Treat Tier 5.11a as a passed noncanonical need diagnostic: v1.6 no-replay fails silent reentry tails while unbounded/oracle controls solve them, producing `replay_or_consolidation_needed`.
29. Do not freeze v1.7 from 5.11a; it is a need test, not a replay mechanism.
30. Treat Tier 5.11b as failed/non-promoted replay-intervention evidence: prioritized replay repaired the no-replay failure, but the shuffled-replay sham came too close on `partial_key_reentry`.
31. Treat Tier 5.11c as failed/non-promoted priority-specific replay evidence: sharper wrong-memory/no-write controls separate from the candidate, but shuffled-order replay still comes too close.
32. Treat Tier 5.11d as passed baseline-frozen correct-binding replay/consolidation evidence: the candidate repairs silent reentry, separates from wrong-key/key-label/priority-only/no-consolidation controls, and preserves compact regression.
33. Freeze v1.7 as the post-Tier-5.11d host-side replay/consolidation baseline; do not claim priority weighting, native/on-chip replay, or hardware memory transfer.
34. Treat Tier 5.12a as passed noncanonical predictive task-validation evidence; it authorizes mechanism testing but is not predictive coding or world modeling.
35. Treat Tier 5.12b as a failed noncanonical predictive-context diagnostic: the path matched the scaffold, but wrong-sign coding was not an information-destroying sham and the absolute masked-task gate was too blunt.
36. Treat Tier 5.12c as passed visible predictive-context software evidence: the candidate matched the scaffold, beat v1.7, beat shuffled/permuted/no-write shams, and beat selected external baselines.
37. Freeze v1.8 after Tier 5.12d compact regression: all old guardrails, v1.7 replay/consolidation, and compact predictive sham separation stayed green.
38. Treat Tier 5.13 as a passed noncanonical compositional-skill diagnostic: explicit host-side reusable-module composition solves held-out skill combinations; before Tier 5.13c, native/internal CRA composition and module routing remained unproven.
39. Treat Tier 5.13b as a passed noncanonical module-routing diagnostic: explicit host-side contextual routing selects the correct module before feedback; before Tier 5.13c, native/internal CRA routing and bridge integration remained unproven.
40. Freeze v1.9 after Tier 5.13c and a fresh full compact regression: internal host-side composition/routing separates from internal shams and preserves guardrails, but is not hardware/on-chip routing, language, planning, AGI, or external-baseline superiority.
41. Treat Tier 5.14 as passed noncanonical working-memory/context-binding diagnostic evidence: v1.9 host-side context/cue memory and delayed module-state routing survive broader working-memory pressure, but this is not hardware/on-chip working memory, language, planning, AGI, external-baseline superiority, or a v2.0 freeze by itself.
42. Treat Tier 5.15 as passed noncanonical software temporal-code diagnostic evidence: temporal CRA learns from latency, burst, and temporal-interval codes on fixed_pattern, delayed_cue, and sensor_control; time-shuffle and rate-only controls lose on the successful temporal cells. It is not hardware/on-chip temporal coding, not a v2.0 freeze, and not hard-switch temporal superiority.
43. Treat Tier 5.16 as passed noncanonical NEST neuron-parameter sensitivity evidence: 66/66 runs completed across 11 LIF variants with all 33 task/variant cells functional, zero parameter-propagation failures, zero fallback/failure counters, zero collapse rows, and monotonic direct LIF response probes. It is not SpiNNaker hardware evidence, custom-C/on-chip neuron evidence, adaptive/Izhikevich evidence, or a v2.0 freeze.
44. Treat Tier 5.17 as failed noncanonical pre-reward representation diagnostic evidence: the no-label/no-reward harness completed with zero non-oracle leakage and zero raw dopamine, but the strict no-history-input scaffold failed probe/sham-separation/sample-efficiency gates.
45. Treat Tier 5.17b as passed failure-analysis coverage, not a capability promotion: it classified one positive subcase, one input-encoded/easy task, and one temporal task dominated by fixed-history controls; it routes the repair to Tier 5.17c intrinsic predictive / MI-style preexposure and does not justify returning to Tier 5.9 yet.
46. Treat Tier 5.17c as failed noncanonical intrinsic predictive preexposure evidence: zero leakage/dopamine and partial gains were present, but the candidate did not clear held-out episode probe accuracy or target-shuffled/wrong-domain/STDP-only/best-control separation. Reward-free representation learning remains unpromoted.
47. Treat Tier 5.17d as passed bounded noncanonical predictive-binding evidence: cross-modal and reentry binding passed zero-leakage, target-shuffled, wrong-domain, history/reservoir, STDP-only, and best-control gates on held-out ambiguous episodes.
48. Freeze v2.0 after Tier 5.17e: v1.8 compact regression, v1.9 composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d predictive-binding guardrails all pass. v2.0 is bounded host-side predictive-binding evidence, not hardware representation, general unsupervised concept learning, full world modeling, language, planning, AGI, or external-baseline superiority.
49. Treat Tier 5.18 as passed noncanonical self-evaluation / metacognitive-monitoring diagnostic evidence: the 150-run matrix completed with zero outcome leakage and zero pre-feedback monitor failures, but Tier 5.18 alone does not freeze v2.1 or prove consciousness/self-awareness, hardware self-monitoring, language, planning, AGI, or external-baseline superiority.
50. Freeze v2.1 after Tier 5.18c: the full v2.0 compact gate and Tier 5.18 guardrail both pass. v2.1 is bounded host-side software self-evaluation / reliability-monitoring evidence, not consciousness, self-awareness, introspection, SpiNNaker/custom-C/on-chip self-monitoring, language, long-horizon planning, AGI, or external-baseline superiority.
51. Treat Tier 5.9c as failed noncanonical macro-eligibility recheck evidence: the full v2.1 guardrail passed, but macro residual still failed trace-ablation specificity, so macro eligibility remains parked and should not move to hardware/custom C.
52. Treat Tier 4.20a as passed engineering transfer audit evidence: v2.1 mechanisms are classified by chunked-host readiness versus future custom-runtime/on-chip blockers. It is not hardware evidence; it authorized Tier 4.20b only.
53. Treat Tier 4.20b as passed one-seed v2.1 chunked-host bridge/transport hardware evidence from `controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass_ingested/`: real pyNN.spiNNaker execution, zero fallback, zero sim.run/readback failures, nonzero spike readback, macro eligibility excluded. It is not native/on-chip v2.1 mechanism evidence.
54. Treat Tier 4.20c as passed three-seed v2.1 chunked-host bridge repeat evidence from `controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_hardware_pass_ingested/`: six real `pyNN.spiNNaker` child runs, seeds 42/43/44, delayed_cue plus hard_noisy_switching, zero fallback, zero `sim.run`/readback failures, nonzero spike readback, macro eligibility excluded. Preserve the raw wrapper false-fail under `controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_raw_false_fail/`; the failure was the missing local Tier 4.20b prerequisite manifest in the minimal EBRAINS source bundle, not a hardware/science failure.
55. Treat Tier 4.21a as passed one-seed keyed-context-memory bridge hardware evidence from `controlled_test_output/tier4_21a_20260430_keyed_context_memory_seed42_hardware_pass_ingested/`: four real `pyNN.spiNNaker` variants, zero fallback, zero `sim.run`/readback failures, active keyed-memory telemetry, keyed all/tail accuracy `1.0/1.0`, and best-ablation all accuracy `0.5`. It is not native/on-chip memory or broader v2 mechanism transfer.
56. Do not run large per-mechanism hardware bridge matrices by default; Tier 4.21a runtime was about `3522.7107` seconds for one seed/four variants.
57. Treat Tier 4.22a as passed engineering contract evidence from `controlled_test_output/tier4_22a_20260430_custom_runtime_contract/`: it defines constrained-NEST plus sPyNNaker mapping preflight, state ownership, parity gates, and memory/resource budgets before custom runtime implementation. It is not custom C, native/on-chip execution, continuous runtime, speedup evidence, or new hardware science evidence.
58. Treat Tier 4.22a0 as passed local constrained-transfer preflight from `controlled_test_output/tier4_22a0_20260430_spinnaker_constrained_preflight/`: NEST/PyNN/sPyNNaker imports, sPyNNaker feature checks, constrained NEST scheduled-input/binned-readback smoke, static bridge compliance, resource/fixed-point checks, and custom C host tests passed. It is not real hardware evidence, custom-C hardware execution, native/on-chip learning, continuous runtime, or speedup evidence.
59. Use Tier 4.20c and Tier 4.21a as chunked-host reference traces while starting Tier 4.22 custom/on-chip runtime work. Hybrid paths are transitional diagnostics, not the destination.
60. Treat Tier 4.22b as passed continuous-transport scaffold evidence: local PyNN/NEST passed at `controlled_test_output/tier4_22b_20260430_continuous_transport_local/`, and the EBRAINS hardware transport probe passed at `controlled_test_output/tier4_22b_20260430_continuous_transport_hardware_pass_ingested/` with real `pyNN.spiNNaker`, one `sim.run` per task, zero fallback/failures, and minimum per-case spike readback `94896`. It is not learning evidence, custom-C execution, native/on-chip learning, continuous-learning parity, or speedup evidence.
61. Treat Tier 4.22c as passed persistent custom-C state scaffold evidence from `controlled_test_output/tier4_22c_20260430_persistent_state_scaffold/`: host C tests passed, 12/12 static state checks passed, bounded keyed slots/readout/counter/reset state is owned by the custom runtime, and `state_manager.c` avoids dynamic allocation. It is not hardware evidence, reward/plasticity learning, speedup evidence, or full CRA deployment.
62. Treat Tier 4.22d as passed local custom-C reward/plasticity scaffold evidence from `controlled_test_output/tier4_22d_20260430_reward_plasticity_scaffold/`: host C tests passed, 11/11 static checks passed, eligibility traces, trace-gated dopamine, fixed-point trace decay, signed one-shot dopamine, and runtime-owned readout reward updates exist. It is not hardware evidence, continuous-learning parity, scale-ready eligibility optimization, speedup evidence, or full CRA deployment.
63. Treat Tier 4.22e as passed local minimal delayed-readout parity evidence from `controlled_test_output/tier4_22e_20260430_local_learning_parity/`: fixed-point C-equation mirror matched the floating reference on delayed_cue and hard_noisy_switching seed 42, pending horizons do not store future targets, no-pending ablation loses, and pending drops are zero. It is not hardware evidence, full CRA parity, lifecycle/replay/routing parity, speedup evidence, or final on-chip proof.
64. Treat Tier 4.22f0 as passed custom-runtime scale-readiness audit evidence from `controlled_test_output/tier4_22f0_20260430_custom_runtime_scale_audit/`: host tests and static audit checks passed, PyNN/sPyNNaker remains the primary supported hardware layer, and `7` custom-C scale blockers were documented with `3` high-severity blockers. It is not hardware evidence, not scale-ready evidence, not speedup evidence, and it blocks direct custom-runtime learning hardware claims until event-indexed spike delivery, lazy/active eligibility traces, and compact state readback are repaired.
65. Treat Tier 4.22g as passed local custom-C event-indexed/active-trace optimization evidence from `controlled_test_output/tier4_22g_20260430_event_indexed_trace_runtime/`: host tests and `12/12` static checks passed; `SCALE-001`, `SCALE-002`, and `SCALE-003` are repaired locally; Tier 4.22i later cleared the compact state-readback/build-load acceptance gate. It is not hardware evidence, measured speedup evidence, full CRA parity, or final on-chip learning proof.
66. Treat Tier 4.22h as passed local compact-readback/build-readiness evidence from `controlled_test_output/tier4_22h_20260430_compact_readback_acceptance/`: host tests and `30/30` static readback/callback/SARK-SDP/router-API/build-recipe compatibility checks passed, `CMD_READ_STATE` schema v1 packs a 73-byte state summary, and `.aplx` build was honestly recorded as `not_attempted_spinnaker_tools_missing`. It is not hardware evidence, board-load evidence, command round-trip evidence, speedup evidence, or custom-runtime learning evidence.
67. Treat Tier 4.22k as passed EBRAINS Spin1API event-symbol discovery evidence from `controlled_test_output/tier4_22k_20260430_ebrains_event_symbol_discovery_pass/`: the job image exposed `/home/jovyan/spinnaker/spinnaker_tools/include`, `spin1_callback_on`, and the official enum constants `MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`; timer, SDP, and both MC receive callback probes compiled with `/usr/bin/arm-none-eabi-gcc`, while legacy guessed `MC_PACKET_RX`/`MCPL_PACKET_RX` did not. This is toolchain/header discovery only, not board execution, command round-trip, learning, or speedup evidence.
68. Treat Tier 4.22i as passed custom-runtime board-load/command-roundtrip evidence from `controlled_test_output/tier4_22i_20260501_ebrains_board_roundtrip_pass/`: regenerated `cra_422r` built `coral_reef.aplx`, acquired a real board through pyNN.spiNNaker/SpynnakerDataView, selected free core `(0,0,4)`, loaded the app, acknowledged mutation commands, and returned `CMD_READ_STATE` schema version `1` with a 73-byte payload showing `2` neurons, `1` synapse, and `reward_events=1`. Preserve `controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared/` as the source-package gate and the earlier failed EBRAINS attempts as noncanonical toolchain/API/target/protocol diagnostics. This is not full CRA learning, speedup, multi-core scaling, continuous runtime parity, or final on-chip autonomy.
69. Treat Tier 4.22j as passed minimal custom-runtime closed-loop learning-smoke evidence from `controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/`: one chip-owned delayed pending/readout update passed after ingest correction. It is not full CRA task learning, v2.1 mechanism transfer, speedup, scaling, or final autonomy.
70. Treat Tier 4.22l as passed tiny signed fixed-point learning-parity evidence from `controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_hardware_pass_ingested/`: four signed prediction/weight/bias parity rows matched exactly on real SpiNNaker. It is not full CRA task learning or speedup evidence.
71. Treat Tier 4.22m as passed minimal fixed-pattern task micro-loop evidence from `controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_hardware_pass_ingested/`: twelve schedule/mature task events matched the local s16.15 reference with zero raw deltas, observed accuracy `0.9166666667`, tail accuracy `1.0`, and final raw readout `32256/0`. It is not full CRA task learning or speedup evidence.
72. Treat Tier 4.22n as passed tiny delayed-cue pending-queue evidence from `controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/`: delayed decisions survived a two-event pending gap, all raw deltas were `0`, max pending depth was `3`, and tail accuracy was `1.0`. It is not full delayed_cue transfer, v2.1 transfer, or speedup evidence.
73. Treat Tier 4.22o as passed tiny noisy-switching custom-runtime evidence from `controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/`: after the `cra_422w` 32-bit `FP_MUL` overflow diagnostic, repaired `cra_422x` passed on board `10.11.210.25`, selected core `(0,0,4)`, with `44/44` criteria, all prediction/weight/bias raw deltas `0`, observed accuracy/tail accuracy `0.7857142857/1.0`, max pending depth `3`, and final raw readout `-48768/-1536`. It is not full CRA hard_noisy_switching, v2.1 mechanism transfer, speedup, scaling, or final autonomy.
74. Treat Tier 4.22p as passed tiny A-B-A reentry custom-runtime evidence from `controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_hardware_pass_ingested/`: returned `cra_422y` passed on board `10.11.222.17`, selected core `(0,0,4)`, with `44/44` criteria, all `30` schedule/mature pairs acknowledged, all prediction/weight/bias raw deltas `0`, observed accuracy/tail accuracy `0.8666666667/1.0`, max pending depth `3`, and final raw readout `30810/-1`. It is not full CRA recurrence, v2.1 mechanism transfer, speedup, scaling, or final autonomy.
75. Treat Tier 4.22q as passed tiny integrated host-v2/custom-runtime bridge-smoke hardware evidence from `controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_hardware_pass_ingested/`: returned `cra_422z` passed on board `10.11.236.65`, selected core `(0,0,4)`, with `47/47` remote criteria plus ingest criterion, all `30` schedule/mature pairs acknowledged, all prediction/weight/bias raw deltas `0`, observed accuracy/tail accuracy `0.9333333333/1.0`, bridge context/route updates `9/9`, max keyed slots `3`, max pending depth `3`, and final raw readout `32768/0`. It is not native/on-chip v2 memory/routing, full CRA task learning, speedup, scaling, or final autonomy.
76. Run Tier 4.19 hardware lifecycle feasibility only after software lifecycle survives sham controls and the relevant v2 mechanism bridge/custom-runtime path is clear.
77. Build Tier 6.2 hard synthetic benchmark suite plus Tier 7.1-7.6 real-ish, holdout, policy/action, curriculum, and long-horizon planning/subgoal tests.
78. Migrate only proven mechanisms toward Tier 4.22-4.23 custom C/on-chip paths.
79. Run integrated Tier 8 final software/hardware matrices and reproduction capsule.
80. Freeze final paper baseline.
81. Write paper only after the final claim level is known.
```

## Final Guardrail

The roadmap is not designed to force a positive conclusion. It is designed to
find the truth.

If CRA is useful, this plan should expose where and why. If CRA is not useful
against baselines or if the organism mechanisms do not add value, this plan
should make that obvious before the paper claim becomes inflated.

### Tier 4.22r: Tiny Native Context-State Custom-Runtime Smoke

Current status: **returned hardware pass ingested** at:

```text
controlled_test_output/tier4_22r_20260501_native_context_state_smoke_local/
controlled_test_output/tier4_22r_20260501_native_context_state_smoke_prepared/
controlled_test_output/tier4_22r_20260501_native_context_state_smoke_hardware_pass_ingested/
```

Prepared upload folder and command:

```text
ebrains_jobs/cra_422aa
cra_422aa/experiments/tier4_22r_native_context_state_smoke.py --mode run-hardware --output-dir tier4_22r_job_output
```

Question:

```text
Can the custom runtime own a tiny keyed-context state primitive, retrieve it on
chip, compute feature=context*cue, and still match the delayed readout reference?
```

Reference task:

```text
30 signed native-context events
context keys = ctx_A, ctx_B, ctx_C
context key ids = 101, 202, 303
context writes = 9
context reads = 30
max native context slots = 3
feature source = chip_context_lookup_feature_transform
pending_gap_depth = 2
max_pending_depth = 3
learning_rate = 0.25
expected accuracy = 0.9333333333
expected tail accuracy = 1.0
expected second-half improvement = 0.1333333333
expected final readout_weight_raw = 32752
expected final readout_bias_raw = -16
```

Claim boundary:

```text
LOCAL/PREPARED = source bundle and local s16.15 reference are ready
PASS = returned EBRAINS artifacts show real board target, .aplx build/load,
       context write/read scheduling, chip-computed feature parity, delayed
       maturation parity, pending counters, slot counters, and task metrics
       matching the local reference
```

Returned result:

```text
board = 10.11.237.25
selected core = (0,0,4)
remote criteria = 58/58
ingest criterion = pass
events = 30 context/schedule/mature rows
chip-computed feature/context/prediction/weight/bias raw deltas = 0
observed accuracy = 0.9333333333
observed tail accuracy = 1.0
final pending_created = 30
final pending_matured = 30
final reward_events = 30
final decisions = 30
final active_pending = 0
final readout_weight_raw = 32752
final readout_bias_raw = -16
```

Do not cite Tier 4.22r as full native v2.1 memory/routing, full CRA task
learning, speedup evidence, scaling, or final autonomy.

### Tier 4.22s: Tiny Native Route-State Custom-Runtime Smoke

Current status: **hardware pass ingested**.

```text
controlled_test_output/tier4_22s_20260501_native_route_state_smoke_local/
controlled_test_output/tier4_22s_20260501_native_route_state_smoke_prepared/
```

Prepared upload folder and command:

```text
ebrains_jobs/cra_422ab
cra_422ab/experiments/tier4_22s_native_route_state_smoke.py --mode run-hardware --output-dir tier4_22s_job_output
```

Question:

```text
Can the custom runtime own tiny route state in addition to keyed context, retrieve
both on chip, compute feature=context*route*cue, and still match the delayed
readout reference?
```

Reference task:

```text
30 signed native context+route events
context keys = ctx_A, ctx_B, ctx_C
context key ids = 101, 202, 303
context writes = 9
context reads = 30
route writes = 9
route reads = 30
route values = [-1, 1]
feature source = chip_context_route_lookup_feature_transform
pending_gap_depth = 2
max_pending_depth = 3
learning_rate = 0.25
expected accuracy = 0.9333333333
expected tail accuracy = 1.0
expected final readout_weight_raw = 32768
expected final readout_bias_raw = 0
```

Claim boundary:

```text
LOCAL/PREPARED = source bundle and local s16.15 reference are ready
PASS = returned EBRAINS artifacts show real board target, .aplx build/load,
       context+route write/read scheduling, chip-computed feature parity,
       delayed maturation parity, pending counters, slot counters, route
       counters, and task metrics matching the local reference
```

Do not cite Tier 4.22s as hardware evidence until returned artifacts pass and
are ingested. Even then, it is a tiny native route-state primitive only, not
full v2.1 memory/routing, full CRA task learning, speedup evidence, scaling, or
final autonomy.

Returned Tier 4.22s result:

```text
controlled_test_output/tier4_22s_20260501_native_route_state_smoke_hardware_pass_ingested/
status = pass after ingest correction
raw_remote_status = fail
false_fail_correction = route write counter was checked in the wrong reply surface
board = 10.11.237.89
selected core = (0,0,4)
route writes = 9 via CMD_WRITE_ROUTE row counters
route reads = 31 via final CMD_READ_ROUTE
all feature/context/route/prediction/weight/bias raw deltas = 0
observed accuracy = 0.9333333333
observed tail accuracy = 1.0
final readout_weight_raw = 32768
final readout_bias_raw = 0
```

This upgrades Tier 4.22s from prepared to returned hardware evidence, with a
preserved false-fail audit trail. It still does not prove full native v2.1
memory/routing, full CRA task learning, speedup evidence, scaling, or final
autonomy.

### Tier 4.22t: Tiny Native Keyed Route-State Custom-Runtime Smoke

Current status: **local pass and EBRAINS package prepared**, not hardware-passed
yet.

```text
controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_local/
controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_prepared/
```

Prepared upload folder and command:

```text
ebrains_jobs/cra_422ac
cra_422ac/experiments/tier4_22t_native_keyed_route_state_smoke.py --mode run-hardware --output-dir tier4_22t_job_output
```

Question:

```text
Can the custom runtime own bounded keyed route slots, retrieve both context and
route by key, compute feature=context[key]*route[key]*cue, and still match the
delayed readout reference?
```

Reference task:

```text
30 signed native keyed context+route-slot events
context keys = ctx_A, ctx_B, ctx_C
context key ids = 101, 202, 303
context writes = 9
context reads = 30
route-slot writes = 15
route-slot reads = 30
max route slots = 3
route values = [-1, 1]
feature source = chip_context_keyed_route_lookup_feature_transform
pending_gap_depth = 2
max_pending_depth = 3
learning_rate = 0.25
expected accuracy = 0.9333333333
expected tail accuracy = 1.0
expected final readout_weight_raw = 32768
expected final readout_bias_raw = 0
```

Claim boundary:

```text
LOCAL/PREPARED = source bundle and local s16.15 reference are ready
PASS = returned EBRAINS artifacts show real board target, .aplx build/load,
       context+route-slot write/read scheduling, chip-computed feature parity,
       delayed maturation parity, pending counters, context-slot counters,
       route-slot counters, and task metrics matching the local reference
```

Returned Tier 4.22t result:

```text
controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_hardware_pass_ingested/
status = pass
raw_remote_status = pass
board = 10.11.235.25
selected core = (0,0,4)
route-slot writes = 15
active route slots = 3
route-slot hits = 33
route-slot misses = 0
all feature/context/route/prediction/weight/bias raw deltas = 0
observed accuracy = 0.9333333333
observed tail accuracy = 1.0
final readout_weight_raw = 32768
final readout_bias_raw = 0
```

This upgrades Tier 4.22t from prepared to returned hardware evidence. It still
does not prove full native v2.1 memory/routing, full CRA task learning, speedup
evidence, scaling, or final autonomy.

## Tier 4.22u Native Memory-Route State Custom-Runtime Smoke

Tier 4.22u is the next native custom-runtime bridge after the Tier 4.22t keyed route-state hardware pass. It adds bounded keyed memory/working-state slots alongside keyed context and keyed route slots. The host writes context, route, and memory updates, then sends only `key+cue+delay`; the custom runtime retrieves `context[key]`, `route[key]`, and `memory[key]` and computes `feature=context[key]*route[key]*memory[key]*cue` on chip before scheduling delayed credit.

Local/prepared outputs:

```text
controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_local/
controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_prepared/
```

Prepared EBRAINS upload folder and command:

```text
/Users/james/JKS:CRA/ebrains_jobs/cra_422ad
cra_422ad/experiments/tier4_22u_native_memory_route_state_smoke.py --mode run-hardware --output-dir tier4_22u_job_output
```

Local/prepared reference summary:

```text
sequence_length = 30
context writes/reads = 9 / 30
route-slot writes/reads = 15 / 30
memory-slot writes/reads = 15 / 30
max context/route/memory slots = 3 / 3 / 3
feature source = chip_context_memory_route_lookup_feature_transform
accuracy = 0.9666666667
tail_accuracy = 1.0
pending_gap_depth = 2
max_pending_depth = 3
final_readout_weight_raw = 32768
final_readout_bias_raw = 0
```

Claim boundary: this is a tiny native memory-route primitive layered on the prior native keyed context and keyed route primitives. Local/prepared evidence proves package/source readiness only. A returned EBRAINS pass would prove chip-owned keyed memory-slot lookup participates in the minimal pending/readout micro-loop. It still would not prove full native v2.1 memory/routing, full CRA task learning, speedup, multi-core scaling, or final on-chip autonomy.

Returned EBRAINS update: Tier 4.22u passed outright with raw remote status `pass`. Target acquisition succeeded through pyNN.spiNNaker/SpynnakerDataView on board `10.11.235.89`, selected core `(0,0,4)`, `.aplx` build/load passed, all `30` context/route-slot/memory-slot/schedule/mature rows completed, final route-slot writes/hits/misses were `15/33/0`, final memory-slot writes/hits/misses were `15/33/0`, active route and memory slots were both `3`, all feature/context/route/memory/prediction/weight/bias raw deltas were `0`, observed accuracy was `0.9666666667`, tail accuracy was `1.0`, and the final readout state was `readout_weight_raw=32768`, `readout_bias_raw=0`.

Ingested hardware evidence:

```text
controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_hardware_pass_ingested/
```

## Tier 4.22v Native Memory-Route Reentry/Composition Custom-Runtime Smoke

Tier 4.22v is the next native custom-runtime gate after the Tier 4.22u memory-route hardware pass. It does not add a new command surface. Instead, it stresses the 4.22u primitive with a harder 48-event stream: four keyed context/route/memory slots, independent context/route/memory updates, interleaved recalls, and reentry pressure. The chip still receives only `key+cue+delay` per decision and must retrieve `context[key]`, `route[key]`, and `memory[key]` before computing `feature=context[key]*route[key]*memory[key]*cue`.

Local/prepared outputs:

```text
controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_local/
controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_prepared/
```

Prepared EBRAINS upload folder and command:

```text
/Users/james/JKS:CRA/ebrains_jobs/cra_422ae
cra_422ae/experiments/tier4_22v_native_memory_route_reentry_composition_smoke.py --mode run-hardware --output-dir tier4_22v_job_output
```

Local/prepared reference summary:

```text
sequence_length = 48
context writes/reads = 18 / 48
route-slot writes/reads = 21 / 48
memory-slot writes/reads = 21 / 48
max context/route/memory slots = 4 / 4 / 4
feature source = chip_context_memory_route_lookup_feature_transform
accuracy = 0.9375
tail_accuracy = 1.0
pending_gap_depth = 2
max_pending_depth = 3
final_readout_weight_raw = 32768
final_readout_bias_raw = 0
```

Claim boundary: this is a harder tiny native memory-route reentry/composition primitive layered on the prior native keyed context, route, and memory primitives. Local/prepared evidence proves package/source readiness only. A returned EBRAINS pass would show the existing native memory-route primitive survives longer interleaving and four-slot reentry pressure. It still would not prove full native v2.1 memory/routing, full CRA task learning, speedup, multi-core scaling, or final on-chip autonomy.

Returned EBRAINS update: Tier 4.22v passed outright with raw remote status `pass`. Target acquisition succeeded through pyNN.spiNNaker/SpynnakerDataView on board `10.11.240.153`, selected core `(0,0,4)`, `.aplx` build/load passed, all `48` context/route-slot/memory-slot/schedule/mature rows completed, final route-slot writes/hits/misses were `21/52/0`, final memory-slot writes/hits/misses were `21/52/0`, active route and memory slots were both `4`, all feature/context/route/memory/prediction/weight/bias raw deltas were `0`, observed accuracy was `0.9375`, tail accuracy was `1.0`, and the final readout state was `readout_weight_raw=32768`, `readout_bias_raw=0`.

Ingested hardware evidence:

```text
controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/
```


## Tier 4.22w Native Decoupled Memory-Route Composition Custom-Runtime Smoke

Tier 4.22w was the next native custom-runtime integration gate after Tier 4.22v. Its purpose is reviewer-facing and architectural: Tier 4.22u/v proved the chip can combine context, route, and memory slots when they share one key; Tier 4.22w tests whether the custom runtime can compose independently addressed state. The new opcode is `CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING`, and the hardware acceptance task requires `feature=context[context_key]*route[route_key]*memory[memory_key]*cue` to be computed on chip before delayed-credit scheduling.

Local/prepared outputs:

```text
controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_local_profiled/
controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared_profiled/
```

Prepared EBRAINS upload folder and command:

```text
/Users/james/JKS:CRA/ebrains_jobs/cra_422ag
cra_422ag/experiments/tier4_22w_native_decoupled_memory_route_composition_smoke.py --mode run-hardware --output-dir tier4_22w_job_output
```

Current status: **returned hardware pass ingested** at:

```text
controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/
```

Returned Tier 4.22w result: **hardware pass**. Board `10.11.236.9`, selected core `(0,0,4)`, `.aplx` build/load pass, `90/90` criteria passed, all `48` schedule/mature pairs completed, all feature/context/route/memory/prediction/weight/bias raw deltas `0`, observed accuracy `0.958333`, tail accuracy `1.0`, context writes/reads `18/48`, route-slot writes/reads `15/48`, memory-slot writes/reads `18/48`, active context/route/memory slots `4/4/4`, route/memory misses `0/0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`.

Claim boundary: this returned hardware pass proves only a tiny native independent-key memory-route composition primitive on real SpiNNaker through the custom runtime. It is not full native v2.1 memory/routing, full CRA task learning, speedup evidence, multi-core scaling, or final on-chip autonomy.

Next native gate: build a compact v2 bridge over the decoupled state primitive rather than adding unrelated mechanisms. Start with local/protocol tests, then prepare a fresh EBRAINS package only after the local gate passes.

Hardware-resource lesson: the first `cra_422af` EBRAINS attempt failed before app load because the unprofiled custom runtime overflowed ITCM by 16 bytes. The repair is not a scientific workaround; it is a hardware-resource control. Tier 4.22w passed with `RUNTIME_PROFILE=decoupled_memory_route` and package `cra_422ag`, establishing the rule that native mechanism gates must declare their compiled command surface and resource profile before hardware execution.


## Tier 4.22x Compact v2 Bridge Over Native Decoupled State Primitive

Tier 4.22x is the next native custom-runtime gate after Tier 4.22w. Its purpose is architectural: prove a bounded host-side v2 state bridge can drive the native decoupled context/route/memory primitive, while the chip performs lookup, feature composition, pending queue, prediction, maturation, and readout update.

Tier 4.22w proved the custom runtime can execute independent-key decoupled composition on real SpiNNaker. Tier 4.22x adds a host-side bridge layer that maintains v2-style state (context slots, route table, memory slots), selects decoupled keys per event, writes state to the chip, and schedules decisions. The chip still executes CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING and owns all lookup, composition, pending, and readout mechanics. No new command surface is added.

Question: Can a bounded host-side v2 state bridge drive the native decoupled context/route/memory primitive on real SpiNNaker, with the chip performing lookup, feature composition, pending queue, prediction, maturation, and readout update?

Hypothesis: A host-side bridge that maintains v2-style state and selects decoupled keys per event can drive the native custom-runtime primitive to produce correct delayed-credit learning on a structured task stream.

Null hypothesis: The host bridge adds no value. Random key selection, fixed keys, or host-pre-composed features produce equivalent or better results.

Mechanism under test: Host-side v2 state bridge → native decoupled CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING → chip-side lookup / composition / pending / readout.

Status: **HARDWARE PASS**. Returned EBRAINS run at `controlled_test_output/tier4_22x_20260501_compact_v2_bridge_decoupled_smoke_hardware_pass_ingested/` passed all `89` remote criteria plus `1` ingest criterion. Board `10.11.236.73`, selected core `(0,0,4)` after fallback from requested core 1 (cores 1,2,3 occupied). Target acquisition used `pyNN.spiNNaker` probe fallback because EBRAINS JobManager does not expose a raw hostname. Probe runtime ~46.8 seconds. Observed accuracy `0.958333`, tail accuracy `1.0`. Reference accuracy `0.958333`, reference tail accuracy `1.0`. All 48 chip-computed feature deltas `0`. All 48 context/route/memory readback deltas `0`. All 48 prediction/weight/bias raw deltas `0`. Zero synthetic fallback. APLX build pass, app load pass, task micro-loop pass. Active context/route/memory slots `4/4/4`, context writes/reads `12/48`, route-slot writes/reads `12/48`, memory-slot writes/reads `12/48`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`.

Claim boundary: this hardware pass proves a bounded host-side v2 state bridge can drive the native decoupled primitive on real SpiNNaker. It is not full native v2.1, not native predictive binding, not native self-evaluation, not full CRA task learning, not continuous no-batching runtime, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

Controls and ablations:
- Fixed-key sham, random-key sham, host-composed sham.
- No-context bridge, no-route bridge, no-memory bridge ablations.

Hardware mode: run-hardware with RUNTIME_PROFILE=decoupled_memory_route (same profile as 4.22w; no new command surface).

Pass criteria:
- APLX build pass, app load pass, target acquisition pass.
- All 48 schedule/mature commands succeed.
- All feature/prediction/weight/bias raw deltas = 0.
- observed_accuracy ≥ 0.85, tail_accuracy = 1.0.
- pending_created = pending_matured = 48.
- Active context/route/memory slots ≤ 4 each.
- At least one sham control fails to match candidate.

Fail criteria:
- Any raw delta nonzero.
- Accuracy < 0.85 or tail accuracy < 1.0.
- Pending leak.
- All sham controls match or exceed candidate.
- Build/load/SDP/protocol failure.

Next plan if 4.22x passes:
Tier 4.22x passed. The master execution plan selects Tier 4.23 Contract - Continuous / Stop-Batching Parity as the current next gate. Do not jump to implementation or hardware until the 4.23 contract predeclares subset, references, state ownership, cadence, readback, tolerance, controls, and failure classes.

Next plan if 4.22x fails or blocks:
Do not move forward. Ingest and classify the exact failure stage, preserve returned artifacts, update EBRAINS/custom-runtime lessons, repair the smallest failing layer locally, prepare a fresh upload folder, and only then rerun hardware.


## Tier 4.25C Two-Core State/Learning Split Repeatability

Tier 4.25C is the next custom-runtime gate after Tier 4.25B. Its purpose is
repeatability: prove the two-core state/learning split survives independent
random seeds and converges to the same monolithic reference within tolerance.

Tier 4.25B proved the split works for one seed. Tier 4.25C tests seeds 42, 43,
and 44 using the same runner, same cores, same task stream, and same
pass/fail criteria. If the split architecture is deterministic and the inter-core
SDP channel is reliable, all three seeds should pass individually and show
minimal cross-seed variance.

Question: Can the two-core state/learning split reproduce the monolithic
single-core result within tolerance across seeds 42, 43, and 44?

Hypothesis: The two-core split architecture is deterministic enough that
independent seeds produce weight/bias trajectories converging to the same
monolithic reference within ±8192 fixed-point tolerance.

Null hypothesis: Inter-core SDP timing variability, fixed-point rounding, or
initialization sensitivity cause seed-dependent divergence outside tolerance.

Mechanism under test: Same as 4.25B.
- State core (profile=state_core, core 4): context/route/memory state, feature
  computation, schedule upload, timer-driven SDP send of schedule-pending-split.
- Learning core (profile=learning_core, core 5): pending queue, dynamic
  prediction at maturation using own weight, oldest-first maturation, readout
  weight/bias update.
- Inter-core SDP: fire-and-forget, no reply.

What changes from 4.25B:
- Three independent runs with seeds 42, 43, 44.
- Runner accepts `--seed` argument and rebuilds schedule per seed.
- Aggregate criteria: max weight/bias delta across seeds ≤ 8192.

Status: **HARDWARE PASS - INGESTED (23/23 per seed, 3 seeds)**

Expected runner: `experiments/tier4_25b_two_core_split_smoke.py` with `--seed`
argument added.

Expected upload package: reuse `ebrains_jobs/cra_425g` with seed-parameterized
runner.

Local reference:
```text
4.23c monolithic single-core hardware pass:
    board 10.11.235.9, core (0,0,4)
    final readout_weight_raw = 32768, readout_bias_raw = 0
    decisions = 48, reward_events = 48
    pending_created = 48, pending_matured = 48, active_pending = 0
```

Per-seed pass criteria:
```text
23/23 criteria passed (same as 4.25B)
weight within ±8192 of 32768
bias within ±8192 of 0
pending_created == pending_matured == 48
active_pending == 0
decisions == 48 (state core), reward_events == 48 (learning core)
zero synthetic fallback
```

Aggregate pass criteria:
```text
all 3 seeds pass individually
max weight delta across seeds <= 8192
max bias delta across seeds <= 8192
no seed shows pending leak or drop
```

Claim boundary: A PASS proves the two-core state/learning split is repeatable
across three seeds on real SpiNNaker. It is NOT speedup evidence, NOT
multi-chip scaling, NOT a general multi-core framework, and NOT full native
v2.1 autonomy.

Controls:
- Monolithic reference: 4.23c single-core hardware pass
- Chunked reference: 4.22x single-core chunked pass
- Zero-schedule control
- Single-event control

Hardware mode: run-hardware with RUNTIME_PROFILE=state_core on core 4 and
RUNTIME_PROFILE=learning_core on core 5.

Next plan if 4.25C passes:
Tier 4.26 - Four-Core Context/Route/Memory/Learning Distributed Smoke.

Next plan if 4.25C fails or blocks:
Ingest and classify the exact failure stage per seed. Preserve returned
artifacts. Update EBRAINS/custom-runtime lessons. Repair the smallest failing
layer locally. Do not expand to four cores until two-core repeatability is
proven.

## Tier 4.26 Four-Core Context/Route/Memory/Learning Distributed Smoke

Tier 4.26 is the next custom-runtime gate after Tier 4.25C. Its purpose is to
prove that the CRA runtime can distribute context, route, memory, and learning
across four independent cores on a single SpiNNaker chip while reproducing the
monolithic single-core result within tolerance.

Tier 4.25C proved two-core repeatability. Tier 4.26 expands the split from
two cores to four: context (core 4), route (core 5), memory (core 6), and
scheduler/learning (core 7). The learning core drives parallel lookups to the
other three cores, composes the feature, and runs the same delayed-credit
pending horizon as before.

Question: Can four independent cores hold distributed state and cooperate to
reproduce the monolithic delayed-credit result within tolerance?

Hypothesis: Parallel lookup requests from the learning core to dedicated
context/route/memory cores return deterministic values that compose into the
same `feature = context * route * memory * cue` as the monolithic reference.
All cores load, all lookups reply, no stale replies contaminate the sequence,
and final weight/bias converge within ±8192 fixed-point tolerance.

Null hypothesis: Inter-core message loss, stale reply contamination, lookup
ordering bugs, fixed-point composition differences, or timeout races cause
divergence outside tolerance.

Mechanism under test:
- Core 4 (profile=context_core): context slot table, lookup reply.
- Core 5 (profile=route_core): route slot table, lookup reply.
- Core 6 (profile=memory_core): memory slot table, lookup reply.
- Core 7 (profile=learning_core): event schedule, parallel lookups, feature
  composition, pending horizon, readout update.

Inter-core protocol architecture:
```text
A. multicast / MCPL payloads for inter-core messages   = preferred long-term
B. SDP core-to-core messages                           = acceptable temporary scaffold
C. shared SDRAM / mailbox + signal packet              = later option

The first implementation MAY use Option B (SDP) if it gets the smoke working
quickly, but it must be documented as transitional. The architecture target is
event/multicast-style inter-core messaging, with SDP reserved for host control
and readback.
```

What changes from 4.25C:
- Four cores instead of two.
- State is distributed: context on core 4, route on core 5, memory on core 6.
- Learning core (core 7) owns schedule and drives parallel lookups.
- Lookups are independent, not chained.
- Sequence IDs detect stale reply contamination.
- New failure class: missing reply / timeout.

Status: **HARDWARE PASS, INGESTED** - EBRAINS package `cra_426f` passed on
hardware (board 10.11.194.1, cores 4/5/6/7). All 30/30 criteria passed.
Learning core returned exact monolithic reference values: weight=32768, bias=0,
48 decisions, 48 reward events, 48 pending created, 48 pending matured,
active_pending=0. Context core served 48 lookup hits. Evidence archived to
`controlled_test_output/tier4_26_20260502_pass_ingested/`.

Next: evaluate migrating inter-core protocol from SDP to multicast/MCPL,
then design Tier 4.27.

Expected runner: `experiments/tier4_26_four_core_distributed_smoke.py`

Passed upload package: `ebrains_jobs/cra_426f`

Local reference:
```text
4.23c monolithic single-core hardware pass:
    board 10.11.235.9, core (0,0,4)
    final readout_weight_raw = 32768, readout_bias_raw = 0
    decisions = 48, reward_events = 48
    pending_created = 48, pending_matured = 48, active_pending = 0
```

Pass criteria:
```text
Four cores load and report correct profile IDs
Event schedule runs from learning core (core 7)
Context/route/memory lookup replies match sequence IDs
No stale reply contamination
No missing reply / timeout
Feature matches monolithic fixed-point reference
pending_created == pending_matured == 48
reward_events == 48
final readout weight/bias within ±8192 of 32768/0
compact readback from all cores works
zero synthetic fallback
no per-event host intervention
```

Claim boundary: A PASS proves four independent cores can hold distributed
state and cooperate to reproduce the monolithic delayed-credit result within
tolerance on real SpiNNaker. It is NOT speedup evidence, NOT multi-chip
scaling, NOT a general multi-core framework, and NOT full native v2.1 autonomy.

Controls:
- Monolithic reference: 4.23c single-core hardware pass
- Two-core reference: 4.25C seed-42 hardware pass
- Chunked reference: 4.22x single-core chunked pass
- Zero-schedule control
- Single-event control
- Stale-reply control (sequence ID audit)

Hardware mode: run-hardware with RUNTIME_PROFILE=context_core on core 4,
RUNTIME_PROFILE=route_core on core 5, RUNTIME_PROFILE=memory_core on core 6,
and RUNTIME_PROFILE=learning_core on core 7.

Next plan if 4.26 passes:
Ingest hardware artifacts. Design Tier 4.27 as a four-core runtime resource / timing characterization plus MCPL decision gate. MCPL/multicast is the target inter-core data plane for scale; SDP is transitional for scaffolding, host control, diagnostics, and readback.



## Tier 4.27 - Four-Core Runtime Resource / Timing Characterization + MCPL Decision Gate

Tier 4.27 follows the Tier 4.26 four-core distributed hardware pass. It is an engineering characterization and protocol-migration gate, not a mechanism promotion and not a baseline freeze by itself.

Question: What is the measured envelope of the current four-core SDP scaffold, and what is the concrete MCPL/multicast migration path required for scalable inter-core event traffic?

Hypothesis: The 4.26 SDP path provides a measurable scaffold, while MCPL/multicast can become the scalable inter-core data plane. Tier 4.27 should quantify SDP, test MCPL feasibility with official Spin1API symbols, and decide the exact migration plan.

Null hypothesis: The four-core pass is only a smoke success; resource, timing, reliability, or MCPL feasibility is too unclear to treat the runtime as a stable scaling foundation.

Mechanism under test: four-core runtime communication and instrumentation, including SDP scaffold characterization and MCPL/multicast feasibility.

Claim boundary: Tier 4.27 is resource/timing/protocol decision evidence. It is not a new learning result, not a software baseline freeze, not multi-chip scaling, and not final autonomy.

Required measurements:
- inter-core lookup request/reply counts
- lookup latency if measurable
- stale/duplicate reply rate
- timeouts
- wall time, load time, pause/readback time
- payload bytes and command counts
- per-core compact readback
- schedule length tolerance: 48, 96, 192 if practical
- resource footprint per runtime profile

Required MCPL path:
1. Local compile/source audit using official `MC_PACKET_RECEIVED` / `MCPL_PACKET_RECEIVED` symbols.
2. Two-core MCPL round-trip smoke.
3. Three-state-core MCPL lookup smoke with sequence IDs.
4. SDP-vs-MCPL comparison.

Pass criteria:
- SDP scaffold envelope is measured.
- MCPL feasibility is tested, not deferred as a vague future goal.
- Bottlenecks and failure classes are identified.
- Next migration step is explicit.
- Baseline freeze decision is explicit.

Fail criteria:
- Timing/resource data are insufficient.
- MCPL path is not tested or cannot compile with official symbols.
- Stale/duplicate/missing replies cannot be measured.
- The plan would scale SDP core-to-core traffic as if it were the final data plane.

Decision rule:
- If MCPL passes feasibility and smoke gates, make MCPL the default for later multi-core/multi-chip runtime gates.
- If MCPL fails, repair MCPL before claiming scalable runtime architecture; any SDP-based continuation must be labeled temporary/non-scaling.


Next plan if 4.26 fails or blocks:
Ingest and classify the exact failure stage per core. Preserve returned
artifacts. Distinguish build/load, inter-core messaging, stale/missing reply,
composition mismatch, and readback mismatch. Repair the smallest failing layer
locally. Do not expand to multi-seed or harder tasks until four-core
single-seed smoke passes.

## Current Native Runtime Update - 2026-05-05

Since the original Tier 4.27 protocol-gate text above, the native runtime path
has advanced substantially:

- Tier 4.28a passed four-core MCPL repeatability across seeds 42/43/44.
- Tier 4.28b/c passed delayed-cue MCPL task transfer and repeatability.
- Tier 4.28d passed hard-noisy-switching MCPL task transfer across seeds 42/43/44.
- Tier 4.28e measured the native failure envelope and froze `CRA_NATIVE_TASK_BASELINE_v0.2`.
- Tier 4.29a passed native keyed-memory overcapacity/repeatability.
- Tier 4.29b passed native routing/composition with wrong-route and overwrite controls.
- Tier 4.29c passed native predictive binding across three seeds.
- Tier 4.29d passed native self-evaluation / confidence-gated learning across three seeds.
- Tier 4.29e passed hardware after `cra_429p` repair: host-scheduled replay/consolidation ran through native four-core state primitives across seeds 42/43/44 with 38/38 criteria per seed. `cra_429o` remains preserved as a noncanonical diagnostic failure.
- Tier 4.29f passed the compact native mechanism evidence-regression gate over 4.29a-4.29e with 113/113 criteria and froze `CRA_NATIVE_MECHANISM_BRIDGE_v0.3`.

Immediate roadmap boundary:

```text
`CRA_NATIVE_MECHANISM_BRIDGE_v0.3` is frozen from 4.29f.
Tier 4.29f is an evidence-regression gate over already-ingested real hardware
passes, not a new hardware execution and not a single-task all-mechanism stack
proof.
Tier 7.0 standard dynamical benchmarks are complete. The harness passed 10/10
criteria, but CRA v2.1 online ranked 5/5 against the tested causal sequence
baselines by aggregate geometric-mean MSE. Tier 7.0b is also complete and
localized the gap to a recoverable state-signal/default-readout failure: raw
CRA geomean MSE was 1.2233, a leakage-safe internal-state probe improved to
0.4433, and CRA state plus the same causal lag budget improved to 0.0544. Tier
7.0c then tested a bounded continuous readout/interface repair. It improved raw
CRA and beat shuffled/frozen controls, but lag-only online LMS remained better
and explains most of the benchmark gain. Tier 7.0d then tested state-specific
value beyond lag regression and classified the benchmark path as
`lag_regression_explains_benchmark`: the best state-specific online candidate
did not clear the lag-only margin or sham-separation gates, and train-prefix
ridge lag-only beat lag+state probes.
Tier 5.19 / 7.0e is complete. The narrowed Tier 5.19c gate froze v2.2 for
bounded host-side fading-memory temporal state only; bounded nonlinear
recurrence, universal benchmark superiority, and native/on-chip temporal
dynamics remain unproven. Tier 4.30-readiness through Tier 4.30g-hw then advanced and froze
the lifecycle-native path on top of `CRA_NATIVE_MECHANISM_BRIDGE_v0.3`, with
v2.2 retained as a software reference boundary only. Tier 4.30g-hw returned a
real SpiNNaker pass and ingest pass for a bounded host-ferried lifecycle-to-task
bridge: enabled lifecycle opened the task gate, all five predeclared controls
closed it, resource/readback accounting returned cleanly, and
`CRA_LIFECYCLE_NATIVE_BASELINE_v0.4` is now frozen. Do not move Tier 7.0
benchmark workloads to hardware under the current interface.
```

Paper implication:

```text
4.29a-4.29e support a bounded claim that promoted v2.1 mechanisms are being
migrated into the custom SpiNNaker runtime one mechanism at a time.
4.29f freezes the cumulative mechanism-bridge evidence set. It does not prove
native replay buffers, biological sleep, lifecycle hardware, multi-chip scaling,
speedup, or external-baseline superiority.
Tier 7.0 adds a reviewer-facing limitation: CRA v2.1 is not yet competitive on
the tested continuous-valued standard dynamical regression suite. Tier 7.0b
turns that limitation into a specific engineering/science question: the
organism state contains useful signal, but the default online readout/interface
does not extract it. Tier 7.0c shows a bounded readout/interface improves raw
CRA but does not yet establish a CRA-specific mechanism advantage because the
lag-only control is stronger. Tier 7.0d completes that branch by showing the
state-specific repair does not separate from lag-only/sham controls. The correct
paper posture is to cite this honestly as a limitation: the current CRA
interface is not competitive on these continuous-valued standard dynamical
regression tasks, and the path should not be migrated to hardware unless a
future mechanism changes the failure class.
```

Near-term roadmap insertion:

```text
1. Tier 5.19 / 7.0e - Continuous Temporal Dynamics Substrate Contract. COMPLETE.
2. Tier 5.19a - Local temporal-substrate reference. COMPLETE: fading memory is
   promising, recurrence-specific value not yet separated.
3. Tier 5.19b - Benchmark and sham-control gate. COMPLETE: fading-memory value
   supported; bounded nonlinear recurrence still not proven.
4. Tier 5.19c - Fading-memory narrowing / compact-regression decision.
   COMPLETE: v2.2 frozen for bounded fading-memory temporal state only.
5. Tier 4.30-readiness audit. COMPLETE: lifecycle-native path layers on the
   native mechanism bridge v0.3 with v2.2 as software reference only.
6. Tier 4.30 lifecycle-native contract. COMPLETE: static-pool command/readback
   contract defined.
7. Tier 4.30a local static-pool lifecycle reference. COMPLETE: deterministic
   local reference and sham-control outputs passed.
8. Tier 4.30b source audit / single-core lifecycle mask-smoke preparation.
   COMPLETE: runtime lifecycle static-pool surface and local host/schema parity
   passed.
9. Tier 4.30b-hw single-core lifecycle active-mask/lineage hardware smoke.
   COMPLETE.
10. Tier 4.30c multi-core lifecycle split contract/reference. COMPLETE.
11. Tier 4.30d lifecycle runtime source/local C audit. COMPLETE.
12. Tier 4.30e multi-core lifecycle hardware smoke. COMPLETE.
13. Tier 4.30f lifecycle sham-control hardware subset. COMPLETE: hardware pass
    after ingest.
14. Tier 4.30g lifecycle task-benefit/resource bridge local contract/reference.
    COMPLETE: 9/9 local pass with enabled gate open, all controls gated closed,
    and resource/readback fields declared.
15. Tier 4.30g hardware task-benefit/resource bridge. COMPLETE: raw hardware
    pass and ingest pass on board `10.11.242.97`, 285/285 hardware criteria,
    5/5 ingest criteria, 36 returned artifacts preserved, enabled lifecycle
    gate open, five controls gated closed, and resource/readback accounting
    returned.
16. `CRA_LIFECYCLE_NATIVE_BASELINE_v0.4`. COMPLETE: frozen after lifecycle
    telemetry, controls, resource accounting, and one bounded useful hardware
    task effect passed.
17. Tier 4.31a native temporal-substrate readiness. COMPLETE: local pass 24/24;
    first native v2.2 temporal subset is seven causal fixed-point EMA traces,
    with deltas/novelty derived and no hidden recurrent state.
18. Tier 4.31b native temporal-substrate local fixed-point reference. COMPLETE:
    local pass 16/16; fixed-point seven-EMA mirror matched the float fading-
    memory reference and destructive controls separated.
19. Tier 4.31c native temporal-substrate source/runtime implementation. COMPLETE:
    local pass 17/17; C-owned seven-EMA temporal state, compact 48-byte readback,
    behavior-backed shams, ownership guards, and local C host tests passed.
20. Tier 4.31d native temporal-substrate hardware smoke. COMPLETE:
    hardware pass ingested at
    `controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested/`;
    board `10.11.216.121`; runner revision
    `tier4_31d_native_temporal_hardware_smoke_20260506_0003`; remote hardware
    criteria `59/59`; ingest criteria `5/5`; returned artifacts `21`; enabled,
    zero-state, frozen-state, and reset-each-update shams all passed. First
    EBRAINS return was incomplete and remains preserved as non-evidence at
    `controlled_test_output/tier4_31d_hw_20260506_incomplete_return/`.
21. Tier 4.31e native replay/eligibility decision closeout. COMPLETE:
    local pass 15/15 at
    `controlled_test_output/tier4_31e_20260506_native_replay_eligibility_decision_closeout/`;
    native replay buffers, sleep-like replay, and native macro eligibility are
    deferred until measured blockers exist; Tier 4.31f is deferred; Tier 4.32
    mapping/resource modeling is authorized next; no baseline freeze.
22. Tier 4.32 native-runtime mapping/resource model. COMPLETE:
    local pass 23/23 at
    `controlled_test_output/tier4_32_20260506_mapping_resource_model/`;
    measured 4.27-4.31 evidence now has an explicit resource envelope. MCPL is
    the scale data plane, profile builds have positive ITCM/DTCM headroom,
    Tier 4.32a single-chip scale stress is authorized next, and no native-scale
    baseline freeze is authorized.
23. Tier 4.32a single-chip multi-core scale-stress preflight. COMPLETE:
    local pass 19/19 at
    `controlled_test_output/tier4_32a_20260506_single_chip_scale_stress/`;
    4/5/8/12/16-core MCPL-first stress points are predeclared, but only 4/5-core
    single-shard points are currently eligible. Replicated 8/12/16-core stress
    is blocked until shard-aware MCPL routing exists because the current key has
    no shard/group field and dest_core is reserved/ignored. Tier 4.32a-hw is
    authorized single-shard only, Tier 4.32a-r1 is required before replicated
    stress, and Tier 4.32b/multi-chip/native-scale baseline freeze remain
    blocked.
24. Tier 4.32a-r0 protocol truth audit. COMPLETE:
    local pass 10/10 at
    `controlled_test_output/tier4_32a_r0_20260506_protocol_truth_audit/`;
    the planned MCPL-first 4.32a-hw package is blocked because the current
    confidence-gated lookup path still uses transitional SDP, MCPL replies drop
    confidence/hit status, MCPL receive hardcodes confidence=1.0, and the MCPL
    key lacks shard/group identity. Tier 4.32a-r1 confidence-bearing
    shard-aware MCPL repair is required before MCPL-first hardware stress,
    replicated stress, static reef partitioning, multi-chip scaling, or native
    scale baseline freeze.
25. Tier 4.32a-r1 confidence-bearing shard-aware MCPL lookup repair. COMPLETE:
    local pass 14/14 at
    `controlled_test_output/tier4_32a_r1_20260506_mcpl_lookup_repair/`;
    MCPL lookup replies now use value/meta packets, confidence/hit/status are
    preserved, keys carry shard identity, identical seq/type cross-shard
    controls pass, and full/zero/half-confidence four-core local learning
    controls pass through MCPL. Single-shard 4.32a-hw and replicated-shard
    4.32a-hw-replicated have now both passed after EBRAINS ingest. Static reef
    partition smoke/resource mapping is reopened next; multi-chip scaling and
    native scale baseline freeze remain blocked until static partition evidence
    passes.
26. Tier 4.32a-hw-replicated single-chip replicated-shard EBRAINS stress.
    COMPLETE: hardware pass ingested at
    `controlled_test_output/tier4_32a_hw_replicated_20260507_hardware_pass_ingested/`;
    board `10.11.215.121`, raw remote status pass, ingest status pass,
    185/185 raw hardware criteria, 9/9 ingest criteria, 80 returned artifacts,
    and point08/point12/point16 replicated-shard stress all passed with zero
    stale replies, duplicate replies, timeouts, or synthetic fallback. Boundary:
    single-chip replicated-shard stress only; not static reef partition proof,
    not multi-chip, not speedup, and not a native-scale baseline freeze.
27. Tier 4.32b static reef partition smoke/resource mapping. COMPLETE:
    local pass 25/25 at
    `controlled_test_output/tier4_32b_20260507_static_reef_partition_smoke/`;
    canonical `quad_mechanism_partition_v0` maps four static reef partitions to
    the measured 16-core replicated envelope, assigns polyp slots 0-7 two per
    partition, preserves 384/384 lookup parity per partition, rejects
    one-polyp-one-chip as unsupported, and blocks quad partition plus dedicated
    lifecycle core at 17 cores on one conservative chip. Boundary: local mapping
    evidence only; not a new hardware run, not multi-chip, not speedup, and not
    a native-scale baseline freeze.
```

Tier 5.19a result:

```text
Output: controlled_test_output/tier5_19a_20260505_temporal_substrate_reference/
Criteria: 12/12
Classification: fading_memory_ready_but_recurrence_not_yet_specific
Interpretation: fading-memory state helped the held-out long-memory diagnostic
against lag-only and destructive shams, but the no-recurrence ablation was too
close to the full candidate. Tier 5.19b must sharpen recurrence-specific
controls before any promotion/freeze decision.
```

Tier 5.19b result:

```text
Output: controlled_test_output/tier5_19b_20260505_temporal_substrate_gate/
Criteria: 12/12
Classification: fading_memory_supported_recurrence_unproven
Interpretation: the temporal substrate remained useful on the held-out
long-memory diagnostic (candidate MSE 0.3857 vs lag-only 1.2710), but the
recurrence-pressure diagnostic did not separate from lag-only or state-reset
(candidate 0.8982, lag-only 0.8967, state-reset 0.9029). Therefore the paper
cannot claim bounded nonlinear recurrence from 5.19b. The next valid step is a
narrowed fading-memory promotion/regression decision or a separate recurrence
repair.
```

Tier 5.19c result:

```text
Output: controlled_test_output/tier5_19c_20260505_fading_memory_regression/
Runner: experiments/tier5_19c_fading_memory_regression.py
Criteria: 11/11
Classification: fading_memory_ready_for_v2_2_freeze
Baseline frozen: baselines/CRA_EVIDENCE_BASELINE_v2.2.md
Compact regression: full NEST compact gate passed
Key metric: temporal-memory geomean candidate MSE 0.2275 vs lag-only 0.8954
            (3.94x margin) and raw v2.1 2.1842 (9.60x margin)
Boundary: bounded host-side fading-memory temporal state only; not bounded
          nonlinear recurrence, not hardware/on-chip temporal dynamics, not
          universal benchmark superiority, not language/planning/AGI/ASI.
Next: Tier 4.30-readiness audit before lifecycle-native implementation
(completed; superseded by Tier 4.30 contract and current Tier 4.30a local
reference work).
```

Tier 4.30-readiness result:

```text
Output: controlled_test_output/tier4_30_readiness_20260505_lifecycle_native_audit/
Runner: experiments/tier4_30_readiness_audit.py
Criteria: 16/16
Decision: initial lifecycle-native work layers on
          CRA_NATIVE_MECHANISM_BRIDGE_v0.3; v2.2 is a software reference only.
Required surface: static preallocated pool, active masks, lineage IDs, parent
                  slots, generation, age, trophic health, cyclin-D, Bax,
                  lifecycle event telemetry, compact readback.
Required controls: fixed pool, random event replay, active-mask shuffle,
                   lineage-ID shuffle, no trophic pressure, no dopamine or
                   plasticity.
Boundary: not hardware evidence, not lifecycle implementation, not speedup,
          not multi-chip scaling, not native/on-chip v2.2 temporal migration,
          and not a lifecycle baseline freeze.
Next: Tier 4.30 lifecycle-native contract.
```

Tier 4.30 result:

```text
Output: controlled_test_output/tier4_30_20260505_lifecycle_native_contract/
Runner: experiments/tier4_30_lifecycle_native_contract.py
Criteria: 14/14
Contract: 8 static slots, 2 founders, lifecycle init/event/trophic/readback/sham
          command schema, 23 readback fields, 5 lifecycle event semantics, 5
          gate definitions, and 7 failure classes.
Boundary: local engineering contract only; not runtime implementation, not
          hardware evidence, not lifecycle/self-scaling proof, not v2.2 temporal
          migration, not speedup, not multi-chip scaling.
Next: Tier 4.30a local static-pool lifecycle reference (completed; superseded
by current Tier 4.30b-hw single-core lifecycle hardware smoke package/run).
```

Tier 4.30a result:

```text
Output: controlled_test_output/tier4_30a_20260505_static_pool_lifecycle_reference/
Runner: experiments/tier4_30a_static_pool_lifecycle_reference.py
Criteria: 20/20
Reference: 8 static slots, 2 founders, canonical 32-event trace, boundary
           64-event trace, exact deterministic repeat, zero invalid events on
           enabled path, capacity bounded at <=8 active slots.
Controls: fixed pool, random event replay, active-mask shuffle, lineage-ID
          shuffle, no trophic pressure, no dopamine/plasticity.
Boundary: local deterministic reference only; not runtime C, not hardware, not
          task benefit, not lifecycle baseline freeze, not v2.2 temporal-state
          migration.
Next: Tier 4.30b source audit / single-core lifecycle mask-smoke preparation
(completed; superseded by current Tier 4.30b-hw single-core lifecycle hardware
smoke package/run).
```

Tier 4.30b result:

```text
Output: controlled_test_output/tier4_30b_20260505_lifecycle_source_audit/
Runner: experiments/tier4_30b_lifecycle_source_audit.py
Criteria: 13/13
Result: runtime lifecycle opcodes, static-pool lifecycle structs, exact 4.30a
        canonical/boundary checksum parity, lifecycle SDP readback, and
        existing runtime/profile tests preserved.
Boundary: local source/runtime host evidence only; not hardware evidence, not
          task benefit, not multi-core lifecycle, not v2.2 temporal-state
          migration, and not a baseline freeze.
```

Tier 4.30b-hw result:

```text
Output: controlled_test_output/tier4_30b_hw_20260505_hardware_pass_ingested/
Raw remote status: fail
Corrected ingest status: pass
Correction: runner rev-0001 checked cumulative readback_bytes instead of compact payload_len
Board/core: 10.11.226.17 / (0,0,4)
Ingest criteria: 5/5
canonical_32 corrected scenario criteria: 16/16
boundary_64 corrected scenario criteria: 16/16
payload_len: 68 for both scenarios
fallback: 0
```

Meaning: the scoped single-core lifecycle metadata/readback surface transfers
to real SpiNNaker hardware. The raw remote failure is preserved as a criterion
bug and corrected only because raw artifacts already contained compact
`payload_len=68` and exact state/reference parity. Boundary remains unchanged:
not task-benefit evidence, not multi-core lifecycle migration, not speedup, not
v2.2 temporal-state migration, and not a lifecycle baseline freeze.

Tier 4.30c result:

```text
Output: controlled_test_output/tier4_30c_20260505_multicore_lifecycle_split/
Runner: experiments/tier4_30c_multicore_lifecycle_split.py
Criteria: 22/22
Result: five-core lifecycle ownership contract, single-writer lifecycle_core
        semantics, host-only init/readback, inter-core lifecycle event/trophic/
        mask-sync messages, explicit MCPL/multicast target, exact 4.30a
        canonical/boundary split parity, final active-mask sync, payload_len=68
        requirement, and eight distributed failure classes.
Boundary: local contract/reference evidence only; not C implementation, not
          hardware evidence, not task benefit, not speedup, not multi-chip
          scaling, not v2.2 temporal-state migration, and not a lifecycle
          baseline freeze.
Next: Tier 4.30d multi-core lifecycle runtime source audit/local C host test.
```

Tier 4.30d result:

```text
Output: controlled_test_output/tier4_30d_20260505_lifecycle_runtime_source_audit/
Runner: experiments/tier4_30d_lifecycle_runtime_source_audit.py
Runner revision: tier4_30d_lifecycle_runtime_source_audit_20260505_0001
Criteria: 14/14
Result: dedicated lifecycle_core runtime profile, lifecycle inter-core
        event/trophic request stubs, active-mask/count/lineage sync
        send/receive bookkeeping, duplicate/stale/missing-ack counters,
        non-lifecycle ownership guards, compact payload_len=68 preservation,
        and local C host tests against the Tier 4.30c split contract.
Boundary: local source/runtime host evidence only; not EBRAINS hardware
          evidence, not task benefit, not speedup, not multi-chip scaling, not
          v2.2 temporal-state migration, and not a lifecycle baseline freeze.
Next: Tier 4.30e multi-core lifecycle hardware smoke package/run.
```

Tier 4.30e result:

```text
Prepared output: controlled_test_output/tier4_30e_hw_20260505_prepared/
Ingested output: controlled_test_output/tier4_30e_hw_20260505_hardware_pass_ingested/
Runner: experiments/tier4_30e_multicore_lifecycle_hardware_smoke.py
Runner revision: tier4_30e_multicore_lifecycle_hardware_smoke_20260505_0001
Upload folder: ebrains_jobs/cra_430e
Status: hardware pass / ingested
Board: 10.11.226.145
Raw remote status: pass
Ingest status: pass
Hardware criteria: 75/75
Ingest criteria: 5/5
Purpose: five-profile lifecycle hardware smoke over context_core, route_core,
         memory_core, learning_core, and lifecycle_core with compact lifecycle
         readback, non-lifecycle ownership guards, canonical/boundary lifecycle
         reference parity, and duplicate/stale event rejection.
Boundary: not lifecycle task benefit, not sham-control success, not speedup,
          not multi-chip scaling, not v2.2 temporal-state migration, and not a
          lifecycle baseline freeze.
Next: Tier 4.30f lifecycle sham-control hardware subset (completed; superseded
by Tier 4.30g-hw task-benefit/resource bridge hardware pass and v0.4 freeze).
```

Tier 4.30f result:

```text
Prepared output: controlled_test_output/tier4_30f_hw_20260505_prepared/
Ingested output: controlled_test_output/tier4_30f_hw_20260505_hardware_pass_ingested/
Runner: experiments/tier4_30f_lifecycle_sham_hardware_subset.py
Runner revision: tier4_30f_lifecycle_sham_hardware_subset_20260505_0001
Upload folder: ebrains_jobs/cra_430f
Status: hardware pass / ingested
Prepared criteria: 8/8
Raw remote status: pass
Ingest status: pass
Board: 10.11.227.9
Hardware criteria: 185/185
Ingest criteria: 5/5
Returned artifacts preserved: 35
JobManager command:
cra_430f/experiments/tier4_30f_lifecycle_sham_hardware_subset.py --mode run-hardware --output-dir tier4_30f_hw_job_output
Scope: enabled, fixed-pool, random-event replay, active-mask shuffle,
       no-trophic-pressure, and no-dopamine/no-plasticity controls on the
       canonical 32-event lifecycle trace.
Result: enabled mode remained canonical; fixed-pool separated active-mask bits
        and suppressed mask-mutation counters; random replay separated lineage
        checksum; active-mask shuffle separated active-mask bits; no-trophic and
        no-dopamine/no-plasticity separated trophic checksums; compact payload
        length stayed 68; synthetic fallback stayed zero.
Boundary: compact lifecycle sham-control hardware subset only, not full Tier 6.3
          hardware, not lifecycle task-benefit evidence, not speedup, not
          multi-chip scaling, not v2.2 temporal-state migration, and not a
          lifecycle baseline freeze.
Next: Tier 4.30g lifecycle task-benefit/resource bridge local contract/reference
      has passed and the hardware source package is prepared at
      `ebrains_jobs/cra_430g`. Run the prepared package on EBRAINS, then ingest
      returned artifacts to evaluate hardware task effect and resource/readback
      accounting.
```

Tier 4.30g result:

```text
Local output: controlled_test_output/tier4_30g_20260506_lifecycle_task_benefit_resource_bridge/
Hardware ingested output: controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/
Runner: experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py
Runner revision: tier4_30g_lifecycle_task_benefit_resource_bridge_20260506_0001
Local status: pass, 9/9
Hardware raw remote status: pass
Hardware ingest status: pass
Board: 10.11.242.97
Hardware criteria: 285/285
Ingest criteria: 5/5
Returned artifacts preserved: 36
Scope: enabled lifecycle versus fixed-pool, random-replay, active-mask-shuffle,
       no-trophic, and no-dopamine/no-plasticity controls.
Result: enabled bridge gate opened; all five controls closed the bridge gate;
        enabled reference tail accuracy 1.0; control reference tail accuracy
        0.375; compact lifecycle payload length 68; stale replies/timeouts 0;
        resource/readback accounting returned for every mode.
Boundary: hardware task-benefit/resource bridge only, still host-ferried; not
          autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip
          scaling, not v2.2 temporal-state migration, and not full organism
          autonomy.
Baseline: CRA_LIFECYCLE_NATIVE_BASELINE_v0.4 frozen.
Tier 4.31a result:

```text
Output: controlled_test_output/tier4_31a_20260506_native_temporal_substrate_readiness/
Status: pass
Criteria: 24/24
Decision: seven causal fixed-point EMA traces for the first native v2.2 temporal
          migration; deltas and novelty derived, no hidden recurrent state
Persistent state: 56 bytes
Total initial trace/table budget: 112 bytes
Boundary: local readiness only, not C implementation or hardware evidence
```

Tier 4.31b result:

```text
Output: controlled_test_output/tier4_31b_20260506_native_temporal_fixed_point_reference/
Status: pass
Criteria: 16/16
Fixed/float ratio: 0.9987474666079806
Selected max feature error: 0.004646656591329457
Selected saturation count: 0
Control margins: lag 3.94, zero-state 2.74, frozen 1.35, shuffled 4.92,
                 reset 3.11, shuffled-target 5.14, no-plasticity 9.61
Boundary: local fixed-point reference only, not C implementation or hardware
```

Tier 4.31c result:

```text
Output: controlled_test_output/tier4_31c_20260506_native_temporal_runtime_source_audit/
Status: pass
Criteria: 17/17
Runtime source: C-owned seven-EMA temporal state
Trace bound: ±2 s16.15
Compact temporal readback length: 48
Command codes: 39-42
Tests: test-temporal-state, test-profiles, test, test-lifecycle, test-lifecycle-split
Boundary: local source/runtime host evidence only, not hardware
```

Next: Tier 4.32c inter-chip feasibility contract. Tier 4.32b has passed at
      `controlled_test_output/tier4_32b_20260507_static_reef_partition_smoke/`
      with 25/25 criteria. The next gate must define board/chip/shard key
      fields, message paths, compact readback ownership, failure counters,
      placement assumptions, and the smallest cross-chip smoke target before any
      multi-chip hardware job. Multi-chip execution, speedup claims, benchmark
      claims, and native-scale baseline freeze remain blocked until that
      contract passes.
      Reopen native replay-buffer, sleep-like replay, or eligibility-trace
      implementation only if a later measured blocker specifically demands it.
```

Detailed Tier 5.19 contract:

```text
docs/TIER5_19_CONTINUOUS_TEMPORAL_DYNAMICS_CONTRACT.md
```

Remaining mechanism families to keep visible:

```text
continuous temporal dynamics / fading memory
CRA-native nonlinear recurrent state
local continuous-value readout/interface
macro/native eligibility only if a measured blocker justifies it
lifecycle/self-scaling
native lifecycle with static pools/masks/lineage
native/on-chip temporal state
native/on-chip replay buffers or sleep-like replay
native/on-chip eligibility traces at scale if justified
policy/action selection
real-ish task adapters and held-out task families
curriculum/environment generator
long-horizon planning / subgoal control
single-chip multi-core stress
multi-chip communication and learning
final expanded baselines, fairness audit, reproduction capsule, and paper lock
```

Mechanism scope rule:

```text
Do not force every capability into one overloaded polyp. Polyps should remain
small specialists. Larger capability belongs in distributed reef machinery:
population state, routing state, memory slots, lifecycle masks, readout
interfaces, and native runtime primitives. Each future mechanism must declare
whether it is per-polyp, population-level, readout/interface-level,
lifecycle-level, or runtime-substrate-level.
```
