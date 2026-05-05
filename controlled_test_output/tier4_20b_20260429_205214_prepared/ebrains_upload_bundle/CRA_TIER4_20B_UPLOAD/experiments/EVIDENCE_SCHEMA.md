# CRA Evidence Schema

This project separates experiment execution from study evidence accounting.
Experiment harnesses write raw bundles under `controlled_test_output/`; the
registry script decides which bundles are canonical and validates the evidence
trail.

## Registry Command

Run this after any new controlled experiment, hardware ingest, or artifact
cleanup:

```bash
python3 experiments/evidence_registry.py
```

The command writes:

- `controlled_test_output/STUDY_REGISTRY.json`
- `controlled_test_output/STUDY_REGISTRY.csv`
- `controlled_test_output/README.md`
- `STUDY_EVIDENCE_INDEX.md`
- normalized `controlled_test_output/*_latest_manifest.json` pointers

After the registry is current, run:

```bash
python3 experiments/export_paper_results_table.py
python3 experiments/repo_audit.py
```

Those commands write the paper-facing table and research-grade audit reports.

## Canonical Entry Fields

Every canonical evidence entry must have:

- `entry_id`: stable citation key, for example `tier4_13_spinnaker_hardware_capsule`
- `tier_label`: human-readable tier name
- `plan_position`: where the entry sits in the 12-core-test plan or addenda
- `status`: `pass`, `fail`, `blocked`, `prepared`, or `unknown`
- `source_generated_at_utc`: timestamp from the source result bundle
- `canonical_output_dir`: absolute local path to the accepted evidence bundle
- `results_json`: machine-readable source result
- `report_md`: human-readable source result
- `summary_csv`: compact table, when applicable
- `harness`: experiment runner that generated or ingested the bundle
- `claim`: the strongest claim supported by this evidence
- `caveat`: the explicit boundary that prevents overclaiming
- `test_results`: normalized per-test status, criteria counts, metrics, and artifacts
- `missing_expected_artifacts`: any required files absent from the bundle

## Canonical Bundle Requirements

A bundle can be canonical only if:

- the result JSON exists and parses
- the Markdown report exists
- the summary CSV exists when the harness produces one
- all required plots/provenance files for that tier exist
- all canonical criteria pass
- the claim and caveat are documented
- the matching `*_latest_manifest.json` points to this bundle



## Evidence Categories

This repo uses five evidence labels so paper claims stay clean:

- **Canonical registry evidence**: entries in `controlled_test_output/STUDY_REGISTRY.json`; these populate the paper-facing results table and require all registered criteria/artifacts to pass.
- **Baseline-frozen mechanism evidence**: a mechanism diagnostic or promotion gate that passed its predeclared gate, preserved compact regression, and has a frozen `baselines/CRA_EVIDENCE_BASELINE_vX.Y.*` lock, but is not necessarily listed as a canonical registry bundle yet.
- **Noncanonical diagnostic evidence**: useful pass/fail diagnostic work that answers a design question but does not by itself freeze a new baseline or enter the canonical paper table.
- **Failed/parked diagnostic evidence**: clean negative evidence retained to prevent p-hacking and explain why a mechanism was not promoted.
- **Hardware prepare/probe evidence**: prepared capsules and one-off probes; these are not hardware claims until returned artifacts are reviewed and explicitly promoted.

In short: `noncanonical` means the result is audit-relevant but not a formal registry/paper-table claim by itself. A frozen baseline such as v1.6, v1.7, v1.9, v2.0, or v2.1 is stronger than an ordinary diagnostic even when its source bundle remains outside the canonical registry.

## Citation Rules

