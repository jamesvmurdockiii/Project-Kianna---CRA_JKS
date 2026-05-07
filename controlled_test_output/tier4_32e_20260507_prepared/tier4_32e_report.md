# Tier 4.32e - Multi-Chip Learning Micro-Task

- Generated: `2026-05-07T17:02:16+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Runner revision: `tier4_32e_multichip_learning_microtask_20260507_0001`

## Claim Boundary

Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.

## Summary

- upload_package: `cra_432e`
- upload_bundle: `/Users/james/JKS:CRA/controlled_test_output/tier4_32e_20260507_prepared/ebrains_upload_bundle/cra_432e`
- stable_upload_folder: `/Users/james/JKS:CRA/ebrains_jobs/cra_432e`
- job_command: `cra_432e/experiments/tier4_32e_multichip_learning_microtask.py --mode run-hardware --output-dir tier4_32e_job_output`
- what_i_need_from_user: `Upload `cra_432e` to EBRAINS/JobManager and run the emitted command.`
- source_chip: `{'x': 0, 'y': 0}`
- remote_chip: `{'x': 1, 'y': 0}`
- event_count: `32`
- expected_lookups: `96`
- learning_cases: `[{'label': 'enabled_lr_0_25', 'learning_rate': 0.25, 'kind': 'enabled'}, {'label': 'no_learning_lr_0_00', 'learning_rate': 0.0, 'kind': 'no_learning'}]`
- reference_cases: `{'enabled_lr_0_25': {'learning_rate': 0.25, 'learning_rate_raw': 8192, 'event_count': 32, 'decisions': 32, 'reward_events': 32, 'pending_created': 32, 'pending_matured': 32, 'active_pending': 0, 'readout_weight_raw': 32768, 'readout_bias_raw': 0, 'readout_weight': 1.0, 'readout_bias': 0.0, 'final_timestep': 34, 'trace_preview': [{'timestep': 2, 'event': 1, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 0, 'due': 3}, {'timestep': 3, 'event': 2, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': 0, 'due': 4}, {'timestep': 4, 'event': 3, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 16384, 'due': 5}, {'timestep': 5, 'event': 4, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': -16384, 'due': 6}, {'timestep': 6, 'event': 5, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': -16384, 'due': 7}, {'timestep': 7, 'event': 6, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 24576, 'due': 8}, {'timestep': 8, 'event': 7, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': -32768, 'due': 9}, {'timestep': 9, 'event': 8, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 28672, 'due': 10}]}, 'no_learning_lr_0_00': {'learning_rate': 0.0, 'learning_rate_raw': 0, 'event_count': 32, 'decisions': 32, 'reward_events': 32, 'pending_created': 32, 'pending_matured': 32, 'active_pending': 0, 'readout_weight_raw': 0, 'readout_bias_raw': 0, 'readout_weight': 0.0, 'readout_bias': 0.0, 'final_timestep': 34, 'trace_preview': [{'timestep': 2, 'event': 1, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 0, 'due': 3}, {'timestep': 3, 'event': 2, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': 0, 'due': 4}, {'timestep': 4, 'event': 3, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 0, 'due': 5}, {'timestep': 5, 'event': 4, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': 0, 'due': 6}, {'timestep': 6, 'event': 5, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': 0, 'due': 7}, {'timestep': 7, 'event': 6, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 0, 'due': 8}, {'timestep': 8, 'event': 7, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': 0, 'due': 9}, {'timestep': 9, 'event': 8, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 0, 'due': 10}]}}`
- claim_boundary: `Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.32c inter-chip contract passed | `"pass"` | == pass | yes |
| Tier 4.32d hardware pass ingested | `"pass"` | == pass | yes |
| Tier 4.32d-r0 route audit passed | `"pass"` | == pass | yes |
| Tier 4.32d-r1 route repair/local QA passed | `"pass"` | == pass | yes |
| inter-chip route source checks pass | `"pass"` | == pass | yes |
| runner and dependencies py_compile | `"pass"` | == pass | yes |
| upload bundle created | `"/Users/james/JKS:CRA/controlled_test_output/tier4_32e_20260507_prepared/ebrains_upload_bundle/cra_432e"` | exists | yes |
| stable upload folder created | `"/Users/james/JKS:CRA/ebrains_jobs/cra_432e"` | exists | yes |
| run-hardware command emitted | `"cra_432e/experiments/tier4_32e_multichip_learning_microtask.py --mode run-hardware --output-dir tier4_32e_job_output"` | contains --mode run-hardware | yes |
| bundle Makefile exposes request link route | `"MCPL_INTERCHIP_REQUEST_LINK_ROUTE"` | present | yes |
| bundle Makefile exposes reply link route | `"MCPL_INTERCHIP_REPLY_LINK_ROUTE"` | present | yes |
| bundle installs outbound request route | `"CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE"` | present | yes |
| bundle installs outbound reply route | `"CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE"` | present | yes |
| reference enabled learning moves readout | `32768` | > 0 | yes |
| reference no-learning control stays fixed | `0` | == 0 | yes |
| multi-chip learning micro-task only | `{"remote": {"x": 1, "y": 0}, "source": {"x": 0, "y": 0}}` | predeclared | yes |
| true two-partition learning remains blocked | `"blocked"` | == blocked | yes |
| native-scale baseline freeze remains blocked | `"not_authorized"` | == not_authorized | yes |

## Next

Upload the stable `cra_432e` folder to EBRAINS and run the emitted JobManager command.
