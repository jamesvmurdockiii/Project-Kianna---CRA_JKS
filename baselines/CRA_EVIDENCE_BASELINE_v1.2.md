# CRA Evidence Baseline v1.2

- Frozen at: `2026-04-28T06:14:03.686697+00:00`
- Source registry generated at: `2026-04-28T06:12:26.818822+00:00`
- Registry status: **PASS**
- Canonical evidence bundles: `21`
- Core tests: `12`
- Expanded tracked evidence entries: `25`
- Missing expected artifacts: `0`
- Failed canonical criteria: `0`
- Noncanonical output folders recorded by registry: `58`

## Freeze Rule

Historical evidence lock after Tier 6.1 software lifecycle/self-scaling passed and before Tier 6.3 lifecycle sham-control experiments.

## Strongest Current Claim

CRA has controlled post-Tier-6.1 evidence: all v1.1 evidence plus software lifecycle expansion/self-scaling with clean lineage tracking and hard_noisy_switching advantage regimes versus same-initial fixed-N controls. The organism claim is now partially supported in software, but Tier 6.1 was cleavage-dominated with one adult birth and zero deaths; full adult turnover, sham-control robustness, hardware lifecycle, and external-baseline superiority remain future claims.

## Claim Boundaries

- Tier 6.1 is controlled software lifecycle/self-scaling evidence only; it is not hardware evidence.
- Lifecycle cases produced 75 new-polyp events with clean lineage integrity and no aggregate extinction.
- Event-type analysis shows 74 cleavage events, 1 adult birth event, and 0 death events, so Tier 6.1 should be cited as lifecycle expansion/self-scaling, not full adult birth/death turnover.
- The Tier 6.1 advantage appears on hard_noisy_switching for life4_16 and life8_32 versus same-initial fixed controls; delayed_cue saturated and life16_64 did not meet the advantage gate.
- Tier 6.3 sham controls are required before a stronger organism/ecology mechanism claim.
- Tier 6.1 does not prove external-baseline superiority, hardware lifecycle, native on-chip lifecycle, compositionality, world modeling, or real-world usefulness.

## Tier 6.1 Event-Type Summary

- New-polyp events total: `75`
- Cleavage events: `74`
- Adult birth events: `1`
- Death events: `0`

## Canonical Evidence Bundles

