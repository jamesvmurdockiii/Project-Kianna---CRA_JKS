# Documentation Index

This directory contains the research-facing narrative docs.

| File | Purpose |
| --- | --- |
| `../codebasecontract.md` | Root operating contract for agents/humans: evidence discipline, code/update rules, EBRAINS workflow, promotion gates, validation, and anti-patterns. |
| `ABSTRACT.md` | Short abstract of CRA, current evidence, and claim boundaries. |
| `PAPER_READINESS_ROADMAP.md` | Strategic roadmap from the current evidence state to paper-ready claims, including pass/fail gates and make-or-break criteria. |
| `MECHANISM_STATUS.md` | Mechanism ledger separating promoted mechanisms, diagnostics, parked ideas, and future research targets. |
| `MASTER_EXECUTION_PLAN.md` | Operational step-by-step execution plan from the current state through chip-native migration, remaining capability tiers, final matrices, reproduction, and paper lock. |
| `TIER6_2_USEFULNESS_BATTERY_CONTRACT.md` | Current usefulness-testing contract: hard synthetic diagnostics, real-ish/real dataset transition rules, baseline requirements, pass/fail criteria, and hardware-transfer gates. |
| `REVIEWER_DEFENSE_PLAN.md` | Adversarial reviewer-attack matrix, statistical/fairness safeguards, and additional proof targets before paper release. |
| `WHITEPAPER.md` | Full technical whitepaper covering architecture, evidence, hardware, limitations, and roadmap. |
| `PAPER_RESULTS_TABLE.md` | Paper-facing evidence table generated from the canonical registry. |
| `RESEARCH_GRADE_AUDIT.md` | Generated hygiene/evidence-paperwork audit. |
| `CODEBASE_MAP.md` | Complete repository map covering source files, experiment harnesses, tests, runtime sidecar, and generated evidence groups. |
| `PUBLIC_REPO_HYGIENE.md` | Public Apache-2.0 repository hygiene policy: what belongs in Git, what stays ignored, EBRAINS package rules, security checks, and clean/commit SOP. |
| `SPINNAKER_EBRAINS_RUNBOOK.md` | Dedicated operational guide for EBRAINS/SpiNNaker uploads, JobManager commands, pass criteria, and lessons learned. |
| `SPINNAKER_EBRAINS_CUSTOM_RUNTIME_GUIDE.md` | Canonical custom-runtime guide based on official SpiNNakerManchester SDP/SCP, Spin1API, SARK, and EBRAINS JobManager lessons. |

## Evidence Categories

- **Canonical registry evidence** appears in `controlled_test_output/STUDY_REGISTRY.json` and the paper-facing results table.
- **Baseline-frozen mechanism evidence** passed a mechanism gate plus compact regression and has a frozen `baselines/CRA_EVIDENCE_BASELINE_vX.Y.*` lock, even if the source bundle is not a registry row.
- **Noncanonical diagnostic evidence** answers a design question but does not freeze a new baseline by itself.
- **Failed/parked diagnostic evidence** is kept deliberately as anti-p-hacking audit history.
- **Hardware prepare/probe evidence** is not a claim until reviewed and promoted.

`Noncanonical` does not mean useless; it means not a formal paper-table claim by itself.

Tier 4.15 is now canonical hardware repeatability evidence for the same minimal
fixed-pattern SpiNNaker capsule across seeds `42`, `43`, and `44`. It is not a
harder-task hardware or hardware-scaling claim.

Tier 5.1 is now canonical controlled software baseline evidence. It documents
where CRA has a hard-task edge and where simpler online learners beat it.

Tier 5.2 is now canonical controlled software learning-curve evidence. It shows
that the Tier 5.1 CRA edge does not strengthen at 1500 steps under the tested
settings.

Tier 5.3 is now canonical controlled software failure-analysis evidence. It
identifies stronger delayed credit as the leading candidate fix, but remains
software-only diagnostic evidence rather than a hardware or superiority claim.

Tier 5.4 is now canonical controlled software delayed-credit confirmation
evidence. It confirms `delayed_lr_0_20` at 960 and 1500 steps versus current
CRA and external-baseline medians, but remains software-only evidence and not a
hard-switching best-baseline superiority claim.

