# Tier 5.21 NEST Per-Neuron Dimensionality Diagnostic Contract
- Status: **PASS** (14/14)
- Outcome: `nest_per_neuron_dimensionality_contract_locked`

## Question

Does the NEST organism's per-neuron spike state measured via get_per_neuron_spike_vector() achieve state dimensionality (PR > 4.0) comparable to the standalone edge-of-chaos reference (PR=7.0), and exceed 2x the per-polyp aggregate PR, or is the gap fundamental to spiking LIF architecture?

## Primary Pass Criteria

- 16-polyp (512-channel) per-neuron PR > 4.0
- Per-neuron PR > 2.0x per-polyp aggregate PR
- Shuffled assignment PR Δ > 2.0

## Next Gate

Tier 5.21a - NEST Per-Neuron Dimensionality Scoring Gate
