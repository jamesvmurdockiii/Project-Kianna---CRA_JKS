# Polyp Microcircuit Architecture v2.0
## Canonical Cortical Column on SpiNNaker
## For Coral Reef Architecture — April 22, 2026

---

## The Premise

A single LIF neuron cannot do AGI. A cortical microcircuit might be the smallest unit that can.

This document sketches a **biologically grounded cortical column** as the new "polyp" unit for Coral Reef. Each polyp becomes a ~50-100 neuron canonical microcircuit with distinct cell types, layers, and motifs.

**Key insight:** Mountcastle (1957) showed the cortex is organized into ~300µm columns with ~100 neurons each. Douglas & Martin (2004) showed these columns share a common "canonical circuit" across all cortical areas. **A column is the brain's reusable computational module.**

---

## The Microcircuit: 4 Layers, 5 Cell Types

```
                    ┌─────────────────────────────────────┐
                    │  INPUT LAYER (L4 analog)            │
                    │  12 pyramidal + 2 PV+ interneurons  │
                    │  Receives thalamic / sensory input    │
                    │  Fast adaptation, precise timing      │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  SUPERFICIAL LAYER (L2/3 analog)    │
                    │  16 pyramidal + 4 SST+ + 2 VIP+     │
                    │  Lateral connectivity, binding      │
                    │  Working memory, pattern completion   │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  DEEP LAYER (L5 analog)             │
                    │  10 pyramidal + 3 PV+ + 1 NGF+     │
                    │  Output to other columns, action    │
                    │  Bursting, motor/executive function   │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  CONTEXT LAYER (L6 analog)          │
                    │  6 pyramidal + 2 SST+ + 1 VIP+     │
                    │  Top-down modulation, prediction      │
                    │  Feedback to L4 (predictive coding) │
                    └─────────────────────────────────────┘
```

**Total per polyp: ~60-80 neurons** (vs. current 1)

---

## Cell Types & Parameters

### Excitatory Pyramidal Cells (E)

```python
pyramidal_params = {
    'C_m': 250.0,        # pF
    'tau_m': 20.0,       # ms
    'tau_refrac': 2.0,   # ms
    'v_rest': -70.0,     # mV
    'v_reset': -70.0,    # mV
    'v_thresh': -55.0,   # mV
    'tau_syn_E': 5.0,    # ms (AMPA)
    'tau_syn_I': 10.0,   # ms (GABA-A)
    'i_offset': 0.0,     # Baseline drive
}
```

**L5 pyramidal special:** Lower threshold (`v_thresh=-50`), longer refractory (`tau_refrac=5.0`) — they're "output" neurons, meant to fire bursts.

### Parvalbumin+ Fast-Spiking Interneurons (PV)

```python
pv_params = {
    'C_m': 100.0,
    'tau_m': 10.0,       # Faster membrane
    'tau_refrac': 1.0,   # Very fast
    'v_rest': -65.0,
    'v_reset': -65.0,
    'v_thresh': -50.0,   # Lower threshold
    'tau_syn_E': 2.0,    # Fast AMPA
    'tau_syn_I': 5.0,    # Fast GABA
}
```

**Role:** Perisomatic inhibition. PV cells receive from all pyramidal cells in the column and inhibit them back. Creates **winner-take-all** dynamics within the column.

### Somatostatin+ Interneurons (SST)

```python
sst_params = {
    'C_m': 150.0,
    'tau_m': 15.0,
    'tau_refrac': 2.0,
    'v_rest': -70.0,
    'v_reset': -70.0,
    'v_thresh': -52.0,
    'tau_syn_E': 5.0,
    'tau_syn_I': 8.0,
}
```

**Role:** Dendritic inhibition. SST cells target distal dendrites of pyramidal cells. They receive top-down feedback (from L6/deep layers) and **gate plasticity** — when SST fires, it suppresses dendritic calcium, blocking STDP. This is your **modulatory plasticity gating**.

### Vasoactive Intestinal Peptide+ Interneurons (VIP)

```python
vip_params = {
    'C_m': 120.0,
    'tau_m': 12.0,
    'tau_refrac': 2.0,
    'v_rest': -68.0,
    'v_reset': -68.0,
    'v_thresh': -50.0,
    'tau_syn_E': 3.0,
    'tau_syn_I': 6.0,
}
```

