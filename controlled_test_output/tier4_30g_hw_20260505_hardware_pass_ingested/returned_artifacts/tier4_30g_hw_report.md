# Tier 4.30g Lifecycle Task-Benefit / Resource Bridge Hardware Findings

- Generated: `2026-05-06T03:23:56+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Runner revision: `tier4_30g_lifecycle_task_benefit_resource_bridge_20260506_0001`

## Claim Boundary

Tier 4.30g hardware tests a host-ferried lifecycle task-benefit/resource bridge. It is not autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not a lifecycle baseline freeze.

## Summary

- upload_package: `cra_430g`
- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.242.97`
- profile_builds_passed: `True`
- profile_loads_passed: `True`
- task_status: `pass`
- sham_modes: `['enabled', 'fixed_static_pool_control', 'random_event_replay_control', 'active_mask_shuffle_control', 'no_trophic_pressure_control', 'no_dopamine_or_plasticity_control']`
- claim_boundary: `Hardware task-benefit/resource bridge only; not autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip scaling, and not a lifecycle baseline freeze.`
- next_step_if_passed: `Ingest returned artifacts, then decide whether the lifecycle-native baseline can freeze or needs a stronger task gate.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `"tier4_30g_lifecycle_task_benefit_resource_bridge_20260506_0001"` | expected current source | yes |
| runtime source checks pass | `"pass"` | == pass | yes |
| main.c host syntax check pass | `"pass"` | == pass | yes |
| all five profile builds pass | `{"context": "pass", "learning": "pass", "lifecycle": "pass", "memory": "pass", "route": "pass"}` | all == pass | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spy...` | status == pass and hostname acquired | yes |
| all five profile loads pass | `{"context": "pass", "learning": "pass", "lifecycle": "pass", "memory": "pass", "route": "pass"}` | all == pass | yes |
| lifecycle task-benefit bridge pass | `"pass"` | == pass | yes |
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
| enabled lifecycle reset acknowledged | `true` | == True | yes |
| enabled lifecycle init succeeded | `true` | == True | yes |
| enabled sham mode command succeeded | `true` | == True | yes |
| enabled successful event command count | `32` | == 32 | yes |
| enabled failed event command count | `0` | == 0 | yes |
| enabled lifecycle schema_version | `1` | == 1 | yes |
| enabled lifecycle sham_mode | `0` | == 0 | yes |
| enabled lifecycle pool_size | `8` | == 8 | yes |
| enabled lifecycle founder_count | `2` | == 2 | yes |
| enabled lifecycle active_count | `6` | == 6 | yes |
| enabled lifecycle inactive_count | `2` | == 2 | yes |
| enabled lifecycle active_mask_bits | `63` | == 63 | yes |
| enabled lifecycle attempted_event_count | `32` | == 32 | yes |
| enabled lifecycle lifecycle_event_count | `32` | == 32 | yes |
| enabled lifecycle cleavage_count | `4` | == 4 | yes |
| enabled lifecycle adult_birth_count | `4` | == 4 | yes |
| enabled lifecycle death_count | `4` | == 4 | yes |
| enabled lifecycle maturity_count | `4` | == 4 | yes |
| enabled lifecycle trophic_update_count | `16` | == 16 | yes |
| enabled lifecycle invalid_event_count | `0` | == 0 | yes |
| enabled lifecycle lineage_checksum | `105428` | == 105428 | yes |
| enabled lifecycle trophic_checksum | `466851` | == 466851 | yes |
| enabled lifecycle payload_len | `68` | == 68 | yes |
| enabled bridge gate hardware | `1` | == 1 | yes |
| enabled task core resets | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| enabled context write | `true` | == True | yes |
| enabled route write | `true` | == True | yes |
| enabled memory bridge write | `true` | == True | yes |
| enabled memory bridge value | `1` | >= 1 | yes |
| enabled schedule uploads | `24` | == 24 | yes |
| enabled run_continuous commands | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| enabled pause commands | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| enabled final reads | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| enabled pending_created | `24` | == 24 | yes |
| enabled pending_matured | `24` | == 24 | yes |
| enabled active_pending cleared | `0` | == 0 | yes |
| enabled readout weight near reference | `32768` | within +/- 8192 of 33024 | yes |
| enabled readout bias near reference | `0` | within +/- 8192 of -256 | yes |
| enabled lookup_requests | `72` | == 72 | yes |
| enabled lookup_replies | `72` | == 72 | yes |
| enabled stale replies zero | `0` | == 0 | yes |
| enabled timeouts zero | `0` | == 0 | yes |
| fixed_static_pool_control lifecycle reset acknowledged | `true` | == True | yes |
| fixed_static_pool_control lifecycle init succeeded | `true` | == True | yes |
| fixed_static_pool_control sham mode command succeeded | `true` | == True | yes |
| fixed_static_pool_control successful event command count | `19` | == 19 | yes |
| fixed_static_pool_control failed event command count | `13` | == 13 | yes |
| fixed_static_pool_control lifecycle schema_version | `1` | == 1 | yes |
| fixed_static_pool_control lifecycle sham_mode | `1` | == 1 | yes |
| fixed_static_pool_control lifecycle pool_size | `8` | == 8 | yes |
| fixed_static_pool_control lifecycle founder_count | `2` | == 2 | yes |
| fixed_static_pool_control lifecycle active_count | `2` | == 2 | yes |
| fixed_static_pool_control lifecycle inactive_count | `6` | == 6 | yes |
| fixed_static_pool_control lifecycle active_mask_bits | `3` | == 3 | yes |
| fixed_static_pool_control lifecycle attempted_event_count | `32` | == 32 | yes |
| fixed_static_pool_control lifecycle lifecycle_event_count | `19` | == 19 | yes |
| fixed_static_pool_control lifecycle cleavage_count | `0` | == 0 | yes |
| fixed_static_pool_control lifecycle adult_birth_count | `0` | == 0 | yes |
| fixed_static_pool_control lifecycle death_count | `0` | == 0 | yes |
| fixed_static_pool_control lifecycle maturity_count | `4` | == 4 | yes |
| fixed_static_pool_control lifecycle trophic_update_count | `3` | == 3 | yes |
| fixed_static_pool_control lifecycle invalid_event_count | `13` | == 13 | yes |
| fixed_static_pool_control lifecycle lineage_checksum | `5722` | == 5722 | yes |
| fixed_static_pool_control lifecycle trophic_checksum | `151469` | == 151469 | yes |
| fixed_static_pool_control lifecycle payload_len | `68` | == 68 | yes |
| fixed_static_pool_control bridge gate hardware | `0` | == 0 | yes |
| fixed_static_pool_control task core resets | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| fixed_static_pool_control context write | `true` | == True | yes |
| fixed_static_pool_control route write | `true` | == True | yes |
| fixed_static_pool_control memory bridge write | `true` | == True | yes |
| fixed_static_pool_control memory bridge value | `1` | >= 1 | yes |
| fixed_static_pool_control schedule uploads | `24` | == 24 | yes |
| fixed_static_pool_control run_continuous commands | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| fixed_static_pool_control pause commands | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| fixed_static_pool_control final reads | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| fixed_static_pool_control pending_created | `24` | == 24 | yes |
| fixed_static_pool_control pending_matured | `24` | == 24 | yes |
| fixed_static_pool_control active_pending cleared | `0` | == 0 | yes |
| fixed_static_pool_control readout weight near reference | `0` | within +/- 8192 of 0 | yes |
| fixed_static_pool_control readout bias near reference | `-4936` | within +/- 8192 of -7426 | yes |
| fixed_static_pool_control lookup_requests | `72` | == 72 | yes |
| fixed_static_pool_control lookup_replies | `72` | == 72 | yes |
| fixed_static_pool_control stale replies zero | `0` | == 0 | yes |
| fixed_static_pool_control timeouts zero | `0` | == 0 | yes |
| random_event_replay_control lifecycle reset acknowledged | `true` | == True | yes |
| random_event_replay_control lifecycle init succeeded | `true` | == True | yes |
| random_event_replay_control sham mode command succeeded | `true` | == True | yes |
| random_event_replay_control successful event command count | `2` | == 2 | yes |
| random_event_replay_control failed event command count | `30` | == 30 | yes |
| random_event_replay_control lifecycle schema_version | `1` | == 1 | yes |
| random_event_replay_control lifecycle sham_mode | `2` | == 2 | yes |
| random_event_replay_control lifecycle pool_size | `8` | == 8 | yes |
| random_event_replay_control lifecycle founder_count | `2` | == 2 | yes |
| random_event_replay_control lifecycle active_count | `0` | == 0 | yes |
| random_event_replay_control lifecycle inactive_count | `8` | == 8 | yes |
| random_event_replay_control lifecycle active_mask_bits | `0` | == 0 | yes |
| random_event_replay_control lifecycle attempted_event_count | `32` | == 32 | yes |
| random_event_replay_control lifecycle lifecycle_event_count | `2` | == 2 | yes |
| random_event_replay_control lifecycle cleavage_count | `0` | == 0 | yes |
| random_event_replay_control lifecycle adult_birth_count | `0` | == 0 | yes |
| random_event_replay_control lifecycle death_count | `2` | == 2 | yes |
| random_event_replay_control lifecycle maturity_count | `0` | == 0 | yes |
| random_event_replay_control lifecycle trophic_update_count | `0` | == 0 | yes |
| random_event_replay_control lifecycle invalid_event_count | `30` | == 30 | yes |
| random_event_replay_control lifecycle lineage_checksum | `6170` | == 6170 | yes |
| random_event_replay_control lifecycle trophic_checksum | `98304` | == 98304 | yes |
| random_event_replay_control lifecycle payload_len | `68` | == 68 | yes |
| random_event_replay_control bridge gate hardware | `0` | == 0 | yes |
| random_event_replay_control task core resets | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| random_event_replay_control context write | `true` | == True | yes |
| random_event_replay_control route write | `true` | == True | yes |
| random_event_replay_control memory bridge write | `true` | == True | yes |
| random_event_replay_control memory bridge value | `1` | >= 1 | yes |
| random_event_replay_control schedule uploads | `24` | == 24 | yes |
| random_event_replay_control run_continuous commands | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| random_event_replay_control pause commands | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| random_event_replay_control final reads | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| random_event_replay_control pending_created | `24` | == 24 | yes |
| random_event_replay_control pending_matured | `24` | == 24 | yes |
| random_event_replay_control active_pending cleared | `0` | == 0 | yes |
| random_event_replay_control readout weight near reference | `0` | within +/- 8192 of 0 | yes |
| random_event_replay_control readout bias near reference | `-4936` | within +/- 8192 of -7426 | yes |
| random_event_replay_control lookup_requests | `72` | == 72 | yes |
| random_event_replay_control lookup_replies | `72` | == 72 | yes |
| random_event_replay_control stale replies zero | `0` | == 0 | yes |
| random_event_replay_control timeouts zero | `0` | == 0 | yes |
| active_mask_shuffle_control lifecycle reset acknowledged | `true` | == True | yes |
| active_mask_shuffle_control lifecycle init succeeded | `true` | == True | yes |
| active_mask_shuffle_control sham mode command succeeded | `true` | == True | yes |
| active_mask_shuffle_control successful event command count | `3` | == 3 | yes |
| active_mask_shuffle_control failed event command count | `29` | == 29 | yes |
| active_mask_shuffle_control lifecycle schema_version | `1` | == 1 | yes |
| active_mask_shuffle_control lifecycle sham_mode | `3` | == 3 | yes |
| active_mask_shuffle_control lifecycle pool_size | `8` | == 8 | yes |
| active_mask_shuffle_control lifecycle founder_count | `2` | == 2 | yes |
| active_mask_shuffle_control lifecycle active_count | `0` | == 0 | yes |
| active_mask_shuffle_control lifecycle inactive_count | `8` | == 8 | yes |
| active_mask_shuffle_control lifecycle active_mask_bits | `0` | == 0 | yes |
| active_mask_shuffle_control lifecycle attempted_event_count | `32` | == 32 | yes |
| active_mask_shuffle_control lifecycle lifecycle_event_count | `3` | == 3 | yes |
| active_mask_shuffle_control lifecycle cleavage_count | `0` | == 0 | yes |
| active_mask_shuffle_control lifecycle adult_birth_count | `0` | == 0 | yes |
| active_mask_shuffle_control lifecycle death_count | `2` | == 2 | yes |
| active_mask_shuffle_control lifecycle maturity_count | `0` | == 0 | yes |
| active_mask_shuffle_control lifecycle trophic_update_count | `1` | == 1 | yes |
| active_mask_shuffle_control lifecycle invalid_event_count | `29` | == 29 | yes |
| active_mask_shuffle_control lifecycle lineage_checksum | `6170` | == 6170 | yes |
| active_mask_shuffle_control lifecycle trophic_checksum | `102480` | == 102480 | yes |
| active_mask_shuffle_control lifecycle payload_len | `68` | == 68 | yes |
| active_mask_shuffle_control bridge gate hardware | `0` | == 0 | yes |
| active_mask_shuffle_control task core resets | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| active_mask_shuffle_control context write | `true` | == True | yes |
| active_mask_shuffle_control route write | `true` | == True | yes |
| active_mask_shuffle_control memory bridge write | `true` | == True | yes |
| active_mask_shuffle_control memory bridge value | `1` | >= 1 | yes |
| active_mask_shuffle_control schedule uploads | `24` | == 24 | yes |
| active_mask_shuffle_control run_continuous commands | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| active_mask_shuffle_control pause commands | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| active_mask_shuffle_control final reads | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| active_mask_shuffle_control pending_created | `24` | == 24 | yes |
| active_mask_shuffle_control pending_matured | `24` | == 24 | yes |
| active_mask_shuffle_control active_pending cleared | `0` | == 0 | yes |
| active_mask_shuffle_control readout weight near reference | `0` | within +/- 8192 of 0 | yes |
| active_mask_shuffle_control readout bias near reference | `-4936` | within +/- 8192 of -7426 | yes |
| active_mask_shuffle_control lookup_requests | `72` | == 72 | yes |
| active_mask_shuffle_control lookup_replies | `72` | == 72 | yes |
| active_mask_shuffle_control stale replies zero | `0` | == 0 | yes |
| active_mask_shuffle_control timeouts zero | `0` | == 0 | yes |
| no_trophic_pressure_control lifecycle reset acknowledged | `true` | == True | yes |
| no_trophic_pressure_control lifecycle init succeeded | `true` | == True | yes |
| no_trophic_pressure_control sham mode command succeeded | `true` | == True | yes |
| no_trophic_pressure_control successful event command count | `32` | == 32 | yes |
| no_trophic_pressure_control failed event command count | `0` | == 0 | yes |
| no_trophic_pressure_control lifecycle schema_version | `1` | == 1 | yes |
| no_trophic_pressure_control lifecycle sham_mode | `5` | == 5 | yes |
| no_trophic_pressure_control lifecycle pool_size | `8` | == 8 | yes |
| no_trophic_pressure_control lifecycle founder_count | `2` | == 2 | yes |
| no_trophic_pressure_control lifecycle active_count | `6` | == 6 | yes |
| no_trophic_pressure_control lifecycle inactive_count | `2` | == 2 | yes |
| no_trophic_pressure_control lifecycle active_mask_bits | `63` | == 63 | yes |
| no_trophic_pressure_control lifecycle attempted_event_count | `32` | == 32 | yes |
| no_trophic_pressure_control lifecycle lifecycle_event_count | `32` | == 32 | yes |
| no_trophic_pressure_control lifecycle cleavage_count | `4` | == 4 | yes |
| no_trophic_pressure_control lifecycle adult_birth_count | `4` | == 4 | yes |
| no_trophic_pressure_control lifecycle death_count | `4` | == 4 | yes |
| no_trophic_pressure_control lifecycle maturity_count | `4` | == 4 | yes |
| no_trophic_pressure_control lifecycle trophic_update_count | `16` | == 16 | yes |
| no_trophic_pressure_control lifecycle invalid_event_count | `0` | == 0 | yes |
| no_trophic_pressure_control lifecycle lineage_checksum | `105428` | == 105428 | yes |
| no_trophic_pressure_control lifecycle trophic_checksum | `336384` | == 336384 | yes |
| no_trophic_pressure_control lifecycle payload_len | `68` | == 68 | yes |
| no_trophic_pressure_control bridge gate hardware | `0` | == 0 | yes |
| no_trophic_pressure_control task core resets | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| no_trophic_pressure_control context write | `true` | == True | yes |
| no_trophic_pressure_control route write | `true` | == True | yes |
| no_trophic_pressure_control memory bridge write | `true` | == True | yes |
| no_trophic_pressure_control memory bridge value | `1` | >= 1 | yes |
| no_trophic_pressure_control schedule uploads | `24` | == 24 | yes |
| no_trophic_pressure_control run_continuous commands | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| no_trophic_pressure_control pause commands | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| no_trophic_pressure_control final reads | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| no_trophic_pressure_control pending_created | `24` | == 24 | yes |
| no_trophic_pressure_control pending_matured | `24` | == 24 | yes |
| no_trophic_pressure_control active_pending cleared | `0` | == 0 | yes |
| no_trophic_pressure_control readout weight near reference | `0` | within +/- 8192 of 0 | yes |
| no_trophic_pressure_control readout bias near reference | `-4936` | within +/- 8192 of -7426 | yes |
| no_trophic_pressure_control lookup_requests | `72` | == 72 | yes |
| no_trophic_pressure_control lookup_replies | `72` | == 72 | yes |
| no_trophic_pressure_control stale replies zero | `0` | == 0 | yes |
| no_trophic_pressure_control timeouts zero | `0` | == 0 | yes |
| no_dopamine_or_plasticity_control lifecycle reset acknowledged | `true` | == True | yes |
| no_dopamine_or_plasticity_control lifecycle init succeeded | `true` | == True | yes |
| no_dopamine_or_plasticity_control sham mode command succeeded | `true` | == True | yes |
| no_dopamine_or_plasticity_control successful event command count | `32` | == 32 | yes |
| no_dopamine_or_plasticity_control failed event command count | `0` | == 0 | yes |
| no_dopamine_or_plasticity_control lifecycle schema_version | `1` | == 1 | yes |
| no_dopamine_or_plasticity_control lifecycle sham_mode | `6` | == 6 | yes |
| no_dopamine_or_plasticity_control lifecycle pool_size | `8` | == 8 | yes |
| no_dopamine_or_plasticity_control lifecycle founder_count | `2` | == 2 | yes |
| no_dopamine_or_plasticity_control lifecycle active_count | `6` | == 6 | yes |
| no_dopamine_or_plasticity_control lifecycle inactive_count | `2` | == 2 | yes |
| no_dopamine_or_plasticity_control lifecycle active_mask_bits | `63` | == 63 | yes |
| no_dopamine_or_plasticity_control lifecycle attempted_event_count | `32` | == 32 | yes |
| no_dopamine_or_plasticity_control lifecycle lifecycle_event_count | `32` | == 32 | yes |
| no_dopamine_or_plasticity_control lifecycle cleavage_count | `4` | == 4 | yes |
| no_dopamine_or_plasticity_control lifecycle adult_birth_count | `4` | == 4 | yes |
| no_dopamine_or_plasticity_control lifecycle death_count | `4` | == 4 | yes |
| no_dopamine_or_plasticity_control lifecycle maturity_count | `4` | == 4 | yes |
| no_dopamine_or_plasticity_control lifecycle trophic_update_count | `16` | == 16 | yes |
| no_dopamine_or_plasticity_control lifecycle invalid_event_count | `0` | == 0 | yes |
| no_dopamine_or_plasticity_control lifecycle lineage_checksum | `105428` | == 105428 | yes |
| no_dopamine_or_plasticity_control lifecycle trophic_checksum | `457850` | == 457850 | yes |
| no_dopamine_or_plasticity_control lifecycle payload_len | `68` | == 68 | yes |
| no_dopamine_or_plasticity_control bridge gate hardware | `0` | == 0 | yes |
| no_dopamine_or_plasticity_control task core resets | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| no_dopamine_or_plasticity_control context write | `true` | == True | yes |
| no_dopamine_or_plasticity_control route write | `true` | == True | yes |
| no_dopamine_or_plasticity_control memory bridge write | `true` | == True | yes |
| no_dopamine_or_plasticity_control memory bridge value | `1` | >= 1 | yes |
| no_dopamine_or_plasticity_control schedule uploads | `24` | == 24 | yes |
| no_dopamine_or_plasticity_control run_continuous commands | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| no_dopamine_or_plasticity_control pause commands | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| no_dopamine_or_plasticity_control final reads | `{"context": true, "learning": true, "memory": true, "route": true}` | all True | yes |
| no_dopamine_or_plasticity_control pending_created | `24` | == 24 | yes |
| no_dopamine_or_plasticity_control pending_matured | `24` | == 24 | yes |
| no_dopamine_or_plasticity_control active_pending cleared | `0` | == 0 | yes |
| no_dopamine_or_plasticity_control readout weight near reference | `0` | within +/- 8192 of 0 | yes |
| no_dopamine_or_plasticity_control readout bias near reference | `-4936` | within +/- 8192 of -7426 | yes |
| no_dopamine_or_plasticity_control lookup_requests | `72` | == 72 | yes |
| no_dopamine_or_plasticity_control lookup_replies | `72` | == 72 | yes |
| no_dopamine_or_plasticity_control stale replies zero | `0` | == 0 | yes |
| no_dopamine_or_plasticity_control timeouts zero | `0` | == 0 | yes |
| enabled hardware mode passed | `"pass"` | == pass | yes |
| all control hardware modes passed | `{"active_mask_shuffle_control": "pass", "fixed_static_pool_control": "pass", "no_dopamine_or_plasticity_control": "pass", "no_trophic_pre...` | all == pass | yes |
| enabled hardware bridge gate open | `1` | == 1 | yes |
| control hardware bridge gates closed | `[0, 0, 0, 0, 0]` | all == 0 | yes |
| resource accounting returned | `true` | == True | yes |
| no unhandled hardware exception | `true` | == True | yes |
| synthetic fallback zero | `0` | == 0 | yes |
