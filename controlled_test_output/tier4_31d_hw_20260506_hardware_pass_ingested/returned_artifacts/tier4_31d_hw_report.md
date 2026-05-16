# Tier 4.31d Native Temporal-Substrate Hardware Smoke

- Generated: `2026-05-06T19:00:23+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Runner revision: `tier4_31d_native_temporal_hardware_smoke_20260506_0003`

## Claim Boundary

Tier 4.31d is a one-board native temporal-state hardware smoke. It proves build/load/command/readback of the C-owned seven-EMA temporal subset only; it does not prove speedup, benchmark superiority, multi-chip scaling, nonlinear recurrence, replay/sleep, or full v2.2 hardware transfer.

## Summary

- hardware_target_configured: `True`
- target_method: `pyNN.spiNNaker_probe`
- hostname: `10.11.216.121`
- dest_x: `0`
- dest_y: `0`
- dest_cpu: `4`
- runtime_profile: `learning_core`
- temporal_payload_len: `48`
- scenario_statuses: `{'enabled': 'pass', 'zero_state': 'pass', 'frozen_state': 'pass', 'reset_each_update': 'pass'}`
- synthetic_fallback_used: `False`
- claim_boundary: `Tier 4.31d is a one-board native temporal-state hardware smoke. It proves build/load/command/readback of the C-owned seven-EMA temporal subset only; it does not prove speedup, benchmark superiority, multi-chip scaling, nonlinear recurrence, replay/sleep, or full v2.2 hardware transfer.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runtime temporal/profile host checks pass | `pass` | == pass | yes |
| runner py_compile pass | `0` | == 0 | yes |
| learning_core APLX build pass | `pass` | == pass | yes |
| hardware target configured | `pass` | == pass | yes |
| hardware load pass | `pass` | == pass | yes |
| temporal roundtrip pass | `pass` | == pass | yes |
| all four temporal scenarios executed | `{'enabled': 'pass', 'zero_state': 'pass', 'frozen_state': 'pass', 'reset_each_update': 'pass'}` | enabled/zero/frozen/reset all pass | yes |
| enabled schema_version matches reference | `1` | == 1 | yes |
| enabled trace_count matches reference | `7` | == 7 | yes |
| enabled sham_mode matches reference | `0` | == 0 | yes |
| enabled timescale_checksum matches reference | `1811900589` | == 1811900589 | yes |
| enabled update_count matches reference | `16` | == 16 | yes |
| enabled saturation_count matches reference | `0` | == 0 | yes |
| enabled reset_count matches reference | `0` | == 0 | yes |
| enabled input_clip_count matches reference | `0` | == 0 | yes |
| enabled trace_checksum matches reference | `2782142982` | == 2782142982 | yes |
| enabled trace_abs_sum_raw matches reference | `5086` | == 5086 | yes |
| enabled latest_input_raw matches reference | `-4096` | == -4096 | yes |
| enabled latest_novelty_raw matches reference | `-4342` | == -4342 | yes |
| enabled compact readback bytes monotonic | `864` | >= 48 and multiple of 48 | yes |
| zero_state schema_version matches reference | `1` | == 1 | yes |
| zero_state trace_count matches reference | `7` | == 7 | yes |
| zero_state sham_mode matches reference | `1` | == 1 | yes |
| zero_state timescale_checksum matches reference | `1811900589` | == 1811900589 | yes |
| zero_state update_count matches reference | `16` | == 16 | yes |
| zero_state saturation_count matches reference | `0` | == 0 | yes |
| zero_state reset_count matches reference | `1` | == 1 | yes |
| zero_state input_clip_count matches reference | `0` | == 0 | yes |
| zero_state trace_checksum matches reference | `0` | == 0 | yes |
| zero_state trace_abs_sum_raw matches reference | `0` | == 0 | yes |
| zero_state latest_input_raw matches reference | `-4096` | == -4096 | yes |
| zero_state latest_novelty_raw matches reference | `0` | == 0 | yes |
| zero_state compact readback bytes monotonic | `1776` | >= 48 and multiple of 48 | yes |
| frozen_state schema_version matches reference | `1` | == 1 | yes |
| frozen_state trace_count matches reference | `7` | == 7 | yes |
| frozen_state sham_mode matches reference | `2` | == 2 | yes |
| frozen_state timescale_checksum matches reference | `1811900589` | == 1811900589 | yes |
| frozen_state update_count matches reference | `17` | == 17 | yes |
| frozen_state saturation_count matches reference | `0` | == 0 | yes |
| frozen_state reset_count matches reference | `0` | == 0 | yes |
| frozen_state input_clip_count matches reference | `0` | == 0 | yes |
| frozen_state trace_checksum matches reference | `3255268949` | == 3255268949 | yes |
| frozen_state trace_abs_sum_raw matches reference | `17340` | == 17340 | yes |
| frozen_state latest_input_raw matches reference | `-4096` | == -4096 | yes |
| frozen_state latest_novelty_raw matches reference | `-4255` | == -4255 | yes |
| frozen_state compact readback bytes monotonic | `2736` | >= 48 and multiple of 48 | yes |
| reset_each_update schema_version matches reference | `1` | == 1 | yes |
| reset_each_update trace_count matches reference | `7` | == 7 | yes |
| reset_each_update sham_mode matches reference | `3` | == 3 | yes |
| reset_each_update timescale_checksum matches reference | `1811900589` | == 1811900589 | yes |
| reset_each_update update_count matches reference | `16` | == 16 | yes |
| reset_each_update saturation_count matches reference | `0` | == 0 | yes |
| reset_each_update reset_count matches reference | `17` | == 17 | yes |
| reset_each_update input_clip_count matches reference | `0` | == 0 | yes |
| reset_each_update trace_checksum matches reference | `2744195752` | == 2744195752 | yes |
| reset_each_update trace_abs_sum_raw matches reference | `3471` | == 3471 | yes |
| reset_each_update latest_input_raw matches reference | `-4096` | == -4096 | yes |
| reset_each_update latest_novelty_raw matches reference | `-4159` | == -4159 | yes |
| reset_each_update compact readback bytes monotonic | `3648` | >= 48 and multiple of 48 | yes |

## Artifacts

- `results_json`: `<jobmanager_tmp>`
- `report_md`: `<jobmanager_tmp>`
- `summary_csv`: `<jobmanager_tmp>`
