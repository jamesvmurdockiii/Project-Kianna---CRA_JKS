# Polyp Microcircuit Design Specification

## Status
**APPROVED for Phase 1 implementation** — v2.1 with 5 guardrails applied.

## Decision
Each polyp is a **local recurrent spiking microcircuit** (minicolumn-scale), not a single neuron.

The reef remains a **polyp-level graph**. Edges connect polyps, not individual neurons.

---

## 1. Internal Polyp Blueprint (v1)

```text
Polyp (microcircuit)
├── input neurons        n=8   receives external stream & inter-polyp input
├── excitatory pool      n=16  recurrent computation
├── inhibitory pool      n=4   stabilization / global normalization
└── readout neurons      n=4   projects to other polyps + colony readout

Total: 32 neurons per polyp
```

### Why these counts?

| Group | Count | Role |
|-------|-------|------|
| input | 8 | Multiplex sensory streams + inter-polyp afferents. Small bottleneck forces feature extraction. |
| excitatory | 16 | Core recurrent dynamics. Enough for weak attractors, not overparameterized. |
| inhibitory | 4 | ~20% E/I ratio. Global divisive normalization within the polyp. |
| readout | 4 | More stable aggregate signal, less fragile to single-neuron dominance, better summary statistics. |

---

## 2. Indexing Contract (Zero Ambiguity)

For a global Population of size `max_polyps × 32`, polyp slot `p` (0-indexed) occupies:

```python
BASE = p * 32

input_slice     = slice(BASE + 0,  BASE + 8)    # 8 neurons
exc_slice       = slice(BASE + 8,  BASE + 24)   # 16 neurons
inh_slice       = slice(BASE + 24, BASE + 28)   # 4 neurons
readout_slice   = slice(BASE + 28, BASE + 32)   # 4 neurons
```

This is **hard-coded** in v1. No runtime recomputation. No flexibility.

Per-polyp host state stores these slices explicitly:

```python
@dataclass
class PolypBlock:
    polyp_id: int
    slot_index: int           # which polyp slot (0..max_polyps-1)
    base_index: int           # BASE = slot_index * 32
    input_slice: slice
    exc_slice: slice
    inh_slice: slice
    readout_slice: slice
    is_alive: bool
```

### Helper methods (required)

```python
def input_slice(slot_index: int) -> slice:     return slice(slot_index*32 + 0,  slot_index*32 + 8)
def exc_slice(slot_index: int) -> slice:       return slice(slot_index*32 + 8,  slot_index*32 + 24)
def inh_slice(slot_index: int) -> slice:       return slice(slot_index*32 + 24, slot_index*32 + 28)
def readout_slice(slot_index: int) -> slice:   return slice(slot_index*32 + 28, slot_index*32 + 32)
```

---

## 3. Internal Connection Template (Fixed at Birth)

**Not random.** A **deterministic template** with controlled randomness.

### Allowed pathways

```text
input      → excitatory    (sparse, fixed)
input      → inhibitory    (sparse, fixed)
excitatory → excitatory    (sparse recurrent, fixed)
excitatory → inhibitory    (sparse, fixed)
inhibitory → excitatory    (all-to-all or dense, fixed)
excitatory → readout       (sparse, fixed)
```

### Forbidden pathways in v1

```text
input      → readout       (no shortcut)
input      → input         (no autapse)
inhibitory → readout       (no suppression of readout)
readout    → anything      (readout is output-only in v1)
inhibitory → inhibitory    (no I→I in v1)
```

### Exact template parameters

| Pathway | Fan-out | Weight | Delay | Notes |
|---------|---------|--------|-------|-------|
| input → excitatory | each input → 4 random exc targets | 0.15 | 1.0 ms | Sparse, fixed targets at birth |
| input → inhibitory | each input → 2 random inh targets | 0.10 | 1.0 ms | Sparse |
| excitatory → excitatory | each exc → 4 random exc targets | lognormal(μ=0.1, σ=0.5) | 1.0 ms | No self-connections |
| excitatory → inhibitory | each exc → 2 random inh targets | 0.20 | 1.0 ms | Sparse |
| inhibitory → excitatory | each inh → ALL exc targets | **-0.40** | 1.0 ms | Global divisive normalization |
| excitatory → readout | each exc → 2 random readout targets | 0.10 | 1.0 ms | Sparse |

