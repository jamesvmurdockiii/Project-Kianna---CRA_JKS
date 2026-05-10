# Tier 7.8 Polyp Morphology / Template Variability Contract
- Status: **PASS** (15/15)
- Outcome: `morphology_contract_locked`

## Question

Can variable polyp internal templates (diverse timescales, recurrence parameters, E/I ratios, sparse connectivity, input selectivity, polyp size) increase state diversity and benchmark usefulness beyond the current homogeneous architecture, without being explained by generic random projection or nonlinear-lag controls?

## Candidates

- **diverse_timescales**: Polyps assigned to fast/medium/slow regimes with different EMA alpha values per polyp group.
- **variable_recurrence**: Polyps differ in spectral radius (0.3-1.0) and antisymmetry (0.0-0.5), creating diverse dynamical regimes across the population.
- **excitatory_inhibitory_ratio_variability**: Polyps vary in E/I ratio (70:30 to 30:70), creating different baseline activity levels and sensitivity patterns.
- **sparse_structured_connectivity**: Polyps use small-world or modular connectivity instead of all-to-all, with different sparsity patterns per polyp.
- **input_selectivity**: Polyp groups attend to different input feature subsets (some to raw x, some to EMAs, some to deltas).
- **template_size_variability**: Polyps vary in size (hidden units per polyp: 16/32/64/128) with the same total neuron budget.

## Next Gate

Tier 7.8a - Morphology Candidate Compact Scoring Gate
