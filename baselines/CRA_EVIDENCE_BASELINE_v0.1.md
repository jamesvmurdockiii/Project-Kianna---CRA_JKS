# CRA Evidence Baseline v0.1

- Frozen at: `2026-04-27T01:27:18.250056+00:00`
- Source registry generated at: `2026-04-27T01:06:38.053654+00:00`
- Registry status: **PASS**
- Canonical evidence bundles: `8`
- Core tests: `12`
- Expanded tracked evidence entries: `14`
- Missing expected artifacts: `0`
- Failed canonical criteria: `0`

## Freeze Rule

This baseline is a historical evidence lock. New tiers may supersede or extend the study, but they must not rewrite what v0.1 claimed.

## Strongest Current Claim

CRA has a controlled v0.1 evidence baseline: negative controls, positive learning tasks, mechanism ablations, software scaling/domain/backend evidence, and a narrow Tier 4.13 minimal SpiNNaker hardware-capsule pass.

## Claim Boundaries

- Tier 4.13 is a single-seed N=8 fixed-pattern hardware capsule, not full hardware scaling.
- Tier 4.10 baseline scaling proves stability, not strong scaling advantage.
- Tier 4.10b hard scaling shows value through correlation/recovery/variance, not a large raw-accuracy jump.
- The custom C runtime remains an experimental sidecar and is not the source of current learning claims.
- Future tiers must be added as new evidence, not retroactively blended into v0.1.

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

## Baseline Files

- `CRA_EVIDENCE_BASELINE_v0.1.json`: machine-readable baseline record with checksums
- `CRA_EVIDENCE_BASELINE_v0.1_STUDY_REGISTRY.snapshot.json`: exact registry snapshot at freeze time

## Next Evidence After Freeze

The next planned evidence entry is Tier 4.14 Hardware Runtime Characterization. It must be recorded as post-v0.1 evidence and must not change this baseline.
