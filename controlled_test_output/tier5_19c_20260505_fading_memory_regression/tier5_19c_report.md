# Tier 5.19c Fading-Memory Narrowing / Compact-Regression Decision

- Generated: `2026-05-05T19:01:36+00:00`
- Status: **PASS**
- Criteria: `11/11`
- Outcome: `fading_memory_ready_for_v2_2_freeze`
- Freeze authorized: `True`

## Claim Boundary

Tier 5.19c is software-only fading-memory promotion/regression evidence. A pass can authorize a bounded fading-memory baseline only with full compact regression. It does not prove bounded nonlinear recurrence, hardware transfer, native on-chip temporal dynamics, universal benchmark superiority, language, planning, AGI, or ASI.

## Interpretation

- Temporal-memory geomean candidate MSE: `0.22752229502159751`
- Temporal-memory geomean lag-only MSE: `0.8953538816902333`
- Temporal-memory margin vs lag-only: `3.9352358044966187`
- Temporal-memory margin vs raw v2.1: `9.599924553845483`
- Standard-task geomean candidate MSE: `0.19853975759572184`
- Standard-task geomean lag-only MSE: `0.15368196619186625`
- Recommendation: Freeze a bounded v2.2 software baseline for multi-timescale fading-memory temporal state; do not claim nonlinear recurrence.

## Per-Task Temporal Metrics

| Task | Candidate MSE | Lag MSE | Margin vs lag | Raw v2.1 MSE | Margin vs raw |
| --- | ---: | ---: | ---: | ---: | ---: |
| heldout_long_memory | 0.3653083872204199 | 1.2710078678632046 | 3.4792737104508453 | 2.9750334728645664 | 8.14389588889863 |
| slow_context_drift | 0.074533942806697 | 0.418827752735567 | 5.619288836252664 | 0.8000933403524716 | 10.734617145204638 |
| multiscale_echo | 0.4325717367470247 | 1.3483432700742046 | 3.1170396850563047 | 4.3776680541209325 | 10.120097274596253 |

## Compact Guardrail

- compact_mode: `full`
- compact_backend: `nest`
- compact_pass: `True`
- compact_full: `True`
- compact_freeze_backend: `True`

## Nonclaims

- not bounded nonlinear recurrence
- not hardware evidence
- not native on-chip temporal dynamics
- not universal benchmark superiority
- not language, planning, AGI, or ASI
