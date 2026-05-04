# Tier 4.16 Harder SpiNNaker Hardware Capsule Findings

- Generated: `2026-04-30T02:48:01+00:00`
- Mode: `run-hardware`
- Status: **BLOCKED**
- Output directory: `/tmp/job7406591636550451632.tmp/cra/tier4_20b_target_check_output/child_tier4_16`

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
- seeds: `[42]`
- runtime_mode: `chunked`
- learning_location: `host`
- chunk_size_steps: `4`
- jobmanager_cli: `None`

Failure: No real SpiNNaker target is configured in this environment. pyNN.spiNNaker is installed, but sPyNNaker has no Machine target (no machineName, version, spalloc_server, remote_spinnaker_url, SPINNAKER_MACHINE, or SPALLOC_SERVER). Run inside a real SpiNNaker allocation or provide --spinnaker-hostname if that is the correct target for this EBRAINS job.


## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| real SpiNNaker target configured | {'hardware_target_configured': False, 'spynnaker_config': {'path': '/home/jovyan/.spynnaker.cfg', 'exists': True, 'machineName': None, 'version': None, 'spalloc_server': None, 'remote_spinnaker_url': None, 'spalloc_port': None, 'spalloc_user': None, 'spalloc_group': None, 'virtual_board': None, 'width': None, 'height': None, 'mode': None}, 'env_flags': {'JOB_ID': False, 'SLURM_JOB_ID': False, 'EBRAINS_JOB_ID': False, 'SPINNAKER_MACHINE': False, 'SPALLOC_SERVER': False, 'REMOTE_SPINNAKER_URL': False}} | == True | no |

## Artifacts

- `manifest_json`: `/tmp/job7406591636550451632.tmp/cra/tier4_20b_target_check_output/child_tier4_16/tier4_16_results.json`
- `summary_csv`: `/tmp/job7406591636550451632.tmp/cra/tier4_20b_target_check_output/child_tier4_16/tier4_16_summary.csv`
