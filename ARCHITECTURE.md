# Coral Reef Architecture — Implementation Truth Matrix

This document is the **single source of architectural truth**. It replaces aspirational language with an honest three-column view of what exists today.

## Three-Column Convention

| ✅ Implemented | 🔄 Partial / Fragile | 📋 Roadmap |
|---|---|---|
| Works in CI smoke tests | Works but has known issues | Design exists, code does not |

---

## 1. Runtime Backends

| Feature | Status | Notes |
|---|---|---|
| NEST native dopamine STDP | ✅ | 500-step demo validated, 65.9% accuracy |
| sPyNNaker neuromodulation wiring | ✅ | `StructuralMechanismSTDP` + `SpikeSourcePoisson` reward source |
| Chunked PyNN hardware bridge | ✅ | Tier 4.16a/4.16b hardware transfer and Tier 4.18a runtime characterization pass with scheduled input, binned readback, and host replay; still chunked + host, not continuous/on-chip learning |
| sPyNNaker dynamic rebuild | 🔄 | `rebuild_spinnaker()` works in virtual mode but loses STDP traces |
| Custom C runtime (bare-metal) | 🔄 | Hardware-validated scaffold: build/load/SDP/MCPL/learning-loop through Tier 4.28d. Full CRA substrate (lifecycle, ecology, measurement) remains experimental |
| MockSimulator fallback | ✅ | Pure-Python PyNN-compatible mock; covered by CI smoke and stabilization tests |

**Strategic decision:** The Python/PyNN CRA package is the **mainline**. The custom C runtime is an **experimental backend** with its own protocol tests. Hardware has validated the build/load/SDP/MCPL/learning-loop scaffold (Tiers 4.22i–4.28d). It will be promoted to mainline only when it implements the full CRA substrate (measurement, ecology, lifecycle, learning) rather than just dynamic LIF. |

---

## 2. Neural Substrate

| Feature | Status | Notes |
|---|---|---|
| LIF neuron model | ✅ | Config-driven parameters; PyNN `IF_curr_exp` on NEST/sPyNNaker |
| Dynamic population sizing | 🔄 | sPyNNaker constraint: fixed at `sim.setup()`. Rebuild fallback exists but loses plasticity. True dynamic alloc only in C runtime. |
| Dopamine-modulated STDP | ✅ | `DopamineModulatedWeightDependence` in polyp_neuron.py |
| Winner-take-all readout | 🔄 | `winner_take_all_base` configured but WTA circuit not explicitly wired in all backends |
| Homeostasis | 🔄 | `HOMEOSTASIS_TARGET_RATE_HZ` defined in learning_manager.py but not visibly active in all backends |
| Gap junctions | 📋 | Config field exists (`gap_junction_weight=0.1`) but no explicit gap-junction projection creation |
| Structural plasticity (sPyNNaker) | 🔄 | `StructuralMechanismSTDP` wired; pool-based rewiring within `s_max`, not true growth |

---

## 3. Trophic Economy

| Feature | Status | Notes |
|---|---|---|
| 3-channel energy capture | ✅ | Sensory + outcome + retrograde |
| Scalar trophic health | ✅ | `trophic_health` per polyp |
| Maternal reserve / handoff | ✅ | `MaternalReserve` with taper logic |
| BDNF release & uptake | ✅ | `EnergyConfig` is authoritative: release default `0.024`, uptake-efficiency default `0.5`, saturation `1.0` |
| Apoptosis (BAX-driven) | ✅ | `bax_accumulation_rate` + threshold |
| Cyclin-D reproduction | ✅ | `cyclin_d_threshold=0.5` |
| Retrograde support | ✅ | `retrograde_fraction_default` |

---

## 4. Measurement & Learning

