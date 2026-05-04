# Coral Reef Custom C Runtime — Protocol Specification

**Version:** 0.5  
**Date:** 2026-04-30  
**Status:** EXPERIMENTAL SIDECAR - local host tests and EBRAINS build/load diagnostics passed; command round-trip acceptance pending

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

Tier 4.22i packages the first real-board command round-trip smoke. It must
build/load the `.aplx`, send `CMD_READ_STATE`, and show state mutation in the
returned schema before any custom-runtime learning tier is allowed. Multicast
callback registration uses the Tier 4.22k-confirmed official Spin1API enum
constants `MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`; local guards reject
legacy guessed names such as `MC_PACKET_RX` before we waste a board run.
The `cra_422q` EBRAINS return proved build, target acquisition, and app load,
but failed command round-trip because the host and runtime did not use the
official SDP/SCP command header. Version 0.5 repairs the contract to use
`cmd_rc`, `seq`, `arg1`, `arg2`, and `arg3` before `data[]`.

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
