# Tier 4.29e cra_429p Local Repair Gate

- Status: **PASS**
- Package: `cra_429p`
- Runner revision: `tier4_29e_native_replay_consolidation_20260505_0003`
- Boundary: local repaired reference/schedule evidence only; not SpiNNaker hardware evidence.

## Results
- Seed 42: pass; failed criteria: none
  - no_replay: weight=32768 (1.0000), bias=0 (0.0000)
  - correct_replay: weight=47896 (1.4617), bias=-232 (-0.0071)
  - wrong_key_replay: weight=32768 (1.0000), bias=-5243 (-0.1600)
  - random_event_replay: weight=57344 (1.7500), bias=0 (0.0000)
- Seed 43: pass; failed criteria: none
  - no_replay: weight=32768 (1.0000), bias=0 (0.0000)
  - correct_replay: weight=47896 (1.4617), bias=-232 (-0.0071)
  - wrong_key_replay: weight=32768 (1.0000), bias=-5243 (-0.1600)
  - random_event_replay: weight=57344 (1.7500), bias=0 (0.0000)
- Seed 44: pass; failed criteria: none
  - no_replay: weight=32768 (1.0000), bias=0 (0.0000)
  - correct_replay: weight=47896 (1.4617), bias=-232 (-0.0071)
  - wrong_key_replay: weight=32768 (1.0000), bias=-5243 (-0.1600)
  - random_event_replay: weight=57344 (1.7500), bias=0 (0.0000)

## Repair Covered

- Preserves per-event context keys in schedule construction, so wrong-key replay is a real sham instead of accidentally using the correct key.
- Mirrors native continuous-runtime update/order semantics, including pending maturation and surprise-threshold behavior.
- Makes correct replay differ from no replay under native semantics, so the replay gate tests a real consolidation effect.

## Next

Upload `ebrains_jobs/cra_429p` and run:

```text
cra_429p/experiments/tier4_29e_native_replay_consolidation_bridge.py --mode run-hardware --seeds 42,43,44
```
