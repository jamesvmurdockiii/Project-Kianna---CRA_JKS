# Coral Reef Custom C Runtime — Protocol Specification

**Version:** 0.6  
**Date:** 2026-05-01  
**Status:** EXPERIMENTAL SIDECAR - Tier 4.22i board load/command round-trip passed; Tier 4.22j minimal closed-loop learning smoke passed after raw false-fail correction; Tier 4.22l tiny fixed-point learning parity passed on EBRAINS; Tier 4.22m minimal task micro-loop passed on EBRAINS; Tier 4.22n delayed-cue micro-task passed on EBRAINS; Tier 4.22o noisy-switching micro-task prepared

---

## 1. Scope

This document defines the wire protocol between the host Python controller (`colony_controller.py`) and the custom SpiNNaker C runtime (`spinnaker_runtime/src/`).

The Python/PyNN CRA implementation is the mainline research backend. This
protocol becomes production-relevant only after real-hardware build/load,
command round-trip, and spike-readback acceptance tests pass.

Tier 4.22c/4.22d/4.22e add local C state, reward/plasticity, and
delayed-readout parity scaffolds. These changes update runtime semantics, but
they are still host-tested only until hardware command round-trip and
learning-parity gates pass.

Tier 4.22f0 records the current scale-readiness boundary. The custom C runtime
is a sidecar for CRA-specific substrate mechanics that PyNN/sPyNNaker cannot
express or scale directly; PyNN/sPyNNaker remains the primary supported
construction, mapping, run, and standard-readback layer. Direct custom-runtime
learning hardware claims are blocked until event-indexed spike delivery,
lazy/active eligibility traces, and compact state readback are implemented.

Tier 4.22g implements the event-indexed spike-delivery and active-trace pieces
locally. The protocol boundary is unchanged: compact state readback and
hardware command/build acceptance are still required before this runtime can be
cited as custom-runtime hardware learning evidence.

Tier 4.22h adds `CMD_READ_STATE`, a compact 73-byte runtime state summary
payload. This is locally host-tested only until a real board command round-trip
returns the same schema.

Tier 4.22i passed the first real-board command round-trip smoke. It
builds/loads the `.aplx`, sends `CMD_READ_STATE`, and shows state mutation in
the returned schema before any custom-runtime learning tier is allowed.
Multicast callback registration uses the Tier 4.22k-confirmed official
Spin1API enum constants `MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`; local
guards reject legacy guessed names such as `MC_PACKET_RX` before we waste a
board run.
The `cra_422q` EBRAINS return proved build, target acquisition, and app load,
but failed command round-trip because the host and runtime did not use the
official SDP/SCP command header. Version 0.5 repairs the contract to use
`cmd_rc`, `seq`, `arg1`, `arg2`, and `arg3` before `data[]`.

Tier 4.22j adds and has now passed the first minimal custom-runtime learning
commands:
`CMD_SCHEDULE_PENDING` and `CMD_MATURE_PENDING`. This is intentionally tiny.
It proves one chip-owned delayed pending/readout update after the Tier 4.22i
transport path passed. It is not full CRA task learning, not v2.1 mechanism
transfer, not speedup evidence, and not final on-chip autonomy.

Tier 4.22l has passed as the next hardware-facing parity gate. It uses the same
commands to run four signed readout updates and returned board state matched the
local s16.15 reference exactly, ending at `readout_weight_raw=-4096` and
`readout_bias_raw=-4096`. This is tiny fixed-point parity evidence only; it is
not full CRA task learning, v2.1 mechanism transfer, speedup evidence, or final
on-chip autonomy.

Tier 4.22m passed as the next task-like gate using the same command surface. It ran a 12-event signed fixed-pattern stream, scored the pre-update readout prediction sign, matured one delayed-credit horizon per event, and matched the final compact state against the local fixed-point reference with observed tail accuracy `1.0`, final `readout_weight_raw=32256`, and final `readout_bias_raw=0`. This is minimal fixed-pattern task micro-loop evidence only, not full CRA task learning or speedup evidence.

