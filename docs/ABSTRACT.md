# Abstract

The Coral Reef Architecture (CRA) is a biologically inspired neuromorphic
learning system that replaces global backpropagation with local spiking
plasticity, trophic energy accounting, lifecycle pressure, and population-level
selection. A CRA organism is a colony of polyps: small neural agents connected
by a directed reef graph. Each polyp maintains local state, receives sensory and
outcome signals, earns or loses trophic support, changes synaptic strength under
dopamine-modulated plasticity, and may persist, reproduce, or die under explicit
survival rules.

This repository implements CRA as a Python/PyNN research system with multiple
backends and a staged validation suite. The mainline implementation includes a
configurable organism loop, energy manager, learning manager, lifecycle manager,
reef graph, task adapters, a trading bridge, NEST/Brian2/PyNN-SpiNNaker backend
integration, a pure-Python mock simulator, and an experimental bare-metal
SpiNNaker C runtime sidecar. The evidence system is organized through canonical
result bundles and a generated study registry rather than ad hoc output folders.

The current controlled evidence trail contains 12 core tests plus a growing set
of addenda and reviewer-defense guardrail bundles:
Tier 4.10b hard population scaling, Tier 4.13 SpiNNaker hardware capsule, Tier
4.14 hardware runtime characterization, and Tier 4.15 SpiNNaker hardware
multi-seed repeat, followed by Tier 5.1 external baselines and Tier 5.2
learning curves, Tier 5.3 CRA failure analysis, Tier 5.4 delayed-credit
confirmation, Tier 4.16a repaired delayed-cue hardware repeat, Tier 4.16b
repaired hard-switch hardware repeat, and Tier 4.18a v0.7 chunked hardware
runtime baseline, followed by Tier 5.5 expanded software baselines, Tier 5.6
tuned-baseline fairness auditing, Tier 5.7 compact regression, Tier 5.12a
predictive task-pressure validation, Tier 5.12c predictive-context sham repair,
Tier 5.12d predictive-context compact regression, Tier 5.15 software
temporal-code diagnostic coverage, Tier 5.16 NEST neuron-parameter sensitivity,
Tier 6.1 software lifecycle/self-scaling, Tier 6.3 lifecycle sham controls, and
Tier 6.4 circuit-motif causality. The
canonical registry currently reports
27 evidence bundles, 27 tracked evidence entries, zero missing expected
artifacts, and zero failed criteria in canonical entries. Tier 1
negative controls show that zero-signal and shuffled-label inputs
do not produce false learning. Tier 2 positive controls show learning on fixed
patterns, delayed reward, and nonstationary switch tasks. Tier 3 ablations show
that dopamine, plasticity, and trophic selection each matter. Tier 4 tests show
stable population scaling, hard-scaling value through non-accuracy metrics,
domain transfer from finance to a non-finance sensor-control adapter, NEST to
Brian2 backend parity, a minimal SpiNNaker hardware-capsule pass, a
runtime/provenance breakdown of that pass, repeatability of the same minimal
hardware capsule across three seeds, repaired delayed-cue hardware transfer
across three seeds, repaired hard-switch hardware transfer across three
seeds, and v0.7 chunked hardware runtime characterization showing chunk `50` is
the fastest viable current bridge setting on seed `42`. Tier 5.1 compares CRA against simple
external learners and documents both sides: simple online learners dominate the
easy delayed-cue mapping, while CRA shows a defensible external-median advantage
on the non-finance sensor_control task and hard noisy switching. Tier 5.2 then
repeats the comparison across 120, 240, 480, 960, and 1500 steps and shows that
the Tier 5.1 edge does not strengthen at the longest horizon under the tested
settings. Tier 5.3 diagnoses the long-run weakness and identifies stronger
delayed credit as the leading candidate fix, while documenting that hard noisy
switching still trails the best external baseline. Tier 5.4 confirms
`delayed_lr_0_20` across 960 and 1500 steps: delayed_cue stays at tail accuracy
1.0, hard noisy switching beats the external median at both lengths, and the
candidate does not regress versus current CRA, but hard noisy switching still
does not beat the best external baseline. Tier 5.5 then runs the locked CRA v0.8
configuration against eight implemented external baselines across 1,800
software runs, 10 seeds, five run lengths, and four tasks. The suite passes
methodologically and shows robust advantage regimes plus non-dominated
hard/adaptive behavior, but it also documents that delayed_cue and
sensor_control saturate or tie strong baselines and that hard_noisy_switching
beats the external median at 1500 steps while trailing the best external tail
score there. Tier 5.6 then locks CRA at the promoted delayed-credit setting and
retunes implemented external baselines under predeclared budgets across 990
software runs. It passes the fairness gate with four surviving target regimes
after retuning, while still documenting that CRA does not beat the best tuned
baseline on every metric or horizon. Tier 5.7 then confirms the promoted
setting did not break compact negative controls, positive learning controls,
architecture ablations, or delayed_cue/hard_noisy_switching smoke execution.
Tier 6.1 then compares fixed-N CRA with lifecycle-enabled CRA on identical NEST
streams for delayed_cue and hard_noisy_switching. It passes with clean lineage,
75 new-polyp events, and two hard_noisy_switching advantage regimes versus
same-initial fixed controls, while documenting that the events were mostly
cleavage (`74` cleavage, `1` adult birth, `0` deaths). This is software
lifecycle expansion evidence, not full adult turnover, hardware lifecycle, or
external-baseline superiority. Tier 6.3 then tests the two successful
hard_noisy_switching lifecycle regimes against fixed max-pool capacity,
event-count replay, active-mask/lineage shuffle audits, no trophic pressure, no
dopamine, and no plasticity. It passes with 36/36 actual runs, 26 intact
non-handoff lifecycle events, 0 fixed capacity-control lifecycle events, 0
actual-run lineage failures, 10/10 performance-sham wins, 2/2 fixed max-pool
wins, 2/2 event-count replay wins, and 6/6 intentional lineage-ID shuffles
detected. This strengthens the software organism/ecology claim but remains
software-only sham-control evidence, not hardware lifecycle, native on-chip
lifecycle, full adult turnover, compositionality, world modeling, or
external-baseline superiority. Tier 6.4 then asks whether CRA's internal reef
motifs are doing causal work rather than serving as decorative labels. The
canonical run uses a seeded motif-diverse graph on hard_noisy_switching,
life4_16/life8_32 regimes, seeds `42`, `43`, and `44`, and 960 steps. It
passes with 48/48 actual runs, 2/2 motif-diverse intact aggregates, 1920
pre-reward motif-active steps, 4/8 motif-ablation losses, 0/2 motif-label
shuffle losses, 0/4 random/monolithic dominations, and 0 lineage-integrity
failures. This supports controlled software motif structure/edge-role causality,
not hardware motif execution, custom-C/on-chip learning, compositionality,
world modeling, self-evaluation/metacognitive monitoring, long-horizon
planning/subgoal control, real-world usefulness, or universal baseline
superiority.
The current Tier 5 mechanism ladder also records baseline-frozen and
noncanonical reviewer-useful memory evidence. Macro-eligibility repairs (Tier 5.9a/5.9b) were not promoted,
and the first proxy multi-timescale memory diagnostic (Tier 5.10) exposed weak
task pressure. Tier 5.10b repaired the task surface; Tier 5.10c showed an
explicit host-side context-binding scaffold could solve it; Tier 5.10d moved
that mechanism inside `Organism` and passed full compact regression; and Tier
5.10e stress-tested the internal memory under longer gaps, denser distractors,
and hidden recurrence pressure. Tier 5.10e completed 153/153 NEST runs, had
zero leakage across 2448 checked feedback rows, reached 1.0 all accuracy on all
three stress tasks, matched the external scaffold, and kept a minimum
0.33333333333333337 all-accuracy edge versus v1.4/raw CRA, best memory ablation,
sign persistence, and best standard baseline. This is internal host-side
memory-retention evidence, not sleep/replay, native on-chip memory, hardware
memory transfer, or solved catastrophic forgetting. Tier 5.10f then failed
cleanly under capacity/interference stress: it completed the full 153-run matrix
with zero leakage and active memory updates, but the single-slot internal memory
dropped to 0.25 minimum all accuracy and regressed versus v1.4 on context
reentry. Tier 5.10g repaired that measured failure with bounded keyed/multi-slot
context memory: 171/171 NEST runs completed, feedback leakage remained zero
across 2166 checked rows, keyed memory reached 1.0 all accuracy on all three
capacity/interference tasks, matched the oracle-key scaffold, beat v1.5
single-slot memory and memory ablations by at least 0.33333333333333337, beat
sign persistence and the best standard baseline by 0.5, and preserved compact
regression. This freezes v1.6 as host-side internal keyed-memory evidence, not
sleep/replay, native on-chip memory, hardware memory transfer, compositionality,
module routing, or general working memory.
Tier 5.11a then supplies the pre-implementation sleep/replay need test: v1.6
no-replay keyed memory degrades under silent reentry stressors, while unbounded
keyed memory and oracle scaffold controls reach 1.0 minimum accuracy. The
diagnostic decision is `replay_or_consolidation_needed`, authorizing Tier 5.11b
without claiming replay success or freezing a new baseline.
Tier 5.11b then tests that intervention and deliberately blocks promotion:
prioritized replay reaches 1.0 minimum all/tail accuracy with zero leakage and
full gap closure, but the shuffled-replay sham comes too close on
partial-key reentry, missing the predeclared tail-edge threshold. This keeps
v1.6 as the memory baseline at that point and records priority-specific replay
as non-promoted repair signal rather than a new claim. Tier 5.11c repeats the
sharper sham-separation test and again blocks the priority-specific claim,
because shuffled-order replay remains too close. Tier 5.11d then reframes the
claim to generic correct-binding replay/consolidation and passes: 189/189 NEST
runs complete with zero leakage, candidate replay reaches 1.0 minimum all/tail
accuracy, wrong-key/key-label/priority-only/no-consolidation controls fail to
match it, and compact regression passes afterward. This freezes v1.7 as
host-side software replay/consolidation evidence, not proof of priority
weighting, biological sleep, native/on-chip replay, hardware memory transfer,
compositionality, or world modeling.


