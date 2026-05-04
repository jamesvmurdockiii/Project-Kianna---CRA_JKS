# CRA Evidence Baseline v0.5

- Frozen at: `2026-04-27T16:18:45.173136+00:00`
- Source registry generated at: `2026-04-27T15:15:20.938586+00:00`
- Registry status: **PASS**
- Canonical evidence bundles: `14`
- Core tests: `12`
- Expanded tracked evidence entries: `20`
- Missing expected artifacts: `0`
- Failed canonical criteria: `0`
- Noncanonical output folders recorded by registry: `42`

## Freeze Rule

This baseline is a historical evidence lock immediately before the Tier 4.17 batched/chunked runtime refactor. New runtime work may supersede or extend the study, but it must not rewrite what v0.5 claimed.

## Strongest Current Claim

CRA has a controlled v0.5 pre-batched-runtime evidence baseline through Tier 5.4 plus noncanonical Tier 4.16 diagnostics: negative controls, positive learning tests, mechanism ablations, scaling/domain/backend evidence, minimal repeatable SpiNNaker hardware capsule evidence, external-baseline comparison, learning-curve characterization, CRA failure-analysis diagnostics, delayed-credit confirmation, and a documented failed harder-hardware attempt whose delayed-cue failure reproduced locally and was repaired locally by increasing the scoring window to 1200+ steps.

## Claim Boundaries

- Tier 4.13 and Tier 4.15 remain minimal fixed-pattern SpiNNaker hardware capsule evidence, not full hardware scaling or full CRA hardware deployment.
- Tier 5.4 remains controlled software confirmation only; it does not make a hardware claim and does not claim hard-switch superiority over the best external baseline.
- Tier 4.16 hardware did not pass: it completed the harder hardware execution path cleanly with real spikes and zero fallback/failures, but failed the delayed_cue learning criterion.
- Tier 4.16a debug showed the delayed_cue failure reproduces in NEST and Brian2, so the first diagnosis is metric/task brittleness rather than SpiNNaker breakage.
- Tier 4.16a fix showed delayed_cue passes locally at 1200 steps in NEST and Brian2 and at 1500 steps with more tail events; these are noncanonical repair diagnostics, not hardware evidence.
- The next evidence must be Tier 4.17 batched/chunked runtime scaffolding and then a repaired one-seed hardware probe; do not rerun slow per-step full Tier 4.16 as the default path.

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

## Noncanonical Diagnostics Frozen With v0.5

| Folder | Role | Status | Why It Matters |
| --- | --- | --- | --- |
| `tier4_16_20260427_074216_prepared` | `prepared_capsule` | **PREPARED** | Prepared JobManager package only; not hardware evidence. |
| `tier4_16_20260427_124916_hardware_fail` | `failed_hardware_run` | **FAIL** | Harder hardware path ran cleanly but failed delayed_cue learning threshold. |
| `tier4_16a_debug_20260427_141912` | `debug_diagnostic` | **PASS** | Local debug reproduced delayed_cue failures in NEST and Brian2. |
| `tier4_16a_fix_20260427_143252` | `fix_diagnostic` | **PASS** | Local 1500-step repair passed with a larger delayed-cue scoring window. |
| `tier4_16a_fix_brian2_1200_20260427_145800` | `fix_diagnostic` | **PASS** | Brian2 1200-step local repair passed; useful before hardware probe. |
| `tier4_16a_fix_nest_1200_20260427_145600` | `fix_diagnostic` | **PASS** | NEST 1200-step local repair passed; useful before hardware probe. |
| `tier4_16a_fix_nest_length_sweep_20260427_145400` | `fix_diagnostic` | **FAIL** | Shorter local windows remained brittle and failed the stricter repair criteria. |

## Baseline Files

- `CRA_EVIDENCE_BASELINE_v0.5.json`: machine-readable baseline record
- `CRA_EVIDENCE_BASELINE_v0.5_STUDY_REGISTRY.snapshot.json`: exact registry snapshot at freeze time

## Next Evidence After Freeze

- Tier 4.17a: implement runtime_mode step|chunked|continuous and learning_location host|hybrid|on_chip scaffolding; only chunked+host is implemented first.
- Tier 4.17b: run 120-step old step-mode versus chunked-mode parity before hardware promotion.
- Tier 4.16a-repaired: run delayed_cue seed 43 at 1200 steps using chunked hardware mode after parity passes.
- Tier 4.16a-repaired-full: repeat seeds 42, 43, 44 only after the one-seed probe passes.
