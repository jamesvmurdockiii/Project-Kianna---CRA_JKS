# Tier 4.22w Tiny Native Decoupled Memory-Route Composition Custom-Runtime Smoke

- Generated: `2026-05-01T20:40:04+00:00`
- Mode: `run-hardware`
- Status: **FAIL**
- Output directory: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output`

Tier 4.22w runs a 48-event signed stream through the custom runtime using native keyed context state, keyed route state, and keyed memory/working-state slots. The host writes context, route, and memory updates, then sends independent context_key, route_key, memory_key, cue, and delay for each decision; the chip retrieves all three by their own keys, computes feature=context[context_key]*route[route_key]*memory[memory_key]*cue, scores the pre-update prediction, holds a two-event pending gap, then matures delayed credit against a local s16.15 reference.

## Claim Boundary

- `LOCAL`/`PREPARED` means the task reference, source bundle, and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means the minimal task-like loop matched local fixed-point reference and satisfied the predeclared task metrics on real SpiNNaker.
- This is not full native v2.1 memory/routing, not full CRA task learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22v_status: `missing`
- mode: `run-hardware`
- reference_status: `pass`
- reference_sequence_length: `48`
- reference_accuracy: `0.958333`
- reference_tail_accuracy: `1`
- reference_final_weight: `1`
- reference_final_bias: `0`
- reference_pending_gap_depth: `2`
- reference_max_pending_depth: `3`
- observed_max_pending_depth: `None`
- hardware_target_configured: `False`
- spinnaker_hostname: ``
- selected_dest_cpu: `1`
- aplx_build_status: `fail`
- app_load_status: `not_attempted`
- task_micro_loop_status: `not_attempted`
- observed_accuracy: `None`
- observed_tail_accuracy: `None`
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
- final_pending_created: `None`
- final_pending_matured: `None`
- final_reward_events: `None`
- final_decisions: `None`
- final_readout_weight: `None`
- final_readout_bias: `None`
- final_route_slot_writes: `-1`
- final_route_slot_hits: `-1`
- final_route_slot_misses: `-1`
- final_active_route_slots: `-1`
- final_memory_slot_writes: `-1`
- final_memory_slot_hits: `-1`
- final_memory_slot_misses: `-1`
- final_active_memory_slots: `-1`
- next_step_if_passed: `Ingest returned Tier 4.22w files; if it passes, continue with the next native custom-runtime integration gate, likely compact native v2 bridge integration over the decoupled state primitive.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22w_native_decoupled_memory_route_composition_smoke_20260501_0001` | `expected current source` | yes |
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
| runtime native context, route, memory, and decoupled schedule command constants exist | `CMD_WRITE_CONTEXT/CMD_WRITE_ROUTE_SLOT/CMD_WRITE_MEMORY_SLOT/CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING` | `custom runtime must expose native context plus independently keyed memory-route state primitives` | yes |
| runtime native context write/read handlers use bounded C slots | `cra_state_write_context/cra_state_read_context` | `context state must be owned by the C runtime, not a host-only dictionary` | yes |
| runtime native keyed route write/read handlers exist | `cra_state_write_route_slot/cra_state_read_route_slot` | `keyed route state must be owned by the C runtime, not a host-only dictionary` | yes |
| runtime native keyed memory write/read handlers exist | `cra_state_write_memory_slot/cra_state_read_memory_slot` | `memory/working state must be owned by the C runtime, not a host-only dictionary` | yes |
| runtime native decoupled keyed memory-route schedule forms feature on chip | `feature = FP_MUL(FP_MUL(FP_MUL(context_value, route_value), memory_value), cue)` | `host must send independent context/route/memory keys plus cue/delay, while the runtime retrieves all three slots and computes the scalar feature` | yes |
| runtime task loop can score pre-update predictions | `CMD_SCHEDULE_PENDING returns prediction_raw before maturation` | `task micro-loop must evaluate the decision before credit updates the readout` | yes |
| runtime task loop increments decision counter | `cra_state_record_decision` | `minimal task loop must count decisions separately from rewards` | yes |
| runtime pending horizons do not store future target | `pending_horizon_t has feature/prediction/due only` | `delayed-credit target must arrive at maturation, not be hidden in the pending record` | yes |
| hardware target acquired | `{"reason": "blocked_before_target_acquisition", "status": "not_attempted"}` | `status == pass and hostname/IP/transceiver acquired` | no |
| custom runtime .aplx build pass | `fail` | `== pass` | no |
| custom runtime app load pass | `not_attempted` | `== pass` | no |
| minimal task micro-loop pass | `not_attempted` | `== pass` | no |
| all context writes succeeded | `[]` | `all True` | no |
| all route-slot writes succeeded | `[]` | `all True` | no |
| all memory-slot writes succeeded | `[]` | `all True` | no |
| all schedule commands succeeded | `[]` | `all True` | no |
| all mature commands succeeded | `[]` | `all True` | no |
| one pending matured per step | `[]` | `all == 1` | no |
| chip-computed features match local reference | `[]` | `abs(delta) <= 1` | no |
| chip-retrieved context values match local reference | `[]` | `abs(delta) <= 1` | no |
| chip-retrieved context confidence matches local reference | `[]` | `abs(delta) <= 1` | no |
| chip-retrieved route-slot values match local reference | `[]` | `abs(delta) <= 1` | no |
| chip-retrieved route-slot confidence matches local reference | `[]` | `abs(delta) <= 1` | no |
| chip-retrieved memory-slot values match local reference | `[]` | `abs(delta) <= 1` | no |
| chip-retrieved memory-slot confidence matches local reference | `[]` | `abs(delta) <= 1` | no |
| chip-returned keyed context IDs match requested keys | `[]` | `all True` | no |
| chip-returned keyed route IDs match requested keys | `[]` | `all True` | no |
| chip-returned keyed memory IDs match requested keys | `[]` | `all True` | no |
| predictions match local reference | `[]` | `abs(delta) <= 1` | no |
| weights match local reference | `[]` | `abs(delta) <= 1` | no |
| biases match local reference | `[]` | `abs(delta) <= 1` | no |
| observed tail accuracy | `None` | `>= 1.0` | no |
| observed second-half improves or matches first-half | `None` | `>= 0` | no |
| observed max pending depth | `None` | `>= 3` | no |
| observed task metrics match reference | `{}` | `accuracy/tail/gain equal reference` | no |
| pending created count final | `None` | `== 48` | no |
| pending matured count final | `None` | `== 48` | no |
| reward events final | `None` | `== 48` | no |
| decisions final | `None` | `== 48` | no |
| active pending cleared final | `None` | `== 0` | no |
| context slot writes final | `None` | `== 18` | no |
| context slot hits final | `None` | `>= 48` | no |
| context slot misses final | `None` | `== 0` | no |
| active context slots final | `None` | `>= 4` | no |
| route-slot readback final succeeds | `[]` | `all True` | no |
| observed route-slot writes final | `-1` | `== 15` | no |
| observed active route slots final | `-1` | `>= 4` | no |
| route-slot hits final | `-1` | `>= 48` | no |
| route-slot misses final | `-1` | `== 0` | no |
| memory-slot readback final succeeds | `[]` | `all True` | no |
| observed memory-slot writes final | `-1` | `== 18` | no |
| observed active memory slots final | `-1` | `>= 4` | no |
| memory-slot hits final | `-1` | `>= 48` | no |
| memory-slot misses final | `-1` | `== 0` | no |
| final weight matches reference | `None` | `== 32768 +/- 1` | no |
| final bias matches reference | `None` | `== 0 +/- 1` | no |
| synthetic fallback zero | `0` | `== 0` | yes |

## Artifacts

- `reference_json`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22w_task_reference.json`
- `reference_csv`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22w_task_reference_rows.csv`
- `environment_json`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22w_environment.json`
- `target_acquisition_json`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22w_target_acquisition.json`
- `host_test_stdout`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22i_host_test_stdout.txt`
- `host_test_stderr`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22i_host_test_stderr.txt`
- `main_syntax_stdout`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22i_main_syntax_normal_stdout.txt`
- `main_syntax_stderr`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22i_main_syntax_normal_stderr.txt`
- `aplx_build_stdout`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22i_aplx_build_stdout.txt`
- `aplx_build_stderr`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22i_aplx_build_stderr.txt`
- `load_result_json`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22w_load_result.json`
- `task_micro_loop_result_json`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22w_task_micro_loop_result.json`
- `task_micro_loop_rows_csv`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22w_task_micro_loop_rows.csv`
- `manifest_json`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22w_results.json`
- `report_md`: `/tmp/job13780689853698401094.tmp/tier4_22w_job_output/tier4_22w_report.md`