- Cite only entries in `controlled_test_output/STUDY_REGISTRY.json`.
- Treat older timestamped reruns as audit history unless promoted in the registry.
- Treat `_phase3_probe_*` and `_quarantine_noncanonical/` as debug/provenance material.
- Do not cite Tier 4.12 as hardware learning; it is NEST/Brian2 parity plus SpiNNaker prep.
- Do cite Tier 4.13 as a minimal SpiNNaker hardware-capsule pass, with the single-seed `N=8` boundary.
- Do cite Tier 4.14 only as hardware runtime/provenance characterization, not repeatability or scaling.
- Do cite Tier 4.15 only as three-seed repeatability of the same minimal fixed-pattern hardware capsule, not harder-task hardware or hardware scaling.
- Do cite Tier 5.1 only as a controlled software external-baseline comparison; it documents both CRA hard-task advantages and simpler-baseline wins.
- Do cite Tier 5.2 only as a controlled software learning-curve sweep; it shows the Tier 5.1 CRA edge does not strengthen at 1500 steps under the tested settings.
- Do cite Tier 5.3 only as controlled software failure-analysis evidence; it identifies stronger delayed credit as a candidate fix but is not hardware or final competitiveness evidence.
- Do cite Tier 5.4 only as controlled software delayed-credit confirmation; it confirms `delayed_lr_0_20` against current CRA and external medians at 960 and 1500 steps, but it is not hardware evidence or hard-switching superiority over the best external baseline.
- Do cite Tier 4.16a only as repaired delayed-cue hardware transfer across seeds `42`, `43`, and `44` using `delayed_lr_0_20`, `chunked + host`, zero fallback/failures, and real spike readback.
- Do cite Tier 4.16b only as repaired hard_noisy_switching hardware transfer across seeds `42`, `43`, and `44` using `delayed_lr_0_20`, `chunked + host`, zero fallback/failures, real spike readback, and tail accuracy min `0.5238095238095238`.
- Do not cite Tier 4.16 as hardware scaling, lifecycle/self-scaling, continuous/on-chip learning, native dopamine/eligibility traces, or external-baseline superiority.
- Do not cite Tier 4.16 prepare bundles as evidence.
- Treat Tier 4.16 failed hardware, Tier 4.16a debug bundles, the Tier 4.16b hard-switching failed hardware bundle, the repaired seed-44 hard-switch probe, and the corrected/aligned Tier 4.16b-debug bundles as noncanonical diagnostics. They may be cited in debugging notes, but the successful harder-task hardware evidence is the promoted three-seed Tier 4.16b bundle.
- Treat Tier 4.16a-fix bundles as noncanonical local repair diagnostics. They justified the repaired hardware repeat design, not a hardware pass by themselves.
- Treat Tier 4.17 bundles as noncanonical runtime contract and parity diagnostics. Tier 4.17b locally validates scheduled input, per-step binned readback, and host replay parity for NEST/Brian2, and Tier 4.16 now exposes that chunked host bridge. It is not SpiNNaker hardware evidence and not a continuous/on-chip learning claim.
- Treat Tier 4.18a prepare bundles as run packages only. The canonical Tier 4.18a pass may be cited as v0.7 chunked-host runtime/resource characterization: chunk sizes 10/25/50 on delayed_cue and hard_noisy_switching, seed 42, with chunk 50 recommended. Do not cite it as hardware scaling, lifecycle/self-scaling, native dopamine/eligibility, continuous/custom-C runtime, or superiority over external baselines.
- Do cite Tier 5.5 only as controlled software expanded-baseline evidence: 1,800 runs, 10 seeds, run lengths 120/240/480/960/1500, locked CRA v0.8, eight implemented external baselines, paired confidence intervals/effect sizes, per-seed audit rows, and a fairness contract. Do not cite it as hardware evidence, hyperparameter fairness completion, universal superiority, or best-baseline dominance.
- Do cite Tier 5.6 only as controlled software tuned-baseline fairness evidence: 990 runs, locked CRA delayed-credit setting, predeclared external-baseline candidate budgets, 32 candidate profiles, 48 best/median profile groups, six task/run-length comparisons, and four surviving target regimes after retuning. Do not cite it as hardware evidence, all-possible-baselines coverage, universal superiority, or best-baseline dominance at every metric/horizon.
- Do cite Tier 5.7 only as controlled software compact-regression evidence: promoted delayed-credit setting, Tier 1 controls, Tier 2 learning proof, Tier 3 ablations, and delayed_cue/hard_noisy_switching smokes all passed. Do not cite it as a new capability, hardware evidence, lifecycle/self-scaling evidence, or external-baseline superiority.
- Do cite Tier 5.10g as baseline-frozen internal keyed-memory repair evidence: bounded keyed/multi-slot host memory repaired the Tier 5.10f single-slot capacity/interference failure, beat v1.5 single-slot memory and slot shams, preserved compact regression, and froze v1.6. Do not cite it as native/on-chip memory, sleep/replay, hardware memory transfer, compositionality, module routing, or general working memory.
- Do cite Tier 5.11a only as noncanonical sleep/replay need-test evidence: the 171-run NEST matrix completed with zero leakage, v1.6 no-replay degraded on silent reentry stressors, unbounded keyed memory and oracle scaffold solved them at 1.0, and the predeclared decision was `replay_or_consolidation_needed`. Do not cite it as replay success, hardware memory, native on-chip memory, or a new frozen baseline.
- Do cite Tier 5.11b only as failed/non-promoted replay-intervention evidence: the corrected 162-run NEST matrix completed with zero feedback/replay leakage, prioritized replay reached 1.0 minimum all/tail accuracy and full gap closure, but the shuffled-replay sham-control tail edge failed (`0.4444444444444444 < 0.5`). Do not cite it as replay success, sleep/consolidation proof, hardware replay, native on-chip memory, or a v1.7 freeze.
- Do cite Tier 5.11c only as failed/non-promoted priority-specific replay-sham evidence: the 189-run NEST matrix completed with zero leakage and strong candidate repair, but shuffled-order replay still came too close (`0.40740740740740733 < 0.5`). Do not cite it as proof that priority weighting is essential.
- Do cite Tier 5.11d as baseline-frozen software replay/consolidation evidence: the 189-run NEST matrix completed with zero leakage, correct-binding candidate replay reached 1.0 minimum all/tail accuracy and full gap closure, no-replay tail stayed 0, wrong-key/key-label-permuted/priority-only/no-consolidation controls failed to match it, and compact regression passed afterward. It freezes v1.7 as host-side software replay/consolidation evidence, not native/on-chip replay, hardware memory transfer, priority-weighting proof, compositionality, or world modeling.
- Do cite Tier 5.12a only as predictive task-validation evidence: the 144-cell software matrix completed with zero feedback leakage across 10044 checked rows, causal predictive-memory controls solved all four tasks at 1.0, and current-reflex/sign-persistence/wrong-horizon/shuffled-target controls failed under the predeclared ceilings. Do not cite it as CRA predictive coding, world modeling, language, planning, hardware prediction, or v1.8 by itself.
- Treat Tier 5.12b as failed/non-promoted predictive-context mechanism evidence: the 162-cell NEST matrix completed with zero leakage and active/scaffold-matching predictive context, but the absolute masked-input gates failed and wrong-sign context behaved as a stable alternate code rather than an information-destroying sham. Do not cite it as a pass.
- Do cite Tier 5.12c as host-side visible predictive-context software evidence: the 171-cell NEST matrix completed with zero leakage, the candidate matched the external scaffold, produced 570 writes/active decision uses, beat v1.7 reactive CRA, beat shuffled/permuted/no-write shams, beat shortcut controls, and beat selected external baselines. Tier 5.12d supplies the separate promotion gate.
- Do cite Tier 5.12d as controlled software compact-regression/promotion evidence: six child checks passed, covering Tier 1 controls, Tier 2 learning, Tier 3 ablations, delayed_cue/hard_noisy_switching smokes, v1.7 replay/consolidation, and compact predictive-context sham separation. It freezes v1.8 as bounded host-side visible predictive-context software evidence. Do not cite it as hidden-regime inference, full world modeling, language, planning, hardware prediction, hardware scaling, native on-chip learning, compositionality, or external-baseline superiority.
- Do cite Tier 5.13 only as noncanonical compositional-skill diagnostic evidence: the 126-cell mock matrix completed with zero leakage, explicit host-side reusable-module composition reached 1.0 first-heldout and total heldout accuracy across heldout_skill_pair, order_sensitive_chain, and distractor_skill_chain, raw v1.8 and combo memorization stayed at 0.0 first-heldout accuracy, module shams were materially worse, and selected standard baselines did not close the first-heldout gap. It authorizes internal composition/routing work, not native CRA compositionality, hardware composition, language, planning, AGI, or a v1.9 freeze.
- Do cite Tier 5.13b only as noncanonical module-routing diagnostic evidence: the 126-cell mock matrix completed with zero leakage across 11592 checked feedback rows, explicit host-side contextual routing reached 1.0 first-heldout, heldout, and router accuracy across heldout_context_routing, distractor_router_chain, and context_reentry_routing, selected routes before feedback 276 times, raw v1.8 and the CRA router-input bridge stayed at 0.0 first-heldout accuracy, routing shams were materially worse, and selected standard baselines did not close the first-heldout gap. It authorizes internal routing/gating work, not native CRA routing, successful bridge integration, hardware routing, language, planning, AGI, or a v1.9 freeze.
- Do cite Tier 5.13c plus the post-run full compact regression as baseline-frozen v1.9 host-side software composition/routing evidence: the 243-cell mock matrix completed with zero leakage across 22941 checked feedback rows, internal CRA learned primitive module tables and context-router scores, selected routed/composed features before feedback, reached 1.0 minimum held-out composition/routing and router accuracy, separated from internal no-write/reset/shuffle/random/always-on shams, and full compact regression passed at `controlled_test_output/tier5_12d_20260429_122720/`. It is not SpiNNaker hardware evidence, native/custom-C on-chip routing, language, planning, AGI, or external-baseline superiority.
- Do cite Tier 5.14 only as noncanonical working-memory/context-binding diagnostic evidence: the mock run passed both memory/context-binding and delayed module-state routing subsuites, context-memory reached 1.0 accuracy on all three memory-pressure tasks with 0.5 minimum edge versus the best memory sham and sign persistence, and routing reached 1.0 first-heldout/heldout/router accuracy on all three delayed module-state tasks with 1.0 minimum edge versus routing-off CRA and 0.5 versus the best routing sham. It does not freeze v2.0 by itself and is not SpiNNaker hardware evidence, native/custom-C on-chip working memory, language, planning, AGI, or external-baseline superiority.
- Do cite Tier 5.15 only as noncanonical software temporal-code diagnostic evidence: the 540-run `numpy_temporal_code` matrix completed with 60 spike-trace artifacts, 60 encoding-metadata artifacts, 9 successful genuinely temporal rows, and 3 successful non-finance temporal rows; latency, burst, and temporal-interval encodings beat time-shuffle and/or rate-only controls on fixed_pattern, delayed_cue, and sensor_control. Do not cite it as SpiNNaker hardware temporal coding, custom-C/on-chip temporal coding, a v2.0 freeze, neuron-model robustness, unsupervised representation learning, hard-switch temporal superiority, language, planning, AGI, or external-baseline superiority.
- Do cite Tier 5.16 only as noncanonical NEST neuron-parameter sensitivity evidence: the 66-run matrix completed across 11 LIF variants with all 33 task/variant cells functional, default minimum tail accuracy 0.8, zero collapse rows, zero parameter-propagation failures, zero backend failure/fallback counters, and monotonic direct LIF current-response probes. Do not cite it as SpiNNaker hardware neuron robustness, custom-C/on-chip neuron evidence, adaptive-LIF/Izhikevich evidence, a v2.0 freeze, language, planning, AGI, or external-baseline superiority.
- Treat Tier 5.17 only as failed noncanonical pre-reward representation diagnostic evidence: the 81-run matrix completed with zero non-oracle label leakage, zero reward visibility, and zero raw dopamine during exposure, but the strict no-history-input scaffold failed promotion gates. Tier 5.17b is passed failure-analysis coverage only: it classifies the failure and routes the repair to intrinsic predictive / MI-style preexposure. Tier 5.17c tested that repair and failed promotion under held-out episode probes because target-shuffled, wrong-domain, STDP-only, and best non-oracle controls were not cleanly separated. Tier 5.17d passed as bounded predictive-binding evidence on cross-modal and reentry binding tasks with zero leakage and target-shuffle/wrong-domain/history/reservoir/STDP-only/best-control separation. Tier 5.17e then passed the compact promotion/regression gate and freezes v2.0 after v1.8 compact regression, v1.9 composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d predictive-binding all remain green. Do not cite v2.0 as general reward-free representation learning, unsupervised concept formation, hardware/on-chip representation evidence, full world modeling, language, planning, AGI, or external-baseline superiority.
- Do cite Tier 6.1 only as controlled software lifecycle expansion/self-scaling evidence: fixed controls stayed fixed, lifecycle cases produced clean-lineage new-polyp events, and two hard_noisy_switching lifecycle regimes beat same-initial fixed controls. Do not cite it as full adult birth/death turnover, hardware lifecycle, native on-chip lifecycle, or external-baseline superiority; event analysis is 74 cleavage events, 1 adult birth event, and 0 deaths.
- Do cite Tier 6.3 only as controlled software lifecycle sham-control evidence: intact lifecycle beat all 10 requested performance-sham comparisons, including fixed max-pool capacity, event-count replay, no trophic pressure, no dopamine, and no plasticity, with clean actual-run lineage and lineage-ID shuffle detection. Do not cite it as hardware lifecycle, native on-chip lifecycle, full adult turnover, external-baseline superiority, compositionality, or world modeling.
- Do cite Tier 6.4 only as controlled software circuit-motif causality evidence: seeded motif-diverse intact graphs logged pre-reward motif activity, selected motif ablations caused predicted losses, random/monolithic controls did not dominate under adaptive criteria, and motif-label shuffle did not itself create a loss. Do not cite it as hardware motif execution, custom-C/on-chip learning, compositionality, world modeling, real-world usefulness, or universal baseline superiority.
- Treat Tier 5.17 as failed pre-reward representation-formation coverage and
  Tier 5.17b as diagnostic failure-analysis coverage. Tier 5.15 supplies
  software-only temporal-code diagnostic evidence and Tier 5.16 supplies NEST
  neuron-parameter sensitivity evidence, but do not cite unsupervised/reward-free
  representation learning beyond the bounded predictive-binding claim supported
  by Tier 5.17d and frozen by Tier 5.17e until future mechanisms pass broader
  controls.
