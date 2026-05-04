# Tier 4.15 SpiNNaker Hardware Multi-Seed Repeat Findings

- Generated: `2026-04-27T01:56:58+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_15_20260426_215658`
- Requested seeds: `[42, 43, 44]`

Tier 4.15 repeats the same minimal fixed-pattern hardware capsule from Tier 4.13 across multiple seeds. It is repeatability evidence, not a harder task and not hardware scaling.

## Claim Boundary

- `PREPARED` means the JobManager package exists locally; it is not hardware evidence.
- `PASS` requires every requested seed to run through real `pyNN.spiNNaker` with zero fallback/failures, nonzero spike readback, and learning metrics above threshold.
- A pass supports repeatability of the minimal capsule only; it does not prove full hardware scaling or full CRA hardware deployment.

## Summary

- hardware_run_attempted: `False`
- hardware_target_configured: `False`
- jobmanager_cli: `None`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| capsule package generated | True | == True | yes |

## Artifacts

- `manifest_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_15_20260426_215658/tier4_15_results.json`
- `summary_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_15_20260426_215658/tier4_15_summary.csv`
- `capsule_dir`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_15_20260426_215658/jobmanager_capsule`
- `capsule_config_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_15_20260426_215658/jobmanager_capsule/capsule_config.json`
- `jobmanager_run_script`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_15_20260426_215658/jobmanager_capsule/run_tier4_15_on_jobmanager.sh`
- `jobmanager_readme`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_15_20260426_215658/jobmanager_capsule/README_JOBMANAGER.md`
- `expected_outputs_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_15_20260426_215658/jobmanager_capsule/expected_outputs.json`
