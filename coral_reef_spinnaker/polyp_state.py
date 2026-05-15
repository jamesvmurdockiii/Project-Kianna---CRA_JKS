"""
Polyp state dataclasses and biological constants.

This module contains:
- Module-level biological constants (LIF defaults, trophic parameters,
  mutation rates, heritable trait lists).
- :class:`PolypState` — host-side auxiliary state for a single polyp
  microcircuit.
- :class:`PolypSummary` — lightweight read-only snapshot of a polyp's
  public state.
"""

from __future__ import annotations

import math
import random
import warnings
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

import numpy as np


# PyNN imports – these are only available when running on a SpiNNaker board
# or with the sPyNNaker simulator back-end.
try:
    import pyNN.spiNNaker as sim
    from pyNN.standardmodels.synapses import STDPWeightDependence
    HAVE_SPINNAKER = True
except Exception:  # pragma: no cover
    HAVE_SPINNAKER = False
    sim = None  # type: ignore[assignment]
    STDPWeightDependence = object  # type: ignore[misc,assignment]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# LIF parameter defaults chosen so that drive maps cleanly to firing rate
# via i_offset.  tau_m = 20 ms gives ~50 Hz max firing under strong drive.
DEFAULT_TAU_M_MS: float = 20.0
DEFAULT_V_REST_MV: float = -65.0
DEFAULT_V_RESET_MV: float = -70.0
DEFAULT_V_THRESH_MV: float = -55.0
DEFAULT_TAU_REFRAC_MS: float = 2.0
DEFAULT_CM_NF: float = 0.25  # nF – small for fast response

# Drive-to-current conversion: 1.0 drive unit -> this many nA of i_offset
DEFAULT_DRIVE_TO_CURRENT_NA: float = 2.0

# Neonatal excitability
NEONATAL_EXCITABILITY_PEAK: float = 0.5
SEED_OUTPUT_SCALE: float = 0.1

# Trophic / reproduction constants
CHILD_TROPHIC_SHARE: float = 0.5
DEFAULT_REPRODUCTION_THRESHOLD: float = 1.5
DEFAULT_CYC_THRESHOLD: float = 0.5  # G1/S checkpoint
DEFAULT_BDNF_RELEASE_RATE: float = 0.024
DEFAULT_BDNF_UPTAKE_EFFICIENCY: float = 0.5

# BAX / apoptosis constants
ACCURACY_FLOOR: float = 0.45
BAX_ACCUMULATION_RATE: float = 0.002

# Dopamine EMA time constant
DA_TAU_MS: float = 100.0

# Competitive readout: top max(3, int(sqrt(N))) neurons
MIN_READOUT_SIZE: int = 3

# Juvenile integration window (steps) – cleared by support-history, not just age
JUVENILE_WINDOW_STEPS: int = 50

# Log-normal mutation sigma (log-space)
MUTATION_SIGMA: float = 0.1
MUTATION_LOG_MIN: float = -10.0
MUTATION_LOG_MAX: float = 10.0

# Synapse type defaults
EXC_SYN_TAU_SYN_MS: float = 5.0
DA_SYN_TAU_SYN_MS: float = 10.0

# STDP timing defaults
STDP_TAU_PLUS_MS: float = 20.0
STDP_TAU_MINUS_MS: float = 20.0
STDP_A_PLUS: float = 0.01
STDP_A_MINUS: float = 0.01
STDP_W_MIN: float = 0.0
STDP_W_MAX: float = 1.0

# Heritable trait names – used for mutation and lineage tracking
HERITABLE_TRAITS: Tuple[str, ...] = (
    "metabolic_decay",
    "trophic_synapse_cost",
    "competitive_alpha",
    "sprouting_rate",
    "max_connectivity_factor",
    "construction_efficiency",
    "ff_formation_bias",
    "fb_formation_bias",
    "spatial_dispersion",
    "tau_chemical",
    "bdnf_release_rate",
    "bdnf_uptake_efficiency",
    "uptake_rate",
    "da_gain",
    "reproduction_threshold",
    "apoptosis_threshold",
)


# ---------------------------------------------------------------------------
# PolypState
# ---------------------------------------------------------------------------

