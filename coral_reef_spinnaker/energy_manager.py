"""
Energy Manager for Coral Reef Architecture on SpiNNaker.

Implements the scalar trophic-health economy with three capture channels:
- Sensory: MI-driven exogenous food from external streams
- Outcome: task-consequence food from positive matured credit
- Retrograde: BDNF-like causal mutualism on active edges

All allocation uses pro-rata capacity reconciliation so no channel
starves another. This is the core selection mechanism — there is NO
backpropagation. Polyps survive or die based on earned support.

The energy manager runs HOST-SIDE (Python) between SpiNNaker runs.
It operates on PolypState objects and ReefEdge topology, computing
the three-channel support allocation each step.

References:
- Levi-Montalcini (1987), Oppenheim (1991) neurotrophic theory
- Katz & Shatz (1996) activity-dependent development
- Bhattacharya (2012), Barres (1992) astrocyte BDNF
- Craik & Bialek (2006) normative sensory coding
- Adams & MacKay (2007) Bayesian online changepoint detection (BOCPD)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict, deque
import numpy as np
import math

# ---------------------------------------------------------------------------
# Tag constants — marked with biological origin or engineering rationale
# ---------------------------------------------------------------------------

# --- biology_derived ---
DEFAULT_METABOLIC_DECAY: float = 0.005
"""Heritable base metabolic decay rate.

Derived from cortical neuron ATP consumption rates:
~4.7 billion ATP molecules per second per neuron (Attwell & Laughlin, 2001).
Scaled to dimensionless simulation units. See module docstring.
"""

DEFAULT_TROPHIC_SYNAPSE_COST: float = 0.001
"""Heritable per-synapse trophic maintenance cost.

Models synaptic transmission energy (~10^7 ATP per vesicle release)
and protein turnover at the synapse (Harris & Weinberg, 2012).
"""

DEFAULT_APOPTOSIS_THRESHOLD: float = 0.1
"""Trophic-health level below which apoptosis is triggered.

Based on developmental neurobiology: ~50% of neurons die by apoptosis
when target-derived trophic support is insufficient (Oppenheim, 1991;
Raff et al., 1993). Threshold is tuned to produce comparable selection
pressure in simulation units.
"""

DEFAULT_BDNF_RELEASE_RATE: float = 0.024
"""Heritable BDNF (brain-derived neurotrophic factor) release rate.

Derived from measured BDNF secretion rates in cultured hippocampal
    neurons: ~1-5 ng/mL per 24h (Balkowiec & Katz, 2000; Bhattacharya
    et al., 2012). Converted to dimensionless simulation units. This value
    matches ``EnergyConfig.bdnf_per_trophic_source``.
"""

DEFAULT_BDNF_UPTAKE_EFFICIENCY: float = 0.5
"""Heritable BDNF uptake efficiency.

Models TrkB receptor-mediated endocytosis efficiency. Uptake varies
with activity levels (Nagappan & Lu, 2005). 0.5 is a baseline for
moderately active synapses.
"""

DEFAULT_DA_GAIN: float = 0.5
"""Heritable dopaminergic gain on sensory drive.

Scales the influence of dopamine-EMA on sensory capture claims.
Reflects midbrain dopamine projection strength onto cortical targets
(Schultz, 2015). Stronger gain = more dopamine-dependent motivation.
"""

# --- ENGINEERING ---
MAX_RETROGRADE_CANDIDATES: int = 24
"""Maximum number of fallback candidates for retrograde when spatial
hash returns no local results. This bounds the O(N^2) fallback to
ensure step time remains predictable on SpiNNaker host side."""

BOCPD_PLASTICITY_TEMP_MULTIPLIER: float = 2.5
"""Multiplier on plasticity temperature when BOCPD changepoint
probability exceeds threshold. Higher temperature unlocks
calcification, allowing structural plasticity during regime change."""

BOCPD_CHANGPOINT_THRESHOLD: float = 0.5
"""Threshold on changepoint probability to trigger elevated plasticity."""

MIN_REPRODUCTION_SUPPORTABILITY_RATIO: float = 1.05
"""Minimum ratio of local supportable to survival cost for reproduction.

Ensures reproduction only occurs when the local environment can
support >1 polyp at survival cost, preventing Malthusian collapse."""

DEFAULT_REPRODUCTION_THRESHOLD: float = 1.5
"""Default (heritable) trophic-health threshold for reproduction eligibility."""

DEFAULT_MATERNAL_SURVIVAL_FRACTION: float = 0.5
"""Fraction of maternal reserve allocated to survival floor during
developmental autonomy phase. Reserve is split geometrically at
each cleavage-like division event."""

RETROGRADE_ACTIVITY_THRESHOLD: float = 0.01
"""Minimum gate_activity for a polyp to be considered active for
retrograde release eligibility."""

SENSORY_CLAIM_MIN_DRIVE: float = 1e-9
"""Minimum drive value for a sensory claimant to be included.
Prevents division-by-zero and numerical noise."""

MATERNAL_DEPLETION_SAFETY_EPS: float = 1e-12
"""Safety epsilon for maternal reserve depletion comparisons."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class EnergyPolypStepState:
    """Per-polyp cache for one energy step.

    This dataclass holds all intermediate quantities computed for a single
    polyp during one energy allocation step. It serves as both a working
    scratchpad for the three-channel allocation and as a diagnostic record
    for post-step telemetry.

    Attributes:
        polyp_id: Unique identifier for this polyp.
        degree: Number of incoming synapses (in-degree).
        calcification: Current calcification level (structural rigidity).
        gate_activity: Recent firing-rate / gate activity.
        local_capacity: Local trophic capacity ceiling for this step.
        mi: Mutual information of the polyp's direct stream (0 if none).
        is_adult: True if polyp has passed handoff and is not juvenile.
        is_direct_sensor: True if polyp receives from an external stream.
        sensory_budget_raw: Raw sensory capture before reconciliation.
        outcome_budget_raw: Raw outcome capture before reconciliation.
        retrograde_budget_raw: Raw retrograde capture before reconciliation.
        total_earned: Sum of all channels after reconciliation.
        retrograde_spent: Amount this polyp spent on outgoing retrograde.
        positive_matured_credit: Gross positive matured credit (for outcome).
        net_matured_credit: Net (positive - negative) matured credit.
    """
    polyp_id: int
    degree: int
    calcification: float
    gate_activity: float
    local_capacity: float
    mi: float
    is_adult: bool
    is_direct_sensor: bool
    sensory_budget_raw: float = 0.0
    outcome_budget_raw: float = 0.0
    retrograde_budget_raw: float = 0.0
    total_earned: float = 0.0
    retrograde_spent: float = 0.0
    positive_matured_credit: float = 0.0
    net_matured_credit: float = 0.0


