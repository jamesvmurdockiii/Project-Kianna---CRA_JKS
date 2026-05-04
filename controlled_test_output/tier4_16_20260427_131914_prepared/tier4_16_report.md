# Tier 4.16 Harder SpiNNaker Hardware Capsule Findings

- Generated: `2026-04-27T17:19:14+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_131914_prepared`

Tier 4.16 tests whether the Tier 5.4 confirmed delayed-credit setting survives on real SpiNNaker hardware.

## Claim Boundary

- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.
- `PASS` requires real `pyNN.spiNNaker`, zero synthetic fallback, zero `sim.run` failures, zero summary-read failures, real spike readback, and task metrics above threshold.
- This is not full hardware scaling and not a superiority claim over external baselines.

## Summary

- hardware_run_attempted: `False`
- hardware_target_configured: `False`
- backend: `pyNN.spiNNaker`
- tasks: `['delayed_cue']`
- seeds: `[43]`
- runtime_mode: `chunked`
- learning_location: `host`
- chunk_size_steps: `25`
- capsule_dir: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_131914_prepared/jobmanager_capsule`
- jobmanager_cli: `None`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| capsule directory exists | /Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_131914_prepared/jobmanager_capsule | exists True | yes |
| confirmed delayed-credit setting selected | 0.2 | == 0.2 | yes |
| 4.16a delayed_cue included | True | == True | yes |
| runtime plan is implemented | chunked_host_stepcurrent_binned_replay | implemented True | yes |

## Artifacts

- `manifest_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_131914_prepared/tier4_16_results.json`
- `summary_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_131914_prepared/tier4_16_summary.csv`
- `capsule_dir`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_131914_prepared/jobmanager_capsule`
- `capsule_config_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_131914_prepared/jobmanager_capsule/capsule_config.json`
- `jobmanager_run_script`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_131914_prepared/jobmanager_capsule/run_tier4_16_on_jobmanager.sh`
- `jobmanager_readme`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_131914_prepared/jobmanager_capsule/README_JOBMANAGER.md`
- `expected_outputs_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_16_20260427_131914_prepared/jobmanager_capsule/expected_outputs.json`
