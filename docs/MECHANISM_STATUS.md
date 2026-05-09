# CRA Mechanism Status

Last updated: 2026-05-09.

This document separates three things that can otherwise get blurred:

1. mechanisms that have earned bounded evidence,
2. mechanisms that exist only as diagnostics or partial bridges,
3. mechanisms/tasks still planned for future usefulness testing.

The rule is simple: a mechanism is not treated as part of the paper-lock claim
unless it has passed targeted controls, ablations or shams, repeatability where
appropriate, and a compact regression or freeze gate.

## Current promoted or bounded mechanisms

| # | Mechanism | Current evidence level | Boundary |
| ---: | --- | --- | --- |
| 1 | Reward-modulated local plasticity / dopamine path | Core Tier 2/3 controls and ablations passed. | Controlled synthetic learning evidence, not universal learning. |
| 2 | Delayed-credit PendingHorizon / delayed_lr_0_20 path | Tier 5.4 and repaired Tier 4.16 hardware transfer passed. | Host-side delayed-credit mechanism; native macro eligibility is not promoted. |
| 3 | Trophic/ecology pressure | Tier 3, Tier 6.1, Tier 6.3, and lifecycle-native gates support bounded value. | Bounded ecology/lifecycle evidence, not open-ended organism autonomy. |
| 4 | Lifecycle/static-pool self-scaling | Software lifecycle/sham controls passed; native lifecycle baseline v0.4 passed; 4.32g two-chip lifecycle traffic passed. | Static pool, masks, lineage, trophic counters; not dynamic population creation or lifecycle scaling. |
| 5 | Circuit motifs / reef topology / WTA-style structure | Tier 6.4 motif-causality gate passed. | Software motif evidence; not proof that all motif variants scale natively. |
| 6 | Keyed/multi-slot context memory | Tier 5.10g froze bounded v1.6-style evidence; Tier 4.29a transferred native bridge. | Bounded keyed memory, not general working memory or language. |
| 7 | Generic correct-binding replay/consolidation | Tier 5.11d promoted generic replay/consolidation; Tier 4.29e transferred host-scheduled native bridge. | Priority weighting is not proven; native sleep/replay buffers are deferred. |
| 8 | Predictive-context binding | Tier 5.12c/5.12d froze bounded v1.8 evidence; Tier 4.29c transferred native bridge. | Visible predictive context only; not full world modeling. |
| 9 | Composition/routing/module gating | Tier 5.13c froze bounded v1.9 evidence; Tier 4.29b transferred native bridge. | Bounded reusable-module routing, not language or long-horizon planning. |
| 10 | Pre-reward predictive binding / intrinsic representation repair | Tier 5.17d/5.17e froze bounded v2.0 evidence. | Useful pre-reward predictive-binding structure on tested tasks, not general unsupervised concept learning. |
| 11 | Self-evaluation / confidence-gated adaptation | Tier 5.18/5.18c froze bounded v2.1 evidence; Tier 4.29d transferred native bridge. | Operational confidence monitoring, not consciousness/self-awareness. |
| 12 | Fading-memory temporal state | Tier 5.19c froze bounded v2.2 evidence; Tier 4.31a-d moved the seven-EMA temporal substrate through native readiness/source/hardware smoke. | Fading memory only; bounded nonlinear recurrence remains unproven. |
| 13 | Native MCPL/multi-core/multi-chip substrate | CRA_NATIVE_SCALE_BASELINE_v0.5 freezes 4.32a/4.32d/4.32e/4.32g evidence. | Substrate transfer/scaling path only; not usefulness, speedup, or benchmark superiority. |
| 14 | Generic bounded recurrent interface | Tier 7.0j froze bounded host-side v2.3 evidence after the locked public scoreboard and compact regression. | Generic interface evidence only; topology-specific recurrence and ESN superiority remain nonclaims. |
| 15 | Cost-aware policy/action selection | Tier 7.4c froze bounded host-side v2.4 evidence after full compact regression. | Local policy/action evidence only; not broad public usefulness or reinforcement learning solved. |
| 16 | Reduced-feature planning/subgoal control | Tier 7.6e froze bounded host-side v2.5 evidence after Tier 7.6d repair and full compact regression. | Bounded software planning diagnostics only; not broad planning/reasoning, language, autonomous on-chip planning, or AGI/ASI. |

