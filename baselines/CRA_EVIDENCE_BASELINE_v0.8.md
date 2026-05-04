# CRA Evidence Baseline v0.8

- Frozen at: `2026-04-28T01:43:34.747278+00:00`
- Source registry generated at: `2026-04-28T01:39:00.733919+00:00`
- Registry status: **PASS**
- Canonical evidence bundles: `17`
- Core tests: `12`
- Expanded tracked evidence entries: `23`
- Missing expected artifacts: `0`
- Failed canonical criteria: `0`
- Noncanonical output folders recorded by registry: `52`

## Freeze Rule

Historical evidence lock after Tier 4.18a v0.7 chunked hardware runtime baseline passed and before Tier 5.5 expanded baseline/fairness work.

## Strongest Current Claim

CRA has a controlled post-4.18a evidence baseline: negative controls, positive learning tests, mechanism ablations, software scaling/domain/backend evidence, minimal repeatable SpiNNaker fixed-pattern hardware evidence, external-baseline comparison, learning-curve/failure-analysis/delayed-credit confirmation, repaired delayed-cue and hard-switch SpiNNaker transfer across seeds 42/43/44, and v0.7 chunked-host hardware runtime characterization showing chunk 50 is the fastest viable current bridge setting on seed 42 without observed metric degradation.

## Claim Boundaries

- Tier 4.18a supports v0.7 chunked-host runtime/resource characterization only; it is not hardware scaling or on-chip learning.
- Use chunk_size_steps=50 as the current hardware default unless a future task-specific parity check shows degradation.
- Tier 4.16a and 4.16b remain narrow N=8 hardware-transfer results, not full hardware deployment or external-baseline superiority.
- raw_dopamine is expected to be zero in chunked host delayed-credit traces; cite matured horizon replay/host replay evidence, not native on-chip dopamine.
- Lifecycle/self-scaling value, compositional reuse, predictive/world-model behavior, working memory, and native eligibility remain future claims.
- Expanded baseline fairness, statistics, leakage checks, mechanism controls, and reviewer-defense safeguards are required before a strong paper claim.

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

## Important Noncanonical Diagnostics Frozen With v0.8

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

## Baseline Files

- `CRA_EVIDENCE_BASELINE_v0.8.json`: machine-readable baseline record
- `CRA_EVIDENCE_BASELINE_v0.8_STUDY_REGISTRY.snapshot.json`: exact registry snapshot at freeze time

## Next Evidence After Freeze

- Tier 5.5 expanded fair baselines with stronger/tuned models, effect sizes, confidence intervals, and sample-efficiency metrics.
- Tier 5.6 baseline hyperparameter fairness audit and Tier 5.7 compact regression after promoted tuning.
- Tier 6.1 software lifecycle/self-scaling benchmark plus Tier 6.3 sham controls and Tier 6.4 circuit motif causality.
- Tier 4.19 hardware lifecycle/self-scaling feasibility only after software lifecycle value is proven.
- Tier 5.9-5.17 architecture mechanisms one at a time when measured blockers justify them.
- Tier 4.20-4.22 hybrid/on-chip/custom runtime migration after chunked-host limits are characterized.
