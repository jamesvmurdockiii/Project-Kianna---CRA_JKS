# Tier 4.22w Tiny Native Decoupled Memory-Route Composition Custom-Runtime Smoke

- Generated: `2026-05-01T21:14:30+00:00`
- Mode: `ingest`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested`

Tier 4.22w runs a 48-event signed stream through the custom runtime using native keyed context state, keyed route state, and keyed memory/working-state slots. The host writes context, route, and memory updates, then sends independent context_key, route_key, memory_key, cue, and delay for each decision; the chip retrieves all three by their own keys, computes feature=context[context_key]*route[route_key]*memory[memory_key]*cue, scores the pre-update prediction, holds a two-event pending gap, then matures delayed credit against a local s16.15 reference.

## Claim Boundary

- `LOCAL`/`PREPARED` means the task reference, source bundle, and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means the minimal task-like loop matched local fixed-point reference and satisfied the predeclared task metrics on real SpiNNaker.
- This is not full native v2.1 memory/routing, not full CRA task learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22v_status: `missing`
- mode: `ingest`
- reference_status: `pass`
- reference_sequence_length: `48`
- reference_accuracy: `0.958333`
- reference_tail_accuracy: `1`
- reference_final_weight: `1`
- reference_final_bias: `0`
- reference_pending_gap_depth: `2`
- reference_max_pending_depth: `3`
- observed_max_pending_depth: `3`
- hardware_target_configured: `True`
- spinnaker_hostname: `10.11.236.9`
- selected_dest_cpu: `4`
- aplx_build_status: `pass`
- app_load_status: `pass`
- task_micro_loop_status: `pass`
- observed_accuracy: `0.958333`
- observed_tail_accuracy: `1`
- native_context_keys: `["ctx_A", "ctx_B", "ctx_C", "ctx_D"]`
- native_context_key_ids: `[101, 202, 303, 404]`
- native_context_writes: `18`
- native_context_reads: `48`
- native_context_max_slot_count: `4`
- native_route_keys: `["route_A", "route_B", "route_C", "route_D"]`
- native_route_key_ids: `[1101, 1202, 1303, 1404]`
- native_route_slot_writes: `15`
- native_route_slot_reads: `48`
- native_route_max_slot_count: `4`
- native_route_values: `[-1, 1]`
- native_feature_source: `chip_decoupled_context_route_memory_lookup_feature_transform`
- native_memory_keys: `["mem_A", "mem_B", "mem_C", "mem_D"]`
- native_memory_key_ids: `[2101, 2202, 2303, 2404]`
- native_memory_slot_writes: `18`
- native_memory_slot_reads: `48`
- native_memory_max_slot_count: `4`
- native_memory_values: `[-1, 1]`
- final_pending_created: `48`
- final_pending_matured: `48`
- final_reward_events: `48`
- final_decisions: `48`
- final_readout_weight: `1`
- final_readout_bias: `0`
- final_route_slot_writes: `15`
- final_route_slot_hits: `52`
- final_route_slot_misses: `0`
- final_active_route_slots: `4`
- final_memory_slot_writes: `18`
- final_memory_slot_hits: `52`
- final_memory_slot_misses: `0`
- final_active_memory_slots: `4`
- next_step_if_passed: `Ingest returned Tier 4.22w files; if it passes, continue with the next native custom-runtime integration gate, likely compact native v2 bridge integration over the decoupled state primitive.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22w_native_decoupled_memory_route_composition_smoke_20260501_0002_runtime_profile` | `expected current source` | yes |
| Tier 4.22v native memory-route reentry/composition smoke pass exists or fresh bundle | `missing` | `== pass OR missing in fresh EBRAINS bundle` | yes |
| local task fixed-point reference generated | `pass` | `== pass` | yes |
| reference native context writes observed | `18` | `> 0` | yes |
| reference native context reads observed | `48` | `== 48` | yes |
| reference native context retained four keyed slots | `4` | `>= 4` | yes |
| reference native keyed route writes observed | `15` | `> 0` | yes |
| reference native keyed route reads observed | `48` | `== 48` | yes |
| reference native keyed route retained four slots | `4` | `>= 4` | yes |
| reference native route values cover both signs | `[-1, 1]` | `contains -1 and 1` | yes |
| reference native keyed memory writes observed | `18` | `> 0` | yes |
| reference native keyed memory reads observed | `48` | `== 48` | yes |
| reference native keyed memory retained four slots | `4` | `>= 4` | yes |
| reference native memory values cover both signs | `[-1, 1]` | `contains -1 and 1` | yes |
| reference native feature source declared | `chip_decoupled_context_route_memory_lookup_feature_transform` | `== chip_decoupled_context_route_memory_lookup_feature_transform` | yes |
| custom C host tests pass | `pass` | `== pass` | yes |
| main.c host syntax check pass | `pass` | `== pass` | yes |
| hardware runtime profile selected | `decoupled_memory_route` | `== decoupled_memory_route` | yes |
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
| runtime runtime supports hardware profiles | `RUNTIME_PROFILE=decoupled_memory_route` | `hardware build must be able to compile only the native primitive handlers required by this tier` | yes |
| runtime native context, route, memory, and decoupled schedule command constants exist | `CMD_WRITE_CONTEXT/CMD_WRITE_ROUTE_SLOT/CMD_WRITE_MEMORY_SLOT/CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING` | `custom runtime must expose native context plus independently keyed memory-route state primitives` | yes |
| runtime native context write/read handlers use bounded C slots | `cra_state_write_context/cra_state_read_context` | `context state must be owned by the C runtime, not a host-only dictionary` | yes |
| runtime native keyed route write/read handlers exist | `cra_state_write_route_slot/cra_state_read_route_slot` | `keyed route state must be owned by the C runtime, not a host-only dictionary` | yes |
| runtime native keyed memory write/read handlers exist | `cra_state_write_memory_slot/cra_state_read_memory_slot` | `memory/working state must be owned by the C runtime, not a host-only dictionary` | yes |
| runtime native decoupled keyed memory-route schedule forms feature on chip | `feature = FP_MUL(FP_MUL(FP_MUL(context_value, route_value), memory_value), cue)` | `host must send independent context/route/memory keys plus cue/delay, while the runtime retrieves all three slots and computes the scalar feature` | yes |
| runtime task loop can score pre-update predictions | `CMD_SCHEDULE_PENDING returns prediction_raw before maturation` | `task micro-loop must evaluate the decision before credit updates the readout` | yes |
| runtime task loop increments decision counter | `cra_state_record_decision` | `minimal task loop must count decisions separately from rewards` | yes |
| runtime pending horizons do not store future target | `pending_horizon_t has feature/prediction/due only` | `delayed-credit target must arrive at maturation, not be hidden in the pending record` | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spynnaker.cfg"], "reason": "no explicit hostname/config/environment target found", "status": "fail"}, {"dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.236.9", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 42.90684725996107, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.236.9"}], "dest_cpu": 4, "dest_x": 0, "dest_y": 0, "hostname": "10.11.236.9", "method": "pyNN.spiNNaker_probe", "notes": ["acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname", "requested dest_cpu 1 was occupied; selected free core 4"], "occupied_cores": [1, 2, 3], "probe_population_size": 1, "probe_run_ms": 1.0, "probe_timestep_ms": 1.0, "runtime_seconds": 42.90684725996107, "setup_kwargs": {"timestep": 1.0}, "status": "pass", "target_ipaddress": "10.11.236.9"}` | `status == pass and hostname/IP/transceiver acquired` | yes |
| custom runtime .aplx build pass | `pass` | `== pass` | yes |
| custom runtime app load pass | `pass` | `== pass` | yes |
| minimal task micro-loop pass | `pass` | `== pass` | yes |
| all context writes succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| all route-slot writes succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| all memory-slot writes succeeded | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
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
| chip-returned keyed context IDs match requested keys | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| chip-returned keyed route IDs match requested keys | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| chip-returned keyed memory IDs match requested keys | `[true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true]` | `all True` | yes |
| predictions match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| weights match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| biases match local reference | `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` | `abs(delta) <= 1` | yes |
| observed tail accuracy | `1` | `>= 1.0` | yes |
| observed second-half improves or matches first-half | `0.0833333` | `>= 0` | yes |
| observed max pending depth | `3` | `>= 3` | yes |
| observed task metrics match reference | `{"accuracy": 0.9583333333333334, "accuracy_gain": 0.08333333333333337, "correct_count": 46, "final_abs_error": 0.0, "first_half_accuracy": 0.9166666666666666, "second_half_accuracy": 1.0, "tail_accuracy": 1.0, "tail_window": 6}` | `accuracy/tail/gain equal reference` | yes |
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
| observed route-slot writes final | `15` | `== 15` | yes |
| observed active route slots final | `4` | `>= 4` | yes |
| route-slot hits final | `52` | `>= 48` | yes |
| route-slot misses final | `0` | `== 0` | yes |
| memory-slot readback final succeeds | `[true, true, true, true]` | `all True` | yes |
| observed memory-slot writes final | `18` | `== 18` | yes |
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
| 3 | `1.0` | `1.0` | `0` | `True` | `24576` | `24576` | `24576` | `24576` |
| 4 | `1.0` | `1.0` | `16384` | `True` | `28672` | `28672` | `28672` | `28672` |
| 5 | `-1.0` | `-1.0` | `0` | `False` | `36864` | `36864` | `20480` | `20480` |
| 6 | `1.0` | `1.0` | `49152` | `True` | `32768` | `32768` | `16384` | `16384` |
| 7 | `-1.0` | `-1.0` | `0` | `False` | `40960` | `40960` | `8192` | `8192` |
| 8 | `1.0` | `1.0` | `57344` | `True` | `34816` | `34816` | `2048` | `2048` |
| 9 | `1.0` | `1.0` | `49152` | `True` | `30720` | `30720` | `-2048` | `-2048` |
| 10 | `1.0` | `1.0` | `49152` | `True` | `26624` | `26624` | `-6144` | `-6144` |
| 11 | `-1.0` | `-1.0` | `-32768` | `True` | `26624` | `26624` | `-6144` | `-6144` |
| 12 | `1.0` | `1.0` | `28672` | `True` | `27648` | `27648` | `-5120` | `-5120` |
| 13 | `1.0` | `1.0` | `20480` | `True` | `30720` | `30720` | `-2048` | `-2048` |
| 14 | `-1.0` | `-1.0` | `-32768` | `True` | `30720` | `30720` | `-2048` | `-2048` |
| 15 | `1.0` | `1.0` | `22528` | `True` | `33280` | `33280` | `512` | `512` |
| 16 | `1.0` | `1.0` | `28672` | `True` | `34304` | `34304` | `1536` | `1536` |
| 17 | `-1.0` | `-1.0` | `-32768` | `True` | `34304` | `34304` | `1536` | `1536` |
| 18 | `-1.0` | `-1.0` | `-32768` | `True` | `34304` | `34304` | `1536` | `1536` |
| 19 | `-1.0` | `-1.0` | `-32768` | `True` | `34304` | `34304` | `1536` | `1536` |
| 20 | `-1.0` | `-1.0` | `-32768` | `True` | `34304` | `34304` | `1536` | `1536` |
| 21 | `1.0` | `1.0` | `35840` | `True` | `33536` | `33536` | `768` | `768` |
| 22 | `-1.0` | `-1.0` | `-32768` | `True` | `33536` | `33536` | `768` | `768` |
| 23 | `1.0` | `1.0` | `35840` | `True` | `32768` | `32768` | `0` | `0` |
| 24 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 25 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 26 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 27 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 28 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 29 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 30 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 31 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 32 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 33 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 34 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 35 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 36 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 37 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 38 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 39 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 40 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 41 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 42 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 43 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 44 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 45 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 46 | `-1.0` | `-1.0` | `-32768` | `True` | `32768` | `32768` | `0` | `0` |
| 47 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |
| 48 | `1.0` | `1.0` | `32768` | `True` | `32768` | `32768` | `0` | `0` |

