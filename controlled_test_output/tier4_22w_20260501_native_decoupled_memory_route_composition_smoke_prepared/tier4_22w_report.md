# Tier 4.22w Tiny Native Decoupled Memory-Route Composition Custom-Runtime Smoke

- Generated: `2026-05-01T20:32:16+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared`

Tier 4.22w runs a 48-event signed stream through the custom runtime using native keyed context state, keyed route state, and keyed memory/working-state slots. The host writes context, route, and memory updates, then sends independent context_key, route_key, memory_key, cue, and delay for each decision; the chip retrieves all three by their own keys, computes feature=context[context_key]*route[route_key]*memory[memory_key]*cue, scores the pre-update prediction, holds a two-event pending gap, then matures delayed credit against a local s16.15 reference.

## Claim Boundary

- `LOCAL`/`PREPARED` means the task reference, source bundle, and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means the minimal task-like loop matched local fixed-point reference and satisfied the predeclared task metrics on real SpiNNaker.
- This is not full native v2.1 memory/routing, not full CRA task learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22v_status: `pass`
- mode: `prepare`
- reference_status: `pass`
- reference_sequence_length: `48`
- reference_accuracy: `0.958333`
- reference_tail_accuracy: `1`
- reference_final_weight: `1`
- reference_final_bias: `0`
- reference_pending_gap_depth: `2`
- reference_max_pending_depth: `3`
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
- jobmanager_command: `cra_422af/experiments/tier4_22w_native_decoupled_memory_route_composition_smoke.py --mode run-hardware --output-dir tier4_22w_job_output`
- upload_folder: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared/ebrains_upload_bundle/cra_422af`
- stable_upload_folder: `<repo>/ebrains_jobs/cra_422af`
- what_i_need_from_user: `Upload the generated cra_422af folder to EBRAINS/JobManager and run the emitted command; download returned files after completion.`
- next_step_if_passed: `Run the emitted EBRAINS command and ingest returned files.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.22v native memory-route reentry/composition smoke pass exists | `pass` | `== pass` | yes |
| main.c host syntax check pass | `pass` | `== pass` | yes |
| local task fixed-point reference generated | `pass` | `== pass` | yes |
| reference tail accuracy | `1` | `>= 1.0` | yes |
| reference pending gap depth | `2` | `== 2` | yes |
| reference max pending depth | `3` | `>= 3` | yes |
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
| upload bundle created | `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared/ebrains_upload_bundle/cra_422af` | `exists` | yes |
| runtime source included | `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared/ebrains_upload_bundle/cra_422af/coral_reef_spinnaker/spinnaker_runtime` | `exists` | yes |
| run-hardware command emitted | `cra_422af/experiments/tier4_22w_native_decoupled_memory_route_composition_smoke.py --mode run-hardware --output-dir tier4_22w_job_output` | `contains --mode run-hardware` | yes |
| source CMD_SCHEDULE_PENDING defined | `CMD_SCHEDULE_PENDING 9` | `config.h defines opcode` | yes |
| source CMD_MATURE_PENDING defined | `CMD_MATURE_PENDING 10` | `config.h defines opcode` | yes |
| source learning opcodes host-tested | `assert command constants` | `host tests cover opcodes` | yes |
| source controller exposes schedule command | `schedule_pending_decision` | `Python host can schedule delayed-credit state on board` | yes |
| source controller exposes mature command | `mature_pending` | `Python host can mature delayed-credit state on board` | yes |
| source runtime schedule handler exists | `_handle_schedule_pending` | `runtime computes prediction and schedules pending horizon` | yes |
| source runtime mature handler exists | `_handle_mature_pending` | `runtime matures pending horizon and updates readout` | yes |
| source learning commands dispatched | `case CMD_SCHEDULE_PENDING / CMD_MATURE_PENDING` | `SDP dispatcher routes learning commands` | yes |
| source fixed-point helper is s16.15 | `FP_SHIFT 15` | `config.h defines the same fixed-point scale as the Python reference` | yes |
| source readout prediction equation present | `FP_MUL(readout_weight, feature) + readout_bias` | `runtime prediction must match local parity reference` | yes |
| source readout update equation present | `delta_w = lr * error * feature; delta_b = lr * error` | `runtime maturation must match local parity reference` | yes |
| source mature command supports explicit mature_timestep | `msg->arg3 != 0 ? msg->arg3 : g_timestep` | `parity run uses explicit due_timestep to avoid timer-race false failures` | yes |
| source controller exposes returned due_timestep | `due_timestep` | `hardware parity can mature exactly the pending event it scheduled` | yes |
| source native context, route, memory, and decoupled schedule command constants exist | `CMD_WRITE_CONTEXT/CMD_WRITE_ROUTE_SLOT/CMD_WRITE_MEMORY_SLOT/CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING` | `custom runtime must expose native context plus independently keyed memory-route state primitives` | yes |
| source native context write/read handlers use bounded C slots | `cra_state_write_context/cra_state_read_context` | `context state must be owned by the C runtime, not a host-only dictionary` | yes |
| source native keyed route write/read handlers exist | `cra_state_write_route_slot/cra_state_read_route_slot` | `keyed route state must be owned by the C runtime, not a host-only dictionary` | yes |
| source native keyed memory write/read handlers exist | `cra_state_write_memory_slot/cra_state_read_memory_slot` | `memory/working state must be owned by the C runtime, not a host-only dictionary` | yes |
| source native decoupled keyed memory-route schedule forms feature on chip | `feature = FP_MUL(FP_MUL(FP_MUL(context_value, route_value), memory_value), cue)` | `host must send independent context/route/memory keys plus cue/delay, while the runtime retrieves all three slots and computes the scalar feature` | yes |
| source task loop can score pre-update predictions | `CMD_SCHEDULE_PENDING returns prediction_raw before maturation` | `task micro-loop must evaluate the decision before credit updates the readout` | yes |
| source task loop increments decision counter | `cra_state_record_decision` | `minimal task loop must count decisions separately from rewards` | yes |
| source pending horizons do not store future target | `pending_horizon_t has feature/prediction/due only` | `delayed-credit target must arrive at maturation, not be hidden in the pending record` | yes |
| bundle CMD_SCHEDULE_PENDING defined | `CMD_SCHEDULE_PENDING 9` | `config.h defines opcode` | yes |
| bundle CMD_MATURE_PENDING defined | `CMD_MATURE_PENDING 10` | `config.h defines opcode` | yes |
| bundle learning opcodes host-tested | `assert command constants` | `host tests cover opcodes` | yes |
| bundle controller exposes schedule command | `schedule_pending_decision` | `Python host can schedule delayed-credit state on board` | yes |
| bundle controller exposes mature command | `mature_pending` | `Python host can mature delayed-credit state on board` | yes |
| bundle runtime schedule handler exists | `_handle_schedule_pending` | `runtime computes prediction and schedules pending horizon` | yes |
| bundle runtime mature handler exists | `_handle_mature_pending` | `runtime matures pending horizon and updates readout` | yes |
| bundle learning commands dispatched | `case CMD_SCHEDULE_PENDING / CMD_MATURE_PENDING` | `SDP dispatcher routes learning commands` | yes |
| bundle fixed-point helper is s16.15 | `FP_SHIFT 15` | `config.h defines the same fixed-point scale as the Python reference` | yes |
| bundle readout prediction equation present | `FP_MUL(readout_weight, feature) + readout_bias` | `runtime prediction must match local parity reference` | yes |
| bundle readout update equation present | `delta_w = lr * error * feature; delta_b = lr * error` | `runtime maturation must match local parity reference` | yes |
| bundle mature command supports explicit mature_timestep | `msg->arg3 != 0 ? msg->arg3 : g_timestep` | `parity run uses explicit due_timestep to avoid timer-race false failures` | yes |
| bundle controller exposes returned due_timestep | `due_timestep` | `hardware parity can mature exactly the pending event it scheduled` | yes |
| bundle native context, route, memory, and decoupled schedule command constants exist | `CMD_WRITE_CONTEXT/CMD_WRITE_ROUTE_SLOT/CMD_WRITE_MEMORY_SLOT/CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING` | `custom runtime must expose native context plus independently keyed memory-route state primitives` | yes |
| bundle native context write/read handlers use bounded C slots | `cra_state_write_context/cra_state_read_context` | `context state must be owned by the C runtime, not a host-only dictionary` | yes |
| bundle native keyed route write/read handlers exist | `cra_state_write_route_slot/cra_state_read_route_slot` | `keyed route state must be owned by the C runtime, not a host-only dictionary` | yes |
| bundle native keyed memory write/read handlers exist | `cra_state_write_memory_slot/cra_state_read_memory_slot` | `memory/working state must be owned by the C runtime, not a host-only dictionary` | yes |
| bundle native decoupled keyed memory-route schedule forms feature on chip | `feature = FP_MUL(FP_MUL(FP_MUL(context_value, route_value), memory_value), cue)` | `host must send independent context/route/memory keys plus cue/delay, while the runtime retrieves all three slots and computes the scalar feature` | yes |
| bundle task loop can score pre-update predictions | `CMD_SCHEDULE_PENDING returns prediction_raw before maturation` | `task micro-loop must evaluate the decision before credit updates the readout` | yes |
| bundle task loop increments decision counter | `cra_state_record_decision` | `minimal task loop must count decisions separately from rewards` | yes |
| bundle pending horizons do not store future target | `pending_horizon_t has feature/prediction/due only` | `delayed-credit target must arrive at maturation, not be hidden in the pending record` | yes |

## Artifacts

- `reference_json`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared/tier4_22w_task_reference.json`
- `reference_csv`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared/tier4_22w_task_reference_rows.csv`
- `upload_bundle`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared/ebrains_upload_bundle/cra_422af`
- `job_readme`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared/ebrains_upload_bundle/cra_422af/README_TIER4_22W_JOB.md`
- `stable_upload_folder`: `<repo>/ebrains_jobs/cra_422af`
- `manifest_json`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared/tier4_22w_results.json`
- `report_md`: `<repo>/controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared/tier4_22w_report.md`
