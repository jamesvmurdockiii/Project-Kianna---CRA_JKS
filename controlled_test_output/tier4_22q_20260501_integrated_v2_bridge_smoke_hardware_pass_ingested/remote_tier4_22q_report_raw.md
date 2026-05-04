# Tier 4.22q Tiny Integrated V2 Bridge Custom-Runtime Smoke

- Generated: `2026-05-01T06:59:01+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Output directory: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output`

Tier 4.22q runs a 30-event signed stream produced by a tiny host-side keyed-context plus routing bridge through the custom runtime. Each event is scored from the chip's pre-update prediction, held across a two-event pending gap, then matured in order with delayed credit and checked against a local s16.15 reference.

## Claim Boundary

- `LOCAL`/`PREPARED` means the task reference, source bundle, and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means the minimal task-like loop matched local fixed-point reference and satisfied the predeclared task metrics on real SpiNNaker.
- This is not native v2.1 on-chip memory/routing, not full CRA task learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22p_status: `missing`
- mode: `run-hardware`
- reference_status: `pass`
- reference_sequence_length: `30`
- reference_accuracy: `0.933333`
- reference_tail_accuracy: `1`
- reference_final_weight: `1`
- reference_final_bias: `0`
- reference_pending_gap_depth: `2`
- reference_max_pending_depth: `3`
- observed_max_pending_depth: `3`
- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.236.65`
- selected_dest_cpu: `4`
- aplx_build_status: `pass`
- app_load_status: `pass`
- task_micro_loop_status: `pass`
- observed_accuracy: `0.933333`
- observed_tail_accuracy: `1`
- bridge_context_updates: `9`
- bridge_route_updates: `9`
- bridge_max_slot_count: `3`
- final_pending_created: `30`
- final_pending_matured: `30`
- final_reward_events: `30`
- final_decisions: `30`
- final_readout_weight: `1`
- final_readout_bias: `0`
- next_step_if_passed: `Ingest returned Tier 4.22q files; if it passes, decide whether Tier 4.22r should port one v2 state primitive into C or continue the next custom-runtime integration gate.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22q_integrated_v2_bridge_smoke_20260501_0001` | `expected current source` | yes |
| Tier 4.22p A-B-A reentry micro-task pass exists or fresh bundle | `missing` | `== pass OR missing in fresh EBRAINS bundle` | yes |
| local task fixed-point reference generated | `pass` | `== pass` | yes |
| reference bridge context updates observed | `9` | `> 0` | yes |
| reference bridge route updates observed | `9` | `> 0` | yes |
| reference bridge retained three keyed slots | `3` | `>= 3` | yes |
| reference bridge feature source declared | `host_keyed_context_route_transform` | `== host_keyed_context_route_transform` | yes |
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
| runtime task loop can score pre-update predictions | `CMD_SCHEDULE_PENDING returns prediction_raw before maturation` | `task micro-loop must evaluate the decision before credit updates the readout` | yes |
| runtime task loop increments decision counter | `cra_state_record_decision` | `minimal task loop must count decisions separately from rewards` | yes |
| runtime pending horizons do not store future target | `pending_horizon_t has feature/prediction/due only` | `delayed-credit target must arrive at maturation, not be hidden in the pending record` | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spynnaker.cfg"], "reason": "no explicit hostname/config/environment target found", "status": "fail"}, {"dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.236.65", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 45.1521616729442, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.236.65"}], "dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.236.65", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 45.1521616729442, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.236.65"}` | `status == pass and hostname/IP/transceiver acquired` | yes |
| custom runtime .aplx build pass | `pass` | `== pass` | yes |
| custom runtime app load pass | `pass` | `== pass` | yes |
| minimal task micro-loop pass | `pass` | `== pass` | yes |
| all schedule commands succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| all mature commands succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| one pending matured per step | `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]` | `all == 1` | yes |
| predictions match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| weights match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| biases match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| observed tail accuracy | `1` | `>= 1.0` | yes |
| observed second-half improves or matches first-half | `0.133333` | `>= 0` | yes |
| observed max pending depth | `3` | `>= 3` | yes |
| observed task metrics match reference | `{"accuracy": 0.9333333333333333, "accuracy_gain": 0.1333333333333333, "correct_count": 28, "final_abs_error": 0.0, "first_half_accuracy": 0.8666666666666667, "second_half_accuracy": 1.0, "tail_accuracy": 1.0, "tail_window": 6}` | `accuracy/tail/gain equal reference` | yes |
| pending created count final | `30` | `== 30` | yes |
| pending matured count final | `30` | `== 30` | yes |
| reward events final | `30` | `== 30` | yes |
| decisions final | `30` | `== 30` | yes |
| active pending cleared final | `0` | `== 0` | yes |
| final weight matches reference | `32768` | `== 32768 +/- 1` | yes |
| final bias matches reference | `0` | `== 0 +/- 1` | yes |
| synthetic fallback zero | `0` | `== 0` | yes |

