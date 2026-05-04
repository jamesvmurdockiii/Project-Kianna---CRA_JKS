"""Runtime-mode contracts for CRA hardware execution.

The current proven hardware path is a host-controlled step loop:

``set input -> sim.run(step) -> read spikes -> host learning``.

Tier 4.17 introduces the vocabulary needed to move away from that expensive
loop without pretending the future work is already solved. Tier 4.17b validated
the local mechanics for scheduled input, binned readback, and host replay. The
Tier 4.16 runner then owns the first hardware use of that contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Iterable


RUNTIME_MODES = ("step", "chunked", "continuous")
LEARNING_LOCATIONS = ("host", "hybrid", "on_chip")


@dataclass(frozen=True)
class RuntimeExecutionPlan:
    """Validated runtime/learning placement contract."""

    runtime_mode: str = "step"
    learning_location: str = "host"
    chunk_size_steps: int = 1
    total_steps: int = 120
    dt_seconds: float = 0.05
    implemented: bool = True
    implementation_stage: str = "current_step_host_loop"
    blockers: tuple[str, ...] = field(default_factory=tuple)

    @property
    def sim_run_calls(self) -> int:
        return int(ceil(self.total_steps / self.chunk_size_steps))

    @property
    def simulated_ms_per_chunk(self) -> float:
        return float(self.chunk_size_steps) * float(self.dt_seconds) * 1000.0

    @property
    def call_reduction_factor(self) -> float:
        if self.sim_run_calls <= 0:
            return 0.0
        return float(self.total_steps) / float(self.sim_run_calls)

    @property
    def learning_update_interval_steps(self) -> int:
        return self.chunk_size_steps


def validate_runtime_values(
    *,
    runtime_mode: str,
    learning_location: str,
    chunk_size_steps: int,
    total_steps: int,
    dt_seconds: float,
) -> None:
    """Raise ``ValueError`` when a runtime contract is malformed."""

    if runtime_mode not in RUNTIME_MODES:
        raise ValueError(f"unknown runtime_mode={runtime_mode!r}")
    if learning_location not in LEARNING_LOCATIONS:
        raise ValueError(f"unknown learning_location={learning_location!r}")
    if int(chunk_size_steps) < 1:
        raise ValueError("chunk_size_steps must be >= 1")
    if int(total_steps) < 1:
        raise ValueError("total_steps must be >= 1")
    if float(dt_seconds) <= 0.0:
        raise ValueError("dt_seconds must be positive")
    if runtime_mode == "step" and int(chunk_size_steps) != 1:
        raise ValueError("step runtime mode requires chunk_size_steps=1")


def make_runtime_plan(
    *,
    runtime_mode: str = "step",
    learning_location: str = "host",
    chunk_size_steps: int = 1,
    total_steps: int = 120,
    dt_seconds: float = 0.05,
) -> RuntimeExecutionPlan:
    """Build a conservative implementation-status record.

    ``chunked`` + ``host`` is the first intended bridge. Tier 4.17b validates
    the mechanics locally; Tier 4.16 uses it for the repaired hardware probe.
    ``hybrid`` and ``on_chip`` are deliberately marked future stages so the repo
    cannot overclaim them.
    """

    validate_runtime_values(
        runtime_mode=runtime_mode,
        learning_location=learning_location,
        chunk_size_steps=chunk_size_steps,
        total_steps=total_steps,
        dt_seconds=dt_seconds,
    )

    blockers: tuple[str, ...] = ()
    implemented = True
    stage = "current_step_host_loop"

    if runtime_mode == "chunked" and learning_location == "host":
        implemented = True
        stage = "chunked_host_stepcurrent_binned_replay"
        blockers = ()
    elif runtime_mode == "continuous" or learning_location in {"hybrid", "on_chip"}:
        implemented = False
        stage = "future_custom_runtime"
        blockers = (
            "custom_c_or_backend_native_closed_loop",
            "on_chip_or_hybrid_credit_assignment_state",
            "hardware_provenance_for_continuous_run",
        )

    return RuntimeExecutionPlan(
        runtime_mode=runtime_mode,
        learning_location=learning_location,
        chunk_size_steps=int(chunk_size_steps),
        total_steps=int(total_steps),
        dt_seconds=float(dt_seconds),
        implemented=implemented,
        implementation_stage=stage,
        blockers=blockers,
    )


def chunk_ranges(total_steps: int, chunk_size_steps: int) -> list[tuple[int, int]]:
    """Return half-open ``[start, stop)`` chunk ranges."""

    if int(total_steps) < 1:
        raise ValueError("total_steps must be >= 1")
    if int(chunk_size_steps) < 1:
        raise ValueError("chunk_size_steps must be >= 1")
    ranges: list[tuple[int, int]] = []
    start = 0
    while start < int(total_steps):
        stop = min(int(total_steps), start + int(chunk_size_steps))
        ranges.append((start, stop))
        start = stop
    return ranges


def estimate_plans(
    *,
    total_steps: int,
    dt_seconds: float,
    chunk_sizes: Iterable[int],
) -> list[RuntimeExecutionPlan]:
    """Return step/chunked host plans for a chunk-size sweep."""

    plans: list[RuntimeExecutionPlan] = []
    seen: set[int] = set()
    for size in chunk_sizes:
        size = int(size)
        if size in seen:
            continue
        seen.add(size)
        mode = "step" if size == 1 else "chunked"
        plans.append(
            make_runtime_plan(
                runtime_mode=mode,
                learning_location="host",
                chunk_size_steps=size,
                total_steps=total_steps,
                dt_seconds=dt_seconds,
            )
        )
    return plans
