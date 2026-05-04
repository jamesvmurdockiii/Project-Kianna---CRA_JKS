# Coral Reef SpiNNaker Runtime

A **custom bare-metal SpiNNaker application** built on `spinnaker_tools` (`sark.h` / `spin1_api.h`) that enables **true runtime dynamic neuron birth and death** — something impossible within the fixed-topology sPyNNaker / PyNN stack.

## Status and Integration Decision

This runtime is an **experimental sidecar**, not the current mainline CRA backend.
The Python/PyNN package remains the canonical implementation for controlled
simulation, ecology, lifecycle, measurement, and learning experiments.

Tier 4.22c adds the first audited persistent-state scaffold in this runtime:
bounded keyed context slots, no-leak pending delayed-credit horizons, readout
state, decision/reward counters, summary state, and reset semantics. This is the state substrate for the full
custom/on-chip path. It is not yet reward/plasticity learning or a hardware
claim.

Tier 4.22d adds the first audited reward/plasticity scaffold: synaptic
eligibility traces, trace-gated dopamine, fixed-point trace decay, signed
one-shot dopamine, and runtime-owned readout reward updates. This is still local
C evidence, not hardware or continuous-learning parity.

Tier 4.22e passes a local delayed-readout parity scaffold against a floating
reference. Pending horizons store feature, prediction, and due timestep only;
the target/reward is supplied when the horizon matures.

Tier 4.22f0 passes as a scale-readiness audit, but it deliberately sets
`custom_runtime_scale_ready=false`. The current sidecar still has high-severity
scale blockers: incoming spikes scan all synapses, eligibility decay sweeps all
synapses every millisecond, and readback exposes only count/timestep. The next
custom-runtime engineering step is event-indexed spike delivery, lazy/active
eligibility traces, and compact state readback.

Tier 4.22g repairs the first two high-severity data-structure blockers and the
related dopamine sweep locally. Spike delivery now starts from a pre-neuron
outgoing index, and trace decay/dopamine modulation walk the active trace list
instead of all synapses. Compact state readback and hardware command/build
acceptance are still required before custom-runtime hardware learning claims.

Tier 4.22h adds compact state readback through `CMD_READ_STATE` and host-tests
the 73-byte schema. It records local `.aplx` build status honestly: if
`spinnaker_tools` are unavailable, build/load acceptance is not attempted and
not claimed. It also guards Spin1API callback symbol drift by registering
multicast callbacks with the Tier 4.22k-confirmed official event enum constants
`MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`, not brittle guessed names such
as `MC_PACKET_RX`. A real board load plus `CMD_READ_STATE` round-trip remains
the next hardware-facing gate.

Tier 4.22i is prepared as the first board-facing custom-runtime smoke. The
prepared package builds this runtime on the EBRAINS image, loads
`build/coral_reef.aplx`, sends `CMD_READ_STATE`, and checks that simple
`BIRTH`/`CREATE_SYN` mutations are visible in the compact state summary. A
prepared package is not hardware evidence; only returned `run-hardware` artifacts
can prove board round-trip.

Tier 4.22r is the first native keyed-context state command surface in this
runtime. It adds `CMD_WRITE_CONTEXT`, `CMD_READ_CONTEXT`, and
`CMD_SCHEDULE_CONTEXT_PENDING`, so the host can write bounded context slots and
then send only key+cue+delay while the chip retrieves context and computes
`feature=context*cue`. The local/prepared gate passes, but the EBRAINS return is
still required before citing it as hardware evidence.

Promotion criteria before this C runtime becomes a near-term backend:

1. Build and load `build/coral_reef.aplx` on real SpiNNaker hardware.
2. Validate every SDP command in `PROTOCOL_SPEC.md` against the board.
3. Implement fragmented or streamed spike readback beyond the current count-only proof of concept.
4. Reproduce a minimal closed-loop CRA training step with host-side dopamine, birth/death, and synapse updates.
5. Add hardware acceptance tests that can distinguish transport failures from model failures.

Until those gates pass, this directory should be treated as a hardware research
track rather than the source of truth for learning results.

## Why custom C instead of sPyNNaker?

- **Use PyNN/sPyNNaker first** for supported network construction, mapping,
  standard running, and standard readback. This runtime is not a rewrite of the
  whole organism.
- **sPyNNaker** pre-bakes `Population` sizes at `sim.setup()` time. Neurons cannot be added or removed after simulation starts.
- **This runtime** uses `sark_alloc()` / `sark_free()` to create and destroy neurons and synapses on-the-fly, driven by host SDP commands.
- **Result:** emergent topology growth analogous to biological cortical development.
- **Current limit:** production-scale learning needs preallocated/indexed data
  structures, lazy/active trace updates, and compact readback before hardware
  learning claims.

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
│  synapse_manager.c— trace plasticity│
│  state_manager.c  — state/horizons  │
│  host_interface.c — SDP dispatch    │
└─────────────────────────────────────┘
```

## File Layout

| File | Purpose |
|------|---------|
| `src/config.h` | Fixed-point macros, timing constants, command opcodes |
| `src/neuron_manager.h/c` | Dynamic LIF neuron pool (linked list in SDRAM) |
| `src/synapse_manager.h/c` | Dynamic synapse pool with pre/post indexes plus active-trace-gated dopamine |
| `src/state_manager.h/c` | Static bounded CRA state slots, pending delayed-credit horizons, readout state, counters, and reset summary |
| `src/host_interface.h/c` | SDP packet parsing, command dispatch, compact state readback, reply generation |
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
