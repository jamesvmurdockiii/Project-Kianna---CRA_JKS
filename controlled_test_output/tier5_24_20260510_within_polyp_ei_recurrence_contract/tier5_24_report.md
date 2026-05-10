# Tier 5.24 Within-Polyp E/I Antisymmetric Recurrence Contract
- Status: **PASS** (14/14)
- Outcome: `within_polyp_ei_recurrence_contract_locked`

## Question

Does adding antisymmetric weight structure (W_anti = W - W^T) to the existing within-polyp E->E recurrent projections increase NEST organism state dimensionality beyond the current PR~1.9 ceiling, by creating push-pull oscillatory dynamics analogous to the standalone's skew-symmetric w_rec?

## Diagnosis

The standalone tanh reference achieves PR=7.0 through antisymmetric recurrence (w_rec = W - W^T, sr=1.0). The NEST organism's polyp_population.py already has E->E recurrence at lines 577-583, but with lognormal random weights that are all positive and have no push-pull antisymmetric structure. This is the primary architectural difference between standalone recurrence and spiking polyp recurrence: the standalone's diversity comes from structured antisymmetry, not just raw recurrence.

## Next Gate

Tier 5.24a - Within-Polyp Antisymmetric Recurrence Scoring Gate
