# Tier 4.31a Native Temporal-Substrate Readiness

- Generated: `2026-05-06T04:17:00+00:00`
- Status: **PASS**
- Criteria: `24/24`
- Output directory: `<repo>/controlled_test_output/tier4_31a_20260506_native_temporal_substrate_readiness`

## Claim Boundary

Tier 4.31a is local readiness/contract evidence only. A pass defines the smallest native fading-memory temporal-state subset, fixed-point equations, controls, readback schema, resource budget, command plan, and failure classes before any implementation or EBRAINS package. It does not prove C runtime implementation, SpiNNaker hardware transfer, speedup, multi-chip scaling, nonlinear recurrence, universal benchmark superiority, language, planning, AGI, or ASI.

## Decision

- Decision: `migrate_fading_memory_ema_traces_first`
- State subset: seven causal EMA traces over the current temporal input; deltas and novelty are derived, not stored
- Timescales: `[2, 4, 8, 16, 32, 64, 128]`
- Timescale checksum: `1811900589`
- Persistent state bytes: `56`
- Total initial temporal bytes: `112`

The first native migration is **not** a hidden recurrent substrate. It is the v2.2-promoted causal EMA trace bank with derived deltas and novelty.

## Fixed-Point Trace Table

| tau | decay raw | alpha raw |
| ---: | ---: | ---: |
| 2 | 19874 | 12893 |
| 4 | 25519 | 7248 |
| 8 | 28917 | 3850 |
| 16 | 30782 | 1985 |
| 32 | 31759 | 1008 |
| 64 | 32259 | 508 |
| 128 | 32512 | 255 |

## Controls Required Before Hardware

- `lag_only_online_lms_control`: Preserve the Tier 5.19c requirement that fading memory beat a same-causal-budget lag control on temporal-memory diagnostics.
- `zero_temporal_state_ablation`: Proves task performance is not carried solely by current input/readout.
- `frozen_temporal_state_ablation`: Matches the v2.2 sham where temporal state stops updating after the train/reference prefix.
- `shuffled_temporal_state_sham`: Destroys temporal ordering while preserving marginal state distribution.
- `state_reset_interval_control`: Checks whether the claimed memory horizon survives forced resets.
- `shuffled_target_control`: Detects label/target leakage through the temporal path.
- `no_plasticity_ablation`: Separates temporal state availability from learning/readout adaptation.
- `hidden_recurrence_excluded_control`: Keeps Tier 4.31 aligned with the narrowed v2.2 claim.

## Proposed Command Plan

- Proposed codes: `{'CMD_TEMPORAL_INIT': 39, 'CMD_TEMPORAL_UPDATE': 40, 'CMD_TEMPORAL_READ_STATE': 41, 'CMD_TEMPORAL_SHAM_MODE': 42}`
- Collisions: `{}`
- Implementation rule: do not add commands until 4.31b local fixed-point reference passes

## Next Step

- Tier 4.31b - Native Temporal-Substrate Local Fixed-Point Reference

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_31a_native_temporal_substrate_readiness_20260506_0001` | expected current source | yes |
| v2.2 baseline exists | `<repo>/baselines/CRA_EVIDENCE_BASELINE_v2.2.json` | exists | yes |
| v2.2 baseline frozen | `frozen` | == frozen | yes |
| Tier 5.19c result exists | `<repo>/controlled_test_output/tier5_19c_20260505_fading_memory_regression/tier5_19c_results.json` | exists | yes |
| Tier 5.19c passed | `pass` | == pass | yes |
| Tier 5.19c freeze authorized | `True` | == true | yes |
| nonlinear recurrence excluded | `["not bounded nonlinear recurrence", "not hardware evidence", "not native on-chip temporal dynamics", "not universal benchmark superiority", "not language, planning, AGI, or ASI"]` | contains not bounded nonlinear recurrence | yes |
| lifecycle native baseline exists | `<repo>/baselines/CRA_LIFECYCLE_NATIVE_BASELINE_v0.4.md` | exists | yes |
| Tier 4.30g hardware pass exists | `<repo>/controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/tier4_30g_hw_results.json` | exists | yes |
| Tier 4.30g hardware status passed | `pass` | == pass | yes |
| runtime fixed-point helpers present | `FP_MUL FP_FROM_FLOAT` | present in config.h | yes |
| runtime bounded state constants present | `MAX_MEMORY_SLOTS/MAX_PENDING_HORIZONS` | present | yes |
| existing lifecycle/native summary surface present | `cra_state_summary_t` | present | yes |
| smallest temporal subset declared | `seven causal EMA traces over the current temporal input; deltas and novelty are derived, not stored` | EMA traces only | yes |
| fixed-point table complete | `7` | == 7 | yes |
| persistent temporal state budget compact | `56` | <= 128 bytes | yes |
| total initial temporal budget compact | `112` | <= 256 bytes | yes |
| readback schema declared | `12` | >= 10 fields | yes |
| control suite declared | `8` | >= 7 controls | yes |
| required controls include lag/frozen/shuffled/reset/no-plasticity | `["lag_only_online_lms_control", "zero_temporal_state_ablation", "frozen_temporal_state_ablation", "shuffled_temporal_state_sham", "state_reset_interval_control", "shuffled_target_control", "no_plasticity_ablation", "hidden_recurrence_excluded_control"]` | contains core controls | yes |
| failure classes declared | `9` | >= 8 classes | yes |
| proposed command codes do not collide | `{}` | empty | yes |
| no EBRAINS package prepared | `local-readiness only` | no ebrains_jobs output | yes |
| next step remains local | `Tier 4.31b local fixed-point reference/parity; no EBRAINS package before that passes` | Tier 4.31b local before hardware | yes |
