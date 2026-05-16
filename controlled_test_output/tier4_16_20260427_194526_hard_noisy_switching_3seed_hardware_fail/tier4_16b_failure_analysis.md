# Tier 4.16b Hard Noisy Switching Hardware Failure Analysis

- Generated: `2026-04-27T19:20:27.494879+00:00`
- Status: **FAIL, noncanonical diagnostic**
- Ingested bundle: `<repo>/controlled_test_output/tier4_16_20260427_194526_hard_noisy_switching_3seed_hardware_fail`
- Source: downloaded SpiNNaker JobManager artifacts from `<downloads>`

## Short Read

This is not a hardware execution failure. All three real `pyNN.spiNNaker` runs completed with zero synthetic fallback, zero `sim.run` failures, zero summary/readback failures, and real spike readback. The failure is the predeclared learning gate for `hard_noisy_switching`: worst-seed tail accuracy was `0.47619047619047616`, below the `>= 0.5` floor.

This means Tier 4.16 is **not** complete. Tier 4.16a remains a valid delayed-cue hardware pass; Tier 4.16b says the harder noisy-switching regime is not yet robust enough on the current `N=8`, `chunked + host`, `delayed_lr_0_20` hardware path.

## Aggregate Metrics

- `runs`: `3`
- `all_accuracy_mean`: `0.4619883040935672`
- `all_accuracy_min`: `0.4035087719298245`
- `tail_accuracy_mean`: `0.5476190476190476`
- `tail_accuracy_min`: `0.4761904761904761`
- `tail_prediction_target_corr_mean`: `0.0822072669262492`
- `tail_prediction_target_corr_min`: `-0.0542140807083771`
- `runtime_seconds_mean`: `410.3018355070769`
- `total_step_spikes_min`: `94707.0`
- `sim_run_failures_sum`: `0`
- `summary_read_failures_sum`: `0`
- `synthetic_fallbacks_sum`: `0`

## Per-Seed Metrics

| Seed | All Acc | Early Acc | Tail Acc | Tail Corr | Runtime s | Spikes | Mean Spikes/Step | Final Weight | Noise Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 42 | 0.532164 | 0.485714 | 0.642857 | 0.285407 | 413.922 | 94885 | 79.071 | 4.343069 | 0.222 |
| 43 | 0.450292 | 0.428571 | 0.523810 | 0.015429 | 411.782 | 94846 | 79.038 | -1.895633 | 0.170 |
| 44 | 0.403509 | 0.428571 | 0.476190 | -0.054214 | 405.202 | 94707 | 78.922 | -1.530457 | 0.181 |

## Interpretation

- The hardware pathway worked: real spikes, stable readback, 48 chunked `sim.run` calls per seed, no fallback.
- Learning was weak and seed-sensitive: seed 42 improved, seed 43 barely cleared chance in the tail window, and seed 44 fell below the threshold.
- Correlation is not convincing: aggregate tail correlation is positive but small, and seed 44 is negative.
- The result is consistent with the earlier warning that `hard_noisy_switching` is a marginal CRA regime, not a solved one. Tier 5.4 justified a hardware probe; it did not prove hard-switch superiority.
- Do not retroactively loosen the threshold. This run failed the predeclared hardware pass gate and should stay noncanonical.

## Leading Hypotheses

1. The hard-switch task is close to chance for the current fixed `N=8` delayed-credit rule under noise and frequent switches.
2. `chunked + host` was validated locally on `delayed_cue`; it still needs a hard-switch parity diagnostic because switching/noise may expose replay differences.
3. The current fixed population has no lifecycle/ecology help. This may be exactly where self-scaling/specialist turnover is supposed to matter, but that has not been proven yet.
4. Hardware spike statistics are stable, so the first debugging target is learning dynamics/replay alignment, not SpiNNaker connectivity or readback.

## Required Next Step

Run a local-only Tier 4.16b debug/parity diagnostic before any more hard-switch hardware:

```text
task = hard_noisy_switching
seeds = 42,43,44
steps = 1200
backends = NEST, Brian2
compare = full step CRA vs chunked+host replay vs returned hardware traces
metrics = tail accuracy, all accuracy, correlation, recovery, spike bins, readout-weight trajectory
```

Decision rule:

```text
local chunked fails too -> fix CRA/task/replay in software
step CRA passes but chunked fails -> fix chunked host-replay bridge for hard-switch tasks
local chunked passes but hardware fails -> investigate SpiNNaker current scheduling, binned readback, or timing
single repaired hardware seed passes -> then rerun 3-seed 4.16b
```
