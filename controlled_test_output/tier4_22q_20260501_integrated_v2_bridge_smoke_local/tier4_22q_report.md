# Tier 4.22q Tiny Integrated V2 Bridge Custom-Runtime Smoke

- Generated: `2026-05-01T04:30:11+00:00`
- Mode: `local`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_local`

Tier 4.22q runs a 30-event signed stream produced by a tiny host-side keyed-context plus routing bridge through the custom runtime. Each event is scored from the chip's pre-update prediction, held across a two-event pending gap, then matured in order with delayed credit and checked against a local s16.15 reference.

## Claim Boundary

- `LOCAL`/`PREPARED` means the task reference, source bundle, and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means the minimal task-like loop matched local fixed-point reference and satisfied the predeclared task metrics on real SpiNNaker.
- This is not native v2.1 on-chip memory/routing, not full CRA task learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22p_status: `pass`
- mode: `local`
- reference_status: `pass`
- reference_sequence_length: `30`
- reference_accuracy: `0.933333`
- reference_tail_accuracy: `1`
- reference_final_weight: `1`
- reference_final_bias: `0`
- reference_pending_gap_depth: `2`
- reference_max_pending_depth: `3`
- bridge_context_updates: `9`
- bridge_route_updates: `9`
- bridge_max_slot_count: `3`
- next_step_if_passed: `Prepare cra_422z and run the Tier 4.22q tiny integrated-v2 bridge micro-task on EBRAINS.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.22p A-B-A reentry micro-task pass exists | `pass` | `== pass` | yes |
| main.c host syntax check pass | `pass` | `== pass` | yes |
| local task fixed-point reference generated | `pass` | `== pass` | yes |
| reference sequence length | `30` | `== 30` | yes |
| reference tail accuracy | `1` | `>= 1.0` | yes |
| reference second-half improves or matches first-half | `0.133333` | `>= 0` | yes |
| reference pending gap depth | `2` | `== 2` | yes |
| reference max pending depth | `3` | `>= 3` | yes |
| reference bridge context updates observed | `9` | `> 0` | yes |
| reference bridge route updates observed | `9` | `> 0` | yes |
| reference bridge retained three keyed slots | `3` | `>= 3` | yes |
| reference bridge feature source declared | `host_keyed_context_route_transform` | `== host_keyed_context_route_transform` | yes |
| reference final weight positive after integrated bridge stream | `32768` | `> 0` | yes |
| reference final bias near zero | `0` | `abs(raw) <= 2` | yes |
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
| source task loop can score pre-update predictions | `CMD_SCHEDULE_PENDING returns prediction_raw before maturation` | `task micro-loop must evaluate the decision before credit updates the readout` | yes |
| source task loop increments decision counter | `cra_state_record_decision` | `minimal task loop must count decisions separately from rewards` | yes |
| source pending horizons do not store future target | `pending_horizon_t has feature/prediction/due only` | `delayed-credit target must arrive at maturation, not be hidden in the pending record` | yes |

## Artifacts

- `reference_json`: `<repo>/controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_local/tier4_22q_task_reference.json`
- `reference_csv`: `<repo>/controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_local/tier4_22q_task_reference_rows.csv`
- `manifest_json`: `<repo>/controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_local/tier4_22q_results.json`
- `report_md`: `<repo>/controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_local/tier4_22q_report.md`