Tier 4.22n passed as the next delayed-cue-like gate using the same command
surface. It kept scheduled decisions active across a two-event pending gap,
then matured oldest-first delayed targets against the stored feature/prediction.
The EBRAINS run matched the local fixed-point reference with max observed
pending depth `3`, observed tail accuracy `1.0`, final
`readout_weight_raw=30720`, and final `readout_bias_raw=0`. This is tiny
pending-queue evidence only, not full CRA task learning or speedup evidence.

Tier 4.22o is prepared as the next noisy-switching gate using the same command
surface. It keeps the two-event pending gap but uses a 14-event stream with a
rule switch and two label-noise events. The local fixed-point reference expects
tail accuracy `1.0`, final `readout_weight_raw=-48768`, and final
`readout_bias_raw=-1536`. This remains prepared/local evidence only until
returned EBRAINS artifacts pass.

It is the **single source of truth** for:
- SDP command opcodes
- Multicast key layout
- Packet byte layouts
- Reply formats
- Fixed-point conventions

Any deviation between this spec, `config.h`, and `colony_controller.py` is a bug.

---

## 2. Transport: SDP over UDP

### 2.1 UDP Wire Format

SpiNNaker listens for SDP packets on UDP port **17893** (the SCP port).

Each UDP datagram contains:

| Bytes | Field | Value |
|---|---|---|
| 0–1 | Padding | `0x00 0x00` (aligns SDP header to 4-byte boundary) |
| 2–9 | SDP Header | 8 bytes (see §2.2) |
| 10-25 | Command header | `cmd_rc`, `seq`, `arg1`, `arg2`, `arg3` |
| 26+ | Data | Optional application bytes (`sdp_msg_t.data[]`) |

### 2.2 SDP Header Layout (AppNote 4)

Byte order is **little-endian** for multi-byte fields.

```
byte 2 : flags
    0x07 = no reply expected
    0x87 = reply expected
byte 3 : tag (IPTag, 0xFF for default)
byte 4 : dest_port_cpu = (dest_port << 5) | (dest_cpu & 0x1F)
byte 5 : src_port_cpu  = (src_port  << 5) | (src_cpu  & 0x1F)
byte 6 : dest_y
byte 7 : dest_x
byte 8 : src_y
byte 9 : src_x
```

**Defaults from host:**
- `src_port = 7`, `src_cpu = 31` (indicates external host)
- `src_x = 0`, `src_y = 0`
- `flags = 0x87` for reply-expected commands. Replies sent by the application use `0x07` because no reply to the reply is expected.

### 2.3 SDP Header Layout (C struct)

Inside `sark.h`, the struct is:

```c
typedef struct sdp_msg {
    struct sdp_msg *next;
    ushort length;      // bytes AFTER checksum (header + payload)
    ushort checksum;
    uchar flags;
    uchar tag;
    uchar dest_port;    // Destination port/CPU combined byte
    uchar srce_port;    // Source port/CPU combined byte
    ushort dest_addr;   // (dest_x << 8) | dest_y
    ushort srce_addr;   // (src_x  << 8) | src_y
    ushort cmd_rc;      // command opcode or return code
    ushort seq;         // sequence number
    uint arg1;          // command argument / return value
    uint arg2;          // command argument / return value
    uint arg3;          // command argument / return value
    uchar data[256];    // optional command data
} sdp_msg_t;
```

**Length rule:** `msg->length = 8 + 16 + data_len` for CRA command replies.
The 16 bytes are `cmd_rc`, `seq`, `arg1`, `arg2`, and `arg3`.

---

## 3. Command Opcodes

Defined in `config.h` and `colony_controller.py`.

