# Tier 5.24a Within-Polyp Antisymmetric Recurrence Scoring

- Status: harness **PASS**, outcome **recurrence_does_not_help**
- Baseline PR: 2.92
- Best antisym PR: 2.91
- Delta: -0.0098

## Interpretation

Within-polyp antisymmetric E->E recurrence does not increase NEST organism state dimensionality beyond the current ceiling. The standalone's PR=7.0 comes from continuous-state tanh + antisymmetry via w_anti = W - W^T. This mechanism does not transfer to spiking LIF neurons at the current 16-neuron excitatory population size.
