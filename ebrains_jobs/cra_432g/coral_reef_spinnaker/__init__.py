"""
Coral Reef Architecture for SpiNNaker
=====================================

A neuromorphic implementation of the Coral Reef Architecture (CRA) for
the SpiNNaker platform using PyNN.

CRA is a multi-agent neural substrate in which a colony of autonomous
polyps (spiking neurons) processes sequential input streams, exchanges
messages over a directed graph, updates through dopamine-modulated STDP,
and is selected through a scalar trophic-survival economy rather than
backpropagation.

Biological First Principles
---------------------------
- **Scalar trophic-health economy** (no backpropagation)
  Energy flows from sensory streams -> polyps -> outcomes, with
  retrograde trophic feedback on active incoming edges. Polyps survive
  or perish based solely on their scalar trophic_health balance.

- **Cyclin-D gated reproduction** (Morgan 1995)
  Polyps reproduce when cyclin_d exceeds the G1/S checkpoint threshold
  (0.5), directly analogous to the cell-cycle commitment point in
  proliferating eukaryotic cells.

- **BAX-driven apoptosis** (Katz & Shatz 1996)
  Polyps die when trophic_health falls below apoptosis_threshold,
  modelling activity-dependent synaptic pruning observed during
  vertebrate visual system development.

- **Dopamine-modulated STDP** (Fremaux et al. 2010)
  Synaptic potentiation is gated by dopamine concentration rather than
  a global loss gradient, giving reward-modulated Hebbian plasticity
  with eligibility traces.

- **Winner-take-all competitive readout** (Desimone & Duncan 1995)
  A k-WTA circuit selects the k most active polyps at each timestep,
  implementing biased competition for neural representation.

- **Three-channel energy capture** (neurotrophic theory)
  Each polyp draws energy from: (1) sensory capture from direct
  exteroceptive stream connections, (2) outcome capture from task
  consequences, and (3) retrograde support from downstream polyps
  that spent their trophic budget upstream.

- **Maternal-to-autonomous handoff** (neurotrophic theory)
  Founder polyps receive maternal_reserve support that gradually
tapers as they establish their own trophic capture pathways,
  analogous to the developmental transition from maternal to
autonomous neurotrophic support.

Package Structure
-----------------
The package is organised into 10 core modules totalling ~12,400 lines::

    coral_reef_spinnaker/
        __init__.py          -- Package entry point (this file)
        config.py            -- All CRA parameters as dataclasses
        measurement.py       -- MI estimation (KSG) + BOCPD
        polyp_state.py       -- PolypState / PolypSummary dataclasses
        polyp_plasticity.py  -- Dopamine-modulated STDP weight dependence
        polyp_population.py  -- PyNN Population + PolypNeuronType factory
        polyp_neuron.py      -- Backward-compat re-export shim
        reef_network.py      -- Graph topology + motif definitions
        energy_manager.py    -- 3-channel trophic economy
        lifecycle.py         -- Birth / death / maternal handoff
        learning_manager.py  -- Dopamine STDP + calcification + WTA
        trading_bridge.py    -- Task consequence wrapper
        organism.py          -- High-level Organism orchestrator
        spinnaker_runner.py  -- SpiNNaker execution harness
        demo.py              -- Runnable example simulation

Usage
-----
    from coral_reef_spinnaker import Organism, ReefConfig

    config = ReefConfig.default()
    organism = Organism(config)
    organism.initialize(stream_keys=['EUR/USD'])

    for step, market_return in enumerate(market_data):
        metrics = organism.train_step(market_return)
        print(f"Step {step}: capital={metrics.capital:.4f}, "
              f"population={metrics.n_alive}, "
              f"accuracy={metrics.mean_directional_accuracy_ema:.3f}")

Backends
--------
The package attempts to use the following PyNN backends in order:

1. **sPyNNaker**  -- SpiNNaker neuromorphic hardware (preferred)
2. **NEST**       -- Event-driven simulation on CPU clusters
3. **Brian2**     -- Python-based spiking neural network simulator
4. **MockSimulator** -- Pure-Python fallback with no external deps

Dependencies
------------
- PyNN (with sPyNNaker, NEST, Brian2, or mock backend)
- numpy, scipy
- (optional) matplotlib for visualization in demo.py

Version: 0.1.0-spinnaker

References
----------
.. [1] Desimone, R. & Duncan, J. (1995). Neural mechanisms of
   selective visual attention. *Annual Review of Neuroscience*,
   18(1), 193-222.
.. [2] Katz, L. C. & Shatz, C. J. (1996). Synaptic activity and
   the construction of cortical circuits. *Science*, 274(5290),
   1133-1138.
.. [3] Fremaux, N., Sprekeler, H. & Gerstner, W. (2010).
   Functional requirements for reward-modulated spike-timing-
   dependent plasticity. *Journal of Neuroscience*, 30(40),
   13326-13337.
.. [4] Morgan, D. O. (1995). Principles of CDK regulation.
   *Nature*, 374(6518), 131-134.
.. [5] Kraskov, A., Stogbauer, H. & Grassberger, P. (2004).
   Estimating mutual information. *Physical Review E*, 69(6),
   066138.
.. [6] Adams, R. P. & MacKay, D. J. (2007). Bayesian online
   changepoint detection. *arXiv preprint arXiv:0710.3742*.
.. [7] Ince, R. A., Giordano, B. L., Kayser, C. et al. (2017).
   A novel estimator for mutual information. *PLOS Computational
   Biology*, 13(1), e1005036.
"""