Tier 5.12a then validates the predictive task-pressure battery before adding any
predictive/world-model mechanism: 144/144 software cells complete with zero
feedback leakage across 10044 checked rows, causal predictive-memory controls
solve all four tasks at 1.0, and current-reflex, sign-persistence,
wrong-horizon, and shuffled-target controls fail under the predeclared ceilings.
This authorized the Tier 5.12b/5.12c mechanism sequence but is not CRA predictive coding,
world modeling, language, planning, or a new frozen baseline.

Tier 5.12b is retained as a failed predictive-context diagnostic because it
showed the first wrong-sign sham was learnably informative rather than
destructive. Tier 5.12c repairs that sham contract and passes a 171-cell NEST
matrix: zero leakage, 570 predictive-context writes/active decision uses,
candidate match to the external scaffold, minimum edge 0.8444 versus v1.7,
0.3389 versus shuffled/permuted/no-write shams, 0.3 versus shortcut controls,
and 0.3167 versus selected external baselines. Tier 5.12d then passes compact
regression across Tier 1 controls, Tier 2 learning, Tier 3 ablations,
hard-task smokes, the v1.7 replay/consolidation guardrail, and compact
predictive-context sham separation. This freezes v1.8 as bounded host-side
visible predictive-context binding, not hidden-regime inference, full world
modeling, language, planning, hardware prediction, hardware scaling, native
on-chip learning, compositionality, self-evaluation/metacognitive monitoring,
long-horizon planning/subgoal control, or external-baseline superiority.

