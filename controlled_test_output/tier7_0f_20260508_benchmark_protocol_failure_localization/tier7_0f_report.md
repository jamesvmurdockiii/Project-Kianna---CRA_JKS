# Tier 7.0f Benchmark Protocol Repair / Public Failure Localization

- Generated: `2026-05-08T18:54:20+00:00`
- Status: **PASS**
- Criteria: `8/8`
- Outcome: `benchmark_protocol_blocker_confirmed`
- Next step: repair long benchmark protocol, rerun largest valid public scoreboard, then diagnose readout/interface or add one planned general mechanism

## What This Proves

Tier 7.0f proves the benchmark protocol/failure boundary, not a new CRA capability.

## NARMA10 Finite-Stream Policy

- Largest original-seed finite length: `8000`
- Recommended immediate rerun: `{'policy': 'same_seed_max_finite_length', 'length': 8000, 'seeds': [42, 43, 44], 'reason': 'preserves original seeds while avoiding invalid NARMA streams'}`
- Optional 10k finite-seed sensitivity: `{'policy': 'predeclared_finite_seed_replacement', 'length': 10000, 'seeds': [42, 43, 45], 'reason': 'keeps standard NARMA formula but replaces invalid streams through a model-independent finite pre-scan'}`
- Invalid primary streams: `3`

## Gap Diagnosis

- v2.2 improved over raw v2.1: `True`
- v2.2 competitive with best baseline: `False`
- Length-alone support at 720->2000: `False`
- Candidate improvement first-to-last: `0.7894965793339751`

Failure classes:

- not explained by raw CRA inability: v2.2 improves raw v2.1
- not solved by more exposure at 720->2000: candidate geomean worsened while ESN remains ahead
- Mackey-Glass and Lorenz still favor ESN/offline train-prefix readout
- NARMA10 favors explicit lag memory over v2.2 fading memory
- 10k public aggregate blocked by invalid NARMA stream, not interpretable as model evidence

## Nonclaims

- not a CRA performance improvement
- not a new mechanism
- not a baseline freeze
- not hardware evidence
- not public benchmark superiority
- not AGI/ASI evidence