| Feature | Status | Notes |
|---|---|---|
| KSG mutual information | ✅ | `measurement.py` with KSG estimator |
| BOCPD changepoint detection | ✅ | `BayesianOnlineChangepointDetector` |
| MI-driven dopamine gating | 🔄 | `bocpd_plasticity_temp_multiplier` present but not universally wired |
| Directional accuracy EMA | ✅ | `directional_accuracy_ema_alpha` |
| Pending horizon ledger | ✅ | `PendingHorizon` in learning_manager.py |
| Internal context memory | ✅ | Tier 5.10d/5.10e validated host-side context binding inside `Organism` and compact regression |
| Keyed / multi-slot context memory | ✅ | Tier 5.10g repaired the single-slot capacity/interference failure with bounded keyed slots, oracle-key/overcapacity controls, and slot reset/shuffle/wrong-key ablations |
| Calcification | 🔄 | `calcification_rate` defined but effect on graph topology is subtle |
| Sleep / replay consolidation | 📋 | Roadmap only; not implemented or promoted because v1.6 has not yet shown a measured consolidation/decay failure requiring replay |
| Native on-chip state/context slots | 🔄 | Host-writable keyed context/route/memory slots validated on chip (Tiers 4.22r–4.28d). On-chip eligibility traces and autonomous memory updates remain roadmap. |

---

## 5. Task & Domain Adaptation

| Feature | Status | Notes |
|---|---|---|
| Domain-neutral substrate signals | ✅ | `signals.py` `ConsequenceSignal` |
| Trading bridge (finance) | ✅ | `trading_bridge.py` with `PaperTrader` |
| Task adapter interface | ✅ | `task_adapter.py` |
| Non-finance task examples | ✅ | `SignedClassificationAdapter` provides a concrete non-finance adapter |

**Honest position:** The main organism harness is still finance-heavy because `Organism.train_step()` is trading-shaped today. The substrate boundary is no longer finance-only: `task_adapter.py` now includes a concrete signed-classification adapter alongside the trading bridge.

---

## 6. Hardware Constraints & Policy

| Feature | Status | Notes |
|---|---|---|
| Per-core neuron ceiling (255) | ✅ | `spinnaker_constraints.py` + `SpiNNakerConfig.max_atoms_per_core` |
| Router entry ceiling (1024) | ✅ | Documented; C runtime hits this at 1024 neurons |
| SDRAM budgeting | ✅ | Canonical per-core budget is `118 KiB`; memory-derived population caps are bounded by `max_population_hard` |
| Weight clipping to fixed-point | ✅ | `spinnaker_constraints.py` `clip_weights_to_fixed_point()` |
| Live spike extraction | 📋 | Not implemented; would need `LivePacketGather` / IPTag setup |

---

## Known Integrity Issues / Decisions (Post-Cleanup)

1. **Weight model:** Canonical range is now `[-1, 1]` float host-side, `s16.15` chip-side. `polyp_neuron.py` `STDP_W_MAX` fixed from 5.0 → 1.0.
2. **Config source of truth:** `config.py` is authoritative. `config_adapters.py` now passes the root energy/learning config objects through directly instead of copying partial subsets.
3. **Dopamine source:** `LearningManager` is the canonical dopamine producer during organism training. Task bridges may emit diagnostic dopamine, but `Organism` delivers `learning_result.raw_dopamine` to backend STDP.
4. **Lifecycle identity:** Lifecycle-created child `polyp_id` and `lineage_id` are preserved when allocating hardware slots in `PolypPopulation`.
5. **Dataclass names:** `reef_network.py` `ReefConfig` renamed to `ReefNetworkConfig` to avoid collision with root `ReefConfig`.
6. **SDP protocol:** Verified against AppNote 4 and Rig `SDPPacket` source. `colony_controller.py` uses correct 2-byte padding + 8-byte header order.
7. **C runtime decision:** Python/PyNN remains mainline. The bare-metal C runtime scaffold is hardware-validated (build, load, SDP command, MCPL routing, spike-readback, learning-loop, pending horizon, task micro-loops through 4.28d). Full CRA substrate migration remains future work.
