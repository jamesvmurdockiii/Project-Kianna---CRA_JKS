# Tier 4.22l Tiny Custom-Runtime Learning Parity

- Generated: `2026-05-01T02:23:48+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared`

Tier 4.22l compares a tiny chip-owned pending-horizon/readout update sequence against a local s16.15 fixed-point reference.

## Claim Boundary

- `LOCAL`/`PREPARED` means the reference, source bundle, and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means the tiny on-chip update sequence matched the local fixed-point reference within tolerance.
- This is not full CRA task learning, not v2.1 mechanism transfer, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22j_status: `pass`
- mode: `prepare`
- reference_status: `pass`
- reference_sequence_length: `4`
- reference_final_weight: `-0.125`
- reference_final_bias: `-0.125`
- jobmanager_command: `cra_422t/experiments/tier4_22l_custom_runtime_learning_parity.py --mode run-hardware --output-dir tier4_22l_job_output`
- upload_folder: `/Users/james/JKS:CRA/controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/ebrains_upload_bundle/cra_422t`
- stable_upload_folder: `/Users/james/JKS:CRA/ebrains_jobs/cra_422t`
- what_i_need_from_user: `Upload the generated cra_422t folder to EBRAINS/JobManager and run the emitted command; download returned files after completion.`
- next_step_if_passed: `Run the emitted EBRAINS command and ingest returned files.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.22j minimal learning-smoke pass exists | `pass` | `== pass` | yes |
| main.c host syntax check pass | `pass` | `== pass` | yes |
| local fixed-point reference generated | `pass` | `== pass` | yes |
| upload bundle created | `/Users/james/JKS:CRA/controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/ebrains_upload_bundle/cra_422t` | `exists` | yes |
| runtime source included | `/Users/james/JKS:CRA/controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/ebrains_upload_bundle/cra_422t/coral_reef_spinnaker/spinnaker_runtime` | `exists` | yes |
| run-hardware command emitted | `cra_422t/experiments/tier4_22l_custom_runtime_learning_parity.py --mode run-hardware --output-dir tier4_22l_job_output` | `contains --mode run-hardware` | yes |
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

## Artifacts

- `reference_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/tier4_22l_reference.json`
- `reference_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/tier4_22l_parity_reference.csv`
- `upload_bundle`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/ebrains_upload_bundle/cra_422t`
- `job_readme`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/ebrains_upload_bundle/cra_422t/README_TIER4_22L_JOB.md`
- `stable_upload_folder`: `/Users/james/JKS:CRA/ebrains_jobs/cra_422t`
- `manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/tier4_22l_results.json`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/tier4_22l_report.md`
