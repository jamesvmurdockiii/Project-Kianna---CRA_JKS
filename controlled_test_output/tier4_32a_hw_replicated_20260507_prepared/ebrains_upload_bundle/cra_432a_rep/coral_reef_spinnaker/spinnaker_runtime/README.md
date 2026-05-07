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
`feature=context*cue`. The local/prepared gate and returned EBRAINS hardware run both pass; cite it only as tiny native keyed-context state evidence, not full v2.1 on-chip CRA.

Tier 4.22s is the next native route-state command surface. It adds
`CMD_WRITE_ROUTE`, `CMD_READ_ROUTE`, and
`CMD_SCHEDULE_ROUTED_CONTEXT_PENDING`, so the host can write keyed context plus
a chip-owned route scalar and then send only key+cue+delay while the chip
retrieves both and computes `feature=context*route*cue`. The local/prepared
gate passed and the returned EBRAINS artifacts passed after an ingest correction
for a runner criterion bug. Raw remote status was `fail` because the runner
looked for `route_writes` in final `CMD_READ_ROUTE`; corrected evidence uses
the acknowledged `CMD_WRITE_ROUTE` row counters. Returned hardware showed route
writes `9`, final route reads `31`, all raw deltas `0`, tail accuracy `1.0`,
and final readout state `32768/0`.

Tier 4.22t is the next native keyed route-state command surface. It adds
`CMD_WRITE_ROUTE_SLOT`, `CMD_READ_ROUTE_SLOT`, and
`CMD_SCHEDULE_KEYED_ROUTE_CONTEXT_PENDING`, so the host can write keyed context
plus route slots and then send only key+cue+delay while the chip retrieves both
by key and computes `feature=context[key]*route[key]*cue`. The local/prepared
gate passed and prepared `ebrains_jobs/cra_422ac`; cite it only as source and
package readiness until returned EBRAINS hardware artifacts pass. The returned
EBRAINS artifacts now pass: board `10.11.235.25`, core `(0,0,4)`, route-slot
writes `15`, route-slot hits/misses `33/0`, all raw deltas `0`, tail accuracy
`1.0`, and final readout state `32768/0`. This remains tiny keyed route-state
evidence only, not full v2.1 on-chip CRA.

Tier 4.22w adds the first independent-key memory-route composition command:
`CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING`. The local/prepared gate
passes with a 48-event reference where the host writes context, route, and
memory slots under independent key spaces, then schedules each decision with
`context_key`, `route_key`, `memory_key`, cue, and delay. The runtime computes
`feature=context[context_key]*route[route_key]*memory[memory_key]*cue` on chip.
The returned EBRAINS hardware artifacts passed at `controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/` on board
`10.11.236.9`, selected core `(0,0,4)`, with `90/90` criteria, all raw deltas
`0`, observed accuracy `0.958333`, tail accuracy `1.0`, active
context/route/memory slots `4/4/4`, and final readout state `32768/0`. The
first `cra_422af` EBRAINS attempt failed before target acquisition because the
unprofiled image exceeded ITCM by 16 bytes. The repaired `cra_422ag` package
uses `RUNTIME_PROFILE=decoupled_memory_route`, which compiles only the command
handlers needed by this tiny primitive and records the enabled command surface
in the Tier 4.22w artifacts. This is tiny native independent-key composition
evidence only, not full native v2.1 or full CRA task learning.

Tier 4.30d adds the first local runtime source surface for the multi-core
lifecycle split. It introduces the dedicated `lifecycle_core` profile
(`PROFILE_LIFECYCLE_CORE=7`), MCPL/multicast-target lifecycle message IDs for
event requests, trophic updates, and active-mask sync, local C stubs/counters
for lifecycle inter-core traffic, two-packet active-mask/count/lineage sync
coverage, and ownership guards so non-lifecycle profiles reject direct
lifecycle mutation commands. The local gate passed
`14/14` criteria in
`controlled_test_output/tier4_30d_20260505_lifecycle_runtime_source_audit/`.
This is source/runtime host evidence only. Tier 4.30e then passed after EBRAINS
ingest at
`controlled_test_output/tier4_30e_hw_20260505_hardware_pass_ingested/`: board
`10.11.226.145`, raw remote status `pass`, ingest status `pass`, 75/75 hardware
criteria, 5/5 ingest criteria, five profile builds/loads/readbacks, exact
canonical/boundary lifecycle parity, and duplicate/stale lifecycle event
rejection. This remains hardware-smoke evidence only, not lifecycle task-benefit
or baseline-freeze evidence. Tier 4.30f then passed after EBRAINS ingest at
`controlled_test_output/tier4_30f_hw_20260505_hardware_pass_ingested/`: board
`10.11.227.9`, raw remote status `pass`, ingest status `pass`, 185/185 hardware
criteria, 5/5 ingest criteria, behavior-backed lifecycle shams for fixed-pool,
random replay, active-mask shuffle, no-trophic, and no-dopamine modes, and
predeclared control separation on hardware. This remains sham-control evidence
only, not lifecycle task-benefit or baseline-freeze evidence.