Tier 4.16a is now canonical repaired delayed-cue hardware-transfer evidence. It
confirms the `delayed_lr_0_20` delayed-cue capsule on real SpiNNaker across
seeds `42`, `43`, and `44`, but it is not a hard_noisy_switching, on-chip, or
hardware-scaling claim. Tier 4.16b hard_noisy_switching now also passes on
real SpiNNaker across seeds `42`, `43`, and `44` after aligned local bridge
repair and a seed-44 probe. This is repaired chunked-host hardware transfer, not
hardware scaling, native on-chip dopamine/eligibility, or external-baseline
superiority.

`baselines/CRA_EVIDENCE_BASELINE_v0.4.md` freezes the post-Tier-5.4 evidence
state so later work can extend it without rewriting this claim boundary.
`baselines/CRA_EVIDENCE_BASELINE_v0.5.md` freezes the pre-chunked-runtime
refactor state, `baselines/CRA_EVIDENCE_BASELINE_v0.6.md` freezes the
post-Tier-4.16a delayed-cue hardware-repeat state, and
`baselines/CRA_EVIDENCE_BASELINE_v0.7.md` freezes the post-Tier-4.16b
harder-task hardware-transfer state. `baselines/CRA_EVIDENCE_BASELINE_v0.8.md`
freezes the post-Tier-4.18a chunked-runtime hardware state.
`baselines/CRA_EVIDENCE_BASELINE_v0.9.md` freezes the post-Tier-5.5 expanded
software-baseline state.
`baselines/CRA_EVIDENCE_BASELINE_v1.0.md` freezes the post-Tier-5.6 tuned
baseline-fairness state.
`baselines/CRA_EVIDENCE_BASELINE_v1.1.md` freezes the post-Tier-5.7 compact
regression state.
`baselines/CRA_EVIDENCE_BASELINE_v1.2.md` freezes the post-Tier-6.1
lifecycle/self-scaling state. `baselines/CRA_EVIDENCE_BASELINE_v1.3.md` freezes
the post-Tier-6.3 lifecycle sham-control state.
`baselines/CRA_EVIDENCE_BASELINE_v1.4.md` freezes the post-Tier-6.4
circuit-motif causality state. `baselines/CRA_EVIDENCE_BASELINE_v1.5.md`
freezes the post-Tier-5.10e internal memory-retention state before
capacity/interference or sleep/replay work. `baselines/CRA_EVIDENCE_BASELINE_v1.6.md`
freezes the post-Tier-5.10g keyed context-memory repair state before replay,
composition/routing, or hardware memory work. `baselines/CRA_EVIDENCE_BASELINE_v1.7.md`
freezes the post-Tier-5.11d correct-binding replay/consolidation state before
predictive coding, routing/composition, hardware replay, or custom on-chip
runtime work. `baselines/CRA_EVIDENCE_BASELINE_v1.8.md` freezes bounded visible
predictive-context evidence, `baselines/CRA_EVIDENCE_BASELINE_v1.9.md` freezes
internal host-side composition/routing evidence, and
`baselines/CRA_EVIDENCE_BASELINE_v2.0.md` freezes bounded host-side
predictive-binding evidence. `baselines/CRA_EVIDENCE_BASELINE_v2.1.md` freezes
bounded host-side self-evaluation / reliability-monitoring evidence, and
`baselines/CRA_EVIDENCE_BASELINE_v2.2.md` freezes bounded host-side
fading-memory temporal-state evidence. `baselines/CRA_EVIDENCE_BASELINE_v2.3.md`
freezes generic bounded recurrent-state evidence,
`baselines/CRA_EVIDENCE_BASELINE_v2.4.md` freezes bounded cost-aware
policy/action evidence, and `baselines/CRA_EVIDENCE_BASELINE_v2.5.md` freezes
bounded reduced-feature planning/subgoal-control evidence. Tier 7.7a locks the
v2.5 standardized benchmark/usefulness scoreboard contract before scoring.
Native runtime locks are tracked
separately: `CRA_NATIVE_RUNTIME_BASELINE_v0.1`, `CRA_NATIVE_TASK_BASELINE_v0.2`,
`CRA_NATIVE_MECHANISM_BRIDGE_v0.3`, and the current
`CRA_LIFECYCLE_NATIVE_BASELINE_v0.4` lifecycle-native hardware baseline. The
older software v0.1, v0.2, and v0.3 baselines remain historical locks.