from __future__ import annotations

__version__ = "0.1.0-spinnaker"

# ---------------------------------------------------------------------------
# Public API — version & dependency helpers
# ---------------------------------------------------------------------------

def get_version() -> str:
    """Return the current CRA-SpiNNaker package version string.

    Returns
    -------
    str
        Version in ``"MAJOR.MINOR.PATCH-backend"`` format, e.g.
        ``"0.1.0-spinnaker"``.
    """
    return __version__


def check_dependencies() -> dict:
    """Check which optional / required backends are importable.

    This is useful for CI smoke tests and for diagnosing which PyNN
    backend is selected at runtime.

    Returns
    -------
    dict
        Dictionary with the following boolean flags::

            {
                'pyNN':        bool,   # PyNN core available
                'spiNNaker':   bool,   # sPyNNaker backend
                'nest':        bool,   # pyNN.nest backend
                'brian2':      bool,   # pyNN.brian2 backend
                'numpy':       bool,   # NumPy arrays / rng
                'scipy':       bool,   # SciPy (used in KSG MI estimation)
                'matplotlib':  bool,   # Optional plotting (demo.py)
            }
    """
    deps = {
        "pyNN": False,
        "spiNNaker": False,
        "nest": False,
        "brian2": False,
        "numpy": False,
        "scipy": False,
        "matplotlib": False,
    }

    # NumPy — required by nearly every module
    try:
        import numpy  # noqa: F401

        deps["numpy"] = True
    except Exception:
        pass

    # SciPy — used by measurement (KSG MI estimation)
    try:
        import scipy  # noqa: F401

        deps["scipy"] = True
    except Exception:
        pass

    # Matplotlib — optional, used by demo.py visualisations
    try:
        import matplotlib  # noqa: F401

        deps["matplotlib"] = True
    except Exception:
        pass

    # PyNN core
    try:
        import pyNN  # noqa: F401

        deps["pyNN"] = True
    except Exception:
        return deps  # If PyNN is absent, nothing else matters

    # --- PyNN backends (in preference order) ---
    try:
        import pyNN.spiNNaker  # noqa: F401

        deps["spiNNaker"] = True
    except Exception:
        pass

    try:
        import pyNN.nest  # noqa: F401

        deps["nest"] = True
    except Exception:
        pass

    try:
        import pyNN.brian2  # noqa: F401

        deps["brian2"] = True
    except Exception:
        pass

    return deps


# ---------------------------------------------------------------------------
# Lazy imports via module-level __getattr__
# ---------------------------------------------------------------------------
# We use PEP-562 lazy loading so that ``from coral_reef_spinnaker import
# Organism`` works without eagerly importing all sub-modules (which may
# in turn try to import pyNN / numpy).  This keeps import time low and
# avoids hard failures when only a subset of dependencies are installed.
# ---------------------------------------------------------------------------