**All internal synapses are StaticSynapse in v1. No STDP inside the polyp.**

### Template instantiation at birth

```python
def instantiate_internal_template(slot_index: int, seed: int) -> List[Tuple[int, int, float, float]]:
    """Return a list of (pre, post, weight, delay) for all internal synapses."""
    rng = np.random.RandomState(seed + slot_index)
    BASE = slot_index * 32
    conns = []

    # Neuron index helpers
    def input_idx(i):   return BASE + 0 + i
    def exc_idx(i):     return BASE + 8 + i
    def inh_idx(i):     return BASE + 24 + i
    def readout_idx(i): return BASE + 28 + i

    # input -> excitatory (each input -> 4 random exc)
    for i_in in range(8):
        targets = rng.choice(16, size=4, replace=False)
        for t in targets:
            conns.append((input_idx(i_in), exc_idx(t), 0.15, 1.0))

    # input -> inhibitory (each input -> 2 random inh)
    for i_in in range(8):
        targets = rng.choice(4, size=2, replace=False)
        for t in targets:
            conns.append((input_idx(i_in), inh_idx(t), 0.10, 1.0))

    # excitatory -> excitatory (each exc -> 4 random exc, no self)
    for i_exc in range(16):
        targets = rng.choice(16, size=4, replace=False)
        for t in targets:
            if t != i_exc:
                w = float(rng.lognormal(mean=np.log(0.1), sigma=0.5))
                conns.append((exc_idx(i_exc), exc_idx(t), w, 1.0))

    # excitatory -> inhibitory (each exc -> 2 random inh)
    for i_exc in range(16):
        targets = rng.choice(4, size=2, replace=False)
        for t in targets:
            conns.append((exc_idx(i_exc), inh_idx(t), 0.20, 1.0))

    # inhibitory -> excitatory (each inh -> ALL exc)
    for i_inh in range(4):
        for t in range(16):
            conns.append((inh_idx(i_inh), exc_idx(t), -0.40, 1.0))

    # excitatory -> readout (each exc -> 2 random readout)
    for i_exc in range(16):
        targets = rng.choice(4, size=2, replace=False)
        for t in targets:
            conns.append((exc_idx(i_exc), readout_idx(t), 0.10, 1.0))

    return conns
```

**Total internal synapses per polyp**: ~8×4 + 8×2 + 16×4 + 16×2 + 4×16 + 16×2 = **312 synapses**

For 100 polyps: **31,200 internal synapses** — well within SpiNNaker capacity.

---

## 4. Internal Projection Grouping (Guardrail #1)

### Verified behavior

PyNN/NEST **does** support mixed positive/negative weights in a single Projection with `receptor_type="excitatory"`. Negative weights subtract from the membrane potential numerically.

### Decision for v1

Use **2 internal Projections per polyp**, grouped by receptor/sign family:

```text
internal_exc_proj  (receptor_type="excitatory")
    input → excitatory
    excitatory → excitatory
    excitatory → inhibitory
    excitatory → readout

internal_inh_proj  (receptor_type="inhibitory")
    inhibitory → excitatory
```

**Rationale:**
- Cleaner semantic separation of excitatory and inhibitory pathways
- Allows future tuning of inhibitory receptor dynamics independently
- Only 2 Projections per polyp — still manageable
- Avoids the biological awkwardness of labeling I→E as "excitatory receptor with negative weight"

### Implementation

