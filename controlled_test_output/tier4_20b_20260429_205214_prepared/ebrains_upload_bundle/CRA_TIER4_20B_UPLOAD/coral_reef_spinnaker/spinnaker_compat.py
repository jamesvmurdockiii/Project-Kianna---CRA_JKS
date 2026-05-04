"""Compatibility shims for sPyNNaker/spinnman hardware runs.

These helpers are intentionally isolated from the learning core.  They only
patch host-side SpiNNaker transport utilities when an installed toolchain has
known NumPy-2 casting behaviour that can break hardware upload/checksum paths.
"""

from __future__ import annotations

from typing import Any


def _dtype_is_uint8(dtype: Any) -> bool:
    """Return True when a NumPy dtype argument names uint8."""
    if dtype is None:
        return False
    try:
        import numpy as np

        return np.dtype(dtype) == np.dtype(np.uint8)
    except Exception:
        return str(dtype).lower() in {"uint8", "<class 'numpy.uint8'>"}


def _uint8_memory_view(data: Any):
    """Return a flat uint8 view of byte-like or word-like memory data."""
    import numpy as np

    if isinstance(data, (bytes, bytearray, memoryview)):
        return np.frombuffer(data, dtype=np.uint8)

    if isinstance(data, (list, tuple)):
        if not data:
            return np.asarray([], dtype=np.uint8)
        ints = [int(value) for value in data]
        if all(0 <= value <= 255 for value in ints):
            return np.asarray(ints, dtype=np.uint8)
        return np.asarray([value & 0xFFFFFFFF for value in ints], dtype=np.uint32).view(
            np.uint8
        )

    array = np.asarray(data)
    if array.dtype == np.dtype(np.uint8):
        return np.ascontiguousarray(array).reshape(-1)
    if array.dtype.kind in {"u", "i"}:
        if array.dtype.itemsize == 1:
            return np.ascontiguousarray(array.astype(np.uint8, copy=False)).reshape(-1)
        if array.dtype.kind == "i" or array.dtype.itemsize > 4:
            array = array.astype(np.uint32, copy=False)
        return np.ascontiguousarray(array).view(np.uint8).reshape(-1)
    return np.ascontiguousarray(array.astype(np.uint8, copy=False)).reshape(-1)


def _coerce_uint8_after_overflow(data: Any):
    """Recover from NumPy 2 uint8 overflow using byte-view semantics."""
    return _uint8_memory_view(data)


def _uint32_checksum(data: Any) -> int:
    """Compute the same uint32 additive checksum using a NumPy-2-safe byte view."""
    import numpy as np

    bytes_view = _uint8_memory_view(data)
    padding = (-int(bytes_view.size)) % 4
    if padding:
        bytes_view = np.concatenate((bytes_view, np.zeros(padding, dtype=np.uint8)))
    if bytes_view.size == 0:
        return 0
    return int(np.sum(bytes_view.view(np.uint32), dtype=np.uint32)) & 0xFFFFFFFF


def _neuromodulation_flags(is_reward: Any, synapse_type: Any) -> int:
    """Build sPyNNaker neuromodulation flags with Python-int bitwise ops."""
    return 0x80000000 | (int(is_reward) << 30) | int(synapse_type)


