# Tier 4.22j Minimal Custom-Runtime Closed-Loop Learning Smoke

- Generated: `2026-05-01T01:25:45+00:00`
- Mode: `ingest`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested`

Tier 4.22j tests a minimal chip-owned delayed-credit/readout update after the Tier 4.22i board command path passed.

## Claim Boundary

- `PREPARED` means the source bundle and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means one delayed pending/readout update happened in the loaded custom runtime and was visible through compact readback.
- This is not full CRA task learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22i_status: `missing`
- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.196.177`
- selected_dest_cpu: `4`
- aplx_build_status: `pass`
- app_load_status: `pass`
- learning_smoke_status: `pass`
- pending_created_after_schedule: `1`
- pending_matured_after_mature: `1`
- readout_weight_after_mature: `0.25`
- readout_bias_after_mature: `0.25`
- custom_runtime_learning_next_allowed: `True`
- raw_remote_status: `fail`
- raw_remote_failure_reason: `Failed criteria: active pending cleared`
- ingest_classification: `hardware_pass_raw_false_fail`
- false_fail_reason: `Raw runner treated active_pending=0 as missing because the criterion used Python `or -1`; all returned hardware learning values satisfy the declared pass criteria.`
- next_step_if_passed: `Tier 4.22l small custom-runtime learning parity: compare this C readout update path against the local Tier 4.22e float/C-equation reference on a tiny sequence before scaling task complexity.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22j_minimal_custom_runtime_learning_20260501_0001` | `expected current source` | yes |
| Tier 4.22i board roundtrip pass exists or fresh bundle | `missing` | `== pass OR missing in fresh EBRAINS bundle` | yes |
| custom C host tests pass | `pass` | `== pass` | yes |
| main.c host syntax check pass | `pass` | `== pass` | yes |
| runtime CMD_SCHEDULE_PENDING defined | `CMD_SCHEDULE_PENDING 9` | `config.h defines opcode` | yes |
| runtime CMD_MATURE_PENDING defined | `CMD_MATURE_PENDING 10` | `config.h defines opcode` | yes |
| runtime learning opcodes host-tested | `assert command constants` | `host tests cover opcodes` | yes |
| runtime controller exposes schedule command | `schedule_pending_decision` | `Python host can schedule delayed-credit state on board` | yes |
| runtime controller exposes mature command | `mature_pending` | `Python host can mature delayed-credit state on board` | yes |
| runtime runtime schedule handler exists | `_handle_schedule_pending` | `runtime computes prediction and schedules pending horizon` | yes |
| runtime runtime mature handler exists | `_handle_mature_pending` | `runtime matures pending horizon and updates readout` | yes |
| runtime learning commands dispatched | `case CMD_SCHEDULE_PENDING / CMD_MATURE_PENDING` | `SDP dispatcher routes learning commands` | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spynnaker.cfg"], "reason": "no explicit hostname/config/environment target found", "status": "fail"}, {"dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.196.177", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 47.94513410911895, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.196.177"}], "dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.196.177", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 47.94513410911895, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.196.177"}` | `status == pass and hostname/IP/transceiver acquired` | yes |
| custom runtime .aplx build pass | `pass` | `== pass` | yes |
| custom runtime app load pass | `pass` | `== pass` | yes |
| minimal learning smoke pass | `pass` | `== pass` | yes |
| pending horizon created | `1` | `>= 1` | yes |
| pending horizon active after schedule | `1` | `>= 1` | yes |
| decision recorded after schedule | `1` | `>= 1` | yes |
| pending mature command matured one | `1` | `>= 1` | yes |
| pending horizon matured in state | `1` | `>= 1` | yes |
| active pending cleared | `0` | `== 0` | yes |
| reward event recorded | `1` | `>= 1` | yes |
| readout weight increased | `8192` | `> 0` | yes |
| readout bias increased | `8192` | `> 0` | yes |
| synthetic fallback zero | `0` | `== 0` | yes |
| raw false-fail classification | `hardware_pass_raw_false_fail` | `raw fail may be reclassified only when returned hardware data satisfy all declared criteria` | yes |

## Artifacts

- `aplx_build_stderr`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22i_aplx_build_stderr (9).txt`
- `aplx_build_stdout`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22i_aplx_build_stdout (8).txt`
- `environment_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22j_environment.json`
- `host_test_stderr`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22i_host_test_stderr (8).txt`
- `host_test_stdout`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22i_host_test_stdout (8).txt`
- `learning_result_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22j_learning_result.json`
- `load_result_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22j_load_result.json`
- `main_syntax_stderr`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22i_main_syntax_normal_stderr (7).txt`
- `main_syntax_stdout`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22i_main_syntax_normal_stdout (7).txt`
- `manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22j_results.json`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22j_report.md`
- `target_acquisition_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22j_target_acquisition.json`
- `raw_remote_manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/remote_tier4_22j_results_raw.json`
- `raw_remote_report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/remote_tier4_22j_report_raw.md`
- `main_syntax_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/tier4_22i_main_syntax_normal (7).o`
- `aplx_binary`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/coral_reef (3).aplx`
- `elf_binary`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/coral_reef (4).elf`
- `elf_listing`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/coral_reef (3).txt`
- `spinnaker_reports_zip`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/reports (14).zip`
- `main_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/main (6).o`
- `host_interface_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/host_interface (5).o`
- `state_manager_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/state_manager (6).o`
- `synapse_manager_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/synapse_manager (6).o`
- `neuron_manager_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/neuron_manager (6).o`
- `router_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/router (4).o`