- Treat Tier 5.18 as passed software self-evaluation / metacognitive-monitoring
  diagnostic evidence over frozen v2.0, and Tier 5.18c as the v2.1 promotion
  gate: pre-feedback
  confidence predicts primary-path errors and hazard/OOD/mismatch state,
  confidence-gated behavior beats v2.0 no-monitor, monitor-only, random,
  shuffled, disabled, anti-confidence, and best non-oracle controls, and zero
  outcome leakage/pre-feedback monitor failures were observed; the full v2.0
  compact gate and Tier 5.18 guardrail both pass at Tier 5.18c. Do not cite it
  as consciousness, self-awareness, introspection, hardware evidence, AGI,
  language, planning, or external-baseline superiority.
- Treat Tier 5.9c as failed macro-eligibility recheck evidence: the v2.1
  guardrail passed, but the residual macro trace still failed trace-ablation
  specificity, so macro eligibility remains parked and must not be cited as
  promoted, hardware-ready, or native/on-chip eligibility.
- Treat Tier 4.20a as hardware-transfer readiness audit evidence only: it maps
  v2.1 mechanisms to chunked-host versus future custom-runtime/on-chip work. It
  is not a SpiNNaker hardware pass and does not prove v2.1 hardware transfer.
- Treat prepared Tier 4.20b as hardware-probe preparation only: the JobManager
  capsule at `controlled_test_output/tier4_20b_20260429_205214_prepared/`
  is ready to run a one-seed v2.1 chunked-host bridge probe, but it is not
  hardware evidence until returned `run-hardware` artifacts pass. Even a future
  4.20b pass is v2.1 bridge/transport evidence only, not proof of native
  on-chip v2.1 memory, replay, routing, self-evaluation, custom C, language,
  planning, AGI, or macro eligibility.
