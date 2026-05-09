# Tier 7.7h Lorenz Capacity / NARMA Memory-Depth Scoring Gate

- Generated: `2026-05-09T14:56:35+00:00`
- Status: **PASS**
- Criteria: `19/19`
- Outcome: `overfit_or_sham_blocked`
- Recommendation: Do not promote capacity or a mechanism; repair sham separation before using this diagnostic as evidence.

## Claim Boundary

Tier 7.7h scores the pre-registered 7.7g Lorenz/NARMA capacity matrix. It may classify whether the remaining gap is capacity-limited, capacity-helpful but baseline-gap limited, architecture-limited flat, sham-blocked, or Mackey-regressing. It does not freeze a baseline, promote a mechanism, authorize hardware/native transfer, or claim broad public usefulness.

## Task Diagnostics

| Task | Best capacity | Base16 MSE | Best CRA MSE | ESN MSE | Improvement | Gap closure | Material |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| mackey_glass | 128 | 0.06907697478413959 | 0.03600192012261899 | 0.009547329316296137 | 1.9187025177787802 | 0.5556064445132128 | True |
| lorenz | 128 | 0.011602822346465395 | 0.005320174559587754 | 3.3737069162138967e-05 | 2.1809100841541684 | 0.5430548428235046 | True |
| narma10 | 128 | 0.4334486084343755 | 0.40239030687405786 | 0.4221464040386606 | 1.0771845171957346 | 2.747986186844494 | False |

## Nonclaims

- not a new CRA baseline freeze
- not a mechanism promotion
- not hardware/native transfer
- not external-baseline superiority unless the table explicitly shows it
- not broad public usefulness
- not language, general reasoning, AGI, or ASI evidence
