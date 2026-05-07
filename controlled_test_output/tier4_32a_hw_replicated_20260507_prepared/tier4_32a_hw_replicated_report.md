# Tier 4.32a-hw-replicated - Replicated-Shard MCPL-First EBRAINS Scale Stress

- Generated: `2026-05-07T00:45:04+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Runner revision: `tier4_32a_hw_replicated_shard_stress_20260507_0001`

## Claim Boundary

Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.

## Summary

- upload_package: `cra_432a_rep`
- upload_bundle: `/Users/james/JKS:CRA/controlled_test_output/tier4_32a_hw_replicated_20260507_prepared/ebrains_upload_bundle/cra_432a_rep`
- stable_upload_folder: `/Users/james/JKS:CRA/ebrains_jobs/cra_432a_rep`
- job_command: `cra_432a_rep/experiments/tier4_32a_hw_replicated_shard_stress.py --mode run-hardware --output-dir tier4_32a_replicated_job_output`
- what_i_need_from_user: `Upload `cra_432a_rep` to EBRAINS/JobManager and run the emitted command.`
- scope: `['point_08c_dual_shard', 'point_12c_triple_shard', 'point_16c_quad_shard']`
- core_map: `{'shard_0': {'context': 1, 'route': 2, 'memory': 3, 'learning': 4}, 'shard_1': {'context': 5, 'route': 6, 'memory': 7, 'learning': 8}, 'shard_2': {'context': 9, 'route': 10, 'memory': 11, 'learning': 12}, 'shard_3': {'context': 13, 'route': 14, 'memory': 15, 'learning': 16}}`
- claim_boundary: `Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.32a prerequisite passed | `"pass"` | == pass | yes |
| Tier 4.32a-r1 protocol repair passed | `"pass"` | == pass | yes |
| Tier 4.32a-hw single-shard hardware pass ingested | `"pass"` | == pass | yes |
| MCPL replicated source checks pass | `"pass"` | == pass | yes |
| runner and dependencies py_compile | `"pass"` | == pass | yes |
| upload bundle created | `"/Users/james/JKS:CRA/controlled_test_output/tier4_32a_hw_replicated_20260507_prepared/ebrains_upload_bundle/cra_432a_rep"` | exists | yes |
| stable upload folder created | `"/Users/james/JKS:CRA/ebrains_jobs/cra_432a_rep"` | exists | yes |
| run-hardware command emitted | `"cra_432a_rep/experiments/tier4_32a_hw_replicated_shard_stress.py --mode run-hardware --output-dir tier4_32a_replicated_job_output"` | contains --mode run-hardware | yes |
| bundle includes MCPL_SHARD_ID build flag | `"MCPL_SHARD_ID"` | present | yes |
| bundle includes shard-aware MCPL key | `"MAKE_MCPL_KEY_SHARD"` | present | yes |
| bundle includes value/meta MCPL replies | `"MCPL_MSG_LOOKUP_REPLY_META"` | present | yes |
| bundle drops wrong-shard requests | `"shard_id != (CRA_MCPL_SHARD_ID"` | present | yes |
| multi-chip remains nonclaim | `"single_chip_only"` | == single_chip_only | yes |
| native-scale baseline freeze remains blocked | `"not_authorized"` | == not_authorized | yes |

## Next

Upload the stable `cra_432a_rep` folder to EBRAINS and run the emitted JobManager command.