`baselines/CRA_NATIVE_SCALE_BASELINE_v0.5.md` freezes the bounded native-scale substrate closeout over replicated single-chip MCPL stress, two-chip communication, two-chip learning micro-task, and two-chip lifecycle traffic/resource evidence. It is not speedup, benchmark usefulness, true two-partition learning, lifecycle scaling, multi-shard learning, or AGI/ASI evidence.

Tier 5.18 now supplies noncanonical software self-evaluation /
metacognitive-monitoring diagnostic evidence over v2.0. It is useful
reviewer-defense evidence for calibrated pre-feedback reliability monitoring,
and Tier 5.18c freezes the bounded v2.1 software baseline after compact
regression. It is not a consciousness/self-awareness/hardware claim.

Tier 5.9c rechecked macro eligibility after v2.1 and failed promotion again:
the v2.1 guardrail stayed green, but macro residual did not separate from
trace-ablation controls. Tier 4.20a then passed as a hardware-transfer
readiness audit, not hardware evidence, and routes the next hardware work to a
one-seed v2.1 chunked probe without macro eligibility.

Tier 4.20b now passes as one-seed v2.1 bridge/transport hardware evidence at
`controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass/`
and ingested copy
`controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass_ingested/`.
It uses the in-process Tier 4.16 chunked-host bridge, seed `42`, tasks
`delayed_cue` and `hard_noisy_switching`, zero fallback/readback failures, and
nonzero real spike readback. It is not native v2.1/on-chip mechanism evidence.

The roadmap now explicitly tracks planned future architecture defenses for
catastrophic forgetting, recurrence-task repair, sleep/replay consolidation,
predictive coding/world-model behavior, compositional skill reuse, module
routing/contextual gating, working memory/context binding, policy/action
selection, spike encoding/temporal
coding, neuron-model sensitivity, unsupervised representation formation,
circuit-motif causality, curriculum generation, long-horizon planning/subgoal
control, reproduction hygiene, and eventual custom C/on-chip migration.
These are planned or diagnostic tiers, not promoted evidence, and must be
ablated before any paper claim uses them. Tier 5.9a and Tier 5.9b macro
eligibility have already failed promotion gates and are parked rather than
claims. Tier 5.10 multi-timescale memory has also failed as a first proxy, and
exposed that recurrence tasks had to be hardened before memory/replay claims.
Tier 5.10b has now passed as that task-validation repair: the repaired streams
require remembered context and cleanly fail wrong/reset/shuffled memory
controls. Tier 5.10c has now passed as a noncanonical software mechanism
diagnostic: explicit host-side context binding works on those repaired streams,
but it is not native/on-chip memory or sleep/replay evidence. Tier 5.10d
internalized the context-memory mechanism inside `Organism` and passed compact
regression; Tier 5.10e showed that it survives the first retention stressor.
Tier 5.10f then failed cleanly under capacity/interference pressure, and Tier
5.10g repaired that measured single-slot failure with bounded keyed/multi-slot
memory inside `Organism`. This is now v1.6 host-side keyed-memory evidence, not
native/on-chip memory, sleep/replay, hardware memory transfer, compositionality,
module routing, or general working memory.
Tier 5.11a then passed as a need diagnostic for replay/consolidation: v1.6
no-replay keyed memory degrades under silent reentry stressors while unbounded
keyed memory and oracle scaffold controls solve them, producing the predeclared
decision `replay_or_consolidation_needed`. This authorizes Tier 5.11b, but it is
not replay success and does not freeze a new baseline.
Tier 5.11b then ran the prioritized replay intervention and failed promotion
under the strict sham-control gate: prioritized replay reached `1.0` minimum
all/tail accuracy with zero leakage, but shuffled replay came too close on
`partial_key_reentry` (`0.4444444444444444 < 0.5` tail-edge criterion). v1.6
remained the memory baseline after 5.11b. Tier 5.11c repeats the stricter
sham-separation matrix and again blocks the narrower priority-specific claim:
candidate replay remains strong, but shuffled-order replay still comes too
close (`0.40740740740740733 < 0.5`). Tier 5.11d then promotes the broader
correct-binding replay/consolidation mechanism: the 189-run NEST matrix passes
with zero leakage, candidate minimum all/tail accuracy `1.0`/`1.0`, `1185`
replay events and writes, wrong-key/key-label-permuted/priority-only/no-write
controls fail to match it, and compact regression passes afterward. v1.7 is now
the current host-side software replay/consolidation baseline, while priority
weighting, native/on-chip replay, hardware memory transfer, composition, and
world modeling remain unproven.