Tier 4.31c adds the first local runtime source surface for the v2.2 temporal
substrate. It introduces `CMD_TEMPORAL_INIT`, `CMD_TEMPORAL_UPDATE`,
`CMD_TEMPORAL_READ_STATE`, and `CMD_TEMPORAL_SHAM_MODE`; seven C-owned
fixed-point EMA traces; the Tier 4.31b selected `+/-2.0` trace bound; compact
48-byte temporal readback; zero/frozen/reset sham modes; and ownership guards
so context/route/memory/lifecycle profiles reject temporal mutation commands.
The local source/runtime gate passed `17/17` criteria in
`controlled_test_output/tier4_31c_20260506_native_temporal_runtime_source_audit/`.
This is source/runtime host evidence only. Tier 4.31d must prove the temporal
state surface on real SpiNNaker hardware before it can be cited as hardware
evidence, and it still will not prove benchmark superiority or speedup.

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

### Host-side tests (no SpiNNaker tools needed)

```bash
make test              # runtime host tests
make test-profiles     # all four core profile tests
make test-four-core-48event  # 48-event distributed integration test
```

These compile against local `stubs/` headers and run on the host CPU.

### Hardware `.aplx` builds

Requires `spinnaker_tools` and an ARM cross-compiler (`arm-none-eabi-gcc` with
newlib). On macOS:

```bash
# 1. Clone and build spinnaker_tools
git clone https://github.com/SpiNNakerManchester/spinnaker_tools.git /tmp/spinnaker_tools
cd /tmp/spinnaker_tools && make

# 2. Download ARM GNU Toolchain (includes newlib)
curl -L -o /tmp/arm-gnu-toolchain.tar.xz \
  "https://developer.arm.com/-/media/Files/downloads/gnu/13.3.rel1/binrel/arm-gnu-toolchain-13.3.rel1-darwin-arm64-arm-none-eabi.tar.xz"
cd /tmp && tar xf arm-gnu-toolchain.tar.xz

# 3. Build
export SPINN_DIRS=/tmp/spinnaker_tools
export PATH=/tmp/arm-gnu-toolchain-13.3.rel1-darwin-arm64-arm-none-eabi/bin:$PATH
cd /path/to/this/runtime
make clean && make
```

Output: `build/coral_reef.aplx`

### Hardware runtime profiles

```bash
make RUNTIME_PROFILE=full                          # default; all command handlers
make RUNTIME_PROFILE=decoupled_memory_route        # Tier 4.22w profile
make RUNTIME_PROFILE=context_core                  # Tier 4.26+ state server
make RUNTIME_PROFILE=route_core                    # Tier 4.26+ state server
make RUNTIME_PROFILE=memory_core                   # Tier 4.26+ state server
make RUNTIME_PROFILE=learning_core                 # Tier 4.26+ learning client
make RUNTIME_PROFILE=lifecycle_core                # Tier 4.30d+ lifecycle state owner
```

`full` is the default for host tests and legacy smoke work.
The distributed profiles (`context_core`, `route_core`, `memory_core`,
`learning_core`, `lifecycle_core`) each compile only the command handlers needed
for that role, keeping per-core image size under the 32KB ITCM budget.

As of 2026-05-02:
- `learning_core` text section = 12,448 bytes (with MCPL feasibility code)
- MCPL callback `mcpl_lookup_callback` registered via official `MCPL_PACKET_RECEIVED`
- MCPL key format macros in `config.h` support app_id, msg_type, lookup_type, seq_id

