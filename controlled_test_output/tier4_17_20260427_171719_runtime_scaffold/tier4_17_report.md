# Tier 4.17 Batched / Continuous Hardware Runtime Refactor

- Generated: `2026-04-27T17:17:19.311639+00:00`
- Status: **PREPARED**
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_17_20260427_171719_runtime_scaffold`

Tier 4.17 is a runtime-contract tier, not a learning-result tier.
It freezes the vocabulary for moving from proof-grade per-step hardware
orchestration toward chunked and eventually continuous execution.

## Claim Boundary

- `step + host` is the current proven execution path.
- `chunked + host` is implemented as the first batching bridge after Tier 4.17b local parity.
- Valid chunking still requires real hardware confirmation before it becomes hardware-learning evidence.
- `hybrid`, `on_chip`, and `continuous` are future custom-runtime targets.

## Summary

- steps: `1200`
- dt_seconds: `0.05`
- baseline step-mode `sim.run` calls: `1200`
- max estimated call reduction: `50x`
- executable-now plans: `5`
- chunked-host bridge plans: `4`

## Runtime Plan Rows

| Runtime | Learning | Chunk | Calls | Reduction | Stage | Implemented | Blockers |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| `step` | `host` | 1 | 1200 | 1 | `current_step_host_loop` | True | none |
| `chunked` | `host` | 5 | 240 | 5 | `chunked_host_stepcurrent_binned_replay` | True | none |
| `chunked` | `host` | 10 | 120 | 10 | `chunked_host_stepcurrent_binned_replay` | True | none |
| `chunked` | `host` | 25 | 48 | 25 | `chunked_host_stepcurrent_binned_replay` | True | none |
| `chunked` | `host` | 50 | 24 | 50 | `chunked_host_stepcurrent_binned_replay` | True | none |
| `continuous` | `on_chip` | 1200 | 1 | 1200 | `future_custom_runtime` | False | custom_c_or_backend_native_closed_loop, on_chip_or_hybrid_credit_assignment_state, hardware_provenance_for_continuous_run |
| `chunked` | `hybrid` | 50 | 24 | 50 | `future_custom_runtime` | False | custom_c_or_backend_native_closed_loop, on_chip_or_hybrid_credit_assignment_state, hardware_provenance_for_continuous_run |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| v0.5 baseline exists before runtime refactor | True | == True | yes |
| step+host current path represented | True | == True | yes |
| chunked+host bridge represented | True | == True | yes |
| chunked+host bridge marked implemented | True | == True | yes |
| hybrid/on-chip/continuous explicitly marked future | True | == True | yes |
| candidate chunking reduces sim.run calls | 50 | >= 10 | yes |
| result is noncanonical runtime contract inventory | noncanonical runtime contract inventory | == noncanonical runtime contract inventory | yes |

## Next Order

1. Keep Tier 4.17b as the local parity gate for the chunked bridge.
2. Run Tier 4.16a-repaired delayed_cue seed 43 at 1200 steps with chunk_size_steps=25.
3. Only after that passes, repeat repaired Tier 4.16a across seeds 42, 43, and 44.
4. Then test hard_noisy_switching with the same chunked bridge.
5. Treat hybrid/on-chip/continuous execution as future custom-runtime work.

## Artifacts

- `summary_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_17_20260427_171719_runtime_scaffold/tier4_17_runtime_summary.csv`
- `manifest_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_17_20260427_171719_runtime_scaffold/tier4_17_results.json`
- `report_md`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_17_20260427_171719_runtime_scaffold/tier4_17_report.md`
- `runtime_reduction_png`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_17_20260427_171719_runtime_scaffold/tier4_17_runtime_reduction.png`