- Treat planned Tier 7.6 as a future capability obligation. Do not cite
  long-horizon planning or subgoal control until that tier runs, passes
  leakage-safe shams, and beats appropriate trivial/reactive baselines.

## Current Evidence Count

The study has 12 core tests plus predictive/mechanism addenda and reviewer-defense/guardrail bundles:

```text
3 sanity + 3 learning + 3 architecture + 1 baseline scaling
+ 1 hard-scaling addendum + 1 domain transfer + 1 backend parity
+ 1 hardware capsule + 1 runtime characterization + 1 hardware repeat
+ 1 external-baseline comparison + 1 learning-curve sweep
+ 1 failure-analysis diagnostic + 1 delayed-credit confirmation
+ 1 repaired delayed-cue hardware repeat + 1 repaired hard-switch hardware repeat
+ 1 v0.7 chunked hardware runtime baseline + 1 expanded baseline suite
+ 1 tuned-baseline fairness audit + 1 compact regression guardrail
+ 1 predictive task-pressure validation + 1 predictive-context sham repair
+ 1 predictive-context compact-regression gate
+ 1 software lifecycle/self-scaling benchmark + 1 lifecycle sham-control suite
+ 1 circuit-motif causality suite
= 28 tracked entries including reviewer-defense/guardrail bundles
```

