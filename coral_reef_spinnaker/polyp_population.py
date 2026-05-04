"""
PyNN population management for Coral Reef Architecture polyps.

This module contains:
- :class:`PolypNeuronType` — factory that maps :class:`PolypState` to
  sPyNNaker-compatible LIF parameter dictionaries.
- :class:`PolypPopulation` — manages a PyNN Population together with a
  parallel list of :class:`PolypState` objects, and exposes lifecycle
  methods (add, remove, trophic step, competitive readout).
"""

from __future__ import annotations

import math
import random
import warnings
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from .polyp_plasticity import DopamineModulatedWeightDependence
from .polyp_state import (
    ACCURACY_FLOOR,
    BAX_ACCUMULATION_RATE,
    CHILD_TROPHIC_SHARE,
    DEFAULT_CM_NF,
    DEFAULT_CYC_THRESHOLD,
    DEFAULT_DRIVE_TO_CURRENT_NA,
    DEFAULT_REPRODUCTION_THRESHOLD,
    DEFAULT_TAU_M_MS,
    DEFAULT_TAU_REFRAC_MS,
    DEFAULT_V_RESET_MV,
    DEFAULT_V_REST_MV,
    DEFAULT_V_THRESH_MV,
    HERITABLE_TRAITS,
    JUVENILE_WINDOW_STEPS,
    MIN_READOUT_SIZE,
    MUTATION_LOG_MAX,
    MUTATION_LOG_MIN,
    MUTATION_SIGMA,
    NEONATAL_EXCITABILITY_PEAK,
    SEED_OUTPUT_SCALE,
    STDP_A_MINUS,
    STDP_A_PLUS,
    PolypState,
    PolypSummary,
)

class PolypNeuronType:
    """Factory for creating PyNN LIF neurons representing CRA polyps.

    Each polyp is a single LIF neuron in a PyNN Population.  This class
    manages the mapping between biological ``PolypState`` and the PyNN
    neuron parameter dictionary required by sPyNNaker.

    The LIF parameters are tuned so that:

    ``firing_rate ~ max(0, drive)``

    where ``drive = mi * uptake_rate + da_gain * dopamine_ema``.

    This is achieved through ``i_offset`` (constant current injection)
    proportional to the drive term.  With ``tau_m = 20 ms``,
    ``v_thresh = -55 mV`` and ``v_rest = -65 mV``, the neuron needs
    ``~10 mV`` of depolarisation to spike.  An ``i_offset`` of
    ``drive * drive_to_current_na`` nA achieves approximately the
    desired firing rate.

    Parameters
    ----------
    drive_to_current_na : float, optional
        Conversion factor from drive units to nano-amperes of
        ``i_offset``.  Default ``DEFAULT_DRIVE_TO_CURRENT_NA`` (2.0).
    tau_m_ms : float, optional
        Membrane time constant in ms.  Default 20.0.
    v_rest_mV : float, optional
        Resting potential in mV.  Default -65.0.
    v_reset_mV : float, optional
        Reset potential after a spike, in mV.  Default -70.0.
    v_thresh_mV : float, optional
        Firing threshold in mV.  Default -55.0.
    tau_refrac_ms : float, optional
        Refractory period in ms.  Default 2.0.
    tau_syn_e_ms : float, optional
        Excitatory synaptic time constant in ms. Default 5.0.
    tau_syn_i_ms : float, optional
        Inhibitory synaptic time constant in ms. Default 5.0.
    cm_nF : float, optional
        Membrane capacitance in nF.  Default 0.25.

    Attributes
    ----------
    params : dict
        Base LIF parameter dictionary (without ``i_offset``).
    drive_to_current_na : float
        Current conversion factor.
    """

    def __init__(
        self,
        drive_to_current_na: float = DEFAULT_DRIVE_TO_CURRENT_NA,
        tau_m_ms: float = DEFAULT_TAU_M_MS,
        v_rest_mV: float = DEFAULT_V_REST_MV,
        v_reset_mV: float = DEFAULT_V_RESET_MV,
        v_thresh_mV: float = DEFAULT_V_THRESH_MV,
        tau_refrac_ms: float = DEFAULT_TAU_REFRAC_MS,
        tau_syn_e_ms: float = 5.0,
        tau_syn_i_ms: float = 5.0,
        cm_nF: float = DEFAULT_CM_NF,
    ):
        """Initialise the factory with fixed LIF parameters."""
        self.drive_to_current_na = float(drive_to_current_na)
        self._base_params = {
            "tau_m": float(tau_m_ms),
            "v_rest": float(v_rest_mV),
            "v_reset": float(v_reset_mV),
            "v_thresh": float(v_thresh_mV),
            "tau_refrac": float(tau_refrac_ms),
            "tau_syn_E": float(tau_syn_e_ms),
            "tau_syn_I": float(tau_syn_i_ms),
            "cm": float(cm_nF),
        }

    @property
    def base_params(self) -> Dict[str, float]:
        """Return a copy of the base LIF parameters (no ``i_offset``)."""
        return dict(self._base_params)

    def drive_to_current_offset(self, drive: float) -> float:
        """Convert a drive value to ``i_offset`` in nA.

        The mapping is linear:

        ``i_offset_na = drive * drive_to_current_na``

        Parameters
        ----------
        drive : float
            Non-negative drive value (typically from
            :py:meth:`PolypState.compute_drive`).

        Returns
        -------
        float
            Current injection in nano-amperes.
        """
        return max(0.0, float(drive)) * self.drive_to_current_na

    def create_lif_params(self, state: PolypState) -> Dict[str, float]:
        """Build a complete PyNN LIF parameter dict from a ``PolypState``.

        This is the primary interface: given a polyp's biological state,
        compute the drive and return the dictionary that should be passed
        to ``sim.Population(..., cellclass=sim.IF_curr_exp, ... )`` or
        set via ``population.set(i_offset=...)``.

        Parameters
        ----------
        state : PolypState
            The biological state of the polyp.

        Returns
        -------
        dict
            Dictionary with keys ``tau_m``, ``v_rest``, ``v_reset``,
            ``v_thresh``, ``tau_refrac``, ``tau_syn_E``, ``tau_syn_I``,
            ``cm``, ``i_offset``.
        """
        drive = state.compute_drive()
        i_offset = self.drive_to_current_offset(drive)
        params = self.base_params
        params["i_offset"] = float(i_offset)
        return params

    def create_lif_param_list(
        self, states: List[PolypState]
    ) -> Dict[str, List[float]]:
        """Build parameter dicts for a list of polyps (vectorised).

        When creating a PyNN Population with ``n`` neurons, PyNN expects
        parameters as lists of length ``n`` (or single scalars).  This
        helper converts a list of ``PolypState`` objects into the
        columnar format required by ``sim.Population``.

        Parameters
        ----------
        states : list of PolypState
            One state object per neuron in the population.

        Returns
        -------
        dict
            Dictionary mapping parameter name -> list of values.
        """
        n = len(states)
        param_lists: Dict[str, List[float]] = {
            "tau_m": [self._base_params["tau_m"]] * n,
            "v_rest": [self._base_params["v_rest"]] * n,
            "v_reset": [self._base_params["v_reset"]] * n,
            "v_thresh": [self._base_params["v_thresh"]] * n,
            "tau_refrac": [self._base_params["tau_refrac"]] * n,
            "tau_syn_E": [self._base_params["tau_syn_E"]] * n,
            "tau_syn_I": [self._base_params["tau_syn_I"]] * n,
            "cm": [self._base_params["cm"]] * n,
            "i_offset": [
                self.drive_to_current_offset(s.compute_drive()) for s in states
            ],
        }
        return param_lists