def apply_numpy_uint8_overflow_patch() -> dict[str, Any]:
    """Install a narrow NumPy 2 retry hook for SpiNNaker byte buffers.

    NumPy 2 raises on expressions such as ``np.asarray([0xC0000000],
    dtype=np.uint8)``.  Some SpiNNaker 7.4.x hardware paths still pass raw
    32-bit machine words through uint8 array constructors while building byte
    buffers.  The wrapper keeps normal NumPy behaviour, and only retries after
    that specific overflow failure.
    """
    try:
        import numpy as np
    except Exception as exc:  # pragma: no cover - NumPy is a hard dependency
        return {
            "applied": False,
            "available": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }

    if getattr(np.asarray, "_cra_uint8_overflow_compat", False):
        return {
            "applied": False,
            "available": True,
            "already_patched": True,
            "numpy_version": np.__version__,
        }

    original_array = np.array
    original_asarray = np.asarray

    def should_retry(exc: Exception, dtype: Any) -> bool:
        return (
            _dtype_is_uint8(dtype)
            and "out of bounds for uint8" in str(exc)
            and type(exc).__name__ in {"OverflowError", "ValueError"}
        )

    def patched_array(obj, dtype=None, *args, **kwargs):
        try:
            return original_array(obj, dtype=dtype, *args, **kwargs)
        except Exception as exc:
            if should_retry(exc, dtype):
                return _coerce_uint8_after_overflow(obj)
            raise

    def patched_asarray(obj, dtype=None, *args, **kwargs):
        try:
            return original_asarray(obj, dtype=dtype, *args, **kwargs)
        except Exception as exc:
            if should_retry(exc, dtype):
                return _coerce_uint8_after_overflow(obj)
            raise

    patched_array._cra_uint8_overflow_compat = True  # type: ignore[attr-defined]
    patched_array._cra_original = original_array  # type: ignore[attr-defined]
    patched_asarray._cra_uint8_overflow_compat = True  # type: ignore[attr-defined]
    patched_asarray._cra_original = original_asarray  # type: ignore[attr-defined]
    np.array = patched_array
    np.asarray = patched_asarray
    return {
        "applied": True,
        "available": True,
        "already_patched": False,
        "numpy_version": np.__version__,
        "target": "numpy.array/numpy.asarray uint8 overflow retry",
    }


def apply_spynnaker_neuromodulation_numpy2_patch() -> dict[str, Any]:
    """Patch sPyNNaker neuromodulation flags for NumPy 2 scalar promotion.

    Some EBRAINS sPyNNaker checkouts still compute::

        0x80000000 | (int(is_reward) << 30) | synapse_type

    where ``synapse_type`` is a NumPy ``uint8`` scalar.  NumPy 2 tries to cast
    the large flag word into uint8 before the OR and raises.  The intended value
    is a 32-bit flags word, so the safe fix is to cast ``synapse_type`` to a
    Python ``int`` before the bitwise operation.
    """
    try:
        import numpy
        from numpy import uint8, uint32
        from spinn_front_end_common.utilities.constants import BYTES_PER_WORD
        from spynnaker.pyNN.models.neuron.plasticity.stdp.common import (
            STDP_FIXED_POINT_ONE,
        )
        from spynnaker.pyNN.models.neuron.synapse_dynamics import (
            synapse_dynamics_neuromodulation as nm,
        )
    except Exception as exc:  # pragma: no cover - optional hardware dependency
        return {
            "applied": False,
            "available": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }

    target = nm.SynapseDynamicsNeuromodulation
    current = target.get_plastic_synaptic_data
    if getattr(current, "_cra_numpy2_neuromodulation_compat", False):
        return {
            "applied": False,
            "available": True,
            "already_patched": True,
            "target": "SynapseDynamicsNeuromodulation.get_plastic_synaptic_data",
        }

    original = current

    def patched_get_plastic_synaptic_data(
        self,
        connections,
        connection_row_indices,
        n_rows: int,
        n_synapse_types: int,
        max_n_synapses: int,
        max_atoms_per_core: int,
    ):
        weights = numpy.rint(
            numpy.abs(connections["weight"]) * STDP_FIXED_POINT_ONE
        )
        fixed_plastic = (
            ((weights.astype(uint32) & 0xFFFF) << 16)
            | (connections["target"] & 0xFFFF)
        )
        fixed_plastic_rows = self.convert_per_connection_data_to_rows(
            connection_row_indices,
            n_rows,
            fixed_plastic.view(dtype=uint8).reshape((-1, BYTES_PER_WORD)),
            max_n_synapses,
        )

        is_reward = 0
        synapse_type = 0
        if len(connections) > 0:
            synapse_type = connections[0]["synapse_type"]
            is_reward = int(synapse_type) == nm.NEUROMODULATION_TARGETS["reward"]
        flags = _neuromodulation_flags(is_reward, synapse_type)

        fp_size = self.get_n_items(fixed_plastic_rows, BYTES_PER_WORD)
        fp_data = numpy.vstack(
            [fixed_row.view(uint32) for fixed_row in fixed_plastic_rows]
        )
        pp_data = numpy.full((n_rows, 1), flags, dtype=uint32)
        pp_size = numpy.ones((n_rows, 1), dtype=uint32)

        return fp_data, pp_data, fp_size, pp_size

    patched_get_plastic_synaptic_data._cra_numpy2_neuromodulation_compat = True  # type: ignore[attr-defined]
    patched_get_plastic_synaptic_data._cra_original = original  # type: ignore[attr-defined]
    target.get_plastic_synaptic_data = patched_get_plastic_synaptic_data
    return {
        "applied": True,
        "available": True,
        "already_patched": False,
        "target": "SynapseDynamicsNeuromodulation.get_plastic_synaptic_data",
    }


