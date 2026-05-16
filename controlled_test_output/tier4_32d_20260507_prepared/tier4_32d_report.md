# Tier 4.32d - Two-Chip Split-Role Single-Shard MCPL Lookup Smoke

- Generated: `2026-05-07T03:27:14+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Runner revision: `tier4_32d_interchip_mcpl_smoke_20260507_0001`

## Claim Boundary

Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.

## Summary

- upload_package: `cra_432d`
- upload_bundle: `<repo>/controlled_test_output/tier4_32d_20260507_prepared/ebrains_upload_bundle/cra_432d`
- stable_upload_folder: `<repo>/ebrains_jobs/cra_432d`
- job_command: `cra_432d/experiments/tier4_32d_interchip_mcpl_smoke.py --mode run-hardware --output-dir tier4_32d_job_output`
- what_i_need_from_user: `Upload `cra_432d` to EBRAINS/JobManager and run the emitted command.`
- source_chip: `{'x': 0, 'y': 0}`
- remote_chip: `{'x': 1, 'y': 0}`
- event_count: `32`
- expected_lookups: `96`
- claim_boundary: `Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.32c inter-chip contract passed | `"pass"` | == pass | yes |
| Tier 4.32d-r0 route audit passed | `"pass"` | == pass | yes |
| Tier 4.32d-r1 route repair/local QA passed | `"pass"` | == pass | yes |
| inter-chip route source checks pass | `"pass"` | == pass | yes |
| runner and dependencies py_compile | `"pass"` | == pass | yes |
| upload bundle created | `"<repo>/controlled_test_output/tier4_32d_20260507_prepared/ebrains_upload_bundle/cra_432d"` | exists | yes |
| stable upload folder created | `"<repo>/ebrains_jobs/cra_432d"` | exists | yes |
| run-hardware command emitted | `"cra_432d/experiments/tier4_32d_interchip_mcpl_smoke.py --mode run-hardware --output-dir tier4_32d_job_output"` | contains --mode run-hardware | yes |
| bundle Makefile exposes request link route | `"MCPL_INTERCHIP_REQUEST_LINK_ROUTE"` | present | yes |
| bundle Makefile exposes reply link route | `"MCPL_INTERCHIP_REPLY_LINK_ROUTE"` | present | yes |
| bundle installs outbound request route | `"CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE"` | present | yes |
| bundle installs outbound reply route | `"CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE"` | present | yes |
| two-chip smoke only | `{"remote": {"x": 1, "y": 0}, "source": {"x": 0, "y": 0}}` | predeclared | yes |
| true two-partition learning remains blocked | `"blocked"` | == blocked | yes |
| native-scale baseline freeze remains blocked | `"not_authorized"` | == not_authorized | yes |

## Next

Upload the stable `cra_432d` folder to EBRAINS and run the emitted JobManager command.
