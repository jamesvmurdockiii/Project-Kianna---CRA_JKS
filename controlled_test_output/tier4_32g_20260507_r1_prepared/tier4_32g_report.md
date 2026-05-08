# Tier 4.32g - Two-Chip Lifecycle Traffic/Resource Hardware Smoke

- Generated: `2026-05-08T02:59:50+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Runner revision: `tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260507_0002`

## Claim Boundary

Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.

## Summary

- upload_package: `cra_432g`
- upload_bundle: `/Users/james/JKS:CRA/controlled_test_output/tier4_32g_20260507_r1_prepared/ebrains_upload_bundle/cra_432g`
- stable_upload_folder: `/Users/james/JKS:CRA/ebrains_jobs/cra_432g`
- job_command: `cra_432g/experiments/tier4_32g_multichip_lifecycle_traffic_resource_smoke.py --mode run-hardware --output-dir tier4_32g_job_output`
- what_i_need_from_user: `Upload the cra_432g folder to EBRAINS/JobManager and run the emitted command.`
- source_chip: `{'x': 0, 'y': 0}`
- remote_chip: `{'x': 1, 'y': 0}`
- core_roles: `{'learning': {'chip': 'source', 'profile': 'learning_core', 'core': 7, 'app_id': 4, 'link': 'request_east'}, 'lifecycle': {'chip': 'remote', 'profile': 'lifecycle_core', 'core': 4, 'app_id': 5, 'link': 'sync_west'}}`
- claim_boundary: `Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.32e hardware prerequisite passed | `"pass"` | == pass | yes |
| Tier 4.32f decision prerequisite passed | `"pass"` | == pass | yes |
| Tier 4.32g-r0 source prerequisite passed | `"pass"` | == pass | yes |
| lifecycle source checks pass | `"pass"` | == pass | yes |
| runner and dependencies py_compile | `"pass"` | == pass | yes |
| upload bundle created | `"/Users/james/JKS:CRA/controlled_test_output/tier4_32g_20260507_r1_prepared/ebrains_upload_bundle/cra_432g"` | exists | yes |
| stable upload folder created | `"/Users/james/JKS:CRA/ebrains_jobs/cra_432g"` | exists | yes |
| run-hardware command emitted | `"cra_432g/experiments/tier4_32g_multichip_lifecycle_traffic_resource_smoke.py --mode run-hardware --output-dir tier4_32g_job_output"` | contains --mode run-hardware | yes |
| bundle Makefile exposes lifecycle request route | `"MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE"` | present | yes |
| bundle Makefile exposes lifecycle sync route | `"MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE"` | present | yes |
| bundle dispatches lifecycle receive packets | `"MCPL_MSG_LIFECYCLE_EVENT_REQUEST"` | present in receive | yes |
| bundle learning host emits lifecycle requests | `"_handle_lifecycle_event_request_emit"` | present | yes |
| bundle Python host has request helpers | `"send_lifecycle_event_request"` | present | yes |
| bundle readback exposes lifecycle counters | `"lifecycle_event_requests_sent"` | present | yes |
| lifecycle scaling remains unclaimed | `"not_claimed"` | == not_claimed | yes |
| native-scale baseline freeze remains blocked | `"not_authorized"` | == not_authorized | yes |

## Next

Upload the stable `cra_432g` folder to EBRAINS and run the emitted JobManager command.
