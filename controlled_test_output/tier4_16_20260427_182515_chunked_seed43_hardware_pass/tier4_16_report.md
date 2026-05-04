# Tier 4.16 Harder SpiNNaker Hardware Capsule Findings

- Generated: `2026-04-27T17:40:46+00:00`
- Mode: `ingest`
- Status: **PASS**
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass`

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

- `manifest_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/tier4_16_results.json`
- `summary_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/tier4_16_summary.csv`
- `ingested_source`: `/private/tmp/cra_tier4_16a_seed43_ingest_source/tier4_16_results.json`
- `tier4_16_summary.csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/tier4_16_summary.csv`
- `tier4_16_task_summary.csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/tier4_16_task_summary.csv`
- `tier4_16_hardware_summary.png`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/tier4_16_hardware_summary.png`
- `spinnaker_hardware_delayed_cue_seed43_timeseries.csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/spinnaker_hardware_delayed_cue_seed43_timeseries.csv`
- `spinnaker_hardware_delayed_cue_seed43_timeseries.png`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/spinnaker_hardware_delayed_cue_seed43_timeseries.png`
- `raw_reports.zip`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/raw_hardware_artifacts/reports.zip`
- `raw_global_provenance.sqlite3`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/raw_hardware_artifacts/global_provenance.sqlite3`
- `raw_finished`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/raw_hardware_artifacts/finished`
- `raw_tier4_16_latest_manifest.json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/raw_hardware_artifacts/tier4_16_latest_manifest.json`
- `raw_source_tier4_16_report.md`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/raw_hardware_artifacts/source_tier4_16_report.md`
- `raw_hardware_artifacts_dir`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_182515_chunked_seed43_hardware_pass/raw_hardware_artifacts`
