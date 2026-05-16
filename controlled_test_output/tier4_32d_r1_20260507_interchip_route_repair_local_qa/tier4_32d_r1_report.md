# Tier 4.32d-r1 Inter-Chip MCPL Route Repair Local QA

- Generated: `2026-05-07T03:09:28+00:00`
- Runner revision: `tier4_32d_r1_interchip_route_repair_local_qa_20260507_0001`
- Status: **PASS**
- Criteria: `14/14`
- Decision: `authorize_4_32d_package_next`

## Claim Boundary

Tier 4.32d-r1 is local source/runtime QA for explicit inter-chip MCPL route entries. It is not a SpiNNaker hardware run, not an EBRAINS package, not multi-chip execution evidence, not learning-scale evidence, not speedup evidence, not benchmark superiority, and not a native-scale baseline freeze.

## Result

- Tier 4.32d-r0 prerequisite: `pass`
- Route contract test: `0`
- Existing MCPL lookup regression: `0`
- Existing four-core MCPL regression: `0`
- EBRAINS package authorized next: `True`
- Recommended next step: Tier 4.32d two-chip split-role single-shard MCPL lookup hardware smoke package/run.

## Source Findings

| Finding | File | Observed | Interpretation | Decision |
| --- | --- | --- | --- | --- |
| `request_link_macro_present` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | True | Learning-core builds can install outbound request routes to an explicit chip link. | keep |
| `reply_link_macro_present` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | True | State-core builds can install outbound reply routes to an explicit chip link. | keep |
| `learning_request_routes_specific` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | LOOKUP_TYPE_CONTEXT/ROUTE/MEMORY request routes installed under request-link macro | Source-chip learning profile can route all three lookup request types off chip. | keep |
| `state_reply_routes_specific` | `coral_reef_spinnaker/spinnaker_runtime/src/state_manager.c` | VALUE/META reply routes installed per state profile lookup type under reply-link macro | Remote state profiles avoid broad duplicate reply routes while returning value/meta packets. | keep |
| `route_stub_captures_rtr_mc_set` | `coral_reef_spinnaker/spinnaker_runtime/stubs/sark.h` | True | Host tests can inspect programmed key/mask/route entries instead of trusting comments. | keep |
| `make_target_present` | `coral_reef_spinnaker/spinnaker_runtime/Makefile` | True | The route contract is callable by CI/local validation. | keep |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| Tier 4.32d-r0 prerequisite passed | `pass` | == pass | yes |  |
| source has request link-route macro | `True` | == true | yes |  |
| source has reply link-route macro | `True` | == true | yes |  |
| learning source installs all three request lookup routes | `True` | == true | yes |  |
| state source installs value/meta reply routes | `True` | == true | yes |  |
| route stub records rtr_mc_set key/mask/route | `True` | == true | yes |  |
| Makefile exposes inter-chip route contract target | `True` | == true | yes |  |
| route contract tests learning and state sides | `True` | == true | yes |  |
| inter-chip route contract test passes | `0` | == 0 | yes |  |
| existing MCPL lookup contract still passes | `0` | == 0 | yes |  |
| existing four-core MCPL local regression still passes | `0` | == 0 | yes |  |
| 4.32d upload folder not prepared by local QA | `<repo>/ebrains_jobs/cra_432d` | must not exist | yes |  |
| next hardware smoke is authorized only after this local pass | `Tier 4.32d` | authorized_next_if_all_pass | yes |  |
| no baseline freeze authorized | `blocked` | == blocked | yes |  |

## Test Commands

- `make test-mcpl-interchip-route-contract` -> `0`
- `make test-mcpl-lookup-contract` -> `0`
- `make test-four-core-mcpl-local` -> `0`
