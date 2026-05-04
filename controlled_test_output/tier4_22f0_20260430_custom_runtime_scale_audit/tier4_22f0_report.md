# Tier 4.22f0 Custom Runtime Scale-Readiness Audit

- Generated: `2026-04-30T19:01:01+00:00`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_22f0_20260430_custom_runtime_scale_audit`

Tier 4.22f0 audits the custom-C sidecar before spending another hardware allocation on custom-runtime learning. It keeps the architecture boundary explicit: PyNN/sPyNNaker remains the normal mapping/execution layer, and custom C is reserved for CRA-specific on-chip substrate mechanics that PyNN cannot express or scale directly.

## Summary

- Tier 4.22e latest status: `pass`
- Host C tests passed: `True`
- Static checks passed: `9` / `9`
- High-severity scale blockers: `3`
- Runtime scale-ready: `False`
- Direct custom-runtime hardware learning allowed: `False`
- Next gate: `Tier 4.22g event-indexed spike delivery plus lazy/active eligibility traces before any custom-runtime learning hardware claim.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22f0_custom_runtime_scale_audit_20260430_0000` | `expected current source` | yes |
| Tier 4.22e local parity pass exists | `pass` | `== pass` | yes |
| custom C host tests pass | `0` | `returncode == 0 and ALL TESTS PASSED` | yes |
| all static audit checks pass | `9/9` | `all pass` | yes |
| scale blockers are detected | `7` | `>= 5 documented blockers` | yes |
| high severity blockers are explicit | `3` | `>= 2 known blockers documented` | yes |
| direct custom-runtime hardware learning is blocked | `False` | `False until blockers are fixed` | yes |
| PyNN/sPyNNaker boundary remains explicit | `PyNN/sPyNNaker primary, C only for unsupported substrate mechanics` | `must be documented` | yes |

## Scale Blockers

| ID | Severity | Function | Complexity | Required Fix |
| --- | --- | --- | --- | --- |
| SCALE-001 | `high` | `synapse_deliver_spike` | `O(S) per incoming spike` | add pre-indexed outgoing adjacency: pre_id -> compact outgoing synapse/event list |
| SCALE-002 | `high` | `synapse_decay_traces_all` | `O(S) per ms tick` | use lazy timestamp decay or an active-trace list updated only for recently touched synapses |
| SCALE-003 | `medium` | `synapse_modulate_all` | `O(S) per dopamine event` | modulate only active trace list or lazily evaluated eligible synapses |
| SCALE-004 | `medium` | `neuron_add_input/neuron_find` | `O(N) per delivered input` | add direct neuron id -> neuron/state index table or bounded preallocated pool |
| SCALE-005 | `medium` | `birth/death/create_syn/router_add_neuron` | `allocation-time variable cost and fragmentation risk` | preallocate bounded pools with free lists/active masks and explicit capacity telemetry |
| SCALE-006 | `high` | `_handle_read_spikes` | `insufficient observability, not a runtime cost issue` | add fragmented or compact state-summary readback for spikes, reward, pending, slots, and weights |
| SCALE-007 | `medium` | `timer_callback/c_main` | `single-core proof of concept` | define core-local shard contract, per-core summaries, and inter-core routing/resource budgets |

## Claim Boundary

- This is a scale-readiness audit, not a hardware run.
- A PASS here means the audit is complete and the blockers are explicit; it does not mean the C runtime is scale-ready.
- PyNN/sPyNNaker remains the correct path for supported network construction, mapping, running, and standard readback.
- Custom C remains reserved for CRA-specific on-chip state, plasticity, delayed-credit, lifecycle/routing state, and compact readback where PyNN cannot support the long-term substrate goal.
- The next engineering move is event-indexed/lazy-trace optimization, not a large custom-runtime hardware learning claim.