Tier 5.12a now passes as noncanonical predictive task-validation evidence. It
shows the next predictive mechanism test has real pressure: causal predictive
state solves the battery, while current-reflex, sign-persistence, wrong-horizon,
and shuffled-target shortcuts do not. This is not predictive coding, world
modeling, language, planning, hardware prediction, or v1.8 by itself.

Tier 5.12b is retained as a failed predictive-context diagnostic, and Tier
5.12c repairs it. The 5.12c NEST matrix passes as host-side visible
predictive-context binding evidence with zero leakage, 570 writes/active
decision uses, exact scaffold match, and separation from v1.7,
shuffled/permuted/no-write shams, shortcut controls, and selected external
baselines. Tier 5.12d then passes compact regression and freezes v1.8 as
bounded host-side visible predictive-context software evidence. It is not
hidden-regime inference, full world modeling, language, planning, hardware
prediction, hardware scaling, native on-chip learning, compositionality, or
external-baseline superiority.

Tier 5.13 now passes as noncanonical compositional skill-reuse diagnostic
evidence. The explicit host-side reusable-module scaffold solves held-out
skill-pair, order-sensitive-chain, and distractor-chain compositions with `1.0`
first-heldout and total heldout accuracy, while raw v1.8 CRA, combo
memorization, module shams, and selected standard baselines fail to close the
gap. This authorizes internal CRA composition/routing work, but it is not
native/internal CRA compositionality, hardware evidence, language, planning,
AGI, or a v1.9 freeze.
Tier 5.13b now passes as noncanonical module-routing/contextual-gating
diagnostic evidence. The explicit host-side router scaffold selects the correct
module before feedback on delayed-context, distractor, and reentry routing
tasks with `1.0` minimum first-heldout, heldout, and router accuracy. Raw v1.8
and the CRA router-input bridge remain at `0.0` first-heldout accuracy, so this
authorizes internal CRA routing/gating work but does not prove native/internal
routing, hardware evidence, language, planning, AGI, or a v1.9 freeze.
Tier 5.13c now passes as baseline-frozen internal host-side composition/routing
promotion evidence. The internal CRA pathway completes 243/243 cells with zero
feedback leakage, learns primitive module tables and context-router scores,
selects routed/composed features before feedback, reaches `1.0` minimum
held-out composition/routing accuracy and router accuracy, separates from
internal shams, and a fresh full compact regression passes afterward. This
freezes v1.9 as bounded host-side software composition/routing evidence. It is
not SpiNNaker hardware evidence, native/custom-C on-chip routing, language,
long-horizon planning, AGI, or external-baseline superiority.
Tier 5.14 now passes as noncanonical working-memory/context-binding diagnostic
evidence over frozen v1.9. The combined mock run passes both context/cue-memory
and delayed module-state routing subsuites: context-memory reaches `1.0`
accuracy on all three memory-pressure tasks with minimum edge `0.5` versus the
best memory sham and sign persistence, while routing reaches `1.0`
first-heldout, heldout, and router accuracy on all three delayed module-state
tasks with minimum edge `1.0` versus routing-off CRA and `0.5` versus the best
routing sham. It does not freeze v2.0 by itself and is not hardware/on-chip
working memory, language, planning, AGI, or external-baseline superiority.

Tier 5.15 now passes as noncanonical software spike-encoding/temporal-code
diagnostic evidence. The 540-run matrix exports sampled spike traces and
encoding metadata, and shows latency, burst, and temporal-interval encodings can
carry task-relevant information on fixed_pattern, delayed_cue, and
sensor_control while time-shuffle and rate-only controls lose. It does not
freeze v2.0, does not prove hardware/on-chip temporal coding, and does not prove
hard_noisy_switching temporal superiority.

Tier 5.16 now passes as noncanonical NEST neuron-parameter sensitivity
evidence. The 66-run matrix covers 11 LIF variants across threshold, membrane
tau, refractory period, capacitance, and synaptic tau; all 33 task/variant
cells remain functional with zero fallback/failure counters, zero propagation
failures, zero collapse rows, and monotonic direct LIF response probes. It does
not freeze v2.0 and is not SpiNNaker/custom-C/on-chip neuron evidence.

