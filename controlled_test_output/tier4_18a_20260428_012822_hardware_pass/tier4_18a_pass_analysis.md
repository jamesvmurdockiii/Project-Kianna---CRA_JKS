# Tier 4.18a Runtime Baseline Interpretation

## Result

Tier 4.18a passed as a runtime/resource characterization of the v0.7 chunked-host SpiNNaker path.

It does not create a new learning/superiority/scaling claim. It measures whether the already-promoted v0.7 hardware bridge can use larger chunks without degrading learning or readback.

## What Passed

- runs completed: 6 / 6
- sim.run failures: 0
- summary read failures: 0
- synthetic fallbacks: 0
- scheduled-input failures: 0
- spike-readback failures: 0
- minimum real spike readback: 94885.0
- recommended chunk size: 50

## Runtime / Chunk Matrix

| task | chunk | sim.run calls | runtime seconds | tail accuracy | total spikes |
| --- | ---: | ---: | ---: | ---: | ---: |
| `delayed_cue` | 10 | 120 | 805.046 | 1.000000 | 95000 |
| `delayed_cue` | 25 | 48 | 415.252 | 1.000000 | 94976 |
| `delayed_cue` | 50 | 24 | 252.291 | 1.000000 | 95003 |
| `hard_noisy_switching` | 10 | 120 | 883.365 | 0.595238 | 94892 |
| `hard_noisy_switching` | 25 | 48 | 409.642 | 0.595238 | 94885 |
| `hard_noisy_switching` | 50 | 24 | 258.694 | 0.595238 | 94900 |

## Interpretation

- Chunk `50` preserved task behavior relative to the current v0.7 chunk `25` baseline on both tasks.
- Chunk `50` cut `sim.run` calls from `48` to `24` relative to chunk `25`, and from `120` to `24` relative to chunk `10`.
- `delayed_cue` runtime dropped from `805.046s` at chunk `10` to `252.291s` at chunk `50` (68.7% lower), and from `415.252s` at chunk `25` to `252.291s` (39.2% lower).
- `hard_noisy_switching` runtime dropped from `883.365s` at chunk `10` to `258.694s` at chunk `50` (70.7% lower), and from `409.642s` at chunk `25` to `258.694s` (36.8% lower).
- Spike readback stayed stable near `95k` total per run across chunk sizes.
- `raw_dopamine` remains `0.0` in these traces for the same reason as Tier 4.16b: delayed-credit learning is represented by host replay/matured horizon bookkeeping, not same-step raw dopamine overlap.

## Updated Default

Use `chunk_size_steps=50` as the default hardware chunk for the current v0.7 chunked-host path, unless a future task-specific parity check shows degradation.

## Boundaries

- Not hardware scaling.
- Not lifecycle/self-scaling.
- Not native on-chip dopamine or native eligibility traces.
- Not continuous/custom C runtime.
- Not external-baseline superiority.
- Not proof that chunk `100` or larger chunks are safe.

## Next Decision

The next science step is Tier 5.5 expanded baselines/fairness, while future hardware tiers should default to chunk `50` for v0.7 unless they are explicitly testing runtime limits.
