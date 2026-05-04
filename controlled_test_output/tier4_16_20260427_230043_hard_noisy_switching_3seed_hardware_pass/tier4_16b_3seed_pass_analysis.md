# Tier 4.16b Repaired Hard-Switch Three-Seed Hardware Pass Analysis

- Source result generated UTC: `2026-04-27T23:00:43+00:00`
- Ingested bundle: `controlled_test_output/tier4_16_20260427_230043_hard_noisy_switching_3seed_hardware_pass/`
- Status: **PASS**
- Claim boundary: repaired hard-switch hardware transfer across seeds `42`, `43`, and `44`; not hardware scaling, not on-chip learning, and not a superiority claim over external baselines.

## What Passed

The repaired `hard_noisy_switching` capsule ran on real `pyNN.spiNNaker` with:

- task: `hard_noisy_switching`
- seeds: `42`, `43`, `44`
- steps per seed: `1200`
- population: `N=8`
- runtime mode: `chunked`
- learning location: `host`
- chunk size: `25` steps
- hardware `sim.run` calls per seed: `48`
- synthetic fallbacks: `0`
- `sim.run` failures: `0`
- summary/readback failures: `0`
- minimum real spike readback: `94707` spikes
- mean real spike readback: `94812.7` spikes
- mean runtime: `385.21602948141907` seconds

## Per-Seed Metrics

| Seed | Tail Accuracy | Tail Events | All Accuracy | Tail Corr | Runtime Seconds | Spikes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `42` | `0.5952380952380952` | `25 / 42` | `0.543859649122807` | `0.05827046543382765` | `399.1431918621529` | `94885` |
| `43` | `0.5238095238095238` | `22 / 42` | `0.5321637426900585` | `-0.011048756473399007` | `391.8447701931` | `94846` |
| `44` | `0.5238095238095238` | `22 / 42` | `0.5730994152046783` | `0.10016740018210536` | `364.6601263890043` | `94707` |

Aggregate task metrics:

- tail accuracy mean: `0.5476190476190476`
- tail accuracy min: `0.5238095238095238`
- all accuracy mean: `0.5497076023391813`
- tail prediction-target correlation mean: `0.04912970304751133`

The predeclared hard-switch hardware criterion was worst-seed tail accuracy `>= 0.5`; the observed minimum was `0.5238095238095238`.

## Raw Dopamine Boundary

`raw_dopamine` remains zero in this bundle. That is expected for the chunked host delayed-credit scaffold and must not be described as native dopamine learning.

The delayed task separates cue/prediction steps from delayed feedback steps. On delayed feedback steps, the same-step prediction channel is zero, so same-step dopamine telemetry is zero. The learning signal used here is the host delayed-credit replay path:

- every seed had nonzero `matured_horizons_this_step` on `1195 / 1200` steps
- `pending_horizons` stayed active up to `5` records
- `host_replay_weight` moved substantially in every seed
- real spike readback was nonzero every step and every seed

Therefore, cite this as repaired `chunked + host` delayed-credit hardware transfer, not native on-chip dopamine/eligibility traces.

## Interpretation

This result upgrades the Tier 4.16 harder hardware story:

```text
Tier 4.16a delayed_cue hardware repeat = pass
Tier 4.16b hard_noisy_switching hardware repeat = pass
```

The honest claim is now:

```text
The Tier 5.4 confirmed delayed-credit setting transfers to real SpiNNaker hardware on both delayed_cue and hard_noisy_switching under the repaired chunked-host runtime, across seeds 42, 43, and 44, with zero fallback/failures and real spike readback.
```

Do not claim:

- hardware scaling
- lifecycle/self-scaling
- full on-chip learning
- native dopamine/eligibility traces
- superiority over external baselines
- large margin robustness

The hard-switch pass is real but close to threshold, so follow-up runtime/resource characterization and stronger task/baseline work remain necessary.

## Next Gate

Proceed to Tier 4.18 chunked runtime/resource characterization, then expanded baselines and lifecycle/self-scaling tests according to the paper-readiness roadmap.