**Role:** Disinhibition. VIP cells receive top-down/context signals and **inhibit the interneurons that inhibit pyramidal cells**. They "release the brakes." When attention/context is active, VIP fires → PV/SST are suppressed → pyramidal cells can fire freely.

### Neurogliaform Interneurons (NGF) — Optional

```python
ngf_params = {
    'C_m': 80.0,
    'tau_m': 25.0,       # Slow
    'tau_refrac': 3.0,
    'v_rest': -75.0,
    'v_reset': -75.0,
    'v_thresh': -55.0,
    'tau_syn_E': 8.0,
    'tau_syn_I': 15.0,   # Slow GABA
}
```

**Role:** Volume transmission, slow GABA. NGFs don't target specific synapses — they release GABA broadly, creating a "slow tonic inhibition" field. Think of this as **ambient noise regulation** or **column-level gain control**.

---

## Internal Wiring (The Canonical Circuit)

### Within-Layer Recurrence

```python
# L2/3 pyramidal ↔ L2/3 pyramidal (recurrent excitation)
sim.Projection(l23_pyr, l23_pyr, sim.FixedProbabilityConnector(p_connect=0.2),
    synapse_type=sim.StaticSynapse(weight=0.05, delay=1.0))

# L2/3 pyramidal → L2/3 SST (disynaptic inhibition via pyramidal activation)
sim.Projection(l23_pyr, l23_sst, sim.AllToAllConnector(),
    synapse_type=sim.StaticSynapse(weight=0.15, delay=1.0))

# L2/3 SST → L2/3 pyramidal (dendritic inhibition)
sim.Projection(l23_sst, l23_pyr, sim.AllToAllConnector(),
    synapse_type=sim.StaticSynapse(weight=-0.30, delay=2.0))

# L2/3 PV → L2/3 pyramidal (perisomatic inhibition, WTA)
sim.Projection(l23_pv, l23_pyr, sim.AllToAllConnector(),
    synapse_type=sim.StaticSynapse(weight=-0.50, delay=0.5))

# L2/3 pyramidal → L2/3 PV (feedback inhibition)
sim.Projection(l23_pyr, l23_pv, sim.AllToAllConnector(),
    synapse_type=sim.StaticSynapse(weight=0.20, delay=0.5))
```

**Result:** L2/3 implements a **dynamic attractor network**. When a pattern is presented, recurrent excitation amplifies it while PV-mediated inhibition suppresses competing patterns. Only the best-matching pattern survives — **soft WTA within the column**.

### Feedforward Flow (L4 → L2/3)

```python
# L4 pyramidal → L2/3 pyramidal (feedforward)
sim.Projection(l4_pyr, l23_pyr, sim.AllToAllConnector(),
    synapse_type=sim.STDPMechanism(...))  # Plastic!

# L4 pyramidal → L2/3 PV (feedforward inhibition)
sim.Projection(l4_pyr, l23_pv, sim.AllToAllConnector(),
    synapse_type=sim.StaticSynapse(weight=0.30, delay=0.5))
```

**Result:** L4 drives L2/3, but L2/3 PV cells also receive feedforward input. This creates **feedforward inhibition** — when L4 fires strongly, it activates L2/3 PV cells which suppress L2/3 pyramidal firing. This normalizes responses and prevents runaway excitation.

### Deep Output (L2/3 → L5)

```python
# L2/3 pyramidal → L5 pyramidal (cortical output)
sim.Projection(l23_pyr, l5_pyr, sim.AllToAllConnector(),
    synapse_type=sim.STDPMechanism(...))  # Plastic!

# L5 pyramidal → L5 PV (local inhibition)
sim.Projection(l5_pyr, l5_pv, sim.AllToAllConnector(),
    synapse_type=sim.StaticSynapse(weight=0.25, delay=0.5))

# L5 PV → L5 pyramidal (WTA)
sim.Projection(l5_pv, l5_pyr, sim.AllToAllConnector(),
    synapse_type=sim.StaticSynapse(weight=-0.60, delay=0.5))
```

