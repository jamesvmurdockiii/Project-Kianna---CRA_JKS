# 4.25B Design Doc — Two-Core State/Learning Split Smoke

**Status:** Design complete, ready for implementation  
**Date:** 2026-05-02  
**Precedent:** 4.23c monolithic hardware pass, 4.24b build metrics, 4.25A mapping analysis  

---

## 1. Claim Boundary

Prove that CRA state ownership and learning ownership can be split across two SpiNNaker cores without corrupting timing, pending maturity, readout state, or compact readback.

Not a speedup claim. Not a multi-chip claim. Not a general multi-core framework. Just the first architecture boundary: **state module → learning module**.

---

## 2. Core Roles

| Role | Core | Owns | Does NOT own |
|------|------|------|-------------|
| **State core** | Core 0 (0,0,4) | context_slots, route_slots, memory_slots, schedule, timer | pending, readout, maturity logic |
| **Learning core** | Core 1 (0,0,5) | pending_horizons, readout_weight, readout_bias, maturity logic, timer | context, route, memory, schedule |

Both cores advance `g_timestep` from the same timer tick (loaded simultaneously by host).

---

## 3. Transport: SDP (not multicast)

**Decision:** Use SDP point-to-point for core-to-core messages. Multicast is faster but requires multiple packets per event (32-bit payload limit), routing table entries, and has no delivery guarantees. SDP fits a single message per event, is reliable, and is easier to debug.

**Future migration path:** If profiling shows SDP latency is a bottleneck, migrate to multicast. The message format is designed to be transport-agnostic.

---

## 4. Message Format

### Core 0 → Core 1: `CMD_SCHEDULE_PENDING_SPLIT` (opcode 30)

Sent when state core matches a schedule entry at current timestep.

| Field | Type | Value |
|-------|------|-------|
| `cmd_rc` | uint8 | 30 |
| `arg1` | int32 | feature (s16.15) |
| `arg2` | int32 | prediction (s16.15) |
| `arg3` | uint32 | due_timestep |
| `data[0:4]` | int32 | target (s16.15) |

Total payload: 16 bytes + headers. Fits comfortably in SDP.

### Core 1 → Core 0: `CMD_MATURE_ACK_SPLIT` (opcode 31)

Sent when learning core matures one or more pending horizons. Lightweight summary.

| Field | Type | Value |
|-------|------|-------|
| `cmd_rc` | uint8 | 31 |
| `arg1` | uint32 | matured_count |
| `arg2` | int32 | current readout_weight (s16.15) |
| `arg3` | int32 | current readout_bias (s16.15) |

Core 0 does not block on this ACK. It is advisory for debugging and optional state mirroring.

---

## 5. Timing Assumptions

1. Both cores are loaded and started in the same `execute_flood` call. Timer ticks are synchronized to within microseconds.
2. Core 0 sends `CMD_SCHEDULE_PENDING_SPLIT` immediately after computing feature at tick N.
3. Core 1 receives the SDP and calls `cra_state_schedule_pending_horizon_with_target()` before its own tick-N callback completes.
4. Pending maturity happens on Core 1 at `due_timestep`, which is `current_tick + delay`. Since both cores share the same tick source, `due_timestep` is unambiguous.
5. SDP delivery latency (~10-100 µs) is negligible compared to 1 ms timestep.

**Risk:** If SDP is delayed across a tick boundary, Core 1 might mature before scheduling. Mitigation: `due_timestep` is always `current + delay` where `delay >= 1`. Even a 1-tick delay in delivery is safe because maturity happens at `due_timestep`, not immediately.

---

## 6. Ack / No-Ack Behavior

- **No application-level ACK required.** SDP delivery is reliable (buffered, no drops unless buffer full). For a 48-event schedule at 1 event/tick, buffer pressure is minimal.
- The `CMD_MATURE_ACK_SPLIT` from Core 1 to Core 0 is advisory only. Core 0 does not block on it.
- Host-level verification: compare final readout and pending counts with 4.23c reference. If messages were lost, the counts would mismatch.

---

## 7. Failure Modes