# ---------------------------------------------------------------------------
# PolypPopulation
# ---------------------------------------------------------------------------

class PolypPopulation:
    """Manage a PyNN Population of polyp neurons and their host-side state.

    This is the main interface for the Coral Reef Architecture on
    SpiNNaker.  It wraps:

    1. A PyNN ``Population`` (the actual LIF neurons running on the
       SpiNNaker hardware).
    2. A parallel list of :py:class:`PolypState` objects living in host
       memory.
    3. A ``PolypNeuronType`` factory for translating biological state to
       LIF parameters.

    After each ``sim.run()``, spike counts are read from the hardware
    and used to update ``PolypState.activity_rate``.  The orchestrator
    then calls the ``step_*`` methods on each ``PolypState`` and finally
    calls :py:meth:`update_current_injections` to push the new drive
    values back to the hardware before the next ``sim.run()``.

    Parameters
    ----------
    simulator : module
        The PyNN simulator module (typically ``pyNN.spiNNaker``).
    n_neurons : int
        Initial size of the population (number of polyp slots).
    label : str
        Human-readable label for the PyNN population.
    neuron_type : PolypNeuronType or None, optional
        Factory for LIF parameters.  If ``None``, a default instance is
        created.

    Attributes
    ----------
    sim : module
        Simulator module reference.
    population : pyNN.Population
        The PyNN population object (hardware neurons).
    states : list of PolypState
        Host-side state, index-matched to ``population``.
    neuron_type : PolypNeuronType
        LIF parameter factory.
    next_polyp_id : int
        Monotonically increasing counter for unique polyp IDs.
    lineage_counter : int
        Monotonically increasing counter for lineage IDs.
    _spike_recorder_enabled : bool
        Whether spike recording has been activated on the population.
    """

    def __init__(
        self,
        simulator,
        max_polyps: int,
        label: str,
        neuron_type: Optional[PolypNeuronType] = None,
        constraint_checker=None,
        neurons_per_polyp: int = 32,
        n_input: int = 8,
        n_exc: int = 16,
        n_inh: int = 4,
        n_readout: int = 4,
        internal_conn_seed: int = 42,
        backend_factory: Optional[Any] = None,
    ):
        """Create the PyNN population and initialise host-side state.

        Each polyp is a microcircuit — a contiguous block of
        ``neurons_per_polyp`` LIF neurons within the population.
        Unused blocks are kept in a "dead" state until :py:meth:`add_polyp`
        assigns them.

        Parameters
        ----------
        simulator : module
            The PyNN simulator module.
        max_polyps : int
            Maximum number of polyp slots to pre-allocate.
        label : str
            Label for the PyNN population.
        neuron_type : PolypNeuronType or None, optional
            Custom LIF parameter factory.  Default ``None`` -> default
            factory.
        constraint_checker : SpiNNakerConstraintChecker or None
            Hardware constraint validator (optional).
        neurons_per_polyp : int
            Number of LIF neurons per polyp microcircuit.
        n_input : int
            Input neurons per polyp.
        n_exc : int
            Excitatory neurons per polyp.
        n_inh : int
            Inhibitory neurons per polyp.
        n_readout : int
            Readout neurons per polyp.
        internal_conn_seed : int
            Base seed for deterministic internal microcircuit wiring.
        """
        if max_polyps < 1:
            raise ValueError("max_polyps must be >= 1")
        if neurons_per_polyp < 1:
            raise ValueError("neurons_per_polyp must be >= 1")
        expected = n_input + n_exc + n_inh + n_readout
        if neurons_per_polyp != expected:
            raise ValueError(
                f"neurons_per_polyp ({neurons_per_polyp}) must equal "
                f"n_input + n_exc + n_inh + n_readout = {expected}"
            )

        self.sim = simulator
        if backend_factory is None:
            from .backend_factory import get_backend_factory
            self._factory = get_backend_factory(self.sim)
        else:
            self._factory = backend_factory

        self.neuron_type = neuron_type or PolypNeuronType()
        self.label = str(label)
        self.next_polyp_id: int = 0
        self.lineage_counter: int = 0
        self._spike_recorder_enabled: bool = False
        self._constraint_checker = constraint_checker
        self.neurons_per_polyp = neurons_per_polyp
        self.max_polyps = max_polyps
        self.n_input = n_input
        self.n_exc = n_exc
        self.n_inh = n_inh
        self.n_readout = n_readout
        self.internal_conn_seed = int(internal_conn_seed)

        # Total hardware neurons = polyps × neurons per polyp
        total_neurons = max_polyps * neurons_per_polyp

        # Validate against hardware constraints if checker provided
        if self._constraint_checker is not None:
            violations = self._constraint_checker.check_population(
                total_neurons, label=self.label
            )
            if violations:
                msgs = "; ".join(v.message for v in violations)
                raise RuntimeError(
                    f"PolypPopulation '{self.label}' violates SpiNNaker constraints: {msgs}"
                )

        # Create empty host-side state list (one entry per POLYP, not per neuron)
        self.states: List[PolypState] = []

        # Build initial parameter list – all neurons start with zero drive
        zero_params: Dict[str, float] = self.neuron_type.base_params
        zero_params["i_offset"] = 0.0

        # PyNN expects either scalar params or list-per-parameter
        param_lists: Dict[str, list] = {
            k: [v] * total_neurons for k, v in zero_params.items()
        }

        # Create the hardware population
        cell_type = self._factory.create_cell_type()
        # PyNN accepts either a celltype class + params dict, or a
        # celltype instance with no params.  The factory may return
        # either depending on the backend (NEST class vs sPyNNaker
        # custom model instance).
        if callable(cell_type):
            self.population = self.sim.Population(
                total_neurons,
                cell_type,
                param_lists,
                label=self.label,
            )
        else:
            self.population = self.sim.Population(
                total_neurons,
                cell_type,
                label=self.label,
            )
        # Alias expected by ReefNetwork._create_projection
        self._population = self.population

        # Mark all polyp slots as unused (dead placeholder state)
        for idx in range(max_polyps):
            base = idx * neurons_per_polyp
            placeholder = PolypState(
                polyp_id=-1,
                lineage_id=-1,
                slot_index=idx,
                base_index=base,
                block_start=base,
                block_end=base + neurons_per_polyp,
                n_neurons_per_polyp=neurons_per_polyp,
                input_slice=slice(base, base + n_input),
                exc_slice=slice(base + n_input, base + n_input + n_exc),
                inh_slice=slice(base + n_input + n_exc, base + n_input + n_exc + n_inh),
                readout_slice=slice(base + n_input + n_exc + n_inh, base + neurons_per_polyp),
                is_alive=False,
                activity_rate=0.0,
            )
            self.states.append(placeholder)

        # Enable spike recording by default
        self.population.record("spikes")
        self._spike_recorder_enabled = True

    # ------------------------------------------------------------------
    # Slice helpers
    # ------------------------------------------------------------------

    def input_slice(self, slot_index: int) -> slice:
        """Return the input neuron slice for polyp slot *slot_index*."""
        base = slot_index * self.neurons_per_polyp
        return slice(base, base + self.n_input)

    def exc_slice(self, slot_index: int) -> slice:
        """Return the excitatory neuron slice for polyp slot *slot_index*."""
        base = slot_index * self.neurons_per_polyp
        return slice(base + self.n_input, base + self.n_input + self.n_exc)

    def inh_slice(self, slot_index: int) -> slice:
        """Return the inhibitory neuron slice for polyp slot *slot_index*."""
        base = slot_index * self.neurons_per_polyp
        return slice(
            base + self.n_input + self.n_exc,
            base + self.n_input + self.n_exc + self.n_inh,
        )

    def readout_slice(self, slot_index: int) -> slice:
        """Return the readout neuron slice for polyp slot *slot_index*."""
        base = slot_index * self.neurons_per_polyp
        return slice(
            base + self.n_input + self.n_exc + self.n_inh,
            base + self.neurons_per_polyp,
        )

    # ------------------------------------------------------------------
    # Population queries
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Total number of neuron slots (alive + dead)."""
        return len(self.states)

    @property
    def n_alive(self) -> int:
        """Number of currently alive polyps."""
        return sum(1 for s in self.states if s.is_alive)

    @property
    def n_dead(self) -> int:
        """Number of dead / unused slots."""
        return sum(1 for s in self.states if not s.is_alive)

    def get_alive_indices(self) -> List[int]:
        """Return hardware neuron indices of all alive polyps.

        Returns
        -------
        list of int
            Indices into ``self.states`` (and ``self.population``) of
            alive polyps.
        """
        return [i for i, s in enumerate(self.states) if s.is_alive]

    def get_alive_states(self) -> List[PolypState]:
        """Return a list of all alive ``PolypState`` objects.

        Returns
        -------
        list of PolypState
        """
        return [s for s in self.states if s.is_alive]

    def get_state_by_polyp_id(self, polyp_id: int) -> Optional[PolypState]:
        """Find a ``PolypState`` by its ``polyp_id``.

        Parameters
        ----------
        polyp_id : int
            The unique polyp ID to search for.

        Returns
        -------
        PolypState or None
            The matching state, or ``None`` if not found.
        """
        for s in self.states:
            if s.polyp_id == polyp_id:
                return s
        return None

    def get_index_by_polyp_id(self, polyp_id: int) -> Optional[int]:
        """Return the polyp slot index for a given ``polyp_id``.

        Parameters
        ----------
        polyp_id : int
            The unique polyp ID.

        Returns
        -------
        int or None
            The slot index into ``self.states``, or ``None``.
        """
        for i, s in enumerate(self.states):
            if s.polyp_id == polyp_id:
                return i
        return None

    # ------------------------------------------------------------------
    # Internal template
    # ------------------------------------------------------------------

    def instantiate_internal_template(
        self,
        slot_index: int,
        seed: int = 42,
    ) -> Tuple[List[Tuple[int, int, float, float]], List[Tuple[int, int, float, float]]]:
        """Generate internal synapse list for a polyp microcircuit.

        Returns two connection lists: ``(exc_conns, inh_conns)``.

        *exc_conns* contains all positive-weight connections:
        input→exc, E→E, E→inh, E→readout.

        *inh_conns* contains all negative-weight connections:
        I→E.

        Parameters
        ----------
        slot_index : int
            Polyp slot index (determines base neuron index).
        seed : int
            Random seed offset for deterministic wiring.

        Returns
        -------
        tuple of lists
            ``(exc_conns, inh_conns)`` where each element is a list of
            ``(pre, post, weight, delay)`` tuples.
        """
        rng = np.random.RandomState(seed + slot_index)
        base = slot_index * self.neurons_per_polyp

        def input_idx(i):   return base + i
        def exc_idx(i):     return base + self.n_input + i
        def inh_idx(i):     return base + self.n_input + self.n_exc + i
        def readout_idx(i): return base + self.n_input + self.n_exc + self.n_inh + i

        exc_conns: List[Tuple[int, int, float, float]] = []
        inh_conns: List[Tuple[int, int, float, float]] = []

        # input -> excitatory
        for i_in in range(self.n_input):
            targets = rng.choice(self.n_exc, size=min(4, self.n_exc), replace=False)
            for t in targets:
                exc_conns.append((input_idx(i_in), exc_idx(t), 0.15, 1.0))

        # input -> inhibitory
        for i_in in range(self.n_input):
            targets = rng.choice(self.n_inh, size=min(2, self.n_inh), replace=False)
            for t in targets:
                exc_conns.append((input_idx(i_in), inh_idx(t), 0.10, 1.0))

        # excitatory -> excitatory (sparse recurrent, no self)
        for i_exc in range(self.n_exc):
            targets = rng.choice(self.n_exc, size=min(4, self.n_exc - 1), replace=False)
            for t in targets:
                if t != i_exc:
                    w = float(rng.lognormal(mean=np.log(0.1), sigma=0.5))
                    exc_conns.append((exc_idx(i_exc), exc_idx(t), w, 1.0))

        # excitatory -> inhibitory
        for i_exc in range(self.n_exc):
            targets = rng.choice(self.n_inh, size=min(2, self.n_inh), replace=False)
            for t in targets:
                exc_conns.append((exc_idx(i_exc), inh_idx(t), 0.20, 1.0))

        # inhibitory -> excitatory (all-to-all)
        for i_inh in range(self.n_inh):
            for t in range(self.n_exc):
                inh_conns.append((inh_idx(i_inh), exc_idx(t), -0.40, 1.0))

        # excitatory -> readout
        for i_exc in range(self.n_exc):
            targets = rng.choice(self.n_readout, size=min(2, self.n_readout), replace=False)
            for t in targets:
                w = float(rng.lognormal(mean=np.log(0.1), sigma=0.5))
                exc_conns.append((exc_idx(i_exc), readout_idx(t), w, 1.0))

        return exc_conns, inh_conns

    # ------------------------------------------------------------------
    # Polyp lifecycle
    # ------------------------------------------------------------------

    def add_polyp(
        self,
        state: PolypState,
        preserve_identity: Optional[bool] = None,
    ) -> int:
        """Activate a dead slot with a new ``PolypState``.

        The method finds the first dead slot in ``self.states``, writes
        the provided ``state`` into it, sets ``is_alive = True``, and updates the
        hardware neuron's ``i_offset`` to match the state's drive.

        If the incoming state already has a non-negative ``polyp_id`` or
        ``lineage_id`` (as lifecycle-born children do), identity is preserved by
        default. Otherwise a fresh polyp and lineage identity is assigned.

        Parameters
        ----------
        state : PolypState
            Biological state for the new polyp.
        preserve_identity : bool or None
            ``True`` preserves existing non-negative IDs, ``False`` always
            allocates fresh IDs, and ``None`` auto-preserves states that already
            carry lifecycle-assigned identity.

        Returns
        -------
        int
            The polyp slot index assigned to this polyp.

        Raises
        ------
        RuntimeError
            If no dead slots are available (population is full).
        """
        # Find first dead slot
        slot_idx: Optional[int] = None
        for i, s in enumerate(self.states):
            if not s.is_alive:
                slot_idx = i
                break

        if slot_idx is None:
            raise RuntimeError(
                f"Population '{self.label}' is full (size={self.size}). "
                "Cannot add more polyps without resizing."
            )

        # Assign or preserve identity before writing the hardware slot.
        if preserve_identity is None:
            preserve_identity = state.polyp_id >= 0 or state.lineage_id >= 0

        if preserve_identity:
            if state.polyp_id < 0:
                state.polyp_id = self.next_polyp_id
            if state.lineage_id < 0:
                state.lineage_id = self.lineage_counter
            self.next_polyp_id = max(self.next_polyp_id, state.polyp_id + 1)
            self.lineage_counter = max(self.lineage_counter, state.lineage_id + 1)
        else:
            state.polyp_id = self.next_polyp_id
            state.lineage_id = self.lineage_counter
            self.next_polyp_id += 1
            self.lineage_counter += 1

        # Assign block layout
        state.is_alive = True
        state.slot_index = slot_idx
        state.base_index = slot_idx * self.neurons_per_polyp
        state.n_neurons_per_polyp = self.neurons_per_polyp
        state.block_start = state.base_index
        state.block_end = state.base_index + self.neurons_per_polyp
        state.input_slice = self.input_slice(slot_idx)
        state.exc_slice = self.exc_slice(slot_idx)
        state.inh_slice = self.inh_slice(slot_idx)
        state.readout_slice = self.readout_slice(slot_idx)
        # Store state
        self.states[slot_idx] = state

        # Set hardware parameters for ALL neurons in the block.
        # Biological heterogeneity: each neuron gets slightly different
        # tau_m, v_thresh and cm so that even with identical synaptic
        # input, readout neurons fire at different rates.
        n = state.block_end - state.block_start
        base_params = self.neuron_type.create_lif_params(state)
        param_lists: Dict[str, List[float]] = {
            "v_rest": [base_params["v_rest"]] * n,
            "v_reset": [base_params["v_reset"]] * n,
            "tau_refrac": [base_params["tau_refrac"]] * n,
            "tau_syn_E": [base_params["tau_syn_E"]] * n,
            "tau_syn_I": [base_params["tau_syn_I"]] * n,
            "i_offset": [base_params["i_offset"]] * n,
        }
        # Heterogeneous membrane properties (~10% CV, biologically observed)
        rng = np.random.RandomState(state.polyp_id + 42)
        param_lists["tau_m"] = rng.normal(
            self.neuron_type._base_params["tau_m"], 2.0, n
        ).tolist()
        param_lists["v_thresh"] = rng.normal(
            self.neuron_type._base_params["v_thresh"], 1.0, n
        ).tolist()
        param_lists["cm"] = rng.normal(
            self.neuron_type._base_params["cm"], 0.02, n
        ).tolist()
        for pname, pval in param_lists.items():
            self.population[state.block_start : state.block_end].set(
                **{pname: pval}
            )

        # Create internal projections (excitatory and inhibitory)
        if self.sim is not None:
            exc_conns, inh_conns = self.instantiate_internal_template(
                slot_index=slot_idx,
                seed=self.internal_conn_seed,
            )
            if exc_conns:
                state._internal_proj_exc = self.sim.Projection(
                    self.population,
                    self.population,
                    self.sim.FromListConnector(exc_conns),
                    synapse_type=self._factory.create_excitatory_synapse(),
                    receptor_type="excitatory",
                    label=f"polyp_{state.polyp_id}_exc",
                )
            if inh_conns:
                state._internal_proj_inh = self.sim.Projection(
                    self.population,
                    self.population,
                    self.sim.FromListConnector(inh_conns),
                    synapse_type=self._factory.create_inhibitory_synapse(),
                    receptor_type="inhibitory",
                    label=f"polyp_{state.polyp_id}_inh",
                )

        return slot_idx

    def restore_polyp(
        self,
        state: PolypState,
        slot_index: int,
        polyp_id: int,
    ) -> int:
        """Restore a polyp to a specific slot with a specific ID.

        Unlike :py:meth:`add_polyp`, this does **not** auto-assign
        ``polyp_id`` or ``lineage_id``.  It is used during sPyNNaker
        full rebuilds to preserve topology and identity across
        ``sim.end()`` / ``sim.setup()`` cycles.

        Parameters
        ----------
        state : PolypState
            The polyp state to restore (must already have ``polyp_id``
            and ``lineage_id`` set).
        slot_index : int
            Hardware slot index to place the polyp into.
        polyp_id : int
            The original polyp ID to preserve.

        Returns
        -------
        int
            The slot index assigned.
        """
        if slot_index < 0 or slot_index >= self.max_polyps:
            raise ValueError(
                f"Invalid slot_index {slot_index} (max={self.max_polyps})"
            )

        existing = self.states[slot_index]
        if existing.is_alive:
            raise RuntimeError(
                f"Cannot restore polyp {polyp_id}: slot {slot_index} is already alive"
            )

        # Preserve original identity
        state.polyp_id = polyp_id
        state.slot_index = slot_index
        state.base_index = slot_index * self.neurons_per_polyp
        state.n_neurons_per_polyp = self.neurons_per_polyp
        state.block_start = state.base_index
        state.block_end = state.base_index + self.neurons_per_polyp
        state.input_slice = self.input_slice(slot_index)
        state.exc_slice = self.exc_slice(slot_index)
        state.inh_slice = self.inh_slice(slot_index)
        state.readout_slice = self.readout_slice(slot_index)
        state.is_alive = True

        self.states[slot_index] = state

        # Set hardware parameters (same logic as add_polyp)
        n = state.block_end - state.block_start
        base_params = self.neuron_type.create_lif_params(state)
        param_lists: Dict[str, List[float]] = {
            "v_rest": [base_params["v_rest"]] * n,
            "v_reset": [base_params["v_reset"]] * n,
            "tau_refrac": [base_params["tau_refrac"]] * n,
            "tau_syn_E": [base_params["tau_syn_E"]] * n,
            "tau_syn_I": [base_params["tau_syn_I"]] * n,
            "i_offset": [base_params["i_offset"]] * n,
        }
        rng = np.random.RandomState(state.polyp_id + 42)
        param_lists["tau_m"] = rng.normal(
            self.neuron_type._base_params["tau_m"], 2.0, n
        ).tolist()
        param_lists["v_thresh"] = rng.normal(
            self.neuron_type._base_params["v_thresh"], 1.0, n
        ).tolist()
        param_lists["cm"] = rng.normal(
            self.neuron_type._base_params["cm"], 0.02, n
        ).tolist()
        for pname, pval in param_lists.items():
            self.population[state.block_start : state.block_end].set(
                **{pname: pval}
            )

        # Re-create internal projections
        if self.sim is not None:
            exc_conns, inh_conns = self.instantiate_internal_template(
                slot_index=slot_index, seed=self.internal_conn_seed
            )
            if exc_conns:
                state._internal_proj_exc = self.sim.Projection(
                    self.population,
                    self.population,
                    self.sim.FromListConnector(exc_conns),
                    synapse_type=self._factory.create_excitatory_synapse(),
                    receptor_type="excitatory",
                    label=f"polyp_{state.polyp_id}_exc",
                )
            if inh_conns:
                state._internal_proj_inh = self.sim.Projection(
                    self.population,
                    self.population,
                    self.sim.FromListConnector(inh_conns),
                    synapse_type=self._factory.create_inhibitory_synapse(),
                    receptor_type="inhibitory",
                    label=f"polyp_{state.polyp_id}_inh",
                )

        # Bump counters so future births don't reuse IDs
        self.next_polyp_id = max(self.next_polyp_id, polyp_id + 1)
        self.lineage_counter = max(self.lineage_counter, state.lineage_id + 1)

        return slot_index

    def add_polyp_from_parent(
        self,
        parent_state: PolypState,
        xyz_offset: Optional[np.ndarray] = None,
    ) -> int:
        """Create a child polyp via reproduction from a parent.

        This is a convenience wrapper around :py:meth:`add_polyp` that:
        1. Creates a new ``PolypState`` with default values.
        2. Calls ``child.inherit_traits(parent)`` to copy and mutate
           heritable traits and split trophic reserve.
        3. Places the child near the parent (with ``spatial_dispersion``).
        4. Adds the child to the population.

        Parameters
        ----------
        parent_state : PolypState
            The parent polyp.  Its traits are copied with log-normal
            mutation and its trophic reserve is split.
        xyz_offset : np.ndarray or None, optional
            Optional 3-D offset vector for child placement.  If ``None``,
            a random offset scaled by the child's
            ``spatial_dispersion`` trait is used.

        Returns
        -------
        int
            Hardware neuron index of the new child polyp.
        """
        # Create fresh child state
        child = PolypState(
            polyp_id=-1,  # assigned by add_polyp
            lineage_id=-1,  # replaced with parent's lineage below
            is_juvenile=True,
            age_steps=0,
            handoff_complete=False,
            maternal_reserve_fraction=1.0,
        )

        # Inherit and mutate traits from parent
        child.inherit_traits(parent_state)

        # Place child near parent
        parent_xyz = parent_state.xyz.copy()
        if xyz_offset is not None:
            child.xyz = parent_xyz + np.asarray(xyz_offset, dtype=float)
        else:
            disp = child.spatial_dispersion
            offset = np.random.normal(0.0, disp, size=3)
            child.xyz = parent_xyz + offset

        # Inherit stream mask
        child.direct_stream_mask = set(parent_state.direct_stream_mask)

        child.lineage_id = parent_state.lineage_id

        return self.add_polyp(child, preserve_identity=True)

    def remove_polyp(self, polyp_id: int) -> bool:
        """Mark a polyp as dead and suppress its spikes.

        The slot is *not* removed from the PyNN Population (SpiNNaker
        does not support dynamic resizing efficiently).  Instead, the
        neuron's ``i_offset`` is set to a large negative value and
        ``v_thresh`` is raised so it cannot spike, and the host-side
        ``is_alive`` flag is cleared.

        Parameters
        ----------
        polyp_id : int
            The unique polyp ID to kill.

        Returns
        -------
        bool
            ``True`` if the polyp was found and killed, ``False``
            otherwise.
        """
        idx = self.get_index_by_polyp_id(polyp_id)
        if idx is None:
            return False

        state = self.states[idx]
        state.is_alive = False
        state.trophic_health = 0.0
        state.activity_rate = 0.0

        # Suppress spiking for entire microcircuit block
        self.population[state.block_start : state.block_end].set(
            i_offset=-1000.0,
            v_thresh=1000.0,
        )
        return True

    def kill_dead_polyps(self) -> int:
        """Scan all polyps and kill any whose ``is_alive`` is already ``False``.

        This is useful for batch cleanup after the orchestrator has
        already set ``is_alive = False`` based on trophic or BAX
        criteria.

        Returns
        -------
        int
            Number of polyps killed.
        """
        killed = 0
        for i, state in enumerate(self.states):
            if not state.is_alive and state.polyp_id >= 0:
                # Ensure hardware is suppressed for entire block
                self.population[state.block_start : state.block_end].set(
                    i_offset=-1000.0,
                    v_thresh=1000.0,
                )
                killed += 1
        return killed

    # ------------------------------------------------------------------
    # Hardware <-> host synchronisation
    # ------------------------------------------------------------------

    def get_spike_counts(self, runtime_ms: float) -> Dict[int, int]:
        """Read spike data from SpiNNaker and count spikes per polyp.

        For microcircuit polyps, spikes are aggregated across all neurons
        in the block to produce a single per-polyp count.

        Parameters
        ----------
        runtime_ms : float
            The duration of the last ``sim.run()`` call in milliseconds.
            Used to normalise firing rates.

        Returns
        -------
        dict
            Mapping from *polyp_id* -> total spike count across the block.
            Only alive polyps with non-zero counts are included.
        """
        if runtime_ms <= 0:
            raise ValueError("runtime_ms must be positive")

        # Get spikes from the population
        spiketrains = self._read_recent_spiketrains(runtime_ms)

        counts: Dict[int, int] = {}
        for state in self.states:
            if not state.is_alive:
                continue
            # Aggregate spikes across the entire microcircuit block
            n_spikes = 0
            for neuron_idx in range(state.block_start, state.block_end):
                if neuron_idx < len(spiketrains):
                    n_spikes += len(spiketrains[neuron_idx])
            if n_spikes > 0:
                counts[state.polyp_id] = n_spikes
                # Normalise to activity rate (spikes per ms -> Hz / max)
                max_rate_hz = 1000.0 / self.neuron_type._base_params["tau_refrac"]
                rate_hz = (n_spikes / runtime_ms) * 1000.0
                state.activity_rate = min(1.0, rate_hz / max_rate_hz)
            else:
                state.activity_rate = 0.0

        return counts

    def get_polyp_summaries(self, runtime_ms: float) -> Dict[int, PolypSummary]:
        """Read spike data and return per-polyp summaries.

        Computes firing rates for each subgroup, prediction, and confidence
        according to the v2.1 readout contract.

        Parameters
        ----------
        runtime_ms : float
            Duration of the last ``sim.run()`` in milliseconds.

        Returns
        -------
        dict
            Mapping from *polyp_id* -> :class:`PolypSummary`.
        """
        if runtime_ms <= 0:
            raise ValueError("runtime_ms must be positive")

        spiketrains = self._read_recent_spiketrains(runtime_ms)
        max_rate_hz = 1000.0 / self.neuron_type._base_params["tau_refrac"]

        summaries: Dict[int, PolypSummary] = {}
        for state in self.states:
            if not state.is_alive:
                continue

            def count_slice(sl: slice) -> int:
                return sum(
                    len(spiketrains[i]) for i in range(sl.start, sl.stop)
                    if i < len(spiketrains)
                )

            def rate_from_count(n_spikes: int, n_neurons: int) -> float:
                if n_neurons <= 0 or runtime_ms <= 0:
                    return 0.0
                rate_hz = (n_spikes / n_neurons) / runtime_ms * 1000.0
                return min(1.0, rate_hz / max_rate_hz)

            n_in = count_slice(state.input_slice)
            n_ex = count_slice(state.exc_slice)
            n_ih = count_slice(state.inh_slice)
            n_ro = count_slice(state.readout_slice)
            n_total = n_in + n_ex + n_ih + n_ro

            input_rate = rate_from_count(n_in, self.n_input)
            exc_rate = rate_from_count(n_ex, self.n_exc)
            inh_rate = rate_from_count(n_ih, self.n_inh)
            readout_rate = rate_from_count(n_ro, self.n_readout)

            # Per-readout-neuron rates for prediction differential
            ro_rates = [
                rate_from_count(
                    len(spiketrains[i]) if i < len(spiketrains) else 0, 1
                )
                for i in range(state.readout_slice.start, state.readout_slice.stop)
            ]

            # prediction = tanh(output_scale * (rate_r0 - rate_r1))
            # Use raw spike counts for the first two readout neurons.
            # With differential i_offset drive, n0-n1 directly encodes
            # market direction.  Scale is reduced because 5000 ms runtime
            # produces large spike-count differences; 0.02 keeps predictions
            # in the sensitive (-0.5, +0.5) range rather than saturating.
            r0_idx = state.readout_slice.start
            r1_idx = r0_idx + 1
            n0 = len(spiketrains[r0_idx]) if r0_idx < len(spiketrains) else 0
            n1 = len(spiketrains[r1_idx]) if r1_idx < len(spiketrains) else 0
            # Reduced coefficient to avoid saturation; keeps predictions
            # in the sensitive (-0.5, +0.5) range for most spike differentials.
            prediction = math.tanh(0.005 * (n0 - n1))

            # confidence = clip(max_rate / (mean_rate + eps), 0, 1)
            mean_ro = sum(ro_rates) / len(ro_rates) if ro_rates else 0.0
            max_ro = max(ro_rates) if ro_rates else 0.0
            confidence = 0.0 if mean_ro <= 0 else min(1.0, max_ro / (mean_ro + 1e-7))

            # Update state activity_rate for backward compat
            state.activity_rate = readout_rate

            summaries[state.polyp_id] = PolypSummary(
                polyp_id=state.polyp_id,
                input_rate=input_rate,
                exc_rate=exc_rate,
                inh_rate=inh_rate,
                readout_rate=readout_rate,
                activity_rate=readout_rate,
                prediction=prediction,
                confidence=confidence,
                n_spikes_total=n_total,
            )

        return summaries

    def _read_recent_spiketrains(self, runtime_ms: float) -> list:
        """Return spike trains for the most recent runtime window.

        NEST handles ``get_data(clear=True)`` as expected. PyNN/Brian2 can keep
        cumulative spike trains and reject the clear-window request if older
        spikes precede its current ``t_start``. For Brian2, avoid the clear path
        entirely and read the raw SpikeMonitor before PyNN can resize it.
        """
        monitor_trains = self._read_brian2_monitor_spiketrains(runtime_ms)
        if monitor_trains is not None:
            return monitor_trains
        try:
            return self.population.get_data("spikes", clear=True).segments[0].spiketrains
        except Exception:
            monitor_trains = self._read_brian2_monitor_spiketrains(runtime_ms)
            if monitor_trains is not None:
                return monitor_trains
            data = self.population.get_data("spikes", clear=False)
            spiketrains = data.segments[0].spiketrains
            try:
                current_time = float(self.sim.get_current_time())
            except Exception:
                current_time = float(runtime_ms)
            start_time = max(0.0, current_time - float(runtime_ms))
            filtered = []
            for train in spiketrains:
                times = np.asarray(train, dtype=float)
                mask = (times >= start_time) & (times <= current_time)
                filtered.append(times[mask])
            return filtered

    def _read_brian2_monitor_spiketrains(self, runtime_ms: float) -> Optional[list]:
        """Read recent spikes directly from PyNN/Brian2's raw SpikeMonitor.

        PyNN/Brian2 can fail when converting cumulative spike trains to Neo
        after a clear-window request because older spikes precede the recorder's
        new ``t_start``. The raw monitor still contains valid cumulative spike
        ids/times, so the parity harness can use those and filter the latest
        runtime window without falling back to synthetic activity.
        """
        try:
            recorder = getattr(self.population, "recorder", None)
            devices = getattr(recorder, "_devices", {}) if recorder is not None else {}
            spike_device = devices.get("spikes")
            if spike_device is None:
                return None

            ms_unit = getattr(self.sim, "ms", None)
            if ms_unit is None:
                from brian2 import ms as ms_unit  # type: ignore

            neuron_ids = np.asarray(spike_device.i, dtype=int)
            spike_times = np.asarray(spike_device.t / ms_unit, dtype=float)

            try:
                current_time = float(self.sim.get_current_time())
            except Exception:
                current_time = float(np.max(spike_times)) if spike_times.size else float(runtime_ms)
            start_time = max(0.0, current_time - float(runtime_ms))
            if start_time <= 0.0:
                window_mask = (spike_times >= 0.0) & (spike_times <= current_time)
            else:
                window_mask = (spike_times > start_time) & (spike_times <= current_time)

            n_neurons = int(self.max_polyps * self.neurons_per_polyp)
            filtered: list = []
            for neuron_idx in range(n_neurons):
                mask = window_mask & (neuron_ids == neuron_idx)
                filtered.append(spike_times[mask])
            return filtered
        except Exception:
            return None

    def update_current_injections(self) -> None:
        """Push new ``i_offset`` values to SpiNNaker from host-side state.

        For each alive polyp:
          1. Base drive (MI + dopamine) goes to ALL neurons, with a tiny
             per-neuron bias to break deterministic synchronization.
          2. Input neurons get a strong baseline + sensory signal so the
             network always fires, even on negative returns.
          3. Readout neurons 0 and 1 get a weak differential drive
             (diff_gain = 0.05) that nudges the cold-start bias without
             hardcoding the answer.
        """
        for state in self.states:
            if not state.is_alive:
                continue

            # Base drive without sensory component
            base_drive = (
                state.last_mi_or_zero * state.uptake_rate
                + state.da_gain * state.dopamine_ema
            )
            base_i_offset = self.neuron_type.drive_to_current_offset(base_drive)

            n_neurons = state.block_end - state.block_start
            neuron_indices = np.arange(n_neurons, dtype=float)
            # Deterministic pseudo-random biases [-0.02, +0.02] nA
            biases = np.sin(neuron_indices * 2.39996) * 0.02

            # Start with base + bias for all neurons
            i_offsets = np.clip(base_i_offset + biases, 0.0, None)

            # Input neurons: strong baseline (1.0 drive unit) + raw sensory
            input_drive = base_drive + 1.0 + state.sensory_drive
            input_i_offset = self.neuron_type.drive_to_current_offset(
                max(0.0, input_drive)
            )
            for idx in range(state.input_slice.start, state.input_slice.stop):
                i_offsets[idx - state.block_start] = max(
                    0.0, input_i_offset + biases[idx - state.block_start]
                )

            # Weak differential drive on readout 0 (+) and 1 (-)
            r0 = state.readout_slice.start
            r1 = r0 + 1
            if r0 < state.block_end and r1 < state.block_end:
                diff_gain = 0.15  # drive units per unit sensory_drive
                r0_drive = base_drive + state.sensory_drive * diff_gain
                r1_drive = base_drive - state.sensory_drive * diff_gain
                i_offsets[r0 - state.block_start] = max(
                    0.0,
                    self.neuron_type.drive_to_current_offset(r0_drive)
                    + biases[r0 - state.block_start],
                )
                i_offsets[r1 - state.block_start] = max(
                    0.0,
                    self.neuron_type.drive_to_current_offset(r1_drive)
                    + biases[r1 - state.block_start],
                )

            self.population[state.block_start : state.block_end].set(
                i_offset=i_offsets.tolist()
            )

    def push_all_parameters(self) -> None:
        """Push complete LIF parameter sets for all alive polyps.

        Unlike :py:meth:`update_current_injections` (which only updates
        ``i_offset``), this method writes *all* LIF parameters.  It is
        useful after trait mutations that change ``tau_m``, ``cm``, etc.
        """
        for i, state in enumerate(self.states):
            if not state.is_alive:
                continue
            params = self.neuron_type.create_lif_params(state)
            self.population[state.block_start : state.block_end].set(**params)

    # ------------------------------------------------------------------
    # Competitive readout (winner-take-all)
    # ------------------------------------------------------------------

    def competitive_readout(self) -> List[Tuple[int, float]]:
        """Select top-K polyps by activity rate for colony readout.

        The readout size is ``max(MIN_READOUT_SIZE, int(sqrt(N)))``
        where ``N`` is the number of *alive* polyps.  This maps directly
        to the CRA competitive aggregation mechanism.

        Returns
        -------
        list of tuple
            ``(polyp_id, activity_rate)`` for each selected polyp,
            sorted by activity rate descending.
        """
        alive = [
            (i, state.polyp_id, state.activity_rate)
            for i, state in enumerate(self.states)
            if state.is_alive
        ]

        n_alive = len(alive)
        if n_alive == 0:
            return []

        k = max(MIN_READOUT_SIZE, int(math.sqrt(n_alive)))
        k = min(k, n_alive)

        # Sort by activity_rate descending
        alive_sorted = sorted(alive, key=lambda x: x[2], reverse=True)
        top_k = alive_sorted[:k]

        return [(polyp_id, rate) for _idx, polyp_id, rate in top_k]

    def colony_output(self) -> float:
        """Compute a single scalar colony readout from competitive winners.

        The output is the weighted sum of ``output_scale * activity_rate``
        for the top-K polyps, weighted by their relative activity.

        Returns
        -------
        float
            Scalar colony prediction / readout value.
        """
        winners = self.competitive_readout()
        if not winners:
            return 0.0

        total = 0.0
        total_weight = 0.0
        for polyp_id, rate in winners:
            state = self.get_state_by_polyp_id(polyp_id)
            if state is None:
                continue
            # Amplify polyps with proven directional accuracy;
            # suppress random/noisy ones so the colony converges
            # on its best predictors.
            accuracy_boost = 0.5 + 0.5 * max(
                -1.0, min(1.0, state.directional_accuracy_ema)
            )
            weighted_rate = rate * accuracy_boost
            contribution = state.output_scale * weighted_rate
            total += contribution * weighted_rate
            total_weight += weighted_rate

        if total_weight == 0.0:
            return 0.0
        return total / total_weight

    # ------------------------------------------------------------------
    # STDP helpers
    # ------------------------------------------------------------------

    def create_dopamine_stdpc_mechanism(
        self,
        dopamine_ema: float,
        dopamine_scale: float = 1.0,
    ) -> object:
        """Create a dopamine-modulated STDP mechanism for projections.

        This factory method builds a ``sim.STDPMechanism`` with a
        ``sim.SpikePairRule`` whose ``A_plus`` and ``A_minus`` are
        scaled by the current dopamine EMA.  The weight dependence uses
        ``sim.AdditiveWeightDependence`` (sPyNNaker native).

        Parameters
        ----------
        dopamine_ema : float
            Current dopamine exponentially-weighted average.
        dopamine_scale : float, optional
            Additional scaling for dopamine modulation.  Default 1.0.

        Returns
        -------
        pyNN.STDPMechanism
            An STDP mechanism object ready to pass to
            ``sim.Projection(..., synapse_type=...)``.
        """
        if sim is None:
            raise RuntimeError(
                "SpiNNaker simulator not available; cannot create STDP mechanism."
            )

        a_plus, a_minus = DopamineModulatedWeightDependence.modulated_parameters(
            base_a_plus=STDP_A_PLUS,
            base_a_minus=STDP_A_MINUS,
            dopamine_ema=dopamine_ema,
            dopamine_scale=dopamine_scale,
        )

        # Delegate to the backend factory so sPyNNaker can inject a
        # custom dopamine-modulated STDP synapse when available.
        return self._factory.create_dopamine_stdpc_mechanism(
            dopamine_ema=dopamine_ema,
            dopamine_scale=dopamine_scale,
        )

    def apply_dopamine_to_all_stdpc(
        self,
        projection,
        dopamine_scale: float = 1.0,
    ) -> None:
        """Reconfigure an existing projection with new dopamine-modulated STDP.

        This method iterates over all alive polyps, reads each polyp's
        ``dopamine_ema``, and updates the STDP amplitudes on the
        corresponding synapses.  *Note*: sPyNNaker does not support
        per-synapse dynamic STDP parameter changes at runtime; this
        method is a best-effort helper that may need to be replaced by
        projection recreation depending on the sPyNNaker version.

        Parameters
        ----------
        projection : pyNN.Projection
            The projection to reconfigure.
        dopamine_scale : float, optional
            Dopamine scaling factor.  Default 1.0.
        """
        # sPyNNaker limitation: STDP parameters are typically fixed at
        # projection creation time.  This method documents the intended
        # behaviour and falls back to a population-wide average dopamine.
        if self.n_alive == 0:
            return

        avg_da = sum(s.dopamine_ema for s in self.states if s.is_alive)
        avg_da /= self.n_alive

        a_plus, a_minus = DopamineModulatedWeightDependence.modulated_parameters(
            base_a_plus=STDP_A_PLUS,
            base_a_minus=STDP_A_MINUS,
            dopamine_ema=avg_da,
            dopamine_scale=dopamine_scale,
        )

        # Attempt to update – may raise on older sPyNNaker versions
        try:
            projection.set(
                A_plus=a_plus,
                A_minus=a_minus,
            )
        except Exception as exc:
            warnings.warn(
                f"Could not update STDP parameters at runtime: {exc}. "
                "Consider recreating the projection with new amplitudes."
            )

    # ------------------------------------------------------------------
    # Batch orchestration helpers
    # ------------------------------------------------------------------

    def step_all_trophic(
        self,
        earned_map: Dict[int, float],
        retro_spent_map: Dict[int, float],
        degree_map: Dict[int, int],
        dt: float,
    ) -> None:
        """Run :py:meth:`PolypState.step_trophic` for all alive polyps.

        Parameters
        ----------
        earned_map : dict
            ``polyp_id -> earned_support`` mapping.
        retro_spent_map : dict
            ``polyp_id -> retrograde_spent`` mapping.
        degree_map : dict
            ``polyp_id -> out-degree`` mapping.
        dt : float
            Time step.
        """
        for state in self.states:
            if not state.is_alive:
                continue
            pid = state.polyp_id
            earned = earned_map.get(pid, 0.0)
            retro = retro_spent_map.get(pid, 0.0)
            degree = degree_map.get(pid, 0)
            state.step_trophic(earned, retro, degree, dt)

    def step_all_cyclin(self, dt: float) -> None:
        """Run :py:meth:`PolypState.step_cyclin` for all alive polyps."""
        for state in self.states:
            if state.is_alive:
                state.step_cyclin(dt)

    def step_all_bax(self, dt: float, post_handoff: bool = True) -> None:
        """Run :py:meth:`PolypState.step_bax` for all alive polyps.

        Uses each polyp's own ``directional_accuracy_ema``.
        """
        for state in self.states:
            if state.is_alive:
                state.step_bax(
                    accuracy_ema=state.directional_accuracy_ema,
                    dt=dt,
                    post_handoff=post_handoff,
                )

    def step_all_dopamine(
        self,
        raw_dopamine_map: Dict[int, float],
        dt_ms: float,
    ) -> None:
        """Run :py:meth:`PolypState.step_dopamine` for all alive polyps.

        Parameters
        ----------
        raw_dopamine_map : dict
            ``polyp_id -> raw_dopamine`` mapping.
        dt_ms : float
            Time step in milliseconds.
        """
        for state in self.states:
            if not state.is_alive:
                continue
            pid = state.polyp_id
            raw_da = raw_dopamine_map.get(pid, 0.0)
            state.step_dopamine(raw_da, dt_ms)

    def step_all_age(self) -> None:
        """Run :py:meth:`PolypState.step_age` for all alive polyps."""
        for state in self.states:
            if state.is_alive:
                state.step_age()

    def spawn_from_eligible_parents(self) -> List[int]:
        """Find all polyps that can reproduce and spawn one child each.

        Returns
        -------
        list of int
            Hardware neuron indices of all newly created children.
        """
        children: List[int] = []
        # Snapshot to avoid mutating while iterating
        eligible = [s for s in self.states if s.is_alive and s.can_reproduce]
        for parent in eligible:
            try:
                child_idx = self.add_polyp_from_parent(parent)
                children.append(child_idx)
            except RuntimeError:
                # Population full – stop spawning
                break
        return children

    # ------------------------------------------------------------------
    # House-keeping
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"PolypPopulation(label={self.label!r}, size={self.size}, "
            f"alive={self.n_alive}, dead={self.n_dead})"
        )

    def summary(self) -> Dict[str, object]:
        """Return a JSON-serialisable summary of the population state.

        Returns
        -------
        dict
            Keys: ``label``, ``size``, ``n_alive``, ``n_dead``,
            ``next_polyp_id``, ``mean_trophic``, ``mean_dopamine_ema``,
            ``mean_activity_rate``.
        """
        alive_states = self.get_alive_states()
        if not alive_states:
            return {
                "label": self.label,
                "size": self.size,
                "n_alive": 0,
                "n_dead": self.size,
                "next_polyp_id": self.next_polyp_id,
                "mean_trophic": 0.0,
                "mean_dopamine_ema": 0.0,
                "mean_activity_rate": 0.0,
            }

        n = len(alive_states)
        return {
            "label": self.label,
            "size": self.size,
            "n_alive": n,
            "n_dead": self.size - n,
            "next_polyp_id": self.next_polyp_id,
            "mean_trophic": sum(s.trophic_health for s in alive_states) / n,
            "mean_dopamine_ema": sum(s.dopamine_ema for s in alive_states) / n,
            "mean_activity_rate": sum(s.activity_rate for s in alive_states) / n,
        }