**Result:** L5 is the "output" layer. It integrates L2/3 activity and produces the column's final response. Because L5 pyramidal cells have lower thresholds, they can "burst" when L2/3 input is strong — **this is your colony readout signal**.

### Top-Down / Predictive Coding (L6 → L4, L2/3)

```python
# L6 pyramidal → L4 pyramidal (feedback / prediction)
sim.Projection(l6_pyr, l4_pyr, sim.AllToAllConnector(),
    synapse_type=sim.StaticSynapse(weight=0.10, delay=3.0))

# L6 pyramidal → L2/3 SST (modulatory, gates plasticity)
sim.Projection(l6_pyr, l23_sst, sim.AllToAllConnector(),
    synapse_type=sim.StaticSynapse(weight=0.20, delay=2.0))

# L6 pyramidal → L2/3 VIP (disinhibition / attention)
sim.Projection(l6_pyr, l23_vip, sim.AllToAllConnector(),
    synapse_type=sim.StaticSynapse(weight=0.15, delay=2.0))

# L2/3 VIP → L2/3 SST (VIP inhibits SST → releases pyramidal inhibition)
sim.Projection(l23_vip, l23_sst, sim.AllToAllConnector(),
    synapse_type=sim.StaticSynapse(weight=-0.20, delay=1.0))
```

**Result:** This implements **predictive coding** (Rao & Ballard, 1999; Friston, 2005). L6 carries predictions about what input to expect. It:
1. Depolarizes L4 (expectation signal)
2. Activates SST (prepares to suppress "predicted" input)
3. Activates VIP ("pay attention to this")

When actual input matches prediction, SST suppresses L2/3 pyramidal firing ("nothing new to learn"). When input is unexpected, SST is not activated enough, L2/3 fires strongly, and STDP updates synapses ("learn this").

**This is your BOCPD changepoint detector, implemented in spikes.**

---

## Between-Polyp (Inter-Column) Wiring

### Feedforward (Sensory Up)

```python
# Polyp A L5 (output) → Polyp B L4 (input)
sim.Projection(polyp_a.l5_pyr, polyp_b.l4_pyr,
    sim.FixedProbabilityConnector(p_connect=0.15),
    synapse_type=sim.STDPMechanism(...))
```

### Lateral (Same Level)

```python
# Polyp A L2/3 → Polyp B L2/3 (lateral binding)
sim.Projection(polyp_a.l23_pyr, polyp_b.l23_pyr,
    sim.FixedProbabilityConnector(p_connect=0.10),
    synapse_type=sim.StaticSynapse(weight=0.03, delay=2.0))

# Polyp A L2/3 SST → Polyp B L2/3 pyramidal (lateral suppression)
sim.Projection(polyp_a.l23_sst, polyp_b.l23_pyr,
    sim.FixedProbabilityConnector(p_connect=0.05),
    synapse_type=sim.StaticSynapse(weight=-0.10, delay=3.0))
```

**Result:** Lateral excitation binds related features (e.g., edge detectors that form a contour). Lateral inhibition creates **sparse coding** — only the most salient columns activate.

### Feedback (Top-Down)

```python
# Polyp B L6 → Polyp A L6 (hierarchical prediction)
sim.Projection(polyp_b.l6_pyr, polyp_a.l6_pyr,
    sim.FixedProbabilityConnector(p_connect=0.20),
    synapse_type=sim.StaticSynapse(weight=0.08, delay=5.0))
```

**Result:** Higher-level polyps predict lower-level polyps. This is how the colony builds **hierarchical representations** — raw pixels → edges → shapes → objects → concepts.

---

## Trophic Economy Re-Mapped to Microcircuit

The current trophic system maps naturally:

| Current (1 neuron) | New (microcircuit) |
|---|---|
| `i_offset` (injected current) | `i_offset` across **all pyramidal cells** in the column |
| Spike count (activity) | **L5 burst rate** (output layer firing) |
| `activity_rate` | Normalized L5 population firing rate |
| Death (v_thresh=1000) | **Global inhibition**: all interneurons fire strongly, suppress all pyramidal cells + set all thresholds high |
| Sensory capture (MI with input stream) | **L4-L2/3 plasticity strength** — how much the column learned from its stream |
| Outcome capture (prediction reward) | **L5 burst correlation with reward signal** |
| Retrograde capture (BDNF) | **L5→L2/3 feedback weight strength** |
| Dopamine EMA | **VIP cell activation** — VIP is literally the dopamine analog here |