## Task Rows

| Step | Feature | Target | Observed pred raw | Sign correct | Expected weight raw | Observed weight raw | Expected bias raw | Observed bias raw |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `1.0` | `1.0` | `0` | `True` | `8192` | `8192` | `8192` | `8192` |
| 2 | `-1.0` | `-1.0` | `0` | `False` | `16384` | `16384` | `0` | `0` |
| 3 | `-1.0` | `-1.0` | `0` | `False` | `24576` | `24576` | `-8192` | `-8192` |
| 4 | `1.0` | `1.0` | `16384` | `True` | `28672` | `28672` | `-4096` | `-4096` |
| 5 | `-1.0` | `-1.0` | `-16384` | `True` | `32768` | `32768` | `-8192` | `-8192` |
| 6 | `1.0` | `1.0` | `16384` | `True` | `36864` | `36864` | `-4096` | `-4096` |
| 7 | `-1.0` | `-1.0` | `-32768` | `True` | `36864` | `36864` | `-4096` | `-4096` |
| 8 | `1.0` | `1.0` | `24576` | `True` | `38912` | `38912` | `-2048` | `-2048` |
| 9 | `-1.0` | `-1.0` | `-40960` | `True` | `36864` | `36864` | `0` | `0` |
| 10 | `1.0` | `1.0` | `32768` | `True` | `36864` | `36864` | `0` | `0` |
| 11 | `-1.0` | `-1.0` | `-40960` | `True` | `34816` | `34816` | `2048` | `2048` |
| 12 | `1.0` | `1.0` | `36864` | `True` | `33792` | `33792` | `1024` | `1024` |
| 13 | `1.0` | `1.0` | `36864` | `True` | `32768` | `32768` | `0` | `0` |
| 14 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 15 | `1.0` | `1.0` | `34816` | `True` | `32256` | `32256` | `-512` | `-512` |
| 16 | `-1.0` | `-1.0` | `-32768` | `True` | `32256` | `32256` | `-512` | `-512` |
| 17 | `1.0` | `1.0` | `32768` | `True` | `32256` | `32256` | `-512` | `-512` |
| 18 | `-1.0` | `-1.0` | `-32768` | `True` | `32256` | `32256` | `-512` | `-512` |
| 19 | `1.0` | `1.0` | `31744` | `True` | `32512` | `32512` | `-256` | `-256` |
| 20 | `-1.0` | `-1.0` | `-32768` | `True` | `32512` | `32512` | `-256` | `-256` |
| 21 | `1.0` | `1.0` | `31744` | `True` | `32768` | `32768` | `0` | `0` |
| 22 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 23 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 24 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 25 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 26 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 27 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 28 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 29 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 30 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |

## Artifacts

- `reference_json`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22q_task_reference.json`
- `reference_csv`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22q_task_reference_rows.csv`
- `environment_json`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22q_environment.json`
- `target_acquisition_json`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22q_target_acquisition.json`
- `host_test_stdout`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22i_host_test_stdout.txt`
- `host_test_stderr`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22i_host_test_stderr.txt`
- `main_syntax_stdout`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22i_main_syntax_normal_stdout.txt`
- `main_syntax_stderr`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22i_main_syntax_normal_stderr.txt`
- `aplx_build_stdout`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22i_aplx_build_stdout.txt`
- `aplx_build_stderr`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22i_aplx_build_stderr.txt`
- `load_result_json`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22q_load_result.json`
- `task_micro_loop_result_json`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22q_task_micro_loop_result.json`
- `task_micro_loop_rows_csv`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22q_task_micro_loop_rows.csv`
- `manifest_json`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22q_results.json`
- `report_md`: `/tmp/job18200290945432121555.tmp/tier4_22q_job_output/tier4_22q_report.md`
