"""
Learning Manager for Coral Reef Architecture on SpiNNaker.

Implements dopamine-modulated STDP learning with:
- Local market-correctness reward (not colony-agreement)
- Winner-take-all competitive readout (Desimone & Duncan 1995)
- Dopamine-modulated STDP (Fremaux et al. 2010)
- Homeostatic normalization (Oja-style)
- BOCPD-gated plasticity temperature
- Calcification-based consolidation
- Output scale adaptation to 5m returns
- Directional accuracy tracking
- Delayed matured consequence credit

There is NO backpropagation. All learning is local STDP gated by
a global dopamine signal derived from task consequence.

Mathematical Architecture:
    RPE = colony_prediction * actual_return_5m                (raw market signal)
    D_t = alpha * (RPE - D_{t-1}) + D_{t-1}                  (dopamine EMA, tau=100ms)
    dw = dw_STDP * (1 + dopamine_scale * D_t)                (Fremaux 2010 modulation)
    T_plasticity = 1.0 + bocpd_weight * P_changepoint        (BOCPD gating)
    output_scale += alpha * (|return_5m| - output_scale)     (sensory calibration)

References:
    Fremaux et al. (2010) Functional Requirements for Reward-Modulated STDP
    Desimone & Duncan (1995) Neural mechanisms of selective visual attention
    Ermentrout (1998) Linearization of F-I curves by adaptation
    Oja (1982) Simplified neuron model as principal component analyzer
    Adams & MacKay (2007) Bayesian Online Changepoint Detection
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any, Set
from collections import deque, defaultdict
import numpy as np
import math


# ---------------------------------------------------------------------------
# Constants — tagged with biological or engineering origin
#
# DEPRECATED: These module-level constants are being migrated to
# config.py LearningConfig.  New code should read from the instance
# config passed to LearningManager.__init__.  Constants are retained
# here temporarily so internal functions compile while migration proceeds.
# ---------------------------------------------------------------------------

# STDP parameters (biological: Markram et al. 1997; Song et al. 2000)
STDP_A_PLUS: float = 0.01
STDP_A_MINUS: float = 0.01
STDP_TAU_PLUS_MS: float = 20.0
STDP_TAU_MINUS_MS: float = 20.0

# Dopamine timescale (biological: Schultz 1998, 2007)
DOPAMINE_TAU_MS: float = 100.0
DOPAMINE_SCALE: float = 1.0
DOPAMINE_GAIN: float = 10000.0  # legacy alias; runtime uses LearningConfig.dopamine_gain

# Winner-take-all (computational: Desimone & Duncan 1995)
WTA_BASE_K: int = 3

# Homeostasis (biological: Turrigiano & Nelson 2004)
HOMEOSTASIS_TARGET_RATE_HZ: float = 10.0
HOMEOSTASIS_STRENGTH: float = 0.001

# Plasticity gating (engineering: Adams & MacKay 2007 BOCPD)
PLASTICITY_BOCPD_WEIGHT: float = 2.0
CALCIFICATION_RATE: float = 0.001
SYNAPTIC_TAG_THRESHOLD: float = 0.5

# Output scale adaptation (engineering: sensory calibration)
SEED_OUTPUT_SCALE: float = 0.1
OUTPUT_SCALE_ADAPTATION_ALPHA: float = 0.01

# Directional accuracy (engineering: performance tracking)
DIRECTIONAL_ACCURACY_EMA_ALPHA: float = 0.02
EVALUATION_HORIZON_BARS: int = 5  # legacy default; manager.step uses config

# Delayed credit assignment (engineering: consequence-based)
MAX_PENDING_HORIZONS: int = 100

# Weight bounds (biological: excitatory synapse range)
WEIGHT_MIN: float = 0.0
WEIGHT_MAX: float = 1.0

# Reward computation (biological: Ermentrout 1998 saturator)
REWARD_SATURATOR = math.tanh

# Competitive alpha discounts
PRIOR_MONOPOLY_DISCOUNT: float = 0.05
UNVALIDATED_LOUDNESS_DISCOUNT: float = 0.03
MATURED_CONSEQUENCE_TILT: float = 0.04


# ---------------------------------------------------------------------------
# Canonical LearningConfig — imported from config.py (single source of truth)
# ---------------------------------------------------------------------------
from .config import LearningConfig


# ---------------------------------------------------------------------------
# Polyp state interface (stub for type-checking; actual implementation in
# reef_network.py — we use Protocol-like duck typing here)
# ---------------------------------------------------------------------------

class PolypStateProtocol:
    """Duck-typing interface for polyp state objects.

    The actual PolypState class lives in reef_network.py. This protocol
    documents the fields LearningManager expects.

    Required attributes:
        dopamine_ema (float): Exponential moving average of dopamine.
        last_mi (float): Last mutual information estimate.
        uptake_rate (float): Nutrient uptake rate.
        da_gain (float): Dopamine gain factor.
        activity_rate (float): Current firing rate in Hz.
        directional_accuracy_ema (float): EMA of directional correctness.
        output_scale (float): Sensory output calibration scale.
        last_raw_rpe (float): Last raw reward prediction error.
        last_output_signed_contribution (float): Signed prediction contribution.
        last_net_matured_consequence_credit (float): Net matured delayed credit.
        polyp_id (int): Unique identifier.
    """
    dopamine_ema: float
    last_mi: float
    uptake_rate: float
    da_gain: float
    activity_rate: float
    directional_accuracy_ema: float
    output_scale: float
    last_raw_rpe: float
    last_output_signed_contribution: float
    last_net_matured_consequence_credit: float
    polyp_id: int

    def step_dopamine(self, raw_dopamine: float, dt_ms: float) -> None:
        """Update dopamine EMA given raw signal."""
        ...

    def compute_drive(self) -> float:
        """Return metabolic drive level."""
        ...


# ---------------------------------------------------------------------------
# Edge state interface
# ---------------------------------------------------------------------------

class ReefEdgeProtocol:
    """Duck-typing interface for synaptic edges.

    Required attributes:
        weight (float): Synaptic weight.
        calcification (float): Consolidation level (0=plastic, 1=frozen).
        synaptic_tag (float): Eligibility trace for consolidation.
    """
    weight: float
    calcification: float
    synaptic_tag: float


# ---------------------------------------------------------------------------
# Task outcome interface
# ---------------------------------------------------------------------------
# Canonical TaskOutcomeSurface lives in trading_bridge.py (the concrete
# implementation used by organism.py).  We import it here for type hints.
from .trading_bridge import TaskOutcomeSurface

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class LearningResult:
    """Result of one learning step for external logging and diagnostics.

    Attributes:
        colony_prediction: Final aggregated colony prediction.
        winner_polyp_ids: IDs of polyps selected by WTA.
        winner_weights: Normalized readout weights for winners.
        raw_dopamine: Global dopamine signal before per-polyp EMA.
        mean_accuracy_ema: Average directional accuracy across all polyps.
        stdp_updates_count: Number of STDP weight updates applied.
        calcification_events: Number of consolidation state changes.
        plasticity_temperature: Current BOCPD-gated plasticity multiplier.
        per_polyp_rewards: Dict mapping polyp_id -> reward value.
    """
    colony_prediction: float = 0.0
    winner_polyp_ids: List[int] = field(default_factory=list)
    winner_weights: List[float] = field(default_factory=list)
    raw_dopamine: float = 0.0
    mean_accuracy_ema: float = 0.5
    stdp_updates_count: int = 0
    calcification_events: int = 0
    plasticity_temperature: float = 1.0
    per_polyp_rewards: Dict[int, float] = field(default_factory=dict)
    macro_eligibility_trace_abs_sum: float = 0.0
    macro_eligibility_trace_nonzero_count: int = 0
    macro_eligibility_matured_updates: int = 0
    macro_eligibility_trace_mode: str = "disabled"
    macro_eligibility_credit_mode: str = "disabled"


@dataclass
class STDPUpdate:
    """A single dopamine-modulated STDP weight update for logging.

    Attributes:
        source_id: Presynaptic polyp identifier.
        target_id: Postsynaptic polyp identifier.
        pre_time: Absolute spike time of presynaptic neuron (ms).
        post_time: Absolute spike time of postsynaptic neuron (ms).
        dw_base: Raw STDP weight change before dopamine modulation.
        dw_modulated: Final weight change after dopamine modulation.
        old_weight: Synaptic weight before update.
        new_weight: Synaptic weight after update.
    """
    source_id: int
    target_id: int
    pre_time: float
    post_time: float
    dw_base: float
    dw_modulated: float
    old_weight: float
    new_weight: float


# ---------------------------------------------------------------------------
# Calcification state
# ---------------------------------------------------------------------------

@dataclass
class CalcificationState:
    """Tracks synaptic consolidation per edge (biological analog: protein
    synthesis-dependent late-phase LTP).

    Calcification represents the degree to which a synapse has been
    consolidated / "frozen" through structural changes. High calcification
    means low plasticity; low calcification means the synapse can still adapt.

    Attributes:
        edge_key: Tuple of (source_id, target_id) identifying the synapse.
        calcification: Consolidation level in [0, 1]. 0 = fully plastic,
            1 = fully consolidated and frozen.
        synaptic_tag: Eligibility trace for consolidation. When this exceeds
            a threshold, consolidation can proceed.
        last_plasticity_step: Simulation step of last plasticity event.
    """
    edge_key: Tuple[int, int]
    calcification: float = 0.0
    synaptic_tag: float = 0.0
    last_plasticity_step: int = 0

    def update(
        self,
        weight_change: float,
        step: int,
        temperature: float,
        rate: float = CALCIFICATION_RATE,
    ) -> bool:
        """Update calcification based on weight stability and plasticity events.

        The synaptic tag accumulates with weight changes. When the tag exceeds
        a threshold, calcification increases (consolidation). High plasticity
        temperature can temporarily suppress calcification ("unlocking").

        Args:
            weight_change: Absolute weight change from STDP.
            step: Current simulation step.
            temperature: Plasticity temperature (BOCPD-gated).
            rate: Base calcification rate.

        Returns:
            True if a calcification event occurred (tag crossed threshold or
            calcification level changed meaningfully).
        """
        event_occurred = False

        # Update eligibility trace (synaptic tag)
        # Tag decays exponentially and accumulates with weight changes
        tag_decay = 0.95  # per-step decay constant
        self.synaptic_tag = tag_decay * self.synaptic_tag + abs(weight_change)

        # If plasticity temperature is high, temporarily suppress calcification
        # This "unlocks" the synapse during regime changes
        effective_rate = rate / max(temperature, 0.1)

        # Consolidation proceeds when tag is strong and weights are stable
        if self.synaptic_tag > SYNAPTIC_TAG_THRESHOLD:
            # Weight stability: small changes -> more calcification
            stability = math.exp(-abs(weight_change) * 10.0)
            delta_calc = effective_rate * stability * (1.0 - self.calcification)
            old_calc = self.calcification
            self.calcification = min(1.0, self.calcification + delta_calc)
            if abs(self.calcification - old_calc) > 1e-6:
                event_occurred = True

        # Tag resets partially after crossing threshold
        if self.synaptic_tag > SYNAPTIC_TAG_THRESHOLD * 2.0:
            self.synaptic_tag *= 0.5

        self.last_plasticity_step = step
        return event_occurred


# ---------------------------------------------------------------------------
# Pending horizon for delayed credit assignment
# ---------------------------------------------------------------------------

@dataclass
class PendingHorizon:
    """Delayed consequence record for one polyp prediction.

    A horizon record tracks a polyp's prediction and the future returns
    that accrue while a position is held. Credit only matures on bars
    where the held position could have influenced the outcome. This is
    the mechanism for delayed credit assignment without backpropagation.

    Attributes:
        polyp_id: Which polyp made the prediction.
        prediction: The polyp's signed prediction value.
        held_position: The trading position held when prediction was made.
        creation_step: Simulation step when record was created.
        future_returns: Deque of subsequent bar returns.
        is_matured: Whether this record has reached its evaluation horizon.
        gross_matured_credit: Net credit after maturity evaluation.
    """
    polyp_id: int
    prediction: float
    held_position: float
    creation_step: int
    prediction_feature: float = 0.0
    macro_eligibility_feature: float = 0.0
    macro_eligibility_trace_mode: str = "disabled"
    future_returns: deque = field(default_factory=deque)
    is_matured: bool = False
    gross_matured_credit: float = 0.0

    def accumulate_return(self, bar_return: float) -> None:
        """Add one bar's return to the future ledger."""
        self.future_returns.append(bar_return)

    def evaluate_maturity(self, horizon_bars: int = EVALUATION_HORIZON_BARS) -> float:
        """Evaluate matured credit over the held-horizon window.

        Credit is computed as the product of prediction sign and cumulative
        directional return over the horizon. This ensures credit only flows
        when the prediction's direction aligns with realized market movement.

        Args:
            horizon_bars: Number of bars over which to accumulate returns.

        Returns:
            Gross matured credit value.
        """
        if len(self.future_returns) < horizon_bars:
            return 0.0  # Not enough history yet

        # Credit only matures on bars where held position could influence
        # Sign from directional correctness against held-position horizon return
        horizon_returns = list(self.future_returns)[:horizon_bars]
        cumulative_return = sum(horizon_returns)

        # Net-positive gating: credit from directional alignment.
        pred_sign = LearningManager._sign(self.prediction)
        return_sign = LearningManager._sign(cumulative_return)
        if pred_sign == 0 or return_sign == 0:
            self.gross_matured_credit = 0.0
            self.is_matured = True
            return self.gross_matured_credit
        directional_sign = pred_sign * return_sign
        magnitude = REWARD_SATURATOR(abs(cumulative_return))

        self.gross_matured_credit = directional_sign * magnitude
        self.is_matured = True
        return self.gross_matured_credit


