# Tier 4.28d — Hard Noisy Switching Four-Core MCPL Hardware Probe

Upload the `cra_428i` folder itself so the JobManager path starts
with `cra_428i/`.

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

## Exact JobManager Command (all 3 seeds in one job)

```text
cra_428i/experiments/tier4_28d_hard_noisy_switching_four_core_mcpl.py --mode run-hardware --seeds 42,43,44
```

This runs seeds 42, 43, and 44 sequentially on the same board.

## Alternative: single-seed command

```text
cra_428i/experiments/tier4_28d_hard_noisy_switching_four_core_mcpl.py --mode run-hardware --seed 42
```

## Expected Reference Metrics (hard_noisy_switching, ~62 events)

```text
readout_weight_raw  ≈ +32768 (positive, converges to ~+1.0)
readout_bias_raw    ≈ 0
pending_created     ≈ 62
pending_matured     ≈ 62
active_pending      = 0
decisions           ≈ 62
reward_events       ≈ 62
lookup_requests     ≈ 186 (3 per event: context + route + memory)
lookup_replies      ≈ 186
stale_replies       = 0
timeouts            = 0
accuracy            ≈ 0.80 (20% noisy trials)
tail_accuracy       ≈ 1.0 (non-noisy tail events)
schema_version      = 2
payload_bytes       = 105
```

Tolerance: weight ±8192 of +32768, bias ±8192 of 0

## Multi-Seed Repeatability

Run `--seeds 42,43,44` for one-job three-seed execution.
Each seed produces output in `tier4_28d_seed{seed}_job_output/`.
If variability appears across seeds, document it before freezing the baseline.

## Claim Boundary

Local package preparation and build validation only. NOT hardware evidence.
Returned EBRAINS artifacts must pass all criteria for each seed to claim
repeatability.

## Next Step

If all three seeds pass: ingest artifacts, update docs.
If any seed fails: classify failure (router, timing, drop), repair, re-run.
