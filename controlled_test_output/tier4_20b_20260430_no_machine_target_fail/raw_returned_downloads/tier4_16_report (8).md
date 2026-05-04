# Tier 4.16 Harder SpiNNaker Hardware Capsule Findings

- Generated: `2026-04-30T01:49:54+00:00`
- Mode: `run-hardware`
- Status: **FAIL**
- Output directory: `/tmp/job17535888640787705408.tmp/tier4_20b_job_output/child_tier4_16`

Tier 4.16 tests whether the Tier 5.4 confirmed delayed-credit setting survives on real SpiNNaker hardware.

## Claim Boundary

- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.
- `PASS` requires real `pyNN.spiNNaker`, zero synthetic fallback, zero `sim.run` failures, zero summary-read failures, real spike readback, and task metrics above threshold.
- This is not full hardware scaling and not a superiority claim over external baselines.

## Summary

- hardware_run_attempted: `True`
- hardware_target_configured: `False`
- backend: `pyNN.spiNNaker`
- tasks: `['delayed_cue', 'hard_noisy_switching']`
- seeds: `[42]`
- runs: `0`
- total_step_spikes_min: `None`
- total_step_spikes_mean: `None`
- sim_run_failures_sum: `0`
- summary_read_failures_sum: `0`
- synthetic_fallbacks_sum: `0`
- runtime_seconds_mean: `None`
- jobmanager_cli: `None`
- failure_step: `None`

Failure: task hard_noisy_switching seed 42 raised SpinnMachineException: No version with cfg [Machine] values version=None, machine_name=None, spalloc_server=None, remote_spinnaker_url=None, virtual_board=False, width=None, and height=None


## Task Summary

| Part | Task | Runs | Tail Acc Mean | Tail Acc Min | Tail Corr Mean | Spike Min | Runtime Mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4.16a | `delayed_cue` | 0 | None | None | None | None | None |
| 4.16b | `hard_noisy_switching` | 0 | None | None | None | None | None |

## Artifacts

- `manifest_json`: `/tmp/job17535888640787705408.tmp/tier4_20b_job_output/child_tier4_16/tier4_16_results.json`
- `summary_csv`: `/tmp/job17535888640787705408.tmp/tier4_20b_job_output/child_tier4_16/tier4_16_summary.csv`
- `task_summary_csv`: `/tmp/job17535888640787705408.tmp/tier4_20b_job_output/child_tier4_16/tier4_16_task_summary.csv`
- `delayed_cue_seed_42_failure_traceback`: `/tmp/job17535888640787705408.tmp/tier4_20b_job_output/child_tier4_16/delayed_cue_seed_42_failure_traceback.txt`
- `hard_noisy_switching_seed_42_failure_traceback`: `/tmp/job17535888640787705408.tmp/tier4_20b_job_output/child_tier4_16/hard_noisy_switching_seed_42_failure_traceback.txt`
- `spinnaker_report_1`: `/tmp/job17535888640787705408.tmp/tier4_20b_job_output/child_tier4_16/spinnaker_reports/2026-04-30-02-49-47-895490`
- `spinnaker_report_2`: `/tmp/job17535888640787705408.tmp/tier4_20b_job_output/child_tier4_16/spinnaker_reports/2026-04-30-02-49-51-241186`