# Registry:  public_name -> (module_path, class_name)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # High-level orchestrators
    "Organism": ("coral_reef_spinnaker.organism", "Organism"),
    # Configuration (primary definition in config.py)
    "ReefConfig": ("coral_reef_spinnaker.config", "ReefConfig"),
    "EnergyConfig": ("coral_reef_spinnaker.config", "EnergyConfig"),
    "LifecycleConfig": ("coral_reef_spinnaker.config", "LifecycleConfig"),
    "LearningConfig": ("coral_reef_spinnaker.config", "LearningConfig"),
    "NetworkConfig": ("coral_reef_spinnaker.config", "NetworkConfig"),
    "SpiNNakerConfig": ("coral_reef_spinnaker.config", "SpiNNakerConfig"),
    "MeasurementConfig": ("coral_reef_spinnaker.config", "MeasurementConfig"),
    # Configuration (reef_network.py also defines some config classes)
    "ReefNetworkConfig": ("coral_reef_spinnaker.reef_network", "ReefNetworkConfig"),
    # Measurement
    "BayesianOnlineChangepointDetector": ("coral_reef_spinnaker.measurement", "BayesianOnlineChangepointDetector"),
    # Polyp neuron
    "PolypState": ("coral_reef_spinnaker.polyp_neuron", "PolypState"),
    "PolypNeuronType": ("coral_reef_spinnaker.polyp_neuron", "PolypNeuronType"),
    "PolypPopulation": ("coral_reef_spinnaker.polyp_neuron", "PolypPopulation"),
    "DopamineModulatedWeightDependence": ("coral_reef_spinnaker.polyp_neuron", "DopamineModulatedWeightDependence"),
    # Reef network
    "ReefNetwork": ("coral_reef_spinnaker.reef_network", "ReefNetwork"),
    "ReefEdge": ("coral_reef_spinnaker.reef_network", "ReefEdge"),
    "EdgeType": ("coral_reef_spinnaker.reef_network", "EdgeType"),
    "ReefGraphState": ("coral_reef_spinnaker.reef_network", "ReefGraphState"),
    # Energy manager
    "EnergyManager": ("coral_reef_spinnaker.energy_manager", "EnergyManager"),
    "EnergyResult": ("coral_reef_spinnaker.energy_manager", "EnergyResult"),
    "MaternalReserve": ("coral_reef_spinnaker.energy_manager", "MaternalReserve"),
    "TaskOutcomeSurface": ("coral_reef_spinnaker.trading_bridge", "TaskOutcomeSurface"),
    # Lifecycle
    "LifecycleManager": ("coral_reef_spinnaker.lifecycle", "LifecycleManager"),
    "LineageRecord": ("coral_reef_spinnaker.lifecycle", "LineageRecord"),
    "LifecycleEvent": ("coral_reef_spinnaker.lifecycle", "LifecycleEvent"),
    "GrowthBudget": ("coral_reef_spinnaker.lifecycle", "GrowthBudget"),
    # Learning manager
    "LearningManager": ("coral_reef_spinnaker.learning_manager", "LearningManager"),
    "STDPUpdate": ("coral_reef_spinnaker.learning_manager", "STDPUpdate"),
    "CalcificationState": ("coral_reef_spinnaker.learning_manager", "CalcificationState"),
    "PendingHorizon": ("coral_reef_spinnaker.learning_manager", "PendingHorizon"),
    # Trading bridge
    "TradingBridge": ("coral_reef_spinnaker.trading_bridge", "TradingBridge"),
    "PaperTrader": ("coral_reef_spinnaker.trading_bridge", "PaperTrader"),
    "TradingConfig": ("coral_reef_spinnaker.trading_bridge", "TradingConfig"),
    # Domain-neutral task adapters
    "TaskAdapter": ("coral_reef_spinnaker.task_adapter", "TaskAdapter"),
    "Observation": ("coral_reef_spinnaker.task_adapter", "Observation"),
    "DummyAdapter": ("coral_reef_spinnaker.task_adapter", "DummyAdapter"),
    "SignedClassificationAdapter": ("coral_reef_spinnaker.task_adapter", "SignedClassificationAdapter"),
    "SensorControlAdapter": ("coral_reef_spinnaker.task_adapter", "SensorControlAdapter"),
    "ConsequenceSignal": ("coral_reef_spinnaker.signals", "ConsequenceSignal"),
    "GenericTaskOutcomeSurface": ("coral_reef_spinnaker.signals", "GenericTaskOutcomeSurface"),
    # Runtime planning
    "RuntimeExecutionPlan": ("coral_reef_spinnaker.runtime_modes", "RuntimeExecutionPlan"),
    "make_runtime_plan": ("coral_reef_spinnaker.runtime_modes", "make_runtime_plan"),
    "chunk_ranges": ("coral_reef_spinnaker.runtime_modes", "chunk_ranges"),
    # Mock simulator (fallback when no real backend is available)
    "MockSimulator": ("coral_reef_spinnaker.mock_simulator", "MockSimulator"),
}

