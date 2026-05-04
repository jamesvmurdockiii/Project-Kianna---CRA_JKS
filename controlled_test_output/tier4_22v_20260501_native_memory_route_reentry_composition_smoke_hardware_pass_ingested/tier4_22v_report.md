# Tier 4.22v Tiny Native Memory-Route Reentry/Composition Custom-Runtime Smoke

- Generated: `2026-05-01T20:15:13+00:00`
- Mode: `ingest`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested`

Tier 4.22v runs a 48-event signed stream through the custom runtime using native keyed context state, keyed route state, and keyed memory/working-state slots. The host writes context, route, and memory updates, then sends only key+cue+delay for each decision; the chip retrieves all three by key, computes feature=context[key]*route[key]*memory[key]*cue, scores the pre-update prediction, holds a two-event pending gap, then matures delayed credit against a local s16.15 reference.

## Claim Boundary

- `LOCAL`/`PREPARED` means the task reference, source bundle, and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means the minimal task-like loop matched local fixed-point reference and satisfied the predeclared task metrics on real SpiNNaker.
- This is not full native v2.1 memory/routing, not full CRA task learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22u_status: `missing`
- mode: `ingest`
- reference_status: `pass`
- reference_sequence_length: `48`
- reference_accuracy: `0.9375`
- reference_tail_accuracy: `1`
- reference_final_weight: `1`
- reference_final_bias: `0`
- reference_pending_gap_depth: `2`
- reference_max_pending_depth: `3`
- observed_max_pending_depth: `3`
- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.240.153`
- selected_dest_cpu: `4`
- aplx_build_status: `pass`
- app_load_status: `pass`
- task_micro_loop_status: `pass`
- observed_accuracy: `0.9375`
- observed_tail_accuracy: `1`
- native_context_keys: `["ctx_A", "ctx_B", "ctx_C", "ctx_D"]`
- native_context_key_ids: `[101, 202, 303, 404]`
- native_context_writes: `18`
- native_context_reads: `48`
- native_context_max_slot_count: `4`
- native_route_slot_writes: `21`
- native_route_slot_reads: `48`
- native_route_max_slot_count: `4`
- native_route_values: `[-1, 1]`
- native_feature_source: `chip_context_memory_route_lookup_feature_transform`
- native_memory_slot_writes: `21`
- native_memory_slot_reads: `48`
- native_memory_max_slot_count: `4`
- native_memory_values: `[-1, 1]`
- final_pending_created: `48`
- final_pending_matured: `48`
- final_reward_events: `48`
- final_decisions: `48`
- final_readout_weight: `1`
- final_readout_bias: `0`
- final_route_slot_writes: `21`
- final_route_slot_hits: `52`
- final_route_slot_misses: `0`
- final_active_route_slots: `4`
- final_memory_slot_writes: `21`
- final_memory_slot_hits: `52`
- final_memory_slot_misses: `0`
- final_active_memory_slots: `4`
- next_step_if_passed: `Ingest returned Tier 4.22v files; if it passes, continue with the next native custom-runtime integration gate, likely route-key/memory-key decoupling or compact native v2 bridge integration.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22v_native_memory_route_reentry_composition_smoke_20260501_0001` | `expected current source` | yes |
| Tier 4.22u native memory-route smoke pass exists or fresh bundle | `missing` | `== pass OR missing in fresh EBRAINS bundle` | yes |
| local task fixed-point reference generated | `pass` | `== pass` | yes |
| reference native context writes observed | `18` | `> 0` | yes |
| reference native context reads observed | `48` | `== 48` | yes |
| reference native context retained four keyed slots | `4` | `>= 4` | yes |
| reference native keyed route writes observed | `21` | `> 0` | yes |
| reference native keyed route reads observed | `48` | `== 48` | yes |
| reference native keyed route retained four slots | `4` | `>= 4` | yes |
| reference native route values cover both signs | `[-1, 1]` | `contains -1 and 1` | yes |
| reference native keyed memory writes observed | `21` | `> 0` | yes |
| reference native keyed memory reads observed | `48` | `== 48` | yes |
| reference native keyed memory retained four slots | `4` | `>= 4` | yes |
| reference native memory values cover both signs | `[-1, 1]` | `contains -1 and 1` | yes |
| reference native feature source declared | `chip_context_memory_route_lookup_feature_transform` | `== chip_context_memory_route_lookup_feature_transform` | yes |
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
| runtime native context, route, and memory command constants exist | `CMD_WRITE_CONTEXT/CMD_WRITE_ROUTE_SLOT/CMD_WRITE_MEMORY_SLOT/CMD_SCHEDULE_MEMORY_ROUTE_CONTEXT_PENDING` | `custom runtime must expose native context plus memory-route state primitives` | yes |
| runtime native context write/read handlers use bounded C slots | `cra_state_write_context/cra_state_read_context` | `context state must be owned by the C runtime, not a host-only dictionary` | yes |
| runtime native keyed route write/read handlers exist | `cra_state_write_route_slot/cra_state_read_route_slot` | `keyed route state must be owned by the C runtime, not a host-only dictionary` | yes |
| runtime native keyed memory write/read handlers exist | `cra_state_write_memory_slot/cra_state_read_memory_slot` | `memory/working state must be owned by the C runtime, not a host-only dictionary` | yes |
| runtime native keyed memory-route schedule forms feature on chip | `feature = FP_MUL(FP_MUL(FP_MUL(context_value, route_value), memory_value), cue)` | `host must send key+cue, while the runtime retrieves context+route+memory slots by key and computes the scalar feature` | yes |
| runtime task loop can score pre-update predictions | `CMD_SCHEDULE_PENDING returns prediction_raw before maturation` | `task micro-loop must evaluate the decision before credit updates the readout` | yes |
| runtime task loop increments decision counter | `cra_state_record_decision` | `minimal task loop must count decisions separately from rewards` | yes |
| runtime pending horizons do not store future target | `pending_horizon_t has feature/prediction/due only` | `delayed-credit target must arrive at maturation, not be hidden in the pending record` | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spynnaker.cfg"], "reason": "no explicit hostname/config/environment target found", "status": "fail"}, {"dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.240.153", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 48.8609430489596, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.240.153"}], "dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.240.153", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 48.8609430489596, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.240.153"}` | `status == pass and hostname/IP/transceiver acquired` | yes |
| custom runtime .aplx build pass | `pass` | `== pass` | yes |
| custom runtime app load pass | `pass` | `== pass` | yes |
| minimal task micro-loop pass | `pass` | `== pass` | yes |
| all context writes succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| all route-slot writes succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| all memory-slot writes succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| all schedule commands succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| all mature commands succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| one pending matured per step | `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]` | `all == 1` | yes |
| chip-computed features match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| chip-retrieved context values match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| chip-retrieved context confidence matches local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| chip-retrieved route-slot values match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| chip-retrieved route-slot confidence matches local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| chip-retrieved memory-slot values match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| chip-retrieved memory-slot confidence matches local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| chip-returned keyed memory IDs match requested keys | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| predictions match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| weights match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| biases match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| observed tail accuracy | `1` | `>= 1.0` | yes |
| observed second-half improves or matches first-half | `0.125` | `>= 0` | yes |
| observed max pending depth | `3` | `>= 3` | yes |
| observed task metrics match reference | `{"accuracy": 0.9375, "accuracy_gain": 0.125, "correct_count": 45, "final_abs_error": 0.0, "first_half_accuracy": 0.875, "second_half_accuracy": 1.0, "tail_accuracy": 1.0, "tail_window": 6}` | `accuracy/tail/gain equal reference` | yes |
| pending created count final | `48` | `== 48` | yes |
| pending matured count final | `48` | `== 48` | yes |
| reward events final | `48` | `== 48` | yes |
| decisions final | `48` | `== 48` | yes |
| active pending cleared final | `0` | `== 0` | yes |
| context slot writes final | `18` | `== 18` | yes |
| context slot hits final | `48` | `>= 48` | yes |
| context slot misses final | `0` | `== 0` | yes |
| active context slots final | `4` | `>= 4` | yes |
| route-slot readback final succeeds | `[true, true, true, true]` | `all True` | yes |
| observed route-slot writes final | `21` | `== 21` | yes |
| observed active route slots final | `4` | `>= 4` | yes |
| route-slot hits final | `52` | `>= 48` | yes |
| route-slot misses final | `0` | `== 0` | yes |
| memory-slot readback final succeeds | `[true, true, true, true]` | `all True` | yes |
| observed memory-slot writes final | `21` | `== 21` | yes |
| observed active memory slots final | `4` | `>= 4` | yes |
| memory-slot hits final | `52` | `>= 48` | yes |
| memory-slot misses final | `0` | `== 0` | yes |
| final weight matches reference | `32768` | `== 32768 +/- 1` | yes |
| final bias matches reference | `0` | `== 0 +/- 1` | yes |
| synthetic fallback zero | `0` | `== 0` | yes |
| returned EBRAINS artifact ingested | `hardware_pass_ingested` | `raw remote pass OR documented false-fail correction preserved with returned artifacts copied into controlled output` | yes |