| Opcode | Name | Direction | Args / data | Reply |
|---|---|---|---|---|
| `1` | `BIRTH` | Host -> Chip | `arg1 = neuron_id` | `cmd_rc = cmd/status`, data = `u32 id + u16 count` |
| `2` | `DEATH` | Host -> Chip | `arg1 = neuron_id` | `cmd_rc = cmd/status`, data = `u16 count` |
| `3` | `DOPAMINE` | Host -> Chip | `arg1 = s32 level` (s16.15) | `cmd_rc = cmd/status`, data = `s32 level` |
| `4` | `READ_SPIKES` | Host -> Chip | no args | `cmd_rc = cmd/status`, data = `u16 count + u16 timestep` |
| `5` | `CREATE_SYN` | Host -> Chip | `arg1 = pre`, `arg2 = post`, `arg3 = s32 weight` | `cmd_rc = cmd/status` |
| `6` | `REMOVE_SYN` | Host -> Chip | `arg1 = pre`, `arg2 = post` | `cmd_rc = cmd/status` |
| `7` | `RESET` | Host -> Chip | no args | `cmd_rc = cmd/status` |
| `8` | `READ_STATE` | Host -> Chip | no args | `cmd_rc = cmd/status`, data = schema-v1 state bytes |
| `9` | `SCHEDULE_PENDING` | Host -> Chip | `arg1 = feature`, `arg2 = delay_steps` | `cmd_rc = cmd/status`, data = `s32 prediction + u32 due_timestep` |
| `10` | `MATURE_PENDING` | Host -> Chip | `arg1 = target`, `arg2 = learning_rate`, `arg3 = mature_timestep or 0` | `cmd_rc = cmd/status`, data = `u32 matured + s32 readout_weight + s32 readout_bias` |

For host requests:

```text
cmd_rc low byte = opcode
cmd_rc high byte = 0
seq = 0
arg1-3 = command arguments
data[] = empty unless a future command needs bulk bytes
```

For runtime replies:

```text
cmd_rc low byte = echoed opcode
cmd_rc high byte = status
seq = request seq
arg1-3 = 0 for now
data[] = optional response bytes
```

### 3.1 BIRTH (0x01)

**Request:**
```
cmd_rc = 1
arg1 = neuron_id
```

**Reply:**
```
cmd_rc low byte = 1
cmd_rc high byte = status (0 = success, 1 = fail)
data[0..3] = neuron_id (LE)   // u32
data[4..5] = neuron_count (LE) // u16
```

### 3.2 DEATH (0x02)

**Request:**
```
cmd_rc = 2
arg1 = neuron_id
```

**Reply:**
```
cmd_rc low byte = 2
cmd_rc high byte = status
data[0..1] = neuron_count (LE)
```

### 3.3 DOPAMINE (0x03)

Runtime semantics as of Tier 4.22d:

- `level` is signed s16.15 fixed point.
- The runtime applies dopamine as a one-shot pending event on the timer path.
- Synaptic weight change is trace-gated:
  `delta_w = dopamine_level * eligibility_trace`.
- A dopamine event with no causal eligibility trace must not move a synaptic
  weight.
- Eligibility traces decay with `DEFAULT_ELIGIBILITY_DECAY` on the timer path.

Delayed-credit boundary:

- Pending horizons must not store the future target/reward at prediction time.
- A pending horizon stores only feature, prediction, and due timestep.
- The reward/target is supplied when the horizon matures.

**Request:**
```
cmd_rc = 3
arg1 = level (LE, s16.15 fixed point)
```

**Reply:**
```
cmd_rc low byte = 3
cmd_rc high byte = status
data[0..3] = level (LE, s16.15)
```

### 3.4 READ_SPIKES (0x04)

**Request:** `cmd_rc = 4`, no args.

**Reply:**
```
cmd_rc low byte = 4
cmd_rc high byte = status
data[0..1] = neuron_count (LE, u16)
data[2..3] = current_timestep (LE, u16)
```

