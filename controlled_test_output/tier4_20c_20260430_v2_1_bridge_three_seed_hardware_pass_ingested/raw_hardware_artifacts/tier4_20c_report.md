# Tier 4.20c v2.1 Three-Seed Chunked Hardware Repeat

- Generated: `2026-04-30T04:36:48+00:00`
- Mode: `run-hardware`
- Status: **FAIL**
- Output directory: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output`

Tier 4.20c repeats the passed Tier 4.20b v2.1 bridge/transport path across seeds `42`, `43`, and `44`.

## Claim Boundary

- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.
- `PASS` in `run-hardware` requires a passing child pyNN.spiNNaker run, zero fallback/failures, nonzero real spike readback, and six expected child runs.
- This is repeatability evidence for the current v2.1 bridge/transport path, not full v2.1 native/on-chip execution, custom C, language, planning, AGI, or macro eligibility evidence.

## Summary

- baseline: `v2.1`
- runner_revision: `tier4_20c_inprocess_no_baselines_20260430_0000`
- tasks: `['delayed_cue', 'hard_noisy_switching']`
- seeds: `[42, 43, 44]`
- steps: `1200`
- population_size: `8`
- runtime_mode: `chunked`
- learning_location: `host`
- chunk_size_steps: `50`
- expected_child_runs: `6`
- macro_eligibility_enabled: `False`
- hardware_run_attempted: `True`
- child_status: `pass`
- child_hardware_run_attempted: `True`
- child_runs: `6`
- child_total_step_spikes_min: `94727.0`
- child_sim_run_failures_sum: `0`
- child_summary_read_failures_sum: `0`
- child_synthetic_fallbacks_sum: `0`

Failure: Failed criteria: Tier 4.20b prerequisite pass recorded


## Child Task Summary

| Task | Runs | Tail min | Tail mean | Corr mean | Spikes min |
| --- | --- | --- | --- | --- | --- |
| `delayed_cue` | `3` | `1.0` | `1.0` | `0.9999999999999997` | `94995.0` |
| `hard_noisy_switching` | `3` | `0.5238095238095238` | `0.5476190476190476` | `0.04912970304751133` | `94727.0` |

## Bridge Profile

| Mechanism | Status | Probe Role | Boundary |
| --- | --- | --- | --- |
| PendingHorizon delayed credit / delayed_lr_0_20 | `included` | `exercised_by_child_hardware_runner` | host-side delayed credit at chunk boundaries; not native on-chip eligibility |
| keyed context memory | `not_native_in_child_runner` | `bridge_contract_declared` | requires later adapter/hybrid probe before claiming hardware memory |
| replay / consolidation | `not_native_in_child_runner` | `bridge_contract_declared` | requires explicit replay epoch design before hardware replay claims |
| visible predictive context / predictive binding | `not_native_in_child_runner` | `bridge_contract_declared` | requires metadata scheduler/controls before hardware predictive-binding claims |
| composition and module routing | `not_native_in_child_runner` | `bridge_contract_declared` | requires router/module adapter before hardware routing claims |
| self-evaluation / reliability monitoring | `not_native_in_child_runner` | `bridge_contract_declared` | requires pre-feedback monitor adapter before hardware self-evaluation claims |
| macro eligibility residual trace | `parked` | `explicitly_excluded` | failed 5.9c; do not port or include in hardware/custom-C work |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.20c runner revision | `tier4_20c_inprocess_no_baselines_20260430_0000` | `expected current source` | yes |
| source package import path available | `{'canonical_package': '/tmp/job5149451337032864846.tmp/cra_420c/coral_reef_spinnaker', 'canonical_package_exists': True, 'action': 'already_canonical', 'aliases_checked': ['/tmp/job5149451337032864846.tmp/cra_420c/coral-reef-spinnaker', '/tmp/job5149451337032864846.tmp/cra_420c/coral reef spinnaker']}` | `coral_reef_spinnaker exists` | yes |
| Tier 4.16 child hardware runner exists | `/tmp/job5149451337032864846.tmp/cra_420c/experiments/tier4_harder_spinnaker_capsule.py` | `exists` | yes |
| Tier 4.20b prerequisite pass recorded | `{'status': 'missing', 'manifest': None}` | `status == pass` | no |
| three predeclared seeds requested | `[42, 43, 44]` | `== [42, 43, 44]` | yes |
| tasks match v2.1 bridge repeat | `['delayed_cue', 'hard_noisy_switching']` | `delayed_cue + hard_noisy_switching` | yes |
| runtime mode is chunked | `chunked` | `fixed` | yes |
| learning location is host | `host` | `fixed` | yes |
| chunk size uses 4.20b default | `50` | `== 50` | yes |
| macro eligibility disabled | `False` | `== false` | yes |
| delayed_lr_0_20 selected | `0.2` | `== 0.20` | yes |
| mode has explicit claim boundary | `run-hardware` | `prepare|run-hardware|ingest` | yes |
| child Tier 4.16 in-process runner exited cleanly | `0` | `== 0` | yes |
| child Tier 4.16 manifest exists | `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/tier4_16_results.json` | `exists` | yes |
| child hardware status passed | `pass` | `== pass` | yes |
| child hardware was attempted | `True` | `== true` | yes |
| child seeds match repeat plan | `[42, 43, 44]` | `== [42, 43, 44]` | yes |
| child tasks match repeat plan | `['delayed_cue', 'hard_noisy_switching']` | `== delayed_cue + hard_noisy_switching` | yes |
| child run count matches task x seed grid | `6` | `== 6` | yes |
| child sim.run failures zero | `0` | `== 0` | yes |
| child summary read failures zero | `0` | `== 0` | yes |
| child synthetic fallback zero | `0` | `== 0` | yes |
| child real spike readback nonzero | `94727.0` | `> 0` | yes |
| child runtime documented | `262.68560729618184` | `finite` | yes |

## Artifacts

- `bridge_profile_json`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/tier4_20c_bridge_profile.json`
- `child_output_dir`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16`
- `child_spinnaker_hardware_delayed_cue_seed42_timeseries.csv`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/spinnaker_hardware_delayed_cue_seed42_timeseries.csv`
- `child_spinnaker_hardware_delayed_cue_seed42_timeseries.png`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/spinnaker_hardware_delayed_cue_seed42_timeseries.png`
- `child_spinnaker_hardware_delayed_cue_seed43_timeseries.csv`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/spinnaker_hardware_delayed_cue_seed43_timeseries.csv`
- `child_spinnaker_hardware_delayed_cue_seed43_timeseries.png`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/spinnaker_hardware_delayed_cue_seed43_timeseries.png`
- `child_spinnaker_hardware_delayed_cue_seed44_timeseries.csv`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/spinnaker_hardware_delayed_cue_seed44_timeseries.csv`
- `child_spinnaker_hardware_delayed_cue_seed44_timeseries.png`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/spinnaker_hardware_delayed_cue_seed44_timeseries.png`
- `child_spinnaker_hardware_hard_noisy_switching_seed42_timeseries.csv`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/spinnaker_hardware_hard_noisy_switching_seed42_timeseries.csv`
- `child_spinnaker_hardware_hard_noisy_switching_seed42_timeseries.png`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/spinnaker_hardware_hard_noisy_switching_seed42_timeseries.png`
- `child_spinnaker_hardware_hard_noisy_switching_seed43_timeseries.csv`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/spinnaker_hardware_hard_noisy_switching_seed43_timeseries.csv`
- `child_spinnaker_hardware_hard_noisy_switching_seed43_timeseries.png`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/spinnaker_hardware_hard_noisy_switching_seed43_timeseries.png`
- `child_spinnaker_hardware_hard_noisy_switching_seed44_timeseries.csv`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/spinnaker_hardware_hard_noisy_switching_seed44_timeseries.csv`
- `child_spinnaker_hardware_hard_noisy_switching_seed44_timeseries.png`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/spinnaker_hardware_hard_noisy_switching_seed44_timeseries.png`
- `child_stderr_log`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/tier4_20c_child_stderr.log`
- `child_stdout_log`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/tier4_20c_child_stdout.log`
- `child_tier4_16_hardware_summary.png`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/tier4_16_hardware_summary.png`
- `child_tier4_16_report.md`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/tier4_16_report.md`
- `child_tier4_16_results.json`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/tier4_16_results.json`
- `child_tier4_16_summary.csv`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/tier4_16_summary.csv`
- `child_tier4_16_task_summary.csv`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/child_tier4_16/tier4_16_task_summary.csv`
- `report_md`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/tier4_20c_report.md`
- `results_json`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/tier4_20c_results.json`
- `summary_csv`: `/tmp/job5149451337032864846.tmp/tier4_20c_job_output/tier4_20c_summary.csv`