Tier 5.13 then attacks the compositionality/reflex critique directly as a
software diagnostic: 126/126 mock task/model/seed cells complete with zero
feedback leakage, explicit host-side reusable-module composition reaches 1.0
first-heldout and total heldout accuracy on held-out skill-pair,
order-sensitive-chain, and distractor-chain tasks, raw v1.8 and combo
memorization remain at 0.0 first-heldout accuracy, module reset/shuffle/order
shams are materially worse, and selected standard baselines do not close the
gap. This authorizes internal composition/routing work but is not native CRA
compositionality, hardware composition, language, planning, AGI, or a new
baseline freeze.
Tier 5.13b then separates module availability from module selection:
126/126 mock cells complete with zero leakage across 11592 checked feedback
rows, explicit host-side contextual routing reaches 1.0 first-heldout, heldout,
and router accuracy across delayed-context, distractor, and reentry routing
tasks, and the router selects before feedback 276 times. Raw v1.8 and the CRA
router-input bridge remain at 0.0 first-heldout accuracy, while routing shams
and selected baselines do not close the gap. This authorizes internal
routing/gating work but is not native CRA routing, hardware routing, language,
planning, AGI, or a baseline freeze.
Tier 5.13c then internalizes the scaffolded composition/routing capability into
the CRA host loop: 243/243 mock cells complete with zero leakage across 22941
checked feedback rows, the internal path learns 192 primitive module updates and
88 router updates, selects/composes before feedback, reaches 1.0 minimum
held-out composition/routing and router accuracy, separates from no-write/reset/
shuffle/random/always-on shams, and is followed by a fresh full compact
regression pass. This freezes v1.9 as internal host-side software
composition/routing evidence, not SpiNNaker hardware evidence, native on-chip
routing, language, long-horizon planning, AGI, or external-baseline superiority.
Tier 5.14 then tests broader working-memory/context binding over frozen v1.9:
the noncanonical mock diagnostic passes both context/cue-memory and delayed
module-state routing subsuites. Context-memory reaches 1.0 accuracy on all
three memory-pressure tasks with minimum edge 0.5 versus the best memory sham
and sign persistence; routing reaches 1.0 first-heldout, heldout, and router
accuracy on all three delayed module-state tasks with minimum edge 1.0 versus
routing-off CRA and 0.5 versus the best routing sham. This supports a bounded
host-side software working-memory/context-binding claim for v1.9, but it is not
a v2.0 freeze, hardware/on-chip working memory, language, planning, AGI, or
external-baseline superiority.
Tier 5.15 then tests whether spike timing is functionally meaningful in the
software stack. The 540-run temporal-code diagnostic passes with 60 sampled
spike-trace artifacts, 60 encoding-metadata artifacts, 9 successful genuinely
temporal cells, and 3 successful non-finance temporal cells. Latency, burst,
and temporal-interval codes support learning on fixed_pattern, delayed_cue, and
sensor_control while time-shuffle and rate-only controls lose. This is
software-only temporal-code evidence, not hardware/custom-C on-chip temporal
coding, not a v2.0 freeze, and not hard_noisy_switching temporal superiority.
Tier 5.16 then tests whether that software stack is fragile to one exact LIF
parameterization. The 66-run NEST diagnostic passes across 11 threshold,
membrane-tau, refractory, capacitance, and synaptic-tau variants with all 33
task/variant cells functional, zero parameter-propagation failures, zero
backend failure/fallback counters, zero collapse rows, and monotonic direct LIF
response probes. This is software neuron-parameter robustness evidence, not
SpiNNaker/custom-C on-chip neuron evidence or a v2.0 freeze.

