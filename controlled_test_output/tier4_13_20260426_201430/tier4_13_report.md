# Tier 4.13 SpiNNaker Hardware Capsule Findings

- Generated: `2026-04-27T00:14:30+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_13_20260426_201430`

Tier 4.13 is separate from Tier 4.12. It is the hardware capsule step: a minimal fixed-pattern CRA task intended to run on real SpiNNaker hardware through EBRAINS/JobManager.

## Claim Boundary

- `PREPARED` means the capsule package exists locally; it is not a hardware pass.
- `PASS` requires a real `pyNN.spiNNaker` run with zero synthetic fallback, zero `sim.run` failures, zero summary-read failures, real spike readback, and learning metrics above threshold.
- SpiNNaker virtual-board or setup-only results must not be described as hardware learning.

## Summary

- hardware_run_attempted: `False`
- hardware_target_configured: `False`
- jobmanager_cli: `None`
- capsule_dir: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_13_20260426_201430/jobmanager_capsule`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| sPyNNaker imports locally | True | == True | yes |
| capsule package generated | True | == True | yes |

## Artifacts

- `manifest_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_13_20260426_201430/tier4_13_results.json`
- `summary_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_13_20260426_201430/tier4_13_summary.csv`
- `capsule_dir`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_13_20260426_201430/jobmanager_capsule`
- `capsule_config_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_13_20260426_201430/jobmanager_capsule/capsule_config.json`
- `jobmanager_run_script`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_13_20260426_201430/jobmanager_capsule/run_tier4_13_on_jobmanager.sh`
- `jobmanager_readme`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_13_20260426_201430/jobmanager_capsule/README_JOBMANAGER.md`
- `expected_outputs_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_13_20260426_201430/jobmanager_capsule/expected_outputs.json`