def apply_spinnman_numpy2_write_memory_patch() -> dict[str, Any]:
    """Patch spinnman's bytearray checksum path when running under NumPy 2.

    spinnman 7.4.x has a host-side checksum line that can call
    ``numpy.array(data, dtype=uint8)``.  Under NumPy 2, Python integers larger
    than 255 now raise instead of silently truncating.  Hardware upload paths can
    legitimately carry 32-bit words such as routing keys, so the safe behaviour
    is to view the underlying memory as bytes before summing uint32 words.
    """
    try:
        import numpy as np
        import spinnman.processes.write_memory_process as wmp
    except Exception as exc:  # pragma: no cover - optional hardware dependency
        return {
            "applied": False,
            "available": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }

    target = wmp.WriteMemoryProcess
    current = target._write_memory_from_bytearray
    if getattr(current, "_cra_numpy2_compat", False):
        return {
            "applied": False,
            "available": True,
            "already_patched": True,
            "numpy_version": np.__version__,
        }

    original = current

    def patched_write_memory_from_bytearray(
        self,
        base_address: int,
        data: bytes,
        data_offset: int,
        n_bytes: int,
        packet_class,
        get_sum: bool,
    ) -> int:
        offset = 0
        n_bytes_to_write = int(n_bytes)
        data_offset_to_write = int(data_offset)
        with self._collect_responses():
            while n_bytes_to_write > 0:
                bytes_to_send = min(n_bytes_to_write, wmp.UDP_MESSAGE_MAX_SIZE)
                data_array = data[
                    data_offset_to_write : data_offset_to_write + bytes_to_send
                ]
                self._send_request(packet_class(base_address + offset, data_array))
                n_bytes_to_write -= bytes_to_send
                offset += bytes_to_send
                data_offset_to_write += bytes_to_send

        if not get_sum:
            return 0
        return _uint32_checksum(data)

    patched_write_memory_from_bytearray._cra_numpy2_compat = True  # type: ignore[attr-defined]
    patched_write_memory_from_bytearray._cra_original = original  # type: ignore[attr-defined]
    target._write_memory_from_bytearray = patched_write_memory_from_bytearray
    return {
        "applied": True,
        "available": True,
        "already_patched": False,
        "numpy_version": np.__version__,
        "target": "spinnman.processes.write_memory_process.WriteMemoryProcess",
    }


def apply_spinnaker_numpy2_compat_patches() -> dict[str, Any]:
    """Apply all local NumPy 2 compatibility patches used by hardware capsules."""
    return {
        "numpy_uint8_overflow": apply_numpy_uint8_overflow_patch(),
        "spynnaker_neuromodulation": apply_spynnaker_neuromodulation_numpy2_patch(),
        "spinnman_write_memory": apply_spinnman_numpy2_write_memory_patch(),
    }