> NOTE: A full per-neuron spike dump is not implemented in the PoC. It would require SDP fragmentation or DMA-to-SDRAM transfer.

### 3.5 CREATE_SYN (0x05)

**Request:**
```
cmd_rc = 5
arg1 = pre_id  (u32)
arg2 = post_id (u32)
arg3 = weight  (s32, s16.15)
```

**Reply:**
```
cmd_rc low byte = 5
cmd_rc high byte = status
```

### 3.6 REMOVE_SYN (0x06)

**Request:**
```
cmd_rc = 6
arg1 = pre_id  (u32)
arg2 = post_id (u32)
```

**Reply:**
```
cmd_rc low byte = 6
cmd_rc high byte = status
```

### 3.7 RESET (0x07)

**Request:**
```
cmd_rc = 7
```

**Reply:**
```
cmd_rc low byte = 7
cmd_rc high byte = status
```

### 3.8 READ_STATE (0x08)

Runtime semantics as of Tier 4.22h:

- Compact state readback is separate from `READ_SPIKES`.
- Payload schema version is `1`.
- Payload length is `73` bytes, below the 255-byte SDP payload ceiling.
- This is sufficient for tiny command acceptance and learning-state
  observability; full spike dumps still require fragmentation or streamed
  readback later.

**Request:**
```
cmd_rc = 8
```

**Reply schema v1:**
```
cmd_rc low byte = 8
cmd_rc high byte = status
data[0]      schema_version = 1
data[1]      reserved
data[2-5]    timestep (u32 LE)
data[6-9]    neuron_count (u32 LE)
data[10-13]  synapse_count (u32 LE)
data[14-17]  active_trace_count (u32 LE)
data[18-21]  active_slots (u32 LE)
data[22-25]  slot_writes (u32 LE)
data[26-29]  slot_hits (u32 LE)
data[30-33]  slot_misses (u32 LE)
data[34-37]  slot_evictions (u32 LE)
data[38-41]  decisions (u32 LE)
data[42-45]  reward_events (u32 LE)
data[46-49]  pending_created (u32 LE)
data[50-53]  pending_matured (u32 LE)
data[54-57]  pending_dropped (u32 LE)
data[58-61]  active_pending (u32 LE)
data[62-65]  readout_weight (s32 LE, s16.15)
data[66-69]  readout_bias (s32 LE, s16.15)
data[70]     flags/reserved
```

The Python parser reconstructs this as a 73-byte logical payload:

```text
cmd, status, data[0..70]
```

### 3.9 SCHEDULE_PENDING (0x09)

Runtime semantics as of Tier 4.22j:

- The host supplies the current scalar feature and a delay in runtime ticks.
- The runtime computes a readout prediction from its current readout weight/bias.
- The runtime records a decision and schedules a pending horizon containing only
  feature, prediction, and due timestep.
- The future target/reward is not supplied or stored at schedule time.

**Request:**
```
cmd_rc = 9
arg1 = feature (LE, s16.15 fixed point)
arg2 = delay_steps (u32)
arg3 = 0
```

**Reply:**
```
cmd_rc low byte = 9
cmd_rc high byte = status
data[0-3] = prediction (s32 LE, s16.15)
data[4-7] = due_timestep (u32 LE)
```

### 3.10 MATURE_PENDING (0x0A)

Runtime semantics as of Tier 4.22j:

- The host supplies the target and learning rate only when the delayed horizon
  is mature.
- `arg3 = 0` means use the current runtime timestep; otherwise it supplies an
  explicit maturity timestep.
- The runtime matures due pending horizons, updates readout weight/bias in
  fixed point, increments reward counters, and exposes the updated state through
  both the command reply and `CMD_READ_STATE`.

**Request:**
```
cmd_rc = 10
arg1 = target (LE, s16.15 fixed point)
arg2 = learning_rate (LE, s16.15 fixed point)
arg3 = mature_timestep (u32, 0 = current timestep)
```

