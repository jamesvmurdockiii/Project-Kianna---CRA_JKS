# Tier 4.29e Native Replay/Consolidation Bridge

- Status: **HARDWARE PASS, INGESTED**
- Package: `cra_429p`
- Runner revision: `tier4_29e_native_replay_consolidation_20260505_0003`
- Seeds: `42`, `43`, `44`
- Criteria: `114/114`

## Per Seed
- Seed 42: `pass`, board `10.11.226.129`, criteria `38/38`
- Seed 43: `pass`, board `10.11.226.1`, criteria `38/38`
- Seed 44: `pass`, board `10.11.226.65`, criteria `38/38`

## Control Summary
- `no_replay`: hardware weight `32768`, bias `0`; reference weight `32768`, bias `0`
- `correct_replay`: hardware weight `47896`, bias `-232`; reference weight `47896`, bias `-232`
- `wrong_key_replay`: hardware weight `32768`, bias `0`; reference weight `32768`, bias `-5243`
- `random_event_replay`: hardware weight `57344`, bias `0`; reference weight `57344`, bias `0`

## Claim Boundary

Host-scheduled replay/consolidation works through native four-core state primitives on real SpiNNaker for this bounded capsule. This is not native on-chip replay buffers, biological sleep, speedup, multi-chip scaling, or external-baseline superiority.

## Noncanonical Predecessor

`cra_429o` returned real hardware execution but failed the old schedule/reference gate. It remains preserved as noncanonical diagnostic evidence and is not promoted.
