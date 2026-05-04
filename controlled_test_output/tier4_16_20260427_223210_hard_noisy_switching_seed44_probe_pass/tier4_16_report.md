# Tier 4.16 Harder SpiNNaker Hardware Capsule Findings

- Generated: `2026-04-27T22:39:50+00:00`
- Mode: `ingest`
- Status: **PASS**
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass`

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
- seeds: `[44]`
- runs: `1`
- total_step_spikes_min: `94707`
- total_step_spikes_mean: `94707`
- sim_run_failures_sum: `0`
- summary_read_failures_sum: `0`
- synthetic_fallbacks_sum: `0`
- runtime_seconds_mean: `413.99`
- jobmanager_cli: `None`
- failure_step: `None`

## Task Summary

| Part | Task | Runs | Tail Acc Mean | Tail Acc Min | Tail Corr Mean | Spike Min | Runtime Mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4.16b | `hard_noisy_switching` | 1 | 0.52381 | 0.52381 | 0.100167 | 94707 | 413.99 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| all requested task/seed hardware runs completed | 1 | == 1 | yes |
| sim.run failures sum | 0 | == 0 | yes |
| summary read failures sum | 0 | == 0 | yes |
| synthetic fallback sum | 0 | == 0 | yes |
| real spike readback in every run | 94707 | > 0 | yes |
| fixed population has no births/deaths | {'births': 0, 'deaths': 0} | == {'births': 0, 'deaths': 0} | yes |
| 4.16b hard_noisy_switching tail accuracy | 0.52381 | >= 0.5 | yes |
| 4.16b hard_noisy_switching tail correlation is finite | 0.100167 | is finite True | yes |
| confirmed delayed-credit setting used | 0.2 | == 0.2 | yes |

## Artifacts

- `manifest_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/tier4_16_results.json`
- `summary_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/tier4_16_summary.csv`
- `ingested_source`: `/private/tmp/cra_tier4_16b_seed44_probe_ingest/tier4_16_results.json`
- `tier4_16_summary.csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/tier4_16_summary.csv`
- `tier4_16_task_summary.csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/tier4_16_task_summary.csv`
- `tier4_16_hardware_summary.png`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/tier4_16_hardware_summary.png`
- `spinnaker_hardware_hard_noisy_switching_seed44_timeseries.csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/spinnaker_hardware_hard_noisy_switching_seed44_timeseries.csv`
- `spinnaker_hardware_hard_noisy_switching_seed44_timeseries.png`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/spinnaker_hardware_hard_noisy_switching_seed44_timeseries.png`
- `raw_reports.zip`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/raw_hardware_artifacts/reports.zip`
- `raw_global_provenance.sqlite3`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/raw_hardware_artifacts/global_provenance.sqlite3`
- `raw_finished`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/raw_hardware_artifacts/finished`
- `raw_tier4_16_latest_manifest.json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/raw_hardware_artifacts/tier4_16_latest_manifest.json`
- `raw_source_tier4_16_report.md`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/raw_hardware_artifacts/source_tier4_16_report.md`
- `raw_hardware_artifacts_dir`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/raw_hardware_artifacts`