Host tests:
```bash
make test                  # runtime host tests
make test-profiles         # all four core profile tests
make test-four-core-48event  # 48-event distributed integration test
make test-mcpl-feasibility # Tier 4.27d MCPL compile-time feasibility
make test-lifecycle        # Tier 4.30 lifecycle static-pool + sham-control host tests
make test-lifecycle-split  # Tier 4.30d lifecycle-core split host tests
```

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
| `8` | `READ_STATE` | — | Compact runtime summary |
| `9` | `SCHEDULE_PENDING` | `s32 feature, u32 delay` | Schedule delayed readout credit |
| `10` | `MATURE_PENDING` | `s32 target, s32 lr, u32 mature_timestep` | Mature pending readout credit |
| `11` | `WRITE_CONTEXT` | `u32 key, s32 value, s32 confidence` | Write bounded keyed context |
| `12` | `READ_CONTEXT` | `u32 key` | Read bounded keyed context |
| `13` | `SCHEDULE_CONTEXT_PENDING` | `u32 key, s32 cue, u32 delay` | Compute `context*cue` on chip |
| `14` | `WRITE_ROUTE` | `s32 value, s32 confidence` | Write global route state |
| `15` | `READ_ROUTE` | — | Read global route state |
| `16` | `SCHEDULE_ROUTED_CONTEXT_PENDING` | `u32 key, s32 cue, u32 delay` | Compute `context*route*cue` on chip |
| `17` | `WRITE_ROUTE_SLOT` | `u32 key, s32 value, s32 confidence` | Write bounded keyed route slot |
| `18` | `READ_ROUTE_SLOT` | `u32 key` | Read bounded keyed route slot |
| `19` | `SCHEDULE_KEYED_ROUTE_CONTEXT_PENDING` | `u32 key, s32 cue, u32 delay` | Compute `context[key]*route[key]*cue` on chip |
| `20` | `WRITE_MEMORY_SLOT` | `u32 key, s32 value, s32 confidence` | Write bounded keyed memory slot |
| `21` | `READ_MEMORY_SLOT` | `u32 key` | Read bounded keyed memory slot |
| `22` | `SCHEDULE_MEMORY_ROUTE_CONTEXT_PENDING` | `u32 key, s32 cue, u32 delay` | Compute same-key context/route/memory feature on chip |
| `23` | `SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING` | `arg1=context_key`, data=`route_key,memory_key,cue,delay` | Compute independent-key context/route/memory feature on chip |

All commands return an SDP reply packet for acknowledgement.

## Next Steps / Production Roadmap

1. **STDP + Eligibility Traces** — Replace the simplified dopamine modulation with proper spike-timing-dependent plasticity using pre-/post-synaptic trace variables.
2. **Router Table Management** — Use `sark_router_alloc()` / `sark_router_free()` to dynamically manage multicast routing entries when neurons are born/die.
3. **Multi-Core Distribution** — Shard neurons across cores using a consistent hashing scheme; route inter-core spikes via the SpiNNaker multicast fabric.
4. **Host-Growth Loop** — Python host reads `READ_SPIKES` replies, runs a topology-evolution policy (e.g. novelty search, gradient estimation), and issues new `BIRTH` / `CREATE_SYN` commands.
5. **SpiNNaker 2 Support** — The same C code compiles for S2 (153 cores, FPU, 2 GB SDRAM) with only Makefile flag changes.

## License

Same as the parent Coral Reef project.

Tier 4.22u is the next native memory-route command surface. It adds `CMD_WRITE_MEMORY_SLOT`, `CMD_READ_MEMORY_SLOT`, and `CMD_SCHEDULE_MEMORY_ROUTE_CONTEXT_PENDING` so the runtime can own bounded keyed memory/working-state slots in addition to keyed context and keyed route slots. The prepared/local gate computes `feature=context[key]*route[key]*memory[key]*cue` on chip from `key+cue+delay`; this is still a tiny custom-runtime primitive, not full native v2.1 memory/routing or full CRA task learning.

Tier 4.22w extends this surface with independent-key composition through `CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING`. It passed on real SpiNNaker from `ebrains_jobs/cra_422ag` with `RUNTIME_PROFILE=decoupled_memory_route` and sends `context_key`, `route_key`, `memory_key`, `cue`, and `delay` so the chip computes `feature=context[context_key]*route[route_key]*memory[memory_key]*cue`. This is still a tiny custom-runtime primitive, not full native v2.1 memory/routing or full CRA task learning. Ingested evidence: `controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/`.
