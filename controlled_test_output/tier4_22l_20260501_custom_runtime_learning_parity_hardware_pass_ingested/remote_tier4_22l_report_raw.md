# Tier 4.22l Tiny Custom-Runtime Learning Parity

- Generated: `2026-05-01T02:17:11+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Output directory: `<jobmanager_tmp>`

Tier 4.22l compares a tiny chip-owned pending-horizon/readout update sequence against a local s16.15 fixed-point reference.

## Claim Boundary

- `LOCAL`/`PREPARED` means the reference, source bundle, and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means the tiny on-chip update sequence matched the local fixed-point reference within tolerance.
- This is not full CRA task learning, not v2.1 mechanism transfer, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22j_status: `missing`
- mode: `run-hardware`
- reference_status: `pass`
- reference_sequence_length: `4`
- reference_final_weight: `-0.125`
- reference_final_bias: `-0.125`
- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.194.1`
- selected_dest_cpu: `4`
- aplx_build_status: `pass`
- app_load_status: `pass`
- learning_parity_status: `pass`
- final_pending_created: `4`
- final_pending_matured: `4`
- final_reward_events: `4`
- final_readout_weight: `-0.125`
- final_readout_bias: `-0.125`
- next_step_if_passed: `Tier 4.22m: expand from tiny parity to a minimal task micro-loop only after this exact fixed-point path passes on board.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22l_custom_runtime_learning_parity_20260501_0001` | `expected current source` | yes |
| Tier 4.22j minimal learning-smoke pass exists or fresh bundle | `missing` | `== pass OR missing in fresh EBRAINS bundle` | yes |
| local fixed-point reference generated | `pass` | `== pass` | yes |
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
| runtime fixed-point helper is s16.15 | `FP_SHIFT 15` | `config.h defines the same fixed-point scale as the Python reference` | yes |
| runtime readout prediction equation present | `FP_MUL(readout_weight, feature) + readout_bias` | `runtime prediction must match local parity reference` | yes |
| runtime readout update equation present | `delta_w = lr * error * feature; delta_b = lr * error` | `runtime maturation must match local parity reference` | yes |
| runtime mature command supports explicit mature_timestep | `msg->arg3 != 0 ? msg->arg3 : g_timestep` | `parity run uses explicit due_timestep to avoid timer-race false failures` | yes |
| runtime controller exposes returned due_timestep | `due_timestep` | `hardware parity can mature exactly the pending event it scheduled` | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spynnaker.cfg"], "reason": "no explicit hostname/config/environment target found", "status": "fail"}, {"dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.194.1", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 54.541590745793656, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.194.1"}], "dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.194.1", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 54.541590745793656, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.194.1"}` | `status == pass and hostname/IP/transceiver acquired` | yes |
| custom runtime .aplx build pass | `pass` | `== pass` | yes |
| custom runtime app load pass | `pass` | `== pass` | yes |
| tiny learning parity pass | `pass` | `== pass` | yes |
| all schedule commands succeeded | `[true, true, true, true]` | `all True` | yes |
| all mature commands succeeded | `[true, true, true, true]` | `all True` | yes |
| one pending matured per step | `[1, 1, 1, 1]` | `all == 1` | yes |
| predictions match local reference | `[0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| weights match local reference | `[0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| biases match local reference | `[0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| pending created count final | `4` | `== 4` | yes |
| pending matured count final | `4` | `== 4` | yes |
| reward events final | `4` | `== 4` | yes |
| active pending cleared final | `0` | `== 0` | yes |
| final weight matches reference | `-4096` | `== -4096 +/- 1` | yes |
| final bias matches reference | `-4096` | `== -4096 +/- 1` | yes |
| synthetic fallback zero | `0` | `== 0` | yes |

## Parity Rows

| Step | Feature | Target | Expected prediction raw | Observed prediction raw | Expected weight raw | Observed weight raw | Expected bias raw | Observed bias raw |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `1.0` | `1.0` | `0` | `0` | `8192` | `8192` | `8192` | `8192` |
| 2 | `1.0` | `-1.0` | `16384` | `16384` | `-4096` | `-4096` | `-4096` | `-4096` |
| 3 | `-1.0` | `-1.0` | `0` | `0` | `4096` | `4096` | `-12288` | `-12288` |
| 4 | `-1.0` | `0.5` | `-16384` | `-16384` | `-4096` | `-4096` | `-4096` | `-4096` |

## Artifacts

- `reference_json`: `<jobmanager_tmp>`
- `reference_csv`: `<jobmanager_tmp>`
- `environment_json`: `<jobmanager_tmp>`
- `target_acquisition_json`: `<jobmanager_tmp>`
- `host_test_stdout`: `<jobmanager_tmp>`
- `host_test_stderr`: `<jobmanager_tmp>`
- `main_syntax_stdout`: `<jobmanager_tmp>`
- `main_syntax_stderr`: `<jobmanager_tmp>`
- `aplx_build_stdout`: `<jobmanager_tmp>`
- `aplx_build_stderr`: `<jobmanager_tmp>`
- `load_result_json`: `<jobmanager_tmp>`
- `learning_parity_result_json`: `<jobmanager_tmp>`
- `learning_parity_rows_csv`: `<jobmanager_tmp>`
- `manifest_json`: `<jobmanager_tmp>`
- `report_md`: `<jobmanager_tmp>`
