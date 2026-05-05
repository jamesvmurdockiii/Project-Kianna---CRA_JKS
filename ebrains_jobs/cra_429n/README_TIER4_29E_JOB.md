# Tier 4.29e — Native Replay/Consolidation Bridge

Upload folder: `cra_429n`

Command:
```text
cra_429n/experiments/tier4_29e_native_replay_consolidation_bridge.py --mode run-hardware --seeds 42,43,44
```

Purpose: Verify that host-scheduled replay events are processed correctly by the
native four-core runtime through existing state primitives.

Controls:
- no_replay: 16 base events only; baseline learning
- correct_replay: 16 base + 8 replay with correct keys; consolidation
- wrong_key_replay: 16 base + 8 replay with wrong context keys (feature=0)
- random_event_replay: 16 base + 8 random conflicting events

Note: This package reuses cra_429j binaries (no C runtime changes required).
The runner constructs schedules with replay events; the native runtime processes
them through the existing schedule primitive.

Expected artifacts per seed:
- tier4_29e_hardware_results_seed{N}.json

After all seeds return, run locally:
```bash
python3 experiments/tier4_29e_native_replay_consolidation_bridge.py --mode ingest --seed 42 --hardware-results controlled_test_output/tier4_29e_*/tier4_29e_hardware_results_seed42.json
python3 experiments/tier4_29e_native_replay_consolidation_bridge.py --mode ingest --seed 43 --hardware-results controlled_test_output/tier4_29e_*/tier4_29e_hardware_results_seed43.json
python3 experiments/tier4_29e_native_replay_consolidation_bridge.py --mode ingest --seed 44 --hardware-results controlled_test_output/tier4_29e_*/tier4_29e_hardware_results_seed44.json
```
