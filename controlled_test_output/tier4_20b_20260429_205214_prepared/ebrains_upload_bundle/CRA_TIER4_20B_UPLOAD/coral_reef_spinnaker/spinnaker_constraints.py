"""SpiNNaker hardware constraint checker for software simulation.

Validates that the colony's topology, connectivity, and resource usage
remain within the physical limits of the SpiNNaker neuromorphic platform.
This catches hardware-violating configurations *before* deployment to
silicon, saving expensive board-time debugging.

References
----------
- Furber et al. (2014) The SpiNNaker Project. Proc. IEEE 102:652-665.
- sPyNNaker documentation: https://spinnakermanchester.github.io/
"""

from __future__ import annotations

import logging
import math
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SpiNNaker hardware constants
# ---------------------------------------------------------------------------

CORES_PER_CHIP = 18
SYSTEM_CORES_PER_CHIP = 1
USABLE_CORES_PER_CHIP = CORES_PER_CHIP - SYSTEM_CORES_PER_CHIP  # 17

# SDRAM per core (bytes).  Each SpiNNaker core has 128 KB SRAM total.
# The monitor / system software reserve ~10 KB, leaving ~118 KB for user
# data (synaptic rows + neuron state).  This value is the canonical
# budget used by sPyNNaker and matches ReefConfig.spinnaker.sdram_per_core_bytes.
SDRAM_PER_CORE_BYTES = 118 * 1024  # 118 KB

# Synaptic row overhead (bytes per connection in sPyNNaker fixed format).
# Each synaptic word = 16 bits weight + 16 bits delay/target = 4 bytes.
BYTES_PER_SYNAPSE = 4

# Routing table entries per chip.  SpiNNaker multicast router has 1024
# entries, but some are reserved for system use.
MAX_ROUTING_ENTRIES_PER_CHIP = 1024
SYSTEM_RESERVED_ROUTING_ENTRIES = 32
USABLE_ROUTING_ENTRIES_PER_CHIP = (
    MAX_ROUTING_ENTRIES_PER_CHIP - SYSTEM_RESERVED_ROUTING_ENTRIES
)

# Weight precision: sPyNNaker uses 16-bit fixed-point with 15 fractional
# bits (range [-1.0, +1.0 - 2^-15]).  Weights outside this range are
# saturated.
WEIGHT_FIXED_FRACTIONAL_BITS = 15
WEIGHT_FIXED_SCALE = 1 << WEIGHT_FIXED_FRACTIONAL_BITS  # 32768
WEIGHT_MIN = -1.0
WEIGHT_MAX = 1.0 - 1.0 / WEIGHT_FIXED_SCALE


def clip_weight_for_hardware(weight: float, fixed_scale: int = WEIGHT_FIXED_SCALE) -> float:
    """Clip a float weight to the range representable on SpiNNaker hardware.

    sPyNNaker uses 16-bit fixed-point with *fixed_scale* fractional bits.
    The representable range is ``[-1.0, +1.0 - 1/fixed_scale]``.
    Values outside this range are saturated (clipped).

    This is a standalone function so that ``backend_factory.py`` and
    ``reef_network.py`` can enforce the hardware limit without needing
    a full ``SpiNNakerConstraintChecker`` instance.

    Parameters
    ----------
    weight : float
        The weight value to clip.
    fixed_scale : int, optional
        Fixed-point scale factor.  Default ``32768`` (15 fractional bits).

    Returns
    -------
    float
        The clipped weight.
    """
    w_max = 1.0 - 1.0 / fixed_scale
    return max(-1.0, min(w_max, float(weight)))