**Reply:**
```
cmd_rc low byte = 10
cmd_rc high byte = status (0 = at least one horizon matured)
data[0-3]  = matured_count (u32 LE)
data[4-7]  = readout_weight (s32 LE, s16.15)
data[8-11] = readout_bias (s32 LE, s16.15)
```

---

## 4. Multicast Key Layout

SpiNNaker multicast packets carry a 32-bit key. The Coral Reef runtime uses:

```
key[31:24] = APP_ID     (0x01)
key[23:0]  = neuron_id  (24-bit, up to 16,777,215 neurons per app)
```

C definition:
```c
#define MAKE_KEY(app, nid)   (((app) << 24) | ((nid) & 0x00FFFFFF))
#define EXTRACT_NEURON_ID(k) ((k) & 0x00FFFFFF)
```

**App ID:** `0x01` (defined in `config.h` as `APP_ID`).

**Note on multi-core scaling:** Future versions may repartition as `app_id(8) | core_id(8) | local_neuron_id(16)` to support multi-core chips. The current 24-bit layout is sufficient for the single-core PoC.

---

## 5. Fixed-Point Convention

All voltages, currents, weights, and time constants on-chip use **s16.15** fixed point:

```
integer_part  = 16 bits  (range -32768 .. +32767)
fraction_part = 15 bits  (precision ≈ 3.05e-5)
```

Conversion macros:
```c
#define FP_SHIFT      15
#define FP_ONE        (1 << 15)          // 32768
#define FP_FROM_FLOAT(f) ((int32_t)((f) * 32768.0f))
#define FP_TO_FLOAT(v)   ((float)(v) / 32768.0f)
#define FP_MUL(a, b)     (((int32_t)(a) * (int32_t)(b)) >> 15)
#define FP_DIV(a, b)     (((int32_t)(a) << 15) / (int32_t)(b))
```

**Canonical weight domain:** `[-1.0, 1.0]` float maps to `[-32768, 32767]` fixed.

Hardware clip limit (SpiNNaker 16-bit fixed-point synaptic weights):
```
WEIGHT_MAX = 1.0 - 1/32768 ≈ 0.99997
WEIGHT_MIN = -1.0
```

The host controller (`colony_controller.py`) sends weights as **32-bit little-endian signed integers** in s16.15 format.

Python helper:
```python
def float_to_fp(v: float) -> int:
    return int(v * (1 << 15))
```

---

## 6. Router Entry Allocation

Each neuron birth allocates **one exact-match route** in the chip-level router CAM:

```c
key  = MAKE_KEY(APP_ID, neuron_id)
mask = 0xFFFFFFFF
route = ROUTE_CORE(sark_core_id())   // current app core, NOT core 0 (monitor)
```

**Limitation:** The chip has 1,024 router entries. At 1 entry per neuron, the design hits the ceiling at ~1k neurons. This is acceptable for the PoC. Production scaling requires route aggregation (e.g., one route per app with neuron_id in payload, or hierarchical routing across chips).

---

## 7. Reply Timeouts

The host controller default timeout is **2.0 seconds**. On the chip, `spin1_send_sdp_msg()` uses a 1 ms timeout for monitor-processor handoff. If no reply arrives within the host timeout, the command should be retried or treated as a chip-level failure.

---

## 8. Version History

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-04-21 | Initial skeleton — protocol contradictions between config.h, host_interface.h, main.c |
| 0.2 | 2026-04-22 | Unified into config.h as single source of truth; fixed SDP padding + header byte order; fixed router core target; added synapse incident cleanup; all smoke tests pass |
| 0.5 | 2026-04-30 | Repaired protocol to official SDP/SCP command header: host/runtime use `cmd_rc`, `seq`, `arg1`, `arg2`, `arg3`, then `data[]`; documents `cra_422q` payload-short failure and `cra_422r` repair |