| Entry | Status | Claim | Boundary |
| --- | --- | --- | --- |
| `tier1_sanity` | **PASS** | No usable signal and shuffled labels do not produce false learning. | Passing Tier 1 rules out obvious fake learning; it does not prove positive learning. |
| `tier2_learning` | **PASS** | Fixed pattern, delayed reward, and nonstationary switch tasks learn above threshold. | Positive-control learning evidence depends on the controlled synthetic task definitions. |
| `tier3_architecture` | **PASS** | Dopamine, plasticity, and trophic selection each contribute measurable value. | Ablation claims are scoped to the controlled tasks and seeds in this bundle. |
| `tier4_10_population_scaling` | **PASS** | Fixed populations from N=4 to N=64 remain stable on the switch stressor. | This baseline scaling task saturated; the honest claim is stability, not strong scaling advantage. |
| `tier4_10b_hard_population_scaling` | **PASS** | Hard scaling remains stable and shows value through correlation/recovery/variance rather than raw accuracy. | Hard-scaling accuracy is near baseline; the pass is based on stability plus non-accuracy scaling signals. |
| `tier4_11_domain_transfer` | **PASS** | The same CRA core transfers from finance/signed-return to non-finance sensor_control. | Domain transfer is proven for the controlled adapters here, not arbitrary domains. |
| `tier4_12_backend_parity` | **PASS** | The fixed-pattern result survives NEST to Brian2 movement with zero synthetic fallback. | The SpiNNaker item in Tier 4.12 is readiness prep, not a hardware learning result. |
| `tier4_13_spinnaker_hardware_capsule` | **PASS** | The minimal fixed-pattern CRA capsule executes through pyNN.spiNNaker with real spike readback and passes learning thresholds. | Single-seed N=8 fixed-pattern capsule; not full hardware scaling or full CRA hardware deployment. |
| `tier4_14_hardware_runtime_characterization` | **PASS** | The Tier 4.13 hardware pass has profiled wall-clock and sPyNNaker provenance costs; overhead is dominated by repeated per-step run/readback orchestration. | Derived from the single-seed N=8 Tier 4.13 hardware pass unless rerun in run-hardware mode; not hardware repeatability or scaling evidence. |
| `tier4_15_spinnaker_hardware_multiseed_repeat` | **PASS** | The minimal fixed-pattern CRA hardware capsule repeats across seeds 42, 43, and 44 with zero fallback/failures and consistent learning metrics. | Three-seed N=8 fixed-pattern capsule only; not a harder hardware task, hardware population scaling, or full CRA hardware deployment. |
| `tier5_1_external_baselines` | **PASS** | CRA is competitive against simple external learners and shows a defensible median-baseline advantage on sensor_control and hard noisy switching, while simpler online learners dominate the easy delayed-cue task. | Controlled software comparison only; not hardware evidence, not a claim that CRA wins every task, and not proof against all possible baselines. |
| `tier5_2_learning_curve_sweep` | **PASS** | Across 120, 240, 480, 960, and 1500 steps, CRA's Tier 5.1 hard-task edge does not strengthen at the longest horizon: sensor_control saturates for CRA and baselines, delayed_cue remains externally dominated, and hard_noisy_switching is mixed/negative at 1500 steps. | Controlled software learning-curve characterization only; not hardware evidence, not proof that CRA cannot improve under other tasks/tuning, and not a claim that Tier 5.1 was invalid. |
| `tier5_3_cra_failure_analysis` | **PASS** | A 78-run CRA-only diagnostic matrix identifies delayed-credit strength as the leading candidate failure mode: `delayed_lr_0_20` restores delayed_cue to 1.0 tail accuracy and improves hard_noisy_switching above the external median at 960 steps. | Controlled software diagnostic only; not hardware evidence, not final competitiveness evidence, and hard_noisy_switching still trails the best external baseline. |
| `tier5_4_delayed_credit_confirmation` | **PASS** | The Tier 5.3 delayed-credit candidate `cra_delayed_lr_0_20` confirms across 960 and 1500 steps: delayed_cue stays at 1.0 tail accuracy, hard_noisy_switching beats the external median at both lengths, and the candidate does not regress versus current CRA. | Controlled software confirmation only; not hardware evidence and not a superiority claim because hard_noisy_switching still trails the best external baseline. |
| `tier4_16a_delayed_cue_hardware_repeat` | **PASS** | The repaired delayed-credit delayed_cue regime transfers to real SpiNNaker hardware across seeds 42, 43, and 44 using chunked host replay. | Three-seed N=8 delayed_cue capsule only; not hard_noisy_switching hardware transfer, hardware scaling, on-chip learning, or a full Tier 4.16 pass. |
| `tier4_16b_hard_switch_hardware_repeat` | **PASS** | The repaired hard_noisy_switching regime transfers to real SpiNNaker hardware across seeds 42, 43, and 44 using chunked host replay. | Three-seed N=8 hard_noisy_switching capsule only; close-to-threshold transfer, not hardware scaling, on-chip learning, lifecycle/self-scaling, or external-baseline superiority. |
| `tier4_18a_chunked_runtime_baseline` | **PASS** | The v0.7 chunked-host SpiNNaker path remains stable on delayed_cue and hard_noisy_switching at chunk sizes 10, 25, and 50; chunk 50 is the fastest viable default for the current hardware bridge. | Single-seed N=8 runtime/resource characterization only; not hardware scaling, lifecycle/self-scaling, native on-chip dopamine/eligibility, continuous/custom-C runtime, or external-baseline superiority. |
| `tier5_5_expanded_baselines` | **PASS** | The locked CRA v0.8 delayed-credit configuration completes the 1,800-run expanded baseline matrix, shows robust advantage regimes, and is not dominated on most hard/adaptive regimes while documenting where strong external baselines tie or win. | Controlled software evidence only; not hardware evidence, not a hyperparameter fairness audit, not a universal superiority claim, and not proof that CRA beats the best external baseline at every horizon. |
| `tier5_6_baseline_hyperparameter_fairness_audit` | **PASS** | With CRA locked at the promoted delayed-credit setting, the 990-run Tier 5.6 audit gives external baselines a documented tuning budget and finds surviving target regimes after retuning. | Controlled software fairness audit only; not hardware evidence, not universal superiority, and not proof that CRA beats the best tuned external baseline at every metric or horizon. |
| `tier5_7_compact_regression` | **PASS** | The promoted v1.0 delayed-credit setting passes compact negative controls, positive learning controls, architecture ablations, and delayed_cue/hard_noisy_switching smoke checks before lifecycle/self-scaling work. | Controlled software regression evidence only; not a new capability claim, not hardware evidence, not lifecycle/self-scaling evidence, and not external-baseline superiority. |
| `tier6_1_lifecycle_self_scaling` | **PASS** | Lifecycle-enabled CRA expands from fixed initial populations with clean lineage tracking and shows hard_noisy_switching advantage regimes versus same-initial fixed-N controls. | Controlled software lifecycle evidence only; growth is cleavage-dominated with one adult birth and zero deaths, so this is not full adult turnover, not sham-control proof, not hardware lifecycle evidence, and not external-baseline superiority. |

