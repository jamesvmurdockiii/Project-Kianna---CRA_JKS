# Tier 4.25C — Two-Core State/Learning Split Repeatability — Aggregate Report

- Status: **PASS**
- Seeds tested: 42, 43, 44
- Aggregate generated: 2026-05-02T16:08:27.368696+00:00

## Per-Seed Results

| Seed | Board | Weight | Bias | Pending Created | Pending Matured | Active Pending | Ingest |
|------|-------|--------|------|-----------------|-----------------|----------------|--------|
| 42 | unknown | 32767 | -1 | 48 | 48 | 0 | 23/23 |
| 43 | unknown | 32767 | -1 | 48 | 48 | 0 | 23/23 |
| 44 | unknown | 32767 | -1 | 48 | 48 | 0 | 23/23 |

## Aggregate Criteria

- Max weight delta across seeds: 0 (tolerance: ±8192) — PASS
- Max bias delta across seeds: 0 (tolerance: ±8192) — PASS
- All seeds individual ingest pass: PASS
- All seeds pending_created == 48: PASS
- All seeds pending_matured == 48: PASS
- All seeds active_pending == 0: PASS

## Claim Boundary

The three-seed repeatability pass proves the two-core state/learning split is
deterministic across independent hardware runs on real SpiNNaker. It is NOT
speedup evidence, NOT multi-chip scaling, NOT a general multi-core framework,
and NOT full native v2.1 autonomy.
