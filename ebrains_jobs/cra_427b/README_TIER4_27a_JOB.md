# Tier 4.27a — Four-Core Runtime Resource / Timing Characterization

Upload the `cra_427b` folder itself so the JobManager path starts
with `cra_427b/`.

## Core Role Map

| Core | App ID | Profile | Role |
|------|--------|---------|------|
| 4 | 1 | `context_core` | Context slot table; replies to context lookup requests |
| 5 | 2 | `route_core` | Route slot table; replies to route lookup requests |
| 6 | 3 | `memory_core` | Memory slot table; replies to memory lookup requests |
| 7 | 4 | `learning_core` | Event schedule, parallel lookups, feature composition, pending horizon, readout |

## Inter-Core Protocol

- Learning core sends `CMD_LOOKUP_REQUEST` (opcode 32) to state cores.
- State cores reply with `CMD_LOOKUP_REPLY` (opcode 33).
- Sequence IDs detect stale reply contamination.
- Transitional SDP; architecture target is multicast/MCPL.

## Exact JobManager Command

```text
cra_427b/experiments/tier4_27a_four_core_distributed_smoke.py --mode run-hardware --seed 42
```

Default output dir is `tier4_27a_seed42_job_output`.

**Do NOT add `--out-dir` or `--output-dir` flags; EBRAINS strips `out` from arguments.**
This was the root cause of the `cra_425h` failure (repaired as `cra_425i`).

## Expected 48-Event Reference Metrics

```text
readout_weight_raw  = 32768
readout_bias_raw    = 0
pending_created     = 48
pending_matured     = 48
active_pending      = 0
decisions           = 48
reward_events       = 48
lookup_requests     = 144
lookup_replies      = 144
stale_replies       = 0
timeouts            = 0
accuracy            = 0.9583
tail_accuracy       = 1.0000
tail_window         = 6
delay_steps         = 2
learning_rate       = 0.25
schema_version      = 2
payload_bytes       = 105
```

Tolerance: weight ±8192 of 32768, bias ±8192 of 0

## Failure-Class Table

| Class | Description | Detection | Recovery |
|-------|-------------|-----------|----------|
| build/load failure | One of the four .aplx images fails to link or exceeds ITCM/DTCM limits | build_returncode != 0 or aplx missing | Reduce code size or split functionality further |
| core role/profile mismatch | Wrong runtime profile loaded onto a core (e.g., learning_core on context core) | READ_STATE profile_id does not match expected role for that core | Verify app_id/core mapping in load script matches core role map |
| inter-core lookup timeout | Lookup request sent but no reply arrives within timeout window | timeout_count > 0, or decisions < 48 with pending lookups stuck | Verify SDP routing; check state core tick is running; increase timeout |
| stale/duplicate seq_id accepted | Sequence ID mismatch or duplicate reply not rejected by learning core | stale_count > 0 in learning core state summary | Verify seq_id monotonically advances; check lookup table clearing logic |
| wrong-profile reply accepted | Learning core accepts a reply from an unexpected profile (e.g., route reply for context lookup) | Cross-profile key/type mismatch in lookup table | Verify lookup_type matching in state core handlers |
| feature/reference mismatch | feature = context * route * memory * cue differs from monolithic reference | final weight/bias outside ±8192 tolerance, or per-event prediction divergence | Check fixed-point multiply order matches monolithic; verify slot values |
| pending maturation mismatch | Learning core matures wrong count, wrong order, or wrong due timestep | pending_created != pending_matured, or active_pending > 0 at end | Check due_timestep calculation; verify no double-maturation or skipped maturation |
| readout mismatch | Final readout weight/bias outside tolerance on learning core | READ_STATE returns weight/bias outside expected range | Check for state corruption or uninitialized slot values |
| missing compact readback | CMD_READ_STATE fails or returns incomplete payload from any core | READ_STATE success=False or payload shorter than 73 bytes | Verify SDP port/routing; check host_interface pack function |

## Claim Boundary

Prepared only. Not hardware evidence until EBRAINS artifacts return and are ingested. Not speedup evidence. Not full native v2.1. Not multi-chip. Not arbitrary task switching.

## Next Step

If hardware run passes: ingest artifacts, evaluate migrating inter-core protocol
from SDP to multicast/MCPL, then design Tier 4.28.

If hardware run fails: classify per failure-class table above, repair smallest
failing layer locally, do not promote to multi-seed until single-seed smoke passes.