**Key insight:** Your current `PolypState` dataclass stays structurally the same. It just now tracks **aggregate population statistics** instead of single-neuron state:

```python
@dataclass
class PolypState:
    polyp_id: int
    is_alive: bool
    # Aggregate circuit state
    l5_firing_rate: float       # Was: activity_rate
    l23_pattern_stability: float # New: attractor convergence measure
    prediction_error: float     # New: L4 actual vs L6 prediction mismatch
    attention_gain: float       # New: VIP activation level
    trophic_health: float       # Same concept
    # ... rest stays similar
```

---

## Plasticity: Where STDP Lives

**STDP on plastic synapses only:**

```python
# L4 → L2/3: Learns feature selectivity
stdp_l4_l23 = sim.STDPMechanism(
    timing_dependence=sim.SpikePairRule(tau_plus=20, tau_minus=20, A_plus=0.01, A_minus=0.01),
    weight_dependence=sim.AdditiveWeightDependence(w_min=0.0, w_max=0.5)
)

# L2/3 → L5: Learns output mapping
stdp_l23_l5 = sim.STDPMechanism(
    timing_dependence=sim.SpikePairRule(tau_plus=20, tau_minus=20, A_plus=0.01, A_minus=0.01),
    weight_dependence=sim.AdditiveWeightDependence(w_min=0.0, w_max=0.8)
)

# Polyp_A L5 → Polyp_B L4: Learns inter-column associations
stdp_inter = sim.STDPMechanism(
    timing_dependence=sim.SpikePairRule(tau_plus=30, tau_minus=30, A_plus=0.005, A_minus=0.005),
    weight_dependence=sim.AdditiveWeightDependence(w_min=0.0, w_max=0.3)
)
```

**Dopamine modulation:** VIP cell activity scales the STDP A+/A- parameters via the host sync loop (same as current system, just reading VIP spikes instead of a scalar dopamine EMA).

**SST gating:** When SST fires strongly (high prediction = low error), it suppresses dendritic calcium in pyramidal cells, which **blocks STDP**. This is biologically accurate — STDP requires postsynaptic calcium, and SST closes calcium channels.

---

## Scaling to AGI: What This Buys You

### What a Single-Neuron Polyp CANNOT Do
- No memory (stateless)
- No pattern completion
- No gain control
- Cannot represent conjunctions ("A AND B")
- Cannot gate learning by context

### What a Microcircuit Polyp CAN Do
- **Attractor dynamics** (working memory): L2/3 recurrent connections form stable activity patterns that persist after input is removed
- **Pattern completion**: Partial input → full internal representation via recurrence
- **Gain control**: PV/SST balance means the column is "excitable" or "suppressed" based on context
- **Conjunction coding**: L2/3 recurrent excitation means the column only fires when multiple converging inputs align
- **Context-gated learning**: SST/VIP control whether plasticity is active

### Scaling to AGI: The Colony Level

With microcircuit polyps, the colony can build:

1. **Hierarchical representations** (predictive coding)
   - Layer 1 polyps: raw feature detectors
   - Layer 2 polyps: edge/contour detectors (predictions from Layer 1)
   - Layer 3 polyps: shape/object detectors
   - Layer N polyps: abstract concept cells
   - **This is a deep network, but it's built by evolution, not backprop.**

2. **Working memory** (attractor states)
   - A column that received a stimulus keeps firing via recurrence
   - The colony "remembers" recent context
   - Useful for: sequential tasks, trading (recent market regime), reasoning

3. **Attention** (VIP-mediated disinhibition)
   - Certain columns are "selected" by VIP activation
   - Others are suppressed by SST
   - The colony focuses computational resources on relevant features

4. **Compositional structure** (inter-column binding)
   - Lateral connections bind co-occurring features
   - "Red" + "Round" + "Edible" → "Apple"
   - This is **symbolic composition** emerging from spikes

### What You Still Don't Have (Honest Assessment)

Even with microcircuits, you're missing:

