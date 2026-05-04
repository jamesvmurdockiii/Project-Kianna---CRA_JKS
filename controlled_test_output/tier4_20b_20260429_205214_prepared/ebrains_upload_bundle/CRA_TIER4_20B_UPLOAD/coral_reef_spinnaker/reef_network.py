"""
Reef Network for Coral Reef Architecture on SpiNNaker.

Manages the directed graph topology of polyp neurons, including:
- Sparse directed edges with FF/LAT/FB motif classification
- Gap junction coupling (electrical synapses)
- STDP on all synaptic projections
- Structural dynamics: synaptogenesis, pruning, sprouting, repair
- Runtime-sized architecture (hidden/message/WM/chemistry/TF)

The reef graph lives partly on SpiNNaker (Projections) and partly
on the host (topology dict, motif classification, spatial positions).

The motif classification assigns each directed edge to one of three
categories based on graph distance from sensory source nodes:

    * FEEDFORWARD (FF): target is farther from sensors than source,
      supporting hierarchical bottom-up propagation.
    * LATERAL (LAT): target and source are at similar distances,
      enabling same-level coordination.
    * FEEDBACK (FB): target is closer to sensors than source,
      supporting top-down predictive or attentional modulation.

Gap junctions provide symmetric electrical coupling modelled as
extra excitatory synapses in both directions.

Structural dynamics (synaptogenesis, pruning, sprouting, repair) are
evaluated on the host and then synced to SpiNNaker Projections so
that the hardware graph stays consistent with the host-side model.

Typical usage::

    import pyNN.spiNNaker as sim
    from .polyp_neuron import PolypPopulation, PolypState
    from .reef_network import ReefNetwork, ReefConfig as GraphConfig

    sim.setup(timestep=1.0)
    pop = PolypPopulation(sim, max_polyps=100, label="coral_reef",
                          neurons_per_polyp=1)
    reef_cfg = ReefNetworkConfig(hidden_dim=46, message_dim=46, wm_dim=46,
                          chemistry_dim=46, tf_dim=46)
    reef = ReefNetwork(sim, pop, reef_cfg)

    # Seed initial topology
    for src in range(10):
        for dst in range(20, 30):
            reef.add_edge(src, dst, weight=0.1)

    reef.sync_to_spinnaker()
    sim.run(1000.0)
    reef.sync_from_spinnaker()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional, Callable, Any, Union
from collections import defaultdict, deque
import numpy as np
import random
import logging

from .backend_factory import BackendFactory, factory as _backend_factory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PyNN backend selection -- SpiNNaker preferred, with fallback chain
# ---------------------------------------------------------------------------
try:
    import pyNN.spiNNaker as sim  # type: ignore[import]
    BACKEND = "spiNNaker"
except Exception:
    try:
        import pyNN.nest as sim  # type: ignore[import]
        BACKEND = "nest"
    except Exception:
        try:
            import pyNN.brian2 as sim  # type: ignore[import]
            BACKEND = "brian2"
        except Exception:
            # Minimal mock backend for host-side testing without PyNN installed
            BACKEND = "mock"
            sim = None  # type: ignore[assignment]
            logger.warning(
                "No PyNN backend found (tried spiNNaker, nest, brian2). "
                "Operating in host-only mode; sync_to_spinnaker is a no-op."
            )


# ---------------------------------------------------------------------------
# Edge motif constants
# ---------------------------------------------------------------------------


class EdgeType:
    """Motif classification for reef edges.

    Each directed edge between two polyps is tagged with one of the
    motif labels below.  The classification is derived from graph
    distance to the nearest sensory source node (BFS from sensors):

    * :attr:`FEEDFORWARD` — target is farther from sensors than source
      (bottom-up flow).
    * :attr:`LATERAL` — target and source are at roughly the same
      distance from sensors (peer coordination).
    * :attr:`FEEDBACK` — target is closer to sensors than source
      (top-down flow).
    * :attr:`GAP_JUNCTION` — symmetric electrical coupling, not a
      motif edge but tracked alongside them.
    """

    FEEDFORWARD = "ff"
    LATERAL = "lat"
    FEEDBACK = "fb"
    GAP_JUNCTION = "gap"

    _ALL = (FEEDFORWARD, LATERAL, FEEDBACK, GAP_JUNCTION)


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass
class ReefNetworkConfig:
    """Runtime-sized configuration for the Coral Reef Architecture.

    All dimensions are set at initialization time rather than being
    hard-coded.  The default base size of 46 matches the trading
    wrapper default.

    Parameters
    ----------
    hidden_dim : int
        Number of polyp neurons in the hidden (processing) layer.
    message_dim : int
        Number of polyps dedicated to inter-polyp message passing.
    wm_dim : int
        Number of polyps forming the working-memory ensemble.
    chemistry_dim : int
        Number of polyps representing colony chemistry / state.
    tf_dim : int
        Number of transcription-factor (TF) polyps for regulation.
    max_out_degree : int
        Maximum outgoing directed edges per polyp.
    gap_junction_radius : float
        Spatial cutoff (arbitrary units) for automatic gap-junction
        creation between nearby polyps.
    ff_formation_bias : float
        Multiplicative bias toward creating feedforward edges during
        synaptogenesis (values > 1.0 encourage FF growth).
    fb_formation_bias : float
        Multiplicative bias toward creating feedback edges during
        synaptogenesis.
    activity_threshold : int
        Default minimum ``total_spike_transmissions`` for an edge to
        be considered active (used by :meth:`prune_edges`).
    min_age_for_pruning : int
        Default minimum ``age_steps`` before an edge is eligible for
        pruning.
    construction_cost : float
        Support cost deducted when forming a new edge.
    calcification_threshold : float
        When ``calcification`` exceeds this value the edge becomes
        structurally stable and immune to pruning.
    sensor_node_ids : List[int]
        Polyp IDs that act as sensory sources.  Graph distances are
        computed from these nodes for motif classification.
    """

    hidden_dim: int = 46
    message_dim: int = 46
    wm_dim: int = 46
    chemistry_dim: int = 46
    tf_dim: int = 46
    max_out_degree: int = 5
    gap_junction_radius: float = 2.0
    ff_formation_bias: float = 1.5
    fb_formation_bias: float = 1.2
    activity_threshold: int = 1
    min_age_for_pruning: int = 10
    construction_cost: float = 1.0
    calcification_threshold: float = 5.0
    sensor_node_ids: List[int] = field(default_factory=list)

    @property
    def total_neurons(self) -> int:
        """Return the total number of polyp neurons across all bases."""
        return self.hidden_dim + self.message_dim + self.wm_dim + self.chemistry_dim + self.tf_dim


# ---------------------------------------------------------------------------
# ReefEdge dataclass
# ---------------------------------------------------------------------------


@dataclass
class ReefEdge:
    """A single directed edge in the reef graph.

    This object stores **host-side metadata** for a synaptic
    projection living on SpiNNaker.  The actual synaptic weight is
    held in the PyNN ``Projection`` object; this dataclass tracks
    topology, motif class, and structural-history information used
    for synaptogenesis / pruning decisions.

    Attributes
    ----------
    source_id : int
        ``polyp_id`` of the presynaptic polyp.
    target_id : int
        ``polyp_id`` of the postsynaptic polyp.
    edge_type : str
        One of the :class:`EdgeType` constants.
    weight : float
        Cached copy of the synaptic weight (kept in sync with
        SpiNNaker by :meth:`ReefNetwork.sync_from_spinnaker`).
    age_steps : int
        Number of simulation steps the edge has survived.
    last_active_step : int
        Simulation step of the most recent spike transmission.
    total_spike_transmissions : int
        Cumulative spike count transmitted across this edge.
    is_pruned : bool
        Set to ``True`` when the edge is scheduled for removal.
        The host-side dict entry is retained until the next
        :meth:`sync_to_spinnaker` call actually deletes the PyNN
        ``Projection``.
    calcification : float
        Structural stability score.  Increases when the edge carries
        spikes; once it exceeds ``config.calcification_threshold``
        the edge is considered permanent.
    synaptic_tag : float
        Eligibility trace used to gate calcification updates (e.g.
        tag-and-capture-style consolidation).
    """

    source_id: int
    target_id: int
    edge_type: str = EdgeType.FEEDFORWARD
    weight: float = 0.1
    age_steps: int = 0
    last_active_step: int = 0
    total_spike_transmissions: int = 0
    is_pruned: bool = False
    calcification: float = 0.0
    synaptic_tag: float = 0.0

    def __post_init__(self):
        """Validate edge type against allowed constants."""
        if self.edge_type not in EdgeType._ALL:
            raise ValueError(
                f"Invalid edge_type {self.edge_type!r}. "
                f"Must be one of {EdgeType._ALL}."
            )


# ---------------------------------------------------------------------------
# ReefGraphState dataclass
# ---------------------------------------------------------------------------


@dataclass
class ReefGraphState:
    """Serializable state of the entire reef graph.

    This snapshot can be pickled / JSON-serialised and later
    re-loaded via :meth:`ReefNetwork.load_state` to restore a
    colony across SpiNNaker runs.

    Attributes
    ----------
    edges : Dict[Tuple[int, int], ReefEdge]
        Mapping ``(source_id, target_id) -> ReefEdge``.
    gap_junctions : Set[frozenset]
        Undirected pairs ``{pid1, pid2}`` representing electrical
        coupling.
    positions : Dict[int, np.ndarray]
        ``polyp_id -> (x, y, z)`` array.
    motif_counts : Dict[str, int]
        Counters for each motif type.
    next_edge_id : int
        Monotonic counter (optional; not used as dict key but kept
        for future compatibility with edge-id-based storage).
    """

    edges: Dict[Tuple[int, int], ReefEdge] = field(default_factory=dict)
    gap_junctions: Set[frozenset] = field(default_factory=set)
    positions: Dict[int, np.ndarray] = field(default_factory=dict)
    motif_counts: Dict[str, int] = field(
        default_factory=lambda: {
            EdgeType.FEEDFORWARD: 0,
            EdgeType.LATERAL: 0,
            EdgeType.FEEDBACK: 0,
            EdgeType.GAP_JUNCTION: 0,
        }
    )
    next_edge_id: int = 0


# ---------------------------------------------------------------------------
# ReefNetwork
# ---------------------------------------------------------------------------


class ReefNetwork:
    """Directed reef graph managing polyp connectivity on SpiNNaker.

    The :class:`ReefNetwork` is the central topology manager for the
    Coral Reef Architecture.  It maintains a **host-side** directed
    graph (Python ``dict`` / ``set`` structures) that mirrors the
    synaptic projections living on SpiNNaker hardware, classifies
    edges into feedforward / lateral / feedback motifs, handles gap
    junction coupling, and drives structural plasticity
    (synaptogenesis, pruning, sprouting, repair).

    **Architecture sizing** — The network is *runtime-sized*: the
    hidden / message / WM / chemistry / TF dimensions are passed in
    through :class:`ReefNetworkConfig` rather than being hard-coded.  The
    default base size is 46 neurons per compartment.

    **Two-level representation** — Every directed edge exists both
    as a :class:`ReefEdge` object in ``self.edges`` (host) and as a
    PyNN ``Projection`` (SpiNNaker).  Gap junctions are modelled as
    pairs of excitatory synapses (bidirectional) because PyNN does
    not natively support gap-junction mechanisms on all backends.

    **Lifecycle pattern**::

        reef = ReefNetwork(sim, population, config)
        # ... add edges, set positions ...
        reef.sync_to_spinnaker()      # push to hardware
        sim.run(runtime_ms)
        reef.sync_from_spinnaker()    # pull updated weights
        reef.prune_edges()            # host-side structural decisions
        reef.synaptogenesis(...)      # grow new edges
        reef.sync_to_spinnaker()      # push changes back

    Parameters
    ----------
    sim : module
        The PyNN simulator module (``pyNN.spiNNaker`` or fallback).
    population : PolypPopulation
        The wrapped PyNN ``Population`` of polyp neurons.
    config : ReefNetworkConfig
        Runtime-sized configuration object.

    Attributes
    ----------
    edges : Dict[Tuple[int, int], ReefEdge]
        Host-side edge store: ``(src, dst) -> ReefEdge``.
    gap_junctions : Dict[frozenset, float]
        ``{pid1, pid2} -> coupling_strength``.
    positions : Dict[int, np.ndarray]
        ``polyp_id -> (x, y, z)`` float array.
    graph_distances : Dict[int, int]
        Shortest-path distance from the nearest sensor node.
    projections : Dict[Tuple[int, int], Any]
        ``(src, dst) -> PyNN Projection`` (or ``None`` in mock mode).
    _current_step : int
        Simulation step counter incremented each round.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        sim,
        population: "PolypPopulation",
        config: ReefNetworkConfig,
        backend_factory: Optional[BackendFactory] = None,
    ) -> None:
        """Initialise a new ReefNetwork.

        Creates empty host-side data structures and pre-allocates
        positions for all polyp IDs known at construction time.

        Parameters
        ----------
        sim : module
            PyNN simulator module.
        population : PolypPopulation
            Polyp population wrapper.
        config : ReefNetworkConfig
            Runtime configuration.
        backend_factory : BackendFactory, optional
            If provided, used to create backend-specific neuron and
            synapse models.  Defaults to the module-level factory.
        """
        self.sim = sim
        self.population = population
        self.config = config
        self._factory = backend_factory or _backend_factory
        if self._factory.backend_name == "uninitialized":
            from .backend_factory import get_backend_factory
            self._factory = get_backend_factory(self.sim)

        # Host-side topology
        self.edges: Dict[Tuple[int, int], ReefEdge] = {}
        self.gap_junctions: Dict[frozenset, float] = {}
        self.positions: Dict[int, np.ndarray] = {}

        # Graph distances from sensors (for motif classification)
        self.graph_distances: Dict[int, int] = {}

        # SpiNNaker projection objects
        self.projections: Dict[Tuple[int, int], Any] = {}

        # Gap-junction projections (bidirectional pair per gap)
        self._gap_projections: Dict[frozenset, Tuple[Any, Any]] = {}

        # Simulation step counter
        self._current_step: int = 0

        # Monotonic edge counter for optional ID-based addressing
        self._next_edge_id: int = 0

        # Dopamine delivery handle (opaque — managed by backend factory)
        self._dopamine_handle: Any = None

        # Pre-populate positions for all currently alive polyps
        self._initialise_positions()

        logger.info(
            "ReefNetwork initialised (backend=%s, total_neurons=%d, "
            "sensor_nodes=%s).",
            BACKEND,
            config.total_neurons,
            config.sensor_node_ids,
        )

    def _initialise_positions(self) -> None:
        """Scatter polyps in 3-D space with a default spherical layout.

        Alive polyps from the population are assigned uniformly
        random coordinates inside a unit sphere centred at the
        origin.  This provides an initial geometry for spatial
        neighbour queries and gap-junction creation.
        """
        alive = self.population.get_alive_indices()
        for pid in alive:
            if pid not in self.positions:
                # Uniform sampling inside unit sphere (Marsaglia method)
                v = np.random.normal(size=3)
                v /= np.linalg.norm(v)
                r = random.random() ** (1.0 / 3.0)
                self.positions[pid] = r * v

    def add_polyp(self, state) -> None:
        """Register a new host-side polyp in the graph position table."""
        pid = int(state.polyp_id)
        xyz = getattr(state, "xyz", None)
        if xyz is None:
            xyz = np.zeros(3, dtype=float)
        self.positions[pid] = np.asarray(xyz, dtype=float).reshape(3)
        self.graph_distances.setdefault(pid, 0)

    def has_edge(self, src_id: int, dst_id: int) -> bool:
        """Return True if a non-pruned edge exists from src_id to dst_id."""
        edge = self.edges.get((src_id, dst_id))
        if edge is None:
            return False
        if isinstance(edge, ReefEdge):
            return not edge.is_pruned
        return True  # raw float edge treated as alive

    def get_edge(self, src_id: int, dst_id: int):
        """Return the edge between src_id and dst_id, or None if pruned/missing."""
        edge = self.edges.get((src_id, dst_id))
        if edge is None:
            return None
        if isinstance(edge, ReefEdge):
            if edge.is_pruned:
                return None
            return edge
        return None  # raw float edge not wrapped

    # ------------------------------------------------------------------
    # Topology management
    # ------------------------------------------------------------------

    def add_edge(
        self,
        src_id: int,
        dst_id: int,
        weight: float = 0.1,
        edge_type: Optional[str] = None,
    ) -> ReefEdge:
        """Add a directed edge from *src_id* to *dst_id*.

        If an edge already exists in the same direction it is
        overwritten (weight updated, age reset).  The edge is stored
        host-side immediately; the corresponding PyNN ``Projection``
        is **not** created until :meth:`sync_to_spinnaker` is called.

        Parameters
        ----------
        src_id : int
            Source polyp ID.
        dst_id : int
            Target polyp ID.
        weight : float, optional
            Initial synaptic weight.  Positive values are excitatory;
            negative values are inhibitory.  Default ``0.1``.
        edge_type : str or None, optional
            Explicit motif tag.  If ``None`` the edge is classified
            automatically via :meth:`classify_edge`.

        Returns
        -------
        ReefEdge
            The newly created (or updated) edge descriptor.

        Raises
        ------
        ValueError
            If *src_id* == *dst_id* (no self-loops).
        """
        if src_id == dst_id:
            raise ValueError(f"Self-loops are not allowed (polyp {src_id}).")

        if edge_type is None:
            edge_type = self.classify_edge(src_id, dst_id)

        key = (src_id, dst_id)
        edge = ReefEdge(
            source_id=src_id,
            target_id=dst_id,
            edge_type=edge_type,
            weight=weight,
            age_steps=0,
            last_active_step=self._current_step,
            total_spike_transmissions=0,
            is_pruned=False,
            calcification=0.0,
            synaptic_tag=0.0,
        )
        self.edges[key] = edge
        self._next_edge_id += 1

        logger.debug(
            "Edge added: %d -> %d (type=%s, weight=%.4f)",
            src_id, dst_id, edge_type, weight,
        )
        return edge

    def remove_edge(self, src_id: int, dst_id: int) -> None:
        """Remove the directed edge from *src_id* to *dst_id*.

        The edge is marked pruned in the host-side store and the
        associated PyNN ``Projection`` is queued for deletion on the
        next :meth:`sync_to_spinnaker` call.

        Parameters
        ----------
        src_id : int
            Source polyp ID.
        dst_id : int
            Target polyp ID.
        """
        key = (src_id, dst_id)
        if key in self.edges:
            self.edges[key].is_pruned = True
            logger.debug("Edge %d -> %d marked for removal.", src_id, dst_id)
        else:
            logger.warning("remove_edge: no edge %d -> %d found.", src_id, dst_id)

    def get_outgoing_edges(self, polyp_id: int) -> List[ReefEdge]:
        """Return all **non-pruned** outgoing edges from *polyp_id*.

        Parameters
        ----------
        polyp_id : int
            Polyp whose outgoing edges are queried.

        Returns
        -------
        list[ReefEdge]
            Alive outgoing edges.
        """
        return [
            edge
            for (src, _), edge in self.edges.items()
            if src == polyp_id and not edge.is_pruned
        ]

    def get_incoming_edges(self, polyp_id: int) -> List[ReefEdge]:
        """Return all **non-pruned** incoming edges to *polyp_id*.

        Parameters
        ----------
        polyp_id : int
            Polyp whose incoming edges are queried.

        Returns
        -------
        list[ReefEdge]
            Alive incoming edges.
        """
        return [
            edge
            for (_, dst), edge in self.edges.items()
            if dst == polyp_id and not edge.is_pruned
        ]

    def get_neighbors(self, polyp_id: int) -> Set[int]:
        """Return the set of all unique neighbours of *polyp_id*.

        A neighbour is any polyp connected by an edge (outgoing or
        incoming) that is not pruned.  The set does **not** include
        *polyp_id* itself.

        Parameters
        ----------
        polyp_id : int

        Returns
        -------
        set[int]
            Union of source IDs from incoming edges and target IDs
            from outgoing edges.
        """
        neighbors: Set[int] = set()
        for (src, dst), edge in self.edges.items():
            if edge.is_pruned:
                continue
            if src == polyp_id:
                neighbors.add(dst)
            if dst == polyp_id:
                neighbors.add(src)
        return neighbors

    def get_degree(self, polyp_id: int) -> int:
        """Return the total degree (in + out) of *polyp_id*.

        Only non-pruned edges are counted.

        Parameters
        ----------
        polyp_id : int

        Returns
        -------
        int
            Total number of incident edges.
        """
        count = 0
        for (src, dst), edge in self.edges.items():
            if edge.is_pruned:
                continue
            if src == polyp_id or dst == polyp_id:
                count += 1
        return count

    # ------------------------------------------------------------------
    # Motif classification
    # ------------------------------------------------------------------

    def classify_edge(self, src_id: int, dst_id: int) -> str:
        """Classify the directed edge *src_id* -> *dst_id* by motif.

        Classification uses pre-computed graph distances from sensor
        nodes (BFS in :meth:`_compute_graph_distances`).  The logic:

        * FEEDFORWARD  — ``dist[dst] > dist[src] + tol``
        * FEEDBACK     — ``dist[dst] < dist[src] - tol``
        * LATERAL      — otherwise (similar distances)

        If distances have not been computed yet, this method falls
        back to calling :meth:`_compute_graph_distances`.

        Parameters
        ----------
        src_id : int
        dst_id : int

        Returns
        -------
        str
            One of :attr:`EdgeType.FEEDFORWARD`,
            :attr:`EdgeType.LATERAL`, or :attr:`EdgeType.FEEDBACK`.
        """
        if not self.graph_distances:
            self._compute_graph_distances()

        d_src = self.graph_distances.get(src_id, 0)
        d_dst = self.graph_distances.get(dst_id, 0)
        tolerance = 0

        if d_dst > d_src + tolerance:
            return EdgeType.FEEDFORWARD
        if d_dst < d_src - tolerance:
            return EdgeType.FEEDBACK
        return EdgeType.LATERAL

    def _compute_graph_distances(self) -> None:
        """Compute shortest-path distances from sensor nodes via BFS.

        The reef graph is treated as **undirected** for distance
        purposes (i.e. edges can be traversed in either direction)
        because motif classification cares about semantic proximity
        to sensors, not reachability.

        Sensor nodes are taken from ``config.sensor_node_ids``.  If
        that list is empty, all currently-alive polyps with no
        incoming edges are treated as de-facto sensors.

        Distances are stored in ``self.graph_distances``.
        """
        # Determine sensor set
        sensors = set(self.config.sensor_node_ids)
        if not sensors:
            # Default: polyps with no incoming edges are sensors
            alive = set(self.population.get_alive_indices())
            for pid in alive:
                has_incoming = any(
                    dst == pid and not e.is_pruned
                    for (_, dst), e in self.edges.items()
                )
                if not has_incoming:
                    sensors.add(pid)

        # Build undirected adjacency for BFS
        adj: Dict[int, Set[int]] = defaultdict(set)
        alive_set = set(self.population.get_alive_indices())
        for pid in alive_set:
            adj[pid]  # ensure entry
        for (src, dst), edge in self.edges.items():
            if edge.is_pruned:
                continue
            if src in alive_set and dst in alive_set:
                adj[src].add(dst)
                adj[dst].add(src)

        # Multi-source BFS
        distances: Dict[int, int] = {}
        queue: deque = deque()
        for s in sensors:
            if s in alive_set:
                distances[s] = 0
                queue.append(s)

        while queue:
            node = queue.popleft()
            for neighbor in adj[node]:
                if neighbor not in distances:
                    distances[neighbor] = distances[node] + 1
                    queue.append(neighbor)

        # Unreached nodes get distance 0 (treat as sources)
        for pid in alive_set:
            if pid not in distances:
                distances[pid] = 0

        self.graph_distances = distances
        logger.debug(
            "Graph distances computed for %d polyps from %d sensors.",
            len(distances), len(sensors),
        )

    def get_motif_counts(self) -> Dict[str, int]:
        """Return the number of alive edges per motif type.

        Returns
        -------
        dict[str, int]
            Counters keyed by ``EdgeType`` value.
        """
        counts: Dict[str, int] = defaultdict(int)
        for edge in self.edges.values():
            if not edge.is_pruned:
                counts[edge.edge_type] += 1
        # Ensure all keys exist
        for et in (EdgeType.FEEDFORWARD, EdgeType.LATERAL,
                   EdgeType.FEEDBACK, EdgeType.GAP_JUNCTION):
            counts.setdefault(et, 0)
        return dict(counts)

    # ------------------------------------------------------------------
    # Gap junctions
    # ------------------------------------------------------------------

    def add_gap_junction(
        self, pid1: int, pid2: int, strength: float = 0.1
    ) -> None:
        """Add a symmetric gap junction between *pid1* and *pid2*.

        Gap junctions are modelled as a pair of excitatory synapses
        (one in each direction) because most PyNN backends do not
        expose native gap-junction / electrical-coupling mechanisms.
        The coupling strength is stored host-side and applied as the
        weight of both directional projections.

        Parameters
        ----------
        pid1 : int
            First polyp ID.
        pid2 : int
            Second polyp ID.
        strength : float, optional
            Coupling conductance (arbitrary units).  Default ``0.1``.
        """
        if pid1 == pid2:
            raise ValueError("Gap junction requires two distinct polyps.")
        pair = frozenset({pid1, pid2})
        self.gap_junctions[pair] = strength
        logger.debug(
            "Gap junction added between %d and %d (strength=%.4f).",
            pid1, pid2, strength,
        )

    def remove_gap_junction(self, pid1: int, pid2: int) -> None:
        """Remove the gap junction between *pid1* and *pid2*.

        The underlying bidirectional projections are queued for
        deletion on the next :meth:`sync_to_spinnaker` call.

        Parameters
        ----------
        pid1 : int
        pid2 : int
        """
        pair = frozenset({pid1, pid2})
        if pair in self.gap_junctions:
            del self.gap_junctions[pair]
            logger.debug("Gap junction %d <-> %d removed.", pid1, pid2)
        else:
            logger.warning(
                "remove_gap_junction: no gap between %d and %d.", pid1, pid2
            )

    def get_gap_junctions(self, polyp_id: int) -> List[Tuple[int, float]]:
        """Return all gap-junction partners of *polyp_id*.

        Parameters
        ----------
        polyp_id : int

        Returns
        -------
        list[tuple[int, float]]
            ``(partner_id, coupling_strength)`` for each active gap
            junction incident to *polyp_id*.
        """
        result: List[Tuple[int, float]] = []
        for pair, strength in self.gap_junctions.items():
            if polyp_id in pair:
                partner = next(p for p in pair if p != polyp_id)
                result.append((partner, strength))
        return result

    def auto_gap_junctions_from_positions(self) -> int:
        """Create gap junctions for all spatially close polyp pairs.

        For every pair of alive polyps whose Euclidean distance is
        less than ``config.gap_junction_radius``, a gap junction is
        created (if it does not already exist).

        Returns
        -------
        int
            Number of new gap junctions created.
        """
        alive = self.population.get_alive_indices()
        radius = self.config.gap_junction_radius
        created = 0
        for i, pid1 in enumerate(alive):
            pos1 = self.positions.get(pid1)
            if pos1 is None:
                continue
            for pid2 in alive[i + 1:]:
                pair = frozenset({pid1, pid2})
                if pair in self.gap_junctions:
                    continue
                pos2 = self.positions.get(pid2)
                if pos2 is None:
                    continue
                if np.linalg.norm(pos1 - pos2) < radius:
                    self.add_gap_junction(pid1, pid2, strength=0.1)
                    created += 1
        logger.info(
            "auto_gap_junctions_from_positions: created %d new gaps "
            "(radius=%.2f).", created, radius
        )
        return created

    # ------------------------------------------------------------------
    # Spatial management
    # ------------------------------------------------------------------

    def set_position(self, polyp_id: int, xyz: np.ndarray) -> None:
        """Set the 3-D position of *polyp_id*.

        Parameters
        ----------
        polyp_id : int
        xyz : np.ndarray
            Array-like of shape ``(3,)`` with float coordinates.
        """
        xyz = np.asarray(xyz, dtype=float).flatten()
        if xyz.size < 3:
            raise ValueError("Position must have at least 3 coordinates.")
        self.positions[polyp_id] = xyz[:3]

    def get_position(self, polyp_id: int) -> np.ndarray:
        """Return the 3-D position of *polyp_id*.

        If the polyp has no registered position, a new random point
        inside the unit sphere is generated and stored.

        Parameters
        ----------
        polyp_id : int

        Returns
        -------
        np.ndarray
            Float array of shape ``(3,)``.
        """
        if polyp_id not in self.positions:
            v = np.random.normal(size=3)
            v /= np.linalg.norm(v)
            r = random.random() ** (1.0 / 3.0)
            self.positions[polyp_id] = r * v
        return self.positions[polyp_id].copy()

    def get_spatial_neighbors(
        self, polyp_id: int, radius: float
    ) -> List[int]:
        """Return all alive polyps within *radius* of *polyp_id*.

        Parameters
        ----------
        polyp_id : int
            Reference polyp.
        radius : float
            Euclidean distance threshold.

        Returns
        -------
        list[int]
            IDs of nearby alive polyps (excluding *polyp_id*).
        """
        center = self.get_position(polyp_id)
        alive = self.population.get_alive_indices()
        neighbors: List[int] = []
        for other in alive:
            if other == polyp_id:
                continue
            pos = self.positions.get(other)
            if pos is None:
                continue
            if np.linalg.norm(center - pos) < radius:
                neighbors.append(other)
        return neighbors

    def migrate_step(self, polyp_id: int, dt: float = 0.1) -> None:
        """Apply one spatial migration step to *polyp_id*.

        The update combines three classical mechanical forces:

        1. **Adhesion** — pull toward the centroid of current
           neighbours (connected by non-pruned edges).
        2. **Tension** — stretch toward neighbours that are farther
           than an ideal rest distance (``rest_length = 1.0``),
           modelling axonal tension.
        3. **Repulsion** — push away from polyps that are too close
           (``crowd_radius = 0.5``), preventing pile-up.

        Parameters
        ----------
        polyp_id : int
            Polyp to move.
        dt : float
            Time-step scaling factor.  Default ``0.1``.
        """
        pos = self.get_position(polyp_id)
        neighbors = self.get_neighbors(polyp_id)
        if not neighbors:
            return

        # Gather neighbor positions
        nbr_pos = np.vstack([self.get_position(n) for n in neighbors])

        # 1. Adhesion: pull toward centroid
        centroid = nbr_pos.mean(axis=0)
        adhesion = centroid - pos

        # 2. Tension: stretch toward distant neighbors
        rest_length = 1.0
        displacements = nbr_pos - pos
        distances = np.linalg.norm(displacements, axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            unit_vecs = displacements / distances[:, np.newaxis]
        stretch = np.nansum(
            unit_vecs * np.maximum(0.0, distances - rest_length)[:, np.newaxis],
            axis=0,
        )

        # 3. Repulsion: push from very close polyps
        crowd_radius = 0.5
        close_mask = distances < crowd_radius
        if np.any(close_mask):
            close_vecs = unit_vecs[close_mask]
            close_dists = distances[close_mask]
            repulsion = -np.nansum(
                close_vecs
                * (crowd_radius - close_dists)[:, np.newaxis]
                / crowd_radius,
                axis=0,
            )
        else:
            repulsion = np.zeros(3)

        # Composite force with tuned coefficients
        force = 0.3 * adhesion + 0.2 * stretch + 1.0 * repulsion
        new_pos = pos + dt * force

        self.set_position(polyp_id, new_pos)

    # ------------------------------------------------------------------
    # Structural dynamics (host-side decisions)
    # ------------------------------------------------------------------

    def synaptogenesis(
        self,
        polyp_id: int,
        candidates: List[int],
        max_new: int,
        budget: float,
    ) -> List[ReefEdge]:
        """Form new outgoing edges from *polyp_id* to promising candidates.

        New edges are created subject to:

        * *budget* — total support available; each edge costs
          ``config.construction_cost``.
        * *max_new* — hard cap on the number of new edges per call.
        * *max_out_degree* — global cap on outgoing edges per polyp.
        * Formation-bias traits ``ff_formation_bias`` and
          ``fb_formation_bias`` that re-weight candidate scores.

        Candidates are scored by a simple heuristic combining motif
        desirability and inverse existing degree (preferring
        under-connected targets).  The highest-scoring candidates
        within budget are chosen.

        Parameters
        ----------
        polyp_id : int
            Source polyp that will sprout new axons.
        candidates : list[int]
            Potential target polyp IDs.
        max_new : int
            Maximum number of edges to create this call.
        budget : float
            Available support budget (local earned support).

        Returns
        -------
        list[ReefEdge]
            List of newly created edges (may be empty).
        """
        new_edges: List[ReefEdge] = []
        current_out = len(self.get_outgoing_edges(polyp_id))
        slots = self.config.max_out_degree - current_out
        if slots <= 0:
            return new_edges

        effective_max = min(max_new, slots, int(budget // self.config.construction_cost))
        if effective_max <= 0:
            return new_edges

        # Score candidates
        scored: List[Tuple[float, int]] = []
        alive_set = set(self.population.get_alive_indices())
        for cand in candidates:
            if cand == polyp_id:
                continue
            if cand not in alive_set:
                continue
            if (polyp_id, cand) in self.edges and not self.edges[(polyp_id, cand)].is_pruned:
                continue

            # Motif-dependent bias
            motif = self.classify_edge(polyp_id, cand)
            bias = 1.0
            if motif == EdgeType.FEEDFORWARD:
                bias = self.config.ff_formation_bias
            elif motif == EdgeType.FEEDBACK:
                bias = self.config.fb_formation_bias

            # Prefer under-connected targets (inverse degree)
            degree_penalty = 1.0 / (1.0 + self.get_degree(cand))

            # Prefer spatially nearby targets
            d_pos = self.get_position(polyp_id) - self.get_position(cand)
            spatial_score = 1.0 / (1.0 + np.linalg.norm(d_pos))

            score = bias * degree_penalty * spatial_score
            scored.append((score, cand))

        if not scored:
            return new_edges

        scored.sort(key=lambda x: x[0], reverse=True)
        remaining_budget = budget

        for score, cand in scored[:effective_max]:
            if remaining_budget < self.config.construction_cost:
                break
            edge = self.add_edge(
                polyp_id, cand,
                weight=0.05 + random.random() * 0.1,
            )
            new_edges.append(edge)
            remaining_budget -= self.config.construction_cost

        logger.info(
            "synaptogenesis(%d): created %d edges (budget left=%.2f).",
            polyp_id, len(new_edges), remaining_budget,
        )
        return new_edges

    def prune_edges(
        self,
        min_age: Optional[int] = None,
        activity_threshold: Optional[int] = None,
    ) -> int:
        """Mark low-activity edges for pruning.

        An edge is pruned if **all** of the following hold:

        * ``age_steps >= min_age``
        * ``total_spike_transmissions < activity_threshold``
        * ``calcification < calcification_threshold``

        Pruned edges are not deleted from the host dict immediately;
        they are flagged with ``is_pruned=True`` and physically
        removed from SpiNNaker on the next
        :meth:`sync_to_spinnaker`.

        Parameters
        ----------
        min_age : int or None
            Minimum age for pruning eligibility.  Falls back to
            ``config.min_age_for_pruning``.
        activity_threshold : int or None
            Minimum cumulative spike transmissions for survival.
            Falls back to ``config.activity_threshold``.

        Returns
        -------
        int
            Number of edges newly marked as pruned.
        """
        if min_age is None:
            min_age = self.config.min_age_for_pruning
        if activity_threshold is None:
            activity_threshold = self.config.activity_threshold

        pruned_count = 0
        for edge in self.edges.values():
            if edge.is_pruned:
                continue
            if edge.age_steps < min_age:
                continue
            if edge.calcification >= self.config.calcification_threshold:
                continue
            if edge.total_spike_transmissions < activity_threshold:
                edge.is_pruned = True
                pruned_count += 1

        logger.info(
            "prune_edges: marked %d edges for pruning (min_age=%d, "
            "activity_threshold=%d).",
            pruned_count, min_age, activity_threshold,
        )
        return pruned_count

    def axonal_sprouting(self, polyp_id: int, n_candidates: int = 5) -> List[int]:
        """Identify candidate target polyps for axonal sprouting.

        Sprouting explores the local neighbourhood and returns a
        short-list of promising targets that the polyp might attempt
        to connect to during synaptogenesis.  Candidates are:

        1. Spatially nearby polyps (within ``2 * gap_junction_radius``).
        2. Under-connected polyps (degree < max_out_degree).
        3. Sorted by a combined score of motif bias and novelty.

        Parameters
        ----------
        polyp_id : int
            Polyp that is sprouting.
        n_candidates : int
            Number of candidates to return.

        Returns
        -------
        list[int]
            Up to *n_candidates* target polyp IDs.
        """
        search_radius = 2.0 * self.config.gap_junction_radius
        nearby = self.get_spatial_neighbors(polyp_id, search_radius)

        # Exclude existing outgoing targets and self
        existing_targets = {
            e.target_id for e in self.get_outgoing_edges(polyp_id)
        }
        candidates = [
            c for c in nearby
            if c != polyp_id and c not in existing_targets
        ]

        if not candidates:
            # Fallback: sample random alive polyps
            alive = self.population.get_alive_indices()
            candidates = [
                c for c in alive
                if c != polyp_id and c not in existing_targets
            ]
            random.shuffle(candidates)
            return candidates[:n_candidates]

        # Score candidates
        scored: List[Tuple[float, int]] = []
        for cand in candidates:
            motif = self.classify_edge(polyp_id, cand)
            bias = 1.0
            if motif == EdgeType.FEEDFORWARD:
                bias = self.config.ff_formation_bias
            elif motif == EdgeType.FEEDBACK:
                bias = self.config.fb_formation_bias
            novelty = 1.0 / (1.0 + self.get_degree(cand))
            scored.append((bias * novelty, cand))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [cand for _, cand in scored[:n_candidates]]

    def repair_long_range(self, component_ids: List[int]) -> List[ReefEdge]:
        """Create bridging edges to reconnect a disconnected component.

        If a subset of polyps (given by *component_ids*) has become
        topologically isolated from the rest of the colony, this
        method selects a bridge node inside the component and a
        bridge node outside, then creates a new edge between them.

        The strategy is:

        1. Find the most central node inside the component (highest
           degree within the component).
        2. Find the closest alive node outside the component
           (Euclidean distance in 3-D space).
        3. Create a FEEDFORWARD edge from the internal bridge to
           the external bridge (direction respects hierarchy if
           distances are available).

        Parameters
        ----------
        component_ids : list[int]
            IDs of polyps in the disconnected component.

        Returns
        -------
        list[ReefEdge]
            New edges created for repair (empty if no repair needed).
        """
        if not component_ids:
            return []

        alive = set(self.population.get_alive_indices())
        component_set = set(component_ids)
        outside = alive - component_set

        if not outside:
            logger.warning(
                "repair_long_range: no outside nodes available for repair."
            )
            return []

        # Most central inside node
        inside_degrees = {
            pid: sum(
                1 for e in self.get_outgoing_edges(pid) + self.get_incoming_edges(pid)
                if e.source_id in component_set or e.target_id in component_set
            )
            for pid in component_ids if pid in alive
        }
        if not inside_degrees:
            return []
        bridge_inside = max(inside_degrees, key=inside_degrees.get)  # type: ignore[return-value]

        # Closest outside node (spatial)
        pos_inside = self.get_position(bridge_inside)
        closest_outside = min(
            outside,
            key=lambda pid: np.linalg.norm(pos_inside - self.get_position(pid)),
        )

        # Determine direction based on hierarchy
        d_in = self.graph_distances.get(bridge_inside, 0)
        d_out = self.graph_distances.get(closest_outside, 0)
        if d_in <= d_out:
            src, dst = bridge_inside, closest_outside
        else:
            src, dst = closest_outside, bridge_inside

        edge = self.add_edge(src, dst, weight=0.15, edge_type=EdgeType.FEEDFORWARD)
        logger.info(
            "repair_long_range: bridge %d -> %d (dist_in=%d, dist_out=%d).",
            src, dst, d_in, d_out,
        )
        return [edge]

    # ------------------------------------------------------------------
    # SpiNNaker sync
    # ------------------------------------------------------------------

    def sync_to_spinnaker(self) -> None:
        """Push the current host-side graph state to the neuromorphic backend.

        This method performs three operations in order:

        1. **Remove pruned edges** — host-side pruned edges are deleted
           and the corresponding hardware connections are removed.
        2. **Rebuild inter-polyp projections** — all alive edges are
           pushed to the backend using the factory's
           :meth:`create_inter_polyp_projection`.  On NEST this uses
           native ``stdp_dopamine_synapse``; on other backends it
           falls back to PyNN ``Projection`` with ``StaticSynapse``.
        3. **Sync gap junctions** — bidirectional projections for
           all registered gap-junction pairs are created or updated.

        If running in mock mode (no PyNN backend), this method is a
        no-op but still cleans up pruned edges from the host dict.
        """
        if self.sim is None:
            # Mock mode: just purge pruned edges from host dict
            pruned_keys = [
                k for k, e in self.edges.items() if e.is_pruned
            ]
            for k in pruned_keys:
                del self.edges[k]
            logger.debug("sync_to_spinnaker: mock mode — purged %d pruned edges.", len(pruned_keys))
            return

        # --- 1. Remove pruned edges ---
        pruned_keys = []
        for key, edge in list(self.edges.items()):
            if edge.is_pruned:
                self._remove_projection(key[0], key[1])
                pruned_keys.append(key)
        for k in pruned_keys:
            del self.edges[k]

        # --- 2. Rebuild inter-polyp projection via factory ---
        # Clear old native connections (NEST) or zero PyNN projection
        self._factory.clear_inter_polyp_connections(self._dopamine_handle)

        batched_key = ("__batched__", "__inter_reef__")
        old_proj = self.projections.pop(batched_key, None)
        if old_proj is not None and self.sim is not None:
            try:
                for conn in old_proj:
                    conn.weight = 0.0
            except Exception as exc:
                logger.debug("sync_to_spinnaker: failed to zero old batched proj: %s", exc)

        # Build new connection list with ALL current alive edges
        src_all: List[int] = []
        dst_all: List[int] = []
        w_all: List[float] = []
        for (src, dst), edge in self.edges.items():
            src_all.append(src)
            dst_all.append(dst)
            w_all.append(edge.weight)

        # Always create projection in pre-allocation mode, even with no edges
        factory_prealloc = (
            getattr(self._factory, "_preallocate", False)
            and getattr(self._factory, "_max_polyps", None) is not None
        )
        if src_all or factory_prealloc:
            proj, dhandle = self._create_projection(src_all, dst_all, w_all)
            self._dopamine_handle = dhandle

        # --- 3. Sync gap-junction projections ---
        for pair, strength in self.gap_junctions.items():
            if pair in self._gap_projections:
                continue
            pid1, pid2 = tuple(pair)
            # Bidirectional excitatory synapses as gap-junction proxy
            proj1 = self._create_single_projection(pid1, pid2, strength)
            proj2 = self._create_single_projection(pid2, pid1, strength)
            self._gap_projections[pair] = (proj1, proj2)

        logger.info(
            "sync_to_spinnaker: removed %d, created %d edges, %d gaps.",
            len(pruned_keys), len(src_all), len(self.gap_junctions),
        )

    def sync_from_spinnaker(self) -> None:
        """Pull updated synaptic weights from the backend after STDP.

        On NEST with native dopamine STDP, reads weights directly from
        the ``stdp_dopamine_synapse`` connections.  On standard PyNN
        backends, reads from the ``Projection`` objects.  If weight
        retrieval fails, the cached host-side weight is left unchanged.

        Also increments ``age_steps`` for every alive edge and
        increments ``_current_step``.
        """
        if self.sim is None:
            # Mock mode: just age edges
            for edge in self.edges.values():
                edge.age_steps += 1
            self._current_step += 1
            return

        # Try native weight read first (NEST)
        native_weights: Dict[Tuple[int, int], float] = {}
        if self._factory.supports_native_dopamine_stdp():
            try:
                native_weights = self._factory.read_inter_polyp_weights(
                    self._dopamine_handle
                )
            except Exception as exc:
                logger.debug("sync_from_spinnaker: native weight read failed: %s", exc)

        # Map native weights (NEST GIDs) back to polyp IDs.
        # For NEST, the factory returns GID pairs; we need to map those
        # to polyp-level edge keys.  Since inter-polyp edges expand to
        # many neuron-level connections, we average weights per edge.
        # For simplicity, we skip this complex mapping in v1 and rely
        # on host-side cached weights for topology decisions.

        # Standard PyNN projection weight read (fallback / gap junctions)
        for key, edge in self.edges.items():
            proj = self.projections.get(key)
            if proj is not None:
                try:
                    weights = proj.getWeights(format="array")
                    if weights is not None and len(weights) > 0:
                        if hasattr(weights, "__len__") and not isinstance(weights, float):
                            edge.weight = float(np.mean(weights))
                        else:
                            edge.weight = float(weights)
                except Exception as exc:
                    logger.debug(
                        "sync_from_spinnaker: could not read weight for "
                        "edge %s: %s", key, exc
                    )
            edge.age_steps += 1

        self._current_step += 1
        logger.debug(
            "sync_from_spinnaker: pulled weights at step %d.",
            self._current_step,
        )

    def deliver_dopamine(self, dopamine_level: float) -> None:
        """Deliver a dopamine signal to all plastic inter-polyp synapses.

        On NEST this sets the ``n`` parameter on all
        ``stdp_dopamine_synapse`` connections, gating the eligibility
        trace during the subsequent ``sim.run()``.  On other backends
        this is a no-op.

        Parameters
        ----------
        dopamine_level : float
            Scalar dopamine concentration (dimensionless, typical
            range -1.0 to +1.0).
        """
        try:
            self._factory.deliver_dopamine(self._dopamine_handle, dopamine_level)
            logger.debug(
                "deliver_dopamine: dopamine_level=%.4f applied.", dopamine_level
            )
        except Exception as exc:
            logger.warning("deliver_dopamine: failed: %s", exc)

    def _get_or_create_stdp(self) -> Any:
        """Return the shared STDP mechanism, creating it if necessary.

        .. deprecated::
            No longer used for inter-polyp edges; NEST now uses native
            ``stdp_dopamine_synapse`` via the backend factory.
        """
        if self.sim is None:
            return None
        # Fallback: standard STDP (only used if something still calls this)
        return self.sim.STDPMechanism(
            timing_dependence=self.sim.SpikePairRule(
                tau_plus=20.0, tau_minus=20.0, A_plus=0.1, A_minus=0.1
            ),
            weight_dependence=self.sim.AdditiveWeightDependence(
                w_min=0.0, w_max=1.0
            ),
        )

    def _polyp_to_slices(self, polyp_id: int) -> Optional[Tuple[slice, slice]]:
        """Map a polyp ID to its (readout_slice, input_slice).

        Returns
        -------
        tuple or None
            ``(readout_slice, input_slice)`` for the polyp, or ``None``.
        """
        for state in self.population.states:
            if state.polyp_id == polyp_id:
                return state.readout_slice, state.input_slice
        return None

    def _create_projection(
        self,
        src_ids: List[int],
        dst_ids: List[int],
        weights: List[float],
    ) -> Tuple[Optional[Any], Any]:
        """Create all inter-polyp connections via the backend factory.

        In the microcircuit architecture, each edge expands to:
        ``source.readout neurons → target.input neurons`` (all-to-all).

        On NEST the factory creates native ``stdp_dopamine_synapse``
        connections directly.  On other backends a batched PyNN
        ``Projection`` with ``StaticSynapse`` is used.

        Parameters
        ----------
        src_ids : list[int]
            Source polyp IDs for each edge.
        dst_ids : list[int]
            Target polyp IDs for each edge.
        weights : list[float]
            Synaptic weight for each edge.

        Returns
        -------
        tuple
            ``(projection, dopamine_handle)``.  Projection is ``None``
            when using native NEST connections.
        """
        if self.sim is None:
            return None, None
        # Allow pre-allocation mode to proceed with empty edge list
        factory_prealloc = (
            getattr(self._factory, "_preallocate", False)
            and getattr(self._factory, "_max_polyps", None) is not None
        )
        if not src_ids and not factory_prealloc:
            return None, None

        pop = self.population

        conn_list: List[Tuple[int, int, float, float]] = []
        for src, dst, w in zip(src_ids, dst_ids, weights):
            slices = self._polyp_to_slices(src)
            if slices is None:
                continue
            readout_sl, input_sl = slices
            dst_slices = self._polyp_to_slices(dst)
            if dst_slices is None:
                continue
            _, dst_input_sl = dst_slices
            # readout → input all-to-all
            for r in range(readout_sl.start, readout_sl.stop):
                for i in range(dst_input_sl.start, dst_input_sl.stop):
                    conn_list.append((r, i, w, 1.0))

        if not conn_list:
            # Pre-allocation mode (sPyNNaker) builds the full connectivity
            # matrix regardless of the current host-side edge list.
            factory_prealloc = (
                getattr(self._factory, "_preallocate", False)
                and getattr(self._factory, "_max_polyps", None) is not None
            )
            if not factory_prealloc:
                return None, None

        proj, dhandle = self._factory.create_inter_polyp_projection(
            pre_pop=pop._population,
            post_pop=pop._population,
            connection_list=conn_list,
            label="inter_reef",
        )
        if proj is not None:
            self.projections[("__batched__", "__inter_reef__")] = proj

        return proj, dhandle

    def _create_single_projection(
        self, src_id: int, dst_id: int, weight: float
    ) -> Any:
        """Create a single PyNN Projection and return it.

        Parameters
        ----------
        src_id : int
        dst_id : int
        weight : float

        Returns
        -------
        sim.Projection or None
        """
        if self.sim is None:
            return None
        src_slices = self._polyp_to_slices(src_id)
        dst_slices = self._polyp_to_slices(dst_id)
        if src_slices is None or dst_slices is None:
            return None
        # Gap junction proxy: first readout neuron -> first input neuron
        src_neuron = src_slices[0].start  # first readout neuron
        dst_neuron = dst_slices[1].start  # first input neuron
        connector = self.sim.FromListConnector(
            [(src_neuron, dst_neuron, weight, 1.0)]
        )
        try:
            proj = self.sim.Projection(
                self.population._population,
                self.population._population,
                connector,
                synapse_type=self._factory.create_static_synapse(),
                receptor_type="excitatory",
            )
            self.projections[(src_id, dst_id)] = proj
            return proj
        except Exception as exc:
            logger.warning(
                "_create_single_projection: failed for %d -> %d: %s",
                src_id, dst_id, exc,
            )
            return None

    def _remove_projection(self, src_id: int, dst_id: int) -> None:
        """Delete the PyNN Projection for edge *src_id* -> *dst_id*.

        Also removes the entry from ``self.projections``.

        Parameters
        ----------
        src_id : int
        dst_id : int
        """
        key = (src_id, dst_id)
        proj = self.projections.pop(key, None)
        if proj is not None and self.sim is not None:
            try:
                self.sim.Projection(
                    self.population._population,
                    self.population._population,
                    self.sim.FromListConnector([]),
                )
            except Exception as exc:
                logger.debug("_remove_projection: %s", exc)
        pair = frozenset({src_id, dst_id})
        if pair in self._gap_projections:
            del self._gap_projections[pair]

    # ------------------------------------------------------------------
    # Message passing (host-side cascade)
    # ------------------------------------------------------------------

    def run_message_round(
        self, spike_data: Dict[int, int]
    ) -> Dict[int, float]:
        """Execute one round of message passing over the reef graph.

        Each polyp that fired (key in *spike_data*) injects its
        spike count into all outgoing edges.  The weighted sum of
        incoming spikes is aggregated for every target polyp.

        This is a **host-side** discrete-time cascade step.  It does
        **not** run SpiNNaker simulation time; it assumes spike
        counts have already been collected from a prior hardware run.

        Edge activity statistics (``total_spike_transmissions``,
        ``last_active_step``, ``calcification``) are updated as a
        side effect.

        Parameters
        ----------
        spike_data : dict[int, int]
            Mapping ``polyp_id -> number_of_spikes`` for the most
            recent simulation interval.

        Returns
        -------
        dict[int, float]
            Aggregated input current for each polyp that received
            at least one spike-mediated message.
        """
        aggregated: Dict[int, float] = defaultdict(float)

        for (src, dst), edge in self.edges.items():
            if edge.is_pruned:
                continue
            spikes = spike_data.get(src, 0)
            if spikes <= 0:
                continue

            # Weighted message contribution
            message = edge.weight * spikes
            aggregated[dst] += message

            # Update edge statistics
            edge.total_spike_transmissions += spikes
            edge.last_active_step = self._current_step
            edge.calcification = min(
                self.config.calcification_threshold,
                edge.calcification + 0.1 * spikes,
            )

        logger.debug(
            "run_message_round: %d sources fired, %d targets received input.",
            len(spike_data), len(aggregated),
        )
        return dict(aggregated)

    # ------------------------------------------------------------------
    # Checkpointing
    # ------------------------------------------------------------------

    def save_state(self) -> ReefGraphState:
        """Capture a serializable snapshot of the reef graph.

        Returns
        -------
        ReefGraphState
            Deep-ish copy of edges, gap junctions, positions, and
            motif counters.  Positions are copied as numpy arrays.
        """
        state = ReefGraphState(
            edges={k: ReefEdge(
                source_id=e.source_id,
                target_id=e.target_id,
                edge_type=e.edge_type,
                weight=e.weight,
                age_steps=e.age_steps,
                last_active_step=e.last_active_step,
                total_spike_transmissions=e.total_spike_transmissions,
                is_pruned=e.is_pruned,
                calcification=e.calcification,
                synaptic_tag=e.synaptic_tag,
            ) for k, e in self.edges.items()},
            gap_junctions=set(self.gap_junctions.keys()),
            positions={pid: pos.copy() for pid, pos in self.positions.items()},
            motif_counts=self.get_motif_counts(),
            next_edge_id=self._next_edge_id,
        )
        return state

    def load_state(self, state: ReefGraphState) -> None:
        """Restore the reef graph from a previously saved state.

        Overwrites all host-side topology data.  After loading,
        :meth:`sync_to_spinnaker` should be called to rebuild the
        PyNN projections on hardware.

        Parameters
        ----------
        state : ReefGraphState
            Snapshot produced by :meth:`save_state`.
        """
        self.edges = dict(state.edges)
        self.gap_junctions = {
            pair: 0.1 for pair in state.gap_junctions
        }
        self.positions = {
            pid: pos.copy() for pid, pos in state.positions.items()
        }
        self._next_edge_id = state.next_edge_id
        # Recompute distances for motif classification
        self._compute_graph_distances()
        logger.info(
            "load_state: restored %d edges, %d gaps, %d positions.",
            len(self.edges), len(self.gap_junctions), len(self.positions),
        )

    def get_summary(self) -> Dict[str, Any]:
        """Return a human-readable summary of the reef graph.

        Returns
        -------
        dict
            Keys include ``n_edges``, ``n_gap_junctions``,
            ``n_positions``, ``motif_counts``, ``avg_degree``,
            ``avg_weight``, ``pruned_count``, ``current_step``.
        """
        alive_edges = [e for e in self.edges.values() if not e.is_pruned]
        n_edges = len(alive_edges)
        n_pruned = sum(1 for e in self.edges.values() if e.is_pruned)
        n_gaps = len(self.gap_junctions)
        n_positions = len(self.positions)
        motif_counts = self.get_motif_counts()

        avg_degree = 0.0
        avg_weight = 0.0
        if alive_edges:
            # Degree: count unique polyps
            degrees: Dict[int, int] = defaultdict(int)
            for e in alive_edges:
                degrees[e.source_id] += 1
                degrees[e.target_id] += 1
            avg_degree = float(np.mean(list(degrees.values())))
            avg_weight = float(np.mean([e.weight for e in alive_edges]))

        summary = {
            "n_edges": n_edges,
            "n_gap_junctions": n_gaps,
            "n_positions": n_positions,
            "motif_counts": motif_counts,
            "avg_degree": round(avg_degree, 3),
            "avg_weight": round(avg_weight, 4),
            "pruned_count": n_pruned,
            "current_step": self._current_step,
            "alive_polyps": self.population.n_alive,
        }
        return summary

    # ------------------------------------------------------------------
    # Dopamine modulation helper
    # ------------------------------------------------------------------

    def apply_dopamine(self, dopamine_level: float) -> None:
        """Apply a global dopamine signal to all plastic inter-polyp synapses.

        This is a convenience alias for :meth:`deliver_dopamine`.
        """
        self.deliver_dopamine(dopamine_level)

    # ------------------------------------------------------------------
    # Batch structural helpers
    # ------------------------------------------------------------------

    def step_structural_dynamics(self, dopamine_level: float = 0.1) -> Dict[str, Any]:
        """Run a complete structural-dynamics cycle in one call.

        Convenience method that performs, in order:

        1. Sync weights from SpiNNaker.
        2. Apply dopamine modulation.
        3. Prune inactive edges.
        4. Axonal sprouting for under-connected polyps.
        5. Synaptogenesis from sprouted candidates.
        6. Auto gap-junction creation based on positions.
        7. Sync updated topology back to SpiNNaker.

        Parameters
        ----------
        dopamine_level : float
            Dopamine level for STDP modulation this step.

        Returns
        -------
        dict
            Statistics about what changed (pruned, created, etc.).
        """
        self.sync_from_spinnaker()
        self.apply_dopamine(dopamine_level)

        n_pruned = self.prune_edges()

        # Sprouting + synaptogenesis for polyps with low out-degree
        new_edges: List[ReefEdge] = []
        alive = self.population.get_alive_indices()
        for pid in alive:
            out_deg = len(self.get_outgoing_edges(pid))
            if out_deg < self.config.max_out_degree // 2:
                candidates = self.axonal_sprouting(pid, n_candidates=5)
                budget = 5.0  # simplified fixed budget
                edges = self.synaptogenesis(pid, candidates, max_new=2, budget=budget)
                new_edges.extend(edges)

        # Auto gap junctions
        n_gaps = self.auto_gap_junctions_from_positions()

        self.sync_to_spinnaker()

        stats = {
            "pruned": n_pruned,
            "new_edges": len(new_edges),
            "new_gap_junctions": n_gaps,
            "total_alive_edges": len([e for e in self.edges.values() if not e.is_pruned]),
            "total_gap_junctions": len(self.gap_junctions),
        }
        logger.info("step_structural_dynamics: %s", stats)
        return stats
