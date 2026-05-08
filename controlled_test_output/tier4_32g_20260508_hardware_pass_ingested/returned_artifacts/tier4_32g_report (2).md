# Tier 4.32g - Two-Chip Lifecycle Traffic/Resource Hardware Smoke

- Generated: `2026-05-08T03:51:06+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Runner revision: `tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003`

## Claim Boundary

Tier 4.32g is a two-chip lifecycle traffic/resource smoke. It proves only that the named source-chip learning core can emit lifecycle event/trophic MCPL requests to a remote-chip lifecycle core and receive the resulting active-mask/lineage sync through compact readback counters. It is not lifecycle scaling, not benchmark evidence, not speedup evidence, not multi-shard learning, not true partitioned ecology, and not a native-scale baseline freeze.

## Summary

- source_chip: `{'x': 0, 'y': 0}`
- remote_chip: `{'x': 1, 'y': 0}`
- core_roles: `{'learning': {'chip': 'source', 'profile': 'learning_core', 'core': 7, 'app_id': 4, 'link': 'request_east'}, 'lifecycle': {'chip': 'remote', 'profile': 'lifecycle_core', 'core': 4, 'app_id': 5, 'link': 'sync_west'}}`
- lifecycle_traffic_status: `pass`
- synthetic_fallback_used: `False`
- claim_boundary: `Tier 4.32g is a two-chip lifecycle traffic/resource smoke. It proves only that the named source-chip learning core can emit lifecycle event/trophic MCPL requests to a remote-chip lifecycle core and receive the resulting active-mask/lineage sync through compact readback counters. It is not lifecycle scaling, not benchmark evidence, not speedup evidence, not multi-shard learning, not true partitioned ecology, and not a native-scale baseline freeze.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `"tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003"` | expected | yes |
| synthetic fallback zero | `0` | == 0 | yes |
| source checks pass | `"pass"` | == pass | yes |
| main syntax check pass | `"pass"` | == pass | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spynnaker.cfg"], "reaso...` | status == pass | yes |
| both role builds pass | `{"learning": "pass", "lifecycle": "pass"}` | all == pass | yes |
| both role loads pass | `{"learning": "pass", "lifecycle": "pass"}` | all == pass | yes |
| no top-level hardware exception | `true` | == True | yes |
| lifecycle traffic smoke status pass | `"pass"` | == pass | yes |
| no hardware exception | `true` | == True | yes |
| task completed | `"completed"` | completed/pass | yes |
| source chip placement | `{"x": 0, "y": 0}` | == {'x': 0, 'y': 0} | yes |
| remote chip placement | `{"x": 1, "y": 0}` | == {'x': 1, 'y': 0} | yes |
| all resets succeeded | `{"learning": true, "lifecycle": true}` | all success | yes |
| lifecycle init succeeded | `true` | == True | yes |
| trophic request emitted | `true` | == True | yes |
| death event emitted | `true` | == True | yes |
| learning read success | `true` | == True | yes |
| lifecycle runtime read success | `true` | == True | yes |
| lifecycle summary read success | `true` | == True | yes |
| source event request counter | `1` | == 1 | yes |
| source trophic request counter | `1` | == 1 | yes |
| source received one mask sync | `1` | == 1 | yes |
| source saw expected active mask | `1` | == 1 | yes |
| source saw lifecycle event count | `2` | >= 2 | yes |
| source lineage checksum present | `6026` | > 0 | yes |
| lifecycle accepted trophic+death | `2` | == 2 | yes |
| lifecycle sent one mask sync | `1` | == 1 | yes |
| lifecycle duplicate events zero | `0` | == 0 | yes |
| lifecycle stale events zero | `0` | == 0 | yes |
| lifecycle missing acks zero | `0` | == 0 | yes |
| lifecycle active mask mutated | `1` | == 1 | yes |
| lifecycle active count | `1` | == 1 | yes |
| lifecycle death count | `1` | == 1 | yes |
| lifecycle trophic update count | `1` | == 1 | yes |
| lifecycle invalid events zero | `0` | == 0 | yes |
| all pause commands succeeded | `{"learning": {"cmd": 25, "status": 0, "stopped_timestep": 2863, "success": true}, "lifecycle": {"cmd": 25, "status": 0, "stopped_timestep": 1665, "success": ...` | all success | yes |
| learning payload includes lifecycle counters | `149` | >= 149 | yes |
| lifecycle runtime payload includes lifecycle counters | `149` | >= 149 | yes |
| lifecycle scaling not claimed | `"not_claimed"` | == not_claimed | yes |
| native-scale baseline freeze not authorized | `"not_authorized"` | == not_authorized | yes |

## Next

Ingest returned artifacts before authorizing the next multi-chip native-runtime gate.
