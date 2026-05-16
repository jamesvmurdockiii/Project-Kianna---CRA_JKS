# Tier 4.31b Native Temporal-Substrate Local Fixed-Point Reference

- Generated: `2026-05-06T15:21:52+00:00`
- Status: **PASS**
- Criteria: `16/16`
- Outcome: `fixed_point_temporal_reference_ready_for_source_audit`

## Claim Boundary

Tier 4.31b is local fixed-point reference/parity evidence only. A pass supports C/runtime implementation work for the named seven-EMA fading-memory temporal subset. It does not prove C implementation, SpiNNaker hardware transfer, speedup, multi-chip scaling, nonlinear recurrence, universal benchmark superiority, language, planning, AGI, or ASI.

## Result

- Fixed-point candidate geomean MSE: `0.22723731574965408`
- Float fading-memory reference geomean MSE: `0.22752229502159751`
- Fixed/float ratio: `0.9987474666079806`
- Selected max abs feature error: `0.004646656591329457`
- Selected mean abs feature error: `0.0009358316819073308`
- Selected saturation count: `0`
- Conservative ±1 saturation count: `482`

## Control Margins

| Control | Geomean MSE | Margin vs candidate |
| --- | ---: | ---: |
| `lag_only_online_lms_control` | 0.8953538816902333 | 3.9401710002446917 |
| `zero_temporal_state_ablation` | 0.6231044780597117 | 2.742086949954038 |
| `frozen_temporal_state_ablation` | 0.3067393809876693 | 1.3498635995401482 |
| `shuffled_temporal_state_sham` | 1.117037773401471 | 4.915732126637618 |
| `state_reset_interval_control` | 0.7072120040504856 | 3.112217734650662 |
| `shuffled_target_control` | 1.1682194145541391 | 5.1409664416259835 |
| `no_plasticity_ablation` | 2.18419686652511 | 9.611963859542444 |

## Per-Task Metrics

| Task | Candidate MSE | Float reference MSE | Lag margin | Frozen margin | Shuffled margin |
| --- | ---: | ---: | ---: | ---: | ---: |
| heldout_long_memory | 0.36334528665902993 | 0.3653083872204199 | 3.4980717090075877 | 1.6126508432057798 | 4.68153676131888 |
| slow_context_drift | 0.07463301631793513 | 0.074533942806697 | 5.6118293671981485 | 1.7665657750317565 | 10.136009880021621 |
| multiscale_echo | 0.4327015257263749 | 0.4325717367470247 | 3.116104727873895 | 0.8633750588854407 | 2.5032784649607205 |

## Range Refinement

Tier 4.31a used a conservative initial trace clip in the equation sketch. Tier 4.31b documents that a ±2 trace bound preserves the compact state budget while removing saturation on the canonical temporal diagnostics. This is a local-reference refinement before C implementation, not a hardware claim.

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_31b_native_temporal_fixed_point_reference_20260506_0001` | expected current source | yes |
| Tier 4.31a readiness exists | `<repo>/controlled_test_output/tier4_31a_20260506_native_temporal_substrate_readiness/tier4_31a_results.json` | exists | yes |
| Tier 4.31a readiness passed | `pass` | == pass | yes |
| Tier 5.19c reference exists | `<repo>/controlled_test_output/tier5_19c_20260505_fading_memory_regression/tier5_19c_results.json` | exists | yes |
| Tier 5.19c reference passed | `pass` | == pass | yes |
| all temporal-memory tasks included | `["heldout_long_memory", "multiscale_echo", "slow_context_drift"]` | subset of tasks | yes |
| all model rows completed | `81/81` | all pass | yes |
| trace count matches 4.31a | `2,4,8,16,32,64,128` | 7 timescales | yes |
| fixed-point parity passes | `True` | fixed/float geomean ratio within [0.90, 1.10] | yes |
| trace error bound passes | `True` | max<=0.01 mean<=0.003 saturation=0 | yes |
| range refinement supported | `True` | conservative saturates and selected does not | yes |
| control suite passes | `True` | all destructive controls separate | yes |
| lag-only remains weaker | `3.9401710002446917` | >= 1.25 | yes |
| hidden recurrence remains excluded | `fading_only fixed-point EMA` | no hidden/recurrent features | yes |
| no EBRAINS package prepared | `local-reference only` | no ebrains_jobs output | yes |
| next step remains source/local before hardware | `Tier 4.31c source/runtime implementation + local C host tests` | not hardware upload yet | yes |

## Nonclaims

- not C runtime implementation
- not SpiNNaker hardware evidence
- not speedup evidence
- not multi-chip scaling
- not nonlinear recurrence
- not universal benchmark superiority
- not language, planning, AGI, or ASI