def quantize_weight_for_hardware(
    weight: float, fixed_scale: int = WEIGHT_FIXED_SCALE
) -> float:
    """Quantize a float weight to SpiNNaker fixed-point and back.

    This applies :func:`clip_weight_for_hardware` then rounds to the
    nearest fixed-point step.

    Parameters
    ----------
    weight : float
        The weight value to quantize.
    fixed_scale : int, optional
        Fixed-point scale factor.  Default ``32768``.

    Returns
    -------
    float
        The quantized weight.
    """
    w = clip_weight_for_hardware(weight, fixed_scale)
    fixed = round(w * fixed_scale)
    return fixed / fixed_scale

# Real-time constraint: each 1 ms timestep must finish within 1 ms wall
# clock.  sPyNNaker targets real-time factor = 1.0.
REAL_TIME_TIMESTEP_MS = 1.0

# Projection rebuild latency (seconds).  Creating or destroying a PyNN
# Projection on SpiNNaker triggers a chip-wide DMA + router
# reconfiguration.  Typical measured latency is 0.5–2.0 s depending on
# network size.
PROJECTION_REBUILD_LATENCY_S = 1.0

# Max neurons per core (sPyNNaker constraint).
DEFAULT_MAX_NEURONS_PER_CORE = 255


# ---------------------------------------------------------------------------
# Constraint violation record
# ---------------------------------------------------------------------------

@dataclass
class ConstraintViolation:
    """A single hardware constraint violation."""

    category: str  # "neurons", "sdram", "routing", "timing", "weight", "rebuild"
    severity: str  # "warning" or "error"
    message: str
    current: float
    limit: float
    details: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Constraint checker
# ---------------------------------------------------------------------------