@dataclass
class PolypState:
    """Host-side auxiliary state for a single polyp microcircuit.

    A polyp is no longer a single neuron but a microcircuit — a contiguous
    block of ``n_neurons_per_polyp`` LIF neurons within the parent
    ``PolypPopulation``.  This dataclass tracks the collective biological
    state of that microcircuit.

    Parameters
    ----------
    polyp_id : int
        Unique identifier within the colony.
    block_start : int
        Index of the first neuron in this polyp's block.
    block_end : int
        Index one past the last neuron in this polyp's block.
    n_neurons_per_polyp : int
        Size of the microcircuit (neurons per polyp).
    lineage_id : int
        Identifier shared by all polyps descended from a common ancestor.

    Attributes
    ----------
    trophic_health : float
        Scalar survival currency (0 = dead, >1 = can reproduce).
    metabolic_decay : float
        Baseline trophic decay rate (heritable).
    trophic_synapse_cost : float
        Per-synapse trophic cost (heritable).
    bax_activation : float
        Apoptosis driver from persistent local support deficit.
    apoptosis_threshold : float
        Heritable level parameter for death threshold.
    retrograde_spent : float
        Total retrograde support spent this step.
    earned_support : float
        Total support earned this step.
    cyclin_d : float
        Cell-cycle driver (Morgan 1995 G1/S checkpoint).
    cyclin_accumulation_rate : float
        Rate of cyclin-D accumulation when trophic > threshold.
    cyclin_degradation_rate : float
        Rate of cyclin-D degradation.
    reproduction_threshold : float
        Heritable trophic level required for reproduction.
    is_alive : bool
        False when ``trophic_health < apoptosis_threshold + bax``.
    is_juvenile : bool
        True until support-history integration window is complete.
    age_steps : int
        Number of simulation steps this polyp has lived.
    maternal_reserve_fraction : float
        1.0 pre-handoff, tracks reserve depletion.
    handoff_complete : bool
        True once maternal support handoff is finished.
    dopamine_ema : float
        Exponentially-weighted average of dopamine signal.
    dopamine_tau_ms : float
        Time constant (ms) for dopamine EMA.
    last_mi : float or None
        Last measured mutual information (bits).  ``None`` maps to warmup
        prior 1.0.
    uptake_rate : float
        Heritable rate for converting MI to trophic drive.
    da_gain : float
        Heritable gain for converting dopamine to drive.
    activity_rate : float
        Normalized firing rate (0-1).
    directional_accuracy_ema : float
        Tracks prediction accuracy (init 0.5, alpha=0.02).
    output_scale : float
        Current prediction scale (seed 0.1).
    last_raw_rpe : float
        Last reward prediction error.
    last_output_signed_contribution : float
        Signed contribution to colony readout.
    last_net_matured_consequence_credit : float
        Net matured delayed credit.
    competitive_alpha : float
        Heritable trait for competitive readout scaling.
    sprouting_rate : float
        Heritable rate for new synapse formation.
    max_connectivity_factor : int
        Heritable max out-degree multiplier.
    construction_efficiency : float
        Heritable synapse construction efficiency.
    ff_formation_bias : float
        Heritable feed-forward formation bias.
    fb_formation_bias : float
        Heritable feed-back formation bias.
    spatial_dispersion : float
        Heritable spatial spread for offspring placement.
    tau_chemical : float
        Heritable chemical signalling time constant.
    bdnf_release_rate : float
        Heritable BDNF release rate.
    bdnf_uptake_efficiency : float
        Heritable BDNF uptake efficiency.
    xyz : np.ndarray
        3-D spatial position of this polyp.
    direct_stream_mask : set
        Which external streams this polyp directly senses.
    """

    # Identity & microcircuit block
    polyp_id: int
    lineage_id: int
    slot_index: int = 0
    base_index: int = 0
    block_start: int = 0
    block_end: int = 32
    n_neurons_per_polyp: int = 32

    # Subgroup slices (hard-coded offsets in v1)
    input_slice: slice = field(default_factory=lambda: slice(0, 8))
    exc_slice: slice = field(default_factory=lambda: slice(8, 24))
    inh_slice: slice = field(default_factory=lambda: slice(24, 28))
    readout_slice: slice = field(default_factory=lambda: slice(28, 32))

    # Internal projection references (created at birth, never modified in v1)
    _internal_proj_exc: Optional[Any] = None
    _internal_proj_inh: Optional[Any] = None

    # Trophic ecology
    trophic_health: float = 1.0
    metabolic_decay: float = 0.005
    trophic_synapse_cost: float = 0.001
    bax_activation: float = 0.0
    apoptosis_threshold: float = 0.1
    retrograde_spent: float = 0.0
    earned_support: float = 0.0

    # Lifecycle
    cyclin_d: float = 0.001
    cyclin_accumulation_rate: float = 1.0
    cyclin_degradation_rate: float = 0.5
    reproduction_threshold: float = 1.5
    is_alive: bool = True
    is_juvenile: bool = True
    age_steps: int = 0
    maternal_reserve_fraction: float = 1.0
    handoff_complete: bool = False

    # Learning
    dopamine_ema: float = 0.0
    dopamine_tau_ms: float = 100.0
    last_mi: Optional[float] = None
    uptake_rate: float = 0.1
    da_gain: float = 0.5
    sensory_drive: float = 0.0
    activity_rate: float = 0.5  # NEONATAL_EXCITABILITY_PEAK
    directional_accuracy_ema: float = 0.5
    output_scale: float = 0.1  # SEED_OUTPUT_SCALE
    last_raw_rpe: float = 0.0
    last_output_signed_contribution: float = 0.0
    last_net_matured_consequence_credit: float = 0.0
    current_prediction: float = 0.0
    predictive_readout_weight: float = 0.25
    predictive_readout_bias: float = 0.0
    predictive_readout_lr_scale: float = 1.0
    last_prediction_feature: float = 0.0
    last_backend_prediction: float = 0.0

    # Structural traits (heritable)
    competitive_alpha: float = 0.1
    sprouting_rate: float = 0.01
    max_connectivity_factor: int = 5
    construction_efficiency: float = 0.5
    ff_formation_bias: float = 0.5
    fb_formation_bias: float = 0.3
    spatial_dispersion: float = 0.1
    tau_chemical: float = 100.0
    bdnf_release_rate: float = DEFAULT_BDNF_RELEASE_RATE
    bdnf_uptake_efficiency: float = DEFAULT_BDNF_UPTAKE_EFFICIENCY

    # Neural device parameters (heritable via lifecycle)
    # These scale the base config LIF parameters per-polyp, allowing
    # evolution to produce genuinely different computational properties.
    tau_m_factor: float = 1.0
    """Multiplier for membrane time constant tau_m (lower = faster integration)."""
    v_thresh_factor: float = 1.0
    """Multiplier for firing threshold v_thresh (lower = more excitable)."""
    cm_factor: float = 1.0
    """Multiplier for membrane capacitance cm (higher = slower, more stable)."""

    # Stream specialization (heritable via lifecycle)
    stream_mask_coverage: float = 1.0
    """Heritable fraction of input channels the polyp attends to (0.2-1.0)."""
    stream_attention_mask: Set[int] = field(default_factory=lambda: set(range(8)))
    """Computed from coverage: which specific input channel indices the
    polyp's input neurons receive.  Different polyps attend to different
    channels, creating orthogonal response subspaces."""

    # Variable neuron allocation (heritable via lifecycle)
    n_input_alloc: int = 8
    """Number of input neurons in this polyp's 32-neuron block."""
    n_exc_alloc: int = 16
    """Number of excitatory neurons in this polyp's 32-neuron block."""
    n_inh_alloc: int = 4
    """Number of inhibitory neurons in this polyp's 32-neuron block."""
    n_readout_alloc: int = 4
    """Number of readout neurons (always 32 - sum of others, must be >= 1)."""

    # Heritable allocation ratios (the fractional source of n_*_alloc)
    input_allocation_ratio: float = 0.25
    """Heritable fraction of 32 neurons allocated to input."""
    exc_allocation_ratio: float = 0.5
    """Heritable fraction of 32 neurons allocated to excitatory."""
    inh_allocation_ratio: float = 0.125
    """Heritable fraction of 32 neurons allocated to inhibitory."""

    # Temporal specialization (heritable via lifecycle)
    temporal_lag: int = 0
    """Heritable temporal lag index for per-polyp sensory history reading.
    Polyp reads sensory_history[-(lag+1)] instead of current value."""

    # Operator diversity — per-polyp dynamical regime (heritable)
    spectral_radius: float = 1.0
    """Heritable E->E recurrent weight spectral radius. <1 = contractive,
    =1 = critical, >1 = expansive/chaotic edge."""
    ei_ratio: float = 1.0
    """Heritable I->E inhibitory strength multiplier. >1 = stable/damped,
    <1 = excitable/oscillatory."""

    # Functional caste (heritable via lifecycle)
    caste_type: int = 0
    """Heritable functional caste: 0=filter, 1=memory, 2=rotor, 3=chaotic, 4=stabilizer.
    Determines initial spectral_radius and ei_ratio ranges."""

    # Signal export interface — bounded, compressive transport
    export_activity: float = 0.0
    """Bounded export: activity_rate → sigmoid (0,1)."""
    export_prediction: float = 0.0
    """Bounded export: current_prediction → tanh (-1,1)."""
    export_uncertainty: float = 0.0
    """Bounded export: 1-accuracy → sigmoid (0,1)."""
    export_energy: float = 0.0
    """Bounded export: trophic_health/20 → sigmoid (0,1)."""
    export_novelty: float = 0.0
    """Bounded export: abs(last_raw_rpe) → tanh (-1,1)."""

    # Energy economy — explicit per-polyp energy variable
    energy_reserve: float = 0.5
    """Per-polyp energy reserve [0,1]. Gains from prediction usefulness,
    loses from metabolic cost and complexity. Drives survival decisions."""

    # Developmental maturation stages (replaces "freezing")
    maturation_stage: int = 0
    """Developmental stage: 0=larval(exploratory,high plasticity),
    1=juvenile(stabilizing), 2=mature(calcified,reliable),
    3=senescent(recycling). Energy determines progression."""

    # Learned synaptic weights (snapshotted before rebuild, inheritable)
    _learned_exc_weights: Optional[Dict[Tuple[int, int], float]] = None
    """Snapshot of excitatory projection weights (local_pre, local_post)->weight."""
    _learned_inh_weights: Optional[Dict[Tuple[int, int], float]] = None
    """Snapshot of inhibitory projection weights (local_pre, local_post)->weight."""
    _init_exc_conns: Optional[List[Tuple[int, int, float, float]]] = None
    """Stored excitatory connection list for rebuild/inheritance."""
    _init_inh_conns: Optional[List[Tuple[int, int, float, float]]] = None
    """Stored inhibitory connection list for rebuild/inheritance."""

    # Spatial position (3D)
    xyz: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=float))

    # Structural / consolidation state
    calcification: float = 0.0
    gate_activity: float = 0.0

    # Stream specialization
    direct_stream_mask: Set[Any] = field(default_factory=set)

    # Support history for juvenile maturity estimation
    support_history: Deque[float] = field(default_factory=lambda: deque(maxlen=1000))

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def last_mi_or_zero(self) -> float:
        """Return last MI or 1.0 warmup prior when ``last_mi`` is None.

        During the initial warmup phase (before the first mutual-information
        estimate is computed) the drive calculation falls back to a prior
        value of 1.0, keeping neonatal polyps moderately active.
        """
        return 1.0 if self.last_mi is None else float(self.last_mi)

    @property
    def effective_decay(self) -> float:
        """Effective trophic decay rate.

        ``effective_decay = metabolic_decay + trophic_synapse_cost * degree``

        The ``degree`` term is *not* stored inside ``PolypState``; it is
        supplied externally by the graph manager (see
        :py:meth:`step_trophic`).  This property therefore returns the
        baseline ``metabolic_decay`` only.
        """
        return self.metabolic_decay

    @property
    def can_reproduce(self) -> bool:
        """G1/S checkpoint: cyclin_d >= threshold AND trophic sufficient.

        A polyp can reproduce only when:
        1. ``cyclin_d`` has accumulated to at least ``cyclin_threshold``
           (0.5 by default).
        2. ``trophic_health`` is above ``reproduction_threshold``.
        3. The polyp is no longer juvenile.
        4. Maternal handoff is complete.

        Returns
        -------
        bool
        """
        return (
            self.cyclin_d >= DEFAULT_CYC_THRESHOLD
            and self.trophic_health >= self.reproduction_threshold
            and not self.is_juvenile
            and self.handoff_complete
        )

    @property
    def death_risk(self) -> float:
        """BAX-driven apoptosis threshold.

        The polyp dies when ``trophic_health`` falls below
        ``apoptosis_threshold + bax_activation``.  This property returns
        the current combined threshold value.

        Returns
        -------
        float
        """
        return self.apoptosis_threshold + self.bax_activation

    # ------------------------------------------------------------------
    # Step methods – called by the orchestrator once per simulation cycle
    # ------------------------------------------------------------------

    def step_trophic(
        self,
        earned: float,
        retro_spent: float,
        degree: int,
        dt: float,
    ) -> None:
        """Update trophic health per the CRA equation.

        ``trophic[t+1] = (trophic[t] - retro_spent + earned)
                         * exp(-effective_decay * dt)``

        where ``effective_decay = metabolic_decay + trophic_synapse_cost * degree``.

        Parameters
        ----------
        earned : float
            Total support earned this step (from incoming synapses).
        retro_spent : float
            Total retrograde support spent on outgoing synapses.
        degree : int
            Current out-degree (number of outgoing synapses).
        dt : float
            Simulation time step in *seconds* (or same time unit as decay
            rates).
        """
        decay = self.metabolic_decay + self.trophic_synapse_cost * float(degree)
        new_trophic = (self.trophic_health - retro_spent + earned) * math.exp(
            -decay * dt
        )
        self.trophic_health = float(new_trophic)
        self.retrograde_spent = float(retro_spent)
        self.earned_support = float(earned)

        # Death check
        if self.trophic_health < self.death_risk:
            self.is_alive = False

    def step_cyclin(self, dt: float) -> None:
        """Update cyclin-D: accumulation when trophic > threshold, degradation always.

        Cyclin-D implements the Morgan (1995) G1/S cell-cycle checkpoint.
        When trophic health exceeds ``reproduction_threshold``, cyclin-D
        accumulates linearly; it degrades exponentially at all times.

        Parameters
        ----------
        dt : float
            Time step.
        """
        if self.trophic_health > self.reproduction_threshold:
            self.cyclin_d += self.cyclin_accumulation_rate * dt
        self.cyclin_d -= self.cyclin_degradation_rate * self.cyclin_d * dt
        if self.cyclin_d < 0.0:
            self.cyclin_d = 0.0

    def step_bax(
        self,
        accuracy_ema: float,
        dt: float,
        post_handoff: bool = True,
    ) -> None:
        """BAX accumulation from persistent local deficit and accuracy.

        Following Katz & Shatz (1996), incorrect connections are pruned
        via competition.  BAX (the apoptosis driver) accumulates when the
        polyp's directional accuracy EMA remains below ``ACCURACY_FLOOR``
        (0.45) after maternal handoff.

        ``bax[t+1] = bax[t] + max(0, 0.002 * (0.45 - accuracy_ema)) * dt``

        Parameters
        ----------
        accuracy_ema : float
            Current directional-accuracy EMA for this polyp.
        dt : float
            Time step.
        post_handoff : bool, optional
            If ``False``, BAX accumulation is suppressed (pre-handoff
            polyps are protected).  Default is ``True``.
        """
        if post_handoff and accuracy_ema < ACCURACY_FLOOR:
            self.bax_activation += BAX_ACCUMULATION_RATE * (
                ACCURACY_FLOOR - accuracy_ema
            ) * dt
        if self.bax_activation < 0.0:
            self.bax_activation = 0.0

    def step_dopamine(self, raw_dopamine: float, dt_ms: float) -> None:
        """EMA update for dopamine: drives STDP and trophic.

        The dopamine EMA follows a standard first-order low-pass filter:

        ``ema[t+1] = ema[t] + alpha * (raw - ema[t])``

        where ``alpha = dt_ms / dopamine_tau_ms``.

        Parameters
        ----------
        raw_dopamine : float
            Instantaneous dopamine signal (e.g. reward prediction error).
        dt_ms : float
            Time step in milliseconds.
        """
        alpha = dt_ms / self.dopamine_tau_ms
        # Clamp alpha for stability
        alpha = max(0.0, min(1.0, alpha))
        self.dopamine_ema += alpha * (raw_dopamine - self.dopamine_ema)

    def step_accuracy(self, target: float, prediction: float) -> None:
        """Update the directional-accuracy EMA.

        Parameters
        ----------
        target : float
            Ground-truth directional target (e.g. optimal portfolio
            weight or true label).
        prediction : float
            This polyp's current prediction.
        """
        # Binary accuracy for this step
        step_accuracy = 1.0 - abs(target - prediction)
        # Clamp to [0, 1]
        step_accuracy = max(0.0, min(1.0, step_accuracy))
        alpha = 0.02
        self.directional_accuracy_ema += alpha * (
            step_accuracy - self.directional_accuracy_ema
        )

    def step_age(self) -> None:
        """Increment age and potentially clear juvenile status.

        The juvenile flag is cleared either by completing the support-
        history integration window (``JUVENILE_WINDOW_STEPS`` steps) or
        by an explicit signal from the orchestrator when sufficient
        support history has been accumulated.
        """
        self.age_steps += 1
        if self.is_juvenile and self.age_steps >= JUVENILE_WINDOW_STEPS:
            self.is_juvenile = False

    def compute_drive(self) -> float:
        """Compute the total drive that determines firing rate.

        ``drive = last_mi * uptake_rate + da_gain * dopamine_ema``

        The drive is clipped to be non-negative and is mapped to an
        ``i_offset`` current injection by :py:class:`PolypNeuronType`.

        Returns
        -------
        float
            Non-negative drive value.
        """
        drive = (
            self.last_mi_or_zero * self.uptake_rate
            + self.da_gain * self.dopamine_ema
            + self.sensory_drive
        )
        return max(0.0, float(drive))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def inherit_traits(self, parent: PolypState) -> None:
        """Bounded reflected mutation for heritable traits.

        The child receives each heritable trait from the parent with
        log-normal variation:

        ``child_val = exp( clamp( log(parent_val) + N(0, sigma), min, max ) )``

        Trophic health is split: the child receives
        ``CHILD_TROPHIC_SHARE`` (50 %) and the parent retains the rest.
        Stream masks are inherited with possible broadening.

        Parameters
        ----------
        parent : PolypState
            The parent polyp whose traits (and trophic reserve) are
            being inherited.
        """
        for attr in HERITABLE_TRAITS:
            parent_val = getattr(parent, attr)
            # Ensure positive before log
            safe_val = max(float(parent_val), 1e-12)
            log_val = math.log(safe_val)
            mutation = random.gauss(0.0, MUTATION_SIGMA)
            new_log = max(MUTATION_LOG_MIN, min(MUTATION_LOG_MAX, log_val + mutation))
            setattr(self, attr, math.exp(new_log))

        # Split trophic reserve
        child_share = parent.trophic_health * CHILD_TROPHIC_SHARE
        self.trophic_health = float(child_share)
        parent.trophic_health *= 1.0 - CHILD_TROPHIC_SHARE

        # Inherit stream masks with possible broadening
        inherited_streams: Set[int] = set(parent.direct_stream_mask)
        self.direct_stream_mask = inherited_streams


# ---------------------------------------------------------------------------
# PolypSummary
# ---------------------------------------------------------------------------

@dataclass
class PolypSummary:
    """Summarized readout from one polyp microcircuit after a simulation step.

    This is the **only** interface between the microcircuit backend and the
    polyp-level ecology / learning / graph layers.  All downstream decisions
    (WTA, trophic allocation, reproduction, edge pruning) use these scalars.
    """

    polyp_id: int

    # Per-subgroup firing rates (normalized to [0, 1])
    input_rate: float = 0.0
    exc_rate: float = 0.0
    inh_rate: float = 0.0
    readout_rate: float = 0.0

    # Colony-facing signals
    activity_rate: float = 0.0      # alias for readout_rate
    prediction: float = 0.0         # tanh(output_scale * (rate_r0 - rate_r1))
    confidence: float = 0.0         # clip(max_rate / (mean_rate + eps), 0, 1)

    # Diagnostic
    n_spikes_total: int = 0


# ---------------------------------------------------------------------------
# DopamineModulatedWeightDependence
# ---------------------------------------------------------------------------
