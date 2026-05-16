# CRA Evidence Baseline v1.6

- Frozen at: `2026-04-29T03:59:14.153907+00:00`
- Source registry generated at: `2026-04-29T03:58:06.827336+00:00`
- Registry status: **PASS**
- Canonical evidence bundles: `23`
- Core tests: `12`
- Expanded tracked evidence entries: `27`
- Missing expected artifacts: `[]`
- Failed canonical criteria: `[]`
- Noncanonical output folders recorded by registry: `93`

## Freeze Rule

Historical evidence lock after Tier 5.10g keyed/multi-slot context-memory repair passed and compact regression stayed green. v1.5 remains the pre-repair retention baseline; v1.6 records the bounded keyed-memory upgrade before sleep/replay, routing, compositionality, or hardware memory work.

## Strongest Current Claim

CRA now has post-Tier-5.10g noncanonical internal host-side keyed context-memory evidence: all v1.4/v1.5 evidence remains intact, and the internal `Organism` memory path can retain multiple visible context bindings through interference, overlap, and reentry stress while matching the oracle-key scaffold and beating the v1.5 single-slot memory, slot ablations, sign persistence, and selected standard baselines on the tested stress tasks.

## Claim Boundaries

- Tier 5.10g is noncanonical controlled software mechanism-repair evidence only; it is not a new canonical registry entry.
- The memory mechanism remains host-side software inside `Organism`, not native SpiNNaker/on-chip memory.
- The result does not prove sleep/replay consolidation, hardware transfer of memory, broad catastrophic-forgetting resolution, compositionality, module routing, or general working memory.
- The oracle-key scaffold is an upper-bound reference, not the promoted mechanism.
- Overcapacity behavior is documented but not a claim that capacity limits are solved universally.
- Future sleep/replay work still needs a stressor where consolidation or decay repair has a measured job.

## Tier 5.10g Multi-Slot / Keyed Context-Memory Summary

- Output: `<repo>/controlled_test_output/tier5_10g_20260428_232844`
- Actual/expected runs: `171` / `171`
- Backend: `nest`
- Steps: `720`
- Seeds: `42, 43, 44`
- Tasks: `intervening_contexts, overlapping_contexts, context_reentry_interference`
- Feedback leakage violations: `0` across `2166` checked feedback rows
- Candidate feature-active steps: `114.0`
- Candidate context-memory updates: `121.0`
- Compact regression after keyed-memory addition: `pass` at `<repo>/controlled_test_output/tier5_7_20260428_235507`

### Criteria

| Criterion | Value | Rule | Pass |
| --- | ---: | --- | --- |
| full variant/baseline/control/task/seed matrix completed | `171` | == `171` | yes |
| feedback timing has no leakage violations | `0` | == `0` | yes |
| candidate context feature is active | `114.0` | > `0` | yes |
| candidate memory receives context updates | `121.0` | > `0` | yes |
| candidate reaches minimum accuracy on capacity-interference tasks | `1.0` | >= `0.7` | yes |
| keyed candidate improves over v1.4 raw CRA | `0.5` | >= `0.1` | yes |
| keyed candidate improves over v1.5 single-slot memory | `0.33333333333333337` | >= `0.1` | yes |
| keyed candidate approaches oracle-key scaffold | `0.0` | >= `-0.05` | yes |
| full keyed memory is not worse than overcapacity keyed control | `0.0` | >= `0.0` | yes |
| memory ablations are worse than candidate | `0.33333333333333337` | >= `0.1` | yes |
| candidate beats sign persistence | `0.5` | >= `0.2` | yes |
| candidate is competitive with best standard baseline | `0.5` | >= `-0.05` | yes |

### Task Comparisons

| Task | Keyed all | v1.5 single-slot | Oracle key | Best ablation | Best standard | Key deltas |
| --- | ---: | ---: | ---: | --- | --- | --- |
| context_reentry_interference | `1.0` | `0.25` | `1.0` | `slot_reset_ablation` `0.5` | `online_perceptron` `0.5` | vs single-slot `0.75`, vs oracle `0.0`, vs ablation `0.5`, vs standard `0.5` |
| intervening_contexts | `1.0` | `0.6666666666666666` | `1.0` | `slot_shuffle_ablation` `0.6666666666666666` | `sign_persistence` `0.5` | vs single-slot `0.33333333333333337`, vs oracle `0.0`, vs ablation `0.33333333333333337`, vs standard `0.5` |
| overlapping_contexts | `1.0` | `0.5` | `1.0` | `slot_reset_ablation` `0.5` | `sign_persistence` `0.5` | vs single-slot `0.5`, vs oracle `0.0`, vs ablation `0.5`, vs standard `0.5` |

