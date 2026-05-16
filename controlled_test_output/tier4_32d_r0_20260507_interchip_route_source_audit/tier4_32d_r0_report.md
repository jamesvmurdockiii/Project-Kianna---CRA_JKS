# Tier 4.32d-r0 Inter-Chip Route/Source/Package Audit

- Generated: `2026-05-07T02:59:31+00:00`
- Runner revision: `tier4_32d_r0_interchip_route_source_audit_20260507_0001`
- Status: **PASS**
- Criteria: `10/10`
- Decision: `block_4_32d_package_until_route_repair`

## Claim Boundary

Tier 4.32d-r0 is a local route/source/package audit only. It is not a SpiNNaker hardware run, not an EBRAINS package, not multi-chip execution evidence, not speedup evidence, not learning-scale evidence, not benchmark superiority, and not a native-scale baseline freeze.

## Audit Result

- Tier 4.32c prerequisite: `pass`
- First smoke target: `point_2chip_split_partition_lookup_smoke`
- MCPL init local-core route only: `True`
- Explicit inter-chip link route present: `False`
- EBRAINS package authorized: `False`
- Recommended next step: Tier 4.32d-r1 inter-chip MCPL route repair/local QA before any EBRAINS package.

## Source Findings

| Finding | File | Observed | Interpretation | Decision |
| --- | --- | --- | --- | --- |
| `mcpl_request_reply_source_backed` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | cra_state_mcpl_lookup_send_request_shard and cra_state_mcpl_lookup_send_reply_shard emit MCPL packets with shard-aware keys | MCPL packet construction is present for the split-role smoke. | keep |
| `dest_core_not_delivery_authority` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | True | The send path intentionally ignores dest_core; routing table entries are the delivery authority. | 4.32d must verify router entries, not just command arguments |
| `local_core_routes_only` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | MC_CORE_ROUTE(core_id)=True; explicit_link_route=False | cra_state_mcpl_init currently routes matched request/reply keys to the local core only and does not name inter-chip links. | block package until inter-chip route repair or explicit placement/routing contract exists |
| `true_two_partition_learning_protocol_missing` | `coral_reef_spinnaker/spinnaker_runtime/src/config.h` | one shard_id field in MCPL key | The 4.32c boundary remains correct: split-role single-shard smoke is the first honest target; true two-partition learning needs origin/target shard semantics later. | keep blocked for 4.32e+ until repaired |

## Failure Classes

| Failure | Detection | Required Response | Blocks |
| --- | --- | --- | --- |
| `cross_chip_route_missing` | cra_state_mcpl_init has only MC_CORE_ROUTE(core_id) delivery and no explicit link route or placement-provided routing table contract | do not prepare EBRAINS package; implement or prove inter-chip route entries first | Tier 4.32d hardware upload |
| `single_shard_protocol_limit` | attempted true two-partition cross-chip learning with only one shard_id field | add origin/target shard semantics before multi-partition learning | Tier 4.32e+ learning scale |
| `package_overclaim` | upload folder or command claims learning scale, speedup, or two-partition learning before route smoke passes | delete/rewrite package and preserve audit failure | EBRAINS submission |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| Tier 4.32c prerequisite passed | `pass` | == pass | yes |  |
| 4.32c target is split-role single-shard | `point_2chip_split_partition_lookup_smoke` | == point_2chip_split_partition_lookup_smoke | yes |  |
| 4.32c first smoke uses one partition | `1` | == 1 | yes |  |
| MCPL shard-aware key source exists | `True` | == true | yes |  |
| MCPL send path delegates delivery to router table | `True` | == true | yes |  |
| MCPL init installs local core routes | `True` | == true | yes |  |
| explicit inter-chip link route is absent and classified | `False` | == false | yes |  |
| 4.32d upload folder not prepared prematurely | `<repo>/ebrains_jobs/cra_432d` | must not exist | yes |  |
| hardware package remains blocked by source audit | `blocked` | == blocked | yes |  |
| next gate is route repair | `Tier 4.32d-r1` | == Tier 4.32d-r1 | yes |  |
