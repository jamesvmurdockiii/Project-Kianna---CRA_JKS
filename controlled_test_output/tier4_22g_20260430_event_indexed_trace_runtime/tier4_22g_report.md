# Tier 4.22g Event-Indexed Active-Trace Runtime

- Generated: `2026-04-30T19:10:43+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_22g_20260430_event_indexed_trace_runtime`

Tier 4.22g repairs the first custom-C scale blockers identified by Tier 4.22f0: all-synapse spike delivery, all-synapse eligibility decay, and all-synapse dopamine modulation. This remains local C evidence, not hardware learning evidence.

## Summary

- Tier 4.22f0 latest status: `pass`
- Host C tests passed: `True`
- Static optimization checks passed: `12` / `12`
- Repaired scale blockers: `['SCALE-001', 'SCALE-002', 'SCALE-003']`
- Open scale blockers: `['SCALE-004', 'SCALE-005', 'SCALE-006', 'SCALE-007']`
- Custom-runtime hardware learning allowed: `False`
- Next gate: `Tier 4.22h compact state readback plus build/load/command acceptance before custom-runtime learning hardware.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22g_event_indexed_trace_runtime_20260430_0000` | `expected current source` | yes |
| Tier 4.22f0 audit pass exists | `pass` | `== pass` | yes |
| custom C host tests pass | `0` | `returncode == 0 and ALL TESTS PASSED` | yes |
| all static optimization checks pass | `12/12` | `all pass` | yes |
| SCALE-001/002/003 repaired locally | `3` | `== 3` | yes |
| hardware learning still blocked by readback | `1` | `>= 1` | yes |
| no hardware/speedup overclaim | `local C optimization only` | `boundary explicit` | yes |

## Complexity Delta

| Function | Before | After | Hardware Claim |
| --- | --- | --- | --- |
| `synapse_deliver_spike` | `O(S) per incoming spike` | `O(out_degree(pre_id)) per incoming spike` | `not yet measured` |
| `synapse_decay_traces_all` | `O(S) per timer tick` | `O(active_traces) per timer tick` | `not yet measured` |
| `synapse_modulate_all` | `O(S) per dopamine event` | `O(active_traces) per dopamine event` | `not yet measured` |
| `neuron_add_input/neuron_find` | `O(N) per delivered input` | `unchanged` | `open blocker` |
| `_handle_read_spikes` | `count/timestep only` | `unchanged` | `open blocker` |

## Claim Boundary

- This is local custom-C optimization evidence.
- It is not a hardware run.
- It is not full CRA parity, speedup evidence, or final on-chip learning proof.
- PyNN/sPyNNaker remains the primary supported hardware layer for supported primitives.
- Custom-runtime hardware learning remains blocked until compact state readback and build/load/command acceptance pass.
