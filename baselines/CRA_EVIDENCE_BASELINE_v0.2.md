# CRA Evidence Baseline v0.2

- Frozen at: `2026-04-27T03:41:03.589266+00:00`
- Source registry generated at: `2026-04-27T03:40:27.496454+00:00`
- Registry status: **PASS**
- Canonical evidence bundles: `11`
- Core tests: `12`
- Expanded tracked evidence entries: `17`
- Missing expected artifacts: `0`
- Failed canonical criteria: `0`

## Freeze Rule

This baseline is a historical evidence lock. New tiers may supersede or extend the study, but they must not rewrite what v0.2 claimed.

## Strongest Current Claim

CRA has a controlled v0.2 evidence baseline through Tier 5.1: negative controls, learning proof tasks, mechanism ablations, software scaling/domain/backend evidence, real SpiNNaker hardware capsule repeatability, runtime characterization, and an external-baseline comparison that documents both CRA edges and simpler-baseline wins.

## Claim Boundaries

- Tier 4.13 is a single-seed N=8 fixed-pattern SpiNNaker hardware capsule, not full hardware scaling.
- Tier 4.15 repeats the same minimal hardware capsule across three seeds; it is not a harder-task hardware result.
- Tier 5.1 is controlled software baseline evidence only; it documents both CRA advantages and simpler-baseline wins.
- CRA is not claimed to win every task or every metric.
- Tier 5.2 and later tiers must be added as new evidence, not retroactively blended into v0.2.

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

## Baseline Files

- `CRA_EVIDENCE_BASELINE_v0.2.json`: machine-readable baseline record
- `CRA_EVIDENCE_BASELINE_v0.2_STUDY_REGISTRY.snapshot.json`: exact registry snapshot at freeze time

## Next Evidence After Freeze

The next planned evidence entry is Tier 5.2 Learning Curve / Run-Length Sweep. It must be recorded as post-v0.2 evidence and must not change this baseline.
