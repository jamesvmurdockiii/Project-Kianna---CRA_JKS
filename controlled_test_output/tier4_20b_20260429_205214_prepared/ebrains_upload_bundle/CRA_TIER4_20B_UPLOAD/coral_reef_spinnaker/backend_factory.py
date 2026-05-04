"""Backend-agnostic factory for neuron and synapse models.

This module abstracts away the differences between PyNN backends so that
``polyp_neuron.py`` and ``reef_network.py`` don't hard-code
``sim.IF_curr_exp`` or ``sim.StaticSynapse``.

On **NEST / Brian2 / MockSimulator** we fall back to standard PyNN models.
On **sPyNNaker** we can inject custom C models via the factory hooks.

**NEST Dopamine STDP**

NEST has a native C++ ``stdp_dopamine_synapse`` model that implements
reward-modulated STDP (Izhikevich 2007).  A ``volume_transmitter`` node
delivers the neuromodulatory signal to all synapses using the copied
model.  The host sets the dopamine concentration ``n`` directly on the
synapse connections before each ``sim.run()`` call.

Usage::

    from coral_reef_spinnaker.backend_factory import get_backend_factory
    factory = get_backend_factory(sim)
    cell_type = factory.create_cell_type(tau_m=20.0, v_thresh=-55.0, ...)
    exc_syn = factory.create_excitatory_synapse(weight=0.1)
    inh_syn = factory.create_inhibitory_synapse(weight=-0.1)

    # Inter-polyp projections (dopamine STDP on NEST, static on others)
    proj, dopamine_handle = factory.create_inter_polyp_projection(
        pre_pop, post_pop, connection_list, label="inter_reef"
    )
    factory.deliver_dopamine(dopamine_handle, 0.5)

"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .spinnaker_constraints import clip_weight_for_hardware

logger = logging.getLogger(__name__)


class BackendFactory:
    """Abstract base for backend-specific model creation.

    Subclasses override the creation methods to inject custom C models
    on sPyNNaker while standard PyNN models are used everywhere else.
    """

    def __init__(self, sim: Any) -> None:
        self.sim = sim
        self.backend_name = self._detect_backend(sim)

    @staticmethod
    def _detect_backend(sim: Any) -> str:
        name = getattr(sim, "__name__", sim.__class__.__name__)
        # Normalize aliases
        if "spiNNaker" in name or "spinnaker" in name.lower():
            return "sPyNNaker"
        if "nest" in name.lower():
            return "NEST"
        if "brian" in name.lower():
            return "Brian2"
        if "mock" in name.lower():
            return "MockSimulator"
        return name

    # ------------------------------------------------------------------
    # Neuron models
    # ------------------------------------------------------------------

    def create_cell_type(
        self,
        tau_m: float = 20.0,
        v_rest: float = -65.0,
        v_reset: float = -70.0,
        v_thresh: float = -55.0,
        tau_refrac: float = 2.0,
        tau_syn_E: float = 5.0,
        tau_syn_I: float = 5.0,
        cm: float = 0.25,
        i_offset: float = 0.0,
    ) -> Any:
        """Return a PyNN cell type for the polyp neurons.

        On NEST/Brian2 this is ``IF_curr_exp``.  On sPyNNaker this can
        be replaced with a custom C neuron model (e.g. LIF with trophic
        auxiliary state).
        """
        return self.sim.IF_curr_exp(
            tau_m=tau_m,
            v_rest=v_rest,
            v_reset=v_reset,
            v_thresh=v_thresh,
            tau_refrac=tau_refrac,
            tau_syn_E=tau_syn_E,
            tau_syn_I=tau_syn_I,
            cm=cm,
            i_offset=i_offset,
        )

    # ------------------------------------------------------------------
    # Synapse models (static)
    # ------------------------------------------------------------------

    def create_static_synapse(self, weight: float = 0.0, delay: float = 1.0) -> Any:
        """Return a static synapse with the given weight and delay."""
        return self.sim.StaticSynapse(weight=weight, delay=delay)

    def create_excitatory_synapse(self, weight: float = 0.1, delay: float = 1.0) -> Any:
        """Convenience wrapper for excitatory static synapse."""
        return self.create_static_synapse(weight=weight, delay=delay)

    def create_inhibitory_synapse(self, weight: float = -0.1, delay: float = 1.0) -> Any:
        """Convenience wrapper for inhibitory static synapse.

        sPyNNaker requires negative weights for inhibitory receptors;
        standard PyNN/NEST also respects this convention.
        """
        return self.create_static_synapse(weight=weight, delay=delay)

    # ------------------------------------------------------------------
    # Inter-polyp plastic projections
    # ------------------------------------------------------------------

    def supports_native_dopamine_stdp(self) -> bool:
        """True if the backend has native dopamine-modulated STDP.

        NEST supports this via ``stdp_dopamine_synapse`` and
        ``volume_transmitter``.  All other backends fall back to static
        synapses with host-side weight updates.
        """
        return False

    def create_inter_polyp_projection(
        self,
        pre_pop: Any,
        post_pop: Any,
        connection_list: List[Tuple[int, int, float, float]],
        label: str = "inter_polyp",
    ) -> Tuple[Optional[Any], Any]:
        """Create an inter-polyp projection.

        On NEST this uses the native ``stdp_dopamine_synapse`` if
        :meth:`supports_native_dopamine_stdp` is ``True``.
        On all other backends it falls back to a PyNN ``Projection``
        with ``StaticSynapse``.

        Parameters
        ----------
        pre_pop, post_pop :
            PyNN ``Population`` objects (source and target).
        connection_list :
            List of ``(src_neuron_idx, dst_neuron_idx, weight, delay)``
            tuples.  Indices are *population-level* neuron indices.
        label :
            Human-readable label for the projection.

        Returns
        -------
        tuple
            ``(projection, dopamine_handle)``.  *projection* is a PyNN
            ``Projection`` on standard backends, or ``None`` when NEST
            native connections are used.  *dopamine_handle* is an
            opaque handle passed to :meth:`deliver_dopamine`.
        """
        if not connection_list:
            return None, None

        connector = self.sim.FromListConnector(connection_list)
        proj = self.sim.Projection(
            pre_pop,
            post_pop,
            connector,
            synapse_type=self.create_static_synapse(),
            receptor_type="excitatory",
            label=label,
        )
        return proj, None

    def clear_inter_polyp_connections(self, dopamine_handle: Any) -> None:
        """Remove all inter-polyp connections created by this factory.

        On standard backends this is a no-op because PyNN Projections
        are managed externally.  On NEST this disconnects the native
        ``stdp_dopamine_synapse`` connections.
        """
        pass

    def deliver_dopamine(self, dopamine_handle: Any, level: float) -> None:
        """Deliver a dopamine signal to inter-polyp synapses.

        On NEST this sets the ``n`` parameter on all
        ``stdp_dopamine_synapse`` connections.  On other backends this
        is a no-op.

        Parameters
        ----------
        dopamine_handle :
            Opaque handle returned by :meth:`create_inter_polyp_projection`.
        level :
            Scalar dopamine concentration (dimensionless, typical range
            -1.0 to +1.0).
        """
        pass

    def read_inter_polyp_weights(
        self, dopamine_handle: Any
    ) -> Dict[Tuple[int, int], float]:
        """Read current synaptic weights from hardware.

        Returns a mapping ``(src_neuron_idx, dst_neuron_idx) -> weight``.
        On backends without native dopamine STDP this returns an empty
        dict.
        """
        return {}

    # ------------------------------------------------------------------
    # STDP / plastic synapses (legacy — kept for backward compat)
    # ------------------------------------------------------------------

    def create_stdp_synapse(
        self,
        timing_rule: Optional[Any] = None,
        weight_rule: Optional[Any] = None,
        weight: float = 0.5,
        delay: float = 1.0,
        dopamine_ema: float = 0.0,
        dopamine_scale: float = 1.0,
    ) -> Any:
        """Create a plastic synapse for inter-polyp edges.

        .. deprecated::
            Use :meth:`create_inter_polyp_projection` for inter-polyp
            edges; it automatically selects the correct synapse model.
        """
        if timing_rule is None:
            timing_rule = self.sim.SpikePairRule(
                tau_plus=20.0, tau_minus=20.0, A_plus=0.01, A_minus=0.01
            )
        if weight_rule is None:
            weight_rule = self.sim.AdditiveWeightDependence(w_min=0.0, w_max=1.0)

        return self.sim.STDPMechanism(
            timing_dependence=timing_rule,
            weight_dependence=weight_rule,
            weight=weight,
            delay=delay,
        )

    def create_dopamine_stdpc_mechanism(
        self,
        dopamine_ema: float = 0.0,
        dopamine_scale: float = 1.0,
    ) -> Any:
        """Factory version of ``PolypPopulation.create_dopamine_stdpc_mechanism``.

        .. deprecated::
            Use :meth:`create_inter_polyp_projection` instead.
        """
        a_plus = 0.01
        a_minus = 0.01
        modulation = max(0.3, 1.0 + dopamine_scale * dopamine_ema)
        a_plus_mod = a_plus * modulation
        a_minus_mod = a_minus * modulation

        timing = self.sim.SpikePairRule(
            tau_plus=20.0,
            tau_minus=20.0,
            A_plus=a_plus_mod,
            A_minus=a_minus_mod,
        )
        weight = self.sim.AdditiveWeightDependence(w_min=0.0, w_max=1.0)
        return self.sim.STDPMechanism(
            timing_dependence=timing,
            weight_dependence=weight,
            weight=0.5,
            delay=1.0,
        )

    # ------------------------------------------------------------------
    # Backend capabilities probe
    # ------------------------------------------------------------------

    def supports_dynamic_projections(self) -> bool:
        """True if Projections can be created after ``sim.run()``.

        NEST supports this (with caveats).  sPyNNaker does **not**.
        This flag lets ``ReefNetwork`` decide whether to use
        dynamic topology or pre-allocated static topology.
        """
        return self.backend_name in ("NEST", "Brian2", "MockSimulator")

    def supports_runtime_weight_update(self) -> bool:
        """True if ``projection.setWeights()`` or ``conn.weight = x`` works.

        NEST supports per-connection weight updates.  sPyNNaker does
        not (weights are baked into SDRAM synapse rows).
        """
        return self.backend_name in ("NEST", "Brian2", "MockSimulator")

    def supports_live_spike_packet_gathering(self) -> bool:
        """True if the backend can stream spikes via callbacks/packets.

        sPyNNaker supports this (``LivePacketGather``).  NEST does not
        (spikes are buffered until ``get_data``).
        """
        return self.backend_name == "sPyNNaker"

    def uses_fixed_point(self) -> bool:
        """True if the backend uses fixed-point arithmetic.

        sPyNNaker uses s16.15 fixed point.  NEST/Brian2 use float.
        """
        return self.backend_name == "sPyNNaker"


# ---------------------------------------------------------------------------
# NEST-specific factory with native dopamine STDP
# ---------------------------------------------------------------------------

class NESTFactory(BackendFactory):
    """NEST-specific factory using native ``stdp_dopamine_synapse``.

    Inter-polyp projections are created via direct ``nest.Connect()``
    calls using NEST's built-in reward-modulated STDP.  The host
    controls dopamine delivery by setting the ``n`` parameter on the
    synapse connections before each ``sim.run()``.
    """

    def __init__(self, sim: Any) -> None:
        super().__init__(sim)
        try:
            import nest as _nest
            self._nest = _nest
        except Exception as exc:
            logger.warning("NESTFactory: could not import nest module: %s", exc)
            self._nest = None

        # Model state (initialised lazily)
        self._volume_transmitter: Optional[Any] = None
        self._synapse_model_name: Optional[str] = None
        self._nest_connection_handles: Optional[Any] = None

        # Dopamine STDP parameter defaults
        self.da_a_plus: float = 0.01
        self.da_a_minus: float = 0.01
        self.da_tau_plus: float = 20.0
        self.da_tau_c: float = 1000.0
        self.da_tau_n: float = 200.0
        self.da_w_min: float = 0.0
        self.da_w_max: float = 1.0

    def _ensure_dopamine_model(self) -> None:
        """Lazy initialisation of volume_transmitter and copied synapse model."""
        if self._nest is None:
            return
        if self._synapse_model_name is not None:
            return

        self._volume_transmitter = self._nest.Create("volume_transmitter")
        model_name = "cra_dopamine_stdp"
        self._nest.CopyModel(
            "stdp_dopamine_synapse",
            model_name,
            {
                "A_plus": self.da_a_plus,
                "A_minus": self.da_a_minus,
                "tau_plus": self.da_tau_plus,
                "tau_c": self.da_tau_c,
                "tau_n": self.da_tau_n,
                "Wmin": self.da_w_min,
                "Wmax": self.da_w_max,
                "volume_transmitter": self._volume_transmitter[0],
            },
        )
        self._synapse_model_name = model_name
        logger.info(
            "NESTFactory: initialised dopamine STDP model '%s' with VT=%s",
            model_name,
            self._volume_transmitter.tolist(),
        )

    def supports_native_dopamine_stdp(self) -> bool:
        return self._nest is not None

    def create_inter_polyp_projection(
        self,
        pre_pop: Any,
        post_pop: Any,
        connection_list: List[Tuple[int, int, float, float]],
        label: str = "inter_polyp",
    ) -> Tuple[Optional[Any], Any]:
        """Create inter-polyp connections using NEST native dopamine STDP.

        Uses direct ``nest.Connect()`` calls bypassing PyNN's
        ``Projection`` machinery so that NEST's ``stdp_dopamine_synapse``
        can be used.
        """
        if self._nest is None or not connection_list:
            # Fallback to standard PyNN projection
            return super().create_inter_polyp_projection(
                pre_pop, post_pop, connection_list, label
            )

        self._ensure_dopamine_model()

        # Map PyNN population indices -> NEST GIDs.
        # In PyNN.nest, population.all_cells is a numpy array of NEST GIDs.
        pre_gids = pre_pop.all_cells.tolist()
        post_gids = post_pop.all_cells.tolist()

        # Build NEST connection list
        nest_conns: List[Tuple[int, int, float, float]] = []
        for src_idx, dst_idx, w, d in connection_list:
            if src_idx < len(pre_gids) and dst_idx < len(post_gids):
                nest_conns.append((pre_gids[src_idx], post_gids[dst_idx], float(w), float(d)))

        if not nest_conns:
            return None, self._volume_transmitter

        # Disconnect old connections of the same model (best-effort)
        self.clear_inter_polyp_connections(self._volume_transmitter)

        # Create connections in batches for efficiency
        srcs = [c[0] for c in nest_conns]
        dsts = [c[1] for c in nest_conns]
        weights = [c[2] for c in nest_conns]
        delays = [c[3] for c in nest_conns]

        self._nest.Connect(
            srcs,
            dsts,
            conn_spec="one_to_one",
            syn_spec={
                "synapse_model": self._synapse_model_name,
                "weight": weights,
                "delay": delays,
            },
        )

        # Store connection handles for later dopamine delivery / weight reading
        self._nest_connection_handles = self._nest.GetConnections(
            synapse_model=self._synapse_model_name
        )

        logger.debug(
            "NESTFactory: created %d dopamine STDP connections (model=%s)",
            len(nest_conns),
            self._synapse_model_name,
        )
        return None, self._volume_transmitter

    def clear_inter_polyp_connections(self, dopamine_handle: Any) -> None:
        """Disconnect all native dopamine STDP connections."""
        if self._nest is None or self._synapse_model_name is None:
            return
        try:
            conns = self._nest.GetConnections(synapse_model=self._synapse_model_name)
            if len(conns) > 0:
                self._nest.Disconnect(
                    conns.source(),
                    conns.target(),
                    conn_spec="one_to_one",
                    syn_spec={"synapse_model": self._synapse_model_name},
                )
                logger.debug(
                    "NESTFactory: disconnected %d old dopamine STDP connections", len(conns)
                )
        except Exception as exc:
            logger.debug("NESTFactory: clear_inter_polyp_connections: %s", exc)
        self._nest_connection_handles = None

    def deliver_dopamine(self, dopamine_handle: Any, level: float) -> None:
        """Set dopamine concentration ``n`` on all native STDP connections.

        The ``n`` parameter decays with ``tau_n`` during the subsequent
        ``sim.run()``.  Setting it before each run provides a step-wise
        constant dopamine signal.
        """
        if self._nest is None or self._nest_connection_handles is None:
            return
        try:
            self._nest_connection_handles.set({"n": float(level)})
            logger.debug("NESTFactory: delivered dopamine n=%.4f", level)
        except Exception as exc:
            logger.warning("NESTFactory: deliver_dopamine failed: %s", exc)

    def read_inter_polyp_weights(
        self, dopamine_handle: Any
    ) -> Dict[Tuple[int, int], float]:
        """Read weights from NEST native dopamine STDP connections.

        Returns a mapping of NEST GID pairs -> weight.  The caller
        (ReefNetwork) is responsible for mapping GIDs back to polyp IDs.
        """
        if self._nest is None or self._nest_connection_handles is None:
            return {}
        try:
            conns = self._nest_connection_handles
            srcs = conns.source().tolist()
            dsts = conns.target().tolist()
            weights = conns.get("weight")
            # Handle both scalar and list returns
            if not isinstance(weights, list):
                weights = [weights]
            return {
                (int(s), int(d)): float(w)
                for s, d, w in zip(srcs, dsts, weights)
            }
        except Exception as exc:
            logger.debug("NESTFactory: read_inter_polyp_weights failed: %s", exc)
            return {}


class Brian2Factory(BackendFactory):
    """Brian2-specific factory (standard PyNN models)."""
    pass


class MockSimulatorFactory(BackendFactory):
    """MockSimulator factory (no-op models)."""
    pass


class SpiNNakerFactory(BackendFactory):
    """sPyNNaker factory with built-in Izhikevich neuromodulation STDP.

    sPyNNaker ships with precompiled ``synapses_stdp_izhikevich_neuromodulation*.aplx``
    binaries that implement dopamine-modulated STDP (Izhikevich 2007) in C.
    The host controls dopamine delivery by adjusting the firing rate of a
    ``SpikeSourcePoisson`` population that projects to the target neurons via
    ``extra_models.Neuromodulation`` synapses (``receptor_type='reward'``).

    Because sPyNNaker bakes synapse rows into SDRAM before ``sim.run()``,
    projections are created **once** on the first call to
    :meth:`create_inter_polyp_projection` and cached thereafter.  Topology
    changes after the first ``sim.run()`` are not supported.
    """

    # STDP timing parameters
    _STD_TAU_PLUS: float = 20.0
    _STD_TAU_MINUS: float = 20.0
    _STD_A_PLUS: float = 0.01
    _STD_A_MINUS: float = 0.01

    # Neuromodulation parameters
    _NM_TAU_C: float = 1000.0   # dopamine concentration decay [ms]
    _NM_TAU_D: float = 200.0    # eligibility trace decay [ms]
    _NM_WEIGHT: float = 0.5     # weight of neuromodulation synapse
    _DA_RATE_SCALE: float = 100.0  # Hz per unit dopamine level
    _NM_MAX_TARGETS_PER_SOURCE: int = 128
    # sPyNNaker's neuromodulation implementation rejects a single source row
    # with >255 target synapses. Keep each dopamine source well below that cap.

    def __init__(self, sim: Any) -> None:
        super().__init__(sim)
        self._extra_models = None
        try:
            from spynnaker.pyNN import extra_models as _em
            self._extra_models = _em
        except Exception as exc:
            logger.warning("SpiNNakerFactory: extra_models import failed: %s", exc)

        # Cached projections / populations (created lazily)
        self._stdp_proj: Optional[Any] = None
        self._nm_proj: Optional[Any] = None
        self._dopamine_source: Optional[Any] = None

        # Pre-allocation parameters (set by Organism.initialize)
        self._preallocate: bool = False
        self._max_polyps: Optional[int] = None
        self._n_input: Optional[int] = None
        self._n_exc: Optional[int] = None
        self._n_inh: Optional[int] = None
        self._n_readout: Optional[int] = None
        self._neurons_per_polyp: Optional[int] = None
        self._prealloc_weight: float = 0.01

    def set_topology_params(
        self,
        max_polyps: int,
        n_input: int,
        n_exc: int,
        n_inh: int,
        n_readout: int,
        neurons_per_polyp: int,
        initial_weight: float = 0.01,
    ) -> None:
        """Configure the factory for full pre-allocation mode.

        When called, :meth:`create_inter_polyp_projection` will build a
        static all-to-all connectivity matrix across all ``max_polyps``
        slots instead of using the dynamic ``connection_list``.  This is
        the correct way to run on real SpiNNaker hardware — synapse rows
        are baked into SDRAM once and STDP modifies weights in-place.

        Parameters
        ----------
        max_polyps : int
            Maximum colony size (must match ``PolypPopulation.max_polyps``).
        n_input, n_exc, n_inh, n_readout : int
            Microcircuit subgroup sizes.
        neurons_per_polyp : int
            Total neurons per polyp (must equal ``n_input + n_exc + n_inh + n_readout``).
        initial_weight : float
            Starting weight for every potential connection (typical 0.01).
        """
        self._preallocate = True
        self._max_polyps = max_polyps
        self._n_input = n_input
        self._n_exc = n_exc
        self._n_inh = n_inh
        self._n_readout = n_readout
        self._neurons_per_polyp = neurons_per_polyp
        self._prealloc_weight = initial_weight
        logger.info(
            "SpiNNakerFactory: pre-allocation configured (%d polyps, "
            "%d readout→%d input, weight=%.3f)",
            max_polyps, n_readout, n_input, initial_weight,
        )

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

    def supports_dynamic_projections(self) -> bool:
        return False

    def supports_runtime_weight_update(self) -> bool:
        return False

    def supports_live_spike_packet_gathering(self) -> bool:
        return True

    def uses_fixed_point(self) -> bool:
        return True

    def supports_native_dopamine_stdp(self) -> bool:
        return self._extra_models is not None

    # ------------------------------------------------------------------
    # Inter-polyp projections (STDP + neuromodulation)
    # ------------------------------------------------------------------

    def create_inter_polyp_projection(
        self,
        pre_pop: Any,
        post_pop: Any,
        connection_list: List[Tuple[int, int, float, float]],
        label: str = "inter_polyp",
    ) -> Tuple[Optional[Any], Any]:
        """Create STDP + neuromodulation projections on sPyNNaker.

        The first call creates:
        1. An STDP ``Projection`` from *pre_pop* → *post_pop*.
        2. A ``SpikeSourcePoisson`` dopamine source population.
        3. A ``Neuromodulation`` projection from dopamine source → *post_pop*
           with ``receptor_type='reward'``.

        Subsequent calls return the cached projection and dopamine source
        without creating new hardware objects.

        If :meth:`set_topology_params` has been called, the factory builds
        a **full pre-allocated connectivity matrix** (all readout→input
        pairs across every polyp slot) instead of using the dynamic
        ``connection_list``.  This is the correct mode for real SpiNNaker
        hardware.
        """
        if self._extra_models is None:
            return super().create_inter_polyp_projection(
                pre_pop, post_pop, connection_list, label
            )

        # Idempotent: sPyNNaker cannot add/remove projections after setup
        if self._stdp_proj is not None:
            logger.debug("SpiNNakerFactory: returning cached STDP projection")
            return self._stdp_proj, self._dopamine_source

        # ------------------------------------------------------------------
        # Build connection list
        # ------------------------------------------------------------------
        if self._preallocate and self._max_polyps is not None:
            # Full all-to-all readout→input matrix across all slots
            conn_list: List[Tuple[int, int, float, float]] = []
            npp = self._neurons_per_polyp
            n_in = self._n_input
            n_exc = self._n_exc
            n_inh = self._n_inh
            n_ro = self._n_readout
            ro_offset = n_in + n_exc + n_inh
            w0 = self._prealloc_weight
            for src_polyp in range(self._max_polyps):
                src_base = src_polyp * npp
                for dst_polyp in range(self._max_polyps):
                    dst_base = dst_polyp * npp
                    for src_n in range(ro_offset, ro_offset + n_ro):
                        for dst_n in range(0, n_in):
                            conn_list.append(
                                (
                                    src_base + src_n,
                                    dst_base + dst_n,
                                    clip_weight_for_hardware(w0),
                                    1.0,
                                )
                            )
            logger.info(
                "SpiNNakerFactory: pre-allocating %d connections "
                "(%d polyps × %d readout → %d polyps × %d input)",
                len(conn_list), self._max_polyps, n_ro,
                self._max_polyps, n_in,
            )
        else:
            # Dynamic mode: use the caller's connection list
            if not connection_list:
                return super().create_inter_polyp_projection(
                    pre_pop, post_pop, connection_list, label
                )
            conn_list = connection_list

        # 1. STDP projection ------------------------------------------------
        timing = self.sim.SpikePairRule(
            tau_plus=self._STD_TAU_PLUS,
            tau_minus=self._STD_TAU_MINUS,
            A_plus=self._STD_A_PLUS,
            A_minus=self._STD_A_MINUS,
        )
        weight_dep = self.sim.AdditiveWeightDependence(
            w_min=0.0,
            w_max=clip_weight_for_hardware(1.0),
        )
        stdp = self.sim.STDPMechanism(
            timing_dependence=timing,
            weight_dependence=weight_dep,
            weight=clip_weight_for_hardware(0.1),
            delay=1.0,
        )
        connector = self.sim.FromListConnector(conn_list)
        self._stdp_proj = self.sim.Projection(
            pre_pop,
            post_pop,
            connector,
            synapse_type=stdp,
            receptor_type="excitatory",
            label=label,
        )
        logger.info(
            "SpiNNakerFactory: created STDP projection with %d connections",
            len(conn_list),
        )

        # 2. Dopamine source population -------------------------------------
        n_targets = self._population_size(post_pop)
        nm_source_count = self._neuromodulation_source_count(n_targets)
        self._dopamine_source = self.sim.Population(
            nm_source_count,
            self.sim.SpikeSourcePoisson(rate=0.0),
            label="dopamine_source",
        )

        # 3. Neuromodulation projection -------------------------------------
        nm_connections = self._build_neuromodulation_connections(n_targets)
        nm = self._extra_models.Neuromodulation(
            weight=self._NM_WEIGHT,
            tau_c=self._NM_TAU_C,
            tau_d=self._NM_TAU_D,
        )
        self._nm_proj = self.sim.Projection(
            self._dopamine_source,
            post_pop,
            self.sim.FromListConnector(nm_connections),
            synapse_type=nm,
            receptor_type="reward",
            label=f"{label}_neuromodulation",
        )
        logger.info(
            "SpiNNakerFactory: created sharded neuromodulation projection "
            "(%d dopamine sources -> %d targets, max %d targets/source)",
            nm_source_count,
            n_targets,
            self._NM_MAX_TARGETS_PER_SOURCE,
        )

        return self._stdp_proj, self._dopamine_source

    def _population_size(self, population: Any) -> int:
        """Return a PyNN Population size across supported backends."""
        for attr in ("size", "_size"):
            value = getattr(population, attr, None)
            if value is not None:
                try:
                    return int(value() if callable(value) else value)
                except Exception:
                    pass
        try:
            return int(len(population))
        except Exception:
            pass
        if self._max_polyps is not None and self._neurons_per_polyp is not None:
            return int(self._max_polyps * self._neurons_per_polyp)
        raise ValueError("Cannot determine post population size for neuromodulation")

    def _neuromodulation_source_count(self, n_targets: int) -> int:
        if n_targets < 1:
            raise ValueError("Neuromodulation target population must be non-empty")
        return int(
            (n_targets + self._NM_MAX_TARGETS_PER_SOURCE - 1)
            // self._NM_MAX_TARGETS_PER_SOURCE
        )

    def _build_neuromodulation_connections(self, n_targets: int) -> List[Tuple[int, int]]:
        """Build sharded dopamine-source connections for sPyNNaker.

        One dopamine source neuron fans out only to a bounded contiguous target
        slice. This avoids sPyNNaker's 255-neuromodulation-synapse-per-source
        row limit while preserving a global dopamine signal.
        """
        n_sources = self._neuromodulation_source_count(n_targets)
        connections: List[Tuple[int, int]] = []
        for target_idx in range(n_targets):
            source_idx = min(
                n_sources - 1,
                target_idx // self._NM_MAX_TARGETS_PER_SOURCE,
            )
            connections.append((source_idx, target_idx))
        return connections

    def clear_inter_polyp_connections(self, dopamine_handle: Any) -> None:
        """No-op: sPyNNaker cannot remove projections after setup."""
        pass

    def deliver_dopamine(self, dopamine_handle: Any, level: float) -> None:
        """Deliver dopamine by adjusting the Poisson source rate.

        The dopamine *level* (typical range -1.0 … +1.0) is mapped linearly
        to a firing rate in Hz.  Each spike from the source travels through
        the ``Neuromodulation`` synapse and increments the dopamine
        concentration variable on the target STDP synapses.
        """
        if self._dopamine_source is None:
            return
        rate_hz = max(0.0, float(level) * self._DA_RATE_SCALE)
        try:
            self._dopamine_source.set(rate=rate_hz)
            logger.debug("SpiNNakerFactory: dopamine source rate set to %.2f Hz", rate_hz)
        except Exception as exc:
            logger.warning("SpiNNakerFactory: deliver_dopamine failed: %s", exc)

    def read_inter_polyp_weights(
        self, dopamine_handle: Any
    ) -> Dict[Tuple[int, int], float]:
        """sPyNNaker virtual mode cannot read back weights; returns empty dict."""
        return {}

    # ------------------------------------------------------------------
    # Standard models (fallback)
    # ------------------------------------------------------------------

    def create_cell_type(self, **kwargs: Any) -> Any:
        logger.debug("SpiNNakerFactory: using standard IF_curr_exp")
        return super().create_cell_type(**kwargs)

    def create_stdp_synapse(self, **kwargs: Any) -> Any:
        logger.debug("SpiNNakerFactory: using standard STDPMechanism")
        # Clip weight to hardware fixed-point limits
        if "weight" in kwargs:
            kwargs["weight"] = clip_weight_for_hardware(kwargs["weight"])
        return super().create_stdp_synapse(**kwargs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_FACTORY_MAP = {
    "NEST": NESTFactory,
    "Brian2": Brian2Factory,
    "MockSimulator": MockSimulatorFactory,
    "sPyNNaker": SpiNNakerFactory,
}


class _DefaultFactory(BackendFactory):
    """Fallback factory used when ``get_backend_factory`` has not been called."""

    def __init__(self) -> None:
        self.sim = None  # type: ignore[assignment]
        self.backend_name = "uninitialized"

    def _raise(self) -> None:
        raise RuntimeError(
            "BackendFactory not initialized. Call get_backend_factory(sim) first."
        )

    def create_cell_type(self, **kwargs: Any) -> Any:
        self._raise()

    def create_static_synapse(self, **kwargs: Any) -> Any:
        self._raise()

    def create_stdp_synapse(self, **kwargs: Any) -> Any:
        self._raise()

    def create_inter_polyp_projection(self, *args, **kwargs):
        self._raise()

    def deliver_dopamine(self, *args, **kwargs):
        self._raise()


# Module-level singleton.  Set once at organism init.
_default_factory: BackendFactory = _DefaultFactory()


def get_backend_factory(sim: Any) -> BackendFactory:
    """Return the appropriate factory for the given PyNN simulator module.

    This should be called once during ``Organism.__init__`` and stored
    on the organism instance.  PolypPopulation and ReefNetwork then
    receive the factory instance rather than importing ``sim`` directly.
    """
    global _default_factory
    name = BackendFactory._detect_backend(sim)
    cls = _FACTORY_MAP.get(name, BackendFactory)
    _default_factory = cls(sim)
    logger.info("BackendFactory initialized for %s", name)
    return _default_factory


def factory() -> BackendFactory:
    """Return the currently active factory singleton.

    Raises RuntimeError if ``get_backend_factory`` has not been called.
    """
    return _default_factory
