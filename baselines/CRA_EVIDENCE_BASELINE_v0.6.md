# CRA Evidence Baseline v0.6

- Frozen at: `2026-04-27T18:48:54.590928+00:00`
- Source registry generated at: `2026-04-27T18:38:14.134520+00:00`
- Registry status: **PASS**
- Canonical evidence bundles: `15`
- Core tests: `12`
- Expanded tracked evidence entries: `21`
- Missing expected artifacts: `0`
- Failed canonical criteria: `0`
- Noncanonical output folders recorded by registry: `45`

## Freeze Rule

Historical evidence lock after Tier 4.16a repaired delayed-cue three-seed hardware repeat passed and before Tier 4.16b hard_noisy_switching returns.

## Strongest Current Claim

CRA has a controlled post-4.16a evidence baseline: negative controls, positive learning tests, mechanism ablations, scaling/domain/backend evidence, minimal repeatable SpiNNaker fixed-pattern hardware evidence, external-baseline comparison, learning-curve/failure-analysis/delayed-credit confirmation, chunked runtime parity, and repaired delayed-cue SpiNNaker hardware transfer across seeds 42, 43, and 44. Full Tier 4.16 remains pending hard_noisy_switching hardware.

## Claim Boundaries

- Tier 4.16a supports repaired delayed_cue hardware transfer only; it is not hard_noisy_switching transfer, hardware scaling, on-chip learning, or full Tier 4.16.
- Tier 5.4 remains controlled software confirmation and not hard-switching best-baseline superiority.
- Chunked + host is a proof-grade bridge; continuous/hybrid/on-chip learning remains future work.
- Lifecycle/self-scaling value is not yet proven and remains a make-or-break organism claim.
- Expanded baseline fairness, statistics, leakage checks, and reviewer-defense safeguards are required before a strong paper claim.

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

## Important Noncanonical Diagnostics Frozen With v0.6

| Folder | Role | Status | Why It Matters |
| --- | --- | --- | --- |
| `_tier5_4_smoke` | `probe_or_debug` | **PASS** | Retained audit/debug history. |
| `tier4_16_20260427_124916_hardware_fail` | `failed_hardware_run` | **FAIL** | Earlier harder hardware attempt completed cleanly but failed delayed_cue, prompting local metric repair. |
| `tier4_16_20260427_131914_prepared` | `prepared_capsule` | **PREPARED** | Prepared JobManager package only; not citable evidence. |
| `tier4_16_20260427_182515_chunked_seed43_hardware_pass` | `hardware_probe_pass` | **PASS** | One-seed repaired delayed_cue hardware probe that preceded the canonical three-seed repeat. |
| `tier4_16a_debug_20260427_141912` | `debug_diagnostic` | **PASS** | Local delayed_cue failure analysis showing the first failure was metric/task brittleness. |
| `tier4_16a_fix_20260427_143252` | `fix_diagnostic` | **PASS** | Local delayed_cue repair diagnostics validating longer scoring windows before hardware rerun. |
| `tier4_16a_fix_brian2_1200_20260427_145800` | `fix_diagnostic` | **PASS** | Local delayed_cue repair diagnostics validating longer scoring windows before hardware rerun. |
| `tier4_16a_fix_nest_1200_20260427_145600` | `fix_diagnostic` | **PASS** | Local delayed_cue repair diagnostics validating longer scoring windows before hardware rerun. |
| `tier4_16a_fix_nest_length_sweep_20260427_145400` | `fix_diagnostic` | **FAIL** | Local delayed_cue repair diagnostics validating longer scoring windows before hardware rerun. |
| `tier4_17_20260427_171719_runtime_scaffold` | `runtime_contract_diagnostic` | **PREPARED** | Runtime vocabulary/scaffold for step, chunked, continuous and host, hybrid, on_chip modes. |
| `tier4_17b_20260427_164625_step_chunk_parity` | `runtime_parity_diagnostic` | **PASS** | Local step-vs-chunked parity gate for scheduled input, binned readback, and host replay. |

## Baseline Files

- `CRA_EVIDENCE_BASELINE_v0.6.json`: machine-readable baseline record
- `CRA_EVIDENCE_BASELINE_v0.6_STUDY_REGISTRY.snapshot.json`: exact registry snapshot at freeze time

## Next Evidence After Freeze

- Tier 4.16b: hard_noisy_switching hardware transfer with delayed_lr_0_20, N=8, seeds 42/43/44, chunked + host, chunk_size_steps=25.
- Tier 4.18: chunked hardware runtime/resource characterization before large hardware expansions.
- Tier 5.5: expanded fair baselines with effect sizes, confidence intervals, matched task streams, and hyperparameter-budget rules.
- Tier 6.1: software lifecycle/self-scaling value benchmark.
- Tier 4.19: hardware lifecycle/self-scaling feasibility if software lifecycle passes.
