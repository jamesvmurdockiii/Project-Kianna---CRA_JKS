# Coral Reef SpiNNaker Runtime

A **custom bare-metal SpiNNaker application** built on `spinnaker_tools` (`sark.h` / `spin1_api.h`) that enables **true runtime dynamic neuron birth and death** — something impossible within the fixed-topology sPyNNaker / PyNN stack.

## Status and Integration Decision

This runtime is an **experimental sidecar**, not the current mainline CRA backend.
The Python/PyNN package remains the canonical implementation for controlled
simulation, ecology, lifecycle, measurement, and learning experiments.

Promotion criteria before this C runtime becomes a near-term backend:

1. Build and load `build/coral_reef.aplx` on real SpiNNaker hardware.
2. Validate every SDP command in `PROTOCOL_SPEC.md` against the board.
3. Implement fragmented or streamed spike readback beyond the current count-only proof of concept.
4. Reproduce a minimal closed-loop CRA training step with host-side dopamine, birth/death, and synapse updates.
5. Add hardware acceptance tests that can distinguish transport failures from model failures.

Until those gates pass, this directory should be treated as a hardware research
track rather than the source of truth for learning results.

## Why custom C instead of sPyNNaker?

- **sPyNNaker** pre-bakes `Population` sizes at `sim.setup()` time. Neurons cannot be added or removed after simulation starts.
- **This runtime** uses `sark_alloc()` / `sark_free()` to create and destroy neurons and synapses on-the-fly, driven by host SDP commands.
- **Result:** emergent topology growth analogous to biological cortical development.

## Architecture

```
┌─────────────────────────────────────┐
│  Host Python (colony_controller.py) │
│  ─────────────────────────────────  │
│  Sends SDP packets: BIRTH / DEATH   │
│  / DOPAMINE / CREATE_SYN / etc.     │
└──────────────┬──────────────────────┘
               │ UDP / SDP
┌──────────────▼──────────────────────┐
│  SpiNNaker Core (ARM968)            │
│  ─────────────────────────────────  │
│  main.c           — event loop      │
│  neuron_manager.c — LIF neurons     │
│  synapse_manager.c— plastic synapses│
│  host_interface.c — SDP dispatch    │
└─────────────────────────────────────┘
```

## File Layout

| File | Purpose |
|------|---------|
| `src/config.h` | Fixed-point macros, timing constants, command opcodes |
| `src/neuron_manager.h/c` | Dynamic LIF neuron pool (linked list in SDRAM) |
| `src/synapse_manager.h/c` | Dynamic synapse pool (per-post-neuron linked lists) |
| `src/host_interface.h/c` | SDP packet parsing, command dispatch, reply generation |
| `src/main.c` | Entry point: registers timer + MC packet + SDP callbacks |
| `Makefile` | Build rules for `.aplx` binary |

## Building

Host-side smoke tests do **not** require SpiNNaker tools:

```bash
make test
```

This compiles `tests/test_runtime.c` against the local `stubs/` headers and
runs the runtime manager tests on the host.

Hardware `.aplx` builds require a working `spinnaker_tools` installation.

Requires a working `spinnaker_tools` installation (Linux, typically on the SpiNNaker host PC):

```bash
export SPINN_DIRS=/opt/spinnaker_tools   # adjust to your install
make
```

Output: `build/coral_reef.aplx`

## Loading onto SpiNNaker

Using `ybug` or `SpiNNMan`:

```bash
# Via ybug (interactive)
ybug 192.168.240.1
> boot
> app_load build/coral_reef.aplx 1 16
> app_sig all 1 run    # broadcast RUN signal

# Via spinnaker_tools Python (SpiNNMan)
from spinnman.transceiver import Transceiver
tx = Transceiver.create_new_version_generator("192.168.240.1")
tx.execute_application(1, "coral_reef.aplx")
```

## Host Protocol

SDP packets use the opcodes defined in `host_interface.h` / `colony_controller.py`:

| Opcode | Name | Payload | Description |
|--------|------|---------|-------------|
| `1` | `BIRTH` | `u32 id` | Create neuron with default params |
| `2` | `DEATH` | `u32 id` | Destroy neuron and free SDRAM |
| `3` | `DOPAMINE`| `s32 level` | Global weight modulation (s16.15) |
| `4` | `READ_SPIKES`| — | Returns `(neuron_count, timestep)` |
| `5` | `CREATE_SYN`| `u32 pre, u32 post, s32 weight` | Add synapse |
| `6` | `REMOVE_SYN`| `u32 pre, u32 post` | Delete synapse |
| `7` | `RESET` | — | Wipe all neurons & synapses |

All commands return an SDP reply packet for acknowledgement.

## Next Steps / Production Roadmap

1. **STDP + Eligibility Traces** — Replace the simplified dopamine modulation with proper spike-timing-dependent plasticity using pre-/post-synaptic trace variables.
2. **Router Table Management** — Use `sark_router_alloc()` / `sark_router_free()` to dynamically manage multicast routing entries when neurons are born/die.
3. **Multi-Core Distribution** — Shard neurons across cores using a consistent hashing scheme; route inter-core spikes via the SpiNNaker multicast fabric.
4. **Host-Growth Loop** — Python host reads `READ_SPIKES` replies, runs a topology-evolution policy (e.g. novelty search, gradient estimation), and issues new `BIRTH` / `CREATE_SYN` commands.
5. **SpiNNaker 2 Support** — The same C code compiles for S2 (153 cores, FPU, 2 GB SDRAM) with only Makefile flag changes.

## License

Same as the parent Coral Reef project.
