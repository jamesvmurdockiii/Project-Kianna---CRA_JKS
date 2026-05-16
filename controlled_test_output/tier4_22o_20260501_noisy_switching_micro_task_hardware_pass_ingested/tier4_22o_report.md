# Tier 4.22o Tiny Noisy-Switching Custom-Runtime Micro-Task

- Generated: `2026-05-01T03:35:34+00:00`
- Mode: `ingest`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested`

Tier 4.22o runs a 14-event noisy-switching signed micro-task through the custom runtime. Each event is scored from the chip's pre-update prediction, held across a two-event pending gap, then matured in order with delayed credit and checked against a local s16.15 reference.

## Claim Boundary

- `LOCAL`/`PREPARED` means the task reference, source bundle, and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means the minimal task-like loop matched local fixed-point reference and satisfied the predeclared task metrics on real SpiNNaker.
- This is not full CRA task learning, not v2.1 mechanism transfer, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22n_status: `missing`
- mode: `ingest`
- reference_status: `pass`
- reference_sequence_length: `14`
- reference_accuracy: `0.785714`
- reference_tail_accuracy: `1`
- reference_final_weight: `-1.48828`
- reference_final_bias: `-0.046875`
- reference_pending_gap_depth: `2`
- reference_max_pending_depth: `3`
- observed_max_pending_depth: `3`
- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.210.25`
- selected_dest_cpu: `4`
- aplx_build_status: `pass`
- app_load_status: `pass`
- task_micro_loop_status: `pass`
- observed_accuracy: `0.785714`
- observed_tail_accuracy: `1`
- final_pending_created: `14`
- final_pending_matured: `14`
- final_reward_events: `14`
- final_decisions: `14`
- final_readout_weight: `-1.48828`
- final_readout_bias: `-0.046875`
- next_step_if_passed: `Tier 4.22p: expand from tiny noisy-switching micro-task to the next predeclared custom-runtime task gate only after 4.22o passes on board.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22o_noisy_switching_micro_task_20260501_0002_mul64` | `expected current source` | yes |
| Tier 4.22n delayed-cue micro-task pass exists or fresh bundle | `missing` | `== pass OR missing in fresh EBRAINS bundle` | yes |
| local task fixed-point reference generated | `pass` | `== pass` | yes |
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
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spynnaker.cfg"], "reason": "no explicit hostname/config/environment target found", "status": "fail"}, {"dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.210.25", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 48.98669244791381, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.210.25"}], "dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.210.25", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 48.98669244791381, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.210.25"}` | `status == pass and hostname/IP/transceiver acquired` | yes |
| custom runtime .aplx build pass | `pass` | `== pass` | yes |
| custom runtime app load pass | `pass` | `== pass` | yes |
| minimal task micro-loop pass | `pass` | `== pass` | yes |
| all schedule commands succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| all mature commands succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| one pending matured per step | `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]` | `all == 1` | yes |
| predictions match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| weights match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| biases match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| observed tail accuracy | `1` | `>= 1.0` | yes |
| observed second-half improves or matches first-half | `0.142857` | `>= 0` | yes |
| observed max pending depth | `3` | `>= 3` | yes |
| observed task metrics match reference | `{"accuracy": 0.7857142857142857, "accuracy_gain": 0.1428571428571428, "correct_count": 11, "final_abs_error": 0.0, "first_half_accuracy": 0.7142857142857143, "second_half_accuracy": 0.8571428571428571, "tail_accuracy": 1.0, "tail_window": 4}` | `accuracy/tail/gain equal reference` | yes |
| pending created count final | `14` | `== 14` | yes |
| pending matured count final | `14` | `== 14` | yes |
| reward events final | `14` | `== 14` | yes |
| decisions final | `14` | `== 14` | yes |
| active pending cleared final | `0` | `== 0` | yes |
| final weight matches reference | `-48768` | `== -48768 +/- 1` | yes |
| final bias matches reference | `-1536` | `== -1536 +/- 1` | yes |
| synthetic fallback zero | `0` | `== 0` | yes |
| returned EBRAINS artifact ingested | `hardware_pass_ingested` | `raw remote pass preserved with returned artifacts copied into controlled output` | yes |