| Failure | Symptom | Detection |
|---------|---------|-----------|
| SDP buffer overflow on Core 1 | Missed pending schedule | Final `pending_created` < 48 |
| Core 1 crash / not loaded | No readout state | Final read from Core 1 fails |
| Timer desync | Maturity before scheduling | `pending_matured` > `pending_created` |
| Host reads wrong core | Stale or zero state | Readout weight/bias mismatch with reference |
| Build too large for ITCM | Load failure | `load_application_spinnman` returns fail |

---

## 8. Readback Fields

Host queries **both cores** at end of run:

**From Core 0 (state core):**
- `decisions` — should match 4.23c (48)
- `reward_events` — should match 4.23c (48)
- `slot_hits`, `slot_misses`, `active_slots`
- `pending_created` — advisory (Core 0 does not own pending)

**From Core 1 (learning core):**
- `readout_weight_raw` — must match 4.23c (32768)
- `readout_bias_raw` — must match 4.23c (0)
- `pending_created` — must be 48
- `pending_matured` — must be 48
- `active_pending` — must be 0
- `decisions` — advisory
- `reward_events` — advisory

**Combined parity check:** weight==32768 && bias==0 && pending_created==48 && pending_matured==48 && active_pending==0.

---

## 9. Local Reference Parity Target

Same as 4.23c:
- 48-event signed delayed-cue stream, seed 42
- Final weight: 32768 (s16.15)
- Final bias: 0
- Decisions: 48, Rewards: 48
- Pending created: 48, Pending matured: 48

No accuracy claim needed (host still does feature computation on Core 0). The test is whether the **split does not corrupt** the monolithic result.

---

## 10. C Runtime Modifications

Two separate `.aplx` images:

1. **`coral_reef_state.aplx`** — `RUNTIME_PROFILE=state_core`
   - state_manager.c with context/route/memory/schedule
   - host_interface.c extended with `CMD_SCHEDULE_PENDING_SPLIT` sender
   - main.c timer callback: schedule check → feature compute → SDP send to Core 1

2. **`coral_reef_learning.aplx`** — `RUNTIME_PROFILE=learning_core`
   - state_manager.c with pending/readout only (no context/route/memory/slot arrays)
   - host_interface.c extended with `CMD_SCHEDULE_PENDING_SPLIT` receiver
   - main.c timer callback: mature pending at due_timestep

Both images reuse `config.h` and `state_manager.h`. The `state_manager.c` is compiled with `#ifdef` gates for each role.

**Memory savings on learning core:**
- No context_slots array: -160 bytes
- No route_slots array: -160 bytes  
- No memory_slots array: -160 bytes
- No schedule array: -1792 bytes
- No summary counters for slots: ~-60 bytes
- **Total savings: ~2.3 KB DTCM** (makes room for inter-core message buffers)

---

## 11. EBRAINS Command

```text
cra_425b/experiments/tier4_25b_two_core_split_smoke.py --mode run-hardware --out-dir tier4_25b_job_output
```

Runner loads two applications:
- App ID 1 → Core 0 (0,0,4): `coral_reef_state.aplx`
- App ID 2 → Core 1 (0,0,5): `coral_reef_learning.aplx`

Host then:
1. Reset both cores
2. Write context/route/memory slots to Core 0
3. Upload schedule to Core 0
4. Start both timers
5. Wait for schedule exhaustion
6. Read back compact state from both cores
7. Verify parity with 4.23c reference

---

## 12. Blockers

| Blocker | Severity | Mitigation |
|---------|----------|------------|
| Two-application load untested | warning | `execute_flood` supports multi-core; test with `CoreSubsets` containing both processors |
| SDP port collision | info | Use distinct dest_port for state↔learning vs host↔state vs host↔learning |
| ITCM growth from SDP handlers | info | 4.24b showed 41.5% ITCM utilization; handlers add ~200-500 bytes |
| Build profile complexity | warning | Makefile needs two `RUNTIME_PROFILE` values; keep common code in `state_manager.c` |

---

*End of design doc. Ready for implementation.*
