"""
Organism Orchestrator for Coral Reef Architecture on SpiNNaker.

Canonical host/hardware loop:
    1. sim.run(runtime_ms) -- SpiNNaker runs the SNN
    2. Read spikes, update host state
    3. Run learning / energy / lifecycle (host-side Python)
    4. Sync updated state back to SpiNNaker
    5. Repeat
"""

from __future__ import annotations

import logging
import math
import time
import traceback
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .config import ReefConfig
from .config_adapters import (
    energy_manager_config,
    learning_manager_config,
    graph_config,
    trading_config,
)
from .polyp_neuron import PolypNeuronType, PolypPopulation, PolypState
from .reef_network import ReefNetwork, ReefEdge
from .energy_manager import EnergyManager, EnergyResult
from .lifecycle import LifecycleManager, LifecycleEvent
from .learning_manager import LearningManager, LearningResult
from .trading_bridge import TradingBridge, TradingConfig, TaskOutcomeSurface
from .measurement import (
    BayesianOnlineChangepointDetector,
    compute_ksg_mi,
    compute_gcmi,
    warmup_min_samples,
)
from .signals import ConsequenceSignal, GenericTaskOutcomeSurface
from .step_metrics import StepMetrics, empty_metrics, assemble_step_metrics

logger = logging.getLogger(__name__)


