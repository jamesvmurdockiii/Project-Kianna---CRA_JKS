# Tier 4.22n Tiny Delayed-Cue Custom-Runtime Micro-Task

- Generated: `2026-05-01T03:03:01+00:00`
- Mode: `ingest`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested`

Tier 4.22n runs a 12-event delayed-cue-like signed micro-task through the custom runtime. Each event is scored from the chip's pre-update prediction, held across a two-event pending gap, then matured in order with delayed credit and checked against a local s16.15 reference.

## Claim Boundary

- `LOCAL`/`PREPARED` means the task reference, source bundle, and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means the minimal task-like loop matched local fixed-point reference and satisfied the predeclared task metrics on real SpiNNaker.
- This is not full CRA task learning, not v2.1 mechanism transfer, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22m_status: `missing`
- mode: `ingest`
- reference_status: `pass`
- reference_sequence_length: `12`
- reference_accuracy: `0.833333`
- reference_tail_accuracy: `1`
- reference_final_weight: `0.9375`
- reference_final_bias: `0`
- reference_pending_gap_depth: `2`
- reference_max_pending_depth: `3`
- observed_max_pending_depth: `3`
- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.205.1`
- selected_dest_cpu: `4`
- aplx_build_status: `pass`
- app_load_status: `pass`
- task_micro_loop_status: `pass`
- observed_accuracy: `0.833333`
- observed_tail_accuracy: `1`
- final_pending_created: `12`
- final_pending_matured: `12`
- final_reward_events: `12`
- final_decisions: `12`
- final_readout_weight: `0.9375`
- final_readout_bias: `0`
- next_step_if_passed: `Tier 4.22o: expand from delayed-cue-like micro-task to a tiny noisy-switching custom-runtime micro-task only after 4.22n passes on board.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22n_delayed_cue_micro_task_20260501_0001` | `expected current source` | yes |
| Tier 4.22m task micro-loop pass exists or fresh bundle | `missing` | `== pass OR missing in fresh EBRAINS bundle` | yes |
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
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spynnaker.cfg"], "reason": "no explicit hostname/config/environment target found", "status": "fail"}, {"dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.205.1", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 52.18025624915026, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.205.1"}], "dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.205.1", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 52.18025624915026, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.205.1"}` | `status == pass and hostname/IP/transceiver acquired` | yes |
| custom runtime .aplx build pass | `pass` | `== pass` | yes |
| custom runtime app load pass | `pass` | `== pass` | yes |
| minimal task micro-loop pass | `pass` | `== pass` | yes |
| all schedule commands succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| all mature commands succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| one pending matured per step | `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]` | `all == 1` | yes |
| predictions match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| weights match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| biases match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| observed tail accuracy | `1` | `>= 1.0` | yes |
| observed second-half improves or matches first-half | `0.333333` | `>= 0` | yes |
| observed max pending depth | `3` | `>= 3` | yes |
| observed task metrics match reference | `{"accuracy": 0.8333333333333334, "accuracy_gain": 0.33333333333333337, "correct_count": 10, "final_abs_error": 0.0, "first_half_accuracy": 0.6666666666666666, "second_half_accuracy": 1.0, "tail_accuracy": 1.0, "tail_window": 4}` | `accuracy/tail/gain equal reference` | yes |
| pending created count final | `12` | `== 12` | yes |
| pending matured count final | `12` | `== 12` | yes |
| reward events final | `12` | `== 12` | yes |
| decisions final | `12` | `== 12` | yes |
| active pending cleared final | `0` | `== 0` | yes |
| final weight matches reference | `30720` | `== 30720 +/- 1` | yes |
| final bias matches reference | `0` | `== 0 +/- 1` | yes |
| synthetic fallback zero | `0` | `== 0` | yes |
| returned EBRAINS artifact ingested | `hardware_pass_ingested` | `raw remote pass preserved with returned artifacts copied into controlled output` | yes |

## Task Rows

| Step | Feature | Target | Observed pred raw | Sign correct | Expected weight raw | Observed weight raw | Expected bias raw | Observed bias raw |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `1.0` | `1.0` | `0` | `True` | `4096` | `4096` | `4096` | `4096` |
| 2 | `-1.0` | `-1.0` | `0` | `False` | `8192` | `8192` | `0` | `0` |
| 3 | `1.0` | `1.0` | `0` | `True` | `12288` | `12288` | `4096` | `4096` |
| 4 | `-1.0` | `-1.0` | `0` | `False` | `16384` | `16384` | `0` | `0` |
| 5 | `1.0` | `1.0` | `8192` | `True` | `19456` | `19456` | `3072` | `3072` |
| 6 | `-1.0` | `-1.0` | `-8192` | `True` | `22528` | `22528` | `0` | `0` |
| 7 | `1.0` | `1.0` | `16384` | `True` | `24576` | `24576` | `2048` | `2048` |
| 8 | `-1.0` | `-1.0` | `-16384` | `True` | `26624` | `26624` | `0` | `0` |
| 9 | `1.0` | `1.0` | `22528` | `True` | `27904` | `27904` | `1280` | `1280` |
| 10 | `-1.0` | `-1.0` | `-22528` | `True` | `29184` | `29184` | `0` | `0` |
| 11 | `1.0` | `1.0` | `26624` | `True` | `29952` | `29952` | `768` | `768` |
| 12 | `-1.0` | `-1.0` | `-26624` | `True` | `30720` | `30720` | `0` | `0` |

## Artifacts

- `aplx_build_stderr`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22i_aplx_build_stderr (12).txt`
- `aplx_build_stdout`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22i_aplx_build_stdout (11).txt`
- `environment_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22n_environment.json`
- `host_test_stderr`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22i_host_test_stderr (11).txt`
- `host_test_stdout`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22i_host_test_stdout (11).txt`
- `load_result_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22n_load_result.json`
- `main_syntax_stderr`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22i_main_syntax_normal_stderr (10).txt`
- `main_syntax_stdout`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22i_main_syntax_normal_stdout (10).txt`
- `manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22n_results.json`
- `reference_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22n_task_reference_rows.csv`
- `reference_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22n_task_reference.json`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22n_report.md`
- `target_acquisition_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22n_target_acquisition.json`
- `task_micro_loop_result_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22n_task_micro_loop_result.json`
- `task_micro_loop_rows_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22n_task_micro_loop_rows.csv`
- `raw_remote_manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/remote_tier4_22n_results_raw.json`
- `raw_remote_report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/remote_tier4_22n_report_raw.md`
- `remote_latest_manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22n_latest_manifest.json`
- `main_syntax_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/tier4_22i_main_syntax_normal (10).o`
- `aplx_binary`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/coral_reef (6).aplx`
- `elf_binary`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/coral_reef (7).elf`
- `elf_listing`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/coral_reef (6).txt`
- `spinnaker_reports_zip`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/reports (17).zip`
- `main_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/main (9).o`
- `host_interface_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/host_interface (8).o`
- `state_manager_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/state_manager (9).o`
- `synapse_manager_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/synapse_manager (9).o`
- `neuron_manager_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/neuron_manager (9).o`
- `router_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/router (7).o`