The strongest current hardware claims are intentionally narrow. First, a
minimal fixed-pattern CRA capsule ran through `pyNN.spiNNaker` with real spike
readback, zero synthetic fallback, zero `sim.run` failures, zero summary-read
failures, and repeatability across seeds `42`, `43`, and `44`. Second, the
repaired delayed-cue capsule transferred the confirmed `delayed_lr_0_20` setting
to real hardware across the same three seeds. Third, the repaired
hard_noisy_switching capsule also transferred across seeds `42`, `43`, and `44`
under chunked host replay. Fourth, a custom bare-metal C runtime now executes
chip-owned delayed credit on real SpiNNaker: Tier 4.23c proved continuous
single-core learning, Tier 4.25B proved a two-core state/learning split, Tier
4.25C proved two-core repeatability across three seeds, and Tier 4.26 proved a
four-core distributed context/route/memory/learning split with inter-core SDP
lookup request/reply, all matching the monolithic reference within tolerance.
The fixed-pattern repeat recorded mean overall strict accuracy of
0.9747899159663865 and mean tail strict accuracy of 1.0; the delayed-cue repeat
recorded mean all accuracy 0.9933333333333333 and mean tail accuracy 1.0; the
hard-switch repeat recorded mean all accuracy 0.5497076023391813 and minimum
tail accuracy 0.5238095238095238; the four-core custom-runtime pass recorded
exact reference match (weight=32768, bias=0) on seed 42 with 30/30 criteria.
These are evidence that narrow fixed-pattern, delayed-credit, hard-switch, and
distributed custom-runtime capsules can execute on SpiNNaker hardware and
preserve expected behavior repeatably. They are not yet evidence of full
hardware scaling, dynamic lifecycle execution on hardware, native on-chip
v2.1 mechanism transfer, external-baseline superiority, or deployment of the
entire CRA organism on SpiNNaker.