Tier 5.17 now exists as failed noncanonical pre-reward representation diagnostic
evidence. The 81-run no-label/no-reward exposure matrix completed with zero
non-oracle label leakage, zero reward visibility, and zero raw dopamine during
exposure, but the strict no-history-input scaffold failed probe, sham-separation,
and sample-efficiency promotion gates. It is not reward-free representation
learning, unsupervised concept learning, hardware/on-chip representation evidence,
or a v2.0 freeze.

Tier 5.17b now exists as passed noncanonical failure-analysis evidence. It
classifies the failed Tier 5.17 bundle as one positive subcase, one
input-encoded/easy task, and one temporal task dominated by fixed-history
controls. It routes the repair to Tier 5.17c intrinsic predictive / MI-style
preexposure. It still does not promote reward-free representation learning or
freeze v2.0.

Tier 5.17c now exists as failed noncanonical intrinsic predictive preexposure
evidence. The 99-run matrix held the zero-label/zero-reward/zero-dopamine
contract, but target-shuffled, wrong-domain, STDP-only, and best non-oracle
controls were not cleanly separated under held-out episode probes. Reward-free
representation learning remains unpromoted.

Tier 5.17d now exists as passed bounded noncanonical predictive-binding repair
evidence. The 60-run matrix keeps the zero-label/zero-reward/zero-dopamine
contract, scores held-out ambiguous episodes after visible cues fade, and
separates target-shuffled, wrong-domain, history/reservoir, STDP-only, and best
non-oracle controls on cross-modal and reentry binding tasks. This supports a
bounded software pre-reward predictive-binding claim, not general unsupervised
concept learning, hardware/on-chip representation formation, full world
modeling, language, planning, AGI, or a v2.0 freeze.

Tier 5.17e now exists as baseline-frozen predictive-binding promotion/regression
evidence. The full gate passes v1.8 compact regression, v1.9
composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d
predictive-binding guardrails, freezing `baselines/CRA_EVIDENCE_BASELINE_v2.0.md`.
This is bounded host-side software evidence only, not hardware/on-chip
representation formation, broad unsupervised concept learning, full world
modeling, language, planning, AGI, or external-baseline superiority.

Tier 4.18a now passes as canonical v0.7 chunked hardware runtime evidence. It
recommends `chunk_size_steps=50` for the current chunked-host hardware bridge.
Prepared Tier 4.18a capsules remain run packages only until their returned
hardware output is reviewed and promoted.

Tier 5.5 now passes as canonical expanded software-baseline evidence. It
completed the 1,800-run matrix for locked CRA v0.8 versus implemented external
baselines. It supports robust advantage/non-dominated hard-adaptive regimes, but
it is not hardware evidence, not a hyperparameter fairness audit, and not a
universal or best-baseline superiority claim.

Tier 5.6 now passes as canonical tuned-baseline fairness evidence. It completed
the 990-run audit with CRA locked and external baselines retuned under
documented budgets. It leaves four surviving target regimes after retuning, but
it is not hardware evidence, all-possible-baselines coverage, or universal
best-baseline superiority.

Tier 5.7 now passes as canonical compact-regression evidence. It verifies that
the promoted delayed-credit setting still passes compact negative controls,
positive controls, architecture ablations, and delayed_cue/hard_noisy_switching
smokes before Tier 6.1 lifecycle/self-scaling was promoted.

Tier 6.1 now passes as canonical software lifecycle/self-scaling evidence. It
shows clean lineage expansion and two hard_noisy_switching advantage regimes
versus same-initial fixed-N controls. The event boundary is important: 74
cleavage events, 1 adult birth event, and 0 deaths, so this is not full adult
turnover, not sham-control proof, not hardware lifecycle, and not
external-baseline superiority.

Tier 6.3 now passes as canonical software lifecycle sham-control evidence. It
shows the Tier 6.1 organism/lifecycle advantage survives fixed max-pool capacity,
event-count replay, no-trophic, no-dopamine, and no-plasticity shams, with clean
actual-run lineage and intentional lineage-ID shuffle detection. It is still not
hardware lifecycle, native on-chip lifecycle, full adult turnover, or
external-baseline superiority.

Tier 6.4 now passes as canonical software circuit-motif causality evidence. It
uses a seeded motif-diverse graph for hard_noisy_switching, records pre-reward
motif activity, shows selected motif ablations cause predicted losses, and shows
random/monolithic controls do not dominate under adaptive criteria. It is still
not hardware motif execution, custom-C/on-chip learning, compositionality, or
world-model evidence.

Start with the root `README.md` if you are new to the project.
