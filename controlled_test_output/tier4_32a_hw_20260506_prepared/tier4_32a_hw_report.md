# Tier 4.32a-hw - Single-Shard MCPL-First EBRAINS Scale Stress

- Generated: `2026-05-06T23:37:49+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Runner revision: `tier4_32a_hw_single_shard_scale_stress_20260506_0001`

## Claim Boundary

Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.

## Summary

- upload_package: `cra_432a_hw`
- upload_bundle: `/Users/james/JKS:CRA/controlled_test_output/tier4_32a_hw_20260506_prepared/ebrains_upload_bundle/cra_432a_hw`
- stable_upload_folder: `/Users/james/JKS:CRA/ebrains_jobs/cra_432a_hw`
- job_command: `cra_432a_hw/experiments/tier4_32a_hw_single_shard_scale_stress.py --mode run-hardware --output-dir tier4_32a_hw_job_output`
- what_i_need_from_user: `Upload `cra_432a_hw` to EBRAINS/JobManager and run the emitted command.`
- scope: `['point_04c_reference', 'point_05c_lifecycle']`
- claim_boundary: `Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.32a prerequisite passed | `"pass"` | == pass | yes |
| Tier 4.32a-r1 protocol repair passed | `"pass"` | == pass | yes |
| MCPL repair source checks pass | `"pass"` | == pass | yes |
| runner and dependencies py_compile | `"pass"` | == pass | yes |
| upload bundle created | `"/Users/james/JKS:CRA/controlled_test_output/tier4_32a_hw_20260506_prepared/ebrains_upload_bundle/cra_432a_hw"` | exists | yes |
| stable upload folder created | `"/Users/james/JKS:CRA/ebrains_jobs/cra_432a_hw"` | exists | yes |
| run-hardware command emitted | `"cra_432a_hw/experiments/tier4_32a_hw_single_shard_scale_stress.py --mode run-hardware --output-dir tier4_32a_hw_job_output"` | contains --mode run-hardware | yes |
| bundle includes shard-aware MCPL key | `"MCPL_KEY_SHARD_SHIFT"` | present | yes |
| bundle includes value/meta MCPL replies | `"MCPL_MSG_LOOKUP_REPLY_META"` | present | yes |
| bundle receive no hardcoded confidence shortcut | `"cra_state_lookup_receive(seq_id, value, FP_ONE, 1);"` | absent | yes |
| replicated stress remains blocked | `"single_shard_only"` | == single_shard_only | yes |
| native-scale baseline freeze remains blocked | `"not_authorized"` | == not_authorized | yes |

## Next

Upload the stable `cra_432a_hw` folder to EBRAINS and run the emitted JobManager command.