@dataclass
class EnergyResult:
    """Result of one energy step for the whole colony.

    Mirrors the CRA EnergyResult specification with comprehensive
    per-channel telemetry, maternal reserve status, death and
    reproduction events, and bottleneck diagnostics. All monetary
    quantities are in dimensionless *trophic units* (TU).

    Per-channel quantities (raw = before capacity reconciliation;
    final = after pro-rata scaling):
        sensory_total_raw: Sum of raw sensory capture across all polyps.
        sensory_total_final: Sum of final sensory capture.
        sensory_budgets: Dict stream -> per-stream budget amount.
        outcome_total_raw: Sum of raw outcome capture.
        outcome_total_final: Sum of final outcome capture.
        outcome_budget_total: Total outcome budget minted.
        outcome_budget_source: One of "task_signal", "matured_consequence", "none".
        outcome_zero_reason: Human-readable reason if budget is zero.
        retrograde_total_raw: Sum of raw retrograde capture.
        retrograde_total_final: Sum of final retrograde capture.
        retrograde_total_spent: Total trophic spent by senders.
        retrograde_bottleneck: What limited retrograde (e.g. "no_active_receivers").

    Maternal reserve:
        maternal_trophic_fraction: Remaining trophic reserve fraction.
        maternal_atp_fraction: Remaining ATP reserve fraction.
        maternal_is_exhausted: True if reserve is depleted.
        maternal_support_total: Total support provided this step.
        handoff_triggered: True if handoff condition met this step.

    Death and reproduction:
        deaths: List of polyp_ids that died this step.
        reproductions: List of polyp_ids eligible for reproduction.
        bax_activations: Dict polyp_id -> bax level.

    Capacity and calibration:
        capacity_exceeded_count: Number of polyps exceeding local capacity.
        total_capacity_ceiling: Sum of all local capacity ceilings.
        bocpd_changepoint_prob: Changepoint probability this step.
        plasticity_temperature: Effective plasticity temperature.

    Cache and diagnostics:
        polyp_step_states: Dict polyp_id -> EnergyPolypStepState.
        step_num: Simulation step number.
        dt: Time step size.
        colony_size: Number of polyps.
        total_support_consumed: Sum of all final support across all polyps.
    """
    # Sensory channel
    sensory_total_raw: float = 0.0
    sensory_total_final: float = 0.0
    sensory_budgets: Dict[str, float] = field(default_factory=dict)
    sensory_num_claimants: int = 0
    sensory_num_streams_with_budget: int = 0

    # Outcome channel
    outcome_total_raw: float = 0.0
    outcome_total_final: float = 0.0
    outcome_budget_total: float = 0.0
    outcome_budget_source: str = "none"
    outcome_zero_reason: str = ""
    outcome_num_claimants: int = 0
    outcome_num_positive_adults: int = 0
    outcome_num_net_positive_adults: int = 0

    # Retrograde channel
    retrograde_total_raw: float = 0.0
    retrograde_total_final: float = 0.0
    retrograde_total_spent: float = 0.0
    retrograde_num_active_receivers: int = 0
    retrograde_num_active_senders: int = 0
    retrograde_bottleneck: str = ""

    # Maternal reserve
    maternal_trophic_fraction: float = 1.0
    maternal_atp_fraction: float = 1.0
    maternal_is_exhausted: bool = False
    maternal_support_total: float = 0.0
    handoff_triggered: bool = False
    developmental_subsidy_active: bool = False

    # Death and reproduction
    deaths: List[int] = field(default_factory=list)
    reproductions: List[int] = field(default_factory=list)
    bax_activations: Dict[int, float] = field(default_factory=dict)
    cyclin_values: Dict[int, float] = field(default_factory=dict)

    # Capacity and BOCPD
    capacity_exceeded_count: int = 0
    total_capacity_ceiling: float = 0.0
    bocpd_changepoint_prob: float = 0.0
    plasticity_temperature: float = 1.0

    # Diagnostics
    polyp_step_states: Dict[int, EnergyPolypStepState] = field(default_factory=dict)
    step_num: int = 0
    dt: float = 0.0
    colony_size: int = 0
    total_support_consumed: float = 0.0

    # Snapshot of colony-average quantities
    mean_trophic_health: float = 0.0
    mean_calcification: float = 0.0
    mean_bax: float = 0.0

    # Convenience flags
    any_death: bool = False
    any_reproduction: bool = False
    reserve_depleted_this_step: bool = False


@dataclass
class MaternalReserve:
    """Finite maternal reserve for pre-handoff developmental support.

    Before the maternal-to-autonomous handoff, the founder provides a
    finite trophic and ATP reserve that only depletes — never replenishes.
    This models the yolk-to-larva transition in biological development
    (Davit-Beal et al., 2009; Needham, 1942) and the finite nutrient
    stores available to a developing embryo before it must feed itself.

    Attributes:
        trophic_reserve: Current trophic reserve remaining (dimensionless TU).
        atp_reserve: Current ATP reserve remaining (TU).
        initial_trophic: Initial trophic reserve at founding (for telemetry).
        initial_atp: Initial ATP reserve at founding (for telemetry).
        is_exhausted: True when both reserves are effectively zero.
    """
    trophic_reserve: float
    atp_reserve: float
    initial_trophic: float
    initial_atp: float
    is_exhausted: bool = False

    def deplete_trophic(self, amount: float) -> float:
        """Spend trophic reserve, returning the actual amount spent.

        If the request exceeds available reserve, spends all remaining
        reserve and returns only the depleted amount.

        Args:
            amount: Requested trophic amount to spend (must be >= 0).

        Returns:
            Actual amount of trophic spent (<= requested amount).
        """
        if amount <= 0 or self.is_exhausted:
            return 0.0
        actual = min(amount, self.trophic_reserve)
        self.trophic_reserve -= actual
        if self.trophic_reserve <= MATERNAL_DEPLETION_SAFETY_EPS:
            self.trophic_reserve = 0.0
            self._check_exhausted()
        return actual

    def deplete_atp(self, amount: float) -> float:
        """Spend ATP reserve, returning the actual amount spent.

        Args:
            amount: Requested ATP amount to spend (must be >= 0).

        Returns:
            Actual amount of ATP spent (<= requested amount).
        """
        if amount <= 0 or self.is_exhausted:
            return 0.0
        actual = min(amount, self.atp_reserve)
        self.atp_reserve -= actual
        if self.atp_reserve <= MATERNAL_DEPLETION_SAFETY_EPS:
            self.atp_reserve = 0.0
            self._check_exhausted()
        return actual

    def _check_exhausted(self) -> None:
        """Update is_exhausted flag if both reserves are depleted."""
        if self.trophic_reserve <= MATERNAL_DEPLETION_SAFETY_EPS and \
           self.atp_reserve <= MATERNAL_DEPLETION_SAFETY_EPS:
            self.is_exhausted = True

    @property
    def trophic_fraction(self) -> float:
        """Fraction of trophic reserve remaining (1.0 = full, 0.0 = empty)."""
        if self.initial_trophic <= 0:
            return 0.0
        return self.trophic_reserve / self.initial_trophic

    @property
    def atp_fraction(self) -> float:
        """Fraction of ATP reserve remaining (1.0 = full, 0.0 = empty)."""
        if self.initial_atp <= 0:
            return 0.0
        return self.atp_reserve / self.initial_atp

    def can_fund(self, amount: float) -> bool:
        """Check whether reserve can fund the requested amount.

        Args:
            amount: Trophic amount requested.

        Returns:
            True if trophic_reserve >= amount.
        """
        return self.trophic_reserve >= amount


# Canonical TaskOutcomeSurface lives in trading_bridge.py.
from .trading_bridge import TaskOutcomeSurface


# Canonical EnergyConfig — imported from config.py (single source of truth)
from .config import EnergyConfig


# ---------------------------------------------------------------------------
# PolypState interface (stub — defined in polyp_neuron.py)
# ---------------------------------------------------------------------------

@dataclass
class PolypState:
    """Interface stub for the PolypState dataclass defined in polyp_neuron.py.

    The real PolypState lives in the polyp_neuron module. This stub is
    included here so the energy manager can type-check against it without
    creating a circular import. In production, import from polyp_neuron.

    Key invariants:
    - trophic_health is in [0, +inf); death occurs when it falls below
      apoptosis_threshold + bax_activation.
    - metabolic_decay and trophic_synapse_cost are heritable traits.
    - maternal_reserve_fraction tracks how much developmental subsidy
      this polyp still receives (1.0 = full subsidy).
    - direct_stream_mask contains stream names this polyp directly senses.
    """
    polyp_id: int
    lineage_id: int
    trophic_health: float = 1.0
    metabolic_decay: float = DEFAULT_METABOLIC_DECAY
    trophic_synapse_cost: float = DEFAULT_TROPHIC_SYNAPSE_COST
    bax_activation: float = 0.0
    apoptosis_threshold: float = DEFAULT_APOPTOSIS_THRESHOLD
    earned_support: float = 0.0
    cyclin_d: float = 0.001
    reproduction_threshold: float = DEFAULT_REPRODUCTION_THRESHOLD
    is_alive: bool = True
    is_juvenile: bool = True
    age_steps: int = 0
    maternal_reserve_fraction: float = 1.0
    handoff_complete: bool = False
    dopamine_ema: float = 0.0
    last_mi: Optional[float] = None
    uptake_rate: float = 0.1
    da_gain: float = DEFAULT_DA_GAIN
    activity_rate: float = 0.5
    directional_accuracy_ema: float = 0.5
    bdnf_release_rate: float = DEFAULT_BDNF_RELEASE_RATE
    bdnf_uptake_efficiency: float = DEFAULT_BDNF_UPTAKE_EFFICIENCY
    direct_stream_mask: Set[str] = field(default_factory=set)
    calcification: float = 0.0
    gate_activity: float = 0.0

    def compute_drive(self) -> float:
        """Compute sensory drive for claim-strength weighting.

        Drive = MI * uptake_rate + da_gain * dopamine_ema

        Higher drive = stronger claim on sensory budget.

        Returns:
            Scalar drive value (>= 0).
        """
        mi = self.last_mi if self.last_mi is not None else 0.0
        return max(0.0, mi * self.uptake_rate + self.da_gain * self.dopamine_ema)


