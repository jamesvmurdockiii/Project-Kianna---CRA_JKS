# Tier 4.22i Custom Runtime Board Round-Trip Smoke

- Generated: `2026-05-01T00:53:20+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Output directory: `<jobmanager_tmp>`

Tier 4.22i tests the custom C runtime itself on hardware: build/load the tiny `.aplx`, send `CMD_READ_STATE`, and validate the compact state packet after simple command mutations.

## Claim Boundary

- `PREPARED` means the source bundle and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means board load plus `CMD_READ_STATE` round-trip worked on real SpiNNaker.
- This is not full CRA learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22h_status: `missing`
- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.194.113`
- host_tests_passed: `True`
- hardware_target_acquisition_method: `pyNN.spiNNaker_probe`
- selected_dest_cpu: `4`
- main_syntax_check_passed: `True`
- aplx_build_status: `pass`
- app_load_status: `pass`
- command_roundtrip_status: `pass`
- read_state_schema_version: `1`
- state_after_mutation_neuron_count: `2`
- state_after_mutation_synapse_count: `1`
- custom_runtime_learning_hardware_allowed_next: `True`
- next_step_if_passed: `Tier 4.22j minimal custom-runtime closed-loop learning smoke: delayed pending/readout update on board with compact state readback.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22i_custom_runtime_roundtrip_20260430_0009` | `expected current source` | yes |
| Tier 4.22h compact-readback pass exists or fresh bundle | `missing` | `== pass OR missing in fresh EBRAINS bundle` | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spynnaker.cfg"], "reason": "no explicit hostname/config/environment target found", "status": "fail"}, {"dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.194.113", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 45.251352780964226, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.194.113"}], "dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.194.113", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 45.251352780964226, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.194.113"}` | `status == pass and hostname/IP/transceiver acquired` | yes |
| custom C host tests pass | `pass` | `== pass` | yes |
| main.c host syntax check pass | `pass` | `== pass` | yes |
| runtime official no-payload MC callback registered | `spin1_callback_on(MC_PACKET_RECEIVED` | `uses Tier 4.22k-confirmed official Spin1API enum constant` | yes |
| runtime official payload MC callback registered | `spin1_callback_on(MCPL_PACKET_RECEIVED` | `uses Tier 4.22k-confirmed official Spin1API enum constant` | yes |
| runtime legacy guessed callback names absent | `MC_PACKET_RX/MCPL_PACKET_RX absent` | `no direct brittle guessed callback names remain` | yes |
| runtime host stub mirrors confirmed EBRAINS event names | `MC_PACKET_RECEIVED/MCPL_PACKET_RECEIVED` | `local syntax guard exposes official names and omits guessed names` | yes |
| runtime SDP reply uses packed official sdp_msg_t fields | `dest_port/srce_port/dest_addr/srce_addr` | `mirrors real SARK SDP field names instead of local split x/y/cpu guesses` | yes |
| runtime deprecated split SDP fields absent | `dest_y/src_y/dest_x/src_x/src_cpu absent` | `EBRAINS SARK sdp_msg_t uses packed address/port fields` | yes |
| runtime uses official SARK memory copy API | `sark_mem_cpy` | `real spinnaker_tools exposes sark_mem_cpy, not sark_memcpy` | yes |
| runtime host stub mirrors official SARK SDP fields | `srce_port/srce_addr/sark_mem_cpy` | `local syntax guard exposes the same fields/API that EBRAINS build requires` | yes |
| runtime host sends official sdp_msg_t command header | `struct.pack("<HHIII"` | `host must place opcode in cmd_rc and use arg1/arg2/arg3 before data[]` | yes |
| runtime host parses cmd_rc before data payload | `struct.unpack_from("<HHIII", data, 10)` | `board replies expose cmd/status in cmd_rc before data[] on UDP SDP` | yes |
| runtime runtime dispatch reads cmd_rc | `msg->cmd_rc` | `Spin1API callback receives an sdp_msg_t whose data[0] follows cmd_rc/seq/args` | yes |
| runtime runtime command args use arg1-arg3 | `msg->arg1/msg->arg2/msg->arg3` | `simple CRA commands use official SDP argument fields instead of hidden data offsets` | yes |
| runtime runtime replies put cmd/status into cmd_rc | `reply->cmd_rc` | `host parser expects cmd/status in the command header and optional state bytes in data[]` | yes |
| runtime host stub mirrors command-header fields | `cmd_rc/seq/arg1/arg2/arg3` | `local syntax guard must expose the real Spin1API command header fields` | yes |
| runtime router header includes stdint directly | `#include <stdint.h>` | `router.h must not rely on indirect EBRAINS header includes for uint32_t` | yes |
| runtime router uses official SARK allocation API | `rtr_alloc/rtr_mc_set/rtr_free` | `real spinnaker_tools exposes official rtr_* router calls` | yes |
| runtime deprecated local-only router helpers absent | `sark_router_alloc/sark_router_free absent` | `local stubs must not hide EBRAINS SARK API drift` | yes |
| runtime host stub mirrors official router API | `rtr_alloc/rtr_mc_set/rtr_free` | `local syntax guard exposes official SARK router names` | yes |
| runtime hardware build uses official spinnaker_tools.mk | `spinnaker_tools.mk` | `official build chain supplies cpu_reset, build object, spin1_api library, and APLX section packing` | yes |
| runtime hardware build avoids deprecated Makefile.common include | `Makefile.common absent` | `Makefile.common inclusion lacks the app build rules needed for APLX creation` | yes |
| runtime hardware build avoids manual direct linker recipe | `no direct $(LD) object-only link` | `manual object-only link produced empty ELF without cpu_reset/startup sections on EBRAINS` | yes |
| runtime hardware output stays under build directory | `APP_OUTPUT_DIR := build/` | `runner expects build/coral_reef.aplx` | yes |
| runtime hardware build creates nested object directories | `$(OBJECTS): | $(OBJECT_DIRS)` | `spinnaker_tools.mk writes build/gnu/src/*.o and does not create nested source subdirectories itself` | yes |
| custom runtime .aplx build pass | `pass` | `== pass` | yes |
| custom runtime app load pass | `pass` | `== pass` | yes |
| CMD_READ_STATE roundtrip pass | `pass` | `== pass` | yes |
| reset command acknowledged | `True` | `True` | yes |
| birth/synapse mutation commands acknowledged | `{"birth_1": true, "birth_2": true, "synapse": true}` | `all True` | yes |
| READ_STATE schema version valid | `1` | `== 1` | yes |
| READ_STATE payload compact | `73` | `== 73` | yes |
| post-mutation neuron count visible | `2` | `>= 2` | yes |
| post-mutation synapse count visible | `1` | `>= 1` | yes |
| synthetic fallback zero | `0` | `== 0` | yes |

## Artifacts

- `environment_json`: `<jobmanager_tmp>`
- `target_acquisition_json`: `<jobmanager_tmp>`
- `host_test_stdout`: `<jobmanager_tmp>`
- `host_test_stderr`: `<jobmanager_tmp>`
- `main_syntax_stdout`: `<jobmanager_tmp>`
- `main_syntax_stderr`: `<jobmanager_tmp>`
- `aplx_build_stdout`: `<jobmanager_tmp>`
- `aplx_build_stderr`: `<jobmanager_tmp>`
- `load_result_json`: `<jobmanager_tmp>`
- `roundtrip_result_json`: `<jobmanager_tmp>`
- `manifest_json`: `<jobmanager_tmp>`
- `report_md`: `<jobmanager_tmp>`
