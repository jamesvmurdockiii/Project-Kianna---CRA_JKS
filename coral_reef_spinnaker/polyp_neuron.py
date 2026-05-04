"""
Polyp Neuron Model for Coral Reef Architecture on SpiNNaker.

.. deprecated::
   This monolithic module has been split into three focused modules:

   - :mod:`coral_reef_spinnaker.polyp_state` — ``PolypState``,
     ``PolypSummary``, biological constants.
   - :mod:`coral_reef_spinnaker.polyp_plasticity` —
     ``DopamineModulatedWeightDependence``.
   - :mod:`coral_reef_spinnaker.polyp_population` — ``PolypNeuronType``,
     ``PolypPopulation``.

   All symbols are re-exported here for backward compatibility.
"""

from .polyp_plasticity import DopamineModulatedWeightDependence
from .polyp_population import PolypNeuronType, PolypPopulation
from .polyp_state import PolypState, PolypSummary

__all__ = [
    "DopamineModulatedWeightDependence",
    "PolypNeuronType",
    "PolypPopulation",
    "PolypState",
    "PolypSummary",
]
