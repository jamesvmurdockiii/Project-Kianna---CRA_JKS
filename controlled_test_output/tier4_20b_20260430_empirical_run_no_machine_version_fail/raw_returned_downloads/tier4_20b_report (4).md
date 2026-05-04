# Tier 4.20b v2.1 One-Seed Chunked Hardware Probe

- Generated: `2026-04-30T03:05:30+00:00`
- Mode: `run-hardware`
- Status: **FAIL**
- Output directory: `/tmp/job13618709677688345597.tmp/tier4_20b_job_output`

Tier 4.20b checks whether the frozen v2.1 software evidence stack has a clean one-seed SpiNNaker transport path through the current chunked-host bridge.

## Claim Boundary

- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.
- `PASS` in `run-hardware` requires a passing child pyNN.spiNNaker run, zero fallback/failures, and nonzero real spike readback.
- This is not full v2.1 native hardware execution, custom C, on-chip learning, language, planning, AGI, or macro eligibility evidence.

## Summary

- baseline: `v2.1`
- tasks: `['delayed_cue', 'hard_noisy_switching']`
- seeds: `[42]`
- steps: `1200`
- population_size: `8`
- runtime_mode: `chunked`
- learning_location: `host`
- chunk_size_steps: `50`
- macro_eligibility_enabled: `False`
- hardware_run_attempted: `True`
- child_status: `fail`
- child_hardware_run_attempted: `True`
- child_total_step_spikes_min: `None`
- child_sim_run_failures_sum: `0`
- child_summary_read_failures_sum: `0`
- child_synthetic_fallbacks_sum: `0`

Failure: Failed criteria: child Tier 4.16 command exited cleanly, child hardware status passed, child real spike readback nonzero, child runtime documented


## Child Task Summary

| Task | Runs | Tail min | Corr mean | Spikes mean |
| --- | --- | --- | --- | --- |
| `delayed_cue` | `0` | `None` | `None` | `None` |
| `hard_noisy_switching` | `0` | `None` | `None` | `None` |

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
| v2.1 baseline artifact exists | `/tmp/job13618709677688345597.tmp/cra/baselines/CRA_EVIDENCE_BASELINE_v2.1.json` | `exists` | yes |
| source package import path available | `{'canonical_package': '/tmp/job13618709677688345597.tmp/cra/coral_reef_spinnaker', 'canonical_package_exists': True, 'action': 'already_canonical', 'aliases_checked': ['/tmp/job13618709677688345597.tmp/cra/coral-reef-spinnaker', '/tmp/job13618709677688345597.tmp/cra/coral reef spinnaker']}` | `coral_reef_spinnaker exists` | yes |
| Tier 4.16 child hardware runner exists | `/tmp/job13618709677688345597.tmp/cra/experiments/tier4_harder_spinnaker_capsule.py` | `exists` | yes |
| Tier 4.20a transfer audit context | `{'status': 'missing', 'manifest': None}` | `optional; local audit context only` | yes |
| exactly one seed requested for 4.20b | `[42]` | `len == 1` | yes |
| runtime mode is chunked | `chunked` | `fixed` | yes |
| learning location is host | `host` | `fixed` | yes |
| chunk size uses current default unless overridden | `50` | `>= 1` | yes |
| macro eligibility disabled | `False` | `== false` | yes |
| delayed_lr_0_20 selected | `0.2` | `== 0.20` | yes |
| mode has explicit claim boundary | `run-hardware` | `prepare|run-hardware|ingest` | yes |
| child Tier 4.16 command exited cleanly | `1` | `== 0` | no |
| child Tier 4.16 manifest exists | `/tmp/job13618709677688345597.tmp/tier4_20b_job_output/child_tier4_16/tier4_16_results.json` | `exists` | yes |
| child hardware status passed | `fail` | `== pass` | no |
| child hardware was attempted | `True` | `== true` | yes |
| child sim.run failures zero | `0` | `== 0` | yes |
| child summary read failures zero | `0` | `== 0` | yes |
| child synthetic fallback zero | `0` | `== 0` | yes |
| child real spike readback nonzero | `None` | `> 0` | no |
| child runtime documented | `None` | `finite` | no |

## Artifacts

- `bridge_profile_json`: `/tmp/job13618709677688345597.tmp/tier4_20b_job_output/tier4_20b_bridge_profile.json`
- `child_output_dir`: `/tmp/job13618709677688345597.tmp/tier4_20b_job_output/child_tier4_16`
- `child_stderr_log`: `/tmp/job13618709677688345597.tmp/tier4_20b_job_output/tier4_20b_child_stderr.log`
- `child_stdout_log`: `/tmp/job13618709677688345597.tmp/tier4_20b_job_output/tier4_20b_child_stdout.log`
- `child_tier4_16_report.md`: `/tmp/job13618709677688345597.tmp/tier4_20b_job_output/child_tier4_16/tier4_16_report.md`
- `child_tier4_16_results.json`: `/tmp/job13618709677688345597.tmp/tier4_20b_job_output/child_tier4_16/tier4_16_results.json`
- `child_tier4_16_summary.csv`: `/tmp/job13618709677688345597.tmp/tier4_20b_job_output/child_tier4_16/tier4_16_summary.csv`
- `child_tier4_16_task_summary.csv`: `/tmp/job13618709677688345597.tmp/tier4_20b_job_output/child_tier4_16/tier4_16_task_summary.csv`
- `report_md`: `/tmp/job13618709677688345597.tmp/tier4_20b_job_output/tier4_20b_report.md`
- `results_json`: `/tmp/job13618709677688345597.tmp/tier4_20b_job_output/tier4_20b_results.json`
- `summary_csv`: `/tmp/job13618709677688345597.tmp/tier4_20b_job_output/tier4_20b_summary.csv`