The registry currently groups those into 26 canonical bundles:

- Tier 1 sanity: core tests 1-3
- Tier 2 learning proof: core tests 4-6
- Tier 3 architecture ablations: core tests 7-9
- Tier 4.10 population scaling: core test 10
- Tier 4.10b hard population scaling: addendum
- Tier 4.11 domain transfer: core test 11
- Tier 4.12 backend parity: core test 12
- Tier 4.13 SpiNNaker hardware capsule: hardware addendum
- Tier 4.14 hardware runtime characterization: post-v0.1 hardware addendum
- Tier 4.15 SpiNNaker hardware multi-seed repeat: hardware repeatability addendum
- Tier 5.1 external baselines: post-hardware software comparison
- Tier 5.2 learning curve sweep: post-v0.2 software comparison addendum
- Tier 5.3 CRA failure analysis: post-Tier-5.2 learning-dynamics diagnostic
- Tier 5.4 delayed-credit confirmation: post-Tier-5.3 candidate confirmation
- Tier 4.16a repaired delayed-cue hardware repeat: post-Tier-5.4/Tier-4.17b hardware-transfer addendum
- Tier 4.16b repaired hard-switch hardware repeat: post-Tier-4.16a hardware-transfer addendum
- Tier 4.18a v0.7 chunked runtime baseline: post-Tier-4.16b hardware-runtime addendum
- Tier 5.5 expanded baseline suite: post-Tier-4.18a software baseline/fairness gate
- Tier 5.6 baseline hyperparameter fairness audit: post-Tier-5.5 tuned-baseline reviewer-defense gate
- Tier 5.7 compact regression: post-v1.0 guardrail before lifecycle/self-scaling
- Tier 5.12a predictive task-pressure validation: post-v1.7 task-validation gate
- Tier 5.12c predictive-context sham repair: host-side visible predictive-context mechanism gate
- Tier 5.12d predictive-context compact regression: bounded v1.8 promotion gate
- Tier 6.1 lifecycle/self-scaling: post-v1.1 software organism/lifecycle benchmark
- Tier 6.3 lifecycle sham controls: post-Tier-6.1 organism/lifecycle reviewer-defense gate
- Tier 6.4 circuit motif causality: post-Tier-6.3 organism/circuit reviewer-defense gate
