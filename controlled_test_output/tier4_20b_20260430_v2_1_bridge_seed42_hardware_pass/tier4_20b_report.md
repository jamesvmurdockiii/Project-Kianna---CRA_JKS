# Tier 4.20b v2.1 One-Seed Chunked Hardware Probe

- Generated: `2026-04-30T03:41:16+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Output directory: `<jobmanager_tmp>`

Tier 4.20b checks whether the frozen v2.1 software evidence stack has a clean one-seed SpiNNaker transport path through the current chunked-host bridge.

## Claim Boundary

- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.
- `PASS` in `run-hardware` requires a passing child pyNN.spiNNaker run, zero fallback/failures, and nonzero real spike readback.
- This is not full v2.1 native hardware execution, custom C, on-chip learning, language, planning, AGI, or macro eligibility evidence.

## Summary

- baseline: `v2.1`
- runner_revision: `tier4_20b_inprocess_no_baselines_20260429_2330`
- tasks: `['delayed_cue', 'hard_noisy_switching']`
- seeds: `[42]`
- steps: `1200`
- population_size: `8`
- runtime_mode: `chunked`
- learning_location: `host`
- chunk_size_steps: `50`
- macro_eligibility_enabled: `False`
- hardware_run_attempted: `True`
- child_status: `pass`
- child_hardware_run_attempted: `True`
- child_total_step_spikes_min: `94900.0`
- child_sim_run_failures_sum: `0`
- child_summary_read_failures_sum: `0`
- child_synthetic_fallbacks_sum: `0`

## Child Task Summary

| Task | Runs | Tail min | Corr mean | Spikes mean |
| --- | --- | --- | --- | --- |
| `delayed_cue` | `1` | `1.0` | `0.9999999999999998` | `95003.0` |
| `hard_noisy_switching` | `1` | `0.5952380952380952` | `0.05827046543382765` | `94900.0` |

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
| v2.1 baseline identity recorded | `{'baseline': 'v2.1', 'artifact': '<jobmanager_tmp>', 'artifact_present': False}` | `runtime does not require baselines/` | yes |
| Tier 4.20b runner revision | `tier4_20b_inprocess_no_baselines_20260429_2330` | `expected current source` | yes |
| source package import path available | `{'canonical_package': '<jobmanager_tmp>', 'canonical_package_exists': True, 'action': 'already_canonical', 'aliases_checked': ['<jobmanager_tmp>', '<jobmanager_tmp> reef spinnaker']}` | `coral_reef_spinnaker exists` | yes |
| Tier 4.16 child hardware runner exists | `<jobmanager_tmp>` | `exists` | yes |
| Tier 4.20a transfer audit context | `{'status': 'missing', 'manifest': None}` | `optional; local audit context only` | yes |
| exactly one seed requested for 4.20b | `[42]` | `len == 1` | yes |
| runtime mode is chunked | `chunked` | `fixed` | yes |
| learning location is host | `host` | `fixed` | yes |
| chunk size uses current default unless overridden | `50` | `>= 1` | yes |
| macro eligibility disabled | `False` | `== false` | yes |
| delayed_lr_0_20 selected | `0.2` | `== 0.20` | yes |
| mode has explicit claim boundary | `run-hardware` | `prepare|run-hardware|ingest` | yes |
| child Tier 4.16 in-process runner exited cleanly | `0` | `== 0` | yes |
| child Tier 4.16 manifest exists | `<jobmanager_tmp>` | `exists` | yes |
| child hardware status passed | `pass` | `== pass` | yes |
| child hardware was attempted | `True` | `== true` | yes |
| child sim.run failures zero | `0` | `== 0` | yes |
| child summary read failures zero | `0` | `== 0` | yes |
| child synthetic fallback zero | `0` | `== 0` | yes |
| child real spike readback nonzero | `94900.0` | `> 0` | yes |
| child runtime documented | `279.21564924542326` | `finite` | yes |

## Artifacts

- `bridge_profile_json`: `<jobmanager_tmp>`
- `child_output_dir`: `<jobmanager_tmp>`
- `child_spinnaker_hardware_delayed_cue_seed42_timeseries.csv`: `<jobmanager_tmp>`
- `child_spinnaker_hardware_delayed_cue_seed42_timeseries.png`: `<jobmanager_tmp>`
- `child_spinnaker_hardware_hard_noisy_switching_seed42_timeseries.csv`: `<jobmanager_tmp>`
- `child_spinnaker_hardware_hard_noisy_switching_seed42_timeseries.png`: `<jobmanager_tmp>`
- `child_stderr_log`: `<jobmanager_tmp>`
- `child_stdout_log`: `<jobmanager_tmp>`
- `child_tier4_16_hardware_summary.png`: `<jobmanager_tmp>`
- `child_tier4_16_report.md`: `<jobmanager_tmp>`
- `child_tier4_16_results.json`: `<jobmanager_tmp>`
- `child_tier4_16_summary.csv`: `<jobmanager_tmp>`
- `child_tier4_16_task_summary.csv`: `<jobmanager_tmp>`
- `report_md`: `<jobmanager_tmp>`
- `results_json`: `<jobmanager_tmp>`
- `summary_csv`: `<jobmanager_tmp>`
