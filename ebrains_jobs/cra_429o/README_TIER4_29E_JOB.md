# Tier 4.29e - Native Replay/Consolidation Bridge

Upload folder: `cra_429o`

Command:
```text
cra_429o/experiments/tier4_29e_native_replay_consolidation_bridge.py --mode run-hardware --seeds 42,43,44
```

Purpose: Verify that host-scheduled replay/consolidation events run through the
native four-core state pipeline using context, route, memory, and learning cores.

Controls:
- `no_replay`
- `correct_replay`
- `wrong_key_replay`
- `random_event_replay`

Notes:
- Reuses `cra_429j` binaries; 4.29e intentionally makes no C runtime change.
- The 4.29e runner is copied into this package during prepare mode.
- This is host-scheduled replay only, not native on-chip replay buffers.
- Hardware evidence requires three-seed run, ingest, and standard documentation updates.
