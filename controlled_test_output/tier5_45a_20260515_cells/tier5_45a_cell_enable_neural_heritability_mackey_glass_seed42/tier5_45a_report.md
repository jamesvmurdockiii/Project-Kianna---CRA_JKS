# Tier 5.45a — Healthy-NEST Rebaseline Scoring Gate

- Generated: `2026-05-16T14:45:14+00:00`
- Status: **PASS**
- Outcome: `no_promotion_confirmed`
- Criteria: `10/10`
- Runner revision: `tier5_45a_healthy_nest_rebaseline_scoring_20260515_0002`

## Claim Boundary

Software/NEST scoring gate only. A pass means the post-cleanup healthy-NEST rebaseline was measured under the locked contract. It is not a hardware/native transfer, not an automatic mechanism promotion, not a baseline freeze, and not public superiority evidence.

## Aggregate Model Ranking

| Rank | Model | Status | Seed count | Geomean MSE mean |
| ---: | --- | --- | ---: | ---: |
| 1 | esn_or_random_reservoir | pass | 1 | 0.030917170829273404 |
| 2 | online_linear_or_lag_ridge | pass | 1 | 0.14562679084201754 |
| 3 | v2_6_predictive_reference | pass | 1 | 0.28398795532003474 |
| 4 | persistence_baseline | pass | 1 | 1.3805922510483823 |
| 5 | enable_neural_heritability | pass | 1 | 1.7701749913005542 |

## Mechanism Decisions

| Model | Decision | Δ vs v2.6 | Δ vs default |
| --- | --- | ---: | ---: |
| enable_neural_heritability | `no_promotion` | -5.233274891203361 | None |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 5.45 contract exists | `True` | `true` | yes |
| all requested tasks known | `['mackey_glass']` | `subset of sine/MG/Lorenz/NARMA10` | yes |
| all required models scored | `[]` | `[]` | yes |
| expected unique model/task/seed cells | `5` | `== 5` | yes |
| organism synthetic fallbacks zero | `0` | `== 0` | yes |
| organism sim.run failures zero | `0` | `== 0` | yes |
| organism summary read failures zero | `0` | `== 0` | yes |
| outcome classified | `no_promotion_confirmed` | `non-empty` | yes |
| no automatic baseline freeze | `False` | `false` | yes |
| no hardware/native claim | `False` | `false` | yes |
