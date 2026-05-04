"""
Trading Bridge for Coral Reef Architecture on SpiNNaker.

Provides task-level consequence (directional learning signal) from
market returns to drive dopamine-modulated STDP in the neuromorphic
colony.

The bridge:
1. Accumulates a 5-minute trailing return window for directional evaluation
2. Computes colony prediction from winner-take-all polyp spike readout
3. Calculates per-polyp reward via local market correctness
4. Produces task_signal and raw_dopamine for the learning manager
5. Tracks capital, positions, and Sharpe ratio with runtime-derived annualization

Biological Principles Preserved:
- Directional learning from smoothed multi-bar returns: the rectangular
  window of length evaluation_horizon_bars is the MVUE (minimum variance
  unbiased estimator) linear filter for a constant signal in white noise
  (Brockwell & Davis 2016 §1.4). Single-bar returns are noise; the 5m
  window extracts the directional signal.
- Immediate per-polyp reward follows LOCAL market correctness: each polyp
  is reinforced when its individual prediction direction matches the
  actual 5m return direction, independent of the executed colony action.
  This preserves specialist diversity (a dissenting specialist that was
  locally correct stays positively reinforced even when the colony was
  wrong).
- Endogenous prediction-error-normalized position sizing: position scales
  with colony prediction strength relative to recent prediction error,
  NOT raw return magnitude. Weak edges produce near-zero positions.
- Delayed matured consequence credit: horizon records mature on future
  held-position bars, not the prediction bar itself. The matured credit
  uses the bridge's capital-return scale, not the prediction head scale.
- Winner-take-all readout: Desimone & Duncan 1995 competitive attention.
  Only the top-k polyps by |RPE| contribute; democratic averaging
  cancels random predictors.

References:
- Brockwell, P.J. & Davis, R.A. (2016). Time Series: Theory and Methods,
  Springer, §1.4 (MVUE linear filter for constant signal in white noise).
- Frémaux, N., Sprekeler, H., & Gerstner, W. (2010). Functional
  requirements for reward-modulated spike-timing-dependent plasticity,
  J. Neurosci. 30(40):13326-13337.
- Desimone, R. & Duncan, J. (1995). Neural mechanisms of selective
  visual attention, Annu. Rev. Neurosci. 18:193-222.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Deque, Dict, Tuple, Any
from collections import deque
import math
import numpy as np

# ---------------------------------------------------------------------------
# Origin tags for configuration constants
# ---------------------------------------------------------------------------
# ENGINEERING: values chosen for numerical stability, training dynamics,
#              or implementation convenience. Not biologically constrained.
# biology_derived: values grounded in biological literature or principles.
# task_policy: values determined by the task objective (trading).
# stats_theory: values derived from statistical estimation theory.


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SECONDS_PER_YEAR: float = 365.25 * 24 * 3600  # ~31,557,600 s
# origin: stats_theory — exact seconds in Julian year for Sharpe annualization

EPSILON: float = 1e-8
# origin: ENGINEERING — prevents division by zero in normalization

MIN_EFFECTIVE_STD: float = 0.01
# origin: ENGINEERING — prediction std floor for dopamine resolution


@dataclass
class TradingConfig:
    """Trading bridge configuration.

    Every parameter is tagged with its origin to make explicit which
    values are biologically grounded versus engineering choices.

    Attributes:
        evaluation_horizon_bars: Width of the trailing return window.
            Rectangular window is the MVUE linear filter for a constant
            signal in white noise (Brockwell & Davis 2016 §1.4).
            origin: stats_theory
        minimum_effective_exposure_floor: Positions below this are
            treated as zero (tiny position suppression).
            origin: ENGINEERING
        bridge_history_window: Rolling window length for computing
            prediction error scale statistics.
            origin: ENGINEERING
        seed_output_scale: Initial scale factor for raw_dopamine.
            origin: ENGINEERING
        output_scale_adaptation_alpha: EMA decay for output_scale
            adaptation toward target std.
            origin: ENGINEERING
        initial_capital: Starting capital for paper trading.
            origin: task_policy
        max_position_change_per_step: Maximum |delta position| per bar.
            origin: ENGINEERING — limits trading frequency
        conviction_shrink_rate: Rate at which conviction shrinks toward
            zero as prediction error grows.
            origin: ENGINEERING
        direction_accuracy_threshold: Minimum directional accuracy
            before the bridge begins producing non-zero positions.
            origin: task_policy
        target_prediction_std: Target std for colony_prediction over
            recent window; output_scale adapts to hit this.
            origin: ENGINEERING — keeps dopamine in sensitive range
        max_pending_records: Maximum number of pending horizon records.
            origin: ENGINEERING — memory bound
    """

    # --- Horizon / window configuration ---
    evaluation_horizon_bars: int = 5
    # origin: stats_theory — 5m rectangular window is MVUE for
    #         constant-signal-in-white-noise (Brockwell & Davis §1.4)

    # --- Position sizing ---
    minimum_effective_exposure_floor: float = 5e-3
    # origin: ENGINEERING — suppress positions below this magnitude

    max_position_change_per_step: float = 0.1
    # origin: ENGINEERING — limits per-bar position change

    conviction_shrink_rate: float = 0.1
    # origin: ENGINEERING — shrinks position size as error grows

    direction_accuracy_threshold: float = 0.45
    # origin: task_policy — require >45% accuracy before trading

    # --- Prediction error scale ---
    bridge_history_window: int = 500
    # origin: ENGINEERING — rolling window for prediction error std

    # --- Output scaling (for dopamine) ---
    seed_output_scale: float = 0.1
    # origin: ENGINEERING — initial dopamine scale factor

    output_scale_adaptation_alpha: float = 0.01
    # origin: ENGINEERING — slow EMA for scale adaptation

    target_prediction_std: float = 0.1
    # origin: ENGINEERING — target std for colony_prediction

    dopamine_gain: float = 10000.0
    # origin: ENGINEERING — same saturating RPE gain used by LearningManager

    # --- Capital ---
    initial_capital: float = 1.0
    # origin: task_policy — starting capital

    # --- Delayed credit ---
    max_pending_records: int = 100
    # origin: ENGINEERING — memory bound for pending horizon records


@dataclass
class TaskOutcomeSurface:
    """The task consequence signal produced by the bridge each step.

    This is what drives dopamine in the learning manager and outcome
    budget in the energy allocator. It encapsulates every signal that
    the colony needs to learn from market interaction.

    Attributes:
        task_signal: Signed 5m return (direction + magnitude). This is
            the directional learning signal that enters the colony.
        actual_return_1m: The immediate single-bar return observed this
            step. Used for P&L and position valuation.
        actual_return_5m: Smoothed 5m trailing return for directional
            learning. This is the MVUE filter output.
        direction_correct: Whether colony prediction sign matched the
            actual 5m return sign.
        colony_prediction: The winner-take-all aggregated prediction
            produced by the bridge this step.
        position_size: The current held position after bridge sizing.
        capital_return: The P&L realized this step (position * return).
        capital: Cumulative capital after this step's P&L.
        prediction_error_scale: Recent std of absolute prediction
            errors, used for position normalization.
        raw_dopamine: The signal for STDP: prediction * signal * scale.
            Enters effective STDP resolution when prediction_std > 0.01.
        sharpe_ratio: Runtime-annualized Sharpe ratio using dt_ema,
            not hardcoded minute counts.
        time_in_market: Fraction of steps with non-zero position.
        mean_absolute_position: Average |position| over recent window.
    """

    task_signal: float = 0.0
    actual_return_1m: float = 0.0
    actual_return_5m: float = 0.0
    direction_correct: bool = False
    colony_prediction: float = 0.0
    position_size: float = 0.0
    capital_return: float = 0.0
    capital: float = 1.0
    prediction_error_scale: float = 1.0
    raw_dopamine: float = 0.0
    dopamine_output_scale: float = 0.1
    sharpe_ratio: float = 0.0
    time_in_market: float = 0.0
    mean_absolute_position: float = 0.0

    @property
    def held_position(self) -> float:
        """Alias for position_size (compatibility with learning_manager)."""
        return self.position_size


@dataclass
class PendingHorizonRecord:
    """A delayed consequence credit record.

    Tracks a prediction and the position held after it, accumulating
    future returns for matured credit. Only matures on bars where the
    post-trade held position could actually have influenced the return.

    This implements principle 4 (delayed matured consequence credit):
    the record starts with an EMPTY future-return ledger because the
    current bar's return was generated BEFORE the position was held.
    Returns accumulate on subsequent bars where the held_position was
    actually exposed to the market.

    Attributes:
        step: The simulation step when this prediction was made.
        stream_key: Identifier for the market stream.
        prediction: The colony prediction value at creation time.
        target_position: The position the bridge aimed for.
        held_position: The actual position held after this prediction.
            This is what gets used for matured credit calculation.
        capital_return_scale: The scale factor for converting returns
            to capital returns at maturity.
        future_returns: Deque of accumulated future returns. Starts
            EMPTY and grows until the record matures.
        is_matured: Whether this record has reached maturity.
        matured_credit: The final matured credit value.
    """

    step: int
    stream_key: str
    prediction: float
    target_position: float
    held_position: float = 0.0
    capital_return_scale: float = 0.0
    future_returns: Deque[float] = field(default_factory=lambda: deque())
    is_matured: bool = False
    matured_credit: float = 0.0


class PaperTrader:
    """Paper trading simulator for the Coral Reef Architecture.

    Simulates position taking, P&L tracking, and capital management.
    Produces the TaskOutcomeSurface that drives colony learning.

    The trader maintains:
    - Running capital and position state
    - A 5-minute trailing return window (rectangular deque, maxlen=5)
    - Rolling history of capital returns for Sharpe computation
    - An exponentially-weighted average of observed dt for annualization
    - Time-in-market tracking

    Position sizing uses endogenous prediction-error-normalized sizing:
    position_size = prediction / prediction_error_scale * conviction_shrink
    where conviction_shrink smoothly approaches zero as error grows.
    """

    def __init__(
        self,
        config: TradingConfig,
        stream_key: str = "default",
    ) -> None:
        """Initialize the paper trader.

        Args:
            config: TradingConfig with all bridge parameters.
            stream_key: Identifier for this market stream.
        """
        self.config: TradingConfig = config
        self.stream_key: str = stream_key

        # --- Capital state ---
        self.capital: float = config.initial_capital
        self.position: float = 0.0  # current held position
        self.step_count: int = 0

        # --- Return window: rectangular MVUE filter ---
        # origin: stats_theory — deque with maxlen implements the
        #         rectangular window for constant-signal-in-white-noise
        self.return_1m_window: Deque[float] = deque(
            maxlen=config.evaluation_horizon_bars
        )

        # --- Sharpe and statistics history ---
        self.capital_returns_history: Deque[float] = deque(
            maxlen=config.bridge_history_window
        )
        self.position_history: Deque[float] = deque(
            maxlen=config.bridge_history_window
        )

        # --- Runtime-derived dt for Sharpe annualization ---
        # origin: stats_theory — use observed inter-bar interval, not
        #         hardcoded 525600**0.5 (which assumes exact 1m bars)
        self.dt_ema: float = 60.0  # seed with 60 seconds (1m bar)
        self.dt_ema_alpha: float = 0.01  # slow adaptation
        # origin: ENGINEERING — slow EMA for dt stability

        # --- Direction accuracy tracking ---
        self.direction_correct_window: Deque[bool] = deque(
            maxlen=50  # recent window for accuracy estimate
        )
        # origin: ENGINEERING — 50-bar window for accuracy estimate

        # --- Position change smoothing ---
        self.prev_target_position: float = 0.0

    def step(
        self,
        colony_prediction: float,
        actual_return_1m: float,
        dt_seconds: float,
    ) -> TaskOutcomeSurface:
        """Execute one trading step.

        Pipeline:
        1. Update the 5m trailing return window with new 1m return
        2. Compute smoothed 5m return (directional signal)
        3. Compute directional correctness
        4. Calculate target position via error-normalized sizing
        5. Smooth position change (rate limiting)
        6. Realize P&L from held position on this bar
        7. Update capital
        8. Update Sharpe statistics

        Args:
            colony_prediction: The colony's prediction for this step.
            actual_return_1m: The observed single-bar return.
            dt_seconds: Wall-clock seconds since last bar (for dt_ema).

        Returns:
            TaskOutcomeSurface with all consequence signals.
        """
        # --- 1. Update dt EMA (runtime-derived, not hardcoded) ---
        self.dt_ema = (
            self.dt_ema_alpha * dt_seconds
            + (1.0 - self.dt_ema_alpha) * self.dt_ema
        )

        # --- 2. Accumulate 5m trailing return window ---
        self.return_1m_window.append(actual_return_1m)
        # Rectangular window: unbiased linear filter for constant signal
        # in white noise (Brockwell & Davis 2016 §1.4)
        actual_return_5m: float = float(np.sum(list(self.return_1m_window)))

        # --- 3. Directional correctness ---
        actual_sign_5m: int = self._sign(actual_return_5m)
        prediction_sign: int = self._sign(colony_prediction)
        direction_correct: bool = prediction_sign == actual_sign_5m
        self.direction_correct_window.append(direction_correct)

        # --- 4. Prediction error scale (endogenous normalization) ---
        prediction_error_scale: float = self._compute_prediction_error_scale(
            colony_prediction, actual_return_1m
        )

        # --- 5. Conviction shrink (smooth decay toward zero as error grows) ---
        conviction: float = self._compute_conviction(
            prediction_error_scale
        )

        # --- 6. Target position via error-normalized sizing ---
        # Position = prediction / error_scale * conviction_shrink
        # origin: task_policy — weak edges produce near-zero positions
        raw_target: float = colony_prediction / (
            prediction_error_scale + EPSILON
        ) * conviction

        # Suppress tiny positions
        if abs(raw_target) < self.config.minimum_effective_exposure_floor:
            raw_target = 0.0

        # Require minimum direction accuracy before trading
        accuracy: float = self._get_recent_direction_accuracy()
        if accuracy < self.config.direction_accuracy_threshold:
            raw_target = 0.0

        # --- 7. Smooth position change (rate limiting) ---
        position_change: float = np.clip(
            raw_target - self.prev_target_position,
            -self.config.max_position_change_per_step,
            self.config.max_position_change_per_step,
        )
        target_position: float = self.prev_target_position + position_change
        self.prev_target_position = target_position

        # --- 8. Realize P&L from held position ---
        # P&L = position * return (held position generates return this bar)
        capital_return: float = self.position * actual_return_1m
        self.capital += capital_return

        # Update held position to the new target
        self.position = target_position

        # --- 9. Track statistics ---
        self.capital_returns_history.append(capital_return)
        self.position_history.append(abs(self.position))
        self.step_count += 1

        # --- 10. Build outcome surface ---
        outcome = TaskOutcomeSurface(
            task_signal=actual_return_5m,
            actual_return_1m=actual_return_1m,
            actual_return_5m=actual_return_5m,
            direction_correct=direction_correct,
            colony_prediction=colony_prediction,
            position_size=self.position,
            capital_return=capital_return,
            capital=self.capital,
            prediction_error_scale=prediction_error_scale,
            raw_dopamine=0.0,  # filled by TradingBridge
            sharpe_ratio=self.sharpe_ratio,
            time_in_market=self.time_in_market_fraction,
            mean_absolute_position=self._mean_abs_position(),
        )

        return outcome

    def _compute_prediction_error_scale(
        self, colony_prediction: float, actual_return: float
    ) -> float:
        """Compute recent std of absolute prediction errors.

        Uses a rolling window of absolute errors for endogenous
        normalization. The error scale determines how aggressively
        the bridge sizes positions: high error -> smaller positions.

        Args:
            colony_prediction: The colony's prediction this step.
            actual_return: The observed 1m return.

        Returns:
            The rolling std of absolute prediction errors.
        """
        # Compute absolute prediction error for this step
        abs_error: float = abs(colony_prediction - actual_return)

        # Maintain rolling window of absolute errors
        if not hasattr(self, "_abs_error_window"):
            self._abs_error_window: Deque[float] = deque(
                maxlen=self.config.bridge_history_window
            )
        self._abs_error_window.append(abs_error)

        # Rolling std over the window
        if len(self._abs_error_window) < 2:
            return 1.0  # default before enough data

        window_array: np.ndarray = np.array(self._abs_error_window)
        return float(np.std(window_array, ddof=1))

    def _compute_conviction(self, error_scale: float) -> float:
        """Compute conviction shrink factor.

        As prediction error grows, conviction smoothly shrinks toward
        zero, preventing weak edges from producing persistent exposure.
        Uses exponential decay of conviction with error scale.

        Args:
            error_scale: The current prediction error std.

        Returns:
            Conviction factor in [0, 1].
        """
        # conviction = exp(-shrink_rate * error_scale)
        # origin: ENGINEERING — smooth exponential shrink
        conviction: float = math.exp(
            -self.config.conviction_shrink_rate * error_scale
        )
        return conviction

    def _get_recent_direction_accuracy(self) -> float:
        """Estimate recent directional accuracy.

        Returns the fraction of recent steps where colony sign matched
        actual 5m return sign. Before enough data, returns 1.0 (permissive).

        Returns:
            Recent directional accuracy in [0, 1].
        """
        if len(self.direction_correct_window) < 10:
            return 1.0  # permissive until enough data
        return float(np.mean(self.direction_correct_window))

    def _mean_abs_position(self) -> float:
        """Compute mean absolute position over recent history.

        Returns:
            Mean |position| over the position history window.
        """
        if len(self.position_history) == 0:
            return 0.0
        return float(np.mean(self.position_history))

    @property
    def sharpe_ratio(self) -> float:
        """Runtime-annualized Sharpe ratio.

        Uses the exponentially-weighted average of observed dt (dt_ema),
        NOT a hardcoded 525600**0.5. This correctly annualizes for
        irregular bar intervals.

        Formula: sharpe = mean(returns) / std(returns) * sqrt(SECONDS_PER_YEAR / dt_ema)

        Returns:
            Annualized Sharpe ratio, or 0.0 if insufficient data.
        """
        if len(self.capital_returns_history) < 10:
            return 0.0

        returns: np.ndarray = np.array(self.capital_returns_history)
        mean_ret: float = float(np.mean(returns))
        std_ret: float = float(np.std(returns, ddof=1))

        if std_ret < EPSILON:
            return 0.0

        # Runtime-derived annualization factor
        # origin: stats_theory — sqrt(trading_periods_per_year) where
        #         periods_per_year = SECONDS_PER_YEAR / dt_ema
        annualization: float = math.sqrt(SECONDS_PER_YEAR / self.dt_ema)

        sharpe: float = mean_ret / std_ret * annualization
        return sharpe

    @property
    def time_in_market_fraction(self) -> float:
        """Fraction of steps with non-zero position.

        Returns:
            Fraction of steps where |position| > exposure floor.
        """
        if self.step_count == 0:
            return 0.0
        return float(np.sum(np.array(self.position_history) > self.config.minimum_effective_exposure_floor)) / max(len(self.position_history), 1)

    @staticmethod
    def _sign(x: float) -> int:
        """Return the sign of a scalar (-1, 0, or +1).

        Args:
            x: The input value.

        Returns:
            -1 if x < 0, 0 if x == 0, +1 if x > 0.
        """
        if x > EPSILON:
            return 1
        elif x < -EPSILON:
            return -1
        return 0

    @property
    def current_position(self) -> float:
        """Return the current held position.

        Returns:
            Current position size.
        """
        return self.position


class TradingBridge:
    """Main bridge between colony readout and task consequence.

    The bridge is the ONLY place where market data enters the colony.
    All downstream signals (dopamine, outcome budget, delayed credit)
    derive from the TaskOutcomeSurface produced here.

    Pipeline per step:
    1. Receives spike rates / predictions from polyp population
    2. Applies winner-take-all: top-k by |last_raw_rpe|, zero the rest
    3. Computes colony_prediction = weighted average of winners
    4. Runs PaperTrader to get task consequence (returns, P&L, Sharpe)
    5. Computes per-polyp rewards via LOCAL market correctness
    6. Produces raw_dopamine for the learning manager
    7. Updates delayed horizon records for matured consequence credit

    Winner-take-all (Desimone & Duncan 1995):
    - Top k = max(3, int(sqrt(N))) polyps by |RPE| contribute
    - Non-winners are ZEROED before normalization, not just downweighted
    - This prevents democratic averaging from canceling random predictors

    Per-polyp reward (Frémaux et al. 2010 principle):
    - sign = sign(polyp_prediction) * sign(actual_5m_return)
    - magnitude = tanh(blended_rpe)
    - A dissenting specialist with correct local direction gets positive
      reward even when the colony action was wrong
    """

    def __init__(
        self,
        config: TradingConfig,
        stream_key: str = "default",
    ) -> None:
        """Initialize the trading bridge.

        Args:
            config: TradingConfig with all bridge parameters.
            stream_key: Identifier for this market stream.
        """
        self.config: TradingConfig = config
        self.stream_key: str = stream_key

        # --- Paper trader for simulation ---
        self.paper_trader: PaperTrader = PaperTrader(config, stream_key)

        # --- Output scale adaptation ---
        # Adapts seed_output_scale so colony_prediction std converges
        # to target_prediction_std, keeping dopamine in sensitive range.
        self.output_scale: float = config.seed_output_scale
        self._prediction_window: Deque[float] = deque(
            maxlen=config.bridge_history_window
        )

        # --- Delayed consequence credit records ---
        self.pending_horizons: List[PendingHorizonRecord] = []
        self._step_counter: int = 0

        # --- Running totals for matured consequence ---
        self._total_matured_positive: float = 0.0
        self._total_matured_negative: float = 0.0

    def compute_colony_prediction(
        self,
        polyp_states: List[Any],
        spike_counts: Dict[int, int],
    ) -> float:
        """Winner-take-all readout: top-k by |RPE|, zero the rest.

        Implements competitive winner-take-all selection following
        Desimone & Duncan (1995). Attention selectively enhances
        task-relevant (high |RPE|) polyp responses while suppressing
        distractors. Democratic averaging of all polyps cancels random
        predictors; WTA preserves specialist signal.

        The selection process:
        1. Extract |last_raw_rpe| from each polyp state
        2. Select top k = max(3, int(sqrt(N))) polyps
        3. ZERO all non-selected polyp contributions
        4. Normalize winner weights by sum of |RPE|
        5. Compute weighted prediction from winners

        Args:
            polyp_states: List of polyp state objects. Each must have
                attributes: last_raw_rpe (float), current_prediction (float).
            spike_counts: Dict mapping polyp_id to spike count.

        Returns:
            Colony prediction as weighted average of top-k winners.
        """
        n_polyps: int = len(polyp_states)
        if n_polyps == 0:
            return 0.0

        # Determine k: max(3, int(sqrt(N)))
        # origin: biology_derived — sparse readout; 3 is minimum quorum
        k: int = max(3, int(math.sqrt(n_polyps)))

        # Extract |RPE| and predictions from each polyp
        rpe_values: np.ndarray = np.zeros(n_polyps)
        predictions: np.ndarray = np.zeros(n_polyps)

        for i, state in enumerate(polyp_states):
            # last_raw_rpe: the raw reward prediction error from this polyp
            rpe_val: float = getattr(state, "last_raw_rpe", 0.0)
            rpe_values[i] = abs(rpe_val)  # use |RPE| for selection
            predictions[i] = getattr(state, "current_prediction", 0.0)

        # Winner-take-all: select top-k by |RPE|
        # Get indices that would sort by |RPE| descending
        top_k_indices: np.ndarray = np.argsort(rpe_values)[::-1][:k]

        # Create winner mask: 1.0 for winners, 0.0 for non-winners
        # This ZEROES non-top-k polyps (principle 5)
        winner_mask: np.ndarray = np.zeros(n_polyps)
        winner_mask[top_k_indices] = 1.0

        # Weighted by |RPE| among winners
        winner_weights: np.ndarray = rpe_values * winner_mask
        weight_sum: float = float(np.sum(winner_weights))

        if weight_sum < EPSILON:
            # Fallback to unweighted mean of winners if all RPEs are near zero
            winner_count: int = int(np.sum(winner_mask))
            if winner_count == 0:
                return 0.0
            colony_pred: float = float(
                np.sum(predictions * winner_mask) / winner_count
            )
        else:
            # Normalize winner weights and compute weighted prediction
            normalized_weights: np.ndarray = winner_weights / weight_sum
            colony_pred = float(np.dot(predictions, normalized_weights))

        return colony_pred

    def evaluate_step(
        self,
        market_return_1m: float,
        dt_seconds: float,
        polyp_states: List[Any],
        spike_counts: Dict[int, int],
    ) -> TaskOutcomeSurface:
        """Full step: predict -> trade -> evaluate -> produce consequence.

        This is the main entry point for the trading bridge each bar.
        It orchestrates the full pipeline from colony readout to task
        consequence production.

        Pipeline:
        1. Compute colony prediction via winner-take-all readout
        2. Run paper trader with prediction and market return
        3. Compute raw_dopamine for STDP
        4. Update output scale adaptation
        5. Update delayed horizon records
        6. Advance step counter

        Args:
            market_return_1m: The observed 1-minute market return.
            dt_seconds: Wall-clock seconds since last bar.
            polyp_states: List of polyp state objects from the colony.
            spike_counts: Dict mapping polyp_id to spike count this bar.

        Returns:
            TaskOutcomeSurface with all consequence signals filled.
        """
        # --- Step 1: Colony prediction via WTA readout ---
        colony_prediction: float = self.compute_colony_prediction(
            polyp_states, spike_counts
        )

        # --- Exploration noise: break symmetry when predictions are near-zero ---
        # Without noise, all polyp predictions = 0 → dopamine = 0 → no STDP learning.
        # Small Gaussian perturbation bootstraps the reward signal.
        # Noise decays as colony learns (detected by prediction std growth).
        if abs(colony_prediction) < 0.001 and self._step_counter < 500:
            exploration_std = 0.05 * max(0.1, 1.0 - self._step_counter / 500.0)
            colony_prediction += float(np.random.normal(0.0, exploration_std))

        # --- Step 2: Paper trading ---
        outcome: TaskOutcomeSurface = self.paper_trader.step(
            colony_prediction=colony_prediction,
            actual_return_1m=market_return_1m,
            dt_seconds=dt_seconds,
        )

        # --- Step 3: Populate diagnostic raw_dopamine ---
        # LearningManager is the canonical dopamine authority during organism
        # training.  The bridge still computes the same formula for standalone
        # bridge tests and telemetry, and Organism overwrites it with the
        # LearningManager value before hardware delivery.
        task_signal: float = outcome.actual_return_5m
        rpe = colony_prediction * task_signal * self.output_scale
        raw_dopamine: float = math.tanh(rpe * self.config.dopamine_gain)
        outcome.raw_dopamine = raw_dopamine
        outcome.dopamine_output_scale = self.output_scale
        outcome.colony_prediction = colony_prediction

        # --- Step 4: Output scale adaptation ---
        # Adapt output_scale so colony_prediction std -> target_prediction_std
        # origin: ENGINEERING — keeps dopamine in sensitive range for STDP
        self._prediction_window.append(colony_prediction)
        if len(self._prediction_window) >= 10:
            pred_std: float = float(np.std(np.array(self._prediction_window), ddof=1))
            if pred_std > EPSILON:
                # Gradual adaptation toward target
                target_std: float = self.config.target_prediction_std
                adjustment: float = (
                    self.config.output_scale_adaptation_alpha
                    * (target_std / pred_std - 1.0)
                )
                self.output_scale *= 1.0 + adjustment
                # Clamp to reasonable bounds
                self.output_scale = float(
                    np.clip(self.output_scale, 0.001, 10.0)
                )

        # --- Step 5: Delayed consequence credit ---
        # Update and mature pending horizon records
        self.update_delayed_horizons(self._step_counter, outcome)

        # Create a new pending record for this step's prediction
        self._create_pending_horizon_record(outcome, colony_prediction)

        # --- Step 6: Advance step counter ---
        self._step_counter += 1

        return outcome

    def _create_pending_horizon_record(
        self,
        outcome: TaskOutcomeSurface,
        colony_prediction: float,
    ) -> None:
        """Create a new pending horizon record for delayed credit.

        The record starts with an EMPTY future_returns deque because
        the current bar's return was generated BEFORE the position
        was held. Returns accumulate on subsequent bars.

        Args:
            outcome: The current step's TaskOutcomeSurface.
            colony_prediction: The colony prediction this step.
        """
        # Evict oldest record if at capacity
        if len(self.pending_horizons) >= self.config.max_pending_records:
            # Remove the oldest matured record, or oldest overall
            matured_indices: List[int] = [
                i
                for i, r in enumerate(self.pending_horizons)
                if r.is_matured
            ]
            if matured_indices:
                # Remove oldest matured
                self.pending_horizons.pop(matured_indices[0])
            else:
                # Remove oldest overall (force eviction)
                self.pending_horizons.pop(0)

        record = PendingHorizonRecord(
            step=self._step_counter,
            stream_key=self.stream_key,
            prediction=colony_prediction,
            target_position=outcome.position_size,
            held_position=outcome.position_size,
            capital_return_scale=1.0,  # identity scaling; can be customized
            # future_returns starts EMPTY — this is critical for principle 4
            # The current bar's return is NOT included because the position
            # was not held during this bar's price formation.
        )
        self.pending_horizons.append(record)

    def update_delayed_horizons(
        self,
        step: int,
        task_outcome: TaskOutcomeSurface,
    ) -> None:
        """Advance and mature delayed consequence records.

        Each pending record accumulates future returns from subsequent
        bars. When the accumulated return count reaches
        evaluation_horizon_bars, the record matures and produces a
        delayed credit signal.

        Critical implementation details (principle 4):
        - Records start with EMPTY future-return ledger
        - Returns accumulate only on bars AFTER the prediction bar
        - Matured credit uses held_position, not target_position
        - Matured credit uses capital-return scale, not prediction scale

        Args:
            step: The current simulation step.
            task_outcome: The current step's TaskOutcomeSurface.
        """
        return_1m: float = task_outcome.actual_return_1m

        for record in self.pending_horizons:
            if record.is_matured:
                continue

            # Accumulate this bar's return into the record's future ledger
            # This happens for every bar AFTER the record's creation
            record.future_returns.append(return_1m)

            # Check if the record has reached maturity
            if (
                len(record.future_returns)
                >= self.config.evaluation_horizon_bars
            ):
                # Compute matured credit from accumulated returns
                total_future_return: float = float(
                    np.sum(record.future_returns)
                )

                # Credit uses held_position * capital_return_scale
                # origin: task_policy — credit the return on what was
                #         actually held, not what was targeted
                record.matured_credit = (
                    record.held_position
                    * total_future_return
                    * record.capital_return_scale
                )
                record.is_matured = True

                # Accumulate into running totals
                if record.matured_credit > 0:
                    self._total_matured_positive += record.matured_credit
                else:
                    self._total_matured_negative += abs(record.matured_credit)

    def compute_per_polyp_reward(
        self,
        polyp_state: Any,
        task_outcome: TaskOutcomeSurface,
        colony_prediction: float,
    ) -> float:
        """Compute immediate reward for a single polyp.

        This is the LOCAL market correctness reward (principle 2):
        - sign = sign(polyp_prediction) * sign(actual_5m_return)
        - magnitude = tanh(|blended_rpe|)

        A dissenting specialist (polyp predicts +, colony predicts -)
        still gets POSITIVE reward if its local direction was correct
        (i.e., the actual 5m return was positive). This preserves
        specialist diversity — specialists are NOT punished for
        disagreeing with the colony when they were locally correct.

        This follows Frémaux et al. (2010): the reward signal should
        reflect the individual neuron's contribution to the task,
        not just agreement with the population readout.

        Args:
            polyp_state: A polyp state object with attributes:
                current_prediction (float), last_raw_rpe (float).
            task_outcome: The current step's TaskOutcomeSurface.
            colony_prediction: The colony prediction (for reference).

        Returns:
            The per-polyp reward: signed scalar for this polyp.
        """
        # Extract polyp's individual prediction
        polyp_prediction: float = getattr(
            polyp_state, "current_prediction", 0.0
        )
        blended_rpe: float = getattr(polyp_state, "last_raw_rpe", 0.0)

        # Actual 5m return sign
        actual_5m: float = task_outcome.actual_return_5m

        # Local directional correctness sign
        # sign = sign(polyp_prediction) * sign(actual_5m_return)
        # origin: biology_derived — each polyp reinforced for its own
        #         directional correctness, independent of colony action
        polyp_sign: int = self._sign(polyp_prediction)
        actual_sign: int = self._sign(actual_5m)
        reward_sign: float = float(polyp_sign * actual_sign)

        # Magnitude: tanh(|blended_rpe|)
        # origin: ENGINEERING — canonical saturator prevents runaway
        #         reinforcement while preserving rank ordering
        rpe_magnitude: float = float(np.tanh(abs(blended_rpe)))

        # Final reward: sign * magnitude
        reward: float = reward_sign * rpe_magnitude

        return reward

    def compute_all_polyp_rewards(
        self,
        polyp_states: List[Any],
        task_outcome: TaskOutcomeSurface,
    ) -> np.ndarray:
        """Compute rewards for all polyps in the colony.

        Convenience method that applies compute_per_polyp_reward to
        each polyp state and returns a numpy array.

        Args:
            polyp_states: List of polyp state objects.
            task_outcome: The current step's TaskOutcomeSurface.

        Returns:
            Numpy array of rewards, one per polyp.
        """
        colony_prediction: float = task_outcome.colony_prediction
        rewards: List[float] = []

        for polyp_state in polyp_states:
            reward: float = self.compute_per_polyp_reward(
                polyp_state, task_outcome, colony_prediction
            )
            rewards.append(reward)

        return np.array(rewards)

    def get_matured_consequence_totals(self) -> Tuple[float, float]:
        """Return cumulative matured consequence totals.

        Returns:
            Tuple of (gross_positive, gross_negative) matured credit.
            These are cumulative sums across all matured records.
        """
        return (self._total_matured_positive, self._total_matured_negative)

    def get_pending_record_count(self) -> int:
        """Return the number of pending (non-matured) horizon records.

        Returns:
            Count of pending records awaiting maturity.
        """
        return sum(1 for r in self.pending_horizons if not r.is_matured)

    def get_matured_record_count(self) -> int:
        """Return the number of matured horizon records.

        Returns:
            Count of matured records.
        """
        return sum(1 for r in self.pending_horizons if r.is_matured)

    @property
    def current_output_scale(self) -> float:
        """Return the current adapted output scale.

        Returns:
            Current output_scale value.
        """
        return self.output_scale

    @property
    def current_sharpe_ratio(self) -> float:
        """Return the current Sharpe ratio from the paper trader.

        Returns:
            Runtime-annualized Sharpe ratio.
        """
        return self.paper_trader.sharpe_ratio

    @property
    def current_capital(self) -> float:
        """Return the current capital from the paper trader.

        Returns:
            Current capital value.
        """
        return self.paper_trader.capital

    @staticmethod
    def _sign(x: float) -> int:
        """Return the sign of a scalar (-1, 0, or +1).

        Args:
            x: The input value.

        Returns:
            -1 if x < 0, 0 if x == 0, +1 if x > 0.
        """
        if x > EPSILON:
            return 1
        elif x < -EPSILON:
            return -1
        return 0


# ---------------------------------------------------------------------------
# Polyp state protocol (for reference / type checking)
# ---------------------------------------------------------------------------
class PolypStateProtocol:
    """Protocol defining the interface expected from polyp states.

    Polyp state objects passed to the bridge must expose these attributes.
    This is a protocol (structural subtyping), not a required base class.
    """

    last_raw_rpe: float      # last raw reward prediction error
    current_prediction: float  # current directional prediction

    # Optional attributes that may be used for debugging
    polyp_id: int
    spike_count: int
