# Tier 4.20a v2.1 Hardware Transfer Readiness Audit

- Generated: `2026-04-29T23:05:03+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_20a_20260429_190503`

Tier 4.20a is an engineering audit, not a hardware run. It maps v2.1 mechanisms onto the proven runtime vocabulary so we know what can be tested through chunked host SpiNNaker and what must wait for hybrid/custom-C/on-chip work.

## Claim Boundary

- `PASS` means the transfer plan is explicit and auditable.
- It is not a SpiNNaker hardware pass, not custom-C evidence, and not on-chip autonomy.
- Any hardware claim still requires returned pyNN.spiNNaker artifacts with real spike readback, zero fallback, and zero read/run failures.

## Runtime Contracts

- Step host plan: `current_step_host_loop`, sim.run calls `1200`
- Chunked host plan: `chunked_host_stepcurrent_binned_replay`, chunk size `50`, sim.run calls `24`
- Continuous/on-chip plan implemented: `False`; blockers `custom_c_or_backend_native_closed_loop, on_chip_or_hybrid_credit_assignment_state, hardware_provenance_for_continuous_run`

## Mechanism Transfer Matrix

| Mechanism | Chunked host | Continuous | On-chip | Priority | Risk | Required bridge work |
| --- | --- | --- | --- | --- | --- | --- |
| PendingHorizon delayed credit / delayed_lr_0_20 | `ready_for_probe` | `future_custom_runtime` | `not_implemented` | `high` | `medium` | reuse scheduled input and per-step binned readback; verify matured feedback replay under v2.1 tasks |
| keyed context memory | `needs_bridge_adapter` | `future_custom_runtime` | `not_implemented` | `high` | `medium` | carry visible context/decision metadata through chunk scheduler; replay per-step context writes and decisions after binned readback |
| replay / consolidation | `needs_probe_design` | `future_custom_runtime` | `not_implemented` | `medium` | `high` | define replay epochs around hardware chunks; prevent replay from fabricating spike readback; log replay events separately from real hardware events |
| visible predictive context / predictive binding | `needs_bridge_adapter` | `future_custom_runtime` | `not_implemented` | `high` | `medium_high` | schedule precursor/decision metadata inside chunks; preserve no-label/no-reward preexposure contract; compare against shuffled/wrong-domain controls in hardware probe |
| composition and module routing | `needs_bridge_adapter` | `future_custom_runtime` | `not_implemented` | `medium` | `high` | map skill/context events to chunk scheduler; replay module/router updates after feedback; prove pre-feedback route selection with hardware readback |
| self-evaluation / reliability monitoring | `needs_bridge_adapter` | `future_custom_runtime` | `not_implemented` | `medium` | `medium_high` | compute monitor features only from pre-feedback/binned state; log confidence before outcome; verify sham monitors in hardware-compatible capsule |
| macro eligibility residual trace | `not_promoted` | `future_custom_runtime_if_promoted` | `not_implemented` | `low_until_promoted` | `high` | do not port until macro trace beats shuffled/zero controls and v2.1 integration preserves guardrails |
| spike temporal-code diagnostics | `needs_dedicated_temporal_probe` | `future_custom_runtime` | `not_implemented` | `medium` | `medium_high` | ensure temporal codes are delivered inside chunks and read back with bin resolution fine enough to preserve timing controls |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| frozen v2.1 baseline artifact exists | `<repo>/baselines/CRA_EVIDENCE_BASELINE_v2.1.json` | `exists` | yes |
| post-chunked-runtime v0.8 baseline artifact exists | `<repo>/baselines/CRA_EVIDENCE_BASELINE_v0.8.json` | `exists` | yes |
| chunked host runtime contract is implemented | `chunked_host_stepcurrent_binned_replay` | `implemented == true` | yes |
| continuous/on-chip runtime is explicitly not overclaimed | `future_custom_runtime` | `implemented == false` | yes |
| all promoted v2.1 mechanisms classified | `7` | `>= 6 classified transferable/probe rows` | yes |
| no mechanism is incorrectly marked on-chip proven | `none` | `none` | yes |

## Recommended Hardware Sequence

1. Run Tier 5.9c first; keep macro eligibility parked unless it passes and later integration is clean.
2. Run Tier 4.20b one-seed v2.1 chunked hardware probe using delayed/context/predictive mechanisms only; no macro eligibility unless promoted.
3. If 4.20b passes, run Tier 4.20c three-seed repeat on the smallest v2.1 capsule.
4. Only after returned hardware evidence is clean, design Tier 4.21 hybrid/native eligibility or on-chip memory prototypes for the mechanisms that actually mattered.
