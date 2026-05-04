"""
Coral Reef Architecture (CRA) Configuration Module for SpiNNaker / PyNN.

This module defines all tunable parameters for the multi-agent neural substrate
as Python dataclasses.  Every field carries a provenance tag in its docstring:

    [biology_derived]      — Directly motivated by a biological observation or
                             neuroscientific citation.
    [biology_inherited]    — Heritable trait whose value is drawn from a
                             log-normal distribution at polyp birth.
    [ENGINEERING]          — Hard-wired engineering constant chosen for
                             stability, numerical health, or SpiNNaker
                             compatibility.
    [task_policy]          — Task-level policy knob (e.g. evaluation horizon).
    [measurement_protocol] — Parameter governing the MI / BOCPD measurement
                             layer.
    [runtime_ui]           — User-tunable runtime flag (debug verbosity, etc.).
    [numerical]            — Pure numerical safeguard (epsilon, clip bounds).

Biological First Principles
---------------------------
The CRA replaces back-propagation and global loss with a local **trophic-
survival economy**.  Each polyp (neuron) maintains a scalar ``trophic_health``.
Energy flows from sensory streams → polyps → outcomes, with retrograde
trophic feedback on active edges.  Polyps die when ``trophic_health`` falls
below ``apoptosis_threshold`` (BAX-driven, activity-dependent pruning à la
Katz & Shatz 1996) and reproduce when ``cyclin_d`` exceeds 0.5 (G1/S
checkpoint, Morgan 1995).

Key Equations (preserved verbatim)
----------------------------------
::

    drive              = _last_mi_or_zero * _uptake_rate
                         + _da_gain * dopamine_ema
    firing_rate        = max(0, drive)

    sensory_budget_s   = (1 - exp(-stream_mi_s))
                         * median(recovery_demand_q)
                         over direct extero claimants q on s

    outcome_budget     = max(0, task_consequence_signal)
                         * median(recovery_demand_q)
                         over positive task claimants q

    retrograde_release = receiver-spent trophic on active incoming edges,
                         weighted by receiver-local causal contribution

    earned_support_p   = sensory_capture_p + outcome_capture_p
                         + retrograde_received_p

    effective_decay    = _metabolic_decay
                         + _trophic_synapse_cost * degree

    trophic_health     = (trophic_health - retrograde_spent_p + total_support_p)
                         * exp(-effective_decay * dt)

References
----------
- Desimone & Duncan (1995)  Neural mechanisms of selective visual attention.
- Katz & Shatz (1996)     Synaptic activity and the construction of cortical
                          circuits.  *Science* 274:1133-1138.
- Kraskov, Stogbauer & Grassberger (2004)  Estimating mutual information.
                          *PRL* 69:066138.
- Ince, Giordano, Kayser et al. (2017)  A novel estimator for MI.  *PLOS
                          Comput Biol* 13(1):e1005036.
- Adams & MacKay (2007)   Bayesian Online Changepoint Detection.
- Morgan (1995)           Principles of CDK regulation.  *Nature* 374:131-134.

Author: Coral Reef Architecture team (v009bz SpiNNaker port)
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Global numerical safeguards
# ---------------------------------------------------------------------------

EPSILON: float = 1e-7
"""[numerical] Floor to prevent division by zero in log / sqrt operations."""

KSG_MAX_RELIABLE_DIM: int = 8
"""[ENGINEERING] Kraskov estimator becomes data-hungry above 8 dims."""

MI_ESTIMATE_NAN: float = 0.0
"""[ENGINEERING] Returned when MI cannot be estimated (insufficient samples)."""


# =============================================================================
# 1. EnergyConfig — Trophic economy parameters
# =============================================================================

@dataclass
class EnergyConfig:
    """Trophic-energy constants and heritable energy traits.

    These parameters govern the flow of trophic currency through the reef:
    sensory capture, outcome capture, retrograde transport, metabolic decay,
    and the apoptotic / reproductive thresholds.
    """

    # --- Engineering-calibrated neurotrophic constants -----------------------

    bdnf_per_trophic_source: float = 0.024
    """[ENGINEERING] BDNF molecules released per unit trophic per synapse.

    Calibrated against neurotrophic theory (Katz & Shatz 1996; Lu & Figurov
    1997).  The value 0.024 ensures that a moderately active (MI ~ 0.5)
    hidden polyp receives enough support to offset metabolic_decay ~ 0.005
    over a 1-second window.
    """

    bdnf_uptake_saturation: float = 1.0
    """[ENGINEERING] Maximum fractional uptake of BDNF per synapse per step.

    Prevents runaway positive feedback when a polyp has many active parents.
    """

    bdnf_uptake_efficiency_default: float = 0.5
    """[biology_inherited] Default heritable TrkB/BDNF uptake efficiency.

    Distinct from ``bdnf_uptake_saturation``: this is the newborn trait value,
    while saturation is the per-step allocation ceiling.
    """

    # --- Metabolic cost defaults (heritable) ---------------------------------

    metabolic_decay_default: float = 0.005
    """[biology_derived] Base exponential decay constant for ``trophic_health``.

    Corresponds to a half-life of ~138 steps (ln(2)/0.005).  Motivated by
    activity-dependent metabolic rates in neocortical pyramidal neurons
    (Attwell & Laughlin 2001).
    """

    trophic_synapse_cost_default: float = 0.001
    """[biology_derived] Additional per-edge metabolic cost.

    ``effective_decay = metabolic_decay + trophic_synapse_cost * degree``.
    Reflects the ATP demand of maintaining synaptic vesicle pools and
    postsynaptic receptor scaffolding (Rangaraju et al. 2014).
    """

    # --- Child inheritance ---------------------------------------------------

    child_trophic_share_default: float = 0.5
    """[biology_derived] Fraction of parent ``trophic_health`` bequeathed to
    offspring at G1/S division.

    Log-normal inheritance (heritable trait) ensures trophic is never created
    ex nihilo; total reef trophic is conserved except for sensory/outcome
    inflows and metabolic decay outflows.  Value 0.5 mirrors symmetric
    cytokinesis in neuronal progenitor divisions (Chenn & McConnell 1995).
    """

    child_trophic_share_sigma_log: float = 0.3
    """[ENGINEERING] Std-dev of the log-normal perturbation on
    ``child_trophic_share`` inheritance.  sigma_log = 0.3 gives ~25 %
    coefficient of variation while keeping draws in (0.1, 0.9) with > 95 %
    probability.
    """

    # --- Apoptosis (BAX-driven) ----------------------------------------------

    apoptosis_threshold_default: float = 0.1
    """[biology_derived] ``trophic_health`` floor below which BAX accumulates.

    When ``trophic_health < apoptosis_threshold``, the pro-apoptotic factor
    BAX is activated (Oltvai, Milliman & Korsmeyer 1993).  Persistent deficit
    drives programmed cell death (activity-dependent pruning, Katz & Shatz
    1996).
    """

    bax_accumulation_rate: float = 0.002
    """[biology_derived] Per-step BAX accumulation when ``trophic_health`` is
    below ``apoptosis_threshold``.

    Modelled as a leaky integrator: ``bax_level += bax_accumulation_rate``
    per sub-threshold step.  Death triggers when ``bax_level >= 1.0``.
    """

    bax_decay_rate: float = 0.001
    """[biology_derived] BAX natural degradation when polyp is above threshold.

    Allows transient dips below threshold to be recovered from (homeostatic
    resilience).
    """

    bax_death_threshold: float = 1.0
    """[ENGINEERING] Normalised BAX level triggering apoptosis."""

    # --- Survival accuracy floor ---------------------------------------------

    accuracy_survival_floor: float = 0.45
    """[biology_derived] Minimum directional-accuracy EMA for survival.

    Polyps whose ``directional_accuracy_ema`` falls below this floor become
    eligible for pruning even if ``trophic_health`` is mildly positive.
    Motivated by the ~50 % activity threshold below which retinal axons are
    pruned in the LGN (Katz & Shatz 1996).
    """

    accuracy_penalty_multiplier: float = 0.5
    """[ENGINEERING] Factor by which trophic inflow is scaled when accuracy
    is below ``accuracy_survival_floor``.
    """

    # --- Reproduction (cyclin D checkpoint) ----------------------------------

    cyclin_d_threshold: float = 0.5
    """[biology_derived] G1/S transition threshold (Morgan 1995).

    A polyp enters the S-phase of its cell cycle when ``cyclin_d >= 0.5``.
    ``cyclin_d`` accumulates in proportion to ``trophic_health`` and decays
    baseline.  Directly models the restriction-point checkpoint in neuronal
    progenitors.
    """

    cyclin_d_accumulation_base: float = 1.0
    """[biology_derived] Correlated synthesis rate of cyclin D.

    Accumulation per step: ``+= cyclin_d_accumulation_base * trophic_health``.
    """

    cyclin_d_degradation_base: float = 0.5
    """[biology_derived] Baseline cyclin D degradation per step.

    Degradation per step: ``-= cyclin_d_degradation_base * cyclin_d``.
    """

    # --- Retrograde trophic --------------------------------------------------

    retrograde_fraction_default: float = 0.3
    """[biology_derived] Fraction of receiver-spent trophic recycled back to
    senders on active incoming edges.

    Models neurotrophin retrograde transport (e.g. NGF/TrkA signalling from
    hippocampus to basal forebrain; Campenot 1977).
    """

    causal_contribution_temperature: float = 1.0
    """[ENGINEERING] Softmax temperature for weighting retrograde release by
    receiver-local causal contribution.  Lower = sharper winner-take-all.
    """

    # --- Support aggregation -------------------------------------------------

    support_ema_alpha: float = 0.1
    """[ENGINEERING] EMA smoothing coefficient for ``earned_support`` tracking.
    """

    min_trophic_health: float = 0.0
    """[numerical] Hard floor for ``trophic_health`` (never negative)."""

    max_trophic_health: float = 10.0
    """[numerical] Soft cap preventing unbounded trophic accumulation."""

    # --- BOCPD-gated plasticity ----------------------------------------------

    bocpd_plasticity_multiplier: float = 2.5
    """[ENGINEERING] Plasticity temperature boost when BOCPD detects a
    changepoint.  Multiplies the base learning rate during elevated
    uncertainty."""

    bocpd_changepoint_threshold: float = 0.5
    """[ENGINEERING] Minimum changepoint probability to trigger elevated
    plasticity."""

    # --- Reproduction supportability -----------------------------------------

    min_reproduction_supportability_ratio: float = 1.05
    """[ENGINEERING] Minimum ratio of earned support to survival cost for
    a polyp to be eligible for reproduction."""

    maternal_survival_fraction: float = 0.5
    """[biology_derived] Fraction of maternal reserve allocated to the
    survival floor (vs. growth budget)."""

    retrograde_activity_threshold: float = 0.01
    """[ENGINEERING] Minimum presynaptic activity for retrograde support
    eligibility.  Prevents quiescent edges from claiming resources."""

    max_retrograde_candidates: int = 24
    """[ENGINEERING] O(N^2) fallback bound for retrograde support
    candidate selection."""


# =============================================================================
# 2. LifecycleConfig — Birth, maturation, death, population limits
# =============================================================================

@dataclass
class LifecycleConfig:
    """Population-level lifecycle management."""

    initial_population: int = 1
    """[task_policy] Number of founder polyps at reef initialisation."""

    max_population_from_memory: bool = True
    """[ENGINEERING] If ``True``, derive ``max_population`` from measured free
    SDRAM on the SpiNNaker chip at runtime.  If ``False``, use
    ``max_population_hard``.
    """

    max_population_hard: int = 256
    """[ENGINEERING] Fallback hard cap on total polyps when auto-detection
    is disabled or fails.  Must stay below ``max_atoms_per_core`` (255) for
    a single-chip demo; scale linearly with board size.
    """

    memory_bytes_per_polyp: int = 256
    """[ENGINEERING] Estimated SRAM footprint per polyp (weights, state,
    message buffers).  Used only when ``max_population_from_memory=True``.
    """

    maturity_age_estimate_steps: int = 50
    """[measurement_protocol] Steps before a newborn polyp is considered
    mature enough to contribute to MI estimates and reproduction.

    *Not* the fixed 500-step juvenile period used in earlier versions; the
    estimator now auto-detects convergence (warmup_min_samples).  50 is a
    conservative floor.
    """

    reproduction_cooldown_steps: int = 10
    """[ENGINEERING] Minimum inter-division interval (refractory period).
    Prevents population explosion from a single high-trophic parent."""

    max_children_per_step: int = 2
    """[ENGINEERING] Maximum offspring a single polyp can produce in one
    step (binary-fission limit)."""

    pruning_batch_size: int = 5
    """[ENGINEERING] Number of lowest-trophic polyps removed per pruning
    event.  Batched removal reduces graph-reconstruction overhead."""

    enable_apoptosis: bool = True
    """[runtime_ui] Master switch for BAX-driven programmed death."""

    enable_reproduction: bool = True
    """[runtime_ui] Master switch for cyclin-D-driven reproduction."""

    enable_structural_plasticity: bool = True
    """[runtime_ui] Master switch for axon/dendrite sprouting and synapse
    formation (competitive STDP + activity-dependent growth)."""


# =============================================================================
# 3. LearningConfig — Plasticity, evaluation, dopamine
# =============================================================================

@dataclass
class LearningConfig:
    """All parameters governing synaptic plasticity, reward evaluation, and
    the winner-take-all competitive attention mechanism."""

    # --- Sensory seed calibration --------------------------------------------

    seed_output_scale: float = 0.1
    """[ENGINEERING] Initial gain of sensory claimants (photoreceptor-like
    adaptation).  Scales raw input MI into a firing-rate-compatible range
    before drive computation.  Calibrated so that MI ~ 1 bit produces
    firing_rate ~ 0.1 with default ``_uptake_rate``.
    """

    output_scale_adaptation_alpha: float = 0.01
    """[ENGINEERING] EMA learning rate for per-stream ``seed_output_scale``
    adaptation.  Slower than the dopamine EMA so that sensory gain tracks
    long-term statistics, not single-step fluctuations.
    """

    # --- Evaluation horizon --------------------------------------------------

    evaluation_horizon_bars: int = 5
    """[task_policy] Number of time-bars (bars, not steps) used for the
    directional-accuracy signal.

    A 5-bar horizon captures medium-term directional trends (e.g. 5-minute
    bars in financial tasks) without overfitting to tick-level noise.
    """

    directional_accuracy_ema_alpha: float = 0.02
    """[ENGINEERING] EMA coefficient for online directional-accuracy tracking.

    alpha = 0.02 gives an effective memory of ~50 bars (1/alpha), matching
    the ``evaluation_horizon_bars`` at the bar timescale.
    """

    # --- STDP parameters -----------------------------------------------------

    stdp_a_plus: float = 0.01
    """[biology_derived] Long-term potentiation (LTP) magnitude for spike-
    timing-dependent plasticity.

    Pre-before-post timing within ``stdp_tau_plus`` ms potentiates the
    synapse by this amount.  Calibrated to biologically observed STDP curves
    in rat hippocampal CA1 (Bi & Poo 1998).
    """

    stdp_a_minus: float = 0.01
    """[biology_derived] Long-term depression (LTD) magnitude.

    Post-before-pre timing within ``stdp_tau_minus`` ms depresses the
    synapse.  Asymmetric curves (a_plus > a_minus) can be set by the user
    for tasks favouring potentiation-dominant learning.
    """

    stdp_tau_plus: float = 20.0
    """[biology_derived] LTP time constant in milliseconds (pre → post
    causality window).  20 ms matches the NMDA-receptor unbinding time
    constant in neocortical synapses (Froemke et al. 2005).
    """

    stdp_tau_minus: float = 20.0
    """[biology_derived] LTD time constant in milliseconds (post → pre
    anti-causality window)."""

    stdp_mu: float = 0.0
    """[ENGINEERING] STDP weight-update offset for multiplicative
    normalisation.  Keeps weights positive when combined with clipping."""

    stdp_weight_min: float = 0.0
    """[numerical] Hard lower bound on synaptic weight (no negative weights)."""

    stdp_weight_max: float = 1.0
    """[numerical] Hard upper bound on synaptic weight."""

    reinforcement_lr: float = 0.002
    """[ENGINEERING] Learning rate for the polyp-level reinforcement fallback.

    When per-neuron spike times are unavailable, inter-polyp edges are
    updated with a simple reward-modulated Hebbian rule:
    ``dw = lr * reward * dopamine_modulation``.  Small values (0.001–0.005)
    prevent oscillation while still allowing the colony to adapt."""

    readout_learning_rate: float = 0.10
    """[ENGINEERING] Reward-gated learning rate for the polyp-local predictive
    readout head.

    This is a local, one-scalar-per-polyp adaptation used when the substrate
    must learn that a sensory cue predicts a later or transformed outcome.
    It reinforces successful signed actions and anti-reinforces failed ones;
    it does not use backpropagation or gradients through the network.
    """

    delayed_readout_learning_rate: float = 0.05
    """[ENGINEERING] Learning rate for matured delayed-credit readout updates.

    Kept below the immediate readout rate because one matured horizon carries
    a multi-step aggregate consequence rather than a single-step outcome.
    """

    min_delayed_readout_horizon_bars: int = 2
    """[ENGINEERING] Minimum evaluation horizon required before matured
    horizon records can update the predictive readout.

    Horizon-1 tasks are immediate-consequence tasks; applying "future bar"
    credit there can punish correct current predictions on alternating
    sequences.  Delayed readout plasticity is reserved for genuinely delayed
    credit-assignment tests.
    """

    macro_eligibility_enabled: bool = False
    """[runtime_ui] Enable host-side macro eligibility traces for delayed credit.

    When enabled, each polyp maintains a slowly decaying trace of recent local
    predictive features. Matured delayed consequences update the readout using
    the trace snapshot captured when the pending horizon was created instead of
    only the single-step feature. This is the software diagnostic bridge for
    Tier 5.9; native on-chip eligibility remains a later hardware/runtime
    target.
    """

    macro_eligibility_decay: float = 0.92
    """[ENGINEERING] Per-step decay for host-side macro eligibility traces.

    Values near 1 preserve credit over longer delays; values near 0 collapse
    back toward the current PendingHorizon behavior. The value is bounded at
    runtime to [0, 0.999999] for numerical stability.
    """

    macro_eligibility_learning_rate_scale: float = 1.0
    """[ENGINEERING] Multiplier on delayed readout LR for macro trace updates."""

    macro_eligibility_trace_mode: str = "normal"
    """[runtime_ui] Tier 5.9 trace mode: ``normal``, ``shuffled``, or ``zero``.

    ``shuffled`` deterministically assigns another polyp's trace snapshot to
    the horizon and ``zero`` removes the trace. These are ablation controls,
    not candidate production settings.
    """

    macro_eligibility_credit_mode: str = "replace"
    """[runtime_ui] How macro eligibility enters matured delayed credit.

    ``replace`` is the original Tier 5.9a diagnostic behavior: the trace
    snapshot replaces the single-step PendingHorizon feature. ``residual`` is
    the safer Tier 5.9b repair mode: the v1.4 PendingHorizon feature remains
    the base update and the bounded trace contributes only a residual term.
    """

    macro_eligibility_residual_scale: float = 0.10
    """[ENGINEERING] Scale for residual macro trace credit in Tier 5.9b."""

    macro_eligibility_trace_clip: float = 1.0
    """[ENGINEERING] Absolute clip/normalizer for macro trace residuals.

    In residual mode the trace contribution is squashed to [-1, 1] with a
    smooth tanh using this value, preventing long accumulated traces from
    overwhelming the proven PendingHorizon signal.
    """

    context_memory_enabled: bool = False
    """[runtime_ui] Enable the bounded host-side internal context-memory
    pathway.

    This is the Tier 5.10d bridge from external diagnostic scaffolding toward
    an internal CRA working-memory mechanism. It stores only visible context
    cue sign, binds it to later visible decision cues, and exports telemetry
    for reset/shuffled/wrong-memory ablations. Native on-chip memory remains a
    later runtime target.
    """

    context_memory_mode: str = "normal"
    """[runtime_ui] Internal context-memory mode.

    Supported values are ``normal``, ``reset``, ``shuffled``, ``wrong``,
    ``keyed``, ``slot_reset``, ``slot_shuffle``, and ``wrong_key``. The
    non-normal modes are diagnostic controls used by Tier 5.10d-g, not promoted
    production settings.
    """

    context_memory_event_key: str = "event_type"
    """[ENGINEERING] Metadata key containing the visible task event type."""

    context_memory_context_event: str = "context"
    """[ENGINEERING] Event value that authorizes updating context memory."""

    context_memory_decision_event: str = "decision"
    """[ENGINEERING] Event value that authorizes binding memory to a cue."""

    context_memory_input_gain: float = 1.0
    """[ENGINEERING] Gain applied to internally bound context-memory input."""

    context_memory_key_metadata: str = "context_memory_key"
    """[ENGINEERING] Metadata key used by keyed/multi-slot context memory.

    Tier 5.10g uses this visible routing key to bind contexts and later
    decisions without reading labels or future outcomes.
    """

    context_memory_default_key: str = "default"
    """[ENGINEERING] Fallback key for keyed context memory when no key exists."""

    context_memory_slot_count: int = 1
    """[ENGINEERING] Maximum keyed context-memory slots retained on the host.

    ``1`` preserves the original single-slot behavior. Tier 5.10g raises this
    for bounded multi-slot diagnostics and lowers it for overcapacity controls.
    """

    context_memory_overwrite_policy: str = "lru"
    """[ENGINEERING] Slot eviction policy for keyed context memory.

    Currently ``lru`` is implemented. The explicit field is kept so future
    policies can be tested without changing the evidence schema.
    """

    predictive_context_enabled: bool = False
    """[runtime_ui] Enable the host-side predictive-context pathway.

    This is the Tier 5.12 bridge from reactive reward learning toward
    anticipatory state modeling. It stores only causal precursor signs exposed
    by task metadata before feedback arrives, then injects the retained
    predictive state at later decision steps. It is not a full world model and
    not native on-chip prediction.
    """

    predictive_context_mode: str = "keyed"
    """[runtime_ui] Predictive-context mode.

    Supported values are ``keyed``, ``normal``, ``wrong``, ``shuffled``, and
    ``no_write``. The non-keyed modes are Tier 5.12 ablation controls.
    """

    predictive_context_update_metadata: str = "predictive_context_update"
    """[ENGINEERING] Metadata flag that authorizes a predictive-context write."""

    predictive_context_decision_metadata: str = "predictive_context_decision"
    """[ENGINEERING] Metadata flag that marks a decision/evaluation point."""

    predictive_context_signal_metadata: str = "predictive_context_sign"
    """[ENGINEERING] Metadata key containing the causal precursor sign to store."""

    predictive_context_key_metadata: str = "predictive_context_key"
    """[ENGINEERING] Metadata key used to bind predictive state to a context."""

    predictive_context_default_key: str = "default"
    """[ENGINEERING] Fallback predictive-context key."""

    predictive_context_input_gain: float = 1.0
    """[ENGINEERING] Gain applied when predictive context is injected."""

    predictive_context_slot_count: int = 8
    """[ENGINEERING] Maximum host-side predictive-context slots retained."""

    composition_routing_enabled: bool = False
    """[runtime_ui] Enable the bounded host-side composition/routing pathway.

    This is the Tier 5.13c bridge from external composition/router scaffolds
    toward an internal CRA mechanism. It learns primitive module tables and
    context-to-module scores only from visible task metadata and feedback that
    has already arrived, then injects a routed/composed decision feature before
    the current feedback is applied. Native on-chip routing remains a later
    runtime target.
    """

    composition_routing_mode: str = "normal"
    """[runtime_ui] Internal composition/routing mode.

    Supported values are ``normal``, ``reset``, ``shuffle``,
    ``order_shuffle``, ``router_reset``, ``context_shuffle``,
    ``random_router``, ``always_on``, and ``no_write``. Non-normal modes are
    Tier 5.13c sham controls and are not promoted production settings.
    """

    composition_routing_event_key: str = "event_type"
    """[ENGINEERING] Metadata key containing the visible composition/routing event."""

    composition_routing_phase_metadata: str = "phase"
    """[ENGINEERING] Metadata key containing the visible task phase."""

    composition_routing_skill_a_event: str = "skill_a"
    """[ENGINEERING] Event value for the first skill cue in composition tasks."""

    composition_routing_skill_b_event: str = "skill_b"
    """[ENGINEERING] Event value for the second skill cue in composition tasks."""

    composition_routing_skill_event: str = "skill"
    """[ENGINEERING] Event value for a primitive single-module skill cue."""

    composition_routing_context_event: str = "route_context"
    """[ENGINEERING] Event value that updates the current routing context."""

    composition_routing_input_event: str = "input"
    """[ENGINEERING] Event value that updates the current decision input sign."""

    composition_routing_decision_event: str = "decision"
    """[ENGINEERING] Event value where routed/composed features may be injected."""

    composition_routing_skill_a_metadata: str = "composition_skill_a"
    """[ENGINEERING] Metadata key for the visible first skill name."""

    composition_routing_skill_b_metadata: str = "composition_skill_b"
    """[ENGINEERING] Metadata key for the visible second skill name."""

    composition_routing_skill_metadata: str = "composition_skill"
    """[ENGINEERING] Metadata key for a visible primitive skill name."""

    composition_routing_context_metadata: str = "routing_context"
    """[ENGINEERING] Metadata key for the visible routing context name."""

    composition_routing_true_skill_metadata: str = "routing_true_skill"
    """[ENGINEERING] Metadata key for the visible training skill used in routing diagnostics.

    This is used only for telemetry and primitive skill cue persistence; route
    scores are inferred from module predictions versus arrived feedback.
    """

    composition_routing_input_sign_metadata: str = "composition_input_sign"
    """[ENGINEERING] Metadata key containing the visible signed decision input."""

    composition_routing_input_gain: float = 1.0
    """[ENGINEERING] Gain applied when the internal routed/composed feature is injected."""

    composition_routing_prediction_mix: float = 0.0
    """[ENGINEERING] Blend routed/composed feature into polyp readouts.

    ``0`` keeps the mechanism as an input-only bridge. Tier 5.13c can raise
    this to test a bounded host-side module-gating head while keeping the
    feature disabled by default for existing baselines.
    """

    composition_routing_prediction_gain: float = 1.0
    """[ENGINEERING] Gain applied before squashing the routed/composed readout feature."""

    enable_readout_plasticity: bool = True
    """[runtime_ui] Master switch for the polyp-local predictive readout
    learner.

    Tier-3 ablation tests use this to freeze the local action/cue association
    while leaving inference, dopamine computation, and lifecycle dynamics
    intact.
    """

    readout_requires_dopamine: bool = True
    """[ENGINEERING] Require a non-zero dopamine teaching signal before the
    predictive readout can update.

    This keeps the local readout path aligned with the architecture invariant:
    plastic changes are gated by consequence-derived neuromodulation rather
    than direct supervised correction.
    """

    readout_weight_decay: float = 0.001
    """[ENGINEERING] Per-step shrinkage for predictive readout weights.

    Prevents shuffled-label controls from accumulating an unbounded random
    walk while leaving consistent cue/outcome relationships learnable.
    """

    readout_negative_surprise_multiplier: float = 3.0
    """[ENGINEERING] Extra anti-reinforcement on incorrect readout actions.

    Negative reward-prediction events should drive faster plasticity than
    routine successful predictions, especially after a nonstationary rule
    switch.  The multiplier is applied only when the local signed action is
    punished.
    """

    readout_weight_clip: float = 20.0
    """[numerical] Absolute bound for polyp-local predictive readout weights."""

    # --- Dopamine modulation -------------------------------------------------

    dopamine_tau: float = 100.0
    """[biology_derived] Time constant (ms) for the dopamine exponential
    moving average.

    100 ms corresponds to the phasic dopamine burst duration observed in
    VTA recordings during reward prediction (Schultz 1998).
    """

    dopamine_baseline: float = 0.0
    """[biology_derived] Baseline dopamine level (tonic firing).

    Set to 0.0 in the simplified model; positive prediction-error transients
    are the teaching signal.
    """

    dopamine_reward_scale: float = 1.0
    """[task_policy] Scaling factor converting raw task reward signal into
    dopamine concentration compatible with the drive equation."""

    dopamine_scale: float = 1.0
    """[ENGINEERING] Modulation strength for Fremaux 2010 dopamine-STDP.
    Synonymous with ``dopamine_reward_scale`` in some code paths;
    retained for backward compatibility while paths converge."""

    dopamine_gain: float = 10000.0
    """[ENGINEERING] Scaling factor to bring tiny RPE into STDP-sensitive
    range.  Applied before the weight-update nonlinearity."""

    # --- Winner-take-all competition -----------------------------------------

    winner_take_all_base: int = 3
    """[biology_derived] Minimum number of winners in the k-WTA competition
    (Desimone & Duncan 1995).

    Only the top-k polyps by ``drive`` fire and are eligible for trophic
    support in a given step.  Implements competitive attention and sparse
    coding.
    """

    wta_kappa: float = 2.0
    """[ENGINEERING] Sharpness exponent for the soft-WTA mask.

    ``drive^kappa`` is used in the softmax; higher values push the
    distribution toward true hard WTA.
    """

    # --- Homeostasis (Turrigiano & Nelson 2004) ------------------------------

    homeostasis_target_rate_hz: float = 10.0
    """[biology_derived] Target firing rate for Oja-style homeostatic
    normalization.  10 Hz is typical for neocortical pyramidal neurons
    in vivo."""

    homeostasis_strength: float = 0.001
    """[ENGINEERING] Gain of the homeostatic normalization term.
    Small values prevent oscillation while allowing slow drift to target."""

    # --- Plasticity gating (BOCPD) -------------------------------------------

    plasticity_bocpd_weight: float = 2.0
    """[ENGINEERING] Changepoint-probability to plasticity-temperature coupling.
    ``T_plasticity = 1.0 + bocpd_weight * P_changepoint``."""

    calcification_rate: float = 0.001
    """[ENGINEERING] Speed of synaptic consolidation (eligibility trace →
    stable weight).  Lower = slower memory formation."""

    synaptic_tag_threshold: float = 0.5
    """[ENGINEERING] Eligibility-trace magnitude required before consolidation
    can begin.  Prevents noise from being memorised."""

    max_pending_horizons: int = 100
    """[ENGINEERING] Maximum delayed-credit records in the pending ledger.
    Memory bound for matured-consequence tracking."""

    # --- Competitive / structural plasticity --------------------------------

    competitive_alpha_default: float = 0.1
    """[biology_inherited] Learning rate for the polyp-local competitive
    strength (heritable).  Governs how quickly a polyp adapts its synaptic
    identity in response to trophic success / failure.
    """

    sprouting_rate_default: float = 0.05
    """[biology_inherited] Per-step probability of attempting a new outgoing
    synapse (axon sprouting).  Heritable trait bounded to [0, 1].
    """

    max_connectivity_factor_default: int = 5
    """[biology_inherited] Maximum out-degree multiplier:
    ``max_out_degree = max_connectivity_factor * sqrt(N)``.

    Heritable trait controlling axonal arborisation density.  Biological
    pyramidal neurons typically have 10³–10⁴ synapses; the factor is
    scaled down for the SpiNNaker resource budget.
    """

    construction_efficiency_default: float = 0.5
    """[biology_inherited] Fraction of attempted synapses that successfully
    form (heritable).  Models the stochasticity of growth-cone navigation
    and target recognition (Tessier-Lavigne & Goodman 1996).
    """

    ff_formation_bias_default: float = 0.7
    """[biology_inherited] Probability that a new synapse is feed-forward
    (heritable).  0.7 reflects the predominance of FF connections in
    cortical hierarchies (Felleman & Van Essen 1991).
    """

    fb_formation_bias_default: float = 0.3
    """[biology_inherited] Probability that a new synapse is feed-back
    (heritable).  Must satisfy ``ff + fb <= 1.0``; remainder is lateral."""

    synapse_pruning_threshold: float = 0.01
    """[ENGINEERING] Synaptic weight below which the edge is pruned
    (activity-dependent elimination, Low & Cheng 2006).
    """

    gap_junction_weight: float = 0.1
    """[biology_derived] Fixed coupling strength for electrical gap-junction
    edges (synchronisation, Connors & Long 2004).
    """

    # --- Polyp-local drive parameters (heritable) ----------------------------

    uptake_rate_default: float = 1.0
    """[biology_inherited] Gain from ``last_mi`` to ``drive`` (heritable).
    Higher values make a polyp more sensitive to its input MI.
    """

    da_gain_default: float = 0.5
    """[biology_inherited] Dopamine contribution to ``drive`` (heritable).
    Higher values prioritise reward-prediction signals over sensory
    information.
    """

    spatial_dispersion_default: float = 0.1
    """[biology_inherited] Std-dev of Gaussian kernel for spatial offspring
    placement (heritable).  Models the limited diffusion range of neuronal
    migration signals (Radic 1995).
    """

    tau_chemical_default: float = 50.0
    """[biology_inherited] Time constant (ms) for the chemical signalling
    EMA (heritable).  Governs how quickly a polyp tracks its local
    micro-environment.
    """

    # --- Heritable trait bounds ----------------------------------------------

    heritable_log_sigma: float = 0.2
    """[ENGINEERING] Log-normal std-dev for all bounded inheritance draws.
    sigma = 0.2 gives ~20 % coefficient of variation, keeping most draws
    within 0.5×–2× the parent value.
    """

    heritable_hard_bounds: Tuple[float, float] = (0.01, 10.0)
    """[numerical] Global (min, max) clip for every heritable trait after
    log-normal perturbation.  Prevents pathological extremes."""


# =============================================================================
# 4. NetworkConfig — Layer sizes, topology, SpiNNaker graph constraints
# =============================================================================

@dataclass
class NetworkConfig:
    """Dimensions of the polyp state vectors and graph-connectivity limits."""

    hidden_size: int = 46
    """[ENGINEERING] Dimension of the polyp hidden state (message + WM).

    Runtime-sized: on a single SpiNNaker chip with 18 cores, 46 dims
    balances expressiveness against SDRAM bandwidth.  Increase on larger
    boards (SpiNN-5:  up to ~256 dims).
    """

    message_size: int = 46
    """[ENGINEERING] Dimension of the outgoing message vector broadcast to
    children.  Equals ``hidden_size`` by default (shared representation)."""

    wm_size: int = 46
    """[ENGINEERING] Working-memory buffer dimension.  Holds the temporal
    context (past MI estimates) fed back into the hidden state."""

    chemistry_size: int = 46
    """[ENGINEERING] Dimension of the chemical signalling state (local
    micro-environment EMA).  Models diffusible factors (BDNF, NO, etc.)."""

    tf_size: int = 46
    """[ENGINEERING] Transcription-factor identity vector dimension.

    Used to initialise the orthonormal basis that gives each polyp a
    unique developmental identity (O'Leary & Nakagawa 2002).
    """

    num_tf_basis_vectors: int = 8
    """[ENGINEERING] Number of orthonormal basis vectors maintained in the
    TF state.  Limits polyp-type diversity to avoid over-fragmentation."""

    max_connectivity_factor_default: int = 5
    """[biology_inherited] See ``LearningConfig.max_connectivity_factor_default``."""

    gap_junction_weight: float = 0.1
    """[biology_derived] See ``LearningConfig.gap_junction_weight``."""

    # --- Input / output dimensions (task-dependent) --------------------------

    num_sensory_streams: int = 4
    """[task_policy] Number of exteroceptive input streams (e.g. price,
    volume, sentiment, technical indicator).  Must match the task
    preprocessor output.
    """

    num_outcome_channels: int = 1
    """[task_policy] Number of task-consequence signals (typically 1 for
    directional accuracy / PnL).
    """

    # --- Graph topology limits -----------------------------------------------

    max_in_degree: int = 16
    """[ENGINEERING] Maximum incoming synapses per polyp.  Prevents
    SpiNNaker SDRAM overflow for message buffers."""

    max_out_degree_factor: float = 5.0
    """[ENGINEERING] ``max_out_degree = max_out_degree_factor * sqrt(N)``.
    Scales with population so that sparse connectivity is maintained."""

    allow_recurrent: bool = False
    """[ENGINEERING] If ``False``, enforce DAG (no cycles).  Simplifies
    trophic back-propagation and prevents runaway feedback.  Set ``True``
    only for tasks requiring working-memory loops."""

    allow_self_connections: bool = False
    """[ENGINEERING] If ``False``, prohibit autapses."""

    # --- Message passing -----------------------------------------------------

    message_passing_steps: int = 1
    """[ENGINEERING] Number of synchronous message-passing iterations per
    CRA step.  1 = single feed-forward sweep; increase for deeper
    recurrent processing (costs SpiNNaker time steps).
    """

    message_context_gain: float = 0.015
    """[ENGINEERING] Gain applied to graph-mediated spike messages before
    they are blended into each polyp's signed readout contribution.

    This makes the existing reef graph computationally causal in host-side
    controlled tests while keeping the graph signal bounded.
    """

    message_prediction_mix: float = 0.25
    """[ENGINEERING] Blend factor for graph context in the signed readout.

    0 disables graph influence; 1 replaces the local prediction with the
    graph-mediated context.  Intermediate values test motif contribution
    without letting message passing swamp local sensory learning.
    """

    # --- PyNN / SpiNNaker neuron model parameters ----------------------------

    neuron_model: str = "IF_curr_exp"
    """[ENGINEERING] PyNN neuron model class.  ``IF_curr_exp`` is the
    standard leaky integrate-and-fire with exponential synaptic currents,
    well-supported on SpiNNaker.
    """

    v_rest: float = -65.0
    """[biology_derived] Resting membrane potential in mV."""

    v_reset: float = -70.0
    """[biology_derived] Post-spike reset potential in mV."""

    v_thresh: float = -55.0
    """[biology_derived] Firing threshold in mV."""

    tau_m: float = 20.0
    """[biology_derived] Membrane time constant in ms.  20 ms is typical
    for neocortical pyramidal neurons (McCormick et al. 1985).
    """

    tau_refrac: float = 2.0
    """[biology_derived] Absolute refractory period in ms."""

    tau_syn_e: float = 5.0
    """[biology_derived] Excitatory synaptic time constant in ms."""

    tau_syn_i: float = 5.0
    """[biology_derived] Inhibitory synaptic time constant in ms."""

    cm: float = 0.25
    """[biology_derived] Membrane capacitance in nF.  0.25 nF for a
    compact point-neuron model on SpiNNaker."""


# =============================================================================
# 5. SpiNNakerConfig — Hardware-specific settings
# =============================================================================

@dataclass
class SpiNNakerConfig:
    """Parameters specific to the SpiNNaker neuromorphic hardware platform.

    References
    ----------
    - Furber et al. (2014)  The SpiNNaker Project.  *Proceedings IEEE*
      102:652-665.
    """

    timestep_ms: float = 1.0
    """[ENGINEERING] Simulation time step in milliseconds.  Must be >= 1.0
    on SpiNNaker; smaller values increase temporal resolution at the cost
    of real-time factor.
    """

    runtime_ms_per_step: int = 100
    """[ENGINEERING] Wall-clock milliseconds simulated per CRA macro-step.

    Each CRA step (MI estimation, trophic update, WTA, plasticity) is
    executed after ``runtime_ms_per_step`` of neural simulation.  100 ms
    gives 10 CRA steps per simulated second.
    """

    max_atoms_per_core: int = 255
    """[ENGINEERING] SpiNNaker hardware limit: maximum neurons per ARM core.

    The chip has 18 cores; one is reserved for system use, leaving 17
    application cores.  Max ~4,335 neurons per chip with 1:1 mapping.
    """

    num_chips: int = 1
    """[ENGINEERING] Number of SpiNNaker chips in the allocation.  Increase
    to 48 for a full SpiNN-5 board (48 chips × 17 cores × 255 neurons).
    """

    machine_time_step: Optional[int] = None
    """[runtime_ui] Overrides ``timestep_ms`` when set (microseconds)."""

    min_delay: float = 1.0
    """[ENGINEERING] Minimum synaptic delay in ms (SpiNNaker constraint)."""

    sync_interval_steps: int = 1
    """[ENGINEERING] Rebuild hardware projections every N steps.

    1 = every step (required for live hardware with dynamic topology).
    0 = never (fastest for software simulation; host-side graph only).
    10 = every 10 steps (balanced for slow software backends like NEST).
    """

    runtime_mode: str = "step"
    """[runtime_ui] Hardware execution contract: ``step``, ``chunked``, or
    ``continuous``.

    ``step`` is the current proven host-loop path. ``chunked`` is the Tier 4.17
    bridge target. ``continuous`` is reserved for a future custom closed-loop
    runtime and must not be cited as implemented until a dedicated evidence
    bundle passes.
    """

    learning_location: str = "host"
    """[runtime_ui] Where learning/credit assignment executes: ``host``,
    ``hybrid``, or ``on_chip``.

    The current implementation is host-side learning. ``hybrid`` and
    ``on_chip`` are future targets for custom runtime work.
    """

    chunk_size_steps: int = 1
    """[ENGINEERING] Number of CRA macro-steps per backend ``sim.run`` call
    when ``runtime_mode == 'chunked'``.

    Values greater than one are a runtime-refactor setting, not a hardware
    evidence claim by themselves. Scientifically valid chunking also requires
    scheduled input delivery and per-step binned spike readback.
    """

    # ------------------------------------------------------------------
    # Microcircuit subgroup sizes (must sum to n_neurons_per_polyp)
    # ------------------------------------------------------------------

    n_neurons_per_polyp: int = 32
    """[BIOLOGY] Total LIF neurons per polyp microcircuit.

    Each polyp is a 32-neuron recurrent microcircuit:
    8 input + 16 excitatory + 4 inhibitory + 4 readout = 32.
    """

    n_input_per_polyp: int = 8
    """[BIOLOGY] Input neurons per polyp. Receive sensory and inter-polyp input."""

    n_exc_per_polyp: int = 16
    """[BIOLOGY] Excitatory recurrent neurons per polyp."""

    n_inh_per_polyp: int = 4
    """[BIOLOGY] Inhibitory neurons per polyp. Global normalization within polyp."""

    n_readout_per_polyp: int = 4
    """[BIOLOGY] Readout neurons per polyp. Project to other polyps and colony readout."""

    # ------------------------------------------------------------------
    # Internal connectivity template parameters
    # ------------------------------------------------------------------

    internal_conn_seed: int = 42
    """[ENGINEERING] Random seed for internal wiring template instantiation."""

    input_to_exc_weight: float = 0.15
    """[ENGINEERING] Fixed weight for input → excitatory connections."""

    input_to_inh_weight: float = 0.10
    """[ENGINEERING] Fixed weight for input → inhibitory connections."""

    exc_to_exc_mean: float = 0.1
    """[ENGINEERING] Mean of log-normal distribution for E→E weights."""

    exc_to_exc_sigma: float = 0.5
    """[ENGINEERING] Sigma of log-normal distribution for E→E weights."""

    exc_to_inh_weight: float = 0.20
    """[ENGINEERING] Fixed weight for excitatory → inhibitory connections."""

    inh_to_exc_weight: float = -0.40
    """[ENGINEERING] Fixed weight for inhibitory → excitatory connections."""

    exc_to_readout_weight: float = 0.10
    """[ENGINEERING] Fixed weight for excitatory → readout connections."""

    input_to_exc_fanout: int = 4
    """[ENGINEERING] Number of excitatory targets per input neuron."""

    input_to_inh_fanout: int = 2
    """[ENGINEERING] Number of inhibitory targets per input neuron."""

    exc_to_exc_fanout: int = 4
    """[ENGINEERING] Number of excitatory targets per excitatory neuron."""

    exc_to_inh_fanout: int = 2
    """[ENGINEERING] Number of inhibitory targets per excitatory neuron."""

    exc_to_readout_fanout: int = 2
    """[ENGINEERING] Number of readout targets per excitatory neuron."""

    max_delay: float = 144.0
    """[ENGINEERING] Maximum synaptic delay in ms (SpiNNaker DTCM limit)."""

    default_delay: float = 1.0
    """[ENGINEERING] Default axonal delay for newly formed synapses."""

    spike_buffer_size: int = 256
    """[ENGINEERING] Ring-buffer slots for incoming spikes per synapse type.
    Must be power of 2 for SpiNNaker DMA efficiency."""

    sdram_per_core_bytes: int = 118 * 1024
    """[ENGINEERING] Usable SDRAM per core (~118 KiB after system overhead)."""

    # --- Host communication --------------------------------------------------

    live_mode: bool = False
    """[runtime_ui] Enable live spike injection / retrieval via Ethernet.
    Required for closed-loop host-side MI estimation feeding back into
    the reef."""

    database_buffer_size: int = 1024
    """[ENGINEERING] Buffer size for the SpiNNaker database interface."""

    # --- Checkpointing -------------------------------------------------------

    checkpoint_interval_steps: int = 1000
    """[ENGINEERING] Save full reef state every N CRA steps for fault
    tolerance and long-run resumability.  Serialised via pickle to the
    host filesystem."""

    checkpoint_dir: str = "./checkpoints"
    """[runtime_ui] Host directory for checkpoint files."""

    # --- Profiling -----------------------------------------------------------

    profile_execution: bool = False
    """[runtime_ui] Enable SpiNNaker-level profiling (energy, time)."""

    profile_data_dir: str = "./profiles"
    """[runtime_ui] Host directory for profiler output."""


# =============================================================================
# 6. MeasurementConfig — MI estimation and BOCPD parameters
# =============================================================================

@dataclass
class MeasurementConfig:
    """Parameters for the mutual-information estimation layer and the
    Bayesian Online Changepoint Detector (BOCPD)."""

    # --- KSG estimator -------------------------------------------------------

    ksg_k: int = 4
    """[measurement_protocol] Number of nearest neighbours for the KSG MI
    estimator (Kraskov et al. 2004).  k = 4 is the standard choice for
    low-to-moderate sample sizes.
    """

    ksg_max_reliable_dim: int = 8
    """[measurement_protocol] Dimensionality above which KSG is deprecated
    in favour of Gaussian-copula MI (GCMI).  Joint spaces with > 8 dims
    require exponentially more samples for reliable density estimation.
    """

    ksg_min_samples: int = 30
    """[measurement_protocol] Absolute floor on sample count before any
    KSG estimate is attempted.  Below this, return NaN with
    ``insufficient_history`` source tag.
    """

    # --- Gaussian-copula MI --------------------------------------------------

    gcmi_rank_method: str = "average"
    """[measurement_protocol] Ties handling for rank-Gaussianization.
    ``average`` is standard; ``random`` breaks ties deterministically."""

    gcmi_epsilon: float = 1e-6
    """[numerical] Epsilon added to covariance diagonal before Cholesky
    decomposition to ensure positive definiteness."""

    # --- BOCPD ---------------------------------------------------------------

    bocpd_hazard_rate: float = 1e-3
    """[measurement_protocol] Prior hazard rate (constant) for BOCPD.

    Expected changepoints per step.  1e-3 corresponds to ~1 changepoint
    per 1000 steps on average (Adams & MacKay 2007).
    """

    bocpd_mu0: float = 0.0
    """[measurement_protocol] Prior mean for the BOCPD Gaussian likelihood."""

    bocpd_kappa0: float = 1.0
    """[measurement_protocol] Prior pseudo-observations for the mean
    (higher = more confident prior)."""

    bocpd_alpha0: float = 1.0
    """[measurement_protocol] Prior shape for the BOCPD inverse-Gamma
    variance (higher = tighter prior)."""

    bocpd_beta0: float = 1.0
    """[measurement_protocol] Prior scale for the BOCPD inverse-Gamma
    variance."""

    bocpd_tail_mass_threshold: float = 1e-4
    """[measurement_protocol] Adaptive tail-mass truncation threshold.

    When the total probability mass of run lengths > ``max_run_length``
    falls below this threshold, the posterior is truncated and normalised.
    Prevents unbounded memory growth on SpiNNaker.
    """

    bocpd_max_run_length: int = 1000
    """[ENGINEERING] Hard cap on run-length history.

    Once exceeded, tail truncation is forced regardless of mass.  1000
    steps ≈ 100 seconds at runtime_ms_per_step = 100 ms.
    """

    # --- Joint MI history ---------------------------------------------------

    joint_mi_window: int = 500
    """[measurement_protocol] Rolling window size for joint mutual-information
    history.  Used by the Organism to maintain a bounded deque of recent
    colony-wide information estimates.
    """

    # --- Aliases for organism.py compatibility ------------------------------

    spike_buffer_size: int = 256
    """Buffer size for spike history deque."""

    stream_buffer_len: int = 100
    """Buffer length per stream."""

    mi_method: str = "ksg"
    """Mutual information estimation method."""

    bocpd_hazard: float = 1e-3
    """Alias for bocpd_hazard_rate."""

    bocpd_prior_alpha: float = 1.0
    """Alias for bocpd_alpha0."""

    bocpd_prior_beta: float = 1.0
    """Alias for bocpd_beta0."""

    # --- Warmup / sample complexity ------------------------------------------

    warmup_samples_per_dim: int = 10
    """[measurement_protocol] Multiplier for minimum samples:
    ``min_samples = warmup_samples_per_dim * d_eff * tau``.

    10× is the empirical rule-of-thumb for reliable KSG estimation
    (Kraskov et al. 2004 supplement).
    """

    max_autocorrelation_lag: int = 20
    """[measurement_protocol] Maximum lag for autocorrelation-time estimation
    when computing ``tau`` for the warmup formula."""

    # --- Stream history ------------------------------------------------------

    stream_history_maxlen: int = 2000
    """[ENGINEERING] Maximum length of per-stream circular buffers holding
    past observations for MI estimation.  2000 samples ≈ 200 seconds of
    history at 10 Hz (CRA step every 100 ms).  Increase for tasks with
    long autocorrelation times.
    """

    joint_mi_min_samples_factor: int = 10
    """[measurement_protocol] For joint MI across all streams:
    ``required_samples = dimensions * joint_mi_min_samples_factor``.
    Below this, fall back to per-stream proxy estimates.
    """

    # --- Orthonormalisation --------------------------------------------------

    gs_epsilon: float = 1e-10
    """[numerical] Tolerance for linear-dependence detection during
    Gram-Schmidt orthonormalisation of the TF basis."""


# =============================================================================
# 7. ReefConfig — Root configuration container
# =============================================================================

@dataclass
class ReefConfig:
    """Root configuration for the Coral Reef Architecture on SpiNNaker.

    Aggregates all sub-configs and provides a factory method for creating
    a fully populated default configuration.  The default values are the
    v009bz CRA constants calibrated for a single-chip SpiNNaker demo.

    Usage::

        cfg = ReefConfig.default()
        print(cfg.learning.seed_output_scale)  # 0.1
        print(cfg.energy.bdnf_per_trophic_source)  # 0.024
    """

    energy: EnergyConfig = field(default_factory=EnergyConfig)
    """Trophic-economy parameters (BDNF, decay, apoptosis, reproduction)."""

    lifecycle: LifecycleConfig = field(default_factory=LifecycleConfig)
    """Population-level lifecycle management (birth, maturation, death)."""

    learning: LearningConfig = field(default_factory=LearningConfig)
    """Plasticity, evaluation horizon, dopamine, WTA competition."""

    network: NetworkConfig = field(default_factory=NetworkConfig)
    """Layer dimensions, connectivity limits, PyNN neuron parameters."""

    spinnaker: SpiNNakerConfig = field(default_factory=SpiNNakerConfig)
    """SpiNNaker hardware-specific settings."""

    measurement: MeasurementConfig = field(default_factory=MeasurementConfig)
    """MI estimation (KSG, GCMI) and BOCPD parameters."""

    # --- Runtime UI flags ----------------------------------------------------

    debug_verbosity: int = 0
    """[runtime_ui] 0 = silent, 1 = per-step summary, 2 = per-polyp trace."""

    log_interval_steps: int = 100
    """[runtime_ui] Steps between host-side log prints."""

    seed: int = 42
    """[runtime_ui] Global NumPy / PyNN random seed for reproducibility."""

    # -----------------------------------------------------------------------
    # Factory methods
    # -----------------------------------------------------------------------

    @classmethod
    def default(cls) -> "ReefConfig":
        """Return the v009bz default CRA configuration.

        All fields are initialised with the constants documented in the
        task specification (single-chip SpiNNaker, 4-stream input,
        46-dimensional hidden state).
        """
        return cls()

    @classmethod
    def from_dict(cls, d: dict) -> "ReefConfig":
        """Hydrate a ``ReefConfig`` from a nested dictionary.

        This supports JSON / YAML serialisation for experiment manifests::

            cfg = ReefConfig.from_dict(json.load(open("experiment.json")))
        """
        energy = EnergyConfig(**d.get("energy", {}))
        lifecycle = LifecycleConfig(**d.get("lifecycle", {}))
        learning = LearningConfig(**d.get("learning", {}))
        network = NetworkConfig(**d.get("network", {}))
        spinnaker = SpiNNakerConfig(**d.get("spinnaker", {}))
        measurement = MeasurementConfig(**d.get("measurement", {}))
        return cls(
            energy=energy,
            lifecycle=lifecycle,
            learning=learning,
            network=network,
            spinnaker=spinnaker,
            measurement=measurement,
            debug_verbosity=d.get("debug_verbosity", 0),
            log_interval_steps=d.get("log_interval_steps", 100),
            seed=d.get("seed", 42),
        )

    def to_dict(self) -> dict:
        """Serialise the configuration to a plain (JSON-safe) dictionary."""
        from dataclasses import asdict

        return asdict(self)

    @classmethod
    def from_json(cls, path: str | os.PathLike) -> "ReefConfig":
        """Hydrate a ``ReefConfig`` from a JSON file."""
        import json
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    @property
    def neuron_params(self) -> dict[str, float]:
        """Return PyNN-compatible LIF parameter dictionary."""
        return {
            "v_rest": self.network.v_rest,
            "v_reset": self.network.v_reset,
            "v_thresh": self.network.v_thresh,
            "tau_m": self.network.tau_m,
            "tau_refrac": self.network.tau_refrac,
            "cm": self.network.cm,
            "tau_syn_E": self.network.tau_syn_e,
            "tau_syn_I": self.network.tau_syn_i,
        }

    # -----------------------------------------------------------------------
    # Convenience accessors for frequently-used compound values
    # -----------------------------------------------------------------------

    @property
    def winner_take_all_k(self) -> int:
        """Compute ``k = max(3, int(sqrt(N)))`` for competitive attention.

        Desimone & Duncan (1995) competitive attention model.  ``N`` is
        the current hidden population size (``network.hidden_size`` for
        the static estimate).
        """
        n = self.network.hidden_size
        return max(self.learning.winner_take_all_base, int(math.sqrt(n)))

    @property
    def effective_decay(self) -> float:
        """Return the base effective decay rate for a unit-degree polyp.

        ``effective_decay = metabolic_decay + trophic_synapse_cost * 1``.
        For a polyp of arbitrary degree, multiply by degree.
        """
        return (
            self.energy.metabolic_decay_default
            + self.energy.trophic_synapse_cost_default
        )

    @property
    def max_population(self) -> int:
        """Return the runtime population cap.

        If ``lifecycle.max_population_from_memory`` is ``True``, attempt
        to derive from free SDRAM; otherwise return the hard cap.
        """
        if self.lifecycle.max_population_from_memory:
            try:
                free_sdram = self._estimate_free_sdram()
                memory_cap = max(
                    10,
                    free_sdram // self.lifecycle.memory_bytes_per_polyp,
                )
                return min(self.lifecycle.max_population_hard, memory_cap)
            except Exception:
                pass
        return self.lifecycle.max_population_hard

    def _estimate_free_sdram(self) -> int:
        """Estimate free SDRAM across all allocated SpiNNaker cores.

        Returns a conservative lower bound.  When SpiNNaker hardware is
        not available (e.g. simulation mode), falls back to a software
        estimate based on ``num_chips`` and ``sdram_per_core_bytes``.
        """
        cores = (self.spinnaker.num_chips * 17) - 1  # reserve 1 core/system
        return cores * self.spinnaker.sdram_per_core_bytes

    @property
    def heritable_trait_names(self) -> Tuple[str, ...]:
        """Return the canonical list of heritable polyp trait names.

        These are the fields whose values are drawn from a log-normal
        distribution at birth, with ``heritable_log_sigma`` perturbation.
        """
        return (
            "_metabolic_decay",
            "_trophic_synapse_cost",
            "_competitive_alpha",
            "_sprouting_rate",
            "_max_connectivity_factor",
            "_construction_efficiency",
            "_ff_formation_bias",
            "_fb_formation_bias",
            "_child_trophic_share",
            "_reproduction_threshold",
            "_death_threshold",
            "_bdnf_release_rate",
            "_bdnf_uptake_efficiency",
            "_uptake_rate",
            "_da_gain",
            "_spatial_dispersion",
            "_tau_chemical",
        )