## Canonical Evidence Bundles

| Entry | Status | Claim | Boundary |
| --- | --- | --- | --- |
| `tier1_sanity` | `pass` | No usable signal and shuffled labels do not produce false learning. | Passing Tier 1 rules out obvious fake learning; it does not prove positive learning. |
| `tier2_learning` | `pass` | Fixed pattern, delayed reward, and nonstationary switch tasks learn above threshold. | Positive-control learning evidence depends on the controlled synthetic task definitions. |
| `tier3_architecture` | `pass` | Dopamine, plasticity, and trophic selection each contribute measurable value. | Ablation claims are scoped to the controlled tasks and seeds in this bundle. |
| `tier4_10_population_scaling` | `pass` | Fixed populations from N=4 to N=64 remain stable on the switch stressor. | This baseline scaling task saturated; the honest claim is stability, not strong scaling advantage. |
| `tier4_10b_hard_population_scaling` | `pass` | Hard scaling remains stable and shows value through correlation/recovery/variance rather than raw accuracy. | Hard-scaling accuracy is near baseline; the pass is based on stability plus non-accuracy scaling signals. |
| `tier4_11_domain_transfer` | `pass` | The same CRA core transfers from finance/signed-return to non-finance sensor_control. | Domain transfer is proven for the controlled adapters here, not arbitrary domains. |
| `tier4_12_backend_parity` | `pass` | The fixed-pattern result survives NEST to Brian2 movement with zero synthetic fallback. | The SpiNNaker item in Tier 4.12 is readiness prep, not a hardware learning result. |
| `tier4_13_spinnaker_hardware_capsule` | `pass` | The minimal fixed-pattern CRA capsule executes through pyNN.spiNNaker with real spike readback and passes learning thresholds. | Single-seed N=8 fixed-pattern capsule; not full hardware scaling or full CRA hardware deployment. |
| `tier4_14_hardware_runtime_characterization` | `pass` | The Tier 4.13 hardware pass has profiled wall-clock and sPyNNaker provenance costs; overhead is dominated by repeated per-step run/readback orchestration. | Derived from the single-seed N=8 Tier 4.13 hardware pass unless rerun in run-hardware mode; not hardware repeatability or scaling evidence. |
| `tier4_15_spinnaker_hardware_multiseed_repeat` | `pass` | The minimal fixed-pattern CRA hardware capsule repeats across seeds 42, 43, and 44 with zero fallback/failures and consistent learning metrics. | Three-seed N=8 fixed-pattern capsule only; not a harder hardware task, hardware population scaling, or full CRA hardware deployment. |
| `tier5_1_external_baselines` | `pass` | CRA is competitive against simple external learners and shows a defensible median-baseline advantage on sensor_control and hard noisy switching, while simpler online learners dominate the easy delayed-cue task. | Controlled software comparison only; not hardware evidence, not a claim that CRA wins every task, and not proof against all possible baselines. |
| `tier5_2_learning_curve_sweep` | `pass` | Across 120, 240, 480, 960, and 1500 steps, CRA's Tier 5.1 hard-task edge does not strengthen at the longest horizon: sensor_control saturates for CRA and baselines, delayed_cue remains externally dominated, and hard_noisy_switching is mixed/negative at 1500 steps. | Controlled software learning-curve characterization only; not hardware evidence, not proof that CRA cannot improve under other tasks/tuning, and not a claim that Tier 5.1 was invalid. |
| `tier5_3_cra_failure_analysis` | `pass` | A 78-run CRA-only diagnostic matrix identifies delayed-credit strength as the leading candidate failure mode: `delayed_lr_0_20` restores delayed_cue to 1.0 tail accuracy and improves hard_noisy_switching above the external median at 960 steps. | Controlled software diagnostic only; not hardware evidence, not final competitiveness evidence, and hard_noisy_switching still trails the best external baseline. |
| `tier5_4_delayed_credit_confirmation` | `pass` | The Tier 5.3 delayed-credit candidate `cra_delayed_lr_0_20` confirms across 960 and 1500 steps: delayed_cue stays at 1.0 tail accuracy, hard_noisy_switching beats the external median at both lengths, and the candidate does not regress versus current CRA. | Controlled software confirmation only; not hardware evidence and not a superiority claim because hard_noisy_switching still trails the best external baseline. |
| `tier4_16a_delayed_cue_hardware_repeat` | `pass` | The repaired delayed-credit delayed_cue regime transfers to real SpiNNaker hardware across seeds 42, 43, and 44 using chunked host replay. | Three-seed N=8 delayed_cue capsule only; not hard_noisy_switching hardware transfer, hardware scaling, on-chip learning, or a full Tier 4.16 pass. |
| `tier4_16b_hard_switch_hardware_repeat` | `pass` | The repaired hard_noisy_switching regime transfers to real SpiNNaker hardware across seeds 42, 43, and 44 using chunked host replay. | Three-seed N=8 hard_noisy_switching capsule only; close-to-threshold transfer, not hardware scaling, on-chip learning, lifecycle/self-scaling, or external-baseline superiority. |
| `tier4_18a_chunked_runtime_baseline` | `pass` | The v0.7 chunked-host SpiNNaker path remains stable on delayed_cue and hard_noisy_switching at chunk sizes 10, 25, and 50; chunk 50 is the fastest viable default for the current hardware bridge. | Single-seed N=8 runtime/resource characterization only; not hardware scaling, lifecycle/self-scaling, native on-chip dopamine/eligibility, continuous/custom-C runtime, or external-baseline superiority. |
| `tier5_5_expanded_baselines` | `pass` | The locked CRA v0.8 delayed-credit configuration completes the 1,800-run expanded baseline matrix, shows robust advantage regimes, and is not dominated on most hard/adaptive regimes while documenting where strong external baselines tie or win. | Controlled software evidence only; not hardware evidence, not a hyperparameter fairness audit, not a universal superiority claim, and not proof that CRA beats the best external baseline at every horizon. |
| `tier5_6_baseline_hyperparameter_fairness_audit` | `pass` | With CRA locked at the promoted delayed-credit setting, the 990-run Tier 5.6 audit gives external baselines a documented tuning budget and finds surviving target regimes after retuning. | Controlled software fairness audit only; not hardware evidence, not universal superiority, and not proof that CRA beats the best tuned external baseline at every metric or horizon. |
| `tier5_7_compact_regression` | `pass` | The promoted v1.0 delayed-credit setting passes compact negative controls, positive learning controls, architecture ablations, and delayed_cue/hard_noisy_switching smoke checks before lifecycle/self-scaling work. | Controlled software regression evidence only; not a new capability claim, not hardware evidence, not lifecycle/self-scaling evidence, and not external-baseline superiority. |
| `tier6_1_lifecycle_self_scaling` | `pass` | Lifecycle-enabled CRA expands from fixed initial populations with clean lineage tracking and shows hard_noisy_switching advantage regimes versus same-initial fixed-N controls. | Controlled software lifecycle evidence only; growth is cleavage-dominated with one adult birth and zero deaths, so this is not full adult turnover, not sham-control proof, not hardware lifecycle evidence, and not external-baseline superiority. |
| `tier6_3_lifecycle_sham_controls` | `pass` | Lifecycle-enabled CRA beats fixed max-pool, event-count replay, no-trophic, no-dopamine, and no-plasticity sham controls on hard_noisy_switching while preserving clean lineage integrity. | Controlled software sham-control evidence only; replay/shuffle controls are audit artifacts, not independent learners, and this is not hardware lifecycle evidence, full adult turnover, external-baseline superiority, or compositional/world-model evidence. |
| `tier6_4_circuit_motif_causality` | `pass` | Seeded motif-diverse CRA passes motif-causality controls on hard_noisy_switching: ablations cause predicted losses, motif activity is logged before reward/learning, and random/monolithic controls do not dominate across adaptation metrics. | Controlled software motif-causality evidence only; motif-diverse graph is seeded for this suite, motif-label shuffle shows labels alone are not causal, and this is not hardware motif evidence, custom-C/on-chip learning, compositionality, or full world-model evidence. |

## Files Frozen

- `baselines/CRA_EVIDENCE_BASELINE_v1.6.json`
- `baselines/CRA_EVIDENCE_BASELINE_v1.6.md`
- `baselines/CRA_EVIDENCE_BASELINE_v1.6_STUDY_REGISTRY.snapshot.json`
