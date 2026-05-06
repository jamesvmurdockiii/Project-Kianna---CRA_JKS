# Tier 4.30f Lifecycle Sham-Control Hardware Subset

- Generated: `2026-05-06T01:27:19+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Upload package: `cra_430f`

## Claim Boundary

Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.

## Summary

- job_command: `cra_430f/experiments/tier4_30f_lifecycle_sham_hardware_subset.py --mode run-hardware --output-dir tier4_30f_hw_job_output`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| reference sham modes generated | `["enabled", "fixed_static_pool_control", "random_event_replay_control", "active_mask_shuffle_control", "no_trophic_pressure_control", "no...` | == ['enabled', 'fixed_static_pool_control', 'random_event_replay_control', 'active_mask_shuffle_control', 'no_trophic_pressure_control', 'no_dopamine_or_plasticity_control'] | yes |
| enabled reference remains canonical_32 | `{"active_count": 6, "active_mask_bits": 63, "adult_birth_count": 4, "attempted_event_count": 32, "cleavage_count": 4, "death_count": 4, "...` | active_mask=63, lineage=105428, trophic=466851 | yes |
| local reference controls separate | `[true, true, true, true, true, true, true]` | all True | yes |
| lifecycle sham host tests pass | `"pass"` | == pass | yes |
| main.c host syntax check pass | `"pass"` | == pass | yes |
| upload bundle created | `"/Users/james/JKS:CRA/controlled_test_output/tier4_30f_hw_20260505_prepared/ebrains_upload_bundle/cra_430f"` | exists | yes |
| stable upload folder created | `"/Users/james/JKS:CRA/ebrains_jobs/cra_430f"` | exists | yes |
| run-hardware command emitted | `"cra_430f/experiments/tier4_30f_lifecycle_sham_hardware_subset.py --mode run-hardware --output-dir tier4_30f_hw_job_output"` | contains --mode run-hardware | yes |
