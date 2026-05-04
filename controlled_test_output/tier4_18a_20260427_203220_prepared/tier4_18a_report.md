# Tier 4.18a v0.7 Chunked Hardware Runtime Baseline Findings

- Generated: `2026-04-28T00:32:20+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_18a_20260427_203220_prepared`

Tier 4.18a characterizes runtime/resource cost for the v0.7 chunked-host hardware path that already passed Tier 4.16a and Tier 4.16b.

## Claim Boundary

- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.
- `PASS` requires real `pyNN.spiNNaker`, zero fallback/failures, real spike readback, documented runtime/call counts, and task metrics above threshold.
- This is runtime/resource characterization, not hardware scaling, not on-chip learning, and not a new superiority claim.

## Summary

- hardware_run_attempted: `False`
- hardware_target_configured: `False`
- backend: `pyNN.spiNNaker`
- tasks: `['delayed_cue', 'hard_noisy_switching']`
- seeds: `[42]`
- chunk_sizes: `[10, 25, 50]`
- steps: `1200`
- population_size: `8`
- runtime_mode: `chunked`
- learning_location: `host`
- jobmanager_cli: `None`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| capsule directory exists | /Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_18a_20260427_203220_prepared/jobmanager_capsule | exists True | yes |
| delayed_cue included | True | == True | yes |
| hard_noisy_switching included | True | == True | yes |
| chunk sizes include 10,25,50 | [10, 25, 50] | contains [10, 25, 50] | yes |
| confirmed delayed-credit setting selected | 0.2 | == 0.2 | yes |
| all runtime plans implemented | ['chunked_host_stepcurrent_binned_replay', 'chunked_host_stepcurrent_binned_replay', 'chunked_host_stepcurrent_binned_replay'] | implemented True | yes |

## Artifacts

- `manifest_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_18a_20260427_203220_prepared/tier4_18a_results.json`
- `summary_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_18a_20260427_203220_prepared/tier4_18a_summary.csv`
- `capsule_dir`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_18a_20260427_203220_prepared/jobmanager_capsule`
- `capsule_config_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_18a_20260427_203220_prepared/jobmanager_capsule/capsule_config.json`
- `jobmanager_run_script`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_18a_20260427_203220_prepared/jobmanager_capsule/run_tier4_18a_on_jobmanager.sh`
- `jobmanager_readme`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_18a_20260427_203220_prepared/jobmanager_capsule/README_JOBMANAGER.md`
- `expected_outputs_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_18a_20260427_203220_prepared/jobmanager_capsule/expected_outputs.json`
