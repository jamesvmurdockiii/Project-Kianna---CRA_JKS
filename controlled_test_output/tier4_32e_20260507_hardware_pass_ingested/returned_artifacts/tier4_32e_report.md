# Tier 4.32e - Multi-Chip Learning Micro-Task

- Generated: `2026-05-07T17:23:00+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Runner revision: `tier4_32e_multichip_learning_microtask_20260507_0001`

## Claim Boundary

Tier 4.32e is a two-chip split-role single-shard learning micro-task over the MCPL lookup path. It proves only that the named source-chip learning core can retrieve remote context/route/memory state from the remote chip and update its readout on a 32-event deterministic task while a no-learning control stays immobile. It is not speedup evidence, not benchmark evidence, not true two-partition learning, not lifecycle scaling, not multi-shard learning, and not a native-scale baseline freeze.

## Summary

- source_chip: `{'x': 0, 'y': 0}`
- remote_chip: `{'x': 1, 'y': 0}`
- event_count: `32`
- expected_lookups: `96`
- learning_microtask_status: `pass`
- learning_cases: `[{'label': 'enabled_lr_0_25', 'learning_rate': 0.25, 'kind': 'enabled'}, {'label': 'no_learning_lr_0_00', 'learning_rate': 0.0, 'kind': 'no_learning'}]`
- reference_cases: `{'enabled_lr_0_25': {'learning_rate': 0.25, 'learning_rate_raw': 8192, 'event_count': 32, 'decisions': 32, 'reward_events': 32, 'pending_created': 32, 'pending_matured': 32, 'active_pending': 0, 'readout_weight_raw': 32768, 'readout_bias_raw': 0, 'readout_weight': 1.0, 'readout_bias': 0.0, 'final_timestep': 34, 'trace_preview': [{'timestep': 2, 'event': 1, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 0, 'due': 3}, {'timestep': 3, 'event': 2, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': 0, 'due': 4}, {'timestep': 4, 'event': 3, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 16384, 'due': 5}, {'timestep': 5, 'event': 4, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': -16384, 'due': 6}, {'timestep': 6, 'event': 5, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': -16384, 'due': 7}, {'timestep': 7, 'event': 6, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 24576, 'due': 8}, {'timestep': 8, 'event': 7, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': -32768, 'due': 9}, {'timestep': 9, 'event': 8, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 28672, 'due': 10}]}, 'no_learning_lr_0_00': {'learning_rate': 0.0, 'learning_rate_raw': 0, 'event_count': 32, 'decisions': 32, 'reward_events': 32, 'pending_created': 32, 'pending_matured': 32, 'active_pending': 0, 'readout_weight_raw': 0, 'readout_bias_raw': 0, 'readout_weight': 0.0, 'readout_bias': 0.0, 'final_timestep': 34, 'trace_preview': [{'timestep': 2, 'event': 1, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 0, 'due': 3}, {'timestep': 3, 'event': 2, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': 0, 'due': 4}, {'timestep': 4, 'event': 3, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 0, 'due': 5}, {'timestep': 5, 'event': 4, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': 0, 'due': 6}, {'timestep': 6, 'event': 5, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': 0, 'due': 7}, {'timestep': 7, 'event': 6, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 0, 'due': 8}, {'timestep': 8, 'event': 7, 'feature_raw': -32768, 'target_raw': -32768, 'prediction_raw': 0, 'due': 9}, {'timestep': 9, 'event': 8, 'feature_raw': 32768, 'target_raw': 32768, 'prediction_raw': 0, 'due': 10}]}}`
- synthetic_fallback_used: `False`
- true_two_partition_learning_attempted: `False`
- claim_boundary: `Tier 4.32e is a two-chip split-role single-shard learning micro-task over the MCPL lookup path. It proves only that the named source-chip learning core can retrieve remote context/route/memory state from the remote chip and update its readout on a 32-event deterministic task while a no-learning control stays immobile. It is not speedup evidence, not benchmark evidence, not true two-partition learning, not lifecycle scaling, not multi-shard learning, and not a native-scale baseline freeze.`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `"tier4_32e_multichip_learning_microtask_20260507_0001"` | expected | yes |
| synthetic fallback zero | `0` | == 0 | yes |
| source checks pass | `"pass"` | == pass | yes |
| main syntax check pass | `"pass"` | == pass | yes |
| hardware target acquired | `{"attempts": [{"hostname": "", "method": "hostname_discovery", "notes": ["no hostname found in args, common environment variables, or spynnaker.cfg"], "reaso...` | status == pass | yes |
| all four role builds pass | `{"context": "pass", "learning": "pass", "memory": "pass", "route": "pass"}` | all == pass | yes |
| all four role loads pass | `{"context": "pass", "learning": "pass", "memory": "pass", "route": "pass"}` | all == pass | yes |
| no top-level hardware exception | `true` | == True | yes |
| multi-chip learning micro-task status pass | `"pass"` | == pass | yes |
| no top-level hardware exception | `true` | == True | yes |
| both learning cases returned | `2` | == 2 | yes |
| enabled case present | `true` | present | yes |
| no-learning case present | `true` | present | yes |
| all cases pass | `{"enabled_lr_0_25": "pass", "no_learning_lr_0_00": "pass"}` | all == pass | yes |
| enabled readout exceeds no-learning control | `{"enabled": 32768, "no_learning": 0}` | enabled > no_learning | yes |
| both cases used identical lookup budget | `{"enabled": 96, "no_learning": 96}` | both == 96 | yes |
| true two-partition learning not attempted | `"not_attempted"` | == not_attempted | yes |
| native-scale baseline freeze not authorized | `"not_authorized"` | == not_authorized | yes |
| enabled_lr_0_25 :: no hardware exception | `true` | == True | yes |
| enabled_lr_0_25 :: task completed | `"completed"` | completed/pass | yes |
| enabled_lr_0_25 :: case label present | `"enabled_lr_0_25"` | non-empty | yes |
| enabled_lr_0_25 :: case kind valid | `"enabled"` | enabled|no_learning | yes |
| enabled_lr_0_25 :: reference computed | `{"active_pending": 0, "decisions": 32, "event_count": 32, "final_timestep": 34, "learning_rate": 0.25, "learning_rate_raw": 8192, "pending_created": 32, "pen...` | contains final readout | yes |
| enabled_lr_0_25 :: source chip placement | `{"x": 0, "y": 0}` | == {'x': 0, 'y': 0} | yes |
| enabled_lr_0_25 :: remote chip placement | `{"x": 1, "y": 0}` | == {'x': 1, 'y': 0} | yes |
| enabled_lr_0_25 :: all resets succeeded | `{"context": true, "learning": true, "memory": true, "route": true}` | all success | yes |
| enabled_lr_0_25 :: all state writes succeeded | `{"context": [{"key": "ctx_A", "slot": 101, "success": true}, {"key": "ctx_B", "slot": 202, "success": true}, {"key": "ctx_C", "slot": 303, "success": true}, ...` | all success | yes |
| enabled_lr_0_25 :: all schedule uploads succeeded | `[{"index": 0, "success": true}, {"index": 1, "success": true}, {"index": 2, "success": true}, {"index": 3, "success": true}, {"index": 4, "success": true}, {...` | all success | yes |
| enabled_lr_0_25 :: all run_continuous succeeded | `{"context": {"raw": {"cmd": 24, "status": 0, "success": true}, "success": true}, "learning": {"raw": {"cmd": 24, "status": 0, "success": true}, "success": tr...` | all success | yes |
| enabled_lr_0_25 :: all pause commands succeeded | `{"context": {"raw": {"cmd": 25, "status": 0, "stopped_timestep": 4875, "success": true}, "success": true}, "learning": {"raw": {"cmd": 25, "status": 0, "stop...` | all success | yes |
| enabled_lr_0_25 :: context read success | `true` | == True | yes |
| enabled_lr_0_25 :: route read success | `true` | == True | yes |
| enabled_lr_0_25 :: memory read success | `true` | == True | yes |
| enabled_lr_0_25 :: learning read success | `true` | == True | yes |
| enabled_lr_0_25 :: decisions | `32` | == 32 | yes |
| enabled_lr_0_25 :: reward_events | `32` | == 32 | yes |
| enabled_lr_0_25 :: pending_created | `32` | == 32 | yes |
| enabled_lr_0_25 :: pending_matured | `32` | == 32 | yes |
| enabled_lr_0_25 :: active_pending cleared | `0` | == 0 | yes |
| enabled_lr_0_25 :: lookup_requests | `96` | == 96 | yes |
| enabled_lr_0_25 :: lookup_replies | `96` | == 96 | yes |
| enabled_lr_0_25 :: stale_replies zero | `0` | == 0 | yes |
| enabled_lr_0_25 :: duplicate_replies zero | `0` | == 0 | yes |
| enabled_lr_0_25 :: timeouts zero | `0` | == 0 | yes |
| enabled_lr_0_25 :: readout weight matches reference | `32768` | == 32768 | yes |
| enabled_lr_0_25 :: readout bias matches reference | `0` | == 0 | yes |
| enabled_lr_0_25 :: enabled learning moves readout | `32768` | > 0 when enabled | yes |
| enabled_lr_0_25 :: no-learning keeps weight zero | `32768` | == 0 when no_learning | yes |
| enabled_lr_0_25 :: no-learning keeps bias zero | `0` | == 0 when no_learning | yes |
| enabled_lr_0_25 :: learning payload compact | `105` | >= 105 | yes |
| no_learning_lr_0_00 :: no hardware exception | `true` | == True | yes |
| no_learning_lr_0_00 :: task completed | `"completed"` | completed/pass | yes |
| no_learning_lr_0_00 :: case label present | `"no_learning_lr_0_00"` | non-empty | yes |
| no_learning_lr_0_00 :: case kind valid | `"no_learning"` | enabled|no_learning | yes |
| no_learning_lr_0_00 :: reference computed | `{"active_pending": 0, "decisions": 32, "event_count": 32, "final_timestep": 34, "learning_rate": 0.0, "learning_rate_raw": 0, "pending_created": 32, "pending...` | contains final readout | yes |
| no_learning_lr_0_00 :: source chip placement | `{"x": 0, "y": 0}` | == {'x': 0, 'y': 0} | yes |
| no_learning_lr_0_00 :: remote chip placement | `{"x": 1, "y": 0}` | == {'x': 1, 'y': 0} | yes |
| no_learning_lr_0_00 :: all resets succeeded | `{"context": true, "learning": true, "memory": true, "route": true}` | all success | yes |
| no_learning_lr_0_00 :: all state writes succeeded | `{"context": [{"key": "ctx_A", "slot": 101, "success": true}, {"key": "ctx_B", "slot": 202, "success": true}, {"key": "ctx_C", "slot": 303, "success": true}, ...` | all success | yes |
| no_learning_lr_0_00 :: all schedule uploads succeeded | `[{"index": 0, "success": true}, {"index": 1, "success": true}, {"index": 2, "success": true}, {"index": 3, "success": true}, {"index": 4, "success": true}, {...` | all success | yes |
| no_learning_lr_0_00 :: all run_continuous succeeded | `{"context": {"raw": {"cmd": 24, "status": 0, "success": true}, "success": true}, "learning": {"raw": {"cmd": 24, "status": 0, "success": true}, "success": tr...` | all success | yes |
| no_learning_lr_0_00 :: all pause commands succeeded | `{"context": {"raw": {"cmd": 25, "status": 0, "stopped_timestep": 5344, "success": true}, "success": true}, "learning": {"raw": {"cmd": 25, "status": 0, "stop...` | all success | yes |
| no_learning_lr_0_00 :: context read success | `true` | == True | yes |
| no_learning_lr_0_00 :: route read success | `true` | == True | yes |
| no_learning_lr_0_00 :: memory read success | `true` | == True | yes |
| no_learning_lr_0_00 :: learning read success | `true` | == True | yes |
| no_learning_lr_0_00 :: decisions | `32` | == 32 | yes |
| no_learning_lr_0_00 :: reward_events | `32` | == 32 | yes |
| no_learning_lr_0_00 :: pending_created | `32` | == 32 | yes |
| no_learning_lr_0_00 :: pending_matured | `32` | == 32 | yes |
| no_learning_lr_0_00 :: active_pending cleared | `0` | == 0 | yes |
| no_learning_lr_0_00 :: lookup_requests | `96` | == 96 | yes |
| no_learning_lr_0_00 :: lookup_replies | `96` | == 96 | yes |
| no_learning_lr_0_00 :: stale_replies zero | `0` | == 0 | yes |
| no_learning_lr_0_00 :: duplicate_replies zero | `0` | == 0 | yes |
| no_learning_lr_0_00 :: timeouts zero | `0` | == 0 | yes |
| no_learning_lr_0_00 :: readout weight matches reference | `0` | == 0 | yes |
| no_learning_lr_0_00 :: readout bias matches reference | `0` | == 0 | yes |
| no_learning_lr_0_00 :: enabled learning moves readout | `0` | > 0 when enabled | yes |
| no_learning_lr_0_00 :: no-learning keeps weight zero | `0` | == 0 when no_learning | yes |
| no_learning_lr_0_00 :: no-learning keeps bias zero | `0` | == 0 when no_learning | yes |
| no_learning_lr_0_00 :: learning payload compact | `105` | >= 105 | yes |
| true two-partition learning not attempted | `"not_attempted"` | == not_attempted | yes |
| native-scale baseline freeze not authorized | `"not_authorized"` | == not_authorized | yes |

## Next

Ingest returned artifacts before authorizing the next multi-chip native-runtime gate.
