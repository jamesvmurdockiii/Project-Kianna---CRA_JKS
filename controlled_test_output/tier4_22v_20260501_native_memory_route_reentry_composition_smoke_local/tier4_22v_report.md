# Tier 4.22v Tiny Native Memory-Route Reentry/Composition Custom-Runtime Smoke

- Generated: `2026-05-01T20:08:23+00:00`
- Mode: `local`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_local`

Tier 4.22v runs a 48-event signed stream through the custom runtime using native keyed context state, keyed route state, and keyed memory/working-state slots. The host writes context, route, and memory updates, then sends only key+cue+delay for each decision; the chip retrieves all three by key, computes feature=context[key]*route[key]*memory[key]*cue, scores the pre-update prediction, holds a two-event pending gap, then matures delayed credit against a local s16.15 reference.

## Claim Boundary

- `LOCAL`/`PREPARED` means the task reference, source bundle, and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means the minimal task-like loop matched local fixed-point reference and satisfied the predeclared task metrics on real SpiNNaker.
- This is not full native v2.1 memory/routing, not full CRA task learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22u_status: `pass`
- mode: `local`
- reference_status: `pass`
- reference_sequence_length: `48`
- reference_accuracy: `0.9375`
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
- native_route_slot_writes: `21`
- native_route_slot_reads: `48`
- native_route_max_slot_count: `4`
- native_route_values: `[-1, 1]`
- native_feature_source: `chip_context_memory_route_lookup_feature_transform`
- native_memory_slot_writes: `21`
- native_memory_slot_reads: `48`
- native_memory_max_slot_count: `4`
- native_memory_values: `[-1, 1]`
- next_step_if_passed: `Prepare cra_422ae and run the Tier 4.22v tiny native memory-route reentry/composition micro-task on EBRAINS.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.22u native memory-route smoke pass exists | `pass` | `== pass` | yes |
| main.c host syntax check pass | `pass` | `== pass` | yes |
| local task fixed-point reference generated | `pass` | `== pass` | yes |
| reference sequence length | `48` | `== 48` | yes |
| reference tail accuracy | `1` | `>= 1.0` | yes |
| reference second-half improves or matches first-half | `0.125` | `>= 0` | yes |
| reference pending gap depth | `2` | `== 2` | yes |
| reference max pending depth | `3` | `>= 3` | yes |
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
| reference final weight positive after native memory-route stream | `32768` | `> 0` | yes |
| reference final bias bounded near zero | `0` | `abs(raw) <= 32` | yes |
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
| source native context, route, and memory command constants exist | `CMD_WRITE_CONTEXT/CMD_WRITE_ROUTE_SLOT/CMD_WRITE_MEMORY_SLOT/CMD_SCHEDULE_MEMORY_ROUTE_CONTEXT_PENDING` | `custom runtime must expose native context plus memory-route state primitives` | yes |
| source native context write/read handlers use bounded C slots | `cra_state_write_context/cra_state_read_context` | `context state must be owned by the C runtime, not a host-only dictionary` | yes |
| source native keyed route write/read handlers exist | `cra_state_write_route_slot/cra_state_read_route_slot` | `keyed route state must be owned by the C runtime, not a host-only dictionary` | yes |
| source native keyed memory write/read handlers exist | `cra_state_write_memory_slot/cra_state_read_memory_slot` | `memory/working state must be owned by the C runtime, not a host-only dictionary` | yes |
| source native keyed memory-route schedule forms feature on chip | `feature = FP_MUL(FP_MUL(FP_MUL(context_value, route_value), memory_value), cue)` | `host must send key+cue, while the runtime retrieves context+route+memory slots by key and computes the scalar feature` | yes |
| source task loop can score pre-update predictions | `CMD_SCHEDULE_PENDING returns prediction_raw before maturation` | `task micro-loop must evaluate the decision before credit updates the readout` | yes |
| source task loop increments decision counter | `cra_state_record_decision` | `minimal task loop must count decisions separately from rewards` | yes |
| source pending horizons do not store future target | `pending_horizon_t has feature/prediction/due only` | `delayed-credit target must arrive at maturation, not be hidden in the pending record` | yes |

## Artifacts

- `reference_json`: `<repo>/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_local/tier4_22v_task_reference.json`
- `reference_csv`: `<repo>/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_local/tier4_22v_task_reference_rows.csv`
- `manifest_json`: `<repo>/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_local/tier4_22v_results.json`
- `report_md`: `<repo>/controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_local/tier4_22v_report.md`
