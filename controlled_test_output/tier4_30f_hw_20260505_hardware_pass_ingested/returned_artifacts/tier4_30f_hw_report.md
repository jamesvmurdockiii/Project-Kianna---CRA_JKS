# Tier 4.30f Lifecycle Sham-Control Hardware Subset

- Generated: `2026-05-06T01:58:36+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Upload package: `cra_430f`

## Claim Boundary

Lifecycle sham-control hardware subset only; not lifecycle task benefit, not full Tier 6.3 hardware, not speedup, not multi-chip scaling, and not a lifecycle baseline freeze.

## Summary

- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.227.9`
- profile_builds_passed: `True`
- profile_loads_passed: `True`
- task_status: `pass`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `"tier4_30f_lifecycle_sham_hardware_subset_20260505_0001"` | expected current source | yes |
| lifecycle sham host tests pass | `"pass"` | == pass | yes |
| main.c host syntax check pass | `"pass"` | == pass | yes |
| all five profile builds pass | `{"context": "pass", "learning": "pass", "lifecycle": "pass", "memory": "pass", "route": "pass"}` | all == pass | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spy...` | status == pass and hostname acquired | yes |
| all five profile loads pass | `{"context": "pass", "learning": "pass", "lifecycle": "pass", "memory": "pass", "route": "pass"}` | all == pass | yes |
| lifecycle sham-control task pass | `"pass"` | == pass | yes |
| context profile read success | `true` | == True | yes |
| context profile id | `4` | == 4 | yes |
| context final profile read success | `true` | == True | yes |
| route profile read success | `true` | == True | yes |
| route profile id | `5` | == 5 | yes |
| route final profile read success | `true` | == True | yes |
| memory profile read success | `true` | == True | yes |
| memory profile id | `6` | == 6 | yes |
| memory final profile read success | `true` | == True | yes |
| learning profile read success | `true` | == True | yes |
| learning profile id | `3` | == 3 | yes |
| learning final profile read success | `true` | == True | yes |
| lifecycle profile read success | `true` | == True | yes |
| lifecycle profile id | `7` | == 7 | yes |
| lifecycle final profile read success | `true` | == True | yes |
| context rejects direct lifecycle read | `false` | == False | yes |
| route rejects direct lifecycle read | `false` | == False | yes |
| memory rejects direct lifecycle read | `false` | == False | yes |
| learning rejects direct lifecycle read | `false` | == False | yes |
| enabled reset acknowledged | `true` | == True | yes |
| enabled lifecycle init succeeded | `true` | == True | yes |
| enabled sham mode command succeeded | `true` | == True | yes |
| enabled sham mode command readback | `0` | == 0 | yes |
| enabled successful event command count | `32` | == 32 | yes |
| enabled failed event command count | `0` | == 0 | yes |
| enabled lifecycle readback success | `true` | == True | yes |
| enabled schema version | `1` | == 1 | yes |
| enabled sham mode readback | `0` | == 0 | yes |
| enabled pool size | `8` | == 8 | yes |
| enabled founder count | `2` | == 2 | yes |
| enabled active count | `6` | == 6 | yes |
| enabled inactive count | `2` | == 2 | yes |
| enabled active mask bits | `63` | == 63 | yes |
| enabled attempted event count | `32` | == 32 | yes |
| enabled lifecycle accepted event count | `32` | == 32 | yes |
| enabled cleavage count | `4` | == 4 | yes |
| enabled adult birth count | `4` | == 4 | yes |
| enabled death count | `4` | == 4 | yes |
| enabled maturity count | `4` | == 4 | yes |
| enabled trophic update count | `16` | == 16 | yes |
| enabled invalid event count | `0` | == 0 | yes |
| enabled lineage checksum | `105428` | == 105428 | yes |
| enabled trophic checksum | `466851` | == 466851 | yes |
| enabled compact lifecycle payload length | `68` | == 68 | yes |
| fixed_static_pool_control reset acknowledged | `true` | == True | yes |
| fixed_static_pool_control lifecycle init succeeded | `true` | == True | yes |
| fixed_static_pool_control sham mode command succeeded | `true` | == True | yes |
| fixed_static_pool_control sham mode command readback | `1` | == 1 | yes |
| fixed_static_pool_control successful event command count | `19` | == 19 | yes |
| fixed_static_pool_control failed event command count | `13` | == 13 | yes |
| fixed_static_pool_control lifecycle readback success | `true` | == True | yes |
| fixed_static_pool_control schema version | `1` | == 1 | yes |
| fixed_static_pool_control sham mode readback | `1` | == 1 | yes |
| fixed_static_pool_control pool size | `8` | == 8 | yes |
| fixed_static_pool_control founder count | `2` | == 2 | yes |
| fixed_static_pool_control active count | `2` | == 2 | yes |
| fixed_static_pool_control inactive count | `6` | == 6 | yes |
| fixed_static_pool_control active mask bits | `3` | == 3 | yes |
| fixed_static_pool_control attempted event count | `32` | == 32 | yes |
| fixed_static_pool_control lifecycle accepted event count | `19` | == 19 | yes |
| fixed_static_pool_control cleavage count | `0` | == 0 | yes |
| fixed_static_pool_control adult birth count | `0` | == 0 | yes |
| fixed_static_pool_control death count | `0` | == 0 | yes |
| fixed_static_pool_control maturity count | `4` | == 4 | yes |
| fixed_static_pool_control trophic update count | `3` | == 3 | yes |
| fixed_static_pool_control invalid event count | `13` | == 13 | yes |
| fixed_static_pool_control lineage checksum | `5722` | == 5722 | yes |
| fixed_static_pool_control trophic checksum | `151469` | == 151469 | yes |
| fixed_static_pool_control compact lifecycle payload length | `68` | == 68 | yes |
| random_event_replay_control reset acknowledged | `true` | == True | yes |
| random_event_replay_control lifecycle init succeeded | `true` | == True | yes |
| random_event_replay_control sham mode command succeeded | `true` | == True | yes |
| random_event_replay_control sham mode command readback | `2` | == 2 | yes |
| random_event_replay_control successful event command count | `2` | == 2 | yes |
| random_event_replay_control failed event command count | `30` | == 30 | yes |
| random_event_replay_control lifecycle readback success | `true` | == True | yes |
| random_event_replay_control schema version | `1` | == 1 | yes |
| random_event_replay_control sham mode readback | `2` | == 2 | yes |
| random_event_replay_control pool size | `8` | == 8 | yes |
| random_event_replay_control founder count | `2` | == 2 | yes |
| random_event_replay_control active count | `0` | == 0 | yes |
| random_event_replay_control inactive count | `8` | == 8 | yes |
| random_event_replay_control active mask bits | `0` | == 0 | yes |
| random_event_replay_control attempted event count | `32` | == 32 | yes |
| random_event_replay_control lifecycle accepted event count | `2` | == 2 | yes |
| random_event_replay_control cleavage count | `0` | == 0 | yes |
| random_event_replay_control adult birth count | `0` | == 0 | yes |
| random_event_replay_control death count | `2` | == 2 | yes |
| random_event_replay_control maturity count | `0` | == 0 | yes |
| random_event_replay_control trophic update count | `0` | == 0 | yes |
| random_event_replay_control invalid event count | `30` | == 30 | yes |
| random_event_replay_control lineage checksum | `6170` | == 6170 | yes |
| random_event_replay_control trophic checksum | `98304` | == 98304 | yes |
| random_event_replay_control compact lifecycle payload length | `68` | == 68 | yes |
| active_mask_shuffle_control reset acknowledged | `true` | == True | yes |
| active_mask_shuffle_control lifecycle init succeeded | `true` | == True | yes |
| active_mask_shuffle_control sham mode command succeeded | `true` | == True | yes |
| active_mask_shuffle_control sham mode command readback | `3` | == 3 | yes |
| active_mask_shuffle_control successful event command count | `3` | == 3 | yes |
| active_mask_shuffle_control failed event command count | `29` | == 29 | yes |
| active_mask_shuffle_control lifecycle readback success | `true` | == True | yes |
| active_mask_shuffle_control schema version | `1` | == 1 | yes |
| active_mask_shuffle_control sham mode readback | `3` | == 3 | yes |
| active_mask_shuffle_control pool size | `8` | == 8 | yes |
| active_mask_shuffle_control founder count | `2` | == 2 | yes |
| active_mask_shuffle_control active count | `0` | == 0 | yes |
| active_mask_shuffle_control inactive count | `8` | == 8 | yes |
| active_mask_shuffle_control active mask bits | `0` | == 0 | yes |
| active_mask_shuffle_control attempted event count | `32` | == 32 | yes |
| active_mask_shuffle_control lifecycle accepted event count | `3` | == 3 | yes |
| active_mask_shuffle_control cleavage count | `0` | == 0 | yes |
| active_mask_shuffle_control adult birth count | `0` | == 0 | yes |
| active_mask_shuffle_control death count | `2` | == 2 | yes |
| active_mask_shuffle_control maturity count | `0` | == 0 | yes |
| active_mask_shuffle_control trophic update count | `1` | == 1 | yes |
| active_mask_shuffle_control invalid event count | `29` | == 29 | yes |
| active_mask_shuffle_control lineage checksum | `6170` | == 6170 | yes |
| active_mask_shuffle_control trophic checksum | `102480` | == 102480 | yes |
| active_mask_shuffle_control compact lifecycle payload length | `68` | == 68 | yes |
| no_trophic_pressure_control reset acknowledged | `true` | == True | yes |
| no_trophic_pressure_control lifecycle init succeeded | `true` | == True | yes |
| no_trophic_pressure_control sham mode command succeeded | `true` | == True | yes |
| no_trophic_pressure_control sham mode command readback | `5` | == 5 | yes |
| no_trophic_pressure_control successful event command count | `32` | == 32 | yes |
| no_trophic_pressure_control failed event command count | `0` | == 0 | yes |
| no_trophic_pressure_control lifecycle readback success | `true` | == True | yes |
| no_trophic_pressure_control schema version | `1` | == 1 | yes |
| no_trophic_pressure_control sham mode readback | `5` | == 5 | yes |
| no_trophic_pressure_control pool size | `8` | == 8 | yes |
| no_trophic_pressure_control founder count | `2` | == 2 | yes |
| no_trophic_pressure_control active count | `6` | == 6 | yes |
| no_trophic_pressure_control inactive count | `2` | == 2 | yes |
| no_trophic_pressure_control active mask bits | `63` | == 63 | yes |
| no_trophic_pressure_control attempted event count | `32` | == 32 | yes |
| no_trophic_pressure_control lifecycle accepted event count | `32` | == 32 | yes |
| no_trophic_pressure_control cleavage count | `4` | == 4 | yes |
| no_trophic_pressure_control adult birth count | `4` | == 4 | yes |
| no_trophic_pressure_control death count | `4` | == 4 | yes |
| no_trophic_pressure_control maturity count | `4` | == 4 | yes |
| no_trophic_pressure_control trophic update count | `16` | == 16 | yes |
| no_trophic_pressure_control invalid event count | `0` | == 0 | yes |
| no_trophic_pressure_control lineage checksum | `105428` | == 105428 | yes |
| no_trophic_pressure_control trophic checksum | `336384` | == 336384 | yes |
| no_trophic_pressure_control compact lifecycle payload length | `68` | == 68 | yes |
| no_dopamine_or_plasticity_control reset acknowledged | `true` | == True | yes |
| no_dopamine_or_plasticity_control lifecycle init succeeded | `true` | == True | yes |
| no_dopamine_or_plasticity_control sham mode command succeeded | `true` | == True | yes |
| no_dopamine_or_plasticity_control sham mode command readback | `6` | == 6 | yes |
| no_dopamine_or_plasticity_control successful event command count | `32` | == 32 | yes |
| no_dopamine_or_plasticity_control failed event command count | `0` | == 0 | yes |
| no_dopamine_or_plasticity_control lifecycle readback success | `true` | == True | yes |
| no_dopamine_or_plasticity_control schema version | `1` | == 1 | yes |
| no_dopamine_or_plasticity_control sham mode readback | `6` | == 6 | yes |
| no_dopamine_or_plasticity_control pool size | `8` | == 8 | yes |
| no_dopamine_or_plasticity_control founder count | `2` | == 2 | yes |
| no_dopamine_or_plasticity_control active count | `6` | == 6 | yes |
| no_dopamine_or_plasticity_control inactive count | `2` | == 2 | yes |
| no_dopamine_or_plasticity_control active mask bits | `63` | == 63 | yes |
| no_dopamine_or_plasticity_control attempted event count | `32` | == 32 | yes |
| no_dopamine_or_plasticity_control lifecycle accepted event count | `32` | == 32 | yes |
| no_dopamine_or_plasticity_control cleavage count | `4` | == 4 | yes |
| no_dopamine_or_plasticity_control adult birth count | `4` | == 4 | yes |
| no_dopamine_or_plasticity_control death count | `4` | == 4 | yes |
| no_dopamine_or_plasticity_control maturity count | `4` | == 4 | yes |
| no_dopamine_or_plasticity_control trophic update count | `16` | == 16 | yes |
| no_dopamine_or_plasticity_control invalid event count | `0` | == 0 | yes |
| no_dopamine_or_plasticity_control lineage checksum | `105428` | == 105428 | yes |
| no_dopamine_or_plasticity_control trophic checksum | `457850` | == 457850 | yes |
| no_dopamine_or_plasticity_control compact lifecycle payload length | `68` | == 68 | yes |
| fixed_static_pool_control separates active_mask_bits from enabled | `{"control": 3, "enabled": 63}` | control != enabled | yes |
| random_event_replay_control separates lineage_checksum from enabled | `{"control": 6170, "enabled": 105428}` | control != enabled | yes |
| active_mask_shuffle_control separates active_mask_bits from enabled | `{"control": 0, "enabled": 63}` | control != enabled | yes |
| no_trophic_pressure_control separates trophic_checksum from enabled | `{"control": 336384, "enabled": 466851}` | control != enabled | yes |
| no_dopamine_or_plasticity_control separates trophic_checksum from enabled | `{"control": 457850, "enabled": 466851}` | control != enabled | yes |
| fixed-pool suppresses mask mutation counters | `{"adult_birth": 0, "cleavage": 0, "death": 0}` | all == 0 | yes |
| enabled control remains canonical | `{"active_mask_bits": 63, "lineage_checksum": 105428, "trophic_checksum": 466851}` | matches enabled reference | yes |
| no unhandled hardware exception | `true` | == True | yes |
| synthetic fallback zero | `0` | == 0 | yes |