## Task Rows

| Step | Feature | Target | Observed pred raw | Sign correct | Expected weight raw | Observed weight raw | Expected bias raw | Observed bias raw |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `1.0` | `1.0` | `0` | `True` | `8192` | `8192` | `8192` | `8192` |
| 2 | `1.0` | `1.0` | `0` | `True` | `16384` | `16384` | `16384` | `16384` |
| 3 | `-1.0` | `-1.0` | `0` | `False` | `24576` | `24576` | `8192` | `8192` |
| 4 | `-1.0` | `-1.0` | `0` | `False` | `32768` | `32768` | `0` | `0` |
| 5 | `-1.0` | `-1.0` | `0` | `False` | `40960` | `40960` | `-8192` | `-8192` |
| 6 | `1.0` | `1.0` | `32768` | `True` | `40960` | `40960` | `-8192` | `-8192` |
| 7 | `-1.0` | `-1.0` | `-32768` | `True` | `40960` | `40960` | `-8192` | `-8192` |
| 8 | `1.0` | `1.0` | `32768` | `True` | `40960` | `40960` | `-8192` | `-8192` |
| 9 | `-1.0` | `-1.0` | `-49152` | `True` | `36864` | `36864` | `-4096` | `-4096` |
| 10 | `1.0` | `1.0` | `32768` | `True` | `36864` | `36864` | `-4096` | `-4096` |
| 11 | `-1.0` | `-1.0` | `-49152` | `True` | `32768` | `32768` | `0` | `0` |
| 12 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 13 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 14 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 15 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 16 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 17 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 18 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 19 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 20 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 21 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 22 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 23 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 24 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 25 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 26 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 27 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 28 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 29 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 30 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 31 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 32 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 33 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 34 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 35 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 36 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 37 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 38 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 39 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 40 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 41 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 42 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 43 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 44 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 45 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 46 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 47 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 48 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |

## Artifacts

- `aplx_build_stderr`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22i_aplx_build_stderr (21).txt`
- `aplx_build_stdout`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22i_aplx_build_stdout (20).txt`
- `environment_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22v_environment.json`
- `host_test_stderr`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22i_host_test_stderr (20).txt`
- `host_test_stdout`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22i_host_test_stdout (20).txt`
- `load_result_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22v_load_result.json`
- `main_syntax_stderr`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22i_main_syntax_normal_stderr (19).txt`
- `main_syntax_stdout`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22i_main_syntax_normal_stdout (19).txt`
- `manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22v_results.json`
- `reference_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22v_task_reference_rows.csv`
- `reference_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22v_task_reference.json`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22v_report.md`
- `target_acquisition_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22v_target_acquisition.json`
- `task_micro_loop_result_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22v_task_micro_loop_result.json`
- `task_micro_loop_rows_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22v_task_micro_loop_rows.csv`
- `raw_remote_manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/remote_tier4_22v_results_raw.json`
- `raw_remote_report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/remote_tier4_22v_report_raw.md`
- `remote_latest_manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22v_latest_manifest.json`
- `main_syntax_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/tier4_22i_main_syntax_normal (19).o`
- `aplx_binary`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/coral_reef (15).aplx`
- `elf_binary`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/coral_reef (16).elf`
- `elf_listing`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/coral_reef (15).txt`
- `spinnaker_reports_zip`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/reports (26).zip`
- `main_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/main (18).o`
- `host_interface_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/host_interface (17).o`
- `state_manager_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/state_manager (18).o`
- `synapse_manager_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/synapse_manager (18).o`
- `neuron_manager_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/neuron_manager (18).o`
- `router_object`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/router (16).o`