- **Long-term credit assignment** — STDP has a ~50ms window. How does a column learn that an action 10 minutes ago caused a reward? You'd need **eligibility traces** or **reward-modulated STDP** with longer time constants.
- **Symbolic manipulation** — Attractors and binding are great, but true reasoning requires variable binding, unification, search. Neural Turing Machines or working memory stacks might be needed.
- **Meta-learning** — The colony learns tasks, but does it learn *how* to learn? Does it adapt its plasticity rules, architecture, or exploration strategy?
- **World models** — For AGI, you need a model of the environment (physics, causality, other agents). Your current system predicts market returns, not "what happens if I do X."

**These are hard problems.** Nobody has solved them. Microcircuits get you from "toy" to "interesting," but AGI is still a research frontier.

---

## SpiNNaker Considerations

### Memory Per Polyp

| Component | Neurons | Synapses | Memory |
|---|---|---|---|
| L4 | 14 | ~200 | ~8 KB |
| L2/3 | 22 | ~600 | ~24 KB |
| L5 | 14 | ~300 | ~12 KB |
| L6 | 9 | ~150 | ~6 KB |
| Internal | — | ~400 | ~16 KB |
| **Total** | **~60** | **~1650** | **~66 KB** |

A SpiNNaker chip has ~1M cores and ~1GB shared SDRAM.
- **Theoretical max:** ~15,000 polyps on one chip
- **Practical max:** ~1,000-2,000 polyps (accounting for routing, overhead, host sync)

Your current colony uses 256 polyps. With microcircuits, that's still well within limits. You could scale to **1,000 microcircuit polyps = 60,000 neurons** on one SpiNNaker board.

### Sync Frequency

Current: every 100ms. With microcircuits:
- **Option A:** Keep 100ms sync, read L5 firing rates only
- **Option B:** 50ms sync for more responsive trophic economy
- **Option C:** 200ms sync for efficiency (host has more work per polyp)

I recommend **100ms** — it's a good tradeoff.

---

## PyNN Implementation Sketch

