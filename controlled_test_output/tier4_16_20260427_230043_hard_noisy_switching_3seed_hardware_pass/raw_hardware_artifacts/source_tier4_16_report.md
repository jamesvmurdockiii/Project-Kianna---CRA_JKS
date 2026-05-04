# Tier 4.16 Harder SpiNNaker Hardware Capsule Findings

- Generated: `2026-04-27T23:00:43+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Output directory: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware`

Tier 4.16 tests whether the Tier 5.4 confirmed delayed-credit setting survives on real SpiNNaker hardware.

## Claim Boundary

- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.
- `PASS` requires real `pyNN.spiNNaker`, zero synthetic fallback, zero `sim.run` failures, zero summary-read failures, real spike readback, and task metrics above threshold.
- This is not full hardware scaling and not a superiority claim over external baselines.

## Summary

- hardware_run_attempted: `True`
- hardware_target_configured: `False`
- backend: `pyNN.spiNNaker`
- tasks: `['hard_noisy_switching']`
- seeds: `[42, 43, 44]`
- runs: `3`
- total_step_spikes_min: `94707`
- total_step_spikes_mean: `94812.7`
- sim_run_failures_sum: `0`
- summary_read_failures_sum: `0`
- synthetic_fallbacks_sum: `0`
- runtime_seconds_mean: `385.216`
- jobmanager_cli: `None`
- failure_step: `None`

## Task Summary

| Part | Task | Runs | Tail Acc Mean | Tail Acc Min | Tail Corr Mean | Spike Min | Runtime Mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4.16b | `hard_noisy_switching` | 3 | 0.547619 | 0.52381 | 0.0491297 | 94707 | 385.216 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| all requested task/seed hardware runs completed | 3 | == 3 | yes |
| sim.run failures sum | 0 | == 0 | yes |
| summary read failures sum | 0 | == 0 | yes |
| synthetic fallback sum | 0 | == 0 | yes |
| real spike readback in every run | 94707 | > 0 | yes |
| fixed population has no births/deaths | {'births': 0, 'deaths': 0} | == {'births': 0, 'deaths': 0} | yes |
| 4.16b hard_noisy_switching tail accuracy | 0.52381 | >= 0.5 | yes |
| 4.16b hard_noisy_switching tail correlation is finite | 0.0491297 | is finite True | yes |
| confirmed delayed-credit setting used | 0.2 | == 0.2 | yes |

## Artifacts

- `manifest_json`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/tier4_16_results.json`
- `summary_csv`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/tier4_16_summary.csv`
- `task_summary_csv`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/tier4_16_task_summary.csv`
- `hard_noisy_switching_seed_42_timeseries_csv`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/spinnaker_hardware_hard_noisy_switching_seed42_timeseries.csv`
- `hard_noisy_switching_seed_42_timeseries_png`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/spinnaker_hardware_hard_noisy_switching_seed42_timeseries.png`
- `hard_noisy_switching_seed_43_timeseries_csv`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/spinnaker_hardware_hard_noisy_switching_seed43_timeseries.csv`
- `hard_noisy_switching_seed_43_timeseries_png`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/spinnaker_hardware_hard_noisy_switching_seed43_timeseries.png`
- `hard_noisy_switching_seed_44_timeseries_csv`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/spinnaker_hardware_hard_noisy_switching_seed44_timeseries.csv`
- `hard_noisy_switching_seed_44_timeseries_png`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/spinnaker_hardware_hard_noisy_switching_seed44_timeseries.png`
- `hardware_summary_png`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/tier4_16_hardware_summary.png`
- `spinnaker_report_1`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/spinnaker_reports/2026-04-27-23-41-20-749831`
- `spinnaker_report_2`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/spinnaker_reports/2026-04-27-23-48-02-313639`
- `spinnaker_report_3`: `/tmp/job16838073389263760760.tmp/CRA_test/controlled_test_output/tier4_16_20260427_234120_run_hardware/spinnaker_reports/2026-04-27-23-54-36-401001`

![tier4_16_hardware_summary](tier4_16_hardware_summary.png)
