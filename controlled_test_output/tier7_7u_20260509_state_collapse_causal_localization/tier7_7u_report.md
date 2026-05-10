# Tier 7.7u State-Collapse Causal Localization

- Generated: `2026-05-09T19:30:33+00:00`
- Status: **PASS** (13/13 criteria)
- Outcome: `localization_protocol_locked_awaits_model_variants`

## Question

Where does the low-rank collapse enter: input encoding, recurrent dynamics, plasticity, inhibition, trophic pressure, readout exposure, or numerical saturation?

## Definition of Done

This gate locks the localization protocol. Full scoring requires the
following model variants to be implemented in the CRA configuration layer:

- **no_plasticity**: Freeze or zero learning rate while preserving recurrence. Add config key `plasticity_enabled=False`.
- **no_inhibition**: Disable WTA/inhibitory normalization within polyp populations. Add config key `inhibition_enabled=False`.
- **frozen_recurrent**: Initialize random recurrent weights once and freeze them. Compares to learned topology.
- **state_reset**: Periodically reset or reinitialize hidden state during training.
- **input_channel_shuffle**: Permute input channels before encoding to break causal structure.
- **per_partition_probe**: Expose per-polyp-partition state readout for partition-specific PR.
- **trophic_probe**: Instrument trophic energy counters alongside state geometry.

Once these variants are available, the localization scoring follows the
outcome rules defined in `tier7_7u_outcome_rules.csv`. The candidate PR
is compared against each diagnostic control; the control producing the
largest PR improvement identifies the primary collapse mechanism. Tier 7.7v
then activates the corresponding repair family (A-E).

## Claim Boundary

Localization protocol locked. Seven diagnostic model variants must be implemented as CRA configuration options before full causal localization can score. Do not proceed to Tier 7.7v repair implementation without verifying that at least the top-4 priority variants exist and can be instantiated with the current CRA v2.5 baseline. Not a repair, not mechanism promotion, not a baseline freeze, not public usefulness proof, not hardware/native transfer.