Tier 4.14 characterizes the hardware overhead behind that pass: 858.6201063019689
seconds of wall time for 6.0 simulated biological seconds, with the dominant
runtime category in sPyNNaker provenance recorded as `Running Stage`. This is
engineering evidence about orchestration cost, not a stronger learning claim.
Tier 4.18a updates the runtime picture for the v0.7 chunked-host hardware path:
on seed `42`, delayed_cue and hard_noisy_switching both preserved their observed
task metrics at chunk sizes `10`, `25`, and `50`, while chunk `50` reduced
`sim.run` calls to `24` per task and became the fastest viable current bridge
setting. This is runtime/resource evidence, not hardware scaling or on-chip
learning.

Tier 5.1 is the first external-baseline comparison. Across 108 task/model/seed
runs, CRA matched the fixed-pattern tail result, lost the easy delayed-cue task
to simpler online learners, and showed its strongest comparative evidence on
sensor_control and hard noisy switching. Tier 5.2 extends this to 405
task/model/seed/run-length runs. At 1500 steps, final advantage tasks are zero:
sensor_control saturates for both CRA and baselines, delayed_cue remains
externally dominated, and hard_noisy_switching is mixed/negative for CRA. This
constrains the claim further: CRA is not universally better than simple learners,
and its current comparative value is short-horizon/task-dependent under these
settings. Tier 5.3 then runs 78 CRA-only diagnostic variants at 960 steps and
finds that `delayed_lr_0_20` restores delayed_cue tail accuracy to 1.0 and
improves hard_noisy_switching above the external median, but still below the
best external baseline. That makes delayed-credit strength the leading tuning
candidate, not a final superiority claim. Tier 5.4 confirms that candidate in a
120-run matrix at 960 and 1500 steps. The delayed-cue result ties the best
external tail score at 1.0; the hard noisy switching result beats the external
median but remains below the best external tail score. That justified a harder
SpiNNaker capsule using `delayed_lr_0_20`, but not a broad superiority claim.
The first Tier 4.16 hardware attempt ran cleanly
but failed the delayed-cue tail-accuracy criterion. Local NEST/Brian2 replay
reproduced the same delayed-cue seed pattern, so the current blocker is a
task/config/metric issue rather than a primary SpiNNaker execution failure.
Local repair diagnostics show that lengthening the delayed-cue probe to 1200
steps gives 37 tail events and passes in both NEST and Brian2 without changing
`delayed_lr_0_20`. Tier 4.17b then locally validates chunked scheduled input,
per-step binned spike readback, and host replay parity against step mode on NEST
and Brian2, with exact prediction/spike-bin parity and `5x` to `40x` fewer
`sim.run` calls. The repaired Tier 4.16a hardware repeat then passed on real
`pyNN.spiNNaker` for `delayed_cue`, seeds `42`, `43`, and `44`, 1200 steps,
`chunked + host`, and `chunk_size_steps=25`: 48 hardware `sim.run` calls per
seed, minimum 94976 real spikes, zero fallback/failures, mean tail accuracy 1.0,
mean tail prediction-target correlation 0.9999999999999997, and mean all
accuracy 0.9933333333333333. This is hardware evidence for repaired
delayed-cue transfer across seeds, not on-chip learning or hardware scaling. The
repaired hard-switch hardware repeat also passes across seeds `42`, `43`, and
`44` with zero fallback/failures and real spike readback. Together, Tier 4.16a
and Tier 4.16b support a narrow harder-task hardware-transfer claim for the
confirmed delayed-credit setting under `chunked + host`; they do not prove
hardware scaling, native dopamine/eligibility, lifecycle self-scaling, or
superiority over external baselines.

