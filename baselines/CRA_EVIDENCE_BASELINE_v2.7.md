# CRA Evidence Baseline v2.7 — NEST Organism Developmental Architecture

**Date**: 2026-05-13T23:30:00+00:00  
**Relationship to v2.6**: does not supersede v2.6 for predictive benchmarks  
**Type**: Host-side NEST organism-development diagnostic snapshot  
**Status**: FROZEN DIAGNOSTIC SNAPSHOT (corrected PR numbers)

## Claim

CRA v2.7 is a NEST organism-development snapshot for measuring whether
state diversity can be generated through ecological/developmental dynamics
rather than engineered parameter injection. It records 14 config-gated
mechanisms spanning lifecycle evolution, operator diversity, conservation
laws, structured readout, task-coupled selection, and cross-polyp coupling.

This snapshot is not a predictive-performance promotion over v2.6.

## Corrected Benchmark Scores

**Critical correction (2026-05-13):** The high PR numbers (5-10) reported earlier were
artifacts of NEST synthetic spike fallback generating independent Poisson noise per
neuron. ResetKernel recovery fixed NEST health, revealing true organism PR.

| Task | v2.7 PR | MSE | Persist MSE |
|------|---------|-----|-------------|
| Sine (2k) | 1.15 | 0.5067 | 1.0549 |
| Mackey-Glass (2k) | 1.54 | 0.9096 | 0.0762 |
| Lorenz (2k) | 2.05 | 65.03 | 65.03 |

MSE is identical across scalar, nonlinear, and causal credit readout configurations.
State diversity does not improve prediction accuracy. Persistence baseline dominates MG.

## Key Mechanisms (all config-gated via lifecycle.enable_*)

| Tier | Mechanism | PR effect | Config flag (default) |
|------|-----------|-----------|----------------------|
| 5.26 | Neural heritability | +0.12 | enable_neural_heritability (False; opt-in) |
| 5.27 | Stream specialization | +0.11 | enable_stream_specialization (False; opt-in) |
| 5.28 | Variable allocation | +0.16 | enable_variable_allocation (False; opt-in) |
| 5.29 | Task-fitness selection | infra | enable_task_fitness_selection (False; opt-in) |
| 5.30 | Synaptic weight heritability | infra | enable_synaptic_heritability (False) |
| 5.32 | Operator diversity | +4.71* | enable_operator_diversity (False; opt-in) |
| 5.38 | Signal transport | infra | enable_signal_transport (False; opt-in) |
| 5.39 | Energy economy | +0.00 | enable_energy_economy (False; opt-in) |
| 5.40 | Maturation lifecycle | +1.31* | enable_maturation (False; opt-in) |
| 5.41 | Vector readout | infra | enable_vector_readout (False) |
| 5.42 | Task-coupled selection | infra | enable_task_coupled_selection (False; opt-in) |
| 5.43 | Cross-polyp coupling | infra | enable_cross_polyp_coupling (False; opt-in) |
| 5.44 | Causal credit assignment | +0.00 | enable_causal_credit_selection (False; opt-in) |

*PR margins measured during synthetic fallback era; corrected numbers TBD on healthy NEST.

## NEST Platform Fixes

1. **Cleanup workaround**: `nest.Cleanup()` before `sim.run()` at organism.py:2148
   prevents "Prepare called twice" errors when dynamic projections are added.

2. **ResetKernel recovery**: organism.py:2153-2178 catches "Kernel inconsistent state"
   errors, calls `nest.ResetKernel()` + `sim.setup()` + `rebuild_spinnaker()`, retries
   `sim.run()`. Keeps NEST healthy at 2000+ steps.

3. **Population overflow**: organism.py:1760 catches RuntimeError from `add_polyp`
   when population is full, gracefully defers excess births.

## Characterized Boundary

**State diversity ≠ prediction performance.** The organism creates evolved
architectural diversity (allocation profiles, spectral radius, caste structure)
but the spiking LIF substrate produces correlated activity patterns under shared
scalar input. PR ≈ 2 is the measured organism dynamical dimensionality with
healthy NEST.  No mechanism configuration (scalar, nonlinear, vector, causal
credit) improves prediction MSE.

## Claim Boundary

- Host-side NEST software organism diagnostic evidence only
- Does not claim prediction superiority over external baselines
- Does not supersede v2.6 as the predictive benchmark baseline
- Does not claim public usefulness on C-MAPSS, NAB, or real-world tasks
- Does not claim hardware transfer or SpiNNaker evidence
- Does not claim language, planning, AGI, or ASI
- Does not claim that state diversity (PR) translates to prediction performance
- v2.6 standalone tanh recurrence remains the predictive benchmark baseline
