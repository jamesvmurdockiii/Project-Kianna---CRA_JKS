# Tier 4.20b v2.1 One-Seed Chunked Hardware Probe

- Generated: `2026-04-30T02:13:35+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `<repo>/tier4_20b_preflight_output/source_prepare_smoke`

Tier 4.20b checks whether the frozen v2.1 software evidence stack has a clean one-seed SpiNNaker transport path through the current chunked-host bridge.

## Claim Boundary

- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.
- `PASS` in `run-hardware` requires a passing child pyNN.spiNNaker run, zero fallback/failures, and nonzero real spike readback.
- This is not full v2.1 native hardware execution, custom C, on-chip learning, language, planning, AGI, or macro eligibility evidence.

## Summary

- baseline: `v2.1`
- tasks: `['delayed_cue']`
- seeds: `[42]`
- steps: `120`
- population_size: `8`
- runtime_mode: `chunked`
- learning_location: `host`
- chunk_size_steps: `25`
- macro_eligibility_enabled: `False`
- hardware_run_attempted: `False`
- capsule_dir: `<repo>/tier4_20b_preflight_output/source_prepare_smoke/jobmanager_capsule`

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
| v2.1 baseline artifact exists | `<repo>/baselines/CRA_EVIDENCE_BASELINE_v2.1.json` | `exists` | yes |
| source package import path available | `{'canonical_package': '<repo>/coral_reef_spinnaker', 'canonical_package_exists': True, 'action': 'already_canonical', 'aliases_checked': ['<repo>/coral-reef-spinnaker', '<repo>/coral reef spinnaker']}` | `coral_reef_spinnaker exists` | yes |
| Tier 4.16 child hardware runner exists | `<repo>/experiments/tier4_harder_spinnaker_capsule.py` | `exists` | yes |
| Tier 4.20a transfer audit context | `{'status': 'pass', 'manifest': '<repo>/controlled_test_output/tier4_20a_20260429_195403/tier4_20a_results.json'}` | `optional; local audit context only` | yes |
| exactly one seed requested for 4.20b | `[42]` | `len == 1` | yes |
| runtime mode is chunked | `chunked` | `fixed` | yes |
| learning location is host | `host` | `fixed` | yes |
| chunk size uses current default unless overridden | `25` | `>= 1` | yes |
| macro eligibility disabled | `False` | `== false` | yes |
| delayed_lr_0_20 selected | `0.2` | `== 0.20` | yes |
| mode has explicit claim boundary | `prepare` | `prepare|run-hardware|ingest` | yes |
| capsule directory exists | `<repo>/tier4_20b_preflight_output/source_prepare_smoke/jobmanager_capsule` | `exists` | yes |

## Artifacts

- `bridge_profile_json`: `<repo>/tier4_20b_preflight_output/source_prepare_smoke/tier4_20b_bridge_profile.json`
- `capsule_config_json`: `<repo>/tier4_20b_preflight_output/source_prepare_smoke/jobmanager_capsule/capsule_config.json`
- `capsule_dir`: `<repo>/tier4_20b_preflight_output/source_prepare_smoke/jobmanager_capsule`
- `expected_outputs_json`: `<repo>/tier4_20b_preflight_output/source_prepare_smoke/jobmanager_capsule/expected_outputs.json`
- `jobmanager_readme`: `<repo>/tier4_20b_preflight_output/source_prepare_smoke/jobmanager_capsule/README_JOBMANAGER.md`
- `jobmanager_run_script`: `<repo>/tier4_20b_preflight_output/source_prepare_smoke/jobmanager_capsule/run_tier4_20b_on_jobmanager.sh`
- `report_md`: `<repo>/tier4_20b_preflight_output/source_prepare_smoke/tier4_20b_report.md`
- `results_json`: `<repo>/tier4_20b_preflight_output/source_prepare_smoke/tier4_20b_results.json`
- `summary_csv`: `<repo>/tier4_20b_preflight_output/source_prepare_smoke/tier4_20b_summary.csv`
- `v2_1_bridge_profile_json`: `<repo>/tier4_20b_preflight_output/source_prepare_smoke/jobmanager_capsule/v2_1_bridge_profile.json`
