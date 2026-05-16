# Tier 4.30g Lifecycle Task-Benefit / Resource Bridge Hardware Findings

- Generated: `2026-05-06T03:40:20+00:00`
- Mode: `ingest`
- Status: **PASS**
- Runner revision: `tier4_30g_lifecycle_task_benefit_resource_bridge_20260506_0001`

## Claim Boundary

Ingest confirms returned EBRAINS run-hardware artifacts only; no lifecycle baseline freeze until documentation and registry promotion.

## Summary

- raw_remote_status: `pass`
- corrected_ingest_status: `pass`
- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.242.97`
- profile_builds_passed: `True`
- profile_loads_passed: `True`
- task_status: `pass`
- sham_modes: `['enabled', 'fixed_static_pool_control', 'random_event_replay_control', 'active_mask_shuffle_control', 'no_trophic_pressure_control', 'no_dopamine_or_plasticity_control']`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| hardware results json exists | `"<downloads>/tier4_30g_hw_results.json"` | exists | yes |
| hardware mode was run-hardware | `"run-hardware"` | == run-hardware | yes |
| hardware status pass | `"pass"` | == pass | yes |
| runner revision current | `"tier4_30g_lifecycle_task_benefit_resource_bridge_20260506_0001"` | == tier4_30g_lifecycle_task_benefit_resource_bridge_20260506_0001 | yes |
| returned artifacts preserved | `36` | > 0 | yes |