class Organism:
    """Top-level CRA organism orchestrator for SpiNNaker."""

    def __init__(
        self,
        config: ReefConfig,
        sim,
        trading_bridge: Optional[TradingBridge] = None,
        use_default_trading_bridge: bool = True,
        setup_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.config: ReefConfig = config
        self.sim = sim

        self.polyp_population: Optional[PolypPopulation] = None
        self.network: Optional[ReefNetwork] = None
        self.energy_manager: Optional[EnergyManager] = None
        self.lifecycle_manager: Optional[LifecycleManager] = None
        self.learning_manager: Optional[LearningManager] = None
        self.trading_bridge: Optional[TradingBridge] = trading_bridge
        self.use_default_trading_bridge = bool(use_default_trading_bridge)
        self.bocpd: Optional[BayesianOnlineChangepointDetector] = None

        self.stream_keys: list[str] = []
        self.stream_buffers: dict[str, deque] = {}
        self.stream_mi: dict[str, float] = {}
        self.joint_mi_history: deque = deque(maxlen=500)

        self.step_counter: int = 0
        self.spike_buffer: deque = deque(maxlen=config.measurement.stream_history_maxlen)
        self.metrics_history: list[StepMetrics] = []
        self._accuracy_ema: float = 0.5
        self.founder_id: Optional[int] = None
        self._last_changepoint_probability: float = 0.0
        self._last_polyp_summaries: Dict[int, Any] = {}
        self._sim_run_failure_count: int = 0
        self._synthetic_fallback_count: int = 0
        self._summary_read_failure_count: int = 0
        self._last_sim_run_error: str = ""
        self._last_backend_failure_stage: str = ""
        self._last_backend_exception_type: str = ""
        self._last_backend_traceback: str = ""
        self._last_motif_activity: Dict[str, Any] = {}
        self._context_memory_value: int = 1
        self._context_memory_history: list[int] = []
        self._context_memory_slots: Dict[str, int] = {}
        self._context_memory_slot_order: list[str] = []
        self._context_memory_updates: int = 0
        self._last_context_memory_activity: Dict[str, Any] = {}
        self._predictive_context_value: int = 0
        self._predictive_context_slots: Dict[str, int] = {}
        self._predictive_context_slot_order: list[str] = []
        self._predictive_context_updates: int = 0
        self._last_predictive_context_activity: Dict[str, Any] = {}
        self._composition_module_table: Dict[str, Dict[int, int]] = {}
        self._composition_route_scores: Dict[str, Dict[str, float]] = {}
        self._composition_current_skill_a: str = ""
        self._composition_current_skill_b: str = ""
        self._composition_current_skill: str = ""
        self._composition_current_context: str = ""
        self._composition_current_input: int = 1
        self._composition_seen_skills: list[str] = []
        self._composition_seen_contexts: list[str] = []
        self._composition_module_updates: int = 0
        self._composition_router_updates: int = 0
        self._composition_module_uses: int = 0
        self._composition_router_uses: int = 0
        self._composition_correct_route_uses: int = 0
        self._composition_pre_feedback_select_steps: int = 0
        self._composition_rng = np.random.default_rng(int(getattr(config, "seed", 0) or 0) + 95137)
        self._last_composition_routing_activity: Dict[str, Any] = {}
        # Sync interval: rebuild hardware projections every N steps.
        # 1 = every step (hardware mode). 0 = never (fast software test).
        self._sync_interval: int = getattr(
            config.spinnaker, "sync_interval_steps", 1
        )

        # Keyword arguments passed to sim.setup(); stored so we can re-setup
        # after sim.end() during sPyNNaker full rebuilds.
        self._setup_kwargs: Dict[str, Any] = setup_kwargs or {}
        if "timestep" not in self._setup_kwargs:
            self._setup_kwargs["timestep"] = getattr(
                config.spinnaker, "timestep_ms", 1.0
            )

        # Rebuild bookkeeping (sPyNNaker only)
        self._last_rebuild_n_alive: int = 0
        self._last_rebuild_n_edges: int = 0

        backend_name = getattr(sim, "__name__", sim.__class__.__name__)
        logger.info("Organism created (backend=%s)", backend_name)

    @property
    def population_size(self) -> int:
        if self.polyp_population is None:
            return 0
        return len(self.polyp_population.states)

    @property
    def n_alive(self) -> int:
        if self.polyp_population is None:
            return 0
        return sum(1 for s in self.polyp_population.states if s.is_alive)

    @property
    def is_extinct(self) -> bool:
        return self.n_alive == 0

    @property
    def alive_polyp_ids(self) -> list[int]:
        if self.polyp_population is None:
            return []
        return [s.polyp_id for s in self.polyp_population.states if s.is_alive]

    @property
    def alive_polyp_indices(self) -> list[int]:
        if self.polyp_population is None:
            return []
        return [i for i, s in enumerate(self.polyp_population.states) if s.is_alive]

    def initialize(self, stream_keys: list[str]) -> None:
        """Initialise all subsystems."""
        self.stream_keys = list(stream_keys)
        n_streams = len(self.stream_keys)

        max_pop = int(self.config.lifecycle.max_population_hard)

        # 1. Population
        cfg_spin = self.config.spinnaker
        n_per_polyp = getattr(cfg_spin, "n_neurons_per_polyp", 32)
        n_input = getattr(cfg_spin, "n_input_per_polyp", 8)
        n_exc = getattr(cfg_spin, "n_exc_per_polyp", 16)
        n_inh = getattr(cfg_spin, "n_inh_per_polyp", 4)
        n_readout = getattr(cfg_spin, "n_readout_per_polyp", 4)
        # Initialise backend-agnostic factory (NEST vs sPyNNaker vs Brian2)
        from .backend_factory import get_backend_factory
        self._backend_factory = get_backend_factory(self.sim)

        # For sPyNNaker, configure pre-allocation so the factory builds the
        # full static connectivity matrix once instead of using dynamic edges.
        if self._backend_factory.backend_name == "sPyNNaker":
            self._backend_factory.set_topology_params(
                max_polyps=max_pop,
                n_input=n_input,
                n_exc=n_exc,
                n_inh=n_inh,
                n_readout=n_readout,
                neurons_per_polyp=n_per_polyp,
            )

        self.polyp_population = PolypPopulation(
            simulator=self.sim,
            max_polyps=max_pop,
            label="cra_polyps",
            neuron_type=PolypNeuronType(
                tau_m_ms=self.config.network.tau_m,
                v_rest_mV=self.config.network.v_rest,
                v_reset_mV=self.config.network.v_reset,
                v_thresh_mV=self.config.network.v_thresh,
                tau_refrac_ms=self.config.network.tau_refrac,
                tau_syn_e_ms=self.config.network.tau_syn_e,
                tau_syn_i_ms=self.config.network.tau_syn_i,
                cm_nF=self.config.network.cm,
            ),
            neurons_per_polyp=n_per_polyp,
            n_input=n_input,
            n_exc=n_exc,
            n_inh=n_inh,
            n_readout=n_readout,
            internal_conn_seed=getattr(cfg_spin, "internal_conn_seed", 42),
            backend_factory=self._backend_factory,
        )

        # 2. Founders
        initial_pop = int(getattr(self.config.lifecycle, "initial_population", 1))
        if initial_pop < 1:
            raise ValueError("initial_population must be >= 1")
        if initial_pop > max_pop:
            raise ValueError(
                "initial_population cannot exceed max_population_hard "
                f"({initial_pop} > {max_pop})"
            )

        founder_states: list[PolypState] = []
        for founder_idx in range(initial_pop):
            founder = PolypState(
                polyp_id=-1,
                lineage_id=-1,
                trophic_health=20.0,
                metabolic_decay=self.config.energy.metabolic_decay_default,
                cyclin_accumulation_rate=1.0,
                cyclin_degradation_rate=0.01,
                is_alive=True,
                is_juvenile=True,
                direct_stream_mask=set(self.stream_keys[:1]),
            )
            # Slightly spread seeded founders so spatial/gap-junction logic can
            # distinguish them while preserving deterministic initialisation.
            founder.xyz = np.array([float(founder_idx), 0.0, 0.0], dtype=float)
            slot_idx = self.polyp_population.add_polyp(founder)
            founder_state = self.polyp_population.states[slot_idx]
            founder_states.append(founder_state)

        self.founder_id = founder_states[0].polyp_id

        # 3. Network
        self.network = ReefNetwork(
            sim=self.sim,
            population=self.polyp_population,
            config=graph_config(self.config),
            backend_factory=self._backend_factory,
        )

        # For sPyNNaker pre-allocation mode, create the full static projection
        # matrix now so it exists before the first sim.run().
        if (
            self._backend_factory.backend_name == "sPyNNaker"
            and getattr(self._backend_factory, "_preallocate", False)
        ):
            try:
                self.network.sync_to_spinnaker()
            except Exception as exc:
                logger.warning("Pre-allocation sync during init failed: %s", exc)

        # 4. Subsystems
        self.energy_manager = EnergyManager(
            config=energy_manager_config(self.config),
            n_streams=n_streams,
        )
        self.lifecycle_manager = LifecycleManager(
            config=self.config.lifecycle,
            energy_config=self.config.energy,
            n_streams=n_streams,
        )
        # Sync polyp ID counters so lifecycle and population agree
        self.lifecycle_manager._next_polyp_id = self.polyp_population.next_polyp_id
        # Register seeded founders in lifecycle manager so lineage and
        # lifecycle accounting match the preallocated population.
        lm = self.lifecycle_manager
        for founder_state in founder_states:
            lm._polyp_registry[founder_state.polyp_id] = founder_state
            lineage = lm.get_or_create_lineage(founder_state.lineage_id)
            lineage.founder_id = founder_state.polyp_id
            if founder_state.polyp_id not in lineage.polyp_ids:
                lineage.polyp_ids.append(founder_state.polyp_id)
                lineage.birth_steps.append(0)
            lm._juvenile_birth_step[founder_state.polyp_id] = 0

        # Initialize maternal reserve for pre-handoff founder cleavage
        self.energy_manager.initialize_maternal_reserve(
            founder_state=founder_states[0],
            n_streams=n_streams,
            dt=60.0,
        )

        self.learning_manager = LearningManager(
            config=learning_manager_config(self.config),
        )
        if self.trading_bridge is None and self.use_default_trading_bridge:
            self.trading_bridge = TradingBridge(
                config=trading_config(self.config),
                stream_key=stream_keys[0] if stream_keys else "default",
            )

        # 5. BOCPD
        self.bocpd = BayesianOnlineChangepointDetector(
            hazard_rate=self.config.measurement.bocpd_hazard_rate,
            mu0=self.config.measurement.bocpd_mu0,
            kappa0=self.config.measurement.bocpd_kappa0,
            alpha0=self.config.measurement.bocpd_alpha0,
            beta0=self.config.measurement.bocpd_beta0,
            tail_mass_threshold=self.config.measurement.bocpd_tail_mass_threshold,
            max_run_length=self.config.measurement.bocpd_max_run_length,
        )

        # 6. Stream buffers
        hist_len = self.config.measurement.stream_history_maxlen
        self.stream_buffers = {k: deque(maxlen=hist_len) for k in self.stream_keys}
        self.stream_mi = {k: 0.0 for k in self.stream_keys}
        self._reset_context_memory()
        self._reset_predictive_context()
        self._reset_composition_routing()

        logger.info("Organism initialised: %d streams, founder=%s", n_streams, self.founder_id)

    def train_step(
        self,
        market_return_1m: float,
        dt_seconds: float = 60.0,
        sensory_return_1m: Optional[float] = None,
    ) -> StepMetrics:
        """Execute one full CRA simulation step.

        ``market_return_1m`` is the target/outcome used for task consequence.
        ``sensory_return_1m`` optionally decouples the observation injected into
        the SNN from that target.  Controlled tests use this to run shuffled-label
        and leakage checks; normal trading demos leave it as ``None`` so the
        observed market return is both input and outcome.
        """
        if self.trading_bridge is None:
            raise RuntimeError(
                "train_step requires a TradingBridge. Use train_task_step for "
                "domain-neutral task adapters."
            )
        sensory_value = (
            market_return_1m if sensory_return_1m is None else sensory_return_1m
        )

        def outcome_factory(polyp_states: list, spike_data: dict[int, int]) -> TaskOutcomeSurface:
            return self.trading_bridge.evaluate_step(
                market_return_1m=market_return_1m,
                dt_seconds=dt_seconds,
                polyp_states=polyp_states,
                spike_counts=spike_data,
            )

        return self._execute_task_step(
            sensory_value=float(sensory_value),
            dt_seconds=dt_seconds,
            outcome_factory=outcome_factory,
        )

    def train_task_step(
        self,
        observation_value: float,
        consequence_value: float,
        dt_seconds: float = 60.0,
        horizon_signal: Optional[float] = None,
        task_name: str = "generic",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StepMetrics:
        """Execute one step through the domain-neutral task surface.

        ``observation_value`` is injected as sensory drive. ``consequence_value``
        is the immediate signed outcome, and ``horizon_signal`` is the signed
        learning/evaluation consequence. For immediate tasks they are usually
        the same; delayed-control tasks can pass sparse delayed rewards as both
        fields while evaluating cue-time predictions externally.
        """
        target_signal = (
            float(consequence_value)
            if horizon_signal is None
            else float(horizon_signal)
        )

        def outcome_factory(
            polyp_states: list,
            spike_data: dict[int, int],
        ) -> GenericTaskOutcomeSurface:
            colony_prediction = self._compute_domain_neutral_prediction(
                polyp_states=polyp_states,
                spike_data=spike_data,
            )
            pred_sign = 1 if colony_prediction > 0.0 else -1 if colony_prediction < 0.0 else 0
            target_sign = 1 if target_signal > 0.0 else -1 if target_signal < 0.0 else 0
            direction_correct = (
                pred_sign != 0 and target_sign != 0 and pred_sign == target_sign
            )
            return GenericTaskOutcomeSurface(
                task_signal=target_signal,
                actual_return_1m=float(consequence_value),
                actual_return_5m=target_signal,
                direction_correct=direction_correct,
                colony_prediction=colony_prediction,
                position_size=colony_prediction,
                capital=1.0,
                dopamine_output_scale=float(self.config.learning.seed_output_scale),
                task_name=task_name,
                metadata=metadata,
            )

        sensory_value, context_memory_activity = self._prepare_context_memory_observation(
            observation_value=float(observation_value),
            metadata=metadata,
        )
        sensory_value, predictive_context_activity = self._prepare_predictive_context_observation(
            observation_value=sensory_value,
            metadata=metadata,
        )
        sensory_value, composition_routing_activity = self._prepare_composition_routing_observation(
            observation_value=sensory_value,
            metadata=metadata,
        )

        metrics = self._execute_task_step(
            sensory_value=sensory_value,
            dt_seconds=dt_seconds,
            outcome_factory=outcome_factory,
            context_memory_activity=context_memory_activity,
            predictive_context_activity=predictive_context_activity,
            composition_routing_activity=composition_routing_activity,
        )
        post_activity = self._update_composition_routing_after_feedback(
            metadata=metadata,
            target_signal=target_signal,
        )
        if post_activity:
            self._apply_composition_activity_to_metrics(metrics, post_activity)
        return metrics

    def train_adapter_step(
        self,
        adapter: Any,
        observation: Any,
        dt_seconds: float = 60.0,
    ) -> StepMetrics:
        """Execute one step through a domain-neutral ``TaskAdapter``.

        This path intentionally does not require ``TradingBridge``. The adapter
        encodes the observation into channels and evaluates the executed colony
        prediction into a signed consequence surface.
        """
        n_channels = int(getattr(self.config.spinnaker, "n_input_per_polyp", 1))
        encoded = np.asarray(adapter.encode(observation, n_channels), dtype=float).reshape(-1)
        sensory_value = float(encoded[0]) if encoded.size else 0.0

        def outcome_factory(
            polyp_states: list,
            spike_data: dict[int, int],
        ) -> GenericTaskOutcomeSurface:
            colony_prediction = self._compute_domain_neutral_prediction(
                polyp_states=polyp_states,
                spike_data=spike_data,
            )
            consequence = adapter.evaluate(
                colony_prediction,
                observation,
                dt_seconds,
            )
            horizon_signal = float(getattr(consequence, "horizon_signal", 0.0))
            actual_value = float(getattr(consequence, "actual_value", horizon_signal))
            return GenericTaskOutcomeSurface(
                task_signal=horizon_signal,
                actual_return_1m=actual_value,
                actual_return_5m=horizon_signal,
                direction_correct=bool(getattr(consequence, "direction_correct", False)),
                colony_prediction=colony_prediction,
                position_size=colony_prediction,
                capital=1.0,
                raw_dopamine=(
                    0.0
                    if getattr(consequence, "raw_dopamine", None) is None
                    else float(getattr(consequence, "raw_dopamine"))
                ),
                dopamine_output_scale=float(self.config.learning.seed_output_scale),
                task_name=str(
                    getattr(
                        adapter,
                        "task_name",
                        adapter.__class__.__name__,
                    )
                ),
                task_metrics=dict(getattr(consequence, "task_metrics", {}) or {}),
                metadata=getattr(consequence, "metadata", None),
            )

        return self._execute_task_step(
            sensory_value=sensory_value,
            dt_seconds=dt_seconds,
            outcome_factory=outcome_factory,
        )

    def _execute_task_step(
        self,
        *,
        sensory_value: float,
        dt_seconds: float,
        outcome_factory,
        context_memory_activity: Optional[Dict[str, Any]] = None,
        predictive_context_activity: Optional[Dict[str, Any]] = None,
        composition_routing_activity: Optional[Dict[str, Any]] = None,
    ) -> StepMetrics:
        """Shared organism loop for trading and domain-neutral task adapters."""
        step_begin = time.perf_counter()
        step = self.step_counter
        runtime_ms = dt_seconds * 1000.0

        # 0. Inject task observation as sensory drive so the SNN has
        #    task-relevant input to learn from. update_current_injections adds
        #    the baseline internally.
        if self.polyp_population is not None:
            for state in self.polyp_population.states:
                if state.is_alive:
                    state.sensory_drive = sensory_value * 30.0
            self.polyp_population.update_current_injections()

        # 1. SpiNNaker execution
        t0 = time.perf_counter()
        spike_data = self._run_spinnaker(runtime_ms)
        t_spinnaker = (time.perf_counter() - t0) * 1000.0

        if self.is_extinct:
            metrics = empty_metrics(step, t_spinnaker)
            self.metrics_history.append(metrics)
            self.step_counter += 1
            return metrics

        # 1b. Host-side graph cascade.
        #
        # The reef graph is meant to be more than a lineage/telemetry object:
        # spike-mediated messages should be able to bias each polyp's readout
        # before the task outcome is evaluated. This bounded context blend is
        # what makes feedforward/lateral/feedback motif ablations causal in
        # controlled software tiers while keeping the local prediction primary.
        self._last_motif_activity = self._apply_graph_message_context(spike_data)
        self._apply_composition_routing_prediction_context(composition_routing_activity)

        # 2. Measurement
        stream_mi = self._update_measurement(spike_data, step)

        # 3. Task consequence / prediction
        alive_indices = self.alive_polyp_indices
        polyp_states = [self.polyp_population.states[i] for i in alive_indices]

        task_outcome = outcome_factory(polyp_states, spike_data)

        # 4. Learning
        learning_result = self._run_learning(
            polyp_states=polyp_states,
            spike_data=spike_data,
            task_outcome=task_outcome,
            step=step,
            dt_ms=runtime_ms,
        )
        task_outcome.raw_dopamine = learning_result.raw_dopamine

        # 4b. Deliver dopamine to NEST native dopamine STDP synapses.
        # LearningManager is the single dopamine source; backend STDP consumes it.
        if self.network is not None and learning_result is not None:
            try:
                self.network.deliver_dopamine(learning_result.raw_dopamine)
            except Exception as exc:
                logger.warning("deliver_dopamine failed: %s", exc)

        # 5. Energy
        matured = self.learning_manager.get_matured_credits() \
            if self.learning_manager is not None else (0.0, 0.0)

        energy_result = self._run_energy(
            polyp_states=self.polyp_population.states,
            stream_mi=stream_mi,
            task_outcome=task_outcome,
            matured=matured,
            step=step,
            dt=1.0,  # host-side ecology uses per-step time
        )

        # 6. Lifecycle
        lifecycle_events = self._run_lifecycle(
            polyp_states=self.polyp_population.states,
            energy_result=energy_result,
            step=step,
            dt=1.0,
        )
        self._apply_lifecycle_events(
            lifecycle_events,
            energy_deaths=getattr(energy_result, "deaths", None),
        )

        # Increment age for all alive polyps
        if self.polyp_population is not None:
            self.polyp_population.step_all_age()

        # 7. Sync / rebuild
        if self._sync_interval > 0 and self.step_counter % self._sync_interval == 0:
            backend_name = getattr(
                self.sim, "__name__", self.sim.__class__.__name__
            )
            is_spinnaker = "spiNNaker" in backend_name or "spinnaker" in backend_name.lower()
            factory_prealloc = (
                is_spinnaker
                and self._backend_factory is not None
                and getattr(self._backend_factory, "_preallocate", False)
            )
            if factory_prealloc:
                # Pre-allocation mode: hardware topology is static.
                # Dopamine is delivered earlier in train_step; nothing to sync.
                logger.debug("train_step: sPyNNaker pre-allocation mode — skipping sync")
            elif is_spinnaker and self.network is not None:
                # Dynamic mode (no pre-allocation): full rebuild on topology change
                n_alive = self.n_alive
                n_edges = sum(
                    1 for e in self.network.edges.values()
                    if getattr(e, "is_pruned", False) is False
                )
                topology_changed = (
                    n_alive != self._last_rebuild_n_alive
                    or n_edges != self._last_rebuild_n_edges
                )
                if topology_changed:
                    self.rebuild_spinnaker()
                else:
                    self._sync_to_spinnaker()
            else:
                self._sync_to_spinnaker()

        # 8. Telemetry
        t_host = (time.perf_counter() - t0) * 1000.0 - t_spinnaker
        total_wall = (time.perf_counter() - step_begin) * 1000.0

        metrics = assemble_step_metrics(
            step=step,
            dt_ms=self.config.spinnaker.runtime_ms_per_step,
            population_size=self.population_size,
            polyp_states=self.polyp_population.states if self.polyp_population else [],
            network_edges=self.network.edges if self.network else {},
            gap_junctions=getattr(self.network, "gap_junctions", {}),
            energy_result=energy_result,
            learning_result=learning_result,
            task_outcome=task_outcome,
            stream_mi=stream_mi,
            timing={
                "spinnaker": t_spinnaker,
                "host": max(0.0, t_host),
                "total": total_wall,
            },
            lifecycle_events=lifecycle_events,
            accuracy_ema=self._accuracy_ema,
            changepoint_probability=self._last_changepoint_probability,
            motif_activity=self._last_motif_activity,
            context_memory_activity=context_memory_activity,
            predictive_context_activity=predictive_context_activity,
            composition_routing_activity=composition_routing_activity,
        )

        self.metrics_history.append(metrics)
        self.step_counter += 1

        if learning_result.mean_accuracy_ema is not None:
            alpha = self.config.learning.directional_accuracy_ema_alpha
            self._accuracy_ema = alpha * learning_result.mean_accuracy_ema + (1.0 - alpha) * self._accuracy_ema

        return metrics

    def _reset_context_memory(self) -> None:
        """Reset the bounded internal context-memory store."""
        self._context_memory_value = 1
        self._context_memory_history = []
        self._context_memory_slots = {}
        self._context_memory_slot_order = []
        self._context_memory_updates = 0
        self._last_context_memory_activity = self._context_memory_activity(
            enabled=False,
            mode="disabled",
            raw_observation=0.0,
            bound_observation=0.0,
            feature_source="disabled",
            feature_active=False,
            visible_cue_sign=0,
            context_memory_key="",
        )

    def _reset_predictive_context(self) -> None:
        """Reset the bounded internal predictive-context store."""
        self._predictive_context_value = 0
        self._predictive_context_slots = {}
        self._predictive_context_slot_order = []
        self._predictive_context_updates = 0
        self._last_predictive_context_activity = self._predictive_context_activity(
            enabled=False,
            mode="disabled",
            raw_observation=0.0,
            bound_observation=0.0,
            feature_source="disabled",
            feature_active=False,
            visible_signal=0,
            predictive_context_key="",
        )

    def _reset_composition_routing(self) -> None:
        """Reset the bounded internal composition/routing store."""
        self._composition_module_table = {}
        self._composition_route_scores = {}
        self._composition_current_skill_a = ""
        self._composition_current_skill_b = ""
        self._composition_current_skill = ""
        self._composition_current_context = ""
        self._composition_current_input = 1
        self._composition_seen_skills = []
        self._composition_seen_contexts = []
        self._composition_module_updates = 0
        self._composition_router_updates = 0
        self._composition_module_uses = 0
        self._composition_router_uses = 0
        self._composition_correct_route_uses = 0
        self._composition_pre_feedback_select_steps = 0
        self._composition_rng = np.random.default_rng(int(getattr(self.config, "seed", 0) or 0) + 95137)
        self._last_composition_routing_activity = self._composition_routing_activity(
            enabled=False,
            mode="disabled",
            raw_observation=0.0,
            bound_observation=0.0,
            feature_source="disabled",
            feature_active=False,
        )

    @staticmethod
    def _signed(value: float) -> int:
        if value > 0.0:
            return 1
        if value < 0.0:
            return -1
        return 0

    def _context_memory_activity(
        self,
        *,
        enabled: bool,
        mode: str,
        raw_observation: float,
        bound_observation: float,
        feature_source: str,
        feature_active: bool,
        visible_cue_sign: int,
        context_memory_key: str = "",
    ) -> Dict[str, Any]:
        return {
            "enabled": bool(enabled),
            "mode": str(mode),
            "context_memory_value": int(self._context_memory_value),
            "context_memory_updates": int(self._context_memory_updates),
            "feature_active": bool(feature_active),
            "feature_source": str(feature_source),
            "visible_cue_sign": int(visible_cue_sign),
            "raw_observation": float(raw_observation),
            "bound_observation": float(bound_observation),
            "context_memory_key": str(context_memory_key),
            "context_memory_slot_count": int(len(self._context_memory_slots)),
        }

    def _predictive_context_activity(
        self,
        *,
        enabled: bool,
        mode: str,
        raw_observation: float,
        bound_observation: float,
        feature_source: str,
        feature_active: bool,
        visible_signal: int,
        predictive_context_key: str = "",
    ) -> Dict[str, Any]:
        return {
            "enabled": bool(enabled),
            "mode": str(mode),
            "predictive_context_value": int(self._predictive_context_value),
            "predictive_context_updates": int(self._predictive_context_updates),
            "feature_active": bool(feature_active),
            "feature_source": str(feature_source),
            "visible_signal": int(visible_signal),
            "raw_observation": float(raw_observation),
            "bound_observation": float(bound_observation),
            "predictive_context_key": str(predictive_context_key),
            "predictive_context_slot_count": int(len(self._predictive_context_slots)),
        }

    def _composition_routing_activity(
        self,
        *,
        enabled: bool,
        mode: str,
        raw_observation: float,
        bound_observation: float,
        feature_source: str,
        feature_active: bool,
        event_type: str = "",
        phase: str = "",
        skill_a: str = "",
        skill_b: str = "",
        selected_skill: str = "",
        context: str = "",
        true_skill: str = "",
        router_correct: bool = False,
    ) -> Dict[str, Any]:
        return {
            "enabled": bool(enabled),
            "mode": str(mode),
            "raw_observation": float(raw_observation),
            "bound_observation": float(bound_observation),
            "feature_source": str(feature_source),
            "feature_active": bool(feature_active),
            "event_type": str(event_type),
            "phase": str(phase),
            "skill_a": str(skill_a),
            "skill_b": str(skill_b),
            "selected_skill": str(selected_skill),
            "context": str(context),
            "true_skill": str(true_skill),
            "router_correct": bool(router_correct),
            "module_updates": int(self._composition_module_updates),
            "router_updates": int(self._composition_router_updates),
            "module_uses": int(self._composition_module_uses),
            "router_uses": int(self._composition_router_uses),
            "correct_route_uses": int(self._composition_correct_route_uses),
            "pre_feedback_select_steps": int(self._composition_pre_feedback_select_steps),
        }

    def _composition_register_skill(self, skill: str) -> None:
        skill = str(skill or "")
        if skill and skill not in self._composition_seen_skills:
            self._composition_seen_skills.append(skill)
            self._composition_module_table.setdefault(skill, {})

    def _composition_register_context(self, context: str) -> None:
        context = str(context or "")
        if context and context not in self._composition_seen_contexts:
            self._composition_seen_contexts.append(context)
            self._composition_route_scores.setdefault(context, {})

    @staticmethod
    def _composition_input_sign(metadata: Dict[str, Any], cfg: Any, raw: float) -> int:
        key = str(
            getattr(
                cfg,
                "composition_routing_input_sign_metadata",
                "composition_input_sign",
            )
            or "composition_input_sign"
        )
        if key in metadata:
            try:
                value = int(metadata.get(key) or 0)
                if value != 0:
                    return 1 if value > 0 else -1
            except (TypeError, ValueError):
                pass
        return 1 if raw >= 0.0 else -1

    @staticmethod
    def _metadata_str(metadata: Dict[str, Any], key: str, default: str = "") -> str:
        value = metadata.get(key, default)
        if value is None:
            return str(default)
        return str(value)

    def _composition_shuffled_skill(self, skill: str) -> str:
        skills = sorted(self._composition_seen_skills)
        if not skills or skill not in skills:
            return skill
        return skills[(skills.index(skill) + 1) % len(skills)]

    def _composition_shuffled_context(self, context: str) -> str:
        contexts = sorted(self._composition_seen_contexts)
        if not contexts or context not in contexts:
            return context
        return contexts[(contexts.index(context) + 1) % len(contexts)]

    def _composition_module_lookup(self, skill: str, x: int, mode: str) -> int:
        skill = str(skill or "")
        if not skill:
            return 0
        lookup_skill = self._composition_shuffled_skill(skill) if mode == "shuffle" else skill
        table = self._composition_module_table.get(lookup_skill, {})
        x = 1 if int(x) >= 0 else -1
        return int(table.get(x, 0) or 0)

    def _composition_learned_route(self, context: str) -> str:
        scores = self._composition_route_scores.get(str(context or ""), {})
        if not scores:
            return ""
        best_skill, best_score = max(scores.items(), key=lambda item: (float(item[1]), str(item[0])))
        return str(best_skill) if float(best_score) > 0.0 else ""

    def _composition_select_skill(self, context: str, mode: str) -> str:
        context = str(context or "")
        if mode == "context_shuffle":
            context = self._composition_shuffled_context(context)
        if mode == "random_router" and self._composition_seen_skills:
            return str(self._composition_rng.choice(sorted(self._composition_seen_skills)))
        return self._composition_learned_route(context)

    def _prepare_composition_routing_observation(
        self,
        *,
        observation_value: float,
        metadata: Optional[Dict[str, Any]],
    ) -> tuple[float, Dict[str, Any]]:
        """Optionally inject an internally composed/routed decision feature.

        The pathway can update current visible cues before scoring a step, but
        module/router learning happens only in
        :meth:`_update_composition_routing_after_feedback`, after the current
        step has been evaluated. That split is the audit boundary preventing
        feedback leakage.
        """
        cfg = self.config.learning
        enabled = bool(getattr(cfg, "composition_routing_enabled", False))
        mode = str(getattr(cfg, "composition_routing_mode", "normal") or "normal")
        raw = float(observation_value)
        metadata = metadata or {}
        if not enabled:
            activity = self._composition_routing_activity(
                enabled=False,
                mode="disabled",
                raw_observation=raw,
                bound_observation=raw,
                feature_source="raw",
                feature_active=False,
            )
            self._last_composition_routing_activity = activity
            return raw, activity

        event_key = str(getattr(cfg, "composition_routing_event_key", "event_type") or "event_type")
        phase_key = str(getattr(cfg, "composition_routing_phase_metadata", "phase") or "phase")
        event = self._metadata_str(metadata, event_key)
        phase = self._metadata_str(metadata, phase_key)
        skill_a_key = str(getattr(cfg, "composition_routing_skill_a_metadata", "composition_skill_a") or "composition_skill_a")
        skill_b_key = str(getattr(cfg, "composition_routing_skill_b_metadata", "composition_skill_b") or "composition_skill_b")
        skill_key = str(getattr(cfg, "composition_routing_skill_metadata", "composition_skill") or "composition_skill")
        context_key = str(getattr(cfg, "composition_routing_context_metadata", "routing_context") or "routing_context")
        true_skill_key = str(getattr(cfg, "composition_routing_true_skill_metadata", "routing_true_skill") or "routing_true_skill")

        skill_a = self._metadata_str(metadata, skill_a_key, self._composition_current_skill_a)
        skill_b = self._metadata_str(metadata, skill_b_key, self._composition_current_skill_b)
        primitive_skill = self._metadata_str(metadata, skill_key, "")
        true_skill = self._metadata_str(metadata, true_skill_key, primitive_skill)
        context = self._metadata_str(metadata, context_key, self._composition_current_context)
        x = self._composition_input_sign(metadata, cfg, raw)

        if event == str(getattr(cfg, "composition_routing_skill_a_event", "skill_a")):
            self._composition_current_skill_a = skill_a
            self._composition_current_skill_b = ""
            self._composition_register_skill(skill_a)
        elif event == str(getattr(cfg, "composition_routing_skill_b_event", "skill_b")):
            self._composition_current_skill_b = skill_b
            self._composition_register_skill(skill_b)
        elif event == str(getattr(cfg, "composition_routing_skill_event", "skill")):
            skill = primitive_skill or true_skill or skill_a
            self._composition_current_skill = skill
            self._composition_current_skill_a = skill
            self._composition_current_skill_b = ""
            self._composition_register_skill(skill)
        elif event == str(getattr(cfg, "composition_routing_context_event", "route_context")):
            self._composition_current_context = context
            self._composition_register_context(context)
        elif event == str(getattr(cfg, "composition_routing_input_event", "input")):
            self._composition_current_input = x

        decision_event = str(getattr(cfg, "composition_routing_decision_event", "decision"))
        bound = raw
        feature = 0
        selected_skill = ""
        feature_source = "raw"
        feature_active = False
        router_correct = False
        if event == decision_event:
            skill_a = skill_a or primitive_skill or true_skill or self._composition_current_skill_a
            skill_b = skill_b or self._composition_current_skill_b
            context = context or self._composition_current_context
            true_skill = true_skill or primitive_skill or skill_a
            x = x or self._composition_current_input
            if context:
                if mode == "always_on":
                    votes = [
                        self._composition_module_lookup(skill, x, mode)
                        for skill in sorted(self._composition_seen_skills)
                    ]
                    feature = 1 if sum(votes) > 0 else -1 if sum(votes) < 0 else 0
                    selected_skill = "all"
                elif mode == "router_reset" and phase.startswith("heldout"):
                    selected_skill = ""
                    feature = 0
                else:
                    selected_skill = self._composition_select_skill(context, mode)
                    feature = self._composition_module_lookup(selected_skill, x, mode) if selected_skill else 0
                feature_source = f"internal_{mode}_router"
                if phase.startswith("heldout") and selected_skill:
                    self._composition_router_uses += 1
                    self._composition_pre_feedback_select_steps += 1
                    router_correct = bool(true_skill and selected_skill == true_skill)
                    self._composition_correct_route_uses += int(router_correct)
            elif skill_a:
                if mode == "reset" and phase.startswith("heldout"):
                    feature = 0
                else:
                    first = self._composition_module_lookup(skill_a, x, mode)
                    if skill_b:
                        if mode == "order_shuffle":
                            first = self._composition_module_lookup(skill_b, x, mode)
                            feature = self._composition_module_lookup(skill_a, first, mode) if first != 0 else 0
                        else:
                            feature = self._composition_module_lookup(skill_b, first, mode) if first != 0 else 0
                    else:
                        feature = first
                selected_skill = skill_b or skill_a
                feature_source = f"internal_{mode}_composition"
                if phase.startswith("heldout") and feature != 0:
                    self._composition_module_uses += 1

            if feature != 0:
                gain = float(getattr(cfg, "composition_routing_input_gain", 1.0) or 1.0)
                bound = gain * float(1 if feature > 0 else -1)
                feature_active = True

        activity = self._composition_routing_activity(
            enabled=True,
            mode=mode,
            raw_observation=raw,
            bound_observation=bound,
            feature_source=feature_source,
            feature_active=feature_active,
            event_type=event,
            phase=phase,
            skill_a=skill_a,
            skill_b=skill_b,
            selected_skill=selected_skill,
            context=context,
            true_skill=true_skill,
            router_correct=router_correct,
        )
        self._last_composition_routing_activity = activity
        return float(bound), activity

    def _update_composition_routing_after_feedback(
        self,
        *,
        metadata: Optional[Dict[str, Any]],
        target_signal: float,
    ) -> Dict[str, Any]:
        cfg = self.config.learning
        if not bool(getattr(cfg, "composition_routing_enabled", False)):
            return {}
        mode = str(getattr(cfg, "composition_routing_mode", "normal") or "normal")
        if mode == "no_write":
            return dict(self._last_composition_routing_activity)
        metadata = metadata or {}
        event_key = str(getattr(cfg, "composition_routing_event_key", "event_type") or "event_type")
        phase_key = str(getattr(cfg, "composition_routing_phase_metadata", "phase") or "phase")
        event = self._metadata_str(metadata, event_key)
        decision_event = str(getattr(cfg, "composition_routing_decision_event", "decision"))
        if event != decision_event:
            return dict(self._last_composition_routing_activity)
        label = self._signed(float(target_signal))
        if label == 0:
            return dict(self._last_composition_routing_activity)

        skill_a_key = str(getattr(cfg, "composition_routing_skill_a_metadata", "composition_skill_a") or "composition_skill_a")
        skill_key = str(getattr(cfg, "composition_routing_skill_metadata", "composition_skill") or "composition_skill")
        context_key = str(getattr(cfg, "composition_routing_context_metadata", "routing_context") or "routing_context")
        true_skill_key = str(getattr(cfg, "composition_routing_true_skill_metadata", "routing_true_skill") or "routing_true_skill")
        phase = self._metadata_str(metadata, phase_key)
        skill = (
            self._metadata_str(metadata, skill_key)
            or self._metadata_str(metadata, true_skill_key)
            or self._metadata_str(metadata, skill_a_key)
            or self._composition_current_skill
            or self._composition_current_skill_a
        )
        context = self._metadata_str(metadata, context_key, self._composition_current_context)
        x = self._composition_input_sign(metadata, cfg, 1.0)

        if phase == "primitive_train" and skill:
            self._composition_register_skill(skill)
            self._composition_module_table.setdefault(skill, {})[1 if x >= 0 else -1] = int(label)
            self._composition_module_updates += 1
        elif phase == "route_train" and context:
            self._composition_register_context(context)
            scores = self._composition_route_scores.setdefault(context, {})
            for candidate in sorted(self._composition_seen_skills):
                predicted = self._composition_module_lookup(candidate, x, mode)
                if predicted == label:
                    scores[candidate] = float(scores.get(candidate, 0.0)) + 1.0
                elif predicted != 0:
                    scores[candidate] = float(scores.get(candidate, 0.0)) - 0.25
            self._composition_router_updates += 1

        activity = dict(self._last_composition_routing_activity)
        activity.update(
            {
                "module_updates": int(self._composition_module_updates),
                "router_updates": int(self._composition_router_updates),
                "module_uses": int(self._composition_module_uses),
                "router_uses": int(self._composition_router_uses),
                "correct_route_uses": int(self._composition_correct_route_uses),
                "pre_feedback_select_steps": int(self._composition_pre_feedback_select_steps),
            }
        )
        self._last_composition_routing_activity = activity
        return activity

    @staticmethod
    def _apply_composition_activity_to_metrics(
        metrics: StepMetrics,
        activity: Dict[str, Any],
    ) -> None:
        field_map = {
            "enabled": "composition_routing_enabled",
            "mode": "composition_routing_mode",
            "feature_active": "composition_routing_feature_active",
            "feature_source": "composition_routing_feature_source",
            "raw_observation": "composition_routing_raw_observation",
            "bound_observation": "composition_routing_bound_observation",
            "event_type": "composition_routing_event_type",
            "phase": "composition_routing_phase",
            "skill_a": "composition_routing_skill_a",
            "skill_b": "composition_routing_skill_b",
            "selected_skill": "composition_routing_selected_skill",
            "context": "composition_routing_context",
            "true_skill": "composition_routing_true_skill",
            "router_correct": "composition_routing_router_correct",
            "module_updates": "composition_routing_module_updates",
            "router_updates": "composition_routing_router_updates",
            "module_uses": "composition_routing_module_uses",
            "router_uses": "composition_routing_router_uses",
            "correct_route_uses": "composition_routing_correct_route_uses",
            "pre_feedback_select_steps": "composition_routing_pre_feedback_select_steps",
        }
        for source, target in field_map.items():
            if hasattr(metrics, target) and source in activity:
                setattr(metrics, target, activity[source])

    def _apply_composition_routing_prediction_context(
        self,
        activity: Optional[Dict[str, Any]],
    ) -> None:
        """Blend the internal routed/composed feature into colony readouts.

        This is intentionally host-side and disabled unless
        ``composition_routing_prediction_mix`` is set above zero. The feature
        itself must already have been selected before feedback for the current
        decision step; this method only exposes that selected module output to
        the same readout fields used by graph-message context.
        """
        if not activity or not bool(activity.get("feature_active", False)):
            return
        cfg = self.config.learning
        mix = float(getattr(cfg, "composition_routing_prediction_mix", 0.0) or 0.0)
        if mix <= 0.0 or self.polyp_population is None:
            return
        bounded_mix = max(0.0, min(1.0, mix))
        gain = float(getattr(cfg, "composition_routing_prediction_gain", 1.0) or 1.0)
        feature = math.tanh(float(activity.get("bound_observation", 0.0) or 0.0) * gain)
        if abs(feature) <= 1e-12:
            return
        for state in self.polyp_population.states:
            if not getattr(state, "is_alive", False):
                continue
            old_pred = float(getattr(state, "last_output_signed_contribution", 0.0))
            blended = math.tanh((1.0 - bounded_mix) * old_pred + bounded_mix * feature)
            state.last_output_signed_contribution = blended
            state.current_prediction = blended
            state.last_raw_rpe = blended

    @staticmethod
    def _context_memory_key(metadata: Dict[str, Any], cfg: Any) -> str:
        key_name = str(getattr(cfg, "context_memory_key_metadata", "context_memory_key") or "context_memory_key")
        default_key = str(getattr(cfg, "context_memory_default_key", "default") or "default")
        key = metadata.get(key_name, default_key)
        if key is None or str(key) == "":
            return default_key
        return str(key)

    @staticmethod
    def _predictive_context_key(metadata: Dict[str, Any], cfg: Any) -> str:
        key_name = str(
            getattr(
                cfg,
                "predictive_context_key_metadata",
                "predictive_context_key",
            )
            or "predictive_context_key"
        )
        default_key = str(
            getattr(cfg, "predictive_context_default_key", "default") or "default"
        )
        key = metadata.get(key_name, default_key)
        if key is None or str(key) == "":
            return default_key
        return str(key)

    def _touch_context_memory_slot(self, key: str) -> None:
        if key in self._context_memory_slot_order:
            self._context_memory_slot_order.remove(key)
        self._context_memory_slot_order.append(key)

    def _write_context_memory_slot(self, key: str, sign: int, cfg: Any) -> None:
        max_slots = max(1, int(getattr(cfg, "context_memory_slot_count", 1) or 1))
        if key not in self._context_memory_slots and len(self._context_memory_slots) >= max_slots:
            policy = str(getattr(cfg, "context_memory_overwrite_policy", "lru") or "lru")
            if policy != "lru":
                policy = "lru"
            if self._context_memory_slot_order:
                evicted = self._context_memory_slot_order.pop(0)
                self._context_memory_slots.pop(evicted, None)
        self._context_memory_slots[key] = int(sign)
        self._touch_context_memory_slot(key)

    def _touch_predictive_context_slot(self, key: str) -> None:
        if key in self._predictive_context_slot_order:
            self._predictive_context_slot_order.remove(key)
        self._predictive_context_slot_order.append(key)

    def _write_predictive_context_slot(self, key: str, sign: int, cfg: Any) -> None:
        max_slots = max(1, int(getattr(cfg, "predictive_context_slot_count", 1) or 1))
        if key not in self._predictive_context_slots and len(self._predictive_context_slots) >= max_slots:
            if self._predictive_context_slot_order:
                evicted = self._predictive_context_slot_order.pop(0)
                self._predictive_context_slots.pop(evicted, None)
        self._predictive_context_slots[key] = int(sign)
        self._touch_predictive_context_slot(key)

    def _read_context_memory_slot(self, key: str) -> int:
        if key in self._context_memory_slots:
            self._touch_context_memory_slot(key)
            return int(self._context_memory_slots[key])
        return int(self._context_memory_value)

    def _read_alternate_context_memory_slot(self, key: str, fallback: int) -> int:
        for candidate_key in reversed(self._context_memory_slot_order):
            if candidate_key != key and candidate_key in self._context_memory_slots:
                return int(self._context_memory_slots[candidate_key])
        return int(-fallback if fallback != 0 else -1)

    def _read_predictive_context_slot(self, key: str) -> int:
        if key in self._predictive_context_slots:
            self._touch_predictive_context_slot(key)
            return int(self._predictive_context_slots[key])
        return int(self._predictive_context_value)

    def _read_alternate_predictive_context_slot(self, key: str, fallback: int) -> int:
        for candidate_key in reversed(self._predictive_context_slot_order):
            if candidate_key != key and candidate_key in self._predictive_context_slots:
                return int(self._predictive_context_slots[candidate_key])
        return int(-fallback if fallback != 0 else -1)

    def replay_context_memory_episode(
        self,
        *,
        context_memory_key: str,
        context_sign: int,
        consolidate: bool = True,
        source: str = "offline_replay",
    ) -> Dict[str, Any]:
        """Replay a previously observed context episode into keyed memory.

        This is a host-side Tier 5.11b consolidation hook. It does not inspect
        labels, predictions, or future targets; the caller must provide a
        context key/sign that was already visible online. When ``consolidate``
        is false, the method records an auditable no-write replay event.
        """
        cfg = self.config.learning
        key = str(context_memory_key or getattr(cfg, "context_memory_default_key", "default"))
        sign = 1 if int(context_sign) >= 0 else -1
        enabled = bool(getattr(cfg, "context_memory_enabled", False))
        mode = str(getattr(cfg, "context_memory_mode", "normal") or "normal")
        keyed_mode = mode in {"keyed", "multi_slot", "keyed_context", "slot_reset", "slot_shuffle", "wrong_key"}
        wrote = bool(enabled and keyed_mode and consolidate)
        if wrote:
            self._write_context_memory_slot(key, sign, cfg)
        return {
            "enabled": enabled,
            "mode": mode,
            "source": str(source),
            "context_memory_key": key,
            "context_sign": int(sign),
            "consolidate": bool(consolidate),
            "wrote": wrote,
            "context_memory_slot_count": int(len(self._context_memory_slots)),
        }

    def _prepare_context_memory_observation(
        self,
        *,
        observation_value: float,
        metadata: Optional[Dict[str, Any]],
    ) -> tuple[float, Dict[str, Any]]:
        """Optionally bind visible context memory to a later visible cue.

        The mechanism is intentionally small and auditable: it can update only
        on metadata-marked visible context events, it never reads the target
        label, and its ablation modes are deterministic. This is still host-side
        software memory; native on-chip context storage is a future runtime
        target.
        """
        cfg = self.config.learning
        enabled = bool(getattr(cfg, "context_memory_enabled", False))
        mode = str(getattr(cfg, "context_memory_mode", "normal") or "normal")
        raw = float(observation_value)
        if not enabled:
            activity = self._context_memory_activity(
                enabled=False,
                mode="disabled",
                raw_observation=raw,
                bound_observation=raw,
                feature_source="raw",
                feature_active=False,
                visible_cue_sign=0,
                context_memory_key="",
            )
            self._last_context_memory_activity = activity
            return raw, activity

        metadata = metadata or {}
        event = str(metadata.get(getattr(cfg, "context_memory_event_key", "event_type"), ""))
        context_event = str(getattr(cfg, "context_memory_context_event", "context"))
        decision_event = str(getattr(cfg, "context_memory_decision_event", "decision"))
        memory_key = self._context_memory_key(metadata, cfg)
        sign = self._signed(raw)

        if event == context_event and sign != 0:
            self._context_memory_value = int(sign)
            self._context_memory_history.append(int(sign))
            if mode in {"keyed", "multi_slot", "keyed_context", "slot_reset", "slot_shuffle", "wrong_key"}:
                self._write_context_memory_slot(memory_key, int(sign), cfg)
            self._context_memory_updates += 1

        bound = raw
        feature_source = "raw"
        feature_active = False
        cue = sign if event == decision_event else 0
        gain = float(getattr(cfg, "context_memory_input_gain", 1.0) or 1.0)
        if event == decision_event and cue != 0:
            context = int(self._context_memory_value)
            if mode in {"normal", "context_bound", "internal"}:
                bound = gain * context * raw
                feature_source = "internal_context_bound"
                feature_active = True
            elif mode in {"keyed", "multi_slot", "keyed_context"}:
                keyed_context = self._read_context_memory_slot(memory_key)
                bound = gain * keyed_context * raw
                feature_source = "internal_keyed_context"
                feature_active = True
            elif mode == "reset":
                bound = gain * raw
                feature_source = "internal_reset_no_context"
                feature_active = True
            elif mode == "slot_reset":
                bound = gain * raw
                feature_source = "internal_slot_reset_no_context"
                feature_active = True
            elif mode == "shuffled":
                shuffled_context = (
                    int(self._context_memory_history[-2])
                    if len(self._context_memory_history) > 1
                    else -context
                )
                bound = gain * shuffled_context * raw
                feature_source = "internal_shuffled_context"
                feature_active = True
            elif mode == "slot_shuffle":
                keyed_context = self._read_context_memory_slot(memory_key)
                shuffled_context = self._read_alternate_context_memory_slot(memory_key, keyed_context)
                bound = gain * shuffled_context * raw
                feature_source = "internal_slot_shuffled_context"
                feature_active = True
            elif mode == "wrong":
                bound = gain * -context * raw
                feature_source = "internal_wrong_context"
                feature_active = True
            elif mode == "wrong_key":
                keyed_context = self._read_context_memory_slot(memory_key)
                wrong_context = self._read_alternate_context_memory_slot(memory_key, keyed_context)
                bound = gain * wrong_context * raw
                feature_source = "internal_wrong_key_context"
                feature_active = True

        activity = self._context_memory_activity(
            enabled=True,
            mode=mode,
            raw_observation=raw,
            bound_observation=bound,
            feature_source=feature_source,
            feature_active=feature_active,
            visible_cue_sign=cue,
            context_memory_key=memory_key,
        )
        self._last_context_memory_activity = activity
        return float(bound), activity

    def _prepare_predictive_context_observation(
        self,
        *,
        observation_value: float,
        metadata: Optional[Dict[str, Any]],
    ) -> tuple[float, Dict[str, Any]]:
        """Optionally bind a visible predictive precursor to a later decision.

        This Tier 5.12 pathway is intentionally host-side and bounded. It can
        update only from metadata-marked visible precursor events, can read only
        at metadata-marked decision events, and exposes wrong/shuffled/no-write
        modes for causal controls.
        """
        cfg = self.config.learning
        enabled = bool(getattr(cfg, "predictive_context_enabled", False))
        mode = str(getattr(cfg, "predictive_context_mode", "keyed") or "keyed")
        raw = float(observation_value)
        if not enabled:
            activity = self._predictive_context_activity(
                enabled=False,
                mode="disabled",
                raw_observation=raw,
                bound_observation=raw,
                feature_source="raw",
                feature_active=False,
                visible_signal=0,
                predictive_context_key="",
            )
            self._last_predictive_context_activity = activity
            return raw, activity

        metadata = metadata or {}
        update_key = str(
            getattr(
                cfg,
                "predictive_context_update_metadata",
                "predictive_context_update",
            )
            or "predictive_context_update"
        )
        decision_key = str(
            getattr(
                cfg,
                "predictive_context_decision_metadata",
                "predictive_context_decision",
            )
            or "predictive_context_decision"
        )
        signal_key = str(
            getattr(
                cfg,
                "predictive_context_signal_metadata",
                "predictive_context_sign",
            )
            or "predictive_context_sign"
        )
        memory_key = self._predictive_context_key(metadata, cfg)
        update_event = bool(metadata.get(update_key, False))
        decision_event = bool(metadata.get(decision_key, False))
        signal = self._signed(float(metadata.get(signal_key, 0.0) or 0.0))

        if update_event and signal != 0 and mode != "no_write":
            self._predictive_context_value = int(signal)
            if mode in {"keyed", "normal", "predictive_context", "wrong", "shuffled"}:
                self._write_predictive_context_slot(memory_key, int(signal), cfg)
            self._predictive_context_updates += 1

        bound = raw
        feature_source = "raw"
        feature_active = False
        visible_signal = signal if update_event else 0
        if decision_event:
            stored = self._read_predictive_context_slot(memory_key)
            feature = 0
            if mode in {"keyed", "normal", "predictive_context"}:
                feature = stored
                feature_source = "internal_predictive_context"
            elif mode == "wrong":
                feature = -stored
                feature_source = "internal_wrong_predictive_context"
            elif mode == "shuffled":
                feature = self._read_alternate_predictive_context_slot(memory_key, stored)
                feature_source = "internal_shuffled_predictive_context"
            elif mode == "no_write":
                feature = 0
                feature_source = "internal_no_write_predictive_context"

            if feature != 0:
                gain = float(getattr(cfg, "predictive_context_input_gain", 1.0) or 1.0)
                bound = gain * float(feature)
                feature_active = True

        activity = self._predictive_context_activity(
            enabled=True,
            mode=mode,
            raw_observation=raw,
            bound_observation=bound,
            feature_source=feature_source,
            feature_active=feature_active,
            visible_signal=visible_signal,
            predictive_context_key=memory_key,
        )
        self._last_predictive_context_activity = activity
        return float(bound), activity

    def _apply_graph_message_context(self, spike_data: dict[int, int]) -> Dict[str, Any]:
        """Blend reef-graph message passing into per-polyp readouts.

        This uses :meth:`ReefNetwork.run_message_round`, which updates edge
        activity/calcification and returns weighted incoming spike messages.
        The context is intentionally bounded with ``tanh`` and mixed with the
        local readout instead of replacing it.
        """
        if self.network is None or self.polyp_population is None:
            return {}
        steps = int(getattr(self.config.network, "message_passing_steps", 0) or 0)
        mix = float(getattr(self.config.network, "message_prediction_mix", 0.0) or 0.0)
        gain = float(getattr(self.config.network, "message_context_gain", 0.0) or 0.0)
        if steps <= 0 or mix <= 0.0 or gain <= 0.0:
            return {
                "motif_message_total": 0.0,
                "ff_message_total": 0.0,
                "lat_message_total": 0.0,
                "fb_message_total": 0.0,
                "graph_context_mean_abs": 0.0,
                "graph_context_nonzero_count": 0,
            }

        motif_totals = {"ff": 0.0, "lat": 0.0, "fb": 0.0}
        for (src, _dst), edge in self.network.edges.items():
            if getattr(edge, "is_pruned", False):
                continue
            spikes = int(spike_data.get(src, 0) or 0)
            if spikes <= 0:
                continue
            motif = str(getattr(edge, "edge_type", ""))
            if motif in motif_totals:
                motif_totals[motif] += abs(float(getattr(edge, "weight", 0.0)) * spikes)

        aggregated: Dict[int, float] = {}
        current_spikes = dict(spike_data)
        for _ in range(steps):
            aggregated = self.network.run_message_round(current_spikes)
            if not aggregated:
                break
            # For extra rounds, propagate only positive aggregate activity as
            # a coarse host-side spike proxy; negative/inhibitory messages
            # still affect the final readout context below.
            current_spikes = {
                int(pid): max(0, int(abs(value)))
                for pid, value in aggregated.items()
            }

        contexts: list[float] = []
        state_by_id = {
            int(state.polyp_id): state
            for state in self.polyp_population.states
            if getattr(state, "is_alive", False)
        }
        bounded_mix = max(0.0, min(1.0, mix))
        for pid, message in aggregated.items():
            state = state_by_id.get(int(pid))
            if state is None:
                continue
            context = math.tanh(float(message) * gain)
            old_pred = float(getattr(state, "last_output_signed_contribution", 0.0))
            blended = math.tanh((1.0 - bounded_mix) * old_pred + bounded_mix * context)
            state.graph_message_context = context
            state.last_output_signed_contribution = blended
            state.current_prediction = blended
            state.last_raw_rpe = blended
            contexts.append(context)

        return {
            "motif_message_total": float(sum(motif_totals.values())),
            "ff_message_total": float(motif_totals["ff"]),
            "lat_message_total": float(motif_totals["lat"]),
            "fb_message_total": float(motif_totals["fb"]),
            "graph_context_mean_abs": float(np.mean(np.abs(contexts))) if contexts else 0.0,
            "graph_context_nonzero_count": int(sum(1 for value in contexts if abs(value) > 1e-12)),
        }

    def _compute_domain_neutral_prediction(
        self,
        *,
        polyp_states: list,
        spike_data: dict[int, int],
    ) -> float:
        """Compute colony prediction without using the finance bridge."""
        if not polyp_states:
            return 0.0

        if self.learning_manager is not None:
            weights = self.learning_manager.compute_aggregation_weights(
                polyp_states,
                {"spike_counts": spike_data},
            )
            return float(
                sum(
                    weights.get(p.polyp_id, 0.0)
                    * float(getattr(p, "last_output_signed_contribution", 0.0))
                    for p in polyp_states
                )
            )

        predictions = [
            float(getattr(p, "last_output_signed_contribution", 0.0))
            for p in polyp_states
        ]
        return float(np.mean(predictions)) if predictions else 0.0

    def _apply_lifecycle_events(
        self, events: list, energy_deaths: list[int] | None = None
    ) -> None:
        """Apply birth/death events to the population and network.

        LifecycleManager modifies states in-place for deaths, but births
        need to be added through PolypPopulation to allocate hardware slots.
        Energy-manager deaths (which occur before lifecycle) are also handled
        so that incident edges are pruned and hardware i_offset is zeroed.
        """
        if self.polyp_population is None or self.network is None:
            return

        births = [e for e in events if e.event_type in ("birth", "cleavage")]
        deaths = [e for e in events if e.event_type == "death"]

        # Births: lifecycle appended raw states to polyp_states.
        # Remove them and re-add via PolypPopulation so hardware slots are allocated.
        for event in births:
            child_id = event.polyp_id
            # Find the raw appended state
            raw_idx = None
            for idx, state in enumerate(self.polyp_population.states):
                if state.polyp_id == child_id:
                    raw_idx = idx
                    break
            if raw_idx is None:
                continue

            child = self.polyp_population.states[raw_idx]
            # Remove from the end if it was appended there
            if raw_idx == len(self.polyp_population.states) - 1:
                self.polyp_population.states.pop(raw_idx)
            else:
                # Mark as dead placeholder so add_polyp can reuse the slot
                child.is_alive = False
                child.polyp_id = -1
                continue

            # Add properly via population (finds dead slot, sets hardware params)
            self.polyp_population.add_polyp(child, preserve_identity=True)
            if self.lifecycle_manager is not None:
                self.lifecycle_manager._next_polyp_id = max(
                    self.lifecycle_manager._next_polyp_id,
                    self.polyp_population.next_polyp_id,
                )

            # Register in network position table
            self.network.add_polyp(child)

            # Add parent-child edge if not present
            parent_id = event.parent_id
            if parent_id is not None and not self.network.has_edge(parent_id, child.polyp_id):
                self.network.add_edge(parent_id, child.polyp_id, weight=0.5)
            if parent_id is not None and not self.network.has_edge(child.polyp_id, parent_id):
                self.network.add_edge(child.polyp_id, parent_id, weight=0.5)

        # Helper to prune edges and zero hardware for a dead polyp
        def _handle_death(dead_id: int) -> None:
            state = self.polyp_population.get_state_by_polyp_id(dead_id)
            if state is not None:
                state.is_alive = False
                try:
                    self.polyp_population.population[
                        state.block_start : state.block_end
                    ].set(i_offset=-1000.0, v_thresh=1000.0)
                except Exception:
                    pass
            # Prune edges incident to dead polyp
            for key, edge in list(self.network.edges.items()):
                if isinstance(edge, ReefEdge) and (edge.source_id == dead_id or edge.target_id == dead_id):
                    edge.is_pruned = True

        # Deaths from lifecycle events
        for event in deaths:
            _handle_death(event.polyp_id)

        # Deaths from energy manager (silent — no lifecycle event generated
        # because the polyp was already dead when lifecycle ran)
        if energy_deaths:
            for dead_id in energy_deaths:
                _handle_death(dead_id)

    def _run_spinnaker(self, runtime_ms: float) -> dict[int, int]:
        """Execute the SNN and retrieve spike counts.

        Also populates ``self._last_polyp_summaries`` with full
        :class:`~coral_reef_spinnaker.polyp_neuron.PolypSummary`
        objects for downstream use.
        """
        if self.sim is None:
            self._last_sim_run_error = "sim is None"
            self._last_backend_failure_stage = "sim.run"
            self._last_backend_exception_type = "MissingSimulator"
            self._last_backend_traceback = ""
            return self._synthetic_spike_fallback(runtime_ms)

        try:
            self.sim.run(runtime_ms)
        except Exception as exc:
            self._sim_run_failure_count += 1
            self._last_sim_run_error = str(exc)
            self._last_backend_failure_stage = "sim.run"
            self._last_backend_exception_type = type(exc).__name__
            self._last_backend_traceback = traceback.format_exc()
            logger.warning("sim.run() failed (%s); falling back to synthetic spikes", exc)
            return self._synthetic_spike_fallback(runtime_ms)

        if self.polyp_population is not None:
            try:
                summaries = self.polyp_population.get_polyp_summaries(runtime_ms)
                self._last_polyp_summaries = summaries
                # Copy predictions from summaries back to polyp states
                state_map = {s.polyp_id: s for s in self.polyp_population.states}
                for pid, summary in summaries.items():
                    state = state_map.get(pid)
                    if state is not None:
                        backend_pred = float(getattr(summary, "prediction", 0.0))
                        feature = float(getattr(state, "sensory_drive", 0.0))
                        weight = float(
                            getattr(state, "predictive_readout_weight", 0.25)
                        )
                        bias = float(
                            getattr(state, "predictive_readout_bias", 0.0)
                        )
                        pred = math.tanh(weight * feature + bias)
                        state.last_backend_prediction = backend_pred
                        state.last_prediction_feature = feature
                        state.current_prediction = pred
                        # Sync learning-manager fields that were never set (bug fix)
                        state.last_output_signed_contribution = pred
                        state.last_raw_rpe = pred
                # Backward-compatible spike count dict
                spike_data = {pid: s.n_spikes_total for pid, s in summaries.items()}
                self.spike_buffer.append(spike_data)
                return spike_data
            except Exception as exc:
                self._summary_read_failure_count += 1
                self._last_sim_run_error = str(exc)
                self._last_backend_failure_stage = "summary_read"
                self._last_backend_exception_type = type(exc).__name__
                self._last_backend_traceback = traceback.format_exc()
                logger.warning("get_polyp_summaries() failed (%s); falling back to synthetic", exc)
                return self._synthetic_spike_fallback(runtime_ms)
        return {}

    def _synthetic_spike_fallback(self, runtime_ms: float) -> dict[int, int]:
        self._synthetic_fallback_count += 1
        spike_data: dict[int, int] = {}
        if self.polyp_population is None:
            return spike_data

        from coral_reef_spinnaker.polyp_neuron import PolypSummary

        summaries: Dict[int, Any] = {}
        for i, state in enumerate(self.polyp_population.states):
            if not state.is_alive:
                continue
            lam = max(0.1, state.trophic_health * runtime_ms / 1000.0)
            n_spikes = int(np.random.poisson(lam))
            feature = float(getattr(state, "sensory_drive", 0.0))
            weight = float(getattr(state, "predictive_readout_weight", 0.25))
            bias = float(getattr(state, "predictive_readout_bias", 0.0))
            pred = math.tanh(weight * feature + bias)
            state.last_backend_prediction = 0.0
            state.last_prediction_feature = feature
            state.current_prediction = pred
            state.last_output_signed_contribution = pred
            state.last_raw_rpe = pred
            spike_data[state.polyp_id] = n_spikes
            summaries[state.polyp_id] = PolypSummary(
                polyp_id=state.polyp_id,
                readout_rate=min(1.0, n_spikes / 10.0),
                activity_rate=min(1.0, n_spikes / 10.0),
                n_spikes_total=n_spikes,
                prediction=pred,
            )
        self._last_polyp_summaries = summaries
        return spike_data

    def backend_diagnostics(self) -> dict[str, Any]:
        """Return backend health counters for parity/CI harnesses."""
        backend_name = getattr(self.sim, "__name__", self.sim.__class__.__name__)
        return {
            "backend": backend_name,
            "sim_run_failures": int(self._sim_run_failure_count),
            "summary_read_failures": int(self._summary_read_failure_count),
            "synthetic_fallbacks": int(self._synthetic_fallback_count),
            "last_sim_run_error": self._last_sim_run_error,
            "last_backend_failure_stage": self._last_backend_failure_stage,
            "last_backend_exception_type": self._last_backend_exception_type,
            "last_backend_traceback": self._last_backend_traceback,
        }

    def _update_measurement(
        self,
        spike_data: dict[int, int],
        step: int,
    ) -> dict[str, float]:
        """Update per-stream MI, joint MI, and BOCPD."""
        for key in self.stream_keys:
            total = sum(
                spike_data.get(s.polyp_id, 0)
                for s in self.polyp_population.states
                if s.is_alive and key in getattr(s, "direct_stream_mask", set())
            )
            self.stream_buffers[key].append(float(total))

        for key in self.stream_keys:
            buf = self.stream_buffers[key]
            if len(buf) >= warmup_min_samples(d_eff=1, tau=1.0):
                mi = compute_ksg_mi(
                    np.array(list(buf)),
                    np.arange(len(buf)),
                    k=self.config.measurement.ksg_k,
                )
                self.stream_mi[key] = mi if mi is not None else 0.0
            else:
                self.stream_mi[key] = 0.0

        if len(self.stream_keys) > 1:
            buf_arrays = [
                np.array(self.stream_buffers[k], dtype=np.float64)
                for k in self.stream_keys
                if len(self.stream_buffers[k]) >= 3
            ]
            if len(buf_arrays) >= 2:
                joint_data = np.column_stack(buf_arrays)
                if joint_data.shape[0] >= warmup_min_samples(d_eff=joint_data.shape[1], tau=1.0):
                    joint_mi = compute_gcmi(joint_data[:, 0], joint_data[:, 1])
                    self.joint_mi_history.append(joint_mi)

        if self.bocpd is not None and len(self.joint_mi_history) > 0:
            latest_joint = float(self.joint_mi_history[-1])
            self.bocpd.update(latest_joint)
            self._last_changepoint_probability = self.bocpd.changepoint_probability

        return dict(self.stream_mi)

    def _run_learning(
        self,
        polyp_states: list,
        spike_data: dict[int, int],
        task_outcome: TaskOutcomeSurface,
        step: int,
        dt_ms: float,
    ) -> LearningResult:
        if self.learning_manager is None or self.network is None:
            return LearningResult()

        return self.learning_manager.step(
            polyp_states=polyp_states,
            spike_data={"spike_counts": spike_data},
            task_outcome=task_outcome,
            edges=self.network.edges,
            step_num=step,
            dt_ms=dt_ms,
            bocpd_changepoint_prob=self._last_changepoint_probability,
        )

    def _run_energy(
        self,
        polyp_states: list,
        stream_mi: dict[str, float],
        task_outcome: TaskOutcomeSurface,
        matured: tuple[float, float],
        step: int,
        dt: float,
    ) -> EnergyResult:
        if self.energy_manager is None or self.network is None:
            return EnergyResult()

        return self.energy_manager.step(
            polyp_states=polyp_states,
            edges=self.network.edges,
            stream_mi=stream_mi,
            task_outcome=ConsequenceSignal(
                immediate_signal=task_outcome.task_signal,
                horizon_signal=task_outcome.actual_return_5m,
                actual_value=task_outcome.actual_return_1m,
                prediction=task_outcome.colony_prediction,
                direction_correct=task_outcome.direction_correct,
                raw_dopamine=task_outcome.raw_dopamine,
                matured_gross_positive=matured[0],
                matured_net_positive=matured[1],
            ),
            matured_consequence=matured,
            dt=dt,
            step_num=step,
        )

    def _run_lifecycle(
        self,
        polyp_states: list,
        energy_result: EnergyResult,
        step: int,
        dt: float,
    ) -> list[LifecycleEvent]:
        if self.lifecycle_manager is None or self.network is None:
            return []

        return self.lifecycle_manager.step(
            polyp_states=polyp_states,
            edges=self.network.edges,
            energy_result=energy_result,
            maternal_reserve=getattr(self.energy_manager, "maternal_reserve", None),
            step_num=step,
            dt=dt,
        )

    def rebuild_spinnaker(self) -> None:
        """Full teardown/rebuild cycle for sPyNNaker dynamic topology.

        sPyNNaker cannot add or remove projections after ``sim.run()``.
        When the reef topology changes (polyps born/died, edges added/
        removed) this method:

        1. Saves all host-side state.
        2. Calls ``sim.end()``.
        3. Re-calls ``sim.setup()`` with the original kwargs.
        4. Re-creates ``PolypPopulation`` and restores polyps to their
           original slots with original IDs.
        5. Re-creates ``ReefNetwork`` and restores edges / gap junctions.
        6. Re-attachs all manager objects (learning, energy, lifecycle,
           trading, BOCPD).
        7. Re-creates hardware projections via ``sync_to_spinnaker()``.

        All synaptic weights are reset to their host-side cached values;
        learned STDP traces and membrane potentials are lost.
        """
        import copy
        from .backend_factory import get_backend_factory

        t0 = time.perf_counter()
        logger.info("rebuild_spinnaker: starting full teardown/rebuild")

        # ------------------------------------------------------------------
        # 1. Snapshot host-side state
        # ------------------------------------------------------------------
        # Shallow-copy states; deepcopy fails on PyNN Projection refs.
        # restore_polup overwrites hardware-specific attrs, so mutating
        # the original objects is safe (old population is dead).
        saved_states = list(self.polyp_population.states) if self.polyp_population else []
        saved_edges: Dict[Tuple[int, int], Any] = {}
        saved_gaps: Dict[frozenset, float] = {}
        saved_positions: Dict[int, Any] = {}
        saved_graph_distances: Dict[int, int] = {}
        if self.network is not None:
            saved_edges = {
                k: copy.deepcopy(v) for k, v in self.network.edges.items()
            }
            saved_gaps = dict(self.network.gap_junctions)
            saved_positions = {
                k: copy.deepcopy(v) for k, v in self.network.positions.items()
            }
            saved_graph_distances = dict(self.network.graph_distances)

        # Managers are pure-Python objects; keep references
        saved_learning = self.learning_manager
        saved_energy = self.energy_manager
        saved_lifecycle = self.lifecycle_manager
        saved_trading = self.trading_bridge
        saved_bocpd = self.bocpd

        saved_stream_buffers = self.stream_buffers
        saved_stream_mi = self.stream_mi
        saved_joint_mi = self.joint_mi_history
        saved_step_counter = self.step_counter
        saved_metrics = list(self.metrics_history)
        saved_accuracy_ema = self._accuracy_ema
        saved_founder_id = self.founder_id
        saved_last_cp = self._last_changepoint_probability
        saved_last_summaries = dict(self._last_polyp_summaries)
        saved_stream_keys = list(self.stream_keys)
        saved_spike_buffer = self.spike_buffer

        # ------------------------------------------------------------------
        # 2. Teardown
        # ------------------------------------------------------------------
        try:
            self.sim.end()
            logger.debug("rebuild_spinnaker: sim.end() completed")
        except Exception as exc:
            logger.warning("rebuild_spinnaker: sim.end() raised: %s", exc)

        # ------------------------------------------------------------------
        # 3. Re-setup
        # ------------------------------------------------------------------
        self.sim.setup(**self._setup_kwargs)
        logger.debug("rebuild_spinnaker: sim.setup() completed")

        # ------------------------------------------------------------------
        # 4. Re-create PolypPopulation & restore polyps
        # ------------------------------------------------------------------
        cfg_spin = self.config.spinnaker
        n_per_polyp = getattr(cfg_spin, "n_neurons_per_polyp", 32)
        n_input = getattr(cfg_spin, "n_input_per_polyp", 8)
        n_exc = getattr(cfg_spin, "n_exc_per_polyp", 16)
        n_inh = getattr(cfg_spin, "n_inh_per_polyp", 4)
        n_readout = getattr(cfg_spin, "n_readout_per_polyp", 4)
        max_pop = int(self.config.lifecycle.max_population_hard)

        self._backend_factory = get_backend_factory(self.sim)
        self.polyp_population = PolypPopulation(
            simulator=self.sim,
            max_polyps=max_pop,
            label="cra_polyps",
            neuron_type=PolypNeuronType(
                tau_m_ms=self.config.network.tau_m,
                v_rest_mV=self.config.network.v_rest,
                v_reset_mV=self.config.network.v_reset,
                v_thresh_mV=self.config.network.v_thresh,
                tau_refrac_ms=self.config.network.tau_refrac,
                tau_syn_e_ms=self.config.network.tau_syn_e,
                tau_syn_i_ms=self.config.network.tau_syn_i,
                cm_nF=self.config.network.cm,
            ),
            neurons_per_polyp=n_per_polyp,
            n_input=n_input,
            n_exc=n_exc,
            n_inh=n_inh,
            n_readout=n_readout,
            internal_conn_seed=getattr(cfg_spin, "internal_conn_seed", 42),
            backend_factory=self._backend_factory,
        )

        for state in saved_states:
            if state.is_alive and 0 <= state.slot_index < max_pop:
                self.polyp_population.restore_polyp(
                    state, state.slot_index, state.polyp_id
                )

        # ------------------------------------------------------------------
        # 5. Re-create ReefNetwork & restore topology
        # ------------------------------------------------------------------
        from .reef_network import ReefNetwork
        from .config_adapters import graph_config
        self.network = ReefNetwork(
            sim=self.sim,
            population=self.polyp_population,
            config=graph_config(self.config),
            backend_factory=self._backend_factory,
        )
        for (src_id, dst_id), edge in saved_edges.items():
            if getattr(edge, "is_pruned", False):
                continue
            self.network.add_edge(src_id, dst_id, weight=getattr(edge, "weight", 0.5))
        for pair, strength in saved_gaps.items():
            self.network.add_gap_junction(pair, strength)
        self.network.positions.update(saved_positions)
        self.network.graph_distances.update(saved_graph_distances)

        # ------------------------------------------------------------------
        # 6. Re-attach managers
        # ------------------------------------------------------------------
        self.learning_manager = saved_learning
        self.energy_manager = saved_energy
        self.lifecycle_manager = saved_lifecycle
        self.trading_bridge = saved_trading
        self.bocpd = saved_bocpd

        # ------------------------------------------------------------------
        # 7. Restore other organism-level state
        # ------------------------------------------------------------------
        self.stream_buffers = saved_stream_buffers
        self.stream_mi = saved_stream_mi
        self.joint_mi_history = saved_joint_mi
        self.step_counter = saved_step_counter
        self.metrics_history = saved_metrics
        self._accuracy_ema = saved_accuracy_ema
        self.founder_id = saved_founder_id
        self._last_changepoint_probability = saved_last_cp
        self._last_polyp_summaries = saved_last_summaries
        self.stream_keys = saved_stream_keys
        self.spike_buffer = saved_spike_buffer

        # ------------------------------------------------------------------
        # 8. Sync projections (creates STDP + neuromodulation on sPyNNaker)
        # ------------------------------------------------------------------
        self.network.sync_to_spinnaker()

        elapsed = (time.perf_counter() - t0) * 1000.0
        n_alive = sum(1 for s in self.polyp_population.states if s.is_alive)
        n_edges = sum(
            1 for e in self.network.edges.values()
            if getattr(e, "is_pruned", False) is False
        )
        self._last_rebuild_n_alive = n_alive
        self._last_rebuild_n_edges = n_edges
        logger.info(
            "rebuild_spinnaker: completed in %.1f ms (%d polyps, %d edges)",
            elapsed, n_alive, n_edges,
        )

    def _sync_to_spinnaker(self) -> None:
        if self.network is not None:
            try:
                self.network.sync_to_spinnaker()
            except Exception as exc:
                logger.warning("sync_to_spinnaker failed: %s", exc)

    def shutdown(self) -> None:
        logger.info("Organism shutdown at step %d", self.step_counter)
