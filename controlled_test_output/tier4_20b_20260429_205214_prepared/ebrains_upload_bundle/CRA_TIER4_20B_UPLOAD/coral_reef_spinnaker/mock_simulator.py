"""
Minimal PyNN-compatible simulator for testing without neuromorphic hardware.

Provides enough of the PyNN ``sim`` module API to exercise organism logic
in a pure-Python environment. Does **not** simulate spiking dynamics —
spike counts are generated synthetically by organism fallback code.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class MockSpikeTrain:
    """Stand-in for a Neo SpikeTrain."""

    def __init__(self, n_spikes: int, t_start: float = 0.0, t_stop: float = 1000.0) -> None:
        self.times = np.sort(np.random.uniform(t_start, t_stop, size=n_spikes))
        self.t_start = t_start
        self.t_stop = t_stop

    def __len__(self) -> int:
        return int(len(self.times))


class MockSegment:
    """Stand-in for a Neo Segment returned by Population.get_data()."""

    def __init__(self, n_cells: int, t_start: float = 0.0, t_stop: float = 1000.0) -> None:
        self.spiketrains = [
            MockSpikeTrain(np.random.poisson(5), t_start, t_stop)
            for _ in range(n_cells)
        ]
        self.analogsignals = []


class MockNeoBlock:
    """Stand-in for Neo Block with segments."""

    def __init__(self, n_cells: int, t_start: float = 0.0, t_stop: float = 1000.0) -> None:
        self.segments = [MockSegment(n_cells, t_start, t_stop)]


class MockPopulationView:
    """Slice/view into a MockPopulation."""

    def __init__(self, parent: "MockPopulation", indices):
        self.parent = parent
        self.indices = list(indices)

    def set(self, **parameters: Any) -> None:
        for key, value in parameters.items():
            for idx in self.indices:
                if key not in self.parent.cellparams:
                    self.parent.cellparams[key] = [None] * self.parent.size
                self.parent.cellparams[key][idx] = value


class MockPopulation:
    """Stand-in for a PyNN Population when no backend is available."""

    def __init__(
        self,
        size: int,
        cellclass: Any,
        cellparams: Optional[dict] = None,
        label: str = "mock_pop",
    ) -> None:
        self.size = int(size)
        self.cellclass = cellclass
        self.cellparams = cellparams or {}
        self.label = label
        self._recorded: set = set()

    def __len__(self) -> int:
        return self.size

    def __getitem__(self, index):
        if isinstance(index, slice):
            return MockPopulationView(self, range(*index.indices(self.size)))
        if isinstance(index, (list, tuple, np.ndarray)):
            return MockPopulationView(self, index)
        return MockPopulationView(self, [index])

    @property
    def all_cells(self) -> list:
        return list(range(self.size))

    def set(self, **parameters: Any) -> None:
        for key, value in parameters.items():
            if isinstance(value, list) and len(value) == self.size:
                self.cellparams[key] = list(value)
            else:
                self.cellparams[key] = [value] * self.size

    def record(self, variable: str, **kwargs: Any) -> None:
        self._recorded.add(variable)

    def get_data(self, variables: Optional[list] = None, clear: bool = False) -> MockNeoBlock:
        return MockNeoBlock(
            self.size,
            0.0,
            MockSimulator._current_time,
        )


class MockProjection:
    """Stand-in for a PyNN Projection when no backend is available."""

    def __init__(
        self,
        presynaptic_population: Any,
        postsynaptic_population: Any,
        connector: Any,
        synapse_type: Any = None,
        receptor_type: str = "excitatory",
        label: Optional[str] = None,
    ) -> None:
        self.pre = presynaptic_population
        self.post = postsynaptic_population
        self.connector = connector
        self.synapse_type = synapse_type
        self.receptor_type = receptor_type
        self.label = label or "mock_proj"
        self._weights: dict = {}

    def set(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get(self, attribute: str, format: str = "list") -> list:
        if attribute in {"weight", "weights"}:
            return []
        return []

    def getWeights(self, format: str = "list") -> list:
        return []


class MockStaticSynapse:
    """Mock static synapse type."""

    def __init__(self, weight: float = 0.0, delay: float = 1.0) -> None:
        self.weight = weight
        self.delay = delay


class MockFromListConnector:
    """Mock connector from an explicit connection list."""

    def __init__(self, conn_list: list, **kwargs: Any) -> None:
        self.conn_list = list(conn_list)


class MockOneToOneConnector:
    """Mock one-to-one connector."""

    pass


class MockAllToAllConnector:
    """Mock all-to-all connector."""

    def __init__(self, allow_self_connections: bool = True, **kwargs: Any) -> None:
        self.allow_self_connections = allow_self_connections


class MockSTDPMechanism:
    """Mock STDP mechanism."""

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockSpikePairRule:
    """Mock SpikePairRule timing dependence."""

    def __init__(self, tau_plus: float = 20.0, tau_minus: float = 20.0,
                 A_plus: float = 0.01, A_minus: float = 0.01, **kwargs: Any) -> None:
        self.tau_plus = tau_plus
        self.tau_minus = tau_minus
        self.A_plus = A_plus
        self.A_minus = A_minus
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockAdditiveWeightDependence:
    """Mock additive weight dependence."""

    def __init__(self, w_min: float = 0.0, w_max: float = 1.0, **kwargs: Any) -> None:
        self.w_min = w_min
        self.w_max = w_max
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockMultiplicativeWeightDependence:
    """Mock multiplicative weight dependence."""

    def __init__(self, w_min: float = 0.0, w_max: float = 1.0, **kwargs: Any) -> None:
        self.w_min = w_min
        self.w_max = w_max
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockSimulator:
    """Minimal PyNN-compatible simulator for testing without hardware."""

    class IF_curr_exp:
        def __init__(self, **kwargs):
            self.params = kwargs

    class SpikeSourceArray:
        def __init__(self, spike_times=None):
            self.spike_times = spike_times or []

    class SpikeSourcePoisson:
        def __init__(self, rate=0.0, start=0.0, duration=None):
            self.rate = rate
            self.start = start
            self.duration = duration

    Population = MockPopulation
    Projection = MockProjection
    StaticSynapse = MockStaticSynapse
    FromListConnector = MockFromListConnector
    OneToOneConnector = MockOneToOneConnector
    AllToAllConnector = MockAllToAllConnector
    STDPMechanism = MockSTDPMechanism
    SpikePairRule = MockSpikePairRule
    AdditiveWeightDependence = MockAdditiveWeightDependence
    MultiplicativeWeightDependence = MockMultiplicativeWeightDependence

    _is_setup: bool = False
    _timestep: float = 1.0
    _current_time: float = 0.0

    @classmethod
    def setup(cls, timestep: float = 1.0, **kwargs: Any) -> "MockSimulator":
        cls._is_setup = True
        cls._timestep = float(timestep)
        cls._current_time = 0.0
        logger.info("MockSimulator.setup(timestep=%.2f ms)", cls._timestep)
        return cls

    @classmethod
    def end(cls, **kwargs: Any) -> None:
        cls._is_setup = False
        logger.info("MockSimulator.end()")

    @classmethod
    def run(cls, runtime: float, **kwargs: Any) -> None:
        if not cls._is_setup:
            raise RuntimeError("MockSimulator.setup() must be called before run()")
        cls._current_time += float(runtime)
        logger.debug("MockSimulator.run(%.1f ms) -> t=%.1f ms", runtime, cls._current_time)

    @classmethod
    def get_time_step(cls) -> float:
        return cls._timestep

    @classmethod
    def get_current_time(cls) -> float:
        return cls._current_time

    @classmethod
    def set_number_of_neurons_per_core(cls, neuron_type: Any, n: int) -> None:
        pass

    @classmethod
    def record_v(cls, source: Any, filename: str) -> None:
        """No-op voltage recording."""
        pass

    @classmethod
    def record_gsyn(cls, source: Any, filename: str) -> None:
        """No-op synaptic conductance recording."""
        pass