## Diagnostic coverage that is not a promoted mechanism by itself

| Area | Status | Why it is not a standalone promoted mechanism |
| --- | --- | --- |
| Working memory / context binding coverage | Tier 5.14 passed as coverage over v1.9. | It did not introduce a separate mechanism beyond the already frozen memory/routing stack. |
| Spike encoding / temporal code suite | Tier 5.15 passed. | Shows timing information can matter in software diagnostics, but it is coverage, not a new mechanism. |
| Neuron model / parameter sensitivity | Tier 5.16 passed. | Robustness evidence, not a new mechanism. |
| Continuous readout/interface repair | Tier 7.0c/7.0d diagnosed and narrowed. | Lag-only baselines explained the benchmark path, so no mechanism was promoted. |

## Planned, parked, or not-yet-proven mechanisms

These are not paper claims yet. They should not be ported broadly to hardware
until a software/usefulness gate creates a measured need.

| # | Mechanism or program | Current state | Re-entry rule |
| ---: | --- | --- | --- |
| 1 | Macro eligibility / native eligibility traces | Tier 5.9a/b/c failed or stayed non-promoted. | Reopen only if a future task proves PendingHorizon/fading memory cannot handle measured credit assignment. |
| 2 | Priority-specific replay | Not proven; generic correct-binding replay is promoted instead. | Reopen only if generic replay helps but priority order becomes a measured bottleneck. |
| 3 | Native replay buffers / sleep-on-chip | Deferred. | Implement only if host-scheduled replay becomes a scaling/timing blocker after usefulness is shown. |
| 4 | Bounded nonlinear recurrence | Unproven after Tier 5.19; fading memory is the promoted narrower mechanism. | Reopen if hard temporal tasks require recurrence beyond causal EMA traces. |
| 5 | True two-partition cross-chip learning | Not implemented. | Requires origin/target shard semantics and a new predeclared inter-chip learning contract. |
| 6 | Multi-shard learning and lifecycle scaling | Not implemented as a claim. | Requires v0.5 substrate plus a usefulness-selected task and explicit scaling criteria. |
| 7 | Autonomous lifecycle-to-learning MCPL | Not yet proven; current lifecycle bridges are bounded/static or traffic/resource smokes. | Implement after lifecycle helps on useful tasks and host-ferrying becomes the blocker. |
| 8 | Dynamic population creation | Not supported in the PyNN/SpiNNaker path; static pools and active masks are the supported route. | Only revisit with a custom runtime design that predeclares allocation/resource semantics. |
| 9 | Curriculum public/usefulness transfer | Tier 7.5 produced synthetic generated-family evidence but no public-usefulness claim. | Re-enter through a locked standardized benchmark/usefulness scoreboard, not through more generator tuning. |
| 10 | Long-horizon planning public/usefulness transfer | Tier 7.6 froze bounded v2.5 software evidence; Tier 7.7a locked the public/standardized scoreboard contract; Tier 7.7b passed with standardized progress versus v2.3, driven by Mackey-Glass; Tier 7.7c locked the long-run matrix; Tier 7.7d found the long-run NARMA10 stream is non-finite at 16000/32000; Tier 7.7e selected the repaired `narma10_reduced_input_u02` stream; Tier 7.7f reran the repaired long-run scoreboard and classified the result as `mackey_only_localized`; Tier 7.7g locked the Lorenz/NARMA capacity diagnostic; Tier 7.7h scored it and classified `overfit_or_sham_blocked`; Tier 7.7i locked the state-specificity/sham-separation contract. | Next step is Tier 7.7j capacity sham-separation / state-specificity scoring gate. Do not add new mechanisms until the Lorenz capacity gain is separated from generic/permuted recurrent feature effects. |
| 12 | Language/multimodal grounding | Future research direction, not current paper scope. | Requires separate task families, baselines, and safety boundaries. |

## Current strategic rule

Do not keep porting every planned mechanism to native C just because it is on the
roadmap. From v0.5 forward:

```text
software proves usefulness;
hardware proves transfer;
native C proves scale path.
```

The next project phase should use the software/Python/NEST path for hard
synthetic, real-ish, held-out, and real-data benchmarks. Only mechanisms or task
paths that survive those gates should be promoted back into native SpiNNaker
work.