# ---------------------------------------------------------------------------
# EnergyManager — core trophic economy
# ---------------------------------------------------------------------------


class EnergyManager:
    """Core trophic economy for the Coral Reef Architecture.

    The EnergyManager implements the three-channel scalar trophic-health
    economy that is the sole selection mechanism in the CRA. There is NO
    backpropagation and NO global loss. Each polyp earns support through:

        1. Sensory capture   — MI-driven food from external streams
        2. Outcome capture   — task-consequence food from positive credit
        3. Retrograde capture — BDNF-like causal mutualism on active edges

    After computing raw captures for all three channels independently, a
    pro-rata capacity reconciliation scales all channels proportionally
    if the total exceeds the local trophic capacity ceiling. This prevents
    sensory-first starvation — all channels share the same ceiling.

    Before maternal handoff, a finite maternal reserve provides
    developmental support that only depletes. Handoff triggers when the
    reserve can no longer fund one developmental-support tick. After
    handoff, each polyp earns its own support through the three channels.

    The energy manager runs HOST-SIDE (Python) between SpiNNaker runs.
    It operates on PolypState objects and edge topology, returning an
    EnergyResult with full diagnostic telemetry each step.

    Key invariants:
        1. Sensory food ONLY from external streams (no internal helpers).
        2. Outcome budget uses strict net-positive gating.
        3. All three channels reconciled pro-rata against local capacity.
        4. Maternal reserve only depletes — finite embryonic store.
        5. Death is absolute per-polyp, not colony-global ratio.
        6. Retrograde is receiver-spent, not a colony-wide pool.

    Attributes:
        config: EnergyConfig with colony-wide parameters.
        n_streams: Number of external input streams.
        maternal_reserve: MaternalReserve instance (or None post-handoff).
        _step_cache: Dict polyp_id -> EnergyPolypStepState for current step.
        _telemetry_history: deque of recent EnergyResult summaries.
        _bocpd_state: Internal BOCPD state for changepoint detection.
    """

    # --- Internal stream names to EXCLUDE from trophic food ---
    _EXCLUDED_STREAM_NAMES: Set[str] = {
        "_temporal", "asset", "stream_context",
    }

    def __init__(self, config: EnergyConfig, n_streams: int) -> None:
        """Initialize the EnergyManager.

        Args:
            config: EnergyConfig with colony-wide parameters.
            n_streams: Number of external input streams.
        """
        self.config: EnergyConfig = config
        self.n_streams: int = n_streams
        self.maternal_reserve: Optional[MaternalReserve] = None

        # Step cache: polyp_id -> EnergyPolypStepState
        self._step_cache: Dict[int, EnergyPolypStepState] = {}

        # Rolling telemetry history (bounded memory for diagnostics)
        self._telemetry_history: deque = deque(maxlen=1000)

        # BOCPD state: simple run-length based changepoint probability
        # (simplified from Adams & MacKay 2007; full BOCPD lives elsewhere)
        self._bocpd_state: Dict[str, any] = {
            "run_length": 0,
            "predictive_mean": 0.0,
            "predictive_var": 1.0,
            "hazard_rate": 1.0 / 100.0,  # ENGINEERING: prior hazard
        }

        # Internal accumulators for one step
        self._last_sensory_raw: Dict[int, float] = {}
        self._last_outcome_raw: Dict[int, float] = {}
        self._last_retro_raw: Dict[int, float] = {}
        self._last_sensory_final: Dict[int, float] = {}
        self._last_outcome_final: Dict[int, float] = {}
        self._last_retro_final: Dict[int, float] = {}

        # Budget diagnostics
        self._outcome_budget_source: str = "none"
        self._outcome_zero_reason: str = ""
        self._retrograde_bottleneck: str = ""

    # =====================================================================
    # Core step
    # =====================================================================

    def step(self,
             polyp_states: List[PolypState],
             edges: Dict[Tuple[int, int], any],
             stream_mi: Dict[str, float],
             task_outcome: TaskOutcomeSurface,
             matured_consequence: Tuple[float, float],
             dt: float,
             step_num: int) -> EnergyResult:
        """Execute one complete energy allocation step for the colony.

        This is the main entry point called once per simulation step.
        It:
            1. Builds per-polyp step cache
            2. Computes the three-channel budget and allocations
            3. Reconciles pro-rata against local capacity ceilings
            4. Handles maternal reserve (pre-handoff) or adult ecology
            5. Updates trophic health, cyclin-D, and BAX for all polyps
            6. Checks death and reproduction conditions
            7. Returns a fully populated EnergyResult

        Args:
            polyp_states: List of all PolypState objects in the colony.
            edges: Dict mapping (src_id, dst_id) -> ReefEdge objects.
                   Each edge must have at minimum: weight (float),
                   is_active (bool), causal_contribution (float, optional).
            stream_mi: Dict mapping stream_name -> mutual information (float).
                       Only external streams; internal streams excluded later.
            task_outcome: TaskOutcomeSurface with immediate and matured signals.
            matured_consequence: Tuple of (gross_positive, net_positive) from
                                 the matured consequence ledger.
            dt: Simulation time step (dimensionless).
            step_num: Current simulation step number (for diagnostics).

        Returns:
            EnergyResult with full per-step telemetry.
        """
        result = EnergyResult(step_num=step_num, dt=dt,
                              colony_size=len(polyp_states))

        # --- Phase 0: Build step cache and edge index -------------------
        self._step_cache.clear()
        self._last_sensory_raw.clear()
        self._last_outcome_raw.clear()
        self._last_retro_raw.clear()
        self._last_sensory_final.clear()
        self._last_outcome_final.clear()
        self._last_retro_final.clear()

        # Build per-polyp in-degree from edges
        in_degree: Dict[int, int] = defaultdict(int)
        out_degree: Dict[int, int] = defaultdict(int)
        for (src, dst), edge in edges.items():
            in_degree[dst] += 1
            out_degree[src] += 1

        # Pre-index edges by receiver and sender for retrograde
        edges_by_receiver: Dict[int, List[Tuple[int, any]]] = defaultdict(list)
        edges_by_sender: Dict[int, List[Tuple[int, any]]] = defaultdict(list)
        for (src, dst), edge in edges.items():
            edges_by_receiver[dst].append((src, edge))
            edges_by_sender[src].append((dst, edge))

        # Build step cache
        for p in polyp_states:
            if not p.is_alive:
                continue
            deg = in_degree.get(p.polyp_id, 0)
            cap = self._compute_local_capacity(p, deg)
            is_adult = (not p.is_juvenile) or p.handoff_complete
            is_direct = len(p.direct_stream_mask) > 0
            mi = 0.0
            if p.last_mi is not None:
                mi = p.last_mi
            elif p.direct_stream_mask:
                # Derive MI from direct streams if last_mi not cached
                valid_streams = [
                    s for s in p.direct_stream_mask
                    if s not in self._EXCLUDED_STREAM_NAMES
                       and s in stream_mi
                ]
                if valid_streams:
                    mi = np.median([stream_mi[s] for s in valid_streams])

            self._step_cache[p.polyp_id] = EnergyPolypStepState(
                polyp_id=p.polyp_id,
                degree=deg,
                calcification=p.calcification,
                gate_activity=p.gate_activity,
                local_capacity=cap,
                mi=mi,
                is_adult=is_adult,
                is_direct_sensor=is_direct,
                positive_matured_credit=matured_consequence[0],
                net_matured_credit=matured_consequence[1],
            )

        # --- Phase 1: BOCPD-weighted plasticity ------------------------
        cp_prob = self._update_bocpd(task_outcome.immediate_signal)
        plasticity_temp = self._compute_plasticity_temperature(cp_prob)
        result.bocpd_changepoint_prob = cp_prob
        result.plasticity_temperature = plasticity_temp

        # --- Phase 2: Three-channel budget computation ------------------
        # -- Sensory --
        sensory_claimants = self._build_sensory_claimants(
            polyp_states, stream_mi)
        sensory_budgets = self._compute_sensory_budgets(
            stream_mi, sensory_claimants)
        sensory_raw = self._allocate_sensory_capture(
            sensory_budgets, sensory_claimants, polyp_states)

        result.sensory_budgets = sensory_budgets
        result.sensory_num_claimants = sum(
            len(v) for v in sensory_claimants.values())
        result.sensory_num_streams_with_budget = sum(
            1 for b in sensory_budgets.values() if b > 0)
        result.sensory_total_raw = sum(sensory_raw.values())

        # -- Outcome --
        gross_pos, net_pos = matured_consequence
        outcome_claimants = self._build_outcome_claimants(
            polyp_states, gross_pos, net_pos)
        outcome_budget = self._compute_outcome_budget(
            task_outcome.immediate_signal, net_pos,
            list(outcome_claimants.values()))
        outcome_raw = self._allocate_outcome_capture(
            outcome_budget, outcome_claimants)

        result.outcome_budget_total = outcome_budget
        result.outcome_budget_source = self._outcome_budget_source
        result.outcome_zero_reason = self._outcome_zero_reason
        result.outcome_num_claimants = len(outcome_claimants)
        result.outcome_num_positive_adults = sum(
            1 for p in polyp_states
            if (not p.is_juvenile or p.handoff_complete)
            and p.trophic_health > 0)
        result.outcome_num_net_positive_adults = len(outcome_claimants)
        result.outcome_total_raw = sum(outcome_raw.values())

        # -- Retrograde --
        retro_release = self._compute_retrograde_release(
            polyp_states, edges, edges_by_receiver, edges_by_sender, in_degree)
        retro_raw = self._allocate_retrograde_capture(
            retro_release, polyp_states, edges_by_sender)

        result.retrograde_total_spent = sum(retro_release.values())
        result.retrograde_num_active_senders = sum(
            1 for v in retro_release.values() if v > 0)
        result.retrograde_num_active_receivers = sum(
            1 for p in polyp_states
            if p.is_alive and p.gate_activity > self.config.retrograde_activity_threshold)
        result.retrograde_bottleneck = self._retrograde_bottleneck
        result.retrograde_total_raw = sum(retro_raw.values())

        # --- Phase 3: Pro-rata capacity reconciliation ------------------
        final_support = self._reconcile_capacity(
            sensory_raw, outcome_raw, retro_raw, polyp_states)

        result.sensory_total_final = sum(
            self._last_sensory_final.get(pid, 0.0) for pid in self._step_cache)
        result.outcome_total_final = sum(
            self._last_outcome_final.get(pid, 0.0) for pid in self._step_cache)
        result.retrograde_total_final = sum(
            self._last_retro_final.get(pid, 0.0) for pid in self._step_cache)
        result.total_support_consumed = sum(final_support.values())

        # Count capacity-exceeded polyps
        cap_exceeded = 0
        total_cap = 0.0
        for pid, cache in self._step_cache.items():
            total_cap += cache.local_capacity
            raw_sum = (self._last_sensory_raw.get(pid, 0.0) +
                       self._last_outcome_raw.get(pid, 0.0) +
                       self._last_retro_raw.get(pid, 0.0))
            if raw_sum > cache.local_capacity + 1e-12:
                cap_exceeded += 1
        result.capacity_exceeded_count = cap_exceeded
        result.total_capacity_ceiling = total_cap

        # --- Phase 4: Maternal reserve OR adult ecology ----------------
        maternal_support: Dict[int, float] = defaultdict(float)
        handoff_triggered = False
        all_pre_handoff = all(not p.handoff_complete for p in polyp_states
                              if p.is_alive)
        any_pre_handoff = any(not p.handoff_complete for p in polyp_states
                              if p.is_alive)

        if any_pre_handoff and self.maternal_reserve is not None:
            # Pre-handoff: maternal reserve funds developmental support
            result.developmental_subsidy_active = True
            maternal_support = self.spend_maternal_developmental_support(
                polyp_states, dt)
            result.maternal_support_total = sum(maternal_support.values())
            result.maternal_trophic_fraction = \
                self.maternal_reserve.trophic_fraction
            result.maternal_atp_fraction = \
                self.maternal_reserve.atp_fraction
            result.maternal_is_exhausted = \
                self.maternal_reserve.is_exhausted

            # Check handoff trigger
            if self.check_handoff_trigger():
                handoff_triggered = True
                result.handoff_triggered = True
                # Mark all polyps as handoff-complete
                for p in polyp_states:
                    if p.is_alive:
                        p.handoff_complete = True

        # --- Phase 5: Apply support to each polyp ----------------------
        deaths: List[int] = []
        reproductions: List[int] = []
        total_trophic = 0.0
        total_calc = 0.0
        total_bax = 0.0

        for p in polyp_states:
            if not p.is_alive:
                continue

            pid = p.polyp_id
            earned = final_support.get(pid, 0.0)
            retro_spent = self._step_cache[pid].retrograde_spent \
                if pid in self._step_cache else 0.0

            # Add maternal support if pre-handoff
            if not p.handoff_complete or handoff_triggered:
                earned += maternal_support.get(pid, 0.0)

            # Cache final quantities
            if pid in self._step_cache:
                self._step_cache[pid].total_earned = earned
                self._step_cache[pid].retrograde_spent = retro_spent

            # Update polyp state
            deg = in_degree.get(pid, 0)
            self._apply_trophic_update(p, earned, retro_spent, deg, dt)

            # Update cyclin-D
            self._update_cyclin(p, dt)

            # Update BAX (post-handoff only)
            post_handoff = p.handoff_complete and not handoff_triggered
            self._update_bax(p, dt, post_handoff)

            # Check death
            if self.check_death(p, deg):
                p.is_alive = False
                deaths.append(pid)

            # Check reproduction (post-handoff adults only)
            local_supportable = self._step_cache[pid].local_capacity \
                if pid in self._step_cache else 0.0
            if self.check_reproduction_eligible(p, deg, local_supportable):
                reproductions.append(pid)

            # Accumulate telemetry
            total_trophic += p.trophic_health
            total_calc += p.calcification
            total_bax += p.bax_activation
            result.bax_activations[pid] = p.bax_activation
            result.cyclin_values[pid] = p.cyclin_d

        # --- Phase 6: Finalize result ----------------------------------
        result.deaths = deaths
        result.reproductions = reproductions
        result.any_death = len(deaths) > 0
        result.any_reproduction = len(reproductions) > 0
        result.polyp_step_states = dict(self._step_cache)
        result.reserve_depleted_this_step = (
            self.maternal_reserve.is_exhausted
            if self.maternal_reserve is not None else False
        )

        n_live = max(1, len([p for p in polyp_states if p.is_alive]))
        result.mean_trophic_health = total_trophic / n_live
        result.mean_calcification = total_calc / n_live
        result.mean_bax = total_bax / n_live

        # Store telemetry
        self._telemetry_history.append({
            "step": step_num,
            "deaths": len(deaths),
            "reproductions": len(reproductions),
            "total_support": result.total_support_consumed,
            "sensory_raw": result.sensory_total_raw,
            "outcome_raw": result.outcome_total_raw,
            "retro_raw": result.retrograde_total_raw,
        })

        return result

    # =====================================================================
    # Phase 1: BOCPD changepoint detection
    # =====================================================================

    def _update_bocpd(self, signal: float) -> float:
        """Update simplified BOCPD state and return changepoint probability.

        This is a lightweight host-side approximation of Bayesian Online
        Changepoint Detection (Adams & MacKay, 2007). The full BOCPD
        machinery with run-length distribution lives in the colony's
        inference module; this version uses a simple predictive filter
        to estimate P(changepoint | data).

        Args:
            signal: The task outcome signal for this step.

        Returns:
            Estimated changepoint probability in [0, 1].
        """
        st = self._bocpd_state
        run = st["run_length"]
        mu = st["predictive_mean"]
        var = st["predictive_var"]
        hazard = st["hazard_rate"]

        # Predictive probability of this observation under current model
        if var > 1e-12:
            pred_prob = math.exp(-0.5 * ((signal - mu) ** 2) / var) \
                        / math.sqrt(2.0 * math.pi * var)
        else:
            pred_prob = 1.0 if abs(signal - mu) < 1e-6 else 0.0

        # Growth probability: P(no changepoint | data)
        growth = pred_prob * (1.0 - hazard)

        # Changepoint probability: P(changepoint | data)
        cp_prob = hazard if (growth + hazard) < 1e-12 else \
                  hazard / (growth + hazard)
        cp_prob = float(np.clip(cp_prob, 0.0, 1.0))

        # Update run length
        if cp_prob > 0.5:
            st["run_length"] = 0
            st["predictive_mean"] = signal
            st["predictive_var"] = 1.0
        else:
            st["run_length"] = run + 1
            # Recursive mean/variance update
            alpha = 1.0 / (run + 2.0)
            st["predictive_mean"] = (1.0 - alpha) * mu + alpha * signal
            st["predictive_var"] = max(0.01,
                (1.0 - alpha) * var + alpha * (signal - mu) ** 2)

        return cp_prob

    def _compute_plasticity_temperature(self, cp_prob: float) -> float:
        """Compute effective plasticity temperature given changepoint probability.

        When BOCPD signals a likely changepoint, the plasticity temperature
        rises, unlocking calcification and allowing structural rewiring.
        This is analogous to elevated CREB-mediated protein synthesis
        during novel experiences (Abraham & Williams, 2008).

        Args:
            cp_prob: Changepoint probability from _update_bocpd.

        Returns:
            Effective plasticity temperature (>= 1.0).
        """
        base_temp = 1.0
        if cp_prob > self.config.bocpd_changepoint_threshold:
            boost = self.config.bocpd_plasticity_multiplier * cp_prob
            return base_temp + boost
        return base_temp

    # =====================================================================
    # Phase 2: Three-channel budget computation
    # =====================================================================

    def _compute_sensory_budgets(
        self,
        stream_mi: Dict[str, float],
        claimants: Dict[str, List[Tuple[int, float]]]
    ) -> Dict[str, float]:
        """Compute per-stream sensory budgets.

        For each external stream s:
            budget_s = (1 - exp(-stream_MI_s)) * median(recovery_demand_q)
                       over direct exteroceptive claimants q on stream s

        Internal/helper streams and routing-only metadata are excluded.

        Args:
            stream_mi: Dict stream_name -> mutual information.
            claimants: Dict stream_name -> list of (polyp_id, drive) tuples.

        Returns:
            Dict stream_name -> budget amount.
        """
        budgets: Dict[str, float] = {}
        for stream_name, clist in claimants.items():
            # Skip excluded streams
            if stream_name in self._EXCLUDED_STREAM_NAMES:
                continue
            mi = stream_mi.get(stream_name, 0.0)
            if mi <= 0:
                budgets[stream_name] = 0.0
                continue

            # Compute recovery demand as median drive over claimants
            drives = [drive for (_, drive) in clist if drive > 0]
            if not drives:
                budgets[stream_name] = 0.0
                continue
            recovery_demand = float(np.median(drives))

            # Budget formula: (1 - exp(-MI)) * median_recovery_demand
            budget = (1.0 - math.exp(-mi)) * recovery_demand
            budgets[stream_name] = max(0.0, budget)
        return budgets

    def _compute_outcome_budget(
        self,
        task_signal: float,
        net_matured: float,
        claimants: List[Tuple[int, float, float]]
    ) -> float:
        """Compute the total outcome budget.

        Budget is minted from the maximum of:
            - immediate positive task signal
            - net matured positive consequence

        Multiplied by median recovery demand over positive-task claimants.

        Strict net-positive gating: only adults with net_matured_credit > 0
        can be claimants. If no such adults exist, budget is zero.

        Args:
            task_signal: Immediate task performance signal.
            net_matured: Net matured positive consequence.
            claimants: List of (polyp_id, gross_positive, net_positive).

        Returns:
            Total outcome budget (>= 0).
        """
        # Determine budget source
        positive_signal = max(0.0, task_signal)
        positive_matured = max(0.0, net_matured)

        if positive_signal <= 0 and positive_matured <= 0:
            self._outcome_budget_source = "none"
            self._outcome_zero_reason = "no_positive_signal"
            return 0.0

        # Budget is max of the two sources
        if positive_signal >= positive_matured:
            source_amount = positive_signal
            self._outcome_budget_source = "task_signal"
        else:
            source_amount = positive_matured
            self._outcome_budget_source = "matured_consequence"

        # Recovery demand = median net_positive over claimants
        if not claimants:
            self._outcome_zero_reason = "no_net_positive_adults"
            self._outcome_budget_source = "none"
            return 0.0

        net_values = [net_pos for (_, _, net_pos) in claimants if net_pos > 0]
        if not net_values:
            self._outcome_zero_reason = "no_net_positive_adults"
            self._outcome_budget_source = "none"
            return 0.0

        recovery_demand = float(np.median(net_values))
        budget = source_amount * recovery_demand

        self._outcome_zero_reason = ""  # Budget is positive
        return max(0.0, budget)

    def _compute_retrograde_release(
        self,
        polyp_states: List[PolypState],
        edges: Dict[Tuple[int, int], any],
        edges_by_receiver: Dict[int, List[Tuple[int, any]]],
        edges_by_sender: Dict[int, List[Tuple[int, any]]],
        in_degree: Dict[int, int]
    ) -> Dict[int, float]:
        """Compute per-sender retrograde trophic release.

        Retrograde release for sender p:
            release_p = sum over active incoming edges (p -> receiver) of:
                        trophic_spent_by_receiver * causal_contribution

        The receiver's spent trophic is its effective decay cost. The
        causal contribution is a per-edge weight indicating how much
        this sender helped the receiver.

        Valid sender must have:
            - release capacity (bdnf_release_rate > 0)
            - activity > threshold
            - trophic eligibility (trophic_health > 0)

        Args:
            polyp_states: All polyp states.
            edges: Full edge dictionary.
            edges_by_receiver: Pre-computed edges indexed by receiver.
            in_degree: Pre-computed in-degree per polyp.

        Returns:
            Dict sender_polyp_id -> total retrograde release amount.
        """
        release: Dict[int, float] = defaultdict(float)
        state_by_id: Dict[int, PolypState] = \
            {p.polyp_id: p for p in polyp_states if p.is_alive}

        # For each sender, compute release on its outgoing active edges
        for p in polyp_states:
            if not p.is_alive:
                continue
            pid = p.polyp_id

            # Check sender eligibility
            if p.bdnf_release_rate <= 0:
                continue
            if p.gate_activity <= self.config.retrograde_activity_threshold:
                continue
            if p.trophic_health <= 0:
                continue

            # Sum over outgoing edges
            total_release = 0.0
            for dst, edge in edges_by_sender.get(pid, []):
                if not getattr(edge, 'is_active', True):
                    continue
                dst_state = state_by_id.get(dst)
                if dst_state is None or not dst_state.is_alive:
                    continue

                # Receiver's effective decay = metabolic cost
                deg = in_degree.get(dst, 0)
                effective_decay = (dst_state.metabolic_decay +
                    dst_state.trophic_synapse_cost * deg)
                receiver_spent = effective_decay  # dimensionless per-step cost

                # Causal contribution per edge
                causal = getattr(edge, 'causal_contribution', 1.0)
                if causal <= 0:
                    continue

                # Release amount = receiver_spent * causal_contribution * sender_release_rate
                edge_release = receiver_spent * causal * p.bdnf_release_rate
                total_release += edge_release

            if total_release > 0:
                release[pid] = total_release

        return dict(release)

    # =====================================================================
    # Claimant construction
    # =====================================================================

    def _build_sensory_claimants(
        self,
        polyp_states: List[PolypState],
        stream_mi: Dict[str, float]
    ) -> Dict[str, List[Tuple[int, float]]]:
        """Build per-stream lists of sensory claimants.

        Only "direct exteroceptive" polyps (those with the stream in their
        direct_stream_mask) can claim. Claims are proportional to each
        claimant's drive: drive = MI * uptake_rate + DA_gain * dopamine_EMA.

        Internal streams (_temporal, asset, stream_context) are excluded.

        Args:
            polyp_states: All polyp states.
            stream_mi: Dict stream_name -> MI value.

        Returns:
            Dict stream_name -> list of (polyp_id, drive).
        """
        claimants: Dict[str, List[Tuple[int, float]]] = defaultdict(list)

        for p in polyp_states:
            if not p.is_alive:
                continue
            for stream in p.direct_stream_mask:
                # Exclude internal/routing streams
                if stream in self._EXCLUDED_STREAM_NAMES:
                    continue
                if stream not in stream_mi:
                    continue

                drive = p.compute_drive()
                if drive >= SENSORY_CLAIM_MIN_DRIVE:
                    claimants[stream].append((p.polyp_id, drive))

        return dict(claimants)

    def _build_outcome_claimants(
        self,
        polyp_states: List[PolypState],
        gross_positive: float,
        net_positive: float
    ) -> Dict[int, Tuple[int, float, float]]:
        """Build outcome claimants with strict net-positive gating.

        Strict net-positive gating: only adults (non-juvenile or post-handoff)
        with positive NET matured credit can claim. Gross-only claimants
        CANNOT mint outcome support.

        Each claimant carries (polyp_id, gross_positive, net_positive).
        The claim strength is weighted by sqrt(gross_positive * net_positive).

        Args:
            polyp_states: All polyp states.
            gross_positive: Colony gross positive matured credit.
            net_positive: Colony net positive matured credit.

        Returns:
            Dict polyp_id -> (polyp_id, gross_positive, net_positive).
        """
        claimants: Dict[int, Tuple[int, float, float]] = {}

        for p in polyp_states:
            if not p.is_alive:
                continue

            # Must be adult (post-handoff or not juvenile)
            is_adult = (not p.is_juvenile) or p.handoff_complete
            if not is_adult:
                continue

            # Strict net-positive gating
            if net_positive <= 0:
                continue

            # Individual net matured credit — use colony-level for simplicity
            # (per-polyp credit tracking would live in the consequence ledger)
            individual_net = net_positive  # Simplified: colony-level credit
            individual_gross = gross_positive

            if individual_net <= 0:
                continue

            claimants[p.polyp_id] = (p.polyp_id, individual_gross,
                                     individual_net)

        return claimants

    # =====================================================================
    # Capture and allocation
    # =====================================================================

    def _allocate_sensory_capture(
        self,
        budgets: Dict[str, float],
        claimants: Dict[str, List[Tuple[int, float]]],
        polyp_states: List[PolypState]
    ) -> Dict[int, float]:
        """Allocate sensory capture to polyps pro-rata by drive.

        For each stream:
            total_drive = sum of drives of all claimants
            capture_p = budget * (drive_p / total_drive)

        A polyp sensing multiple streams accumulates capture from each.

        Args:
            budgets: Dict stream -> budget amount.
            claimants: Dict stream -> list of (polyp_id, drive).
            polyp_states: All polyp states (for indexing).

        Returns:
            Dict polyp_id -> total sensory capture amount.
        """
        capture: Dict[int, float] = defaultdict(float)

        for stream_name, clist in claimants.items():
            budget = budgets.get(stream_name, 0.0)
            if budget <= 0:
                continue
            if not clist:
                continue

            total_drive = sum(drive for (_, drive) in clist)
            if total_drive < SENSORY_CLAIM_MIN_DRIVE:
                continue

            for pid, drive in clist:
                share = budget * (drive / total_drive)
                capture[pid] += share
                # Cache raw amount
                if pid in self._step_cache:
                    self._step_cache[pid].sensory_budget_raw += share

        return dict(capture)

    def _allocate_outcome_capture(
        self,
        budget: float,
        claimants: Dict[int, Tuple[int, float, float]]
    ) -> Dict[int, float]:
        """Allocate outcome capture pro-rata by claim strength.

        Claim strength = sqrt(gross_positive * net_positive)
        — stronger truthful delayed winners claim more.

        Gross-only claimants cannot mint outcome support (already filtered
        in _build_outcome_claimants via net-positive gating).

        Args:
            budget: Total outcome budget.
            claimants: Dict polyp_id -> (polyp_id, gross, net).

        Returns:
            Dict polyp_id -> outcome capture amount.
        """
        capture: Dict[int, float] = {}

        if budget <= 0 or not claimants:
            return capture

        # Compute claim strengths
        strengths: Dict[int, float] = {}
        for pid, (_, gross, net) in claimants.items():
            if gross > 0 and net > 0:
                strength = math.sqrt(gross * net)
                strengths[pid] = strength

        total_strength = sum(strengths.values())
        if total_strength < 1e-12:
            return capture

        for pid, strength in strengths.items():
            share = budget * (strength / total_strength)
            capture[pid] = share
            if pid in self._step_cache:
                self._step_cache[pid].outcome_budget_raw = share

        return capture

    def _allocate_retrograde_capture(
        self,
        release: Dict[int, float],
        polyp_states: List[PolypState],
        edges_by_sender: Dict[int, List[Tuple[int, any]]]
    ) -> Dict[int, float]:
        """Allocate retrograde capture (receiver-side) based on sender releases.

        Retrograde received by receiver r from sender s:
            received_r += release_s * (bdnf_uptake_r / Z)
        where Z normalizes over competing receivers of sender s.

        The receiver's uptake efficiency (bdnf_uptake_efficiency) scales
        how much of each sender's release it can absorb.

        Args:
            release: Dict sender_id -> total release amount.
            polyp_states: All polyp states.
            edges_by_sender: Pre-computed edges indexed by sender.

        Returns:
            Dict receiver_id -> total retrograde capture amount.
        """
        capture: Dict[int, float] = defaultdict(float)
        state_by_id: Dict[int, PolypState] = \
            {p.polyp_id: p for p in polyp_states if p.is_alive}

        if not release:
            self._retrograde_bottleneck = "no_active_senders"
            return dict(capture)

        total_allocated = 0.0

        for sender_id, sender_release in release.items():
            if sender_release <= 0:
                continue

            # Find all receivers of this sender
            receivers = edges_by_sender.get(sender_id, [])
            if not receivers:
                continue

            # Collect eligible receivers with uptake efficiency
            eligible: List[Tuple[int, float]] = []  # (receiver_id, uptake)
            for dst_id, edge in receivers:
                if not getattr(edge, 'is_active', True):
                    continue
                dst_state = state_by_id.get(dst_id)
                if dst_state is None or not dst_state.is_alive:
                    continue
                uptake = dst_state.bdnf_uptake_efficiency
                if uptake > 0:
                    eligible.append((dst_id, uptake))

            # O(N^2) guard: if spatial hash returns no local candidates
            if not eligible:
                # Fallback: sample up to MAX_RETROGRADE_CANDIDATES random
                # from all live polyps (excluding self)
                candidates = [
                    p for p in polyp_states
                    if p.is_alive and p.polyp_id != sender_id
                ]
                if len(candidates) > self.config.max_retrograde_candidates:
                    rng = np.random.default_rng(seed=sender_id + 42)
                    idx = rng.choice(len(candidates),
                                     size=self.config.max_retrograde_candidates,
                                     replace=False)
                    candidates = [candidates[i] for i in idx]

                eligible = [(p.polyp_id, p.bdnf_uptake_efficiency)
                            for p in candidates
                            if p.bdnf_uptake_efficiency > 0]

            if not eligible:
                continue

            # Pro-rata allocation by uptake efficiency
            total_uptake = sum(u for (_, u) in eligible)
            if total_uptake < 1e-12:
                continue

            for recv_id, uptake in eligible:
                share = sender_release * (uptake / total_uptake)
                capture[recv_id] += share
                total_allocated += share

        if total_allocated <= 0:
            self._retrograde_bottleneck = "no_active_receivers"
        else:
            self._retrograde_bottleneck = ""

        # Cache raw retrograde per polyp
        for pid, amt in capture.items():
            if pid in self._step_cache:
                self._step_cache[pid].retrograde_budget_raw = amt

        return dict(capture)

    # =====================================================================
    # Phase 3: Pro-rata capacity reconciliation
    # =====================================================================

    def _reconcile_capacity(
        self,
        sensory: Dict[int, float],
        outcome: Dict[int, float],
        retrograde: Dict[int, float],
        polyp_states: List[PolypState]
    ) -> Dict[int, float]:
        """Reconcile all three channels pro-rata against local capacity.

        After computing raw captures for all three channels independently:
            1. Sum all raw captures across channels per polyp
            2. Compare to local trophic capacity ceiling
            3. If total exceeds capacity, scale ALL channels pro-rata
            4. This prevents sensory-first starvation

        The scaling factor for polyp p is:
            scale_p = min(1.0, capacity_p / total_raw_p)

        All channels are multiplied by the same scale_p.

        Args:
            sensory: Dict polyp_id -> raw sensory capture.
            outcome: Dict polyp_id -> raw outcome capture.
            retrograde: Dict polyp_id -> raw retrograde capture.
            polyp_states: All polyp states.

        Returns:
            Dict polyp_id -> reconciled total support.
        """
        final_support: Dict[int, float] = {}

        # Gather all polyp IDs present in any channel
        all_pids = set(sensory.keys()) | set(outcome.keys()) | \
                   set(retrograde.keys())

        for pid in all_pids:
            s = sensory.get(pid, 0.0)
            o = outcome.get(pid, 0.0)
            r = retrograde.get(pid, 0.0)
            total_raw = s + o + r

            # Cache raw amounts
            self._last_sensory_raw[pid] = s
            self._last_outcome_raw[pid] = o
            self._last_retro_raw[pid] = r

            # Get capacity ceiling
            cache = self._step_cache.get(pid)
            if cache is None:
                # Polyp not in cache — no capacity data, use raw as-is
                final_support[pid] = total_raw
                self._last_sensory_final[pid] = s
                self._last_outcome_final[pid] = o
                self._last_retro_final[pid] = r
                continue

            capacity = cache.local_capacity

            if total_raw > capacity and capacity > 0:
                # Scale all channels pro-rata
                scale = capacity / total_raw
                s_final = s * scale
                o_final = o * scale
                r_final = r * scale
            else:
                s_final = s
                o_final = o
                r_final = r

            total_final = s_final + o_final + r_final
            final_support[pid] = total_final

            # Cache final amounts
            self._last_sensory_final[pid] = s_final
            self._last_outcome_final[pid] = o_final
            self._last_retro_final[pid] = r_final

            # Update cache
            cache.sensory_budget_raw = s
            cache.outcome_budget_raw = o
            cache.retrograde_budget_raw = r

        return final_support

    # =====================================================================
    # Local capacity computation
    # =====================================================================

    def _compute_local_capacity(self, p: PolypState, degree: int) -> float:
        """Compute the local trophic capacity ceiling for a polyp.

        The capacity ceiling bounds how much trophic support a polyp can
        absorb in one step. It scales with the polyp's metabolic cost
        so that high-degree (many synapse) polyps need more but also
        have higher ceilings.

        Capacity = base_capacity * (1 + calcification_bonus)
        where base_capacity scales with effective_decay.

        Args:
            p: The polyp state.
            degree: In-degree (number of incoming synapses).

        Returns:
            Local trophic capacity ceiling (float).
        """
        effective_decay = (p.metabolic_decay +
                           p.trophic_synapse_cost * degree)
        # Capacity is a multiple of metabolic need — allows accumulation
        base_capacity = 5.0 * effective_decay  # ENGINEERING: 5x metabolic need
        calc_bonus = 1.0 + 0.5 * p.calcification  # More calcified = more capacity
        return base_capacity * calc_bonus

    # =====================================================================
    # Maternal reserve management
    # =====================================================================

    def initialize_maternal_reserve(
        self,
        founder_state: PolypState,
        n_streams: int,
        dt: float
    ) -> None:
        """Initialize maternal reserve from founder state.

        The reserve is derived from founder-local live recovery equations
        plus first-cleavage split geometry. It represents the finite
        nutrient store available to the developing embryo before it must
        transition to autonomous feeding.

        Reserve ONLY depletes — never replenished.

        Args:
            founder_state: The founder polyp's state.
            n_streams: Number of external streams (more streams = more reserve).
            dt: Simulation time step.
        """
        # Base reserve scales with founder health and stream diversity
        # biology_derived: embryonic yolk-to-body mass ratio is ~10-30%
        # in many vertebrates (Needham, 1942)
        base_trophic = founder_state.trophic_health * 100.0 * n_streams
        base_atp = founder_state.trophic_health * 50.0 * n_streams

        # First-cleavage split geometry: reserve is halved at each
        # "cleavage" event (modeled as reserve fraction tracking)
        self.maternal_reserve = MaternalReserve(
            trophic_reserve=base_trophic,
            atp_reserve=base_atp,
            initial_trophic=base_trophic,
            initial_atp=base_atp,
            is_exhausted=False,
        )

    def spend_maternal_developmental_support(
        self,
        polyp_states: List[PolypState],
        dt: float
    ) -> Dict[int, float]:
        """Spend maternal reserve to provide developmental support.

        Pre-handoff support covers developmental autonomy target (not just
        survival). Support tapers toward survival floor as juveniles mature.

        Each pre-handoff polyp receives support proportional to its
        metabolic need and maternal_reserve_fraction.

        Args:
            polyp_states: All polyp states.
            dt: Time step.

        Returns:
            Dict polyp_id -> maternal support amount received.
        """
        support: Dict[int, float] = {}
        if self.maternal_reserve is None or self.maternal_reserve.is_exhausted:
            return support

        # Identify pre-handoff polyps
        pre_handoff = [p for p in polyp_states
                       if p.is_alive and not p.handoff_complete]
        if not pre_handoff:
            return support

        # Compute total developmental need
        total_need = 0.0
        needs: Dict[int, float] = {}
        for p in pre_handoff:
            # Need = metabolic cost * reserve fraction * developmental scaling
            # Tapers as maternal reserve drops
            reserve_frac = self.maternal_reserve.trophic_fraction
            developmental_target = 2.0 * p.metabolic_decay  # 2x survival
            survival_floor = p.metabolic_decay * 0.5

            # Taper from developmental_target toward survival_floor
            # as reserve depletes
            taper = reserve_frac  # 1.0 = full target, 0.0 = survival floor
            need = survival_floor + taper * (developmental_target - survival_floor)
            need *= p.maternal_reserve_fraction
            needs[p.polyp_id] = max(0.0, need)
            total_need += need

        if total_need <= 0:
            return support

        # Distribute reserve pro-rata by need
        reserve_available = self.maternal_reserve.trophic_reserve
        if reserve_available <= 0:
            return support

        # Spend from reserve
        spend_amount = min(total_need, reserve_available)
        actual_spent = self.maternal_reserve.deplete_trophic(spend_amount)

        if actual_spent <= 0:
            return support

        # Distribute actual spent pro-rata
        for p in pre_handoff:
            pid = p.polyp_id
            need = needs[pid]
            if total_need > 0:
                share = actual_spent * (need / total_need)
                support[pid] = share

        return support

    def check_handoff_trigger(self) -> bool:
        """Check if maternal-to-autonomous handoff should trigger.

        Handoff triggers when maternal reserve can no longer fund one
        developmental-support tick. At that point, all polyps transition
        to adult ecology — no more developmental subsidy.

        Returns:
            True if handoff should trigger this step.
        """
        if self.maternal_reserve is None:
            return True  # No reserve = immediate handoff
        if self.maternal_reserve.is_exhausted:
            return True
        # Trigger when reserve fraction drops below threshold
        # (can't fund one more developmental-support tick)
        if self.maternal_reserve.trophic_fraction < 0.05:  # ENGINEERING
            return True
        return False

    # =====================================================================
    # Death and reproduction helpers
    # =====================================================================

    def check_death(self, state: PolypState, degree: int) -> bool:
        """Check if a polyp should die (apoptosis).

        Death is absolute: trophic_health < apoptosis_threshold + bax_activation

        BAX accumulation comes from persistent local support deficit and
        accuracy-based pressure, computed in _update_bax().

        Args:
            state: The polyp's current state.
            degree: Current in-degree.

        Returns:
            True if polyp dies this step.
        """
        if not state.is_alive:
            return False
        death_line = state.apoptosis_threshold + state.bax_activation
        return state.trophic_health < death_line

    def check_reproduction_eligible(
        self,
        state: PolypState,
        degree: int,
        local_supportable: float
    ) -> bool:
        """Check if a polyp is eligible for reproduction (budding).

        Reproduction requires ALL of:
            1. trophic_health > reproduction_threshold
            2. cyclin-D > 0.5
            3. NOT juvenile
            4. local_supportability > MIN_REPRODUCTION_SUPPORTABILITY_RATIO * survival_cost

        Args:
            state: The polyp's current state.
            degree: Current in-degree.
            local_supportable: Local trophic capacity ceiling.

        Returns:
            True if polyp can reproduce this step.
        """
        if not state.is_alive:
            return False
        if state.is_juvenile and not state.handoff_complete:
            return False
        if state.trophic_health < state.reproduction_threshold:
            return False
        if state.cyclin_d <= 0.5:
            return False

        # Check local supportability
        survival_cost = (state.metabolic_decay +
                         state.trophic_synapse_cost * degree)
        min_supportable = (self.config.min_reproduction_supportability_ratio
                           * survival_cost)
        if local_supportable <= min_supportable:
            return False

        return True

    # =====================================================================
    # Polyp state updates (trophic, cyclin, BAX)
    # =====================================================================

    def _apply_trophic_update(
        self,
        p: PolypState,
        earned: float,
        retro_spent: float,
        degree: int,
        dt: float
    ) -> None:
        """Apply the trophic health update equation to a polyp.

        Trophic health update:
            effective_decay = metabolic_decay + trophic_synapse_cost * degree
            trophic_health = (trophic_health - retrograde_spent + total_support)
                             * exp(-effective_decay * dt)

        Args:
            p: Polyp state (modified in place).
            earned: Total earned support from all channels.
            retro_spent: Amount this polyp spent on retrograde (sent).
            degree: In-degree.
            dt: Time step.
        """
        effective_decay = (p.metabolic_decay +
                           p.trophic_synapse_cost * degree)

        # Net change before decay
        net_input = p.trophic_health - retro_spent + earned
        net_input = max(0.0, net_input)  # Floor at zero

        # Exponential decay
        decay_factor = math.exp(-effective_decay * dt)
        p.trophic_health = net_input * decay_factor
        p.earned_support = earned

        # Track support history for juvenile maturity estimation
        if hasattr(p, "support_history"):
            p.support_history.append(earned)

    def _update_cyclin(self, p: PolypState, dt: float) -> None:
        """Update cyclin-D level.

        Cyclin-D accumulates when the polyp is well-supported and decays
        otherwise. It serves as a "readiness to divide" signal, analogous
        to cell-cycle G1/S checkpoint control in biological development
        (Sherr, 1994).

        Args:
            p: Polyp state (modified in place).
            dt: Time step.
        """
        # Cyclin-D dynamics: accumulate when healthy, decay when stressed
        if p.trophic_health > p.apoptosis_threshold * 3.0:
            # Growth phase: cyclin accumulates
            growth_rate = 0.1 * (p.trophic_health - p.apoptosis_threshold * 3.0)
            p.cyclin_d = min(1.0, p.cyclin_d + growth_rate * dt)
        else:
            # Decay phase
            decay_rate = 0.2
            p.cyclin_d = max(0.0, p.cyclin_d - decay_rate * dt)

    def _update_bax(
        self,
        p: PolypState,
        dt: float,
        post_handoff: bool
    ) -> None:
        """Update BAX activation level.

        BAX accumulates from:
            1. Persistent local support deficit (not enough support)
            2. Accuracy-based pressure (low directional accuracy)

        Pre-handoff (developmental phase): BAX accumulation is suppressed
        to protect developing polyps. After handoff, BAX exerts full
        apoptotic pressure.

        Args:
            p: Polyp state (modified in place).
            dt: Time step.
            post_handoff: True if maternal handoff is complete.
        """
        if not post_handoff:
            # Pre-handoff: suppress BAX to protect development
            p.bax_activation = max(0.0, p.bax_activation - 0.05 * dt)
            return

        # Support deficit pressure
        support_ratio = p.earned_support / max(p.metabolic_decay, 1e-9)
        if support_ratio < 1.0:
            deficit_pressure = (1.0 - support_ratio) * 0.1
        else:
            deficit_pressure = -0.02  # Recovery when well-supported

        # Accuracy pressure: low accuracy increases BAX
        accuracy_pressure = (1.0 - p.directional_accuracy_ema) * 0.05

        # Combined update
        delta_bax = (deficit_pressure + accuracy_pressure) * dt
        p.bax_activation = max(0.0, p.bax_activation + delta_bax)

        # BAX naturally decays slowly (repair mechanisms)
        p.bax_activation *= math.exp(-0.01 * dt)

    # =====================================================================
    # Telemetry and diagnostics
    # =====================================================================

    def get_channel_telemetry(self) -> Dict:
        """Get per-channel raw and final capture summaries.

        Returns:
            Dict with keys 'sensory', 'outcome', 'retrograde', each
            containing 'raw' and 'final' totals.
        """
        return {
            "sensory": {
                "raw": sum(self._last_sensory_raw.values()),
                "final": sum(self._last_sensory_final.values()),
            },
            "outcome": {
                "raw": sum(self._last_outcome_raw.values()),
                "final": sum(self._last_outcome_final.values()),
            },
            "retrograde": {
                "raw": sum(self._last_retro_raw.values()),
                "final": sum(self._last_retro_final.values()),
            },
        }

    def get_budget_diagnostics(self) -> Dict:
        """Get budget source and zero-outcome diagnostics.

        Returns:
            Dict with outcome_budget_source, outcome_zero_reason,
            retrograde_bottleneck, and bocpd state.
        """
        return {
            "outcome_budget_source": getattr(self, '_outcome_budget_source', "none"),
            "outcome_zero_reason": getattr(self, '_outcome_zero_reason', ""),
            "retrograde_bottleneck": getattr(self, '_retrograde_bottleneck', ""),
            "bocpd_run_length": self._bocpd_state.get("run_length", 0),
            "bocpd_predictive_mean": self._bocpd_state.get("predictive_mean", 0.0),
        }

    def get_reserve_status(self) -> Dict:
        """Get maternal reserve status.

        Returns:
            Dict with trophic_fraction, atp_fraction, is_exhausted.
            If no maternal reserve exists, returns all zeros.
        """
        if self.maternal_reserve is None:
            return {
                "trophic_fraction": 0.0,
                "atp_fraction": 0.0,
                "is_exhausted": True,
                "trophic_reserve": 0.0,
                "atp_reserve": 0.0,
            }
        return {
            "trophic_fraction": self.maternal_reserve.trophic_fraction,
            "atp_fraction": self.maternal_reserve.atp_fraction,
            "is_exhausted": self.maternal_reserve.is_exhausted,
            "trophic_reserve": self.maternal_reserve.trophic_reserve,
            "atp_reserve": self.maternal_reserve.atp_reserve,
        }

    def get_colony_health_summary(self, polyp_states: List[PolypState]) -> Dict:
        """Compute a summary of colony-wide health metrics.

        Args:
            polyp_states: All polyp states.

        Returns:
            Dict with mean/median/std of trophic_health, calcification,
            bax_activation, and alive/dead counts.
        """
        live = [p for p in polyp_states if p.is_alive]
        if not live:
            return {
                "alive_count": 0,
                "dead_count": len(polyp_states),
                "mean_trophic": 0.0,
                "median_trophic": 0.0,
                "mean_calcification": 0.0,
                "mean_bax": 0.0,
            }

        trophic_vals = [p.trophic_health for p in live]
        calc_vals = [p.calcification for p in live]
        bax_vals = [p.bax_activation for p in live]

        return {
            "alive_count": len(live),
            "dead_count": len(polyp_states) - len(live),
            "mean_trophic": float(np.mean(trophic_vals)),
            "median_trophic": float(np.median(trophic_vals)),
            "std_trophic": float(np.std(trophic_vals)),
            "mean_calcification": float(np.mean(calc_vals)),
            "mean_bax": float(np.mean(bax_vals)),
        }

    def get_telemetry_history(self, n: int = 10) -> List[Dict]:
        """Get the last n telemetry entries.

        Args:
            n: Number of recent entries to return.

        Returns:
            List of telemetry dicts, most recent last.
        """
        hist = list(self._telemetry_history)
        return hist[-n:]
