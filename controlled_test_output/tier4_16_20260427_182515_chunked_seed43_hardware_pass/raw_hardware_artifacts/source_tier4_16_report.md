# Tier 4.16 Harder SpiNNaker Hardware Capsule Findings

- Generated: `2026-04-27T17:34:45+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Output directory: `/tmp/job14824426541542099177.tmp/cra_4_17/controlled_test_output/tier4_16_20260427_182515_run_hardware`

Tier 4.16 tests whether the Tier 5.4 confirmed delayed-credit setting survives on real SpiNNaker hardware.

## Claim Boundary

- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.
- `PASS` requires real `pyNN.spiNNaker`, zero synthetic fallback, zero `sim.run` failures, zero summary-read failures, real spike readback, and task metrics above threshold.
- This is not full hardware scaling and not a superiority claim over external baselines.

## Summary

- hardware_run_attempted: `True`
- hardware_target_configured: `False`
- backend: `pyNN.spiNNaker`
- tasks: `['delayed_cue']`
- seeds: `[43]`
- runs: `1`
- total_step_spikes_min: `94979`
- total_step_spikes_mean: `94979`
- sim_run_failures_sum: `0`
- summary_read_failures_sum: `0`
- synthetic_fallbacks_sum: `0`
- runtime_seconds_mean: `566.76`
- jobmanager_cli: `None`
- failure_step: `None`

## Task Summary

| Part | Task | Runs | Tail Acc Mean | Tail Acc Min | Tail Corr Mean | Spike Min | Runtime Mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4.16a | `delayed_cue` | 1 | 1 | 1 | 1 | 94979 | 566.76 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| all requested task/seed hardware runs completed | 1 | == 1 | yes |
| sim.run failures sum | 0 | == 0 | yes |
| summary read failures sum | 0 | == 0 | yes |
| synthetic fallback sum | 0 | == 0 | yes |
| real spike readback in every run | 94979 | > 0 | yes |
| fixed population has no births/deaths | {'births': 0, 'deaths': 0} | == {'births': 0, 'deaths': 0} | yes |
| 4.16a delayed_cue tail accuracy | 1 | >= 0.85 | yes |
| confirmed delayed-credit setting used | 0.2 | == 0.2 | yes |

## Artifacts

- `manifest_json`: `/tmp/job14824426541542099177.tmp/cra_4_17/controlled_test_output/tier4_16_20260427_182515_run_hardware/tier4_16_results.json`
- `summary_csv`: `/tmp/job14824426541542099177.tmp/cra_4_17/controlled_test_output/tier4_16_20260427_182515_run_hardware/tier4_16_summary.csv`
- `task_summary_csv`: `/tmp/job14824426541542099177.tmp/cra_4_17/controlled_test_output/tier4_16_20260427_182515_run_hardware/tier4_16_task_summary.csv`
- `delayed_cue_seed_43_timeseries_csv`: `/tmp/job14824426541542099177.tmp/cra_4_17/controlled_test_output/tier4_16_20260427_182515_run_hardware/spinnaker_hardware_delayed_cue_seed43_timeseries.csv`
- `delayed_cue_seed_43_timeseries_png`: `/tmp/job14824426541542099177.tmp/cra_4_17/controlled_test_output/tier4_16_20260427_182515_run_hardware/spinnaker_hardware_delayed_cue_seed43_timeseries.png`
- `hardware_summary_png`: `/tmp/job14824426541542099177.tmp/cra_4_17/controlled_test_output/tier4_16_20260427_182515_run_hardware/tier4_16_hardware_summary.png`
- `spinnaker_report_1`: `/tmp/job14824426541542099177.tmp/cra_4_17/controlled_test_output/tier4_16_20260427_182515_run_hardware/spinnaker_reports/2026-04-27-18-25-15-283203`

![tier4_16_hardware_summary](tier4_16_hardware_summary.png)
