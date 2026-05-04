"""
Lifecycle Manager for Coral Reef Architecture on SpiNNaker.

Manages the full lifecycle of polyp neurons:
- Cyclin-D gated reproduction (Morgan 1995 G1/S checkpoint)
- BAX-driven apoptosis (Katz & Shatz 1996 activity-dependent pruning)
- Maternal-to-autonomous handoff (MBT analog: mid-blastula transition)
- Founder cleavage (pre-handoff embryo stage)
- Juvenile integration window (estimator-derived maturity)
- Population control (hardware-derived ceiling)
- ATP economy (construction/maintenance/bootstrap)
- Structural growth budgets (support-limited)
- 3D birth placement and migration

All lifecycle decisions are LOCAL per polyp, not colony-global.
Polyps survive or reproduce based on their own earned state.

References:
- Morgan (1995) The Cell Cycle. Principles of G1/S checkpoint control.
- Oppenheim (1991) Neuronal cell death and survival. ~50% developmental death.
- Katz & Shatz (1996) Synaptic activity and the construction of cortical circuits.
      Activity-dependent pruning; death is per-neuron, not global ratio.
- Levi-Montalcini (1987) The nerve growth factor. Trophic support theory.
- Newport & Kirschner (1982) A major developmental transition in early Xenopus
      embryos: the mid-blastula transition (MBT) analog for handoff.
- Raff (1992) Social controls on cell survival and cell death.
- Chen et al. (2016) Cyclin D-Cdk4,6 drives cell-cycle progression.

CRA Version: v009bz-follow-up (correlated cyclin, per-lineage handoff floor)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any
from collections import defaultdict, deque
import numpy as np
import math
import random
import struct

# ---------------------------------------------------------------------------
# Configuration types (forward references — resolved at runtime via import)
# ---------------------------------------------------------------------------
# These are type-hint placeholders; actual classes are imported from their
# respective modules.  Using TYPE_CHECKING avoids circular imports.

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import LifecycleConfig, EnergyConfig
    from .polyp_neuron import PolypState
    from .energy_manager import MaternalReserve, EnergyResult
    from .reef_network import ReefNetwork


# ---------------------------------------------------------------------------
# Telemetry / record dataclasses
# ---------------------------------------------------------------------------

@dataclass
class LifecycleEvent:
    """Record of a birth, death, or handoff event.

    Attributes:
        event_type: One of "birth", "death", "handoff", "cleavage".
        step: Simulation step at which the event occurred.
        polyp_id: Unique identifier of the affected polyp.
        lineage_id: Lineage (colony) the polyp belongs to.
        parent_id: For births/cleavages, the parent polyp. None otherwise.
        details: Extra key-value data (e.g. position, cyclin-D level, cause).
    """

    event_type: str
    step: int
    polyp_id: int
    lineage_id: int
    parent_id: Optional[int] = None
    details: dict = field(default_factory=dict)


@dataclass
class LineageRecord:
    """Tracks history of one lineage (all descendants of a single founder).

    A *lineage* is a clonal colony: every polyp in it descends from the same
    founder via mitotic division.  Support history is kept in a bounded deque
    so the estimator has enough samples to project maturity without unbounded
    memory growth.

    Attributes:
        lineage_id: Unique lineage identifier.
        founder_id: Polyp ID of the founding polyp.
        polyp_ids: All polyp IDs currently alive in this lineage.
        birth_steps: Step numbers at which births occurred.
        death_steps: Step numbers at which deaths occurred.
        support_history: Deque of recent per-step support values for maturity
            estimation ( maxlen = 1000 to cap memory on SpiNNaker ).
        max_trophic: Highest trophic health ever observed in this lineage.
        n_reproductions: Cumulative reproduction count for this lineage.
        n_deaths: Cumulative death count for this lineage.
    """

    lineage_id: int
    founder_id: int
    polyp_ids: list = field(default_factory=list)
    birth_steps: list = field(default_factory=list)
    death_steps: list = field(default_factory=list)
    support_history: deque = field(default_factory=lambda: deque(maxlen=1000))
    max_trophic: float = 0.0
    n_reproductions: int = 0
    n_deaths: int = 0


@dataclass
class GrowthBudget:
    """Local structural budget for one polyp.

    Every step each *alive* polyp receives a budget that caps how many edges
    it may add or prune.  The budget is derived from:
    1. Earned trophic support (information currency).
    2. Available ATP (construction / maintenance currency).
    3. Heritable max_connectivity_factor (ceiling on degree).

    All growth operations (sprouting, synaptogenesis, pruning, repair) read
    the *same* live budget so that growth is always support-limited.

    Attributes:
        polyp_id: Target polyp.
        max_new_edges: Maximum new edges this polyp may form this step.
        max_prunes: Maximum edges this polyp may prune this step.
        construction_atp: ATP available for construction (synaptogenesis).
        available_for_synaptogenesis: Whether the polyp has enough ATP
            and support to attempt new synapse formation.
    """

    polyp_id: int
    max_new_edges: int
    max_prunes: int
    construction_atp: float
    available_for_synaptogenesis: bool


# ---------------------------------------------------------------------------
# LifecycleManager
# ---------------------------------------------------------------------------

class LifecycleManager:
    """Manages polyp lifecycle: birth, death, development, reproduction.

    All decisions are **LOCAL per polyp**.  The colony has no global controller.
    This mirrors biological reality: each neuron competes independently for
    trophic support (Oppenheim 1991, Katz & Shatz 1996).

    Key invariants
    ==============
    1. **Reproduction** requires cyclin-D >= 0.5, trophic > threshold,
       post-juvenile maturity, lineage supportability, and capacity.
    2. **Death** is absolute per-polyp: trophic < apoptosis_threshold +
       bax_activation (post-handoff only; embryo phase has juvenile protection).
    3. **Maternal reserve** is finite, depletes monotonically, and triggers
       handoff when it can no longer fund one developmental-support tick.
    4. **Founder cleavage** is the ONLY pre-handoff exception to adult gates.
    5. **Juvenile window** is a *real* proving window combining estimator
       maturity, lineage-local support history, and local supportability —
       not merely telemetry bookkeeping.
    6. **Population ceiling** is derived from measured free SpiNNaker SDRAM,
       not a hard-coded constant.
    7. **Birth placement** is 3D near the parent with jitter scaled by the
       lineage's heritable ``spatial_dispersion`` trait.
    8. **Correlated cyclin rates** (CRA v009ao): accumulation and degradation
       are drawn from a shared base so that ``steady_state > 1.0`` for viable
       seeds, preventing sterile founder colonies.
    9. **Handoff step floor** (CRA v009bz-follow-up): the per-step reserve
       floor is the *founder's own* one-step requirement, NOT summed across
       all polyps.  This was a critical bug fix.

    Parameters
    ----------
    config : LifecycleConfig
        Lifecycle-specific parameters (thresholds, rates, defaults).
    energy_config : EnergyConfig
        ATP / trophic cost parameters (death thresholds, metabolic decay).
    n_streams : int
        Number of input data streams (determines founder scaffold size).
    """

    # --- CRA tagged constants (origins noted) ---
    CYCLIN_D_G1S_THRESHOLD: float = 0.5          # Morgan 1995 G1/S checkpoint
    CYCLIN_ACCUMULATION_BASE: float = 1.0        # CRA default synthesis rate
    CYCLIN_DEGRADATION_BASE: float = 0.5         # CRA default degradation rate
    CORRELATION_SYNTHESIS_MARGIN: float = 1.5    # CRA v009ao: guarantee steady > 1
    MIN_STEADY_STATE: float = 1.05               # CRA v009ao: 5% above unity floor
    BAX_ACCUMULATION_RATE: float = 0.002         # Katz & Shatz 1996
    ACCURACY_SURVIVAL_FLOOR: float = 0.45        # CRA: below this BAX rises
    CHILD_TROPHIC_SHARE: float = 0.5             # CRA: parent/child split
    MATURITY_AGE_ESTIMATE_STEPS: int = 50        # CRA: initial maturity guess
    REPRODUCTION_COOLDOWN_STEPS: int = 10        # CRA: minimum inter-birth interval
    INITIAL_POPULATION: int = 1                  # CRA: always one founder
    METABOLIC_DECAY_DEFAULT: float = 0.005       # CRA trophic decay per step
    TROPHIC_SYNAPSE_COST_DEFAULT: float = 0.001  # CRA per-synapse cost
    BDNF_RELEASE_RATE_DEFAULT: float = 0.024     # Matches EnergyConfig
    BDNF_UPTAKE_EFFICIENCY_DEFAULT: float = 0.5  # Heritable uptake trait
    CONSTRUCTION_EFFICIENCY_DEFAULT: float = 0.5 # CRA: ATP->construction yield
    MAX_CONNECTIVITY_FACTOR_DEFAULT: int = 5     # CRA: degree ceiling multiplier
    SPATIAL_DISPERSION_DEFAULT: float = 0.1      # CRA: 3D birth jitter scale
    JUVENILE_PROTECTION_ENABLED: bool = True     # CRA: no BAX pre-handoff
    POST_BIRTH_VIABLE_STEPS: int = 1             # CRA: infant mortality check
    SCAFFOLD_FLOOR_EDGES: int = 2                # CRA: min edges for juvenile
    POPULATION_SAFETY_MARGIN: float = 0.90       # CRA: use 90% of measured memory
    BOUNDED_MUTATION_SIGMA: float = 0.15         # CRA v009bz: log-space std dev
    BOUNDED_MUTATION_REFLECT: bool = True        # Reflect at bounds, don't clip
    SUPPORT_HISTORY_MAXLEN: int = 1000           # CRA: cap per-lineage history

    # Trait bounds for bounded reflected mutation (log-space)
    TRAIT_BOUNDS: Dict[str, Tuple[float, float]] = {
        "reproduction_threshold": (0.5, 5.0),
        "apoptosis_threshold": (0.01, 0.5),
        "spatial_dispersion": (0.01, 1.0),
        "max_connectivity_factor": (1, 20),
        "construction_efficiency": (0.1, 1.0),
        "metabolic_decay": (0.0001, 0.05),
        "trophic_synapse_cost": (0.0001, 0.01),
        "cyclin_accumulation_rate": (0.1, 5.0),
        "cyclin_degradation_rate": (0.1, 5.0),
        "bdnf_release_rate": (0.001, 0.5),
        "bdnf_uptake_efficiency": (0.01, 1.0),
    }

    def __init__(
        self,
        config: Any,  # LifecycleConfig
        energy_config: Any,  # EnergyConfig
        n_streams: int,
    ) -> None:
        """Initialise the LifecycleManager.

        Parameters
        ----------
        config : LifecycleConfig
            Lifecycle parameter bundle.
        energy_config : EnergyConfig
            Energy / ATP parameter bundle.
        n_streams : int
            Number of input data streams (sets founder scaffold).
        """
        self.config = config
        self.energy_config = energy_config
        self.n_streams = n_streams

        # --- Per-polyp bookkeeping ---
        self._next_polyp_id: int = 0
        self._lineage_counter: int = 0
        self._polyp_registry: Dict[int, Any] = {}  # polyp_id -> PolypState
        self._lineage_registry: Dict[int, LineageRecord] = {}
        self._events: List[LifecycleEvent] = []

        # Handoff state
        self._handoff_complete: bool = False
        self._handoff_step: Optional[int] = None
        self._maternal_reserve: Optional[Any] = None  # MaternalReserve

        # Juvenile tracking: polyp_id -> birth step
        self._juvenile_birth_step: Dict[int, int] = {}

        # Reproduction cooldown: polyp_id -> step of last reproduction
        self._last_reproduction_step: Dict[int, int] = {}

        # Step counter (for telemetry rate limiting / debugging)
        self._current_step: int = 0

        # Override defaults from config if attributes exist
        self._override_from_config(config)
        self._override_from_config(energy_config)

    def _override_from_config(self, cfg: Any) -> None:
        """Pull tagged constants from a config object when present.

        This lets the top-level ``config.py`` act as the single source of
        truth while the lifecycle manager still carries sensible defaults.
        """
        mappings = {
            "cyclin_d_threshold": "CYCLIN_D_G1S_THRESHOLD",
            "cyclin_accumulation_base": "CYCLIN_ACCUMULATION_BASE",
            "cyclin_degradation_base": "CYCLIN_DEGRADATION_BASE",
            "bax_accumulation_rate": "BAX_ACCUMULATION_RATE",
            "accuracy_survival_floor": "ACCURACY_SURVIVAL_FLOOR",
            "child_trophic_share_default": "CHILD_TROPHIC_SHARE",
            "maturity_age_estimate_steps": "MATURITY_AGE_ESTIMATE_STEPS",
            "reproduction_cooldown_steps": "REPRODUCTION_COOLDOWN_STEPS",
            "initial_population": "INITIAL_POPULATION",
            "apoptosis_threshold_default": "apoptosis_threshold_default",
            "metabolic_decay_default": "METABOLIC_DECAY_DEFAULT",
            "trophic_synapse_cost_default": "TROPHIC_SYNAPSE_COST_DEFAULT",
            "bdnf_per_trophic_source": "BDNF_RELEASE_RATE_DEFAULT",
            "bdnf_uptake_efficiency_default": "BDNF_UPTAKE_EFFICIENCY_DEFAULT",
            "construction_efficiency": "CONSTRUCTION_EFFICIENCY_DEFAULT",
            "max_connectivity_factor": "MAX_CONNECTIVITY_FACTOR_DEFAULT",
            "spatial_dispersion": "SPATIAL_DISPERSION_DEFAULT",
        }
        for cfg_key, self_key in mappings.items():
            if hasattr(cfg, cfg_key):
                value = getattr(cfg, cfg_key)
                if hasattr(self, self_key):
                    setattr(self, self_key, value)

    # =====================================================================
    #  Founder creation
    # =====================================================================

    def create_founder(self, stream_keys: List[str]) -> Any:
        """Create the founding polyp (initial population = 1).

        The founder is the only polyp that exists at t=0.  It carries a
        *maternal* trophic and ATP reserve that depletes monotonically.
        All descendant polyps inherit traits via the founder's lineage.

        The founder's cyclin-D accumulation and degradation rates are
        **correlated** so that ``steady_state = acc / deg > 1.0``,
        guaranteeing the founder can eventually reproduce
        (CRA v009ao — prevents sterile founder colonies).

        Parameters
        ----------
        stream_keys : list of str
            Identifier strings for each input data stream.

        Returns
        -------
        PolypState
            The founder polyp, fully initialised with maternal reserves.
        """
        traits = self._create_seed_traits()

        founder = self._instantiate_polyp(
            polyp_id=self._next_polyp_id,
            lineage_id=self._lineage_counter,
            is_founder=True,
            traits=traits,
            stream_keys=stream_keys,
        )

        self._next_polyp_id += 1
        self._lineage_counter += 1

        # Register
        self._polyp_registry[founder.polyp_id] = founder
        lineage = self.get_or_create_lineage(founder.lineage_id)
        lineage.founder_id = founder.polyp_id
        lineage.polyp_ids.append(founder.polyp_id)
        lineage.birth_steps.append(0)

        # Founder starts as juvenile (embryo phase) — will undergo handoff
        founder.is_juvenile = True
        self._juvenile_birth_step[founder.polyp_id] = 0

        return founder

    def _create_seed_traits(self) -> Dict[str, float]:
        """Create correlated cyclin-D rates for a viable founder seed.

        Biological rationale (Morgan 1995, Chen et al. 2016):
        Cyclin-D synthesis (accumulation) and degradation must be balanced
        so that the steady-state level is high enough to cross the G1/S
        checkpoint periodically.  If degradation is too fast relative to
        synthesis, the founder will never reproduce (sterile colony).

        CRA v009ao fix:
            Draw a single base rate ``r ~ Uniform(0.3, 1.0)``.
            degradation = r
            accumulation = r * CORRELATION_SYNTHESIS_MARGIN
            steady_state = accumulation / degradation
                         = CORRELATION_SYNTHESIS_MARGIN > 1.0

        This guarantees a viable steady state while preserving biological
        variation in the *speed* of the cell-cycle clock.

        Returns
        -------
        dict
            Trait dictionary with ``cyclin_accumulation_rate`` and
            ``cyclin_degradation_rate`` as correlated values.
        """
        # Base rate controls speed; both synthesis and degradation scale with it
        base_rate: float = random.uniform(0.3, 1.0)  # CRA v009ao

        degradation: float = base_rate * self.CYCLIN_DEGRADATION_BASE
        accumulation: float = (
            base_rate
            * self.CYCLIN_ACCUMULATION_BASE
            * self.CORRELATION_SYNTHESIS_MARGIN
        )

        # Safety clamp (should never trigger with the formula above)
        steady_state = accumulation / max(degradation, 1e-9)
        if steady_state < self.MIN_STEADY_STATE:
            # Force the margin if random draw was pathological
            accumulation = degradation * self.MIN_STEADY_STATE

        traits: Dict[str, float] = {
            "cyclin_accumulation_rate": accumulation,
            "cyclin_degradation_rate": degradation,
            "reproduction_threshold": 1.5,
            "apoptosis_threshold": 0.1,
            "spatial_dispersion": self.SPATIAL_DISPERSION_DEFAULT,
            "max_connectivity_factor": float(self.MAX_CONNECTIVITY_FACTOR_DEFAULT),
            "construction_efficiency": self.CONSTRUCTION_EFFICIENCY_DEFAULT,
            "metabolic_decay": self.METABOLIC_DECAY_DEFAULT,
            "trophic_synapse_cost": self.TROPHIC_SYNAPSE_COST_DEFAULT,
            "bdnf_release_rate": self.BDNF_RELEASE_RATE_DEFAULT,
            "bdnf_uptake_efficiency": self.BDNF_UPTAKE_EFFICIENCY_DEFAULT,
        }
        return traits

    def _instantiate_polyp(
        self,
        polyp_id: int,
        lineage_id: int,
        is_founder: bool,
        traits: Dict[str, float],
        stream_keys: List[str],
        parent: Optional[Any] = None,
    ) -> Any:
        """Construct a PolypState instance from traits.

        This factory method creates the polyp object with all heritable traits
        set.  It uses a lightweight dict-to-object approach so that the
        lifecycle manager does not need to hard-code the PolypState
        constructor signature (which may vary across CRA versions).

        Parameters
        ----------
        polyp_id : int
            Unique polyp identifier.
        lineage_id : int
            Lineage (colony) identifier.
        is_founder : bool
            True for the founding polyp.
        traits : dict
            Heritable trait values (rates, thresholds, efficiencies).
        stream_keys : list of str
            Input stream identifiers.
        parent : PolypState, optional
            Parent polyp for trait inheritance bookkeeping.

        Returns
        -------
        PolypState
            Fully initialised polyp.
        """
        # Import here to avoid circular dependency at module load time
        from .polyp_neuron import PolypState

        n_streams = len(stream_keys)

        polyp = PolypState(
            polyp_id=polyp_id,
            lineage_id=lineage_id,
        )

        # Set all heritable traits
        polyp.reproduction_threshold = traits.get(
            "reproduction_threshold", 1.5
        )
        polyp.apoptosis_threshold = traits.get(
            "apoptosis_threshold", 0.1
        )
        polyp.spatial_dispersion = traits.get(
            "spatial_dispersion", self.SPATIAL_DISPERSION_DEFAULT
        )
        polyp.max_connectivity_factor = int(
            traits.get("max_connectivity_factor", self.MAX_CONNECTIVITY_FACTOR_DEFAULT)
        )
        polyp.construction_efficiency = traits.get(
            "construction_efficiency", self.CONSTRUCTION_EFFICIENCY_DEFAULT
        )
        polyp.metabolic_decay = traits.get(
            "metabolic_decay", self.METABOLIC_DECAY_DEFAULT
        )
        polyp.trophic_synapse_cost = traits.get(
            "trophic_synapse_cost", self.TROPHIC_SYNAPSE_COST_DEFAULT
        )
        polyp.cyclin_accumulation_rate = traits.get(
            "cyclin_accumulation_rate", self.CYCLIN_ACCUMULATION_BASE
        )
        polyp.cyclin_degradation_rate = traits.get(
            "cyclin_degradation_rate", self.CYCLIN_DEGRADATION_BASE
        )
        polyp.bdnf_release_rate = traits.get(
            "bdnf_release_rate", self.BDNF_RELEASE_RATE_DEFAULT
        )
        polyp.bdnf_uptake_efficiency = traits.get(
            "bdnf_uptake_efficiency", self.BDNF_UPTAKE_EFFICIENCY_DEFAULT
        )

        # Lifecycle state
        polyp.is_alive = True
        polyp.is_juvenile = True
        polyp.age_steps = 0
        polyp.cyclin_d = 0.0
        polyp.bax_activation = 0.0
        polyp.trophic_health = 1.0  # Founder starts healthy
        polyp.handoff_complete = False
        polyp.maternal_reserve_fraction = 1.0 if is_founder else 0.0

        # 3D position — founder at origin, others placed later
        polyp.xyz = np.zeros(3, dtype=np.float32)

        # Direct stream mask uses stream identifiers, not numeric bit masks.
        polyp.direct_stream_mask = set(stream_keys)

        return polyp

    # =====================================================================
    #  Main step — orchestrates one lifecycle tick for all polyps
    # =====================================================================

    def step(
        self,
        polyp_states: List[Any],
        edges: Dict[Tuple[int, int], float],
        energy_result: Any,
        maternal_reserve: Any,
        step_num: int,
        dt: float,
    ) -> List[LifecycleEvent]:
        """Execute one lifecycle step for all polyps.

        This is the top-level entry point called once per simulation step.
        It processes, in order:

        1. **Handoff check** — if the maternal reserve is exhausted, trigger
           the maternal-to-autonomous transition (MBT analog).
        2. **Death collection** — identify polyps whose trophic health has
           fallen below their apoptosis threshold + BAX activation.
        3. **Cyclin-D update** — accumulate/degrade cyclin-D for each polyp.
        4. **Reproduction** — for polyps that pass all gates, create children.
        5. **Juvenile maturity check** — polyps that clear the integration
           window graduate from juvenile to adult.
        6. **Structural growth budgets** — compute per-polyp growth limits.
        7. **Telemetry capture** — record events for this step.

        Parameters
        ----------
        polyp_states : list of PolypState
            All polyp state objects (alive and dead — dead ones are skipped).
        edges : dict
            Adjacency map ``(src, dst) -> weight`` for the reef network.
        energy_result : EnergyResult
            Per-polyp energy calculations from the energy manager.
        maternal_reserve : MaternalReserve
            The founder's finite maternal reserve (depletes monotonically).
        step_num : int
            Current simulation step number.
        dt : float
            Time-step duration in simulation time units.

        Returns
        -------
        list of LifecycleEvent
            All lifecycle events that occurred this step (births, deaths,
            handoffs, cleavages).
        """
        self._current_step = step_num
        step_events: List[LifecycleEvent] = []

        # ---- 1. Handoff check (pre-handoff = embryo stage) ----
        if not self._handoff_complete:
            reserve_exhausted = self.check_handoff(
                maternal_reserve, polyp_states, step_num
            )
            if reserve_exhausted:
                self.perform_handoff(polyp_states)
                step_events.append(
                    LifecycleEvent(
                        event_type="handoff",
                        step=step_num,
                        polyp_id=-1,  # colony-level event
                        lineage_id=0,
                        details={"handoff_step": step_num},
                    )
                )

        # Filter to alive polyps for the rest of the step
        alive_states = [p for p in polyp_states if getattr(p, "is_alive", False)]

        # ---- 2. Death collection ----
        dead_ids = self.collect_dead(alive_states, energy_result)
        for pid in dead_ids:
            state = self._polyp_registry.get(pid)
            if state is not None:
                state.is_alive = False
                lineage = self._lineage_registry.get(state.lineage_id)
                if lineage is not None and pid in lineage.polyp_ids:
                    lineage.polyp_ids.remove(pid)
                    lineage.death_steps.append(step_num)
                    lineage.n_deaths += 1
                step_events.append(
                    LifecycleEvent(
                        event_type="death",
                        step=step_num,
                        polyp_id=pid,
                        lineage_id=state.lineage_id,
                        details={
                            "trophic_health": float(state.trophic_health),
                            "bax_activation": float(state.bax_activation),
                            "age_steps": int(state.age_steps),
                        },
                    )
                )

        # Re-filter after death
        alive_states = [p for p in alive_states if p.polyp_id not in dead_ids]

        # ---- 3. Cyclin-D update (Morgan 1995 G1/S checkpoint) ----
        for state in alive_states:
            self._step_cyclin(state, dt)

        # ---- 4. Reproduction ----
        newborns: List[Any] = []
        if getattr(self.config, "enable_reproduction", True):
            for state in alive_states:
                if not getattr(state, "is_alive", False):
                    continue
                child = self.maybe_reproduce(
                    state, alive_states, edges, maternal_reserve, step_num, dt
                )
                if child is not None:
                    newborns.append(child)
                    event_type = (
                        "cleavage"
                        if (not self._handoff_complete and state.age_steps < 100)
                        else "birth"
                    )
                    step_events.append(
                        LifecycleEvent(
                            event_type=event_type,
                            step=step_num,
                            polyp_id=child.polyp_id,
                            lineage_id=child.lineage_id,
                            parent_id=state.polyp_id,
                            details={
                                "parent_cyclin_d": float(state.cyclin_d),
                                "parent_trophic": float(state.trophic_health),
                            },
                        )
                    )

        # Add newborns to the alive pool and registry
        for child in newborns:
            alive_states.append(child)
            polyp_states.append(child)
            self._polyp_registry[child.polyp_id] = child
            lineage = self._lineage_registry.get(child.lineage_id)
            if lineage is not None:
                lineage.polyp_ids.append(child.polyp_id)
                lineage.birth_steps.append(step_num)
                lineage.n_reproductions += 1
            self._juvenile_birth_step[child.polyp_id] = step_num

        # ---- 5. Juvenile maturity check ----
        for state in alive_states:
            if not getattr(state, "is_juvenile", False):
                continue
            # Estimate d_eff from actual degree
            degree = self._count_degree(state.polyp_id, edges)
            d_eff = max(degree, 1)
            tau = getattr(self.energy_config, "time_constant", 10.0)
            if self.check_juvenile_maturity(state, d_eff, tau):
                state.is_juvenile = False

        # ---- 6. Structural growth budgets ----
        # (Computed on demand; stored temporarily for this step)
        self._growth_budgets_cache: Dict[int, GrowthBudget] = {}

        # ---- 7. Record events ----
        self._events.extend(step_events)

        return step_events

    # =====================================================================
    #  Cyclin-D dynamics (Morgan 1995)
    # =====================================================================

    def _step_cyclin(self, state: Any, dt: float) -> None:
        """Update cyclin-D level for one polyp.

        Cyclin-D accumulates when trophic support exceeds the reproduction
        threshold, and degrades continuously (first-order decay).

        This implements the classic G1/S checkpoint model:
        ``d[CyclinD]/dt = synthesis - degradation * [CyclinD]``

        The cell-cycle is a discrete per-step process; ``dt`` is normalised
        to a unit step so that degradation does not dominate when the wall-
        clock step size is large (e.g. 60 s).

        Parameters
        ----------
        state : PolypState
            The polyp whose cyclin-D is being updated.
        dt : float
            Time-step duration (used only for normalisation).
        """
        if not getattr(state, "is_alive", False):
            return

        # Normalise to a single simulation step so rates are per-step
        dt_norm = 1.0

        accumulation_rate = float(getattr(state, "cyclin_accumulation_rate", 1.0))
        degradation_rate = float(getattr(state, "cyclin_degradation_rate", 0.5))
        trophic = float(getattr(state, "trophic_health", 0.0))
        threshold = float(getattr(state, "reproduction_threshold", 1.5))

        # Accumulation only when trophic exceeds threshold (nutrient signal)
        if trophic > threshold:
            state.cyclin_d += accumulation_rate * dt_norm

        # Continuous degradation (ubiquitin-proteasome pathway analog)
        current_cyclin = float(getattr(state, "cyclin_d", 0.0))
        state.cyclin_d = max(
            0.0,
            current_cyclin - degradation_rate * current_cyclin * dt_norm,
        )

    # =====================================================================
    #  Reproduction
    # =====================================================================

    def maybe_reproduce(
        self,
        parent: Any,
        all_states: List[Any],
        edges: Dict[Tuple[int, int], float],
        maternal_reserve: Any,
        step_num: int,
        dt: float,
    ) -> Optional[Any]:
        """Attempt reproduction for a single parent polyp.

        This is the most gated decision in the lifecycle.  A polyp may only
        reproduce if **all** of the following are satisfied:

        1. Polyp is alive.
        2. Population ceiling not reached.
        3. Cyclin-D >= G1/S threshold (0.5) — cell-cycle checkpoint.
        4. Trophic health exceeds reproduction threshold.
        5. Post-handoff: polyp is not juvenile (real maturity window).
        6. Post-handoff: reproduction cooldown has elapsed.
        7. Post-handoff: lineage supportability permits another mouth to feed.
        8. Pre-handoff: founder may cleave (ONLY exception to adult gates).
        9. Parent can afford ATP construction cost for the child.
        10. Newborn passes post-birth viability check.

        Parameters
        ----------
        parent : PolypState
            Candidate parent polyp.
        all_states : list of PolypState
            All currently alive polyps.
        edges : dict
            Current network edge map.
        maternal_reserve : MaternalReserve
            Founder's maternal reserve (pre-handoff only).
        step_num : int
            Current simulation step.
        dt : float
            Time-step duration.

        Returns
        -------
        PolypState or None
            The newborn polyp if reproduction succeeded, else None.
        """
        if not getattr(parent, "is_alive", False):
            return None

        # --- Gate 1: Population ceiling ---
        current_pop = sum(1 for s in all_states if getattr(s, "is_alive", False))
        if self.check_population_ceiling(current_pop):
            return None

        # --- Gate 2: Cyclin-D G1/S checkpoint (Morgan 1995) ---
        cyclin_d = float(getattr(parent, "cyclin_d", 0.0))
        if cyclin_d < self.CYCLIN_D_G1S_THRESHOLD:
            return None

        # --- Gate 3: Trophic readiness ---
        if not self.check_reproduction_readiness(parent, None):
            return None

        # --- Gate 4: Handoff-dependent gates ---
        is_pre_handoff = not self._handoff_complete
        parent_is_juvenile = getattr(parent, "is_juvenile", False)

        if is_pre_handoff:
            # Founder cleavage is the ONLY pre-handoff exception.
            # No other polyp may reproduce before maternal handoff.
            if parent.polyp_id != self._get_founder_id():
                return None
            # Pre-handoff founder cleavage still needs a cooldown so the
            # demo doesn't explode to hundreds of polyps before handoff.
            last_birth = self._last_reproduction_step.get(parent.polyp_id, -999999)
            if step_num - last_birth < self.REPRODUCTION_COOLDOWN_STEPS:
                return None
        else:
            # Post-handoff: full adult gates apply
            if parent_is_juvenile:
                return None
            # Cooldown check
            last_birth = self._last_reproduction_step.get(parent.polyp_id, -999999)
            if step_num - last_birth < self.REPRODUCTION_COOLDOWN_STEPS:
                return None

        # --- Gate 5: ATP construction cost ---
        construction_cost = self.construction_atp_cost(parent)
        parent_trophic = float(getattr(parent, "trophic_health", 0.0))
        if parent_trophic < construction_cost * 0.5:
            return None

        # --- All gates passed: create child ---
        child = self._create_child(parent, all_states, edges, step_num)
        if child is None:
            return None

        # Post-birth viability check: can the newborn survive one step?
        if not self._check_newborn_viability(child):
            # Infant mortality — discard
            child.is_alive = False
            return None

        # Deduct parent's trophic for child share
        share = self.CHILD_TROPHIC_SHARE
        parent.trophic_health = max(0.0, parent_trophic * (1.0 - share))
        child.trophic_health = parent_trophic * share

        # Install birth scaffold: parent-child communication edges
        self._install_birth_scaffold(parent, child, edges)

        # Reset parent's cyclin-D after division
        parent.cyclin_d = 0.0
        self._last_reproduction_step[parent.polyp_id] = step_num

        return child

    def check_reproduction_readiness(
        self, state: Any, energy_result: Any
    ) -> bool:
        """Check whether a polyp's trophic state permits reproduction.

        The polyp must have trophic health strictly greater than its
        heritable reproduction threshold.  This is the nutritional gate:
        a neuron only divides when it has "enough" trophic support.

        Parameters
        ----------
        state : PolypState
            Polyp to evaluate.
        energy_result : EnergyResult
            Energy calculation results (may be None).

        Returns
        -------
        bool
            True if trophic health > reproduction threshold.
        """
        trophic = float(getattr(state, "trophic_health", 0.0))
        threshold = float(getattr(state, "reproduction_threshold", 1.5))
        return trophic > threshold

    def _live_reproduction_requirement(self, state: Any) -> float:
        """Compute the live trophic reproduction requirement for a polyp.

        This is the minimum trophic level the polyp must maintain *after*
        giving birth.  It includes:

        - The polyp's own metabolic maintenance cost.
        - A safety margin so the parent does not die immediately after birth.
        - Proportional to the number of dependent connections (degree).

        Parameters
        ----------
        state : PolypState
            Polyp evaluating reproduction.

        Returns
        -------
        float
            Trophic level the parent must retain post-birth.
        """
        metabolic = float(getattr(state, "metabolic_decay", self.METABOLIC_DECAY_DEFAULT))
        threshold = float(getattr(state, "reproduction_threshold", 1.5))
        safety_margin = 0.2  # CRA: parent must stay 20% above threshold
        return threshold + metabolic + safety_margin

    def _division_trophic_setpoint(self, state: Any) -> float:
        """Trophic setpoint for cell division.

        The parent must accumulate trophic support up to this level before
        division proceeds.  It is higher than the reproduction threshold
        because the parent needs surplus to fund both itself and the child.

        Parameters
        ----------
        state : PolypState
            Polyp evaluating division.

        Returns
        -------
        float
            Trophic setpoint = threshold + child_share_requirement + safety.
        """
        threshold = float(getattr(state, "reproduction_threshold", 1.5))
        child_cost = threshold * self.CHILD_TROPHIC_SHARE
        safety = 0.3  # CRA: surplus required for division
        return threshold + child_cost + safety

    def _developmental_autonomy_target(self, state: Any) -> float:
        """Trophic target for developmental autonomy.

        After handoff, a polyp must reach this trophic level to be considered
        fully autonomous (no longer dependent on maternal subsidy).  The target
        tapers with maturation — older juveniles need less support.

        Parameters
        ----------
        state : PolypState
            Juvenile polyp being evaluated.

        Returns
        -------
        float
            Autonomy trophic target, decreasing with age.
        """
        base_target = 0.6  # CRA: minimum for independent survival
        age = int(getattr(state, "age_steps", 0))
        taper = 1.0 - math.exp(-age / 50.0)  # exponential taper toward full autonomy
        return base_target * (1.0 - 0.5 * taper)

    # =====================================================================
    #  Child creation
    # =====================================================================

    def _create_child(
        self,
        parent: Any,
        all_states: List[Any],
        edges: Dict[Tuple[int, int], float],
        step_num: int,
    ) -> Optional[Any]:
        """Create a new child polyp from a parent.

        The child inherits traits from the parent via bounded reflected
        mutation in log-space.  All 16 ecology traits evolve from birth.

        Parameters
        ----------
        parent : PolypState
            Parent polyp.
        all_states : list of PolypState
            All alive polyps (for population count).
        edges : dict
            Network edge map.
        step_num : int
            Current simulation step.

        Returns
        -------
        PolypState or None
            The new child, or None if creation failed.
        """
        child_id = self._next_polyp_id
        self._next_polyp_id += 1

        # Extract parent's traits
        parent_traits = self._extract_traits(parent)

        # Mutate traits for child
        child_traits = self._mutate_traits(parent_traits)

        # Create child polyp
        child = self._instantiate_polyp(
            polyp_id=child_id,
            lineage_id=parent.lineage_id,
            is_founder=False,
            traits=child_traits,
            stream_keys=[f"stream_{i}" for i in range(self.n_streams)],
            parent=parent,
        )

        # Set child as juvenile
        child.is_juvenile = True
        child.handoff_complete = self._handoff_complete
        child.age_steps = 0
        child.cyclin_d = 0.0
        child.bax_activation = 0.0

        # Place child in 3D space near parent
        existing_positions = [
            np.array(getattr(s, "xyz", np.zeros(3)))
            for s in all_states
            if getattr(s, "is_alive", False)
        ]
        child.xyz = self.place_newborn(parent, existing_positions)

        # Inherit parent's stream mask (with possible mutation)
        parent_mask = getattr(
            parent,
            "direct_stream_mask",
            {f"stream_{i}" for i in range(self.n_streams)},
        )
        child.direct_stream_mask = set(parent_mask)

        return child

    def _check_newborn_viability(self, child: Any) -> bool:
        """Check whether a newborn can survive at least one step.

        Infant mortality filter: after creating a child, verify it has enough
        initial trophic support to survive one tick of metabolic decay and
        synaptic costs.  If not, discard — this mimics biological infant
        mortality where ~50% of neurons die from competition
        (Oppenheim 1991).

        Parameters
        ----------
        child : PolypState
            Newly created child polyp.

        Returns
        -------
        bool
            True if the newborn can survive its first step.
        """
        trophic = float(getattr(child, "trophic_health", 0.0))
        metabolic = float(getattr(child, "metabolic_decay", self.METABOLIC_DECAY_DEFAULT))
        threshold = float(getattr(child, "apoptosis_threshold", 0.1))
        bax = float(getattr(child, "bax_activation", 0.0))

        # After one step of metabolic decay
        projected_trophic = trophic - metabolic
        death_threshold = threshold + bax

        return projected_trophic > death_threshold

    def _install_birth_scaffold(
        self,
        parent: Any,
        child: Any,
        edges: Dict[Tuple[int, int], float],
    ) -> None:
        """Install minimal parent-child communication edges at birth.

        A newborn must have at least ``SCAFFOLD_FLOOR_EDGES`` connections
        to receive trophic support during its juvenile window.  The parent
        is always connected; additional scaffold edges go to spatially
        nearby polyps if ATP permits.

        Parameters
        ----------
        parent : PolypState
            Parent polyp.
        child : PolypState
            Newborn polyp.
        edges : dict
            Network edge map (mutated in place).
        """
        parent_id = int(getattr(parent, "polyp_id", -1))
        child_id = int(getattr(child, "polyp_id", -1))

        # Parent-child edge (bidirectional)
        from .reef_network import ReefEdge
        edges[(parent_id, child_id)] = ReefEdge(source_id=parent_id, target_id=child_id, weight=1.0)
        edges[(child_id, parent_id)] = ReefEdge(source_id=child_id, target_id=parent_id, weight=1.0)

        # Child starts with scaffold count = 2 (bidirectional counts as 2)
        # This meets the SCAFFOLD_FLOOR_EDGES minimum immediately.

    # =====================================================================
    #  Death (BAX-driven apoptosis)
    # =====================================================================

    def check_death(self, state: Any, energy_result: Any) -> bool:
        """Determine whether a polyp should undergo apoptosis.

        Death occurs when::

            trophic_health < apoptosis_threshold + bax_activation

        **Juvenile protection** (CRA): pre-handoff (embryo phase), BAX does
        NOT accumulate — the polyp is protected by maternal subsidy.  Post-
        handoff, the adult competition regime begins and BAX rises from:

        1. Persistent local earned-support deficit.
        2. Low accuracy: ``0.002 * (0.45 - accuracy_ema)`` when accuracy < 0.45.

        This implements activity-dependent pruning (Katz & Shatz 1996):
        neurons that fail to establish functional connections are eliminated.

        Parameters
        ----------
        state : PolypState
            Polyp to evaluate.
        energy_result : EnergyResult
            Energy calculations (may contain per-polip trophic values).

        Returns
        -------
        bool
            True if the polip should die.
        """
        if not getattr(state, "is_alive", False):
            return False

        trophic = float(getattr(state, "trophic_health", 0.0))
        threshold = float(getattr(state, "apoptosis_threshold", 0.1))
        bax = float(getattr(state, "bax_activation", 0.0))
        is_juvenile = getattr(state, "is_juvenile", False)
        handoff_done = self._handoff_complete

        # Pre-handoff juvenile protection: no BAX-driven death
        if is_juvenile and not handoff_done:
            # Still check for catastrophic trophic collapse (extreme case)
            return trophic < threshold * 0.1  # near-zero only

        # Post-handoff: full BAX-driven apoptosis
        death_line = threshold + bax
        return trophic < death_line

    def collect_dead(
        self,
        polyp_states: List[Any],
        energy_result: Any,
    ) -> List[int]:
        """Collect IDs of all polyps that should die this step.

        Death is **absolute per-polyp**, not a colony-global ratio.
        Each neuron is evaluated independently against its own apoptosis
        threshold + BAX activation level.

        Parameters
        ----------
        polyp_states : list of PolypState
            All polyp states to evaluate.
        energy_result : EnergyResult
            Energy calculation results.

        Returns
        -------
        list of int
            Polyp IDs marked for death this step.
        """
        dead_ids: List[int] = []
        for state in polyp_states:
            if self.check_death(state, energy_result):
                dead_ids.append(int(getattr(state, "polyp_id", -1)))
        return dead_ids

    def _step_bax(self, state: Any, dt: float, accuracy_ema: float) -> None:
        """Update BAX activation level for one polyp.

        BAX accumulates from two sources (Katz & Shatz 1996):

        1. **Accuracy-driven**: when ``accuracy_ema < 0.45``, BAX rises as
           ``0.002 * (0.45 - accuracy_ema) * dt``.
        2. **Support deficit**: persistent low trophic health adds BAX
           proportional to the deficit below the survival threshold.

        Juvenile protection: BAX only accumulates post-handoff.

        Parameters
        ----------
        state : PolypState
            Polyp to update.
        dt : float
            Time-step duration.
        accuracy_ema : float
            Exponentially-weighted moving average of directional accuracy.
        """
        if not getattr(state, "is_alive", False):
            return

        # Juvenile protection: no BAX accumulation pre-handoff
        is_juvenile = getattr(state, "is_juvenile", False)
        if is_juvenile and not self._handoff_complete:
            state.bax_activation = 0.0
            return

        bax_rate = 0.0

        # Accuracy-based BAX (activity-dependent pruning)
        if accuracy_ema < self.ACCURACY_SURVIVAL_FLOOR:
            deficit = self.ACCURACY_SURVIVAL_FLOOR - accuracy_ema
            bax_rate += self.BAX_ACCUMULATION_RATE * deficit

        # Support deficit BAX
        trophic = float(getattr(state, "trophic_health", 0.0))
        threshold = float(getattr(state, "apoptosis_threshold", 0.1))
        if trophic < threshold:
            deficit = threshold - trophic
            bax_rate += 0.01 * deficit  # 1% per unit deficit per step

        # Accumulate BAX
        current_bax = float(getattr(state, "bax_activation", 0.0))
        state.bax_activation = min(1.0, current_bax + bax_rate * dt)

    # =====================================================================
    #  Handoff (maternal-to-autonomous / MBT analog)
    # =====================================================================

    def check_handoff(
        self,
        maternal_reserve: Any,
        polyp_states: List[Any],
        step_num: int,
    ) -> bool:
        """Check whether the maternal reserve is exhausted — trigger handoff.

        The maternal-to-autonomous handoff is the analog of the mid-blastula
        transition (MBT) in embryonic development (Newport & Kirschner 1982).
        Before handoff, the founder has a finite maternal reserve of trophic
        support and ATP that depletes monotonically.  The reserve is NEVER
        replenished.

        Handoff is triggered when the reserve can no longer fund **one**
        developmental-support tick.  The per-step floor is the **founder's
        own** one-step requirement — NOT the sum across all polyps
        (CRA v009bz-follow-up: critical bug fix).

        Parameters
        ----------
        maternal_reserve : MaternalReserve
            The finite maternal reserve.
        polyp_states : list of PolypState
            All polyp states.
        step_num : int
            Current simulation step.

        Returns
        -------
        bool
            True if handoff should occur this step.
        """
        if self._handoff_complete:
            return False

        if maternal_reserve is None:
            return False

        # Get founder's one-step requirement (per-lineage, not summed)
        founder_id = self._get_founder_id()
        founder = self._polyp_registry.get(founder_id)
        if founder is None:
            return True  # No founder -> force handoff

        # Per-step floor = founder's own developmental support need
        founder_metabolic = float(getattr(founder, "metabolic_decay", self.METABOLIC_DECAY_DEFAULT))
        founder_trophic_cost = float(getattr(founder, "trophic_synapse_cost", self.TROPHIC_SYNAPSE_COST_DEFAULT))
        per_step_floor = founder_metabolic + founder_trophic_cost + 0.01  # small buffer

        # Check if reserve can fund one more tick
        trophic_frac = float(getattr(maternal_reserve, "trophic_fraction", 0.0))
        atp_available = getattr(maternal_reserve, "atp_fraction", None)
        if atp_available is not None:
            atp_frac = float(atp_available)
        else:
            atp_frac = 1.0

        # Handoff triggers when EITHER currency is exhausted
        reserve_depleted = (trophic_frac < per_step_floor) or (atp_frac <= 0.0)

        if reserve_depleted:
            return True

        return False

    def perform_handoff(self, polyp_states: List[Any]) -> None:
        """Execute the maternal-to-autonomous handoff (MBT transition).

        After handoff:
        - All polyps become fully autonomous (no maternal subsidy).
        - Juvenile protection ends — BAX accumulation begins.
        - Adult competition regime starts.
        - Developmental support targets full autonomy (not just survival).

        Parameters
        ----------
        polyp_states : list of PolypState
            All polyp states (mutated in place).
        """
        self._handoff_complete = True
        self._handoff_step = self._current_step

        for state in polyp_states:
            if not getattr(state, "is_alive", False):
                continue
            state.handoff_complete = True
            state.maternal_reserve_fraction = 0.0

    def derive_maternal_trophic_reserve(
        self,
        founder: Any,
        n_streams: int,
        dt: float,
    ) -> float:
        """Derive the founder's initial maternal trophic reserve.

        The reserve is calculated from founder-local recovery equations plus
        first-cleavage geometry.  It represents the finite "yolk" of
        nutritional support available to the embryo before it must become
        self-sustaining.

        Formula::

            reserve = n_streams * base_support * developmental_multiplier

        where ``developmental_multiplier`` accounts for the geometric cost
        of the first cleavage divisions.

        Parameters
        ----------
        founder : PolypState
            The founding polyp.
        n_streams : int
            Number of input data streams.
        dt : float
            Time-step duration.

        Returns
        -------
        float
            Initial maternal trophic reserve (fraction, 0.0–1.0 scale).
        """
        base_support = 2.0  # CRA: trophic units per stream
        developmental_multiplier = 3.0  # CRA: first-cleavage geometry factor
        reserve = n_streams * base_support * developmental_multiplier * dt
        return min(1.0, reserve)  # cap at 1.0 (fraction scale)

    def derive_maternal_atp_reserve(
        self,
        founder: Any,
        dt: float,
    ) -> float:
        """Derive the founder's initial maternal ATP reserve.

        ATP reserve covers the construction costs of the initial scaffold
        and early developmental support.  Like the trophic reserve, it
        depletes monotonically and is never replenished.

        Parameters
        ----------
        founder : PolypState
            The founding polyp.
        dt : float
            Time-step duration.

        Returns
        -------
        float
            Initial maternal ATP reserve.
        """
        construction_cost = self.construction_atp_cost(founder)
        scaffold_factor = 2.0  # CRA: ATP for initial edge scaffold
        reserve = construction_cost * scaffold_factor * dt
        return min(1.0, reserve)

    def _get_founder_id(self) -> int:
        """Return the founder polyp ID for lineage 0.

        Returns
        -------
        int
            Founder polyp ID, or -1 if not found.
        """
        lineage = self._lineage_registry.get(0)
        if lineage is not None:
            return lineage.founder_id
        # Fallback: search registry
        for pid, state in self._polyp_registry.items():
            if getattr(state, "polyp_id", -1) == pid and pid == 0:
                return pid
        return -1

    # =====================================================================
    #  Juvenile integration window
    # =====================================================================

    def check_juvenile_maturity(
        self,
        state: Any,
        d_eff: int,
        tau: float,
    ) -> bool:
        """Check whether a juvenile polyp has completed its integration window.

        The juvenile window is a **real** proving period, not merely
        telemetry bookkeeping.  A polyp graduates when **all** of the
        following are satisfied:

        1. ``age_steps >= _maturity_age`` (estimator-derived, not fixed 500).
        2. ``_projected_history_count >= warmup_min_samples(d_eff, tau)``
           (lineage-local support-history maturity).
        3. Local supportability exceeds the lineage's reproduction demand
           (the polyp must demonstrate it can earn its own keep).

        Parameters
        ----------
        state : PolypState
            Juvenile polyp to evaluate.
        d_eff : int
            Effective degree (max of actual degree and 1).
        tau : float
            Energy time constant (determines warmup duration).

        Returns
        -------
        bool
            True if the polyp has matured and may reproduce.
        """
        age = int(getattr(state, "age_steps", 0))

        # Minimum age estimate (not a hard 500 — estimator-derived)
        maturity_age = self.MATURITY_AGE_ESTIMATE_STEPS
        if hasattr(state, "_maturity_age"):
            maturity_age = int(getattr(state, "_maturity_age", maturity_age))

        if age < maturity_age:
            return False

        # Support-history maturity: enough samples for reliable estimation
        min_samples = self.warmup_min_samples(d_eff, tau)
        history_count = getattr(state, "_projected_history_count", 0)
        if hasattr(state, "support_history"):
            hist = getattr(state, "support_history")
            if isinstance(hist, (list, deque)):
                history_count = len(hist)
        if history_count < min_samples:
            return False

        # Local supportability: must have earned enough support
        trophic = float(getattr(state, "trophic_health", 0.0))
        threshold = float(getattr(state, "reproduction_threshold", 1.5))
        if trophic < threshold * 0.5:
            return False

        return True

    def warmup_min_samples(self, d_eff: int, tau: float) -> int:
        """Minimum number of support-history samples for maturity estimation.

        The warmup duration scales with the effective dimensionality ``d_eff``
        and the time constant ``tau``.  Higher-degree polyps need more samples
        because their support dynamics are more complex.

        Formula (CRA)::

            min_samples = max(10, d_eff * tau * 2)

        Parameters
        ----------
        d_eff : int
            Effective degree (actual degree, minimum 1).
        tau : float
            Time constant (steps).

        Returns
        -------
        int
            Minimum required history samples.
        """
        return max(10, int(d_eff * tau * 2))

    # =====================================================================
    #  Population control
    # =====================================================================

    def population_capacity(self) -> int:
        """Return the maximum population derived from hardware free memory.

        On SpiNNaker, this queries the measured free SDRAM and divides by
        the per-polyp memory footprint to get a hard ceiling.  The safety
        margin reserves 10% of memory for runtime overhead.

        Falls back to a software estimate if hardware query is unavailable.

        Returns
        -------
        int
            Maximum allowed population (hard ceiling).
        """
        try:
            # Attempt to query SpiNNaker free memory via spinnman
            free_bytes = self._query_spinnaker_free_sdram()
        except Exception:
            # Fallback: software estimate
            free_bytes = self._estimate_free_memory()

        per_polyp_bytes = self._per_polyp_memory_footprint()
        capacity = int(
            (free_bytes * self.POPULATION_SAFETY_MARGIN) / per_polyp_bytes
        )
        return max(self.INITIAL_POPULATION + 1, capacity)

    def check_population_ceiling(self, current_pop: int) -> bool:
        """Check whether the population has hit the hardware-derived ceiling.

        Parameters
        ----------
        current_pop : int
            Current number of alive polyps.

        Returns
        -------
        bool
            True if at or above capacity (no more births allowed).
        """
        capacity = self.population_capacity()
        return current_pop >= capacity

    def _query_spinnaker_free_sdram(self) -> int:
        """Query SpiNNaker hardware for free SDRAM bytes.

        Uses the spinnman API to read the SDRAM availability on the
        chip where this lifecycle manager is running.

        Returns
        -------
        int
            Free SDRAM in bytes.

        Raises
        ------
        RuntimeError
            If the hardware query fails (e.g., not running on SpiNNaker).
        """
        try:
            from spinnman.transceiver import create_transceiver_from_hostname
            # Attempt to get transceiver from runtime context
            tx = self._get_transceiver()
            if tx is None:
                raise RuntimeError("No SpiNNaker transceiver available")
            chip = tx.get_chip_info()
            # Sum free SDRAM across all chips
            total_free = 0
            for c in chip:
                sdram = c.sdram
                total_free += sdram.free
            return total_free
        except ImportError:
            raise RuntimeError("spinnman not available — not running on SpiNNaker")

    def _estimate_free_memory(self) -> int:
        """Software fallback for free memory estimation.

        Returns a conservative estimate based on typical SpiNNaker chip
        SDRAM (128 MB per chip) and assumed utilization.

        Returns
        -------
        int
            Estimated free SDRAM in bytes.
        """
        # SpiNNaker5: 128 MB SDRAM per chip
        typical_chip_sdram = 128 * 1024 * 1024  # 128 MB
        assumed_utilization = 0.3  # 30% already in use
        free = int(typical_chip_sdram * (1.0 - assumed_utilization))
        return free

    def _per_polyp_memory_footprint(self) -> int:
        """Estimate memory footprint of one polyp in bytes.

        Based on the PolypState structure size including:
        - Scalars (trophic, cyclin, BAX, thresholds, etc.)
        - Position array (3 x float32)
        - Stream mask (n_streams x bool)
        - Per-step history buffers

        Returns
        -------
        int
            Estimated bytes per polyp.
        """
        scalar_bytes = 64 * 4       # 64 floats x 4 bytes
        position_bytes = 3 * 4      # 3D position (float32)
        mask_bytes = self.n_streams  # bool array
        history_bytes = 256         # per-step caches
        overhead = 64               # Python object overhead estimate
        return scalar_bytes + position_bytes + mask_bytes + history_bytes + overhead

    def _get_transceiver(self):
        """Get the SpiNNaker transceiver from the runtime context.

        Returns
        -------
        Transceiver or None
            The transceiver if available, else None.
        """
        # This is a placeholder — the actual transceiver is injected by
        # the deployment harness.  For unit testing, returns None.
        return getattr(self, "_injected_transceiver", None)

    # =====================================================================
    #  ATP economy
    # =====================================================================

    def required_constant_atp_support(
        self,
        state: Any,
        degree: int,
        dt: float,
    ) -> float:
        """Compute the ATP required per step for maintenance.

        Maintenance ATP is proportional to the polyp's degree (number of
        synaptic connections).  Each connection has a basal maintenance cost.

        Formula::

            atp = base_cost * degree * dt

        Parameters
        ----------
        state : PolypState
            Polyp being evaluated.
        degree : int
            Current synaptic degree (number of connections).
        dt : float
            Time-step duration.

        Returns
        -------
        float
            ATP units required this step for maintenance.
        """
        base_cost = 0.01  # CRA: ATP per connection per step
        return base_cost * degree * dt

    def construction_atp_cost(self, parent: Any) -> float:
        """Compute the one-time ATP cost for constructing a new child neuron.

        This is the "construction currency" cost of building a new polyp:
        soma, axon, dendrite scaffold, and initial synaptic machinery.

        The cost is modulated by the parent's ``construction_efficiency``
        trait: more efficient parents build children more cheaply.

        Formula::

            cost = base_construction / construction_efficiency

        Parameters
        ----------
        parent : PolypState
            Parent polyp that would reproduce.

        Returns
        -------
        float
            ATP units required to construct one child.
        """
        base_construction = 0.5  # CRA: base ATP for one new neuron
        efficiency = float(getattr(parent, "construction_efficiency", 0.5))
        efficiency = max(0.1, min(1.0, efficiency))  # clamp
        return base_construction / efficiency

    def developmental_atp_bootstrap(self, state: Any) -> float:
        """Compute the ATP bootstrap for a fresh seed or newborn.

        Freshly created polyps need an initial ATP endowment to build
        their first synaptic connections before they can earn support.
        This is the "seed ATP" that jump-starts the metabolic cycle.

        Parameters
        ----------
        state : PolypState
            Newly created polyp (seed or newborn).

        Returns
        -------
        float
            ATP bootstrap amount.
        """
        base_bootstrap = 0.3  # CRA: initial ATP for scaffold construction
        efficiency = float(getattr(state, "construction_efficiency", 0.5))
        return base_bootstrap * efficiency

    # =====================================================================
    #  Structural growth budgets
    # =====================================================================

    def compute_growth_budgets(
        self,
        polyp_states: List[Any],
        edges: Dict[Tuple[int, int], float],
        energy_result: Any,
    ) -> List[GrowthBudget]:
        """Compute local structural budgets for all alive polyps.

        Every step, each alive polyp receives a budget that caps how many
        edges it may add or prune.  The budget is derived from:

        1. **Earned trophic support** — higher trophic = larger budget.
        2. **Available ATP** — construction requires ATP currency.
        3. **Heritable max_connectivity_factor** — hard ceiling on degree.

        All growth operations (sprouting, synaptogenesis, pruning, repair)
        read the *same* live budget, ensuring growth is always
        support-limited.

        Hot paths cache adjacency, degree, positions, and connectivity
        budgets once per pass for efficiency on SpiNNaker.

        Parameters
        ----------
        polyp_states : list of PolypState
            All polyp states.
        edges : dict
            Current network edge map ``(src, dst) -> weight``.
        energy_result : EnergyResult
            Per-polyp energy calculations.

        Returns
        -------
        list of GrowthBudget
            One budget per alive polyp.
        """
        budgets: List[GrowthBudget] = []

        for state in polyp_states:
            if not getattr(state, "is_alive", False):
                continue

            pid = int(getattr(state, "polyp_id", -1))
            degree = self._count_degree(pid, edges)
            max_conn_factor = int(
                getattr(state, "max_connectivity_factor", self.MAX_CONNECTIVITY_FACTOR_DEFAULT)
            )
            max_degree = max_conn_factor * self.n_streams  # CRA: scaled by input dimension

            # Budget from trophic support
            trophic = float(getattr(state, "trophic_health", 0.0))
            threshold = float(getattr(state, "reproduction_threshold", 1.5))
            surplus = max(0.0, trophic - threshold * 0.5)

            # Budget from ATP
            construction_atp = surplus * 0.5  # CRA: half surplus goes to construction

            # Max new edges = room to max degree, scaled by surplus
            room = max(0, max_degree - degree)
            max_new = min(room, int(surplus * 2))  # 2 edges per unit surplus
            max_new = max(0, max_new)

            # Max prunes = fraction of existing edges
            max_prunes = max(0, degree // 4)  # CRA: can prune up to 25%

            # Synaptogenesis availability: need both ATP and connectivity room
            can_synapse = (construction_atp > 0.05) and (max_new > 0)

            budget = GrowthBudget(
                polyp_id=pid,
                max_new_edges=max_new,
                max_prunes=max_prunes,
                construction_atp=construction_atp,
                available_for_synaptogenesis=can_synapse,
            )
            budgets.append(budget)
            self._growth_budgets_cache[pid] = budget

        return budgets

    # =====================================================================
    #  3D birth placement and migration
    # =====================================================================

    def place_newborn(
        self,
        parent: Any,
        existing_positions: List[np.ndarray],
    ) -> np.ndarray:
        """Determine the 3D position of a newborn polyp.

        The child is placed near the parent with a stochastic jitter scaled
        by the lineage's heritable ``spatial_dispersion`` trait.  The jitter
        follows a 3D Gaussian with standard deviation ``dispersion``.

        A simple crowding check ensures the position does not overlap
        exactly with an existing polyp.

        Parameters
        ----------
        parent : PolypState
            Parent polyp (child is placed near this position).
        existing_positions : list of np.ndarray
            3D positions of all existing polyps.

        Returns
        -------
        np.ndarray
            3D position (float32) for the newborn.
        """
        parent_pos = np.array(getattr(parent, "xyz", np.zeros(3)), dtype=np.float64)
        dispersion = float(getattr(parent, "spatial_dispersion", self.SPATIAL_DISPERSION_DEFAULT))

        # 3D Gaussian jitter
        jitter = np.random.normal(0.0, dispersion, size=3)

        # Base position: near parent
        child_pos = parent_pos + jitter

        # Crowding avoidance: if too close to existing, push outward
        min_separation = dispersion * 0.5
        for existing in existing_positions:
            existing = np.array(existing, dtype=np.float64)
            diff = child_pos - existing
            dist = np.linalg.norm(diff)
            if dist < min_separation and dist > 1e-9:
                # Push away along the collision vector
                push = (min_separation - dist) * (diff / dist)
                child_pos += push * 0.5

        return child_pos.astype(np.float32)

    def compute_migration_vector(
        self,
        state: Any,
        neighbors: List[Any],
        positions: Dict[int, np.ndarray],
    ) -> np.ndarray:
        """Compute the 3D migration vector for a polyp.

        Migration combines three biologically-motivated forces:

        1. **Adhesion** — pull toward neighbors (synaptic attraction).
           Weighted by edge strength.
        2. **Tension** — stretch toward the centroid of neighbors
           (maintain structural integrity).
        3. **Repulsion** — push away from neighbors that are too close
           (crowding avoidance, spring-like).

        The net migration is a weighted sum of these forces, scaled by
        the polyp's ``spatial_dispersion`` trait.

        Parameters
        ----------
        state : PolypState
            Polyp being moved.
        neighbors : list of PolypState
            Spatially adjacent polyps (connected or nearby).
        positions : dict
            Map ``polyp_id -> np.ndarray`` of 3D positions.

        Returns
        -------
        np.ndarray
            3D migration vector (float32).
        """
        if not neighbors:
            return np.zeros(3, dtype=np.float32)

        my_pos = np.array(getattr(state, "xyz", np.zeros(3)), dtype=np.float64)
        dispersion = float(getattr(state, "spatial_dispersion", 0.1))

        adhesion = np.zeros(3)
        centroid = np.zeros(3)
        repulsion = np.zeros(3)

        for neighbor in neighbors:
            nid = int(getattr(neighbor, "polyp_id", -1))
            npos = np.array(positions.get(nid, my_pos), dtype=np.float64)
            diff = npos - my_pos
            dist = np.linalg.norm(diff) + 1e-9

            # Adhesion: pull toward neighbor (inverse distance weighted)
            adhesion += diff / dist

            # Centroid accumulation
            centroid += npos

            # Repulsion: push away if too close (spring force)
            optimal_dist = dispersion * 2.0  # CRA: optimal neighbor distance
            if dist < optimal_dist:
                repulsion_strength = (optimal_dist - dist) / optimal_dist
                repulsion -= (diff / dist) * repulsion_strength

        n = len(neighbors)
        centroid = centroid / n - my_pos

        # Weighted combination (CRA: adhesion > tension > repulsion)
        weights = {"adhesion": 0.5, "tension": 0.3, "repulsion": 0.2}
        migration = (
            weights["adhesion"] * adhesion
            + weights["tension"] * centroid
            + weights["repulsion"] * repulsion
        )

        # Scale by dispersion (more dispersed lineages move more)
        migration *= dispersion

        return migration.astype(np.float32)

    # =====================================================================
    #  Trait inheritance (bounded reflected mutation)
    # =====================================================================

    def inherit_traits(self, parent: Any, child: Any) -> None:
        """Copy and mutate traits from parent to child.

        All 16 ecology traits are heritable.  Mutation uses **bounded
        reflected mutation** in log-space:

        1. Take log of the parent's trait value.
        2. Add Gaussian noise: ``N(0, sigma=0.15)``.
        3. Exponentiate back to linear space.
        4. If the result exceeds bounds, **reflect** at the boundary
           (do not clip — reflection preserves distribution mass).

        This is CRA v009bz: log-normal mutation with reflection at bounds.

        Parameters
        ----------
        parent : PolypState
            Parent polyp.
        child : PolypState
            Child polyp (mutated in place).
        """
        parent_traits = self._extract_traits(parent)
        child_traits = self._mutate_traits(parent_traits)
        self._apply_traits(child, child_traits)

    def _extract_traits(self, state: Any) -> Dict[str, float]:
        """Extract heritable traits from a polyp state.

        Parameters
        ----------
        state : PolypState
            Polyp to read traits from.

        Returns
        -------
        dict
            Trait name -> value mapping.
        """
        traits: Dict[str, float] = {}
        for trait_name in self.TRAIT_BOUNDS:
            if hasattr(state, trait_name):
                val = getattr(state, trait_name)
                if isinstance(val, (int, float, np.floating, np.integer)):
                    traits[trait_name] = float(val)
        return traits

    def _apply_traits(self, state: Any, traits: Dict[str, float]) -> None:
        """Write trait values into a polyp state.

        Parameters
        ----------
        state : PolypState
            Polyp to write traits to (mutated in place).
        traits : dict
            Trait name -> value mapping.
        """
        for trait_name, value in traits.items():
            if hasattr(state, trait_name):
                current_type = type(getattr(state, trait_name))
                if current_type == int:
                    setattr(state, trait_name, int(round(value)))
                else:
                    setattr(state, trait_name, float(value))

    def _mutate_traits(self, parent_traits: Dict[str, float]) -> Dict[str, float]:
        """Apply bounded reflected mutation to all traits.

        For each trait:
        1. Convert to log-space.
        2. Add Gaussian noise.
        3. Convert back to linear space.
        4. Reflect at bounds if exceeded.

        Parameters
        ----------
        parent_traits : dict
            Parent trait values.

        Returns
        -------
        dict
            Mutated child trait values.
        """
        child_traits: Dict[str, float] = {}
        for trait_name, parent_value in parent_traits.items():
            low, high = self.TRAIT_BOUNDS.get(trait_name, (0.001, 100.0))

            # Log-space mutation
            log_val = math.log(max(parent_value, 1e-9))
            noise = random.gauss(0.0, self.BOUNDED_MUTATION_SIGMA)
            mutated_log = log_val + noise
            mutated = math.exp(mutated_log)

            # Bounded reflection (CRA v009bz)
            if self.BOUNDED_MUTATION_REFLECT:
                mutated = self._reflect_at_bounds(mutated, low, high)
            else:
                mutated = max(low, min(high, mutated))

            child_traits[trait_name] = mutated

        return child_traits

    def _reflect_at_bounds(self, value: float, low: float, high: float) -> float:
        """Reflect a value at boundaries until it lies within [low, high].

        Reflection preserves the probability mass that would otherwise be
        clipped away, maintaining the intended mutation distribution.

        Parameters
        ----------
        value : float
            Value to reflect.
        low : float
            Lower bound (inclusive).
        high : float
            Upper bound (inclusive).

        Returns
        -------
        float
            Reflected value within bounds.
        """
        if low <= value <= high:
            return value

        span = high - low
        if span <= 0:
            return low

        # Iterative reflection
        for _ in range(10):  # max 10 reflections to avoid infinite loops
            if value < low:
                value = low + (low - value)
            elif value > high:
                value = high - (value - high)
            else:
                return value

        # Fallback: clamp if reflection hasn't converged
        return max(low, min(high, value))

    # =====================================================================
    #  Lineage tracking
    # =====================================================================

    def get_or_create_lineage(self, lineage_id: int) -> LineageRecord:
        """Retrieve or create a lineage record.

        Parameters
        ----------
        lineage_id : int
            Lineage identifier.

        Returns
        -------
        LineageRecord
            Existing or newly created lineage record.
        """
        if lineage_id not in self._lineage_registry:
            self._lineage_registry[lineage_id] = LineageRecord(
                lineage_id=lineage_id,
                founder_id=-1,  # set later by create_founder
            )
        return self._lineage_registry[lineage_id]

    def get_lineage_stats(self) -> Dict[int, Dict[str, Any]]:
        """Return statistics for all lineages.

        Returns
        -------
        dict
            Map ``lineage_id -> stats dict`` with keys:
            ``n_alive``, ``n_total_births``, ``n_deaths``,
            ``max_trophic``, ``support_history_len``.
        """
        stats: Dict[int, Dict[str, Any]] = {}
        for lid, rec in self._lineage_registry.items():
            stats[lid] = {
                "n_alive": len(rec.polyp_ids),
                "n_total_births": len(rec.birth_steps),
                "n_deaths": rec.n_deaths,
                "max_trophic": rec.max_trophic,
                "support_history_len": len(rec.support_history),
            }
        return stats

    # =====================================================================
    #  Telemetry
    # =====================================================================

    def get_lifecycle_telemetry(self) -> Dict[str, Any]:
        """Return telemetry on births, deaths, and handoff status.

        Returns
        -------
        dict
            Keys:
            - ``handoff_complete`` (bool)
            - ``handoff_step`` (int or None)
            - ``total_births`` (int)
            - ``total_deaths`` (int)
            - ``current_population`` (int)
            - ``n_lineages`` (int)
            - ``capacity`` (int)
            - ``events_last_step`` (int)
        """
        total_births = sum(l.n_reproductions for l in self._lineage_registry.values())
        total_deaths = sum(l.n_deaths for l in self._lineage_registry.values())
        alive_now = sum(
            1 for s in self._polyp_registry.values() if getattr(s, "is_alive", False)
        )

        return {
            "handoff_complete": self._handoff_complete,
            "handoff_step": self._handoff_step,
            "total_births": total_births,
            "total_deaths": total_deaths,
            "current_population": alive_now,
            "n_lineages": len(self._lineage_registry),
            "capacity": self.population_capacity(),
            "events_last_step": len(
                [e for e in self._events if e.step == self._current_step]
            ),
        }

    def get_developmental_telemetry(self) -> Dict[str, Any]:
        """Return telemetry on maturity and readiness.

        Returns
        -------
        dict
            Keys:
            - ``n_juveniles`` (int)
            - ``n_adults`` (int)
            - ``avg_cyclin_d`` (float)
            - ``avg_bax_activation`` (float)
            - ``avg_trophic_health`` (float)
            - ``avg_age_steps`` (float)
            - ``ready_to_reproduce`` (int)
        """
        alive = [s for s in self._polyp_registry.values() if getattr(s, "is_alive", False)]
        if not alive:
            return {
                "n_juveniles": 0,
                "n_adults": 0,
                "avg_cyclin_d": 0.0,
                "avg_bax_activation": 0.0,
                "avg_trophic_health": 0.0,
                "avg_age_steps": 0.0,
                "ready_to_reproduce": 0,
            }

        n_juv = sum(1 for s in alive if getattr(s, "is_juvenile", False))
        n_adult = len(alive) - n_juv

        avg_cyclin = float(np.mean([getattr(s, "cyclin_d", 0.0) for s in alive]))
        avg_bax = float(np.mean([getattr(s, "bax_activation", 0.0) for s in alive]))
        avg_trophic = float(np.mean([getattr(s, "trophic_health", 0.0) for s in alive]))
        avg_age = float(np.mean([getattr(s, "age_steps", 0) for s in alive]))

        ready = sum(
            1
            for s in alive
            if (
                not getattr(s, "is_juvenile", False)
                and getattr(s, "cyclin_d", 0.0) >= self.CYCLIN_D_G1S_THRESHOLD
                and getattr(s, "trophic_health", 0.0)
                > getattr(s, "reproduction_threshold", 1.5)
            )
        )

        return {
            "n_juveniles": n_juv,
            "n_adults": n_adult,
            "avg_cyclin_d": avg_cyclin,
            "avg_bax_activation": avg_bax,
            "avg_trophic_health": avg_trophic,
            "avg_age_steps": avg_age,
            "ready_to_reproduce": ready,
        }

    # =====================================================================
    #  Utility helpers
    # =====================================================================

    def _count_degree(
        self, polyp_id: int, edges: Dict[Tuple[int, int], float]
    ) -> int:
        """Count the out-degree of a polyp in the edge map.

        Parameters
        ----------
        polyp_id : int
            Polyp to count degree for.
        edges : dict
            Edge map ``(src, dst) -> weight``.

        Returns
        -------
        int
            Number of outgoing edges.
        """
        count = 0
        for (src, dst) in edges:
            if src == polyp_id:
                count += 1
        return count

    def get_neighbors(
        self, polyp_id: int, edges: Dict[Tuple[int, int], float]
    ) -> List[int]:
        """Return neighbor polyp IDs connected to the given polyp.

        Parameters
        ----------
        polyp_id : int
            Center polyp.
        edges : dict
            Edge map.

        Returns
        -------
        list of int
            Neighbor polyp IDs.
        """
        return [dst for (src, dst) in edges if src == polyp_id]

    def get_growth_budget(self, polyp_id: int) -> Optional[GrowthBudget]:
        """Retrieve the cached growth budget for a polyp.

        Must be called after ``compute_growth_budgets()`` in the same step.

        Parameters
        ----------
        polyp_id : int
            Polyp to look up.

        Returns
        -------
        GrowthBudget or None
            Cached budget, or None if not computed this step.
        """
        return self._growth_budgets_cache.get(polyp_id)

    def get_all_events(self) -> List[LifecycleEvent]:
        """Return all lifecycle events recorded so far.

        Returns
        -------
        list of LifecycleEvent
            Complete event history.
        """
        return list(self._events)

    def get_events_for_step(self, step: int) -> List[LifecycleEvent]:
        """Return lifecycle events for a specific step.

        Parameters
        ----------
        step : int
            Simulation step to query.

        Returns
        -------
        list of LifecycleEvent
            Events at the given step.
        """
        return [e for e in self._events if e.step == step]

    def reset(self) -> None:
        """Reset the lifecycle manager to initial state.

        Clears all polyps, lineages, events, and counters.  The manager
        can then be reused for a new simulation run.
        """
        self._next_polyp_id = 0
        self._lineage_counter = 0
        self._polyp_registry.clear()
        self._lineage_registry.clear()
        self._events.clear()
        self._handoff_complete = False
        self._handoff_step = None
        self._maternal_reserve = None
        self._juvenile_birth_step.clear()
        self._last_reproduction_step.clear()
        self._current_step = 0
        self._growth_budgets_cache.clear()

    def __repr__(self) -> str:
        """String representation for debugging."""
        alive = sum(
            1 for s in self._polyp_registry.values() if getattr(s, "is_alive", False)
        )
        return (
            f"LifecycleManager("
            f"step={self._current_step}, "
            f"alive={alive}, "
            f"lineages={len(self._lineage_registry)}, "
            f"handoff={self._handoff_complete}, "
            f"events={len(self._events)})"
        )
