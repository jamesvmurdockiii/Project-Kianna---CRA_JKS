# Tier 4.22j Minimal Custom-Runtime Closed-Loop Learning Smoke

- Generated: `2026-05-01T01:25:45+00:00`
- Mode: `run-hardware`
- Status: **FAIL**
- Output directory: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output`

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
- custom_runtime_learning_next_allowed: `False`
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
| active pending cleared | `0` | `== 0` | no |
| reward event recorded | `1` | `>= 1` | yes |
| readout weight increased | `8192` | `> 0` | yes |
| readout bias increased | `8192` | `> 0` | yes |
| synthetic fallback zero | `0` | `== 0` | yes |

## Artifacts

- `environment_json`: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output/tier4_22j_environment.json`
- `target_acquisition_json`: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output/tier4_22j_target_acquisition.json`
- `host_test_stdout`: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output/tier4_22i_host_test_stdout.txt`
- `host_test_stderr`: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output/tier4_22i_host_test_stderr.txt`
- `main_syntax_stdout`: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output/tier4_22i_main_syntax_normal_stdout.txt`
- `main_syntax_stderr`: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output/tier4_22i_main_syntax_normal_stderr.txt`
- `aplx_build_stdout`: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output/tier4_22i_aplx_build_stdout.txt`
- `aplx_build_stderr`: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output/tier4_22i_aplx_build_stderr.txt`
- `load_result_json`: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output/tier4_22j_load_result.json`
- `learning_result_json`: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output/tier4_22j_learning_result.json`
- `manifest_json`: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output/tier4_22j_results.json`
- `report_md`: `/tmp/job11994622048194933354.tmp/tier4_22j_job_output/tier4_22j_report.md`
