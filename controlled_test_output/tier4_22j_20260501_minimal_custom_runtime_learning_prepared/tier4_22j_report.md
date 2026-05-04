# Tier 4.22j Minimal Custom-Runtime Closed-Loop Learning Smoke

- Generated: `2026-05-01T01:33:03+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_prepared`

Tier 4.22j tests a minimal chip-owned delayed-credit/readout update after the Tier 4.22i board command path passed.

## Claim Boundary

- `PREPARED` means the source bundle and command are ready, not hardware evidence.
- `PASS` in `run-hardware` means one delayed pending/readout update happened in the loaded custom runtime and was visible through compact readback.
- This is not full CRA task learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

## Summary

- tier4_22i_status: `pass`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.22i board roundtrip pass exists | `pass` | `== pass` | yes |
| main.c host syntax check pass | `pass` | `== pass` | yes |
| upload bundle created | `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_prepared/ebrains_upload_bundle/cra_422s` | `exists` | yes |
| runtime source included | `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_prepared/ebrains_upload_bundle/cra_422s/coral_reef_spinnaker/spinnaker_runtime` | `exists` | yes |
| run-hardware command emitted | `cra_422s/experiments/tier4_22j_minimal_custom_runtime_learning.py --mode run-hardware --output-dir tier4_22j_job_output` | `contains --mode run-hardware` | yes |
| source CMD_SCHEDULE_PENDING defined | `CMD_SCHEDULE_PENDING 9` | `config.h defines opcode` | yes |
| source CMD_MATURE_PENDING defined | `CMD_MATURE_PENDING 10` | `config.h defines opcode` | yes |
| source learning opcodes host-tested | `assert command constants` | `host tests cover opcodes` | yes |
| source controller exposes schedule command | `schedule_pending_decision` | `Python host can schedule delayed-credit state on board` | yes |
| source controller exposes mature command | `mature_pending` | `Python host can mature delayed-credit state on board` | yes |
| source runtime schedule handler exists | `_handle_schedule_pending` | `runtime computes prediction and schedules pending horizon` | yes |
| source runtime mature handler exists | `_handle_mature_pending` | `runtime matures pending horizon and updates readout` | yes |
| source learning commands dispatched | `case CMD_SCHEDULE_PENDING / CMD_MATURE_PENDING` | `SDP dispatcher routes learning commands` | yes |
| source host sends official sdp_msg_t command header | `struct.pack("<HHIII"` | `host must place opcode in cmd_rc and use arg1/arg2/arg3 before data[]` | yes |
| source host parses cmd_rc before data payload | `struct.unpack_from("<HHIII", data, 10)` | `board replies expose cmd/status in cmd_rc before data[] on UDP SDP` | yes |
| source runtime dispatch reads cmd_rc | `msg->cmd_rc` | `Spin1API callback receives an sdp_msg_t whose data[0] follows cmd_rc/seq/args` | yes |
| source runtime command args use arg1-arg3 | `msg->arg1/msg->arg2/msg->arg3` | `simple CRA commands use official SDP argument fields instead of hidden data offsets` | yes |
| source runtime replies put cmd/status into cmd_rc | `reply->cmd_rc` | `host parser expects cmd/status in the command header and optional state bytes in data[]` | yes |
| source host stub mirrors command-header fields | `cmd_rc/seq/arg1/arg2/arg3` | `local syntax guard must expose the real Spin1API command header fields` | yes |
| bundle CMD_SCHEDULE_PENDING defined | `CMD_SCHEDULE_PENDING 9` | `config.h defines opcode` | yes |
| bundle CMD_MATURE_PENDING defined | `CMD_MATURE_PENDING 10` | `config.h defines opcode` | yes |
| bundle learning opcodes host-tested | `assert command constants` | `host tests cover opcodes` | yes |
| bundle controller exposes schedule command | `schedule_pending_decision` | `Python host can schedule delayed-credit state on board` | yes |
| bundle controller exposes mature command | `mature_pending` | `Python host can mature delayed-credit state on board` | yes |
| bundle runtime schedule handler exists | `_handle_schedule_pending` | `runtime computes prediction and schedules pending horizon` | yes |
| bundle runtime mature handler exists | `_handle_mature_pending` | `runtime matures pending horizon and updates readout` | yes |
| bundle learning commands dispatched | `case CMD_SCHEDULE_PENDING / CMD_MATURE_PENDING` | `SDP dispatcher routes learning commands` | yes |
| bundle host sends official sdp_msg_t command header | `struct.pack("<HHIII"` | `host must place opcode in cmd_rc and use arg1/arg2/arg3 before data[]` | yes |
| bundle host parses cmd_rc before data payload | `struct.unpack_from("<HHIII", data, 10)` | `board replies expose cmd/status in cmd_rc before data[] on UDP SDP` | yes |
| bundle runtime dispatch reads cmd_rc | `msg->cmd_rc` | `Spin1API callback receives an sdp_msg_t whose data[0] follows cmd_rc/seq/args` | yes |
| bundle runtime command args use arg1-arg3 | `msg->arg1/msg->arg2/msg->arg3` | `simple CRA commands use official SDP argument fields instead of hidden data offsets` | yes |
| bundle runtime replies put cmd/status into cmd_rc | `reply->cmd_rc` | `host parser expects cmd/status in the command header and optional state bytes in data[]` | yes |
| bundle host stub mirrors command-header fields | `cmd_rc/seq/arg1/arg2/arg3` | `local syntax guard must expose the real Spin1API command header fields` | yes |

## Artifacts

- `upload_bundle`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_prepared/ebrains_upload_bundle/cra_422s`
- `job_readme`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_prepared/ebrains_upload_bundle/cra_422s/README_TIER4_22J_JOB.md`
- `stable_upload_folder`: `/Users/james/JKS:CRA/ebrains_jobs/cra_422s`
- `manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_prepared/tier4_22j_results.json`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_prepared/tier4_22j_report.md`