# ---------------------------------------------------------------------------
# Eagerly import the config module because it is lightweight (numpy-only)
# and most entry points need ReefConfig immediately.  Everything else
# stays lazy so that we don't pull in pyNN unless truly required.
# ---------------------------------------------------------------------------

try:
    from coral_reef_spinnaker.config import ReefConfig
    from coral_reef_spinnaker.config import EnergyConfig
    from coral_reef_spinnaker.config import LifecycleConfig
    from coral_reef_spinnaker.config import LearningConfig
    from coral_reef_spinnaker.config import NetworkConfig
    from coral_reef_spinnaker.config import SpiNNakerConfig
    from coral_reef_spinnaker.config import MeasurementConfig
except Exception:
    # If config.py itself fails (e.g. numpy missing), leave ReefConfig
    # as a lazy import so the package namespace is at least importable.
    pass


def __getattr__(name: str):
    """Lazy-load public symbols on first attribute access.

    Raises
    ------
    AttributeError
        If *name* is not part of the public API.
    ImportError
        If the underlying module cannot be imported (missing
        dependencies, etc.).
    """
    if name not in _LAZY_IMPORTS:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}. "
            f"Available names: {', '.join(sorted(_LAZY_IMPORTS.keys()))}"
        )

    module_path, class_name = _LAZY_IMPORTS[name]
    try:
        mod = __import__(module_path, fromlist=[class_name])
    except ImportError as exc:
        raise ImportError(
            f"Cannot lazy-import {name!r} from {module_path!r}. "
            f"Original error: {exc}"
        ) from exc
    return getattr(mod, class_name)


# ---------------------------------------------------------------------------
# __all__ — controls ``from coral_reef_spinnaker import *``
# ---------------------------------------------------------------------------

__all__ = [
    # Version
    "__version__",
    "get_version",
    "check_dependencies",
    # Config (always available)
    "ReefConfig",
    "EnergyConfig",
    "LifecycleConfig",
    "LearningConfig",
    "NetworkConfig",
    "SpiNNakerConfig",
    "MeasurementConfig",
    # Orchestrators (lazy)
    "Organism",
    # Network (lazy)
    "ReefNetwork",
    "ReefEdge",
    "EdgeType",
    "ReefGraphState",
    "ReefNetworkConfig",
    # Polyp (lazy)
    "PolypState",
    "PolypNeuronType",
    "PolypPopulation",
    "DopamineModulatedWeightDependence",
    # Energy (lazy)
    "EnergyManager",
    "EnergyResult",
    "MaternalReserve",
    "TaskOutcomeSurface",
    # Lifecycle (lazy)
    "LifecycleManager",
    "LineageRecord",
    "LifecycleEvent",
    "GrowthBudget",
    # Learning (lazy)
    "LearningManager",
    "STDPUpdate",
    "CalcificationState",
    "PendingHorizon",
    # Measurement (lazy)
    "BayesianOnlineChangepointDetector",
    # Trading (lazy)
    "TradingBridge",
    "PaperTrader",
    "TradingConfig",
    # Task adapters (lazy)
    "TaskAdapter",
    "Observation",
    "DummyAdapter",
    "SignedClassificationAdapter",
    "SensorControlAdapter",
    "ConsequenceSignal",
    "GenericTaskOutcomeSurface",
    # Runtime planning (lazy)
    "RuntimeExecutionPlan",
    "make_runtime_plan",
    "chunk_ranges",
    # Fallback simulator (lazy)
    "MockSimulator",
]
