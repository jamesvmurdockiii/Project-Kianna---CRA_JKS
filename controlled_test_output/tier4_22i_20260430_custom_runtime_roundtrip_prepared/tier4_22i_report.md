# Tier 4.22i Custom Runtime Board Round-Trip Smoke

- Generated: `2026-04-30T23:44:08+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared`

Tier 4.22i tests the custom C runtime itself on hardware: build/load the tiny `.aplx`, send `CMD_READ_STATE`, and validate the compact state packet after simple command mutations.

## Claim Boundary

- `PREPARED` means the source bundle and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means board load plus `CMD_READ_STATE` round-trip worked on real SpiNNaker.
- This is not full CRA learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22h_status: `pass`
- main_syntax_check_passed: `True`
- next_step_if_passed: `Run the emitted EBRAINS command and ingest returned files.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.22h compact-readback pass exists | `pass` | `== pass` | yes |
| main.c host syntax check pass | `pass` | `== pass` | yes |
| upload bundle created | `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared/ebrains_upload_bundle/cra_422r` | `exists` | yes |
| runtime source included | `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared/ebrains_upload_bundle/cra_422r/coral_reef_spinnaker/spinnaker_runtime` | `exists` | yes |
| controller source includes CMD_READ_STATE | `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared/ebrains_upload_bundle/cra_422r/coral_reef_spinnaker/python_host/colony_controller.py` | `contains CMD_READ_STATE` | yes |
| run-hardware command emitted | `cra_422r/experiments/tier4_22i_custom_runtime_roundtrip.py --mode run-hardware --output-dir tier4_22i_job_output` | `contains --mode run-hardware` | yes |
| source official no-payload MC callback registered | `spin1_callback_on(MC_PACKET_RECEIVED` | `uses Tier 4.22k-confirmed official Spin1API enum constant` | yes |
| source official payload MC callback registered | `spin1_callback_on(MCPL_PACKET_RECEIVED` | `uses Tier 4.22k-confirmed official Spin1API enum constant` | yes |
| source legacy guessed callback names absent | `MC_PACKET_RX/MCPL_PACKET_RX absent` | `no direct brittle guessed callback names remain` | yes |
| source host stub mirrors confirmed EBRAINS event names | `MC_PACKET_RECEIVED/MCPL_PACKET_RECEIVED` | `local syntax guard exposes official names and omits guessed names` | yes |
| source SDP reply uses packed official sdp_msg_t fields | `dest_port/srce_port/dest_addr/srce_addr` | `mirrors real SARK SDP field names instead of local split x/y/cpu guesses` | yes |
| source deprecated split SDP fields absent | `dest_y/src_y/dest_x/src_x/src_cpu absent` | `EBRAINS SARK sdp_msg_t uses packed address/port fields` | yes |
| source uses official SARK memory copy API | `sark_mem_cpy` | `real spinnaker_tools exposes sark_mem_cpy, not sark_memcpy` | yes |
| source host stub mirrors official SARK SDP fields | `srce_port/srce_addr/sark_mem_cpy` | `local syntax guard exposes the same fields/API that EBRAINS build requires` | yes |
| source host sends official sdp_msg_t command header | `struct.pack("<HHIII"` | `host must place opcode in cmd_rc and use arg1/arg2/arg3 before data[]` | yes |
| source host parses cmd_rc before data payload | `struct.unpack_from("<HHIII", data, 10)` | `board replies expose cmd/status in cmd_rc before data[] on UDP SDP` | yes |
| source runtime dispatch reads cmd_rc | `msg->cmd_rc` | `Spin1API callback receives an sdp_msg_t whose data[0] follows cmd_rc/seq/args` | yes |
| source runtime command args use arg1-arg3 | `msg->arg1/msg->arg2/msg->arg3` | `simple CRA commands use official SDP argument fields instead of hidden data offsets` | yes |
| source runtime replies put cmd/status into cmd_rc | `reply->cmd_rc` | `host parser expects cmd/status in the command header and optional state bytes in data[]` | yes |
| source host stub mirrors command-header fields | `cmd_rc/seq/arg1/arg2/arg3` | `local syntax guard must expose the real Spin1API command header fields` | yes |
| source router header includes stdint directly | `#include <stdint.h>` | `router.h must not rely on indirect EBRAINS header includes for uint32_t` | yes |
| source router uses official SARK allocation API | `rtr_alloc/rtr_mc_set/rtr_free` | `real spinnaker_tools exposes official rtr_* router calls` | yes |
| source deprecated local-only router helpers absent | `sark_router_alloc/sark_router_free absent` | `local stubs must not hide EBRAINS SARK API drift` | yes |
| source host stub mirrors official router API | `rtr_alloc/rtr_mc_set/rtr_free` | `local syntax guard exposes official SARK router names` | yes |
| source hardware build uses official spinnaker_tools.mk | `spinnaker_tools.mk` | `official build chain supplies cpu_reset, build object, spin1_api library, and APLX section packing` | yes |
| source hardware build avoids deprecated Makefile.common include | `Makefile.common absent` | `Makefile.common inclusion lacks the app build rules needed for APLX creation` | yes |
| source hardware build avoids manual direct linker recipe | `no direct $(LD) object-only link` | `manual object-only link produced empty ELF without cpu_reset/startup sections on EBRAINS` | yes |
| source hardware output stays under build directory | `APP_OUTPUT_DIR := build/` | `runner expects build/coral_reef.aplx` | yes |
| source hardware build creates nested object directories | `$(OBJECTS): | $(OBJECT_DIRS)` | `spinnaker_tools.mk writes build/gnu/src/*.o and does not create nested source subdirectories itself` | yes |
| bundle official no-payload MC callback registered | `spin1_callback_on(MC_PACKET_RECEIVED` | `uses Tier 4.22k-confirmed official Spin1API enum constant` | yes |
| bundle official payload MC callback registered | `spin1_callback_on(MCPL_PACKET_RECEIVED` | `uses Tier 4.22k-confirmed official Spin1API enum constant` | yes |
| bundle legacy guessed callback names absent | `MC_PACKET_RX/MCPL_PACKET_RX absent` | `no direct brittle guessed callback names remain` | yes |
| bundle host stub mirrors confirmed EBRAINS event names | `MC_PACKET_RECEIVED/MCPL_PACKET_RECEIVED` | `local syntax guard exposes official names and omits guessed names` | yes |
| bundle SDP reply uses packed official sdp_msg_t fields | `dest_port/srce_port/dest_addr/srce_addr` | `mirrors real SARK SDP field names instead of local split x/y/cpu guesses` | yes |
| bundle deprecated split SDP fields absent | `dest_y/src_y/dest_x/src_x/src_cpu absent` | `EBRAINS SARK sdp_msg_t uses packed address/port fields` | yes |
| bundle uses official SARK memory copy API | `sark_mem_cpy` | `real spinnaker_tools exposes sark_mem_cpy, not sark_memcpy` | yes |
| bundle host stub mirrors official SARK SDP fields | `srce_port/srce_addr/sark_mem_cpy` | `local syntax guard exposes the same fields/API that EBRAINS build requires` | yes |
| bundle host sends official sdp_msg_t command header | `struct.pack("<HHIII"` | `host must place opcode in cmd_rc and use arg1/arg2/arg3 before data[]` | yes |
| bundle host parses cmd_rc before data payload | `struct.unpack_from("<HHIII", data, 10)` | `board replies expose cmd/status in cmd_rc before data[] on UDP SDP` | yes |
| bundle runtime dispatch reads cmd_rc | `msg->cmd_rc` | `Spin1API callback receives an sdp_msg_t whose data[0] follows cmd_rc/seq/args` | yes |
| bundle runtime command args use arg1-arg3 | `msg->arg1/msg->arg2/msg->arg3` | `simple CRA commands use official SDP argument fields instead of hidden data offsets` | yes |
| bundle runtime replies put cmd/status into cmd_rc | `reply->cmd_rc` | `host parser expects cmd/status in the command header and optional state bytes in data[]` | yes |
| bundle host stub mirrors command-header fields | `cmd_rc/seq/arg1/arg2/arg3` | `local syntax guard must expose the real Spin1API command header fields` | yes |
| bundle router header includes stdint directly | `#include <stdint.h>` | `router.h must not rely on indirect EBRAINS header includes for uint32_t` | yes |
| bundle router uses official SARK allocation API | `rtr_alloc/rtr_mc_set/rtr_free` | `real spinnaker_tools exposes official rtr_* router calls` | yes |
| bundle deprecated local-only router helpers absent | `sark_router_alloc/sark_router_free absent` | `local stubs must not hide EBRAINS SARK API drift` | yes |
| bundle host stub mirrors official router API | `rtr_alloc/rtr_mc_set/rtr_free` | `local syntax guard exposes official SARK router names` | yes |
| bundle hardware build uses official spinnaker_tools.mk | `spinnaker_tools.mk` | `official build chain supplies cpu_reset, build object, spin1_api library, and APLX section packing` | yes |
| bundle hardware build avoids deprecated Makefile.common include | `Makefile.common absent` | `Makefile.common inclusion lacks the app build rules needed for APLX creation` | yes |
| bundle hardware build avoids manual direct linker recipe | `no direct $(LD) object-only link` | `manual object-only link produced empty ELF without cpu_reset/startup sections on EBRAINS` | yes |
| bundle hardware output stays under build directory | `APP_OUTPUT_DIR := build/` | `runner expects build/coral_reef.aplx` | yes |
| bundle hardware build creates nested object directories | `$(OBJECTS): | $(OBJECT_DIRS)` | `spinnaker_tools.mk writes build/gnu/src/*.o and does not create nested source subdirectories itself` | yes |

## Artifacts

- `upload_bundle`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared/ebrains_upload_bundle/cra_422r`
- `job_readme`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared/ebrains_upload_bundle/cra_422r/README_TIER4_22I_JOB.md`
- `stable_upload_folder`: `/Users/james/JKS:CRA/ebrains_jobs/cra_422r`
- `manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared/tier4_22i_results.json`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared/tier4_22i_report.md`
