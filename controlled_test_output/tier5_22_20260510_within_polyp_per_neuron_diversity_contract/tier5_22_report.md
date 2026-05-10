# Tier 5.22 Within-Polyp Per-Neuron Input Diversity Contract
- Status: **PASS** (11/11)
- Outcome: `within_polyp_diversity_contract_locked`

## Question

Does per-neuron input gain diversity within each polyp's 8 input neurons (0.3x-1.5x gain range on sensory signal, plus amplified per-neuron biases at 15% of sensory ceiling) increase NEST organism state dimensionality beyond the current PR≈1.3 ceiling?

## Code Change

- File: `coral_reef_spinnaker/polyp_population.py`
- Method: `update_current_injections`
## Next Gate

Tier 5.22a - Within-Polyp Per-Neuron Diversity Scoring Gate
