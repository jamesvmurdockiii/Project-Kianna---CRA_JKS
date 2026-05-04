# Tier 4.29b — Native Routing/Composition Gate

Upload the `cra_429d` folder itself so the JobManager path starts
with `cra_429d/`.

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
- 2 keyed route slots with signed values (+1.0, -1.0).
- Neutral memory slot (value = 1.0, no multiplicative effect).
- 32 events in two phases (16 + 16).
- Phase 2 includes mid-stream overwrites: slot 201 (+1.0 → -1.0) and route 102 (-1.0 → +1.0).
- 8 wrong-context events (~25%) expect feature=0.
- 8 wrong-route events (~25%) expect feature=0.
- 4 both-wrong events (~12%) expect feature=0.
- Feature = context[key] * route[key] * memory[key] * cue.

## Exact JobManager Command (all 3 seeds in one job)

```text
cra_429d/experiments/tier4_29b_native_routing_composition_gate.py --mode run-hardware --seeds 42,43,44
```

## Alternative: single-seed command

```text
cra_429d/experiments/tier4_29b_native_routing_composition_gate.py --mode run-hardware --seed 42
```

## Expected Reference Metrics

```text
readout_weight_raw  ≈ +35329 (positive, converges toward +1.0)
readout_bias_raw    ≈ +655
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
context_slot_hits       = 24
context_slot_misses     = 8
route_active_slots      = 2
route_slot_writes       = 3 (2 initial + 1 overwrite)
route_slot_hits         = 24
route_slot_misses       = 8
```

Tolerance: weight ±8192, bias ±8192

## Multi-Seed Repeatability

Run `--seeds 42,43,44` for one-job three-seed execution.
Each seed produces output in `tier4_29b_seed{seed}_job_output/`.

## Claim Boundary

Local package preparation and build validation only. NOT hardware evidence.
Returned EBRAINS artifacts must pass all criteria for each seed to claim
native routing/composition gate.
