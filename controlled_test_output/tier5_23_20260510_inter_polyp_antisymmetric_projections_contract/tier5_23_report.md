# Tier 5.23 Inter-Polyp Antisynaptic PyNN Projections Contract
- Status: **PASS** (13/13)
- Outcome: `inter_polyp_antisymmetric_projections_contract_locked`

## Question

Does enabling inter-polyp PyNN projections with antisymmetric E/I weights on the NEST backend increase organism state dimensionality beyond the current PR≈1.9 ceiling, by creating genuine synaptic recurrence analogous to the standalone's skew-symmetric w_rec?

## Diagnosis

The NEST organism's inter-polyp edges are stored as host-level ReefNetwork objects but never materialized as PyNN projections because sync_to_spinnaker() at organism.py:264 is gated behind backend_name == 'sPyNNaker'. With reproduce=False, the organism has zero inter-polyp synaptic connections — each polyp is synaptically isolated. The antisymmetric_inter_polyp_edges config flag creates host-level edges that never reach the NEST simulation.

## Next Gate

Tier 5.23a - Inter-Polyp Antisymmetric Projections Scoring Gate
