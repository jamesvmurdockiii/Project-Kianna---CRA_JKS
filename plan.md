# Plan: Coral Reef Architecture for SpiNNaker (PyNN)

## Objective
Create a neuromorphic implementation of the Coral Reef Architecture (CRA) biological first principles for the SpiNNaker platform using PyNN. The implementation translates CRA's scalar trophic-health economy, polyp lifecycle, dopamine-modulated STDP learning, and competitive readout into spiking neural network primitives compatible with sPyNNaker.

## Biological First Principles to Preserve
1. **Scalar trophic health economy** - no backpropagation; survival via local energy
2. **Per-polyp LIF neurons** with auxiliary state (trophic_health, bax_activation, cyclin_d, etc.)
3. **Directed reef graph** with sparse connectivity, FF/LAT/FB motifs
4. **Three-channel energy capture** - sensory (MI-driven), outcome (task consequence), retrograde (BDNF-like)
5. **Pro-rata capacity reconciliation** against local trophic ceiling
6. **Lifecycle** - cyclin-D gated reproduction, BAX-driven apoptosis, maternal-to-autonomous handoff
7. **Dopamine-modulated STDP** - winner-take-all readout, delayed matured consequence
8. **Measurement** - KSG/GCMI mutual information, BOCPD changepoint detection
9. **Spatial ecology** - 3D positions, migration, adhesion, repulsion
10. **Competitive aggregation** - top-k by |RPE| rather than democratic averaging

## Architecture (PyNN/SpiNNaker Mapping)

```
coral_reef_spinnaker/
    __init__.py              - Package marker
    config.py                - All CRA parameters (trophic, lifecycle, learning, etc.)
    polyp_neuron.py          - Custom LIF neuron model with trophic auxiliary state
    reef_network.py          - Population + Projection graph with STDP
    energy_manager.py        - Trophic economy (host-side Python)
    lifecycle.py             - Reproduction/apoptosis/handoff logic
    learning_manager.py      - Dopamine STDP and RPE computation
    measurement.py           - MI estimation, BOCPD, stream analytics
    organism.py              - Top-level orchestrator (host-side)
    trading_bridge.py        - Task consequence / directional learning wrapper
    spinnaker_runner.py      - SpiNNaker execution harness
    demo.py                  - Example simulation entrypoint
```

## PyNN/SpiNNaker Design Decisions
- **Neuron model**: LIF with per-neuron trophic_health, cyclin_d, bax_activation, dopamine_ema as extra state variables
- **Connectivity**: PyNN `Population` + `Projection` with `stdp.DopamineModulatedSTDP` synapse type
- **Neuromodulation**: Dopamine delivered via extra synaptic input or gap-junction-like coupling
- **Energy/lifecycle**: Host-side Python (runs between PyNN `run()` calls) since these require global state
- **Measurement**: Host-side Python with numpy/scipy for MI/BOCPD
- **STDP**: Multiplicative STDP with dopamine reward prediction error gating
- **Readout**: Winner-take-all via per-neuron spike rate monitoring

## Stages

### Stage 1 — Core Infrastructure (parallel)
- Subagent 1a: `config.py` + `measurement.py` — all CRA constants + MI/BOCPD
- Subagent 1b: `polyp_neuron.py` — custom LIF neuron type for SpiNNaker
- Subagent 1c: `trading_bridge.py` — task consequence / directional learning

### Stage 2 — Reef Network + Energy (parallel, after Stage 1)
- Subagent 2a: `reef_network.py` — Population/Projection graph construction
- Subagent 2b: `energy_manager.py` — full trophic economy with 3-channel capture

### Stage 3 — Lifecycle + Learning (parallel, after Stage 1)
- Subagent 3a: `lifecycle.py` — reproduction, apoptosis, handoff
- Subagent 3b: `learning_manager.py` — dopamine STDP, RPE, delayed credit

### Stage 4 — Integration
- Subagent 4: `organism.py` + `spinnaker_runner.py` + `demo.py` — full orchestrator

### Stage 5 — Validation
- Run smoke test, verify imports, basic connectivity

## Key Constants (from CRA)
- `bdnf_per_trophic_source = 0.024` (ENGINEERING calibrated)
- `seed_output_scale = 0.1` (sensory calibration)
- `evaluation_horizon_bars = 5` (5m directional signal)
- `child_trophic_share = 0.5` (heritable)
- `apoptosis_threshold` + `bax_activation` drives death
- `cyclin_d_threshold = 0.5` for G1/S checkpoint
- `metabolic_decay = 0.005` (heritable)
- `trophic_synapse_cost` degree-proportional
- `winner_take_all_k = max(3, int(sqrt(N)))`
- `directional_accuracy_ema_alpha = 0.02`
- `accuracy_survival_floor = 0.45`