class SpiNNakerConstraintChecker:
    """Validate colony state against SpiNNaker hardware limits.

    Usage
    -----
    checker = SpiNNakerConstraintChecker(
        max_neurons_per_core=255,
        num_chips=1,
        sdram_per_core=118*1024,
    )
    checker.check_population(n_neurons=200)  # OK
    checker.check_population(n_neurons=300)  # Violation!

    The checker is stateful: it tracks cumulative routing entries and
    synaptic memory across the colony so that multi-step growth can be
    validated incrementally.
    """

    def __init__(
        self,
        max_neurons_per_core: int = DEFAULT_MAX_NEURONS_PER_CORE,
        num_chips: int = 1,
        sdram_per_core: int = SDRAM_PER_CORE_BYTES,
        routing_entries_per_chip: int = USABLE_ROUTING_ENTRIES_PER_CHIP,
        weight_fixed_scale: int = WEIGHT_FIXED_SCALE,
        enable: bool = True,
    ) -> None:
        self.max_neurons_per_core = max_neurons_per_core
        self.num_chips = num_chips
        self.sdram_per_core = sdram_per_core
        self.routing_entries_per_chip = routing_entries_per_chip
        self.weight_fixed_scale = weight_fixed_scale
        self.enable = enable

        # Counters (incrementally updated)
        self.total_neurons: int = 0
        self.total_projections: int = 0
        self._routing_entries_used: int = 0
        self._synaptic_bytes_used: int = 0
        self._violations: List[ConstraintViolation] = []
        self._rebuild_count: int = 0
        self._rebuild_cost_s: float = 0.0

    # ------------------------------------------------------------------
    # Population (neuron-per-core) checks
    # ------------------------------------------------------------------

    def check_population(self, n_neurons: int, label: str = "") -> List[ConstraintViolation]:
        """Check whether *n_neurons* fits within per-core limits.

        Returns any new violations (also stored internally).
        """
        if not self.enable:
            return []

        self.total_neurons = n_neurons
        cores_needed = math.ceil(n_neurons / max(1, self.max_neurons_per_core))
        max_cores = self.num_chips * USABLE_CORES_PER_CHIP

        violations: List[ConstraintViolation] = []

        # Per-core limit
        if n_neurons > self.max_neurons_per_core:
            # This is only an error if we try to map to a single core.
            # sPyNNaker automatically partitions, so we warn rather than
            # error for multi-core fits.
            if cores_needed > max_cores:
                v = ConstraintViolation(
                    category="neurons",
                    severity="error",
                    message=(
                        f"Population '{label}' needs {n_neurons} neurons "
                        f"({cores_needed} cores) but only {max_cores} cores "
                        f"available across {self.num_chips} chip(s)."
                    ),
                    current=float(cores_needed),
                    limit=float(max_cores),
                    details={"n_neurons": n_neurons, "cores_needed": cores_needed},
                )
                self._violations.append(v)
                violations.append(v)
            else:
                v = ConstraintViolation(
                    category="neurons",
                    severity="warning",
                    message=(
                        f"Population '{label}' has {n_neurons} neurons and "
                        f"is partitioned across {cores_needed} cores "
                        f"(max {self.max_neurons_per_core}/core)."
                    ),
                    current=float(n_neurons),
                    limit=float(self.max_neurons_per_core),
                    details={"n_neurons": n_neurons, "cores_needed": cores_needed},
                )
                self._violations.append(v)
                violations.append(v)

        return violations

    # ------------------------------------------------------------------
    # Synaptic memory (SDRAM) checks
    # ------------------------------------------------------------------

    def check_projection(
        self,
        n_connections: int,
        src_label: str = "",
        dst_label: str = "",
    ) -> List[ConstraintViolation]:
        """Check whether a projection's synaptic data fits in SDRAM."""
        if not self.enable:
            return []

        self.total_projections += 1
        bytes_needed = n_connections * BYTES_PER_SYNAPSE
        self._synaptic_bytes_used += bytes_needed

        violations: List[ConstraintViolation] = []

        # Assume worst-case: all projections land on one core.
        # In practice sPyNNaker distributes them, but this is a safe upper
        # bound for early design-phase checking.
        if bytes_needed > self.sdram_per_core:
            v = ConstraintViolation(
                category="sdram",
                severity="error",
                message=(
                    f"Projection {src_label}->{dst_label}: "
                    f"{bytes_needed} bytes synaptic data exceeds "
                    f"{self.sdram_per_core} bytes/core SDRAM limit."
                ),
                current=float(bytes_needed),
                limit=float(self.sdram_per_core),
                details={
                    "n_connections": n_connections,
                    "bytes_per_synapse": BYTES_PER_SYNAPSE,
                },
            )
            self._violations.append(v)
            violations.append(v)

        # Also check cumulative usage (rough heuristic)
        total_cores = max(1, self.num_chips * USABLE_CORES_PER_CHIP)
        avg_bytes_per_core = self._synaptic_bytes_used / total_cores
        if avg_bytes_per_core > self.sdram_per_core:
            v = ConstraintViolation(
                category="sdram",
                severity="error",
                message=(
                    f"Cumulative synaptic memory {self._synaptic_bytes_used} bytes "
                    f"averages {avg_bytes_per_core:.0f} bytes/core across "
                    f"{total_cores} cores, exceeding {self.sdram_per_core} bytes/core."
                ),
                current=float(avg_bytes_per_core),
                limit=float(self.sdram_per_core),
                details={"total_bytes": self._synaptic_bytes_used},
            )
            self._violations.append(v)
            violations.append(v)

        return violations

    # ------------------------------------------------------------------
    # Routing table checks
    # ------------------------------------------------------------------

    def check_routing_entries(
        self,
        n_entries: int,
        chip_id: int = 0,
    ) -> List[ConstraintViolation]:
        """Check whether multicast routing entries fit per chip."""
        if not self.enable:
            return []

        self._routing_entries_used += n_entries
        violations: List[ConstraintViolation] = []
        limit = self.routing_entries_per_chip

        if self._routing_entries_used > limit:
            v = ConstraintViolation(
                category="routing",
                severity="error",
                message=(
                    f"Routing table overflow on chip {chip_id}: "
                    f"{self._routing_entries_used} entries > {limit} limit."
                ),
                current=float(self._routing_entries_used),
                limit=float(limit),
                details={"chip_id": chip_id},
            )
            self._violations.append(v)
            violations.append(v)

        return violations

    # ------------------------------------------------------------------
    # Weight quantization
    # ------------------------------------------------------------------

    def quantize_weight(self, weight: float) -> float:
        """Quantize a weight to sPyNNaker 16-bit fixed-point format.

        sPyNNaker uses 15 fractional bits, range [-1.0, +1.0 - 2^-15].
        Weights outside this range are saturated.
        """
        if not self.enable:
            return weight

        # Saturate
        w = max(WEIGHT_MIN, min(WEIGHT_MAX, float(weight)))
        # Quantize to fixed-point
        fixed = round(w * self.weight_fixed_scale)
        return fixed / self.weight_fixed_scale

    def quantize_weights(self, weights: np.ndarray) -> np.ndarray:
        """Vectorized weight quantization."""
        if not self.enable:
            return weights
        clipped = np.clip(weights, WEIGHT_MIN, WEIGHT_MAX)
        fixed = np.rint(clipped * self.weight_fixed_scale)
        return fixed / self.weight_fixed_scale

    # ------------------------------------------------------------------
    # Projection rebuild cost
    # ------------------------------------------------------------------

    def record_projection_rebuild(self, n_projections: int = 1) -> List[ConstraintViolation]:
        """Record that projections were rebuilt and warn about cost.

        On SpiNNaker, projection creation triggers a chip pause and DMA
        transfer.  Rebuilding every step is not feasible in real-time.
        """
        if not self.enable:
            return []

        self._rebuild_count += n_projections
        cost = n_projections * PROJECTION_REBUILD_LATENCY_S
        self._rebuild_cost_s += cost

        violations: List[ConstraintViolation] = []

        if self._rebuild_count > 1:
            v = ConstraintViolation(
                category="rebuild",
                severity="warning",
                message=(
                    f"Projection rebuilt {self._rebuild_count} times. "
                    f"Estimated chip downtime: {self._rebuild_cost_s:.1f}s. "
                    f"Dynamic topology changes on SpiNNaker require "
                    f"epoch-boundary rebuilds, not per-step."
                ),
                current=float(self._rebuild_count),
                limit=1.0,
                details={"estimated_downtime_s": self._rebuild_cost_s},
            )
            self._violations.append(v)
            violations.append(v)

        return violations

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def has_errors(self) -> bool:
        return any(v.severity == "error" for v in self._violations)

    def has_warnings(self) -> bool:
        return any(v.severity == "warning" for v in self._violations)

    def summary(self) -> Dict[str, Any]:
        """Return a JSON-serializable summary of constraints and violations."""
        errors = [v for v in self._violations if v.severity == "error"]
        warnings = [v for v in self._violations if v.severity == "warning"]
        return {
            "enabled": self.enable,
            "num_chips": self.num_chips,
            "max_neurons_per_core": self.max_neurons_per_core,
            "sdram_per_core": self.sdram_per_core,
            "routing_entries_per_chip": self.routing_entries_per_chip,
            "total_neurons": self.total_neurons,
            "total_projections": self.total_projections,
            "synaptic_bytes_used": self._synaptic_bytes_used,
            "routing_entries_used": self._routing_entries_used,
            "rebuild_count": self._rebuild_count,
            "rebuild_cost_s": self._rebuild_cost_s,
            "n_errors": len(errors),
            "n_warnings": len(warnings),
            "errors": [
                {"category": v.category, "message": v.message}
                for v in errors
            ],
            "warnings": [
                {"category": v.category, "message": v.message}
                for v in warnings
            ],
        }

    def reset(self) -> None:
        """Clear all tracked state (useful between simulation runs)."""
        self.total_neurons = 0
        self.total_projections = 0
        self._routing_entries_used = 0
        self._synaptic_bytes_used = 0
        self._violations.clear()
        self._rebuild_count = 0
        self._rebuild_cost_s = 0.0