```python
exc_conns = [c for c in all_conns if c[2] > 0]   # positive weights
inh_conns = [c for c in all_conns if c[2] < 0]   # negative weights

proj_exc = sim.Projection(
    population, population,
    sim.FromListConnector(exc_conns),
    synapse_type=sim.StaticSynapse(),
    receptor_type="excitatory",
    label=f"polyp_{slot}_exc"
)

proj_inh = sim.Projection(
    population, population,
    sim.FromListConnector(inh_conns),
    synapse_type=sim.StaticSynapse(),
    receptor_type="inhibitory",
    label=f"polyp_{slot}_inh"
)
```

---

## 5. Polyp Summary / Readout Contract (Guardrail #2)

After each `sim.run()`, the host reads spikes and computes **exactly** these scalars:

### Exact equations

```python
@dataclass
class PolypSummary:
    polyp_id: int

    # Firing rates (spikes per ms, normalized to [0, 1] against max theoretical rate)
    input_rate: float       # mean firing rate over 8 input neurons
    exc_rate: float         # mean firing rate over 16 excitatory neurons
    inh_rate: float         # mean firing rate over 4 inhibitory neurons
    readout_rate: float     # mean firing rate over 4 readout neurons

    # Colony-facing signals
    activity_rate: float    # alias for readout_rate (used by WTA)

    # Signed prediction: differential readout weighted by output_scale
    # Uses first two readout neurons as differential pair
    prediction: float       # tanh(output_scale * (rate_r0 - rate_r1))

    # Confidence: how concentrated the readout activity is
    # High when one readout neuron dominates; low when all four fire equally
    confidence: float       # clip(max_rate / (mean_rate + epsilon), 0.0, 1.0)
                            # where max_rate = max(rate_r0, rate_r1, rate_r2, rate_r3)
                            #       mean_rate = mean(rate_r0..rate_r3)

    # Diagnostic
    n_spikes_total: int     # total spikes across all 32 neurons this step
```

### Normalization

All rates are computed as:

```python
def compute_rate(n_spikes: int, n_neurons: int, runtime_ms: float) -> float:
    """Return normalized firing rate in [0, 1]."""
    if runtime_ms <= 0 or n_neurons <= 0:
        return 0.0
    rate_hz = (n_spikes / n_neurons) / runtime_ms * 1000.0
    max_rate_hz = 1000.0 / tau_refrac_ms  # ~500 Hz for tau_refrac=2ms
    return min(1.0, rate_hz / max_rate_hz)
```

### How colony readout works

1. Compute `PolypSummary` for every alive polyp
2. WTA selection: top-K by `readout_rate`
3. Colony prediction = weighted sum of `prediction` from top-K, weighted by `readout_rate * confidence`

---

## 6. Sensory Input Contract (Guardrail #3)

### v1: Current injection into input subgroup

External market streams are converted to currents and injected **only into input neurons**:

```python
# Per step, per stream:
current_per_stream = stream_value * uptake_rate * scale_factor

# Inject into ALL input neurons of polyps that claim this stream
for polyp in claimants:
    for neuron_idx in polyp.input_slice:
        population[neuron_idx].set(i_offset=current_per_stream)
```

### Why not Poisson?

- Deterministic for debugging
- No extra Population objects
- Easy causal tracing

### Future path

The input API should accept an abstraction:

```python
class PolypInputEncoder(ABC):
    def encode(self, stream_value: float, target_neurons: List[int]) -> None: ...

class CurrentInjectionEncoder(PolypInputEncoder):
    """v1: direct i_offset injection."""
    def encode(self, stream_value, target_neurons):
        for nid in target_neurons:
            population[nid].set(i_offset=stream_value)

class PoissonSpikeEncoder(PolypInputEncoder):
    """Future: Poisson spike sources."""
    def encode(self, stream_value, target_neurons): ...
```

This lets us swap encoders later without changing `organism.py`.

---

## 7. Birth Semantics (Exact)

When a polyp reproduces:

1. **Find dead slot** in global population
2. **Assign identity**: new `polyp_id`, `lineage_id`
3. **Instantiate internal template**:
   - Call `instantiate_internal_template(slot_index, seed=config.internal_conn_seed)`
   - Split into excitatory and inhibitory connection lists
   - Create **2 PyNN Projections** for this polyp's internal synapses
   - Store references in `PolypState._internal_proj_exc` and `_internal_proj_inh`