```python
class PolypMicrocircuit:
    """A cortical column as a Coral Reef polyp."""
    
    def __init__(self, polyp_id: int, sim):
        self.polyp_id = polyp_id
        self.sim = sim
        
        # Create populations
        self.l4_pyr = sim.Population(12, sim.IF_cond_exp, PYRAMIDAL_PARAMS)
        self.l4_pv = sim.Population(2, sim.IF_cond_exp, PV_PARAMS)
        
        self.l23_pyr = sim.Population(16, sim.IF_cond_exp, PYRAMIDAL_PARAMS)
        self.l23_pv = sim.Population(4, sim.IF_cond_exp, PV_PARAMS)
        self.l23_sst = sim.Population(2, sim.IF_cond_exp, SST_PARAMS)
        self.l23_vip = sim.Population(2, sim.IF_cond_exp, VIP_PARAMS)
        
        self.l5_pyr = sim.Population(10, sim.IF_cond_exp, L5_PYRAMIDAL_PARAMS)
        self.l5_pv = sim.Population(3, sim.IF_cond_exp, PV_PARAMS)
        self.l5_ngf = sim.Population(1, sim.IF_cond_exp, NGF_PARAMS)
        
        self.l6_pyr = sim.Population(6, sim.IF_cond_exp, PYRAMIDAL_PARAMS)
        self.l6_sst = sim.Population(2, sim.IF_cond_exp, SST_PARAMS)
        self.l6_vip = sim.Population(1, sim.IF_cond_exp, VIP_PARAMS)
        
        # Internal wiring (canonical circuit)
        self._wire_canonical_circuit()
        
        # Host-side state
        self.state = PolypState(polyp_id=polyp_id)
        
        # Record L5 output
        self.l5_pyr.record('spikes')
    
    def _wire_canonical_circuit(self):
        # L2/3 recurrent
        self.sim.Projection(self.l23_pyr, self.l23_pyr, 
            sim.FixedProbabilityConnector(p_connect=0.2),
            synapse_type=self.sim.StaticSynapse(weight=0.05))
        
        # L2/3 PV WTA
        self.sim.Projection(self.l23_pv, self.l23_pyr,
            sim.AllToAllConnector(),
            synapse_type=self.sim.StaticSynapse(weight=-0.50))
        
        # L4 → L2/3 (plastic)
        self.sim.Projection(self.l4_pyr, self.l23_pyr,
            sim.AllToAllConnector(),
            synapse_type=self.sim.STDPMechanism(...))
        
        # L2/3 → L5 (plastic)
        self.sim.Projection(self.l23_pyr, self.l5_pyr,
            sim.AllToAllConnector(),
            synapse_type=self.sim.STDPMechanism(...))
        
        # L6 → L4 (prediction)
        self.sim.Projection(self.l6_pyr, self.l4_pyr,
            sim.AllToAllConnector(),
            synapse_type=self.sim.StaticSynapse(weight=0.10, delay=3.0))
        
        # L6 → L2/3 SST (plasticity gating)
        self.sim.Projection(self.l6_pyr, self.l23_sst,
            sim.AllToAllConnector(),
            synapse_type=self.sim.StaticSynapse(weight=0.20, delay=2.0))
        
        # ... etc
    
    def read_output(self, runtime_ms: float) -> float:
        """Read L5 firing rate as colony output."""
        spiketrains = self.l5_pyr.get_data('spikes').segments[0].spiketrains
        total_spikes = sum(len(st) for st in spiketrains)
        rate_hz = (total_spikes / runtime_ms) * 1000.0 / len(self.l5_pyr)
        return min(1.0, rate_hz / 100.0)  # Normalize
    
    def set_drive(self, drive: float):
        """Set metabolic drive across all pyramidal cells."""
        i_offset = drive * 2.0  # Convert to nA
        self.l4_pyr.set(i_offset=i_offset)
        self.l23_pyr.set(i_offset=i_offset)
        self.l5_pyr.set(i_offset=i_offset)
        self.l6_pyr.set(i_offset=i_offset)
    
    def soft_death(self):
        """Suppress all pyramidal firing."""
        # All interneurons fire strongly
        self.l23_pv.set(i_offset=100.0)
        self.l5_pv.set(i_offset=100.0)
        # Pyramidal thresholds go high
        self.l4_pyr.set(v_thresh=1000.0)
        self.l23_pyr.set(v_thresh=1000.0)
        self.l5_pyr.set(v_thresh=1000.0)
        self.l6_pyr.set(v_thresh=1000.0)
```

---

## Summary

| | Current (v1) | Proposed (v2) |
|---|---|---|
| **Unit** | 1 LIF neuron | 60-80 neuron cortical column |
| **Internal dynamics** | Threshold + spike | Attractor, WTA, prediction |
| **Cell types** | 1 (E) | 5 (E, PV, SST, VIP, NGF) |
| **Layers** | 0 | 4 (L4, L2/3, L5, L6) |
| **Plasticity** | STDP on 1 synapse | STDP on feature + output + inter-column |
| **Modulation** | Scalar dopamine EMA | VIP/SST gating (biologically realistic) |
| **Predictive coding** | BOCPD on host | L6→L4 prediction (in spikes) |
| **Working memory** | None | L2/3 recurrent attractor |
| **Attention** | None | VIP-mediated disinhibition |
| **Hierarchy** | Flat graph | Deep predictive coding |
| **AGI readiness** | Toy | Research-grade substrate |
| **SpiNNaker neurons** | 256 | ~15,000 (60× per polyp) |
| **SpiNNaker memory** | ~2 MB | ~100 MB (still fine) |

---

## What to Tell Dr. Bjorn

> "Each agent in our colony is not a single neuron — it's a canonical cortical microcircuit based on the Douglas-Martin model. It has excitatory pyramidal cells, fast-spiking PV interneurons for winner-take-all, SST interneurons for dendritic gating, and VIP interneurons for attentional modulation. The circuits implement predictive coding through L6 feedback to L4, working memory through L2/3 recurrent attractors, and context-gated learning through SST-mediated plasticity suppression. The colony as a whole forms a deep predictive network with hierarchical representations, built by evolutionary selection rather than backpropagation. This is running on SpiNNaker neuromorphic hardware via PyNN."

---

*Written for Coral Reef Architecture v2.0 — April 22, 2026*
