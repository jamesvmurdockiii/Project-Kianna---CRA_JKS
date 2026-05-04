# Tier 4.20c v2.1 Three-Seed Chunked Hardware Repeat

- Generated: `2026-04-30T04:04:28+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_000428_prepared`

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
- steps: `120`
- population_size: `8`
- runtime_mode: `chunked`
- learning_location: `host`
- chunk_size_steps: `50`
- expected_child_runs: `6`
- macro_eligibility_enabled: `False`
- hardware_run_attempted: `False`
- capsule_dir: `/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_000428_prepared/jobmanager_capsule`

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
| source package import path available | `{'canonical_package': '/Users/james/JKS:CRA/coral_reef_spinnaker', 'canonical_package_exists': True, 'action': 'already_canonical', 'aliases_checked': ['/Users/james/JKS:CRA/coral-reef-spinnaker', '/Users/james/JKS:CRA/coral reef spinnaker']}` | `coral_reef_spinnaker exists` | yes |
| Tier 4.16 child hardware runner exists | `/Users/james/JKS:CRA/experiments/tier4_harder_spinnaker_capsule.py` | `exists` | yes |
| Tier 4.20b prerequisite pass recorded | `{'status': 'pass', 'manifest': '/Users/james/JKS:CRA/controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass_ingested/tier4_20b_results.json'}` | `status == pass` | yes |
| three predeclared seeds requested | `[42, 43, 44]` | `== [42, 43, 44]` | yes |
| tasks match v2.1 bridge repeat | `['delayed_cue', 'hard_noisy_switching']` | `delayed_cue + hard_noisy_switching` | yes |
| runtime mode is chunked | `chunked` | `fixed` | yes |
| learning location is host | `host` | `fixed` | yes |
| chunk size uses 4.20b default | `50` | `== 50` | yes |
| macro eligibility disabled | `False` | `== false` | yes |
| delayed_lr_0_20 selected | `0.2` | `== 0.20` | yes |
| mode has explicit claim boundary | `prepare` | `prepare|run-hardware|ingest` | yes |
| capsule directory exists | `/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_000428_prepared/jobmanager_capsule` | `exists` | yes |

## Artifacts

- `bridge_profile_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_000428_prepared/tier4_20c_bridge_profile.json`
- `capsule_config_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_000428_prepared/jobmanager_capsule/capsule_config.json`
- `capsule_dir`: `/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_000428_prepared/jobmanager_capsule`
- `expected_outputs_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_000428_prepared/jobmanager_capsule/expected_outputs.json`
- `jobmanager_readme`: `/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_000428_prepared/jobmanager_capsule/README_JOBMANAGER.md`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_000428_prepared/tier4_20c_report.md`
- `results_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_000428_prepared/tier4_20c_results.json`
- `summary_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_000428_prepared/tier4_20c_summary.csv`
- `v2_1_bridge_profile_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_000428_prepared/jobmanager_capsule/v2_1_bridge_profile.json`