4. **Inherit traits**: copy parent's scalar traits with log-normal mutation
5. **Inherit ecology**: split trophic reserve
6. **Set initial currents**: based on inherited `uptake_rate`, `da_gain`
7. **Create inter-polyp edges**: `ReefEdge(parent, child)` and `ReefEdge(child, parent)`
8. **Mark juvenile**: `is_juvenile = True`, start handoff

Internal projections are created once at birth and **never modified** in v1.

---

## 8. Death Semantics (Guardrail #4)

When a polyp dies:

### Host-level (required)

```text
- Set is_alive = False
- Set activity_rate = 0, prediction = 0, confidence = 0
- Remove from WTA selection
- Do not count in n_alive
- Do not participate in trophic economy
- Do not receive sensory input
```

### Graph-level (required)

```text
- All ReefEdges incident to dead polyp are marked is_pruned = True
- Dead polyp is never source or target of new edges
- On next sync, pruned edges are removed from batched Projection
```

### Backend-level (best-effort)

```text
- Set i_offset = -1000.0 for all 32 neurons in the block
- Set v_thresh = 1000.0 for all 32 neurons in the block
- Internal Projections are left in place (harmless, saves cost)
- Slot remains allocated and unavailable for reuse in v1
```

### What "dead" means

A dead polyp contributes **nothing** to:
- colony readout / WTA
- trophic economy (no earning, no spending)
- graph topology (no edges expanded)
- sensory processing (no input injected)
- summary statistics

Even if residual backend spikes occur, the host **ignores** them.

---

## 9. Inter-Polyp Connection Contract

### v1 motif: readout → input

A single `ReefEdge(source=A, target=B, weight=w)` expands to:

```text
A.readout neurons (4)  --(w)-->  B.input neurons (8)
```

All-to-all from readout to input. **16 synapses per edge.**

### Batching

All inter-polyp edges are collapsed into **ONE** PyNN Projection per sync cycle:

```python
conn_list = [
    (A_base + 28 + r, B_base + 0 + i, w, 1.0)
    for each ReefEdge(A, B, w)
    for r in range(4)      # A readout neurons
    for i in range(8)      # B input neurons
]
```

This projection uses `StaticSynapse` or `STDPMechanism` depending on config.

---

## 10. Sync Policy (Guardrail #5)

### Inter-polyp projection rebuild policy

```text
Default: rebuild only on topology change
        (edge added, edge pruned, polyp born, polyp dies)

Fallback: if backend does not support in-place weight updates,
          rebuild every N host steps where N = sync_interval_steps

Emergency: if weight corruption is suspected, force full rebuild
```

### Why not every step?

- Full rebuild deletes and recreates the Projection object
- Expensive on NEST, very expensive on SpiNNaker
- Most steps have no topology change
- Weight-only updates should use `proj.set(weight=...)` if backend allows

### Implementation

```python
def sync_to_spinnaker(self) -> None:
    # 1. Check if topology changed since last sync
    if not self._topology_changed:
        # Only update weights in-place if possible
        self._update_weights_in_place()
        return

    # 2. Full rebuild
    self._delete_batched_projection()
    self._create_batched_projection()
    self._topology_changed = False
```

For v1 simplicity, we may default to `sync_interval_steps=1` (rebuild every step) until profiling shows it's a bottleneck. But the **architecture** must support change-only rebuilds.

---

## 11. PyNN Mapping

### Global Population layout

```text
Population("cra_polyps", size=max_polyps * 32)
  [polyp0: 0-31]
  [polyp1: 32-63]
  [polyp2: 64-95]
  ...
```

### Projections

| Projection | Count | Lifetime |
|------------|-------|----------|
| Internal excitatory per polyp | `n_alive` | Created at birth, never destroyed |
| Internal inhibitory per polyp | `n_alive` | Created at birth, never destroyed |
| Inter-polyp (batched) | 1 | Rebuilt on topology change |
| Gap junctions | `n_gap_pairs` | Created on demand, persisted |

