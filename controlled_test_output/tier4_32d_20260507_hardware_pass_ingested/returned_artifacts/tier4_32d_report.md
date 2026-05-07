# Tier 4.32d - Two-Chip Split-Role Single-Shard MCPL Lookup Smoke

- Generated: `2026-05-07T07:50:29+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Runner revision: `tier4_32d_interchip_mcpl_smoke_20260507_0001`

## Claim Boundary

Tier 4.32d is a two-chip split-role single-shard MCPL lookup communication/readback smoke. It proves only the named source-chip learning to remote-chip state-core lookup path for shard 0 if hardware artifacts pass. It is not speedup evidence, not benchmark evidence, not true two-partition learning, not lifecycle scaling, not multi-shard learning, and not a native-scale baseline freeze.

## Summary

- source_chip: `{'x': 0, 'y': 0}`
- remote_chip: `{'x': 1, 'y': 0}`
- event_count: `32`
- expected_lookups: `96`
- interchip_smoke_status: `pass`
- synthetic_fallback_used: `False`
- true_two_partition_learning_attempted: `False`
- claim_boundary: `Tier 4.32d is a two-chip split-role single-shard MCPL lookup communication/readback smoke. It proves only the named source-chip learning to remote-chip state-core lookup path for shard 0 if hardware artifacts pass. It is not speedup evidence, not benchmark evidence, not true two-partition learning, not lifecycle scaling, not multi-shard learning, and not a native-scale baseline freeze.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `"tier4_32d_interchip_mcpl_smoke_20260507_0001"` | expected | yes |
| synthetic fallback zero | `0` | == 0 | yes |
| source checks pass | `"pass"` | == pass | yes |
| main syntax check pass | `"pass"` | == pass | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spynnaker.cfg"], "reaso...` | status == pass | yes |
| all four role builds pass | `{"context": "pass", "learning": "pass", "memory": "pass", "route": "pass"}` | all == pass | yes |
| all four role loads pass | `{"context": "pass", "learning": "pass", "memory": "pass", "route": "pass"}` | all == pass | yes |
| no top-level hardware exception | `true` | == True | yes |
| two-chip smoke status pass | `"pass"` | == pass | yes |
| no hardware exception | `true` | == True | yes |
| task completed | `"completed"` | completed/pass | yes |
| source chip placement | `{"x": 0, "y": 0}` | == {'x': 0, 'y': 0} | yes |
| remote chip placement | `{"x": 1, "y": 0}` | == {'x': 1, 'y': 0} | yes |
| all resets succeeded | `{"context": true, "learning": true, "memory": true, "route": true}` | all success | yes |
| all state writes succeeded | `{"context": [{"key": "ctx_A", "slot": 101, "success": true}, {"key": "ctx_B", "slot": 202, "success": true}, {"key": "ctx_C", "slot": 303, "success": true}, ...` | all success | yes |
| all schedule uploads succeeded | `[{"index": 0, "success": true}, {"index": 1, "success": true}, {"index": 2, "success": true}, {"index": 3, "success": true}, {"index": 4, "success": true}, {...` | all success | yes |
| all run_continuous succeeded | `{"context": {"raw": {"cmd": 24, "status": 0, "success": true}, "success": true}, "learning": {"raw": {"cmd": 24, "status": 0, "success": true}, "success": tr...` | all success | yes |
| all pause commands succeeded | `{"context": {"raw": {"cmd": 25, "status": 0, "stopped_timestep": 4836, "success": true}, "success": true}, "learning": {"raw": {"cmd": 25, "status": 0, "stop...` | all success | yes |
| context read success | `true` | == True | yes |
| route read success | `true` | == True | yes |
| memory read success | `true` | == True | yes |
| learning read success | `true` | == True | yes |
| pending_created | `32` | == 32 | yes |
| pending_matured | `32` | == 32 | yes |
| active_pending cleared | `0` | == 0 | yes |
| lookup_requests | `96` | == 96 | yes |
| lookup_replies | `96` | == 96 | yes |
| stale_replies zero | `0` | == 0 | yes |
| duplicate_replies zero | `0` | == 0 | yes |
| timeouts zero | `0` | == 0 | yes |
| learning payload compact | `105` | >= 105 | yes |
| true two-partition learning not attempted | `"not_attempted"` | == not_attempted | yes |
| native-scale baseline freeze not authorized | `"not_authorized"` | == not_authorized | yes |

## Next

Ingest returned artifacts before authorizing Tier 4.32e multi-chip learning micro-task.
