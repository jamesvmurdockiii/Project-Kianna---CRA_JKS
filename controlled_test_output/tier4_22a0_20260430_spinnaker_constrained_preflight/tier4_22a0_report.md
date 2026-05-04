# Tier 4.22a0 SpiNNaker-Constrained Local Preflight

- Generated: `2026-04-30T17:47:50+00:00`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_22a0_20260430_spinnaker_constrained_preflight`

Tier 4.22a0 is a local pre-hardware gate. It reduces transfer risk before more EBRAINS time, but it is not real SpiNNaker evidence.

## Claim Boundary

- `PASS` means constrained NEST, static PyNN/sPyNNaker feature compliance, bounded resource checks, and host runtime tests passed locally.
- This is not custom C, native/on-chip CRA, continuous execution, or speedup evidence.
- Real hardware claims still require returned pyNN.spiNNaker artifacts with zero fallback/failures and nonzero real spike readback.

## Summary

- Tier 4.20c reference status: `pass`
- Tier 4.21a reference status: `pass`
- Tier 4.22a contract status: `pass`
- NEST probe status: `pass`
- NEST total spikes: `64`
- sPyNNaker feature status: `pass`
- sPyNNaker tiny smoke status: `skipped`
- Static compliance failed checks: `0`
- Resource failed rows: `0`
- Runtime host test status: `pass`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22a0_spinnaker_constrained_preflight_20260430_0000` | `expected current source` | yes |
| Tier 4.20c reference pass exists | `pass` | `== pass` | yes |
| Tier 4.21a reference pass exists | `pass` | `== pass` | yes |
| Tier 4.22a contract pass exists | `pass` | `== pass` | yes |
| NEST imports locally | `pass` | `== pass` | yes |
| pyNN.nest imports locally | `pass` | `== pass` | yes |
| pyNN.spiNNaker imports locally | `pass` | `== pass` | yes |
| sPyNNaker exposes required PyNN primitives | `pass` | `== pass` | yes |
| optional sPyNNaker tiny smoke satisfied if required | `skipped` | `pass OR skipped when not required` | yes |
| constrained NEST StepCurrentSource probe passed | `pass` | `== pass` | yes |
| constrained NEST produced nonzero spikes | `64` | `> 0` | yes |
| constrained NEST sim/readback failures zero | `{"readback": 0, "sim": 0}` | `all == 0` | yes |
| static PyNN bridge compliance passed | `0` | `== 0 failed checks` | yes |
| resource budget checks passed | `0` | `== 0 failed rows` | yes |
| custom runtime host tests passed | `pass` | `== pass` | yes |
| chunked reference remains implemented | `True` | `True` | yes |
| continuous/on-chip remains future until proven | `False` | `False` | yes |

## Static Compliance

| Scope | Check | Rule | Pass |
| --- | --- | --- | --- |
| tier4_16_chunked_bridge_function | uses pyNN.spiNNaker in direct runner | required | yes |
| tier4_16_chunked_bridge_function | uses IF_curr_exp | required hardware-supported cell model | yes |
| tier4_16_chunked_bridge_function | uses StepCurrentSource scheduled input | required bridge input primitive | yes |
| tier4_16_chunked_bridge_function | uses Population | required hardware population primitive | yes |
| tier4_16_chunked_bridge_function | reads spikes through get_data | required binned readback path | yes |
| tier4_16_chunked_bridge_function | does not create PyNN Projection in chunk bridge | no dynamic graph/projection mutation in bridge loop | yes |
| tier4_16_chunked_bridge_function | does not use STDPMechanism in bridge runner | host replay bridge must not imply unsupported native plasticity | yes |
| tier4_21a_keyed_bridge_source | keyed memory bridge has explicit variants | candidate and shams must stay explicit | yes |
| tier4_21a_keyed_bridge_source | keyed memory is bounded by configured slot count | bounded-state telemetry required | yes |
| tier4_22a_contract_source | contract declares constrained-NEST/sPyNNaker preflight | Tier 4.22a0 must stay in roadmap/contract | yes |

## Resource Budget

| Item | Current | Limit | Status | Note |
| --- | --- | --- | --- | --- |
| population_neurons | `8` | `4335` | `pass` | N=8 bridge population should map far below one-chip limits. |
| planned_all_to_all_connections_budget_probe | `64` | `30208` | `pass` | Conservative planning row; current bridge uses StepCurrentSource, not recurrent Projection. |
| keyed_context_slots | `4` | `16` | `pass` | Dynamic dict semantics must remain bounded before chip/hybrid state work. |
| fixed_point_weight_quantization_probe | `-1.2` | `[-1.0, 1.0)` | `pass` | Records the fixed-point clipping/rounding contract used for future runtime parity. |
| fixed_point_weight_quantization_probe | `-1` | `[-1.0, 1.0)` | `pass` | Records the fixed-point clipping/rounding contract used for future runtime parity. |
| fixed_point_weight_quantization_probe | `-0.12345` | `[-1.0, 1.0)` | `pass` | Records the fixed-point clipping/rounding contract used for future runtime parity. |
| fixed_point_weight_quantization_probe | `0` | `[-1.0, 1.0)` | `pass` | Records the fixed-point clipping/rounding contract used for future runtime parity. |
| fixed_point_weight_quantization_probe | `0.12345` | `[-1.0, 1.0)` | `pass` | Records the fixed-point clipping/rounding contract used for future runtime parity. |
| fixed_point_weight_quantization_probe | `0.999999` | `[-1.0, 1.0)` | `pass` | Records the fixed-point clipping/rounding contract used for future runtime parity. |
| fixed_point_weight_quantization_probe | `1.2` | `[-1.0, 1.0)` | `pass` | Records the fixed-point clipping/rounding contract used for future runtime parity. |

## Next Step

- If pass: Tier 4.22b continuous no-learning scaffold: scheduled input, compact readback, no learning claim.
- If fail: Fix local constrained/mapping issue before spending EBRAINS hardware time.