The project is best understood as a controlled neuromorphic learning prototype
with an unusually explicit evidence ledger. Its core contribution is not merely a
single performance number, but a reproducible path for separating true learning,
negative controls, architectural mechanism tests, backend portability, and
hardware-capsule evidence while preserving claim boundaries and external
baseline comparisons, including mixed or unfavorable findings.


Tier 5.17 adds a failed/non-promoted pre-reward representation diagnostic: the
no-label/no-reward exposure harness completed with zero non-oracle leakage and
zero raw dopamine, but the strict scaffold did not pass all probe, sham, and
sample-efficiency gates. Reward-free representation learning remains future
work, not a current claim. Tier 5.17b adds diagnostic classification only: one
positive subcase, one input-encoded/easy task, and one temporal task dominated
by fixed-history controls, routing the next repair toward intrinsic predictive /
MI-style preexposure. Tier 5.17c tested that repair and failed promotion under
held-out episode probes because target-shuffled, wrong-domain, STDP-only, and
best non-oracle controls were not cleanly separated. Reward-free representation
formation remains outside the current broad claim boundary. Tier 5.17d then
passes a narrower predictive-binding repair: cross-modal and reentry binding
tasks keep the zero-label/zero-reward/zero-dopamine contract and separate
target-shuffled, wrong-domain, history/reservoir, STDP-only, and best
non-oracle controls on held-out ambiguous episodes. This supports bounded
software pre-reward predictive-binding evidence only, not general unsupervised
concept learning, hardware/on-chip representation learning, full world
modeling, language, planning, AGI, or external-baseline superiority. Tier 5.17e
then passes the compact promotion/regression gate: v1.8 compact regression, v1.9
composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d
predictive-binding guardrails all remain green. This freezes v2.0 as bounded
host-side software predictive-binding evidence.

Tier 5.18 then adds noncanonical software self-evaluation / metacognitive
monitoring evidence over frozen v2.0: 150/150 rows complete with zero outcome
leakage and zero pre-feedback monitor failures; confidence predicts
primary-path errors and hazard/OOD/mismatch state, passes Brier/ECE calibration
gates, uncertainty rises under detected risk, and confidence-gated behavior
beats v2.0 no-monitor, monitor-only, random, time-shuffled, disabled,
anti-confidence, and best non-oracle controls. This is operational reliability
monitoring only, not consciousness, self-awareness, hardware evidence, language,
planning, or AGI. Tier 5.18c then freezes v2.1 after the full v2.0 compact gate
and Tier 5.18 guardrail both pass, preserving the same software-only reliability
monitoring boundary. Tier 5.9c subsequently rechecks the parked macro
eligibility mechanism against v2.1; v2.1 stays green, but macro still fails
trace-ablation specificity, so it remains non-promoted. Tier 4.20a passes as an
engineering hardware-transfer audit for v2.1, not hardware evidence, and routes
the next hardware step to a one-seed chunked probe without macro eligibility.
Tier 4.20b now passes at
`controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass/`
with an ingested copy at
`controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass_ingested/`;
it is one-seed v2.1 bridge/transport hardware evidence only, not native/on-chip
v2.1 mechanism execution.