## Task Rows

| Step | Feature | Target | Observed pred raw | Sign correct | Expected weight raw | Observed weight raw | Expected bias raw | Observed bias raw |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `1.0` | `1.0` | `0` | `True` | `12288` | `12288` | `12288` | `12288` |
| 2 | `-1.0` | `-1.0` | `0` | `False` | `24576` | `24576` | `0` | `0` |
| 3 | `1.0` | `1.0` | `0` | `True` | `36864` | `36864` | `12288` | `12288` |
| 4 | `-1.0` | `1.0` | `0` | `True` | `24576` | `24576` | `24576` | `24576` |
| 5 | `1.0` | `1.0` | `24576` | `True` | `27648` | `27648` | `27648` | `27648` |
| 6 | `-1.0` | `-1.0` | `-24576` | `True` | `30720` | `30720` | `24576` | `24576` |
| 7 | `1.0` | `-1.0` | `49152` | `False` | `0` | `0` | `-6144` | `-6144` |
| 8 | `-1.0` | `1.0` | `0` | `True` | `-12288` | `-12288` | `6144` | `6144` |
| 9 | `1.0` | `1.0` | `55296` | `True` | `-20736` | `-20736` | `-2304` | `-2304` |
| 10 | `-1.0` | `1.0` | `-6144` | `False` | `-35328` | `-35328` | `12288` | `12288` |
| 11 | `1.0` | `-1.0` | `-6144` | `True` | `-45312` | `-45312` | `2304` | `2304` |
| 12 | `-1.0` | `1.0` | `18432` | `True` | `-50688` | `-50688` | `7680` | `7680` |
| 13 | `1.0` | `-1.0` | `-23040` | `True` | `-54336` | `-54336` | `4032` | `4032` |
| 14 | `-1.0` | `1.0` | `47616` | `True` | `-48768` | `-48768` | `-1536` | `-1536` |

## Artifacts

- `aplx_build_stderr`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22i_aplx_build_stderr.txt`
- `aplx_build_stdout`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22i_aplx_build_stdout.txt`
- `environment_json`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22o_environment.json`
- `host_test_stderr`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22i_host_test_stderr.txt`
- `host_test_stdout`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22i_host_test_stdout.txt`
- `load_result_json`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22o_load_result.json`
- `main_syntax_stderr`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22i_main_syntax_normal_stderr.txt`
- `main_syntax_stdout`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22i_main_syntax_normal_stdout.txt`
- `manifest_json`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22o_results.json`
- `reference_csv`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22o_task_reference_rows.csv`
- `reference_json`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22o_task_reference.json`
- `report_md`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22o_report.md`
- `target_acquisition_json`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22o_target_acquisition.json`
- `task_micro_loop_result_json`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22o_task_micro_loop_result.json`
- `task_micro_loop_rows_csv`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22o_task_micro_loop_rows.csv`
- `raw_remote_manifest_json`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/remote_tier4_22o_results_raw.json`
- `raw_remote_report_md`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/remote_tier4_22o_report_raw.md`
- `remote_latest_manifest_json`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22o_latest_manifest.json`
- `main_syntax_object`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/tier4_22i_main_syntax_normal.o`
- `aplx_binary`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/coral_reef.aplx`
- `elf_binary`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/coral_reef.elf`
- `elf_listing`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/coral_reef.txt`
- `spinnaker_reports_zip`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/reports.zip`
- `main_object`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/main.o`
- `host_interface_object`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/host_interface.o`
- `state_manager_object`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/state_manager.o`
- `synapse_manager_object`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/synapse_manager.o`
- `neuron_manager_object`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/neuron_manager.o`
- `router_object`: `<repo>/controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/router.o`
