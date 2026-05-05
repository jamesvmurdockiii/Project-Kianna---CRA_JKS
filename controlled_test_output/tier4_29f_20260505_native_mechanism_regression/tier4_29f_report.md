# Tier 4.29f Compact Native Mechanism Regression

- Generated: `2026-05-05T13:20:42.804040+00:00`
- Status: **PASS**
- Runner revision: `tier4_29f_compact_native_mechanism_regression_20260505_0001`
- Mode: `local-evidence-regression`
- Criteria: `113/113`

## Claim Boundary

Tier 4.29f is a canonical evidence-regression gate over the real hardware passes from 4.29a-e. It verifies that native keyed memory, routing/composition, predictive binding, confidence gating, and host-scheduled replay/consolidation all remain complete and aligned as ingested evidence. It is not a new SpiNNaker execution, not a single-task all-mechanism stack proof, not lifecycle evidence, not multi-chip scaling, and not speedup evidence.

## Mechanism Rows

| Tier | Mechanism | Status | Audit Criteria | Hardware Criteria | Seeds |
| --- | --- | --- | ---: | ---: | --- |
| 4.29a | native keyed-memory overcapacity | pass | 20/20 | 141/141 | `42,43,44` |
| 4.29b | native routing/composition | pass | 21/21 | 156/156 | `42,43,44` |
| 4.29c | native predictive binding | pass | 20/20 | 78/78 | `42,43,44` |
| 4.29d | native self-evaluation / confidence gating | pass | 25/25 | 90/90 | `42,43,44` |
| 4.29e | native host-scheduled replay/consolidation | pass | 25/25 | 114/114 | `42,43,44` |

## Interpretation

- This pass freezes the cumulative native mechanism bridge evidence set only if all rows pass.
- It does not create a new hardware execution trace.
- It does not prove all five mechanisms are simultaneously active in one monolithic task.
- It authorizes moving to standard benchmarks only if the freeze artifact is created from this pass.
