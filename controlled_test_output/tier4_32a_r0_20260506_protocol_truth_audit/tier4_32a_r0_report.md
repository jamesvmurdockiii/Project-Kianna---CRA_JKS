# Tier 4.32a-r0 Protocol Truth Audit

- Generated: `2026-05-06T22:39:38+00:00`
- Status: **PASS**
- Runner revision: `tier4_32a_r0_protocol_truth_audit_20260506_0001`

## Claim Boundary

Tier 4.32a-r0 is a source/documentation truth audit. It proves that the planned MCPL-first scale stress cannot be honestly packaged yet because the current confidence-gated lookup path still uses SDP and the MCPL lookup helpers do not carry confidence or shard identity. It is not a hardware run, not speedup evidence, not multi-chip scaling, and not a baseline freeze.

## Summary

- The planned MCPL-first 4.32a-hw package is blocked until Tier 4.32a-r1 repairs confidence-bearing and shard-aware MCPL lookup.
- A transitional SDP debug run may still be useful, but it must be labelled as SDP debug evidence, not MCPL-first scale evidence.
- No native-scale baseline freeze is authorized.

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.32a prerequisite passed | `pass` | == pass | yes |
| confidence lookup SDP fallback found | `True` | == True | yes |
| MCPL reply drops confidence found | `True` | == True | yes |
| MCPL receive hardcodes confidence found | `True` | == True | yes |
| MCPL key lacks shard identity found | `True` | == True | yes |
| MCPL dest_core reserved/ignored found | `True` | == True | yes |
| all protocol blockers classified | `5` | == 5 | yes |
| MCPL-first 4.32a-hw package blocked | `blocked` | == blocked | yes |
| Tier 4.32a-r1 protocol repair required next | `required_next` | == required_next | yes |
| native scale baseline freeze remains blocked | `not_authorized` | == not_authorized | yes |

## Source Findings

| Finding | File | Line | Blocks |
| --- | --- | --- | --- |
| `confidence_lookup_uses_sdp` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `1467` | MCPL-first 4.32a-hw scale-stress packaging |
| `mcpl_reply_drops_confidence` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `1707` | confidence-gated learning over MCPL |
| `mcpl_receive_hardcodes_confidence` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `1724` | self-evaluation/confidence-gated v2.1 transfer over MCPL |
| `mcpl_key_lacks_shard_identity` | `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | `201` | replicated 8/12/16-core shard stress and multi-chip routing |
| `mcpl_dest_core_reserved` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | `1700` | directed replicated-shard lookup routing |

## Final Decision

- `status`: `pass`
- `tier4_32a_hw_mcpl_first`: `blocked_until_4_32a_r1_protocol_repair`
- `tier4_32a_sdp_debug_hw`: `allowed_only_if_relabelled_transitional_sdp_debug_not_scale_evidence`
- `tier4_32a_r1`: `required_next`
- `tier4_32a_hw_replicated`: `blocked_until_confidence_and_shard_aware_mcpl_passes`
- `tier4_32b`: `blocked_until_confidence_and_shard_aware_4_32a_hardware_stress_passes`
- `native_scale_baseline_freeze`: `not_authorized`
