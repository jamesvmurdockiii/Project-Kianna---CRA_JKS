# CRA Native Scale Baseline v0.5

- Frozen at: `2026-05-08T17:35:32+00:00`
- Runner revision: `tier4_32h_native_scale_evidence_closeout_20260508_0001`
- Registry status at freeze time: `pass`
- Registry evidence count at freeze time: `81`
- Supersedes: `CRA_LIFECYCLE_NATIVE_BASELINE_v0.4` for native scale/substrate evidence only

## Freeze Rule

Freeze only because Tier 4.32a replicated single-chip stress, Tier 4.32d two-chip communication, Tier 4.32e two-chip learning micro-task, and Tier 4.32g two-chip lifecycle traffic/resource evidence all passed after ingest. This freezes the native-scale substrate boundary, not usefulness.

## Strongest Current Claim

CRA has a bounded native-scale SpiNNaker substrate baseline: replicated single-chip MCPL stress, two-chip MCPL communication/readback, a two-chip learning-bearing micro-task, and two-chip lifecycle traffic/resource counters have all passed canonical evidence gates with preserved returned artifacts, zero synthetic fallback, and explicit claim boundaries.

## Claim Boundaries

- Native-scale substrate baseline only; not a software capability baseline.
- Not speedup evidence; wall-clock efficiency remains separately measurable.
- Not benchmark or real-task usefulness evidence.
- Not true two-partition learning or multi-shard learning.
- Not lifecycle scaling or autonomous organism ecology.
- Not proof that every v2.2 software mechanism is fully chip-native.
- Not language, planning, AGI, or ASI evidence.
- Hardware/native work should pause here except for targeted transfer of mechanisms that win software usefulness gates.

## Frozen Native-Scale Evidence

| Entry | Status | Audit Criteria | Returned Artifacts | Claim | Boundary |
| --- | --- | ---: | ---: | --- | --- |
| `tier4_32a_hw_replicated_shard_stress` | `pass` | 16/16 | 80 | Single-chip replicated-shard MCPL stress passed at 8/12/16-core stress points with returned artifacts preserved. | Single-chip replicated-shard stress only; not multi-chip or speedup evidence. |
| `tier4_32d_two_chip_mcpl_lookup_hardware_smoke` | `pass` | 12/12 | 40 | Two-chip MCPL lookup communication/readback passed with zero stale replies, duplicate replies, timeouts, or synthetic fallback. | Two-chip communication/readback smoke only; not learning scale or speedup evidence. |
| `tier4_32e_multi_chip_learning_microtask` | `pass` | 14/14 | 42 | Two-chip single-shard learning-bearing micro-task passed with the enabled-learning case separated from the no-learning control. | Two-chip learning micro-task only; not true two-partition or benchmark evidence. |
| `tier4_32g_two_chip_lifecycle_traffic_resource_smoke` | `pass` | 14/14 | 30 | Two-chip lifecycle traffic/resource smoke passed with source event/trophic requests, remote lifecycle mutation, mask sync, and zero stale/duplicate/missing-ack counters. | Two-chip lifecycle traffic/resource smoke only; not lifecycle scaling evidence. |

## Next Steps

- Stop broad native migration after v0.5 freeze.
- Run Tier 6.2 hard synthetic usefulness suite in software with strong baselines.
- Run Tier 7.1 real-ish adapter suite, Tier 7.2 held-out task challenge, and Tier 7.3 real-data tasks before more broad porting.
- Only port winning tasks/mechanisms back to SpiNNaker/native C after they show bounded usefulness against fair baselines.
- If native v0.5 evidence is later contradicted, return to the failing 4.32 tier before citing v0.5.

## Re-entry Condition

If future native multi-chip, lifecycle-scaling, benchmark, or real-task work invalidates any included Tier 4.32 evidence boundary, return to the failing 4.32 tier and rerun its local/source/hardware/ingest gate before citing v0.5.