# ---------------------------------------------------------------------------
# LearningManager — the core orchestrator
# ---------------------------------------------------------------------------

class LearningManager:
    """Manages all learning in the CRA colony on SpiNNaker.

    Core responsibilities (10 principal functions):
        1. Winner-take-all readout from polyp spike rates.
        2. Dopamine signal computation from task consequence.
        3. Per-polyp reward via local market correctness.
        4. STDP weight updates modulated by dopamine.
        5. Homeostatic normalization (Oja-style).
        6. BOCPD-gated plasticity temperature.
        7. Calcification / consolidation tracking.
        8. Output scale adaptation to 5m returns.
        9. Directional accuracy EMA per polyp.
        10. Delayed matured consequence ledger.

    All operations are host-side Python between SpiNNaker runs. The actual
    spike-timing-dependent plasticity (STDP) runs on SpiNNaker hardware;
    this manager computes the dopamine signal, evaluates outcomes, and
    coordinates between the host and the neuromorphic substrate.

    Architecture invariant: There is NO backpropagation. All learning is
    local STDP gated by a global dopamine signal derived from task consequence.

    Attributes:
        config: LearningConfig with all hyperparameters.
        calcification_states: Dict mapping edge_key -> CalcificationState.
        pending_horizons: List of PendingHorizon records awaiting maturity.
        matured_horizons: List of matured PendingHorizon for analysis.
        step_count: Total learning steps executed.
        cumulative_stdp_updates: Running count of STDP updates.
        cumulative_calcification_events: Running count of calcification changes.
    """

    def __init__(self, config: Optional[LearningConfig] = None) -> None:
        """Initialize the LearningManager.

        Args:
            config: LearningConfig with hyperparameters. If None, uses defaults.
        """
        self.config: LearningConfig = config if config is not None else LearningConfig()

        # Consolidation tracking per synapse
        self.calcification_states: Dict[Tuple[int, int], CalcificationState] = {}

        # Delayed credit ledgers
        self.pending_horizons: List[PendingHorizon] = []
        self.matured_horizons: List[PendingHorizon] = []
        self.macro_eligibility_traces: Dict[int, float] = defaultdict(float)
        self._last_macro_eligibility_matured_updates: int = 0

        # Statistics
        self.step_count: int = 0
        self.cumulative_stdp_updates: int = 0
        self.cumulative_calcification_events: int = 0

        # Step-to-step memory for competitive discounts
        self._prior_winner_ids: Set[int] = set()
        self._prior_winner_weights: Dict[int, float] = {}

    @staticmethod
    def _sign(value: float, eps: float = 1e-12) -> int:
        """Return -1, 0, or +1 with a small dead zone around zero."""
        if value > eps:
            return 1
        if value < -eps:
            return -1
        return 0

    # ====================================================================
    # MAIN STEP
    # ====================================================================

    def step(
        self,
        polyp_states: List[Any],
        spike_data: Dict[str, Any],
        task_outcome: TaskOutcomeSurface,
        edges: Dict[Tuple[int, int], Any],
        step_num: int,
        dt_ms: float,
        bocpd_changepoint_prob: float = 0.0,
    ) -> LearningResult:
        """Execute one complete learning step.

        This is the principal entry point. It orchestrates:
            (1) WTA readout -> colony prediction
            (2) Dopamine computation from task consequence
            (3) Per-polyp reward via local market correctness
            (4) BOCPD-gated plasticity temperature
            (5) Calcification updates
            (6) Output scale adaptation
            (7) Directional accuracy tracking
            (8) Delayed horizon advancement

        .. note::
            STDP weight updates are handled **natively by the backend**
            (NEST's ``stdp_dopamine_synapse``).  The host only computes
            the dopamine signal and delivers it via
            :meth:`ReefNetwork.deliver_dopamine`.

        Args:
            polyp_states: List of polyp state objects (duck-typed).
            spike_data: Dict with 'spike_times' (list of (neuron_id, time))
                        and 'rates' (dict neuron_id -> Hz).
            task_outcome: TaskOutcomeSurface with market returns.
            edges: Dict mapping (src, dst) -> edge object with .weight,
                   .calcification, .synaptic_tag.
            step_num: Current simulation step number.
            dt_ms: Simulation timestep in milliseconds.
            bocpd_changepoint_prob: BOCPD changepoint probability [0, 1].

        Returns:
            LearningResult with all step outcomes.
        """
        self.step_count = step_num
        result = LearningResult()

        # ---- 1. Winner-take-all readout ----
        winners = self.winner_take_all_selection(polyp_states, spike_data)
        winner_ids = [wid for wid, _ in winners]
        result.winner_polyp_ids = winner_ids

        # Compute normalized aggregation weights
        agg_weights = self.compute_aggregation_weights(polyp_states, spike_data)
        result.winner_weights = [agg_weights.get(wid, 0.0) for wid in winner_ids]

        # Colony prediction = weighted sum of winner outputs
        colony_pred = sum(
            agg_weights.get(p.polyp_id, 0.0) * p.last_output_signed_contribution
            for p in polyp_states
        )
        executed_colony_pred = float(
            getattr(task_outcome, "colony_prediction", colony_pred)
        )
        result.colony_prediction = executed_colony_pred

        # ---- 2. Dopamine signal ----
        dopamine_output_scale = float(
            getattr(task_outcome, "dopamine_output_scale", self.config.seed_output_scale)
        )
        raw_dopamine = self.compute_raw_dopamine(
            executed_colony_pred,
            task_outcome.actual_return_5m,
            output_scale=dopamine_output_scale,
        )
        result.raw_dopamine = raw_dopamine
        if hasattr(task_outcome, "raw_dopamine"):
            task_outcome.raw_dopamine = raw_dopamine

        # Update per-polyp dopamine EMAs
        self.update_polyp_dopamine(polyp_states, raw_dopamine, dt_ms)

        # ---- 3. Per-polyp rewards ----
        per_polyp_rewards = self.compute_per_polyp_rewards(
            polyp_states, task_outcome, executed_colony_pred
        )
        result.per_polyp_rewards = per_polyp_rewards

        # ---- 4. Plasticity temperature ----
        plasticity_temperature = self.compute_plasticity_temperature(
            bocpd_changepoint_prob
        )
        result.plasticity_temperature = plasticity_temperature

        # ---- 5. Calcification updates ----
        # With native dopamine STDP, host-side STDP updates are empty.
        # Calcification still tracks edge stability via host-side state.
        calc_events = self.step_calcification(
            edges, [], plasticity_temperature, step_num
        )
        result.calcification_events = calc_events
        self.cumulative_calcification_events += calc_events

        # ---- 6. Output scale adaptation ----
        self.adapt_all_output_scales(polyp_states, task_outcome.actual_return_5m)

        # ---- 7. Directional accuracy tracking ----
        direction_correct_per_polyp = {
            p.polyp_id: (
                1.0
                if (
                    self._sign(p.last_output_signed_contribution) != 0
                    and self._sign(p.last_output_signed_contribution)
                    == self._sign(task_outcome.actual_return_5m)
                )
                else 0.0
            )
            for p in polyp_states
        }
        self.update_directional_accuracy(polyp_states, direction_correct_per_polyp)
        result.mean_accuracy_ema = self.get_mean_accuracy(polyp_states)
        self.update_predictive_readouts(
            polyp_states=polyp_states,
            target_signal=task_outcome.actual_return_5m,
            direction_correct_per_polyp=direction_correct_per_polyp,
            learning_rate=self.config.readout_learning_rate,
            dopamine_gate=abs(raw_dopamine),
        )

        # ---- 8. Delayed matured consequence ----
        # Advance existing horizons before creating records for the current
        # prediction. This keeps delayed credit causal: a prediction at step t
        # only accumulates returns from steps t+1...t+horizon.
        matured_now = self.advance_horizons(task_outcome.actual_return_5m, step_num)
        self.update_predictive_readouts_from_matured(
            polyp_states=polyp_states,
            matured_horizons=matured_now,
        )
        result.macro_eligibility_matured_updates = int(
            self._last_macro_eligibility_matured_updates
        )

        # Create new horizon records for current predictions after advancing
        # existing records, so the current bar is never counted as "future".
        self.update_macro_eligibility_traces(polyp_states)
        trace_mode = self.macro_eligibility_trace_mode()
        trace_summary = self.get_macro_eligibility_summary()
        result.macro_eligibility_trace_abs_sum = float(trace_summary["trace_abs_sum"])
        result.macro_eligibility_trace_nonzero_count = int(trace_summary["trace_nonzero_count"])
        result.macro_eligibility_trace_mode = trace_mode
        result.macro_eligibility_credit_mode = str(trace_summary["credit_mode"])
        polyp_ids = [int(getattr(p, "polyp_id", -1)) for p in polyp_states]
        for p in polyp_states:
            macro_feature = self.macro_eligibility_feature_for_horizon(
                int(p.polyp_id), polyp_ids
            )
            horizon = self.create_horizon_record(
                p.polyp_id,
                p.last_output_signed_contribution,
                task_outcome.held_position,
                step_num,
                prediction_feature=getattr(p, "last_prediction_feature", 0.0),
                macro_eligibility_feature=macro_feature,
                macro_eligibility_trace_mode=trace_mode,
            )
            self.pending_horizons.append(horizon)

        # Store prior winners for next step's competitive discounting
        self._prior_winner_ids = set(winner_ids)
        self._prior_winner_weights = {
            wid: agg_weights.get(wid, 0.0) for wid in winner_ids
        }

        return result

    def macro_eligibility_enabled(self) -> bool:
        """Whether the Tier 5.9 host-side macro eligibility path is active."""
        return bool(getattr(self.config, "macro_eligibility_enabled", False))

    def macro_eligibility_trace_mode(self) -> str:
        """Return normalized trace mode for diagnostics and ablations."""
        if not self.macro_eligibility_enabled():
            return "disabled"
        mode = str(getattr(self.config, "macro_eligibility_trace_mode", "normal")).lower()
        return mode if mode in {"normal", "shuffled", "zero"} else "normal"

    def macro_eligibility_credit_mode(self) -> str:
        """Return how macro eligibility is applied to matured credit."""
        if not self.macro_eligibility_enabled():
            return "disabled"
        mode = str(getattr(self.config, "macro_eligibility_credit_mode", "replace")).lower()
        return mode if mode in {"replace", "residual"} else "replace"

    def update_macro_eligibility_traces(self, polyp_states: List[Any]) -> None:
        """Update causal, decaying per-polyp macro eligibility traces.

        Only current-step feature/action information enters the trace; pending
        horizons store this snapshot before future consequence can mature.
        """
        if not self.macro_eligibility_enabled():
            self.macro_eligibility_traces.clear()
            return
        decay = float(getattr(self.config, "macro_eligibility_decay", 0.92))
        decay = max(0.0, min(0.999999, decay))
        live_ids = {int(getattr(p, "polyp_id", -1)) for p in polyp_states}
        for pid in list(self.macro_eligibility_traces):
            if pid not in live_ids:
                del self.macro_eligibility_traces[pid]
            else:
                self.macro_eligibility_traces[pid] *= decay
        for polyp in polyp_states:
            pid = int(getattr(polyp, "polyp_id", -1))
            feature = float(getattr(polyp, "last_prediction_feature", 0.0) or 0.0)
            prediction = float(getattr(polyp, "last_output_signed_contribution", 0.0) or 0.0)
            action_sign = float(self._sign(prediction) or self._sign(feature))
            self.macro_eligibility_traces[pid] += feature * action_sign

    def macro_eligibility_feature_for_horizon(self, polyp_id: int, polyp_ids: List[int]) -> float:
        """Return the trace snapshot stored with a new pending horizon."""
        mode = self.macro_eligibility_trace_mode()
        if mode in {"disabled", "zero"}:
            return 0.0
        source_id = int(polyp_id)
        if mode == "shuffled":
            ordered = sorted(pid for pid in polyp_ids if pid >= 0)
            if ordered:
                idx = ordered.index(source_id) if source_id in ordered else 0
                source_id = ordered[(idx + 1) % len(ordered)]
        return float(self.macro_eligibility_traces.get(source_id, 0.0))

    def macro_eligibility_trace_residual(self, horizon: PendingHorizon) -> float:
        """Return a bounded trace residual for Tier 5.9b repair diagnostics."""
        raw_trace = float(getattr(horizon, "macro_eligibility_feature", 0.0) or 0.0)
        if abs(raw_trace) <= 1e-12:
            return 0.0
        clip = abs(float(getattr(self.config, "macro_eligibility_trace_clip", 1.0) or 1.0))
        clip = max(clip, 1e-9)
        residual = math.tanh(raw_trace / clip)
        scale = float(getattr(self.config, "macro_eligibility_residual_scale", 0.10) or 0.0)
        return float(scale * residual)

    def macro_eligibility_credit_feature(self, horizon: PendingHorizon) -> float:
        """Feature used by delayed readout credit with optional macro trace."""
        base_feature = float(getattr(horizon, "prediction_feature", 0.0) or 0.0)
        if not self.macro_eligibility_enabled():
            return base_feature
        raw_trace = float(getattr(horizon, "macro_eligibility_feature", 0.0) or 0.0)
        if self.macro_eligibility_credit_mode() == "residual":
            return float(base_feature + self.macro_eligibility_trace_residual(horizon))
        return raw_trace

    def get_macro_eligibility_summary(self) -> Dict[str, Any]:
        """Compact trace telemetry for per-step and registry summaries."""
        values = [float(v) for v in self.macro_eligibility_traces.values()]
        return {
            "trace_abs_sum": float(sum(abs(v) for v in values)),
            "trace_nonzero_count": int(sum(1 for v in values if abs(v) > 1e-12)),
            "trace_mode": self.macro_eligibility_trace_mode(),
            "credit_mode": self.macro_eligibility_credit_mode(),
        }

    # ====================================================================
    # WINNER-TAKE-ALL READOUT (Desimone & Duncan 1995)
    # ====================================================================

    def winner_take_all_selection(
        self,
        polyp_states: List[Any],
        spike_data: Dict[str, Any],
    ) -> List[Tuple[int, float]]:
        """Select top-k polyps by absolute RPE for colony readout.

        Implements competitive winner-take-all: only the top
        max(3, int(sqrt(N))) polyps by abs(last_raw_rpe) contribute
        to the colony prediction. All others are zeroed out.

        This prevents democratic averaging where random predictors cancel
        each other (Desimone & Duncan 1995 — selective attention via
        competitive suppression).

        Args:
            polyp_states: List of polyp state objects.
            spike_data: Spike timing and rate data (used for tie-breaking).

        Returns:
            List of (polyp_id, selection_score) tuples for winners,
            sorted by score descending.
        """
        n_polyps = len(polyp_states)
        if n_polyps == 0:
            return []

        # k = max(3, int(sqrt(N))) — ensures minimum pool even for small colonies
        k = max(self.config.winner_take_all_base, int(math.sqrt(n_polyps)))

        # Score each polyp by absolute last_raw_rpe (residual prediction error)
        scored = []
        for p in polyp_states:
            score = abs(p.last_raw_rpe)
            # Tie-break by activity rate for stability
            rates = spike_data.get("rates", {})
            tiebreak = rates.get(p.polyp_id, p.activity_rate)
            scored.append((p.polyp_id, score, tiebreak))

        # Sort by score descending, then by tiebreak
        scored.sort(key=lambda x: (-x[1], -x[2]))

        # Select top k
        winners = [(pid, score) for pid, score, _ in scored[:k]]
        return winners

    def compute_aggregation_weights(
        self,
        polyp_states: List[Any],
        spike_data: Dict[str, Any],
    ) -> Dict[int, float]:
        """Compute normalized readout weights for all polyps.

        Top-k winners receive weights proportional to their selection score;
        all other polyps receive zero weight. Weights are normalized to sum
        to 1.0 so the colony prediction is a proper convex combination.

        Competitive alpha discounts are applied on top of trophic-health
        weighting to soften monopolies and boost proven performers.

        Args:
            polyp_states: List of polyp state objects.
            spike_data: Spike timing and rate data.

        Returns:
            Dict mapping polyp_id -> normalized weight (sums to 1.0).
        """
        n_polyps = len(polyp_states)
        if n_polyps == 0:
            return {}

        # Get WTA winners
        winners = self.winner_take_all_selection(polyp_states, spike_data)
        winner_ids = {wid for wid, _ in winners}

        # Build raw weights: score-based for winners, zero for losers
        raw_weights: Dict[int, float] = {}
        for pid, score in winners:
            # Base weight proportional to RPE magnitude
            # Add small epsilon to avoid all-zero weights
            raw_weights[pid] = max(score, 1e-6)

        # Zero out non-winners
        for p in polyp_states:
            if p.polyp_id not in winner_ids:
                raw_weights[p.polyp_id] = 0.0

        # Apply competitive discounts
        discounted_weights = self.apply_wta_discount(
            raw_weights, polyp_states
        )

        # Normalize to sum to 1.0
        total = sum(discounted_weights.values())
        if total > 0:
            normalized = {
                pid: w / total for pid, w in discounted_weights.items()
            }
        else:
            # Fallback: uniform over all polyps if all weights are zero
            n = len(polyp_states)
            normalized = {p.polyp_id: 1.0 / n for p in polyp_states}

        return normalized

    def apply_wta_discount(
        self,
        weights: Dict[int, float],
        polyp_states: List[Any],
    ) -> Dict[int, float]:
        """Apply competitive alpha discounts to readout weights.

        Three discount/tilt mechanisms operate on top of trophic-health
        weighting:

        1. Prior monopoly discount: slight reduction for polyps that won
           in the previous step (prevents persistent dominance).
        2. Unvalidated loudness discount: slight reduction for polyps with
           high activity but low directional accuracy.
        3. Matured consequence tilt: slight boost for polyps with recent
           net-positive matured consequence credit.

        All modifications are multiplicative and applied cumulatively.

        Args:
            weights: Dict of polyp_id -> raw weight.
            polyp_states: List of polyp state objects.

        Returns:
            Dict of polyp_id -> discounted weight.
        """
        discounted = dict(weights)
        state_by_id = {p.polyp_id: p for p in polyp_states}

        for pid, w in list(discounted.items()):
            if w <= 0:
                continue

            polyp = state_by_id.get(pid)
            if polyp is None:
                continue

            multiplier = 1.0

            # Discount 1: prior monopoly — soften persistent winners
            if pid in self._prior_winner_ids:
                prior_weight = self._prior_winner_weights.get(pid, 0.0)
                if prior_weight > 0.3:  # Was a dominant winner
                    multiplier *= (1.0 - PRIOR_MONOPOLY_DISCOUNT)

            # Discount 2: unvalidated loudness — penalize noisy but wrong
            accuracy = getattr(polyp, "directional_accuracy_ema", 0.5)
            activity = getattr(polyp, "activity_rate", 0.0)
            if activity > self.config.homeostasis_target_rate_hz * 2.0:
                # High activity but not validated
                if accuracy < 0.5:
                    multiplier *= (
                        1.0 - UNVALIDATED_LOUDNESS_DISCOUNT
                    )

            # Tilt 3: matured consequence — boost proven performers
            matured_credit = getattr(
                polyp, "last_net_matured_consequence_credit", 0.0
            )
            if matured_credit > 0:
                multiplier *= (1.0 + MATURED_CONSEQUENCE_TILT)

            discounted[pid] = w * multiplier

        return discounted

    # ====================================================================
    # DOPAMINE SIGNAL (Schultz 1998; Fremaux et al. 2010)
    # ====================================================================

    def compute_raw_dopamine(
        self,
        colony_pred: float,
        task_signal: float,
        output_scale: Optional[float] = None,
    ) -> float:
        """Compute the global raw dopamine signal from task consequence.

        Raw dopamine = colony_prediction * task_signal * output_scale.
        This is a reward prediction error: when colony prediction and
        market return have the same sign, dopamine is positive (better
        than expected); when opposite, negative (worse than expected).

        The output_scale seeds at 0.1 and adapts to the data scale — this
        is sensory calibration, not a biological constant.

        Args:
            colony_pred: Colony aggregated prediction (signed).
            task_signal: Actual market return at 5m horizon (signed).
            output_scale: Sensory/output calibration scale. Defaults to
                ``LearningConfig.seed_output_scale``.

        Returns:
            Raw dopamine signal (float, signed).
        """
        # Reward prediction error = prediction * actual outcome
        # This mimics dopaminergic RPE where D > 0 means "better than predicted"
        scale = self.config.seed_output_scale if output_scale is None else output_scale
        rpe = colony_pred * task_signal * scale

        # Scale by output_scale (sensory calibration, not biological constant)
        # Seed: 0.1, adapts to data scale per v009bz-follow-up-4
        # Apply large gain + tanh saturation so tiny startup RPEs still produce
        # meaningful dopamine (STDP modulation needs |DA| ~ 0.1-1.0 to learn).
        raw_dopamine = math.tanh(rpe * self.config.dopamine_gain)

        return float(raw_dopamine)

    def update_polyp_dopamine(
        self,
        polyp_states: List[Any],
        raw_dopamine: float,
        dt_ms: float,
    ) -> None:
        """Update each polyp's dopamine EMA with the global signal.

        Each polyp maintains its own dopamine_ema, updated as:
            dopamine_ema += alpha * (raw_dopamine - dopamine_ema)
        where alpha = dt / dopamine_tau_ms.

        This gives each polyp a temporally-smoothed dopamine level that
        gates its STDP updates. The global signal is broadcast to all
        polyps; individual variation comes from different EMA histories.

        Args:
            polyp_states: List of polyp state objects with dopamine_ema.
            raw_dopamine: Global dopamine signal for this step.
            dt_ms: Simulation timestep in milliseconds.
        """
        for p in polyp_states:
            if hasattr(p, "step_dopamine") and callable(p.step_dopamine):
                p.step_dopamine(raw_dopamine, dt_ms)
            else:
                alpha = dt_ms / max(self.config.dopamine_tau, 1e-12)
                alpha = max(0.0, min(1.0, alpha))
                p.dopamine_ema += alpha * (raw_dopamine - p.dopamine_ema)

    # ====================================================================
    # PER-POLYP REWARD — Local Market Correctness
    # ====================================================================

    def compute_per_polyp_rewards(
        self,
        polyp_states: List[Any],
        task_outcome: TaskOutcomeSurface,
        colony_pred: float,
    ) -> Dict[int, float]:
        """Compute individual reward for each polyp based on local correctness.

        Critical CRA invariant: reward is based on LOCAL directional
        correctness, NOT colony agreement. A dissenting specialist that
        correctly predicts the market direction receives POSITIVE reward
        even if the colony action was wrong. This preserves specialist
        diversity and prevents herding.

        Reward = sign(polyp_pred) * sign(actual_5m) * tanh(|RPE|)

        Args:
            polyp_states: List of polyp state objects.
            task_outcome: TaskOutcomeSurface with market data.
            colony_pred: Colony aggregated prediction.

        Returns:
            Dict mapping polyp_id -> reward value.
        """
        rewards: Dict[int, float] = {}

        for p in polyp_states:
            reward = self.compute_single_reward(p, task_outcome, colony_pred)
            rewards[p.polyp_id] = reward

        return rewards

    def compute_single_reward(
        self,
        polyp: Any,
        task_outcome: TaskOutcomeSurface,
        colony_pred: float,
    ) -> float:
        """Compute reward for a single polyp.

        The reward sign reflects whether the polyp's prediction direction
        matched the realized market direction. The magnitude reflects the
        blended reward prediction error, saturated via tanh (Ermentrout
        1998 — canonical Type-I f-I curve saturator).

        This is the key mechanism that preserves dissenting specialists:
        a polyp that disagrees with the colony but is directionally correct
        receives positive reward, maintaining population diversity.

        Args:
            polyp: Single polyp state object.
            task_outcome: TaskOutcomeSurface with market returns.
            colony_pred: Colony aggregated prediction (for magnitude blending).

        Returns:
            Scalar reward for this polyp (signed, in [-1, 1]).
        """
        # Local directional sign: does polyp prediction match market?
        # This preserves dissenters who are directionally correct
        polyp_sign = self._sign(polyp.last_output_signed_contribution)
        market_sign = self._sign(task_outcome.actual_return_5m)
        if polyp_sign == 0 or market_sign == 0:
            return 0.0
        local_sign = polyp_sign * market_sign  # +1 if aligned, -1 if opposed

        # Reward magnitude from blended RPE, saturated via tanh
        # Ermentrout (1998): tanh as canonical Type-I f-I saturator
        blended_rpe = colony_pred * task_outcome.actual_return_5m
        magnitude = REWARD_SATURATOR(abs(blended_rpe))

        # Final reward: local sign * saturated magnitude
        reward = local_sign * magnitude

        return float(reward)

    def _apply_predictive_readout_update(
        self,
        polyp: Any,
        *,
        prediction: float,
        feature: float,
        reinforcement_sign: float,
        learning_rate: float,
        dopamine_gate: float = 1.0,
    ) -> None:
        """Apply a local reward-gated update to one predictive readout weight."""
        if not bool(getattr(self.config, "enable_readout_plasticity", True)):
            return

        if bool(getattr(self.config, "readout_requires_dopamine", True)):
            dopamine_gate = max(0.0, float(dopamine_gate))
            if dopamine_gate <= 0.0:
                return
        else:
            dopamine_gate = 1.0

        feature_sign = self._sign(feature)
        if feature_sign == 0 or reinforcement_sign == 0:
            return

        pred_sign = self._sign(prediction)
        if pred_sign == 0:
            # If the action was exactly neutral, use the cue sign as the local
            # exploratory action. This keeps zero-valued cold starts movable
            # without peeking at the target magnitude.
            pred_sign = feature_sign

        weight = float(getattr(polyp, "predictive_readout_weight", 0.25))
        decay = float(getattr(self.config, "readout_weight_decay", 0.0))
        clip = float(getattr(self.config, "readout_weight_clip", 20.0))
        lr_scale = max(0.0, float(getattr(polyp, "predictive_readout_lr_scale", 1.0)))
        effective_lr = float(learning_rate) * dopamine_gate * lr_scale
        if reinforcement_sign < 0.0:
            effective_lr *= float(
                getattr(self.config, "readout_negative_surprise_multiplier", 1.0)
            )

        # Reward-modulated signed Hebbian rule:
        #   correct action   -> reinforce action-feature association
        #   incorrect action -> anti-reinforce it
        delta = effective_lr * float(reinforcement_sign) * pred_sign * feature_sign
        weight = (1.0 - decay) * weight + delta
        polyp.predictive_readout_weight = float(np.clip(weight, -clip, clip))

    def update_predictive_readouts(
        self,
        *,
        polyp_states: List[Any],
        target_signal: float,
        direction_correct_per_polyp: Dict[int, float],
        learning_rate: float,
        dopamine_gate: float = 1.0,
    ) -> None:
        """Update polyp-local predictive readouts from immediate consequence.

        This is a local reinforcement update, not a supervised gradient.  The
        only task information used is whether each polyp's signed action was
        rewarded or punished by the current consequence.
        """
        if self._sign(target_signal) == 0:
            return

        for polyp in polyp_states:
            correct = direction_correct_per_polyp.get(polyp.polyp_id, 0.0)
            reinforcement_sign = 1.0 if correct >= 0.5 else -1.0
            self._apply_predictive_readout_update(
                polyp,
                prediction=getattr(polyp, "last_output_signed_contribution", 0.0),
                feature=getattr(polyp, "last_prediction_feature", 0.0),
                reinforcement_sign=reinforcement_sign,
                learning_rate=learning_rate,
                dopamine_gate=dopamine_gate,
            )

    def update_predictive_readouts_from_matured(
        self,
        *,
        polyp_states: List[Any],
        matured_horizons: List[PendingHorizon],
    ) -> None:
        """Apply delayed matured consequence to the stored prediction feature."""
        self._last_macro_eligibility_matured_updates = 0
        if not matured_horizons:
            return
        min_delayed_horizon = int(
            getattr(self.config, "min_delayed_readout_horizon_bars", 2)
        )
        if int(getattr(self.config, "evaluation_horizon_bars", 1)) < min_delayed_horizon:
            return
        if not bool(getattr(self.config, "enable_readout_plasticity", True)):
            return
        if (
            bool(getattr(self.config, "readout_requires_dopamine", True))
            and float(getattr(self.config, "dopamine_gain", 0.0)) <= 0.0
        ):
            return

        state_by_id = {getattr(p, "polyp_id", None): p for p in polyp_states}
        lr = float(getattr(self.config, "delayed_readout_learning_rate", 0.05))
        if self.macro_eligibility_enabled():
            lr *= float(getattr(self.config, "macro_eligibility_learning_rate_scale", 1.0))
        macro_updates = 0

        for horizon in matured_horizons:
            polyp = state_by_id.get(horizon.polyp_id)
            if polyp is None or not horizon.is_matured:
                continue
            reinforcement_sign = self._sign(horizon.gross_matured_credit)
            feature = self.macro_eligibility_credit_feature(horizon)
            self._apply_predictive_readout_update(
                polyp,
                prediction=horizon.prediction,
                feature=feature,
                reinforcement_sign=reinforcement_sign,
                learning_rate=lr,
                dopamine_gate=1.0,
            )
            trace_residual = self.macro_eligibility_trace_residual(horizon)
            if (
                self.macro_eligibility_enabled()
                and (
                    abs(float(getattr(horizon, "macro_eligibility_feature", 0.0) or 0.0)) > 1e-12
                    or abs(trace_residual) > 1e-12
                )
                and reinforcement_sign != 0
            ):
                macro_updates += 1
        self._last_macro_eligibility_matured_updates = macro_updates

    # ====================================================================
    # STDP — Spike-Timing-Dependent Plasticity (Fremaux et al. 2010)
    # ====================================================================

    def compute_stdp_updates(
        self,
        spike_data: Dict[str, Any],
        edges: Dict[Tuple[int, int], Any],
        dopamine_levels: Dict[int, float],
        plasticity_temperature: float = 1.0,
    ) -> List[STDPUpdate]:
        """Compute all dopamine-modulated STDP weight updates.

        For each pair of pre/post spikes within the STDP window, compute
        the raw STDP weight change, modulate by the postsynaptic neuron's
        dopamine EMA, and generate an STDPUpdate record.

        The actual weight application respects calcification: consolidated
        synapses receive attenuated updates.

        Args:
            spike_data: Dict with 'spike_times': list of (neuron_id, time_ms).
            edges: Dict mapping (src, dst) -> edge object.
            dopamine_levels: Dict mapping polyp_id -> dopamine_ema value.
            plasticity_temperature: BOCPD-gated plasticity multiplier.

        Returns:
            List of STDPUpdate records for logging and diagnostics.
        """
        updates: List[STDPUpdate] = []
        spike_times = spike_data.get("spike_times", [])

        if not spike_times or not edges:
            return updates

        # Group spikes by neuron
        spikes_by_neuron: Dict[int, List[float]] = defaultdict(list)
        for neuron_id, t in spike_times:
            spikes_by_neuron[neuron_id].append(float(t))

        # For each edge, find spike pairs within STDP window
        for (src_id, dst_id), edge in edges.items():
            if src_id not in spikes_by_neuron or dst_id not in spikes_by_neuron:
                continue

            pre_spikes = spikes_by_neuron[src_id]
            post_spikes = spikes_by_neuron[dst_id]

            # Get dopamine level for postsynaptic neuron
            da = dopamine_levels.get(dst_id, 0.0)

            # Get calcification for this edge
            calc_state = self.calcification_states.get(
                (src_id, dst_id)
            )
            calcification = (
                calc_state.calcification if calc_state else 0.0
            )

            # Calcification gates plasticity: consolidated synapses adapt less
            plasticity_factor = (1.0 - calcification) * plasticity_temperature
            if plasticity_factor < 0.01:
                continue  # Essentially frozen

            for pre_t in pre_spikes:
                for post_t in post_spikes:
                    delta_t = post_t - pre_t  # post - pre

                    # Only consider pairs within STDP window
                    if abs(delta_t) > max(
                        self.config.stdp_tau_plus,
                        self.config.stdp_tau_minus,
                    ) * 5:  # 5*tau cutoff
                        continue

                    # Compute raw STDP weight change
                    dw_base = self.stdp_pair_rule(pre_t, post_t)

                    # Apply dopamine modulation (Fremaux et al. 2010)
                    dw_modulated = self.apply_dopamine_modulation(dw_base, da)

                    # Apply plasticity temperature and calcification gating
                    dw_final = dw_modulated * plasticity_factor

                    # Apply weight update with bounds
                    old_weight = edge.weight
                    new_weight = self.apply_weight_bounds(
                        old_weight + dw_final
                    )

                    # Write back
                    edge.weight = new_weight

                    # Record update
                    updates.append(
                        STDPUpdate(
                            source_id=src_id,
                            target_id=dst_id,
                            pre_time=pre_t,
                            post_time=post_t,
                            dw_base=dw_base,
                            dw_modulated=dw_final,
                            old_weight=old_weight,
                            new_weight=new_weight,
                        )
                    )

        return updates

    def compute_reinforcement_updates(
        self,
        polyp_states: List[Any],
        edges: Dict[Tuple[int, int], Any],
        actual_return: float,
        dopamine_levels: Dict[int, float],
    ) -> None:
        """Simple reward-modulated Hebbian update for inter-polyp edges.

        Strengthens edges that originate from polyps whose *last* prediction
        agreed with the actual market direction, and weakens edges from
        polyps that were wrong.  This is a coarse but robust substitute
        for full spike-timing-dependent plasticity when only polyp-level
        predictions are available.
        """
        if not edges or actual_return == 0.0:
            return

        state_map = {p.polyp_id: p for p in polyp_states}
        lr = getattr(self.config, "reinforcement_lr", 0.002)

        for (src_id, dst_id), edge in edges.items():
            src_state = state_map.get(src_id)
            if src_state is None:
                continue

            pred = getattr(src_state, "current_prediction", 0.0)
            # Reward = +1 when sign matches, -1 when it doesn't
            reward = 1.0 if pred * actual_return > 0 else -1.0

            # Dopamine modulation (same formula as STDP branch)
            da = dopamine_levels.get(dst_id, 0.0)
            modulation = max(0.3, 1.0 + self.config.dopamine_scale * da)

            dw = lr * reward * modulation
            edge.weight = self.apply_weight_bounds(edge.weight + dw)

    def stdp_pair_rule(
        self,
        pre_time: float,
        post_time: float,
    ) -> float:
        """Compute raw STDP weight change for a pre-post spike pair.

        Standard asymmetric STDP (Markram et al. 1997; Song et al. 2000):
            If pre before post (delta_t > 0): LTP
                dw = A_plus * exp(-delta_t / tau_plus)
            If post before pre (delta_t < 0): LTD
                dw = -A_minus * exp(delta_t / tau_minus)

        Args:
            pre_time: Presynaptic spike time (ms).
            post_time: Postsynaptic spike time (ms).

        Returns:
            Raw weight change before dopamine modulation (float).
        """
        delta_t = post_time - pre_time

        if delta_t > 0:
            # Pre before post: Long-Term Potentiation (LTP)
            dw = (
                self.config.stdp_a_plus
                * math.exp(-delta_t / self.config.stdp_tau_plus)
            )
        elif delta_t < 0:
            # Post before pre: Long-Term Depression (LTD)
            dw = (
                -self.config.stdp_a_minus
                * math.exp(delta_t / self.config.stdp_tau_minus)
            )
        else:
            # Simultaneous: no change
            dw = 0.0

        return float(dw)

    def apply_dopamine_modulation(
        self,
        dw_base: float,
        dopamine_ema: float,
    ) -> float:
        """Apply dopamine modulation to an STDP weight change.

        Fremaux et al. (2010): multiply the STDP weight change by
        (1 + dopamine_scale * dopamine_ema). Positive dopamine
        amplifies both LTP and LTD; negative dopamine suppresses both.

        This is the key mechanism linking task consequence to synaptic
        plasticity: successful predictions (positive dopamine) strengthen
        the responsible synapses; failed predictions weaken them.

        Args:
            dw_base: Raw STDP weight change.
            dopamine_ema: Current dopamine EMA for the postsynaptic neuron.

        Returns:
            Dopamine-modulated weight change.
        """
        # Floor at 0.2 so negative dopamine attenuates rather than
        # abolishes plasticity.  Without a floor, modulation hits 0.0
        # when dopamine = -1.0, freezing weights on wrong predictions
        # and preventing the colony from ever correcting a random bias.
        modulation = max(0.2, 1.0 + self.config.dopamine_scale * dopamine_ema)
        return float(dw_base * modulation)

    def apply_weight_bounds(self, w: float) -> float:
        """Clip weight to biological excitatory synapse bounds.

        Args:
            w: Candidate weight value.

        Returns:
            Clipped weight in [weight_min, weight_max].
        """
        return float(np.clip(w, self.config.stdp_weight_min, self.config.stdp_weight_max))

    # ====================================================================
    # HOMEOSTASIS — Oja-style normalization (Turrigiano & Nelson 2004)
    # ====================================================================

    def apply_homeostasis(
        self,
        polyp_states: List[Any],
        edges: Dict[Tuple[int, int], Any],
        dt_ms: float,
    ) -> None:
        """Apply homeostatic normalization to maintain target firing rates.

        Biological motivation (Turrigiano & Nelson 2004): neurons maintain
        stable firing rates through homeostatic scaling of synaptic weights.
        If a neuron's activity is too high, incoming weights are weakened;
        if too low, they are strengthened.

        This is Oja-style normalization (not rate-coded): it operates on
        synaptic weights directly, not on firing rate setpoints.

        Args:
            polyp_states: List of polyp state objects.
            edges: Dict mapping (src, dst) -> edge object.
            dt_ms: Simulation timestep in milliseconds.
        """
        if not edges:
            return

        for p in polyp_states:
            scale = self.compute_homeostatic_scale(p.activity_rate)
            if abs(scale - 1.0) < 1e-9:
                continue  # No adjustment needed

            # Apply multiplicative scaling to all incoming weights
            dst_id = p.polyp_id
            for (src_id, edge_dst), edge in edges.items():
                if edge_dst == dst_id:
                    edge.weight = self.apply_weight_bounds(
                        edge.weight * scale
                    )

    def compute_homeostatic_scale(
        self,
        activity_rate: float,
    ) -> float:
        """Compute multiplicative weight scale from activity deviation.

        If activity > target: scale < 1 (weaken incoming weights).
        If activity < target: scale > 1 (strengthen incoming weights).
        The scale is near 1.0 for small deviations, preventing oscillation.

        Args:
            activity_rate: Current firing rate in Hz.

        Returns:
            Multiplicative scale factor for synaptic weights.
        """
        target = self.config.homeostasis_target_rate_hz
        deviation = activity_rate - target

        if abs(deviation) < 0.1:
            return 1.0

        # Oja-style: small multiplicative adjustment proportional to deviation
        # Scale = 1 - strength * (activity - target) / target
        adjustment = self.config.homeostasis_strength * (deviation / max(target, 1.0))
        scale = 1.0 - adjustment

        # Clamp to reasonable range to prevent runaway
        return float(np.clip(scale, 0.9, 1.1))

    # ====================================================================
    # PLASTICITY TEMPERATURE — BOCPD Gating
    # ====================================================================

    def compute_plasticity_temperature(
        self,
        changepoint_prob: float,
    ) -> float:
        """Compute BOCPD-gated plasticity temperature.

        When changepoint probability is high, plasticity temperature
        increases, temporarily "unlocking" calcified synapses and allowing
        rapid adaptation to regime changes.

        Formula: T = 1.0 + bocpd_weight * P_changepoint

        Args:
            changepoint_prob: BOCPD changepoint probability [0, 1].

        Returns:
            Plasticity temperature (>= 1.0). Higher = more plasticity.
        """
        temperature = 1.0 + self.config.plasticity_bocpd_weight * max(
            0.0, min(1.0, changepoint_prob)
        )
        return float(temperature)

    def check_calcification_unlock(
        self,
        calc_state: CalcificationState,
        temperature: float,
    ) -> bool:
        """Check if a calcified synapse should be temporarily unlocked.

        High plasticity temperature (from BOCPD changepoint detection)
        can temporarily reduce effective calcification, allowing rapid
        weight updates during regime changes.

        Args:
            calc_state: Current calcification state of the synapse.
            temperature: Current plasticity temperature.

        Returns:
            True if the synapse should be treated as unlocked (plastic).
        """
        # Temperature > 2.0 means strong changepoint signal
        # This unlocks even heavily calcified synapses
        if temperature > 2.0 and calc_state.calcification < 0.95:
            return True

        # Moderate temperature unlocks lightly calcified synapses
        if temperature > 1.5 and calc_state.calcification < 0.5:
            return True

        return False

    # ====================================================================
    # OUTPUT SCALE ADAPTATION — Sensory Calibration
    # ====================================================================

    def adapt_output_scale(
        self,
        polyp: Any,
        actual_return_5m: float,
    ) -> None:
        """Adapt one polyp's output scale toward 5m return magnitude.

        Output scale adapts to the magnitude of 5-minute returns, NOT
        1-minute returns (per v009bz-follow-up-4). This is sensory
        calibration: the system learns the appropriate output gain for
        the data distribution.

        Seed: 0.1, adapts gradually via EMA.

        Args:
            polyp: Polyp state object with output_scale attribute.
            actual_return_5m: Actual 5-minute return (signed).
        """
        target_scale = abs(actual_return_5m)
        alpha = self.config.output_scale_adaptation_alpha

        # EMA update toward target scale
        polyp.output_scale += alpha * (target_scale - polyp.output_scale)

        # Ensure scale stays positive and bounded
        polyp.output_scale = max(1e-6, min(10.0, polyp.output_scale))

    def adapt_all_output_scales(
        self,
        polyp_states: List[Any],
        actual_return_5m: float,
    ) -> None:
        """Adapt output scales for all polyps.

        Args:
            polyp_states: List of polyp state objects.
            actual_return_5m: Actual 5-minute return for scale target.
        """
        for p in polyp_states:
            self.adapt_output_scale(p, actual_return_5m)

    # ====================================================================
    # DIRECTIONAL ACCURACY TRACKING
    # ====================================================================

    def update_directional_accuracy(
        self,
        polyp_states: List[Any],
        direction_correct_per_polyp: Dict[int, float],
    ) -> None:
        """Update directional accuracy EMA for each polyp.

        Each polyp tracks its own directional accuracy via EMA:
            accuracy += alpha * (correct - accuracy)

        This accuracy is used for:
        - BAX accumulation (survival pressure)
        - Winner selection weighting
        - Trophic health computation

        Args:
            polyp_states: List of polyp state objects.
            direction_correct_per_polyp: Dict mapping polyp_id ->
                1.0 if directionally correct, 0.0 otherwise.
        """
        alpha = self.config.directional_accuracy_ema_alpha

        for p in polyp_states:
            correct = direction_correct_per_polyp.get(p.polyp_id, 0.5)
            p.directional_accuracy_ema += alpha * (
                correct - p.directional_accuracy_ema
            )
            # Clamp to [0, 1]
            p.directional_accuracy_ema = float(
                np.clip(p.directional_accuracy_ema, 0.0, 1.0)
            )

    def get_mean_accuracy(self, polyp_states: List[Any]) -> float:
        """Compute mean directional accuracy across all polyps.

        Args:
            polyp_states: List of polyp state objects.

        Returns:
            Mean accuracy_ema value (float in [0, 1]).
        """
        if not polyp_states:
            return 0.5

        accuracies = [p.directional_accuracy_ema for p in polyp_states]
        return float(np.mean(accuracies))

    # ====================================================================
    # DELAYED MATURED CONSEQUENCE CREDIT
    # ====================================================================

    def create_horizon_record(
        self,
        polyp_id: int,
        prediction: float,
        held_position: float,
        step: int,
        prediction_feature: float = 0.0,
        macro_eligibility_feature: float = 0.0,
        macro_eligibility_trace_mode: str = "disabled",
    ) -> PendingHorizon:
        """Create a new pending horizon record for delayed credit.

        The record starts with an empty future-return ledger. Returns
        only accumulate on bars where the held position could have
        influenced the outcome.

        Args:
            polyp_id: Which polyp made the prediction.
            prediction: The polyp's signed prediction value.
            held_position: Trading position held at prediction time.
            step: Current simulation step.
            prediction_feature: Local cue/readout feature that produced the
                prediction, stored for delayed credit assignment.
            macro_eligibility_feature: Decaying trace snapshot for Tier 5.9
                macro eligibility diagnostics.
            macro_eligibility_trace_mode: Trace mode used when the horizon was
                created (`disabled`, `normal`, `shuffled`, or `zero`).

        Returns:
            New PendingHorizon record.
        """
        return PendingHorizon(
            polyp_id=polyp_id,
            prediction=prediction,
            held_position=held_position,
            creation_step=step,
            prediction_feature=prediction_feature,
            macro_eligibility_feature=macro_eligibility_feature,
            macro_eligibility_trace_mode=macro_eligibility_trace_mode,
        )

    def advance_horizons(
        self,
        actual_return: float,
        step: int,
    ) -> List[PendingHorizon]:
        """Advance all pending horizons with the current bar's return.

        For each pending horizon:
        1. Accumulate the current bar return
        2. Check if evaluation horizon is reached
        3. If matured, evaluate directional credit and move to matured list

        Args:
            actual_return: Current bar's market return (signed).
            step: Current simulation step.
        """
        still_pending: List[PendingHorizon] = []
        matured_now: List[PendingHorizon] = []

        for horizon in self.pending_horizons:
            # Accumulate return for this bar
            horizon.accumulate_return(actual_return)

            # Check if matured (reached configured evaluation horizon)
            bars_elapsed = step - horizon.creation_step
            if bars_elapsed >= self.config.evaluation_horizon_bars:
                # Evaluate matured credit
                horizon.evaluate_maturity(self.config.evaluation_horizon_bars)
                self.matured_horizons.append(horizon)
                matured_now.append(horizon)
            else:
                still_pending.append(horizon)

        self.pending_horizons = still_pending

        # Trim matured list to prevent unbounded growth
        max_matured = self.config.max_pending_horizons * 2
        if len(self.matured_horizons) > max_matured:
            self.matured_horizons = self.matured_horizons[-max_matured:]

        return matured_now

    def get_matured_credits(self) -> Tuple[float, float]:
        """Get aggregate matured consequence credits.

        Returns gross positive and gross negative credits separately
        for net-positive gating of outcome budget claimants.

        Returns:
            Tuple of (gross_positive_credit, gross_negative_credit).
        """
        gross_pos = 0.0
        gross_neg = 0.0

        for h in self.matured_horizons:
            if h.is_matured:
                if h.gross_matured_credit > 0:
                    gross_pos += h.gross_matured_credit
                else:
                    gross_neg += h.gross_matured_credit

        return gross_pos, gross_neg

    def get_per_polyp_matured_credit(self) -> Dict[int, float]:
        """Get net matured credit per polyp.

        Returns:
            Dict mapping polyp_id -> net matured credit.
        """
        per_polyp: Dict[int, float] = defaultdict(float)

        for h in self.matured_horizons:
            if h.is_matured:
                per_polyp[h.polyp_id] += h.gross_matured_credit

        return dict(per_polyp)

    # ====================================================================
    # CALCIFICATION — Synaptic Consolidation
    # ====================================================================

    def step_calcification(
        self,
        edges: Dict[Tuple[int, int], Any],
        stdp_updates: List[STDPUpdate],
        temperature: float,
        step: int,
    ) -> int:
        """Update calcification states for all edges.

        Calcification tracks synaptic consolidation: as weights stabilize,
        synapses become more "frozen" (higher calcification). During
        changepoints, high plasticity temperature temporarily suppresses
        calcification, allowing rapid adaptation.

        Args:
            edges: Dict mapping (src, dst) -> edge object.
            stdp_updates: List of STDP updates from this step.
            temperature: Current plasticity temperature.
            step: Current simulation step.

        Returns:
            Number of calcification events (state changes).
        """
        event_count = 0

        # Group weight changes by edge
        weight_changes: Dict[Tuple[int, int], float] = defaultdict(float)
        for upd in stdp_updates:
            key = (upd.source_id, upd.target_id)
            weight_changes[key] += abs(upd.dw_modulated)

        # Update calcification for each edge
        for edge_key, edge in edges.items():
            # Get or create calcification state
            if edge_key not in self.calcification_states:
                self.calcification_states[edge_key] = CalcificationState(
                    edge_key=edge_key
                )

            calc_state = self.calcification_states[edge_key]

            # Sync from edge (in case edge object was modified externally)
            calc_state.calcification = getattr(edge, "calcification", calc_state.calcification)
            calc_state.synaptic_tag = getattr(edge, "synaptic_tag", calc_state.synaptic_tag)

            # Get weight change for this edge
            wc = weight_changes.get(edge_key, 0.0)

            # Update calcification
            had_event = calc_state.update(
                weight_change=wc,
                step=step,
                temperature=temperature,
                rate=self.config.calcification_rate,
            )
            if had_event:
                event_count += 1

            # Sync back to edge object
            edge.calcification = calc_state.calcification
            edge.synaptic_tag = calc_state.synaptic_tag

        return event_count

    def get_calcification_summary(self) -> Dict[str, Any]:
        """Get summary statistics of calcification states.

        Returns:
            Dict with mean, min, max calcification and tag values,
            plus count of fully consolidated synapses.
        """
        if not self.calcification_states:
            return {
                "mean_calcification": 0.0,
                "min_calcification": 0.0,
                "max_calcification": 0.0,
                "mean_tag": 0.0,
                "fully_consolidated_count": 0,
                "total_synapses": 0,
            }

        calcs = [
            s.calcification for s in self.calcification_states.values()
        ]
        tags = [s.synaptic_tag for s in self.calcification_states.values()]
        fully_consolidated = sum(1 for c in calcs if c > 0.95)

        return {
            "mean_calcification": float(np.mean(calcs)),
            "min_calcification": float(np.min(calcs)),
            "max_calcification": float(np.max(calcs)),
            "mean_tag": float(np.mean(tags)),
            "fully_consolidated_count": fully_consolidated,
            "total_synapses": len(calcs),
        }

    # ====================================================================
    # UTILITY / DIAGNOSTICS
    # ====================================================================

    def get_summary(self) -> Dict[str, Any]:
        """Get full learning manager summary statistics.

        Returns:
            Dict with cumulative counts, calcification summary, and
            horizon ledger status.
        """
        calc_summary = self.get_calcification_summary()
        gross_pos, gross_neg = self.get_matured_credits()
        macro_summary = self.get_macro_eligibility_summary()

        return {
            "step_count": self.step_count,
            "cumulative_stdp_updates": self.cumulative_stdp_updates,
            "cumulative_calcification_events": (
                self.cumulative_calcification_events
            ),
            "pending_horizons": len(self.pending_horizons),
            "matured_horizons": len(self.matured_horizons),
            "gross_positive_credit": gross_pos,
            "gross_negative_credit": gross_neg,
            "macro_eligibility_enabled": self.macro_eligibility_enabled(),
            "macro_eligibility_trace_mode": macro_summary["trace_mode"],
            "macro_eligibility_credit_mode": macro_summary["credit_mode"],
            "macro_eligibility_trace_abs_sum": macro_summary["trace_abs_sum"],
            "macro_eligibility_trace_nonzero_count": macro_summary["trace_nonzero_count"],
            "macro_eligibility_matured_updates": self._last_macro_eligibility_matured_updates,
            **calc_summary,
        }

    def reset_statistics(self) -> None:
        """Reset cumulative statistics without clearing state."""
        self.step_count = 0
        self.cumulative_stdp_updates = 0
        self.cumulative_calcification_events = 0

    def clear_horizons(self) -> None:
        """Clear all pending and matured horizon records."""
        self.pending_horizons.clear()
        self.matured_horizons.clear()
        self.macro_eligibility_traces.clear()
        self._last_macro_eligibility_matured_updates = 0