**Why 2 internal Projections per polyp instead of 1:**
- Semantically correct receptor types (excitatory vs inhibitory)
- Allows independent tuning of inhibitory dynamics later
- Only 2× the Projection objects — still manageable
- Avoids mixing receptor families in one Projection

**Future optimization**: if `n_alive` gets large enough that per-polyp Projection objects become a bottleneck, batch all internal synapses into 2 global internal Projections (one exc, one inh). This is a drop-in optimization.

---

## 12. Polyp-Level State

All ecology, lifecycle, reproduction, and graph-topology decisions use scalar `PolypState`. No per-neuron bookkeeping.

The only additions are subgroup slices and internal projection references:

```python
@dataclass
class PolypState:
    # Identity & block
    polyp_id: int
    lineage_id: int
    slot_index: int
    base_index: int
    input_slice: slice
    exc_slice: slice
    inh_slice: slice
    readout_slice: slice
    n_neurons_per_polyp: int = 32

    # Internal projection references (created at birth, never modified in v1)
    _internal_proj_exc: Optional[Any] = None
    _internal_proj_inh: Optional[Any] = None

    # Trophic ecology (all scalar)
    trophic_health: float = 1.0
    metabolic_decay: float = 0.005
    ...
```

---

## 13. Configuration Additions

```python
@dataclass
class SpiNNakerConfig:
    ...
    # Microcircuit size (must sum to 32)
    n_neurons_per_polyp: int = 32
    n_input_per_polyp: int = 8
    n_exc_per_polyp: int = 16
    n_inh_per_polyp: int = 4
    n_readout_per_polyp: int = 4

    # Internal connectivity
    internal_conn_seed: int = 42
    input_to_exc_weight: float = 0.15
    input_to_inh_weight: float = 0.10
    exc_to_exc_mean: float = 0.1
    exc_to_exc_sigma: float = 0.5
    exc_to_inh_weight: float = 0.20
    inh_to_exc_weight: float = -0.40
    exc_to_readout_weight: float = 0.10

    # Internal topology
    input_to_exc_fanout: int = 4
    input_to_inh_fanout: int = 2
    exc_to_exc_fanout: int = 4
    exc_to_inh_fanout: int = 2
    exc_to_readout_fanout: int = 2
```

---

## 14. Migration Plan

### Phase 1: Block layout & indexing
- Update `PolypState` with slices, `base_index`, `slot_index`
- Update `PolypPopulation` to allocate 32-neuron blocks
- Add helper methods: `input_slice()`, `exc_slice()`, `inh_slice()`, `readout_slice()`
- Verify `get_spike_counts` can return per-subgroup counts

### Phase 2: Internal template instantiation at birth
- Implement `instantiate_internal_template()`
- Split into exc/inh connection lists
- `add_polyp` creates 2 internal Projections
- Verify internal dynamics are stable (run NEST, check firing rates)

### Phase 3: Inter-polyp readout→input expansion + batched Projection
- `ReefNetwork._create_projection` expands edges readout→input
- Single batched Projection with topology-change-only rebuilds

### Phase 4: Input subgroup current injection + PolypSummary readout
- Inject currents into input subgroup only
- Add `PolypInputEncoder` abstraction
- Implement exact `prediction` and `confidence` equations
- Verify signal propagation: input → exc → readout

### Phase 5: NEST validation & stability test
- Run full demo with microcircuits
- Compare stability vs single-neuron baseline
- Verify constraint checker passes
- Verify dead-slot semantics

---

## 15. Future Fields (Do Not Block v1)

The `PolypSummary` may eventually need:
- `stability` — rate variance over recent steps
- `novelty` — deviation from expected firing pattern
- `delta_activity` — change from previous step

These are **not** required for Phase 1–5.

---

*End of APPROVED SPEC v2.1*
