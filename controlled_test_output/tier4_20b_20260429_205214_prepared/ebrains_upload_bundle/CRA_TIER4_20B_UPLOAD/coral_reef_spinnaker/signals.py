"""
Domain-neutral signals for the Coral Reef Architecture substrate.

The substrate should not know whether streams are finance, robotics,
audio, text, or sensors. It only consumes Observation and produces
ConsequenceSignal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np


@dataclass
class ConsequenceSignal:
    """Domain-neutral consequence signal consumed by CRA learning and ecology.

    The substrate should not know whether this came from trading, robotics,
    control, classification, prediction, or another sequential task.
    """

    immediate_signal: float = 0.0
    horizon_signal: float = 0.0
    actual_value: float = 0.0
    prediction: float = 0.0
    direction_correct: bool = False

    # Learning
    raw_dopamine: float | None = None

    # Outcome-energy minting
    matured_gross_positive: float = 0.0
    matured_net_positive: float = 0.0

    # Optional task-specific telemetry
    task_metrics: dict[str, float] = field(default_factory=dict)
    metadata: Mapping[str, Any] | None = None


# Compatibility alias: the concrete TaskOutcomeSurface used at runtime
# is defined in trading_bridge.py (finance-specific, 13 fields).
# ConsequenceSignal is the domain-neutral substrate contract.
# New code should import TaskOutcomeSurface from trading_bridge directly.
TaskOutcomeSurface = ConsequenceSignal


@dataclass
class GenericTaskOutcomeSurface:
    """Domain-neutral step outcome with the fields CRA subsystems consume.

    The historical implementation used ``trading_bridge.TaskOutcomeSurface`` as
    the concrete runtime object.  Learning and ecology only need a signed
    consequence, the executed prediction/action, and a few telemetry fields, so
    non-finance adapters can use this surface without constructing a trading
    bridge.
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
    task_name: str = "generic"
    task_metrics: dict[str, float] = field(default_factory=dict)
    metadata: Mapping[str, Any] | None = None

    @property
    def held_position(self) -> float:
        """Domain-neutral alias for the executed signed action."""
        return self.position_size