## Artifacts

- `aplx_build_stderr`: `<jobmanager_tmp>`
- `aplx_build_stdout`: `<jobmanager_tmp>`
- `environment_json`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/tier4_22w_environment.json`
- `host_test_stderr`: `<jobmanager_tmp>`
- `host_test_stdout`: `<jobmanager_tmp>`
- `load_result_json`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/tier4_22w_load_result.json`
- `main_syntax_stderr`: `<jobmanager_tmp>`
- `main_syntax_stdout`: `<jobmanager_tmp>`
- `manifest_json`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/tier4_22w_results.json`
- `reference_csv`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/tier4_22w_task_reference_rows.csv`
- `reference_json`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/tier4_22w_task_reference.json`
- `report_md`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/tier4_22w_report.md`
- `runtime_profile_json`: `<jobmanager_tmp>`
- `target_acquisition_json`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/tier4_22w_target_acquisition.json`
- `task_micro_loop_result_json`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/tier4_22w_task_micro_loop_result.json`
- `task_micro_loop_rows_csv`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/tier4_22w_task_micro_loop_rows.csv`
- `raw_remote_manifest_json`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/remote_tier4_22w_results_raw.json`
- `raw_remote_report_md`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/remote_tier4_22w_report_raw.md`
- `remote_latest_manifest_json`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/tier4_22w_latest_manifest.json`
