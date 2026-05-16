# Tier 4.22k Spin1API Event-Symbol Discovery

- Generated: `2026-04-30T21:02:05+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Output directory: `<jobmanager_tmp>`

Tier 4.22k inspects the EBRAINS Spin1API build image and compiles a callback-symbol probe matrix. It exists because Tier 4.22i reached the raw custom-runtime layer and failed before board execution on callback event-symbol mismatch.

## Claim Boundary

- This is build-image/toolchain discovery evidence only.
- It is not a board load, not a command round-trip, not learning, not speedup, and not hardware transfer of a mechanism.
- If no real multicast receive event macro compiles, custom-runtime learning hardware is blocked until the receive path is repaired with documented Spin1API/SCAMP semantics.

## Summary

- include_dirs_found: `["/home/jovyan/spinnaker/spinnaker_tools/include"]`
- header_inventory_rows: `15`
- compiler: `/usr/bin/arm-none-eabi-gcc`
- baseline_timer_compiles: `True`
- baseline_sdp_compiles: `True`
- mc_receive_event_macros_compiling: `["MC_PACKET_RECEIVED", "MCPL_PACKET_RECEIVED"]`
- custom_runtime_learning_hardware_allowed_next: `True`
- next_step_if_passed: `Patch the custom runtime to use the compiling MC receive event macro, regenerate Tier 4.22i, then rerun board load/CMD_READ_STATE smoke.`
- next_step_if_failed: `Do not run custom-runtime learning. Inspect tier4_22k_header_inventory.csv and pick a documented alternate receive path or toolchain include fix first.`

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| runner revision current | `tier4_22k_spin1api_event_discovery_20260430_0001` | `expected current source` | yes |  |
| include dirs found | `1` | `>= 1` | yes |  |
| spin1_callback_on found in headers | `1` | `>= 1` | yes |  |
| TIMER_TICK callback probe compiles | `True` | `True` | yes |  |
| SDP_PACKET_RX callback probe compiles | `True` | `True` | yes |  |
| official MC receive symbol visible in header inventory | `["MC_PACKET_RECEIVED", "MCPL_PACKET_RECEIVED"]` | `contains MC_PACKET_RECEIVED or MCPL_PACKET_RECEIVED` | yes |  |
| real MC receive event callback probe compiles | `["MC_PACKET_RECEIVED", "MCPL_PACKET_RECEIVED"]` | `at least one real MC receive candidate compiles` | yes |  |

## Artifacts

- `environment_json`: `<jobmanager_tmp>`
- `header_inventory_csv`: `<jobmanager_tmp>`
- `spin1api_symbols_txt`: `<jobmanager_tmp>`
- `probe_matrix_csv`: `<jobmanager_tmp>`
- `probe_build_stdout`: `<jobmanager_tmp>`
- `probe_build_stderr`: `<jobmanager_tmp>`
- `manifest_json`: `<jobmanager_tmp>`
- `report_md`: `<jobmanager_tmp>`

## Official Reference Checked

- Official `spin1_api.h`: `https://github.com/SpiNNakerManchester/spinnaker_tools/blob/master/include/spin1_api.h`
- Official `spinnaker.h`: `https://github.com/SpiNNakerManchester/spinnaker_tools/blob/master/include/spinnaker.h`
- Current official source exposes `MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`; this tier checks whether the EBRAINS image exposes the same symbols.
