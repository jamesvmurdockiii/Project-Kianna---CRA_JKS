# Tier 4.29a — Native Keyed-Memory Overcapacity Gate

Upload the `cra_429b` folder itself so the JobManager path starts
with `cra_429b/`.

## Core Role Map

| Core | Profile | Role |
|------|---------|------|
| 4 | `context_core` | Context slot table; MCPL replies to context lookup requests |
| 5 | `route_core` | Route slot table; MCPL replies to route lookup requests |
| 6 | `memory_core` | Memory slot table; MCPL replies to memory lookup requests |
| 7 | `learning_core` | Event schedule, parallel MCPL lookups, feature composition, pending horizon, readout |

## Inter-Core Protocol

- Learning core sends MCPL lookup REQUEST packets to state cores via `spin1_send_mc_packet`.
- State cores reply via MCPL lookup REPLY packets via `spin1_send_mc_packet`.
- Router tables configured per-core by `cra_state_mcpl_init()` at startup.
- No SDP monitor-processor involvement in lookup traffic.

## Task Design

- 8 keyed context slots with signed values (+1.0, -1.0, +0.5, -0.5).
- 32 events in two phases (16 + 16).
- Phase 2 includes a mid-stream overwrite of slot 201 (+1.0 → -1.0).
- 6 wrong-key events (~19%) expect feature=0 (bias-only prediction).
- Slot-shuffle control: events read slots in different orders across phases.

## Exact JobManager Command (all 3 seeds in one job)

```text
cra_429b/experiments/tier4_29a_native_keyed_memory_overcapacity_gate.py --mode run-hardware --seeds 42,43,44
```

## Alternative: single-seed command

```text
cra_429b/experiments/tier4_29a_native_keyed_memory_overcapacity_gate.py --mode run-hardware --seed 42
```

## Expected Reference Metrics

```text
readout_weight_raw  ≈ +25000 (positive, converges toward +1.0)
readout_bias_raw    ≈ 0
pending_created     = 32
pending_matured     = 32
active_pending      = 0
decisions           = 32
reward_events       = 32
lookup_requests     = 96 (3 per event: context + route + memory)
lookup_replies      = 96
stale_replies       = 0
timeouts            = 0
schema_version      = 2
payload_bytes       = 105
context_active_slots    = 8
context_slot_writes     = 9 (8 initial + 1 overwrite)
context_slot_hits       = 26
context_slot_misses     = 6
```

Tolerance: weight ±8192, bias ±8192

## Multi-Seed Repeatability

Run `--seeds 42,43,44` for one-job three-seed execution.
Each seed produces output in `tier4_29a_seed{seed}_job_output/`.

## Claim Boundary

Local package preparation and build validation only. NOT hardware evidence.
Returned EBRAINS artifacts must pass all criteria for each seed to claim
keyed-memory overcapacity gate.
