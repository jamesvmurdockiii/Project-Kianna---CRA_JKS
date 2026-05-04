# Tier 4.22i Custom Runtime Board Round-Trip Smoke

- Generated: `2026-04-30T22:24:42+00:00`
- Mode: `run-hardware`
- Status: **FAIL**
- Output directory: `/tmp/job18309467254930990212.tmp/tier4_22i_job_output`

Tier 4.22i tests the custom C runtime itself on hardware: build/load the tiny `.aplx`, send `CMD_READ_STATE`, and validate the compact state packet after simple command mutations.

## Claim Boundary

- `PREPARED` means the source bundle and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means board load plus `CMD_READ_STATE` round-trip worked on real SpiNNaker.
- This is not full CRA learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22h_status: `missing`
- hardware_target_configured: `False`
- spinnaker_hostname: ``
- host_tests_passed: `True`
- main_syntax_check_passed: `True`
- aplx_build_status: `fail`
- app_load_status: `not_attempted`
- command_roundtrip_status: `not_attempted`
- read_state_schema_version: `None`
- state_after_mutation_neuron_count: `None`
- state_after_mutation_synapse_count: `None`
- custom_runtime_learning_hardware_allowed_next: `False`
- next_step_if_passed: `Tier 4.22j minimal custom-runtime closed-loop learning smoke: delayed pending/readout update on board with compact state readback.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22i_custom_runtime_roundtrip_20260430_0005` | `expected current source` | yes |
| Tier 4.22h compact-readback pass exists or fresh bundle | `missing` | `== pass OR missing in fresh EBRAINS bundle` | yes |
| hardware target configured | `` | `non-empty hostname` | no |
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
| runtime router header includes stdint directly | `#include <stdint.h>` | `router.h must not rely on indirect EBRAINS header includes for uint32_t` | yes |
| runtime router uses official SARK allocation API | `rtr_alloc/rtr_mc_set/rtr_free` | `real spinnaker_tools exposes official rtr_* router calls` | yes |
| runtime deprecated local-only router helpers absent | `sark_router_alloc/sark_router_free absent` | `local stubs must not hide EBRAINS SARK API drift` | yes |
| runtime host stub mirrors official router API | `rtr_alloc/rtr_mc_set/rtr_free` | `local syntax guard exposes official SARK router names` | yes |
| custom runtime .aplx build pass | `fail` | `== pass` | no |
| custom runtime app load pass | `not_attempted` | `== pass` | no |
| CMD_READ_STATE roundtrip pass | `not_attempted` | `== pass` | no |
| reset command acknowledged | `None` | `True` | no |
| birth/synapse mutation commands acknowledged | `{"birth_1": null, "birth_2": null, "synapse": null}` | `all True` | no |
| READ_STATE schema version valid | `None` | `== 1` | no |
| READ_STATE payload compact | `None` | `== 73` | no |
| post-mutation neuron count visible | `None` | `>= 2` | no |
| post-mutation synapse count visible | `None` | `>= 1` | no |
| synthetic fallback zero | `0` | `== 0` | yes |

## Artifacts

- `environment_json`: `/tmp/job18309467254930990212.tmp/tier4_22i_job_output/tier4_22i_environment.json`
- `host_test_stdout`: `/tmp/job18309467254930990212.tmp/tier4_22i_job_output/tier4_22i_host_test_stdout.txt`
- `host_test_stderr`: `/tmp/job18309467254930990212.tmp/tier4_22i_job_output/tier4_22i_host_test_stderr.txt`
- `main_syntax_stdout`: `/tmp/job18309467254930990212.tmp/tier4_22i_job_output/tier4_22i_main_syntax_normal_stdout.txt`
- `main_syntax_stderr`: `/tmp/job18309467254930990212.tmp/tier4_22i_job_output/tier4_22i_main_syntax_normal_stderr.txt`
- `aplx_build_stdout`: `/tmp/job18309467254930990212.tmp/tier4_22i_job_output/tier4_22i_aplx_build_stdout.txt`
- `aplx_build_stderr`: `/tmp/job18309467254930990212.tmp/tier4_22i_job_output/tier4_22i_aplx_build_stderr.txt`
- `load_result_json`: `/tmp/job18309467254930990212.tmp/tier4_22i_job_output/tier4_22i_load_result.json`
- `roundtrip_result_json`: `/tmp/job18309467254930990212.tmp/tier4_22i_job_output/tier4_22i_roundtrip_result.json`
- `manifest_json`: `/tmp/job18309467254930990212.tmp/tier4_22i_job_output/tier4_22i_results.json`
- `report_md`: `/tmp/job18309467254930990212.tmp/tier4_22i_job_output/tier4_22i_report.md`