## Important Noncanonical Diagnostics Frozen With v1.2

These folders are retained for audit/debug history. They are not promoted canonical evidence unless explicitly listed above.

| Folder | Role | Status |
| --- | --- | --- |
| `_legacy_artifacts` | `legacy_generated_artifacts` | **UNKNOWN** |
| `_phase3_probe_ecology` | `probe_or_debug` | **FAIL** |
| `_phase3_probe_noecology` | `probe_or_debug` | **FAIL** |
| `_tier5_1_smoke` | `probe_or_debug` | **PASS** |
| `_tier5_2_smoke` | `probe_or_debug` | **PASS** |
| `_tier5_3_smoke` | `probe_or_debug` | **PASS** |
| `_tier5_4_smoke` | `probe_or_debug` | **PASS** |
| `tier1_20260426_150252` | `superseded_rerun` | **PASS** |
| `tier1_20260426_150944` | `superseded_rerun` | **PASS** |
| `tier1_20260426_152035` | `superseded_rerun` | **PASS** |
| `tier1_20260426_153453` | `superseded_rerun` | **PASS** |
| `tier1_20260426_153802` | `superseded_rerun` | **PASS** |
| `tier2_20260426_151539` | `superseded_rerun` | **UNKNOWN** |
| `tier2_20260426_151558` | `superseded_rerun` | **FAIL** |
| `tier2_20260426_151659` | `superseded_rerun` | **FAIL** |
| `tier2_20260426_151740` | `superseded_rerun` | **FAIL** |
| `tier2_20260426_151847` | `superseded_rerun` | **FAIL** |
| `tier2_20260426_151923` | `superseded_rerun` | **FAIL** |
| `tier2_20260426_152011` | `superseded_rerun` | **PASS** |
| `tier2_20260426_152616` | `superseded_rerun` | **PASS** |
| `tier2_20260426_153522` | `superseded_rerun` | **FAIL** |
| `tier2_20260426_153749` | `superseded_rerun` | **PASS** |
| `tier2_20260426_153824` | `superseded_rerun` | **PASS** |
| `tier3_20260426_153145` | `superseded_rerun` | **PASS** |
| `tier3_20260426_153850` | `superseded_rerun` | **FAIL** |
| `tier3_20260426_154155` | `superseded_rerun` | **PASS** |
| `tier4_13_20260426_181357` | `superseded_rerun` | **PREPARED** |
| `tier4_13_20260426_192413` | `superseded_rerun` | **PREPARED** |
| `tier4_13_20260426_192455` | `superseded_rerun` | **PREPARED** |
| `tier4_13_20260426_195400` | `superseded_rerun` | **PREPARED** |
| `tier4_13_20260426_195507` | `superseded_rerun` | **PREPARED** |
| `tier4_13_20260426_201136` | `superseded_rerun` | **PREPARED** |
| `tier4_13_20260426_201430` | `superseded_rerun` | **PREPARED** |
| `tier4_13_20260426_201508` | `superseded_rerun` | **PREPARED** |
| `tier4_15_20260426_215658` | `superseded_rerun` | **PREPARED** |
| `tier4_16_20260427_124916_hardware_fail` | `failed_hardware_run` | **FAIL** |
| `tier4_16_20260427_131914_prepared` | `prepared_capsule` | **PREPARED** |
| `tier4_16_20260427_182515_chunked_seed43_hardware_pass` | `hardware_probe_pass` | **PASS** |
| `tier4_16_20260427_194526_hard_noisy_switching_3seed_hardware_fail` | `failed_hardware_run` | **FAIL** |
| `tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass` | `hardware_probe_pass` | **PASS** |
| `tier4_16a_debug_20260427_141912` | `debug_diagnostic` | **PASS** |
| `tier4_16a_fix_20260427_143252` | `fix_diagnostic` | **PASS** |
| `tier4_16a_fix_brian2_1200_20260427_145800` | `fix_diagnostic` | **PASS** |
| `tier4_16a_fix_nest_1200_20260427_145600` | `fix_diagnostic` | **PASS** |
| `tier4_16a_fix_nest_length_sweep_20260427_145400` | `fix_diagnostic` | **FAIL** |
| `tier4_16b_bridge_repair_orderfix_aligned_brian2_20260427` | `fix_diagnostic` | **PASS** |
| `tier4_16b_bridge_repair_orderfix_aligned_nest_20260427` | `fix_diagnostic` | **PASS** |
| `tier4_16b_debug_20260427_200931_hard_switch` | `debug_diagnostic` | **PASS** |
| `tier4_16b_debug_20260427_200931_hard_switch_corrected` | `debug_diagnostic` | **PASS** |
| `tier4_17_20260427_171719_runtime_scaffold` | `runtime_contract_diagnostic` | **PREPARED** |
| `tier4_17b_20260427_164625_step_chunk_parity` | `runtime_parity_diagnostic` | **PASS** |
| `tier4_18a_20260427_203220_prepared` | `prepared_capsule` | **PREPARED** |
| `tier5_5_20260427_222527` | `superseded_rerun` | **PASS** |
| `tier5_6_20260428_001803` | `superseded_rerun` | **PASS** |
| `tier5_7_20260428_005610` | `superseded_rerun` | **FAIL** |
| `tier5_7_20260428_005646` | `superseded_rerun` | **PASS** |
| `tier6_1_20260428_012026` | `superseded_rerun` | **PASS** |
| `tier6_1_20260428_012059` | `superseded_rerun` | **PASS** |

## Baseline Files

- `CRA_EVIDENCE_BASELINE_v1.2.json`: machine-readable baseline record
- `CRA_EVIDENCE_BASELINE_v1.2_STUDY_REGISTRY.snapshot.json`: exact registry snapshot at freeze time

## Next Evidence After Freeze

- Tier 6.3 lifecycle sham controls to prove the observed lifecycle advantage is not random expansion, active-mask leakage, or capacity artifact.
- Tier 6.4 circuit motif causality to ablate lateral inhibition, recurrence/feedback, feedforward hierarchy, mutual inhibition/WTA, and related motifs where implemented.
- Adult-turnover stressor if the paper needs explicit adult birth/death replacement rather than cleavage-dominated expansion.
- Tier 4.19 hardware lifecycle/self-scaling feasibility only after software lifecycle value survives sham controls.
- Tier 5.9-5.17 mechanisms one at a time when measured blockers justify them, each with ablations, compact regression, and baseline comparisons before promotion.
- Tier 7 real-ish tasks, policy/action selection, curriculum generation, and holdout tasks before paper-lock claims.
