"""
Task adapter interface for domain-agnostic CRA substrate.

Finance, robotics, audio, language, control, and other tasks implement
the TaskAdapter protocol. The CRA substrate only consumes Observation
and ConsequenceSignal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

import numpy as np

from .signals import ConsequenceSignal


@dataclass(frozen=True)
class Observation:
    """Domain-neutral observation for one stream/time step."""

    stream_id: str
    x: np.ndarray
    target: float | None = None
    timestamp: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class TaskAdapter(Protocol):
    """Domain adapter boundary.

    Implementations convert domain-specific observations into encoded
    channel vectors and produce consequence signals from predictions.
    """

    def encode(self, observation: Observation, n_channels: int) -> np.ndarray:
        ...

    def evaluate(
        self,
        prediction: float,
        observation: Observation,
        dt_seconds: float,
    ) -> ConsequenceSignal:
        ...


class DummyAdapter:
    """Minimal placeholder adapter for smoke testing."""

    def encode(self, observation: Observation, n_channels: int) -> np.ndarray:
        out = np.zeros(n_channels, dtype=float)
        out[0] = float(observation.x[0])
        return out

    def evaluate(
        self,
        prediction: float,
        observation: Observation,
        dt_seconds: float,
    ) -> ConsequenceSignal:
        target = 1.0 if observation.x[0] > 0 else -1.0
        correct = (prediction >= 0) == (target >= 0)
        return ConsequenceSignal(
            immediate_signal=1.0 if correct else -1.0,
            horizon_signal=target,
            actual_value=target,
            prediction=prediction,
            direction_correct=correct,
        )


@dataclass
class SignedClassificationAdapter:
    """Domain-neutral signed classification adapter.

    This is a concrete non-finance task adapter for binary classification,
    anomaly detection, or any control problem that can express the target as
    a signed scalar.  It proves the substrate boundary does not require market
    returns: observations are encoded as fixed-width channels, and consequences
    are just signed correctness signals.
    """

    positive_value: float = 1.0
    negative_value: float = -1.0
    zero_deadzone: float = 1e-12
    normalize_input: bool = True

    def encode(self, observation: Observation, n_channels: int) -> np.ndarray:
        if n_channels <= 0:
            raise ValueError("n_channels must be positive")

        x = np.asarray(observation.x, dtype=float).reshape(-1)
        if x.size == 0:
            raise ValueError("observation.x must contain at least one value")

        encoded = np.zeros(n_channels, dtype=float)
        n = min(n_channels, x.size)
        values = np.nan_to_num(x[:n], nan=0.0, posinf=1.0, neginf=-1.0)
        if self.normalize_input:
            scale = max(1.0, float(np.max(np.abs(values))))
            values = values / scale
        encoded[:n] = values
        return encoded

    def evaluate(
        self,
        prediction: float,
        observation: Observation,
        dt_seconds: float,
    ) -> ConsequenceSignal:
        del dt_seconds  # Classification consequences are step-local.
        target = self._target_from_observation(observation)
        prediction_sign = self._sign(prediction)
        target_sign = self._sign(target)
        correct = prediction_sign != 0 and prediction_sign == target_sign

        immediate = 0.0 if prediction_sign == 0 else (1.0 if correct else -1.0)
        return ConsequenceSignal(
            immediate_signal=immediate,
            horizon_signal=target,
            actual_value=target,
            prediction=prediction,
            direction_correct=correct,
            raw_dopamine=None,
            task_metrics={
                "classification_margin": abs(float(prediction)),
                "target_sign": float(target_sign),
            },
            metadata={
                "adapter": "signed_classification",
                "stream_id": observation.stream_id,
            },
        )

    def _target_from_observation(self, observation: Observation) -> float:
        if observation.target is not None:
            return (
                self.positive_value
                if observation.target >= 0
                else self.negative_value
            )
        x0 = float(np.asarray(observation.x, dtype=float).reshape(-1)[0])
        return self.positive_value if x0 >= 0 else self.negative_value

    def _sign(self, value: float) -> int:
        if value > self.zero_deadzone:
            return 1
        if value < -self.zero_deadzone:
            return -1
        return 0


@dataclass
class SensorControlAdapter:
    """Non-finance signed control adapter for Tier 4.11 domain transfer.

    The observation is a signed sensor error or cue. The target is a signed
    control consequence: positive means a positive correction was rewarded,
    negative means a negative correction was rewarded, and zero means no
    consequence arrived on this step. Delayed-control harnesses can therefore
    present a cue at step ``t`` and the reward at ``t + delay`` without leaking
    future labels into the observation.
    """

    sensor_scale: float = 1.0
    target_scale: float = 1.0
    zero_deadzone: float = 1e-12

    def encode(self, observation: Observation, n_channels: int) -> np.ndarray:
        if n_channels <= 0:
            raise ValueError("n_channels must be positive")
        x = np.asarray(observation.x, dtype=float).reshape(-1)
        if x.size == 0:
            raise ValueError("observation.x must contain at least one value")

        encoded = np.zeros(n_channels, dtype=float)
        encoded[0] = float(np.nan_to_num(x[0]) * self.sensor_scale)
        if n_channels > 1 and x.size > 1:
            n = min(n_channels - 1, x.size - 1)
            encoded[1 : 1 + n] = np.nan_to_num(x[1 : 1 + n])
        return encoded

    def evaluate(
        self,
        prediction: float,
        observation: Observation,
        dt_seconds: float,
    ) -> ConsequenceSignal:
        del dt_seconds
        target = 0.0 if observation.target is None else float(observation.target)
        target *= self.target_scale
        prediction_sign = self._sign(prediction)
        target_sign = self._sign(target)
        correct = prediction_sign != 0 and target_sign != 0 and prediction_sign == target_sign
        return ConsequenceSignal(
            immediate_signal=target,
            horizon_signal=target,
            actual_value=target,
            prediction=prediction,
            direction_correct=correct,
            raw_dopamine=None,
            task_metrics={
                "sensor_value": float(np.asarray(observation.x, dtype=float).reshape(-1)[0]),
                "target_sign": float(target_sign),
            },
            metadata={
                "adapter": "sensor_control",
                "stream_id": observation.stream_id,
            },
        )

    def _sign(self, value: float) -> int:
        if value > self.zero_deadzone:
            return 1
        if value < -self.zero_deadzone:
            return -1
        return 0
