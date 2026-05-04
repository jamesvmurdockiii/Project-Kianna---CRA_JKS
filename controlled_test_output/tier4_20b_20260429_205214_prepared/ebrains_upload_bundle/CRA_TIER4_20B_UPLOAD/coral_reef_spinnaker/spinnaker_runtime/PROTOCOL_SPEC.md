# Coral Reef Custom C Runtime — Protocol Specification

**Version:** 0.2  
**Date:** 2026-04-22  
**Status:** EXPERIMENTAL SIDECAR — validated in host smoke tests only; no hardware acceptance test yet

---

## 1. Scope

This document defines the wire protocol between the host Python controller (`colony_controller.py`) and the custom SpiNNaker C runtime (`spinnaker_runtime/src/`).

The Python/PyNN CRA implementation is the mainline research backend. This
protocol becomes production-relevant only after real-hardware build/load,
command round-trip, and spike-readback acceptance tests pass.

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
| 10+ | Payload | Application data (our custom commands) |

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
- `flags = 0x07` (reply expected, so transient IPTag created)

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
    // ... optional SCP header + data[256]
} sdp_msg_t;
```

**Length rule:** `msg->length = 8 + payload_len`

---

## 3. Command Opcodes

Defined in `config.h` and `colony_controller.py`.

| Opcode | Name | Direction | Payload | Reply |
|---|---|---|---|---|
| `1` | `BIRTH` | Host → Chip | `u32 neuron_id` | `cmd + status + u32 id + u16 count` |
| `2` | `DEATH` | Host → Chip | `u32 neuron_id` | `cmd + status + u16 count` |
| `3` | `DOPAMINE` | Host → Chip | `s32 level` (s16.15) | `cmd + status + s32 level` |
| `4` | `READ_SPIKES` | Host → Chip | — | `cmd + u16 count + u16 timestep` |
| `5` | `CREATE_SYN` | Host → Chip | `u32 pre + u32 post + s32 weight` | `cmd + status` |
| `6` | `REMOVE_SYN` | Host → Chip | `u32 pre + u32 post` | `cmd + status` |
| `7` | `RESET` | Host → Chip | — | `cmd + status` |

### 3.1 BIRTH (0x01)

**Request:**
```
payload[0] = 1                    // CMD_BIRTH
payload[1..4] = neuron_id (LE)   // u32
```

**Reply:**
```
payload[0] = 1                    // echo cmd
payload[1] = status (0 = success, 1 = fail)
payload[2..5] = neuron_id (LE)   // u32
payload[6..7] = neuron_count (LE) // u16
```

### 3.2 DEATH (0x02)

**Request:**
```
payload[0] = 2
payload[1..4] = neuron_id (LE)
```

**Reply:**
```
payload[0] = 2
payload[1] = status
payload[2..3] = neuron_count (LE)
```

### 3.3 DOPAMINE (0x03)

**Request:**
```
payload[0] = 3
payload[1..4] = level (LE, s16.15 fixed point)
```

**Reply:**
```
payload[0] = 3
payload[1] = status
payload[2..5] = level (LE, s16.15)
```

### 3.4 READ_SPIKES (0x04)

**Request:** empty payload after cmd byte.

**Reply:**
```
payload[0] = 4
payload[1..2] = neuron_count (LE, u16)
payload[3..4] = current_timestep (LE, u16)
```

> NOTE: A full per-neuron spike dump is not implemented in the PoC. It would require SDP fragmentation or DMA-to-SDRAM transfer.

### 3.5 CREATE_SYN (0x05)

**Request:**
```
payload[0]  = 5
payload[1..4]  = pre_id  (LE, u32)
payload[5..8]  = post_id (LE, u32)
payload[9..12] = weight  (LE, s32, s16.15)
```

**Reply:**
```
payload[0] = 5
payload[1] = status
```

### 3.6 REMOVE_SYN (0x06)

**Request:**
```
payload[0] = 6
payload[1..4] = pre_id  (LE, u32)
payload[5..8] = post_id (LE, u32)
```

**Reply:**
```
payload[0] = 6
payload[1] = status
```

### 3.7 RESET (0x07)

**Request:**
```
payload[0] = 7
```

**Reply:**
```
payload[0] = 7
payload[1] = status
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
