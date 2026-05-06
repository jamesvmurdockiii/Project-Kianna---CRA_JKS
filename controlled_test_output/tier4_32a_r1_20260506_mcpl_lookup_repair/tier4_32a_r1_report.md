# Tier 4.32a-r1 MCPL Lookup Repair

- Generated: `2026-05-06T23:17:55+00:00`
- Status: **PASS**
- Mode: `local-runtime-repair`
- Runner revision: `tier4_32a_r1_mcpl_lookup_repair_20260506_0001`

## Claim Boundary

Tier 4.32a-r1 is local source/runtime evidence that the custom runtime now has a confidence-bearing, shard-aware MCPL lookup path with behavior-backed confidence controls. It is not EBRAINS hardware evidence, not speedup evidence, not replicated-shard scale proof, not multi-chip proof, not static reef partitioning, and not a baseline freeze.

## Summary

- Criteria: `14/14`
- MCPL-first single-shard hardware stress: `authorized_next_single_shard_hardware_stress`
- Replicated 8/12/16-core stress: `still_blocked_until_single_shard_hardware_stress_passes`
- Native scale baseline freeze: `not_authorized`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.32a-r0 prerequisite passed | `pass` | == pass | yes |
| source protocol tokens present | `[{"file": "coral_reef_spinnaker/spinnaker_runtime/src/config.h", "present": true, "purpose": "MCPL key has explicit shard identity", "token": "shard_id (4) | seq_id (12)"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/config.h", "present": true, "purpose": "value reply packet type exists", "token": "MCPL_MSG_LOOKUP_REPLY_VALUE"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/config.h", "present": true, "purpose": "confidence/meta reply packet type exists", "token": "MCPL_MSG_LOOKUP_REPLY_META"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/config.h", "present": true, "purpose": "hit/status/confidence packing is centralized", "token": "PACK_MCPL_LOOKUP_META"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/config.h", "present": true, "purpose": "receiver can decode shard identity", "token": "EXTRACT_MCPL_SHARD_ID"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h", "present": true, "purpose": "learning lookup table can track shard-specific pending entries", "token": "cra_state_lookup_send_shard"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.h", "present": true, "purpose": "tests can read shard-specific results without ambiguity", "token": "cra_state_lookup_get_result_shard"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c", "present": true, "purpose": "MCPL path is compile-time selectable instead of #if 0 dead code", "token": "#ifdef CRA_USE_MCPL_LOOKUP"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c", "present": true, "purpose": "state core can send value/meta replies with shard identity", "token": "cra_state_mcpl_lookup_send_reply_shard"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c", "present": true, "purpose": "learning core accepts value packet", "token": "_lookup_receive_mcpl_value"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c", "present": true, "purpose": "learning core accepts confidence/meta packet", "token": "_lookup_receive_mcpl_meta"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c", "present": true, "purpose": "learning core decodes meta reply packet", "token": "MCPL_MSG_LOOKUP_REPLY_META"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c", "present": true, "purpose": "runtime can compile shard-specific images", "token": "CRA_MCPL_SHARD_ID"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/Makefile", "present": true, "purpose": "Makefile exposes MCPL shard id for hardware builds", "token": "MCPL_SHARD_ID ?= 0"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/Makefile", "present": true, "purpose": "local MCPL protocol contract target exists", "token": "test-mcpl-lookup-contract"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/Makefile", "present": true, "purpose": "local MCPL behavior target exists", "token": "test-four-core-mcpl-local"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/tests/test_mcpl_lookup_contract.c", "present": true, "purpose": "cross-talk regression is tested", "token": "shard_id prevents identical seq/type cross-talk"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/tests/test_mcpl_lookup_contract.c", "present": true, "purpose": "wrong-shard negative control is tested", "token": "wrong-shard packets cannot complete pending lookup"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/tests/test_four_core_mcpl_local.c", "present": true, "purpose": "zero-confidence behavior passes through MCPL", "token": "MCPL zero-confidence path blocks learning"}, {"file": "coral_reef_spinnaker/spinnaker_runtime/tests/test_four_core_mcpl_local.c", "present": true, "purpose": "half-confidence behavior passes through MCPL", "token": "MCPL half-confidence path scales learning"}]` | all source checks present | yes |
| request MCPL dead-code gate removed | `True` | no #if 0 around MCPL request path | yes |
| hardcoded MCPL confidence removed | `True` | no FP_ONE/hit=1 receive shortcut | yes |
| confidence no longer ignored by reply helper | `True` | no reserved/ignored confidence in MCPL reply | yes |
| MCPL lookup contract test passed | `True` | returncode == 0 | yes |
| MCPL four-core local behavior test passed | `True` | returncode == 0 | yes |
| legacy MCPL feasibility test preserved | `True` | returncode == 0 | yes |
| SDP four-core local reference preserved | `True` | returncode == 0 | yes |
| 48-event distributed reference preserved | `True` | returncode == 0 | yes |
| profile ownership tests preserved | `True` | returncode == 0 | yes |
| lifecycle split tests preserved | `True` | returncode == 0 | yes |
| no EBRAINS package generated | `local-runtime-repair` | mode is local only | yes |
| hardware scale stress remains separate gate | `4.32a-hw required next` | not hardware evidence | yes |

## Commands

- `make -C coral_reef_spinnaker/spinnaker_runtime test-mcpl-lookup-contract` -> `0`
- `make -C coral_reef_spinnaker/spinnaker_runtime test-four-core-mcpl-local` -> `0`
- `make -C coral_reef_spinnaker/spinnaker_runtime test-mcpl-feasibility` -> `0`
- `make -C coral_reef_spinnaker/spinnaker_runtime test-four-core-local` -> `0`
- `make -C coral_reef_spinnaker/spinnaker_runtime test-four-core-48event` -> `0`
- `make -C coral_reef_spinnaker/spinnaker_runtime test-profiles` -> `0`
- `make -C coral_reef_spinnaker/spinnaker_runtime test-lifecycle-split` -> `0`

## Next Step

Prepare Tier 4.32a-hw as a single-shard MCPL-first EBRAINS hardware stress using the repaired protocol. Do not run replicated 8/12/16-core stress or freeze a native scale baseline until the single-shard hardware stress passes.
