# Tier 5.19b Temporal Substrate Benchmark / Sham / Regression Gate

- Generated: `2026-05-05T17:56:17+00:00`
- Status: **PASS**
- Criteria: `12/12`
- Outcome: `fading_memory_supported_recurrence_unproven`

## Claim Boundary

Tier 5.19b is software benchmark/sham gate evidence only. It may recommend promotion, narrowing, or repair, but does not freeze a baseline by itself and does not authorize hardware migration.

## Classification

- Recurrence-pressure candidate MSE: `0.8981718156218772`
- Recurrence-pressure lag-only MSE: `0.8966776934841564`
- Recurrence margin vs fading-only: `1.1521245862613314`
- Recurrence margin vs reset: `1.0052328667345811`
- Recurrence margin vs shuffled state: `1.3010379581950036`
- Held-out long-memory margin vs lag: `3.2952658887263206`
- Recommendation: Consider a narrowed fading-memory candidate or repair recurrence; do not promote or claim recurrence-specific value from this tier.

## Aggregate Summary

| Scope | Model | Rank | Geomean MSE mean | Geomean NMSE mean |
| --- | --- | ---: | ---: | ---: |
| all_tasks_geomean | fixed_esn_train_prefix_ridge_baseline | 1 | 0.11961516316361176 | 0.1436944825039814 |
| all_tasks_geomean | temporal_plus_lag_reference | 2 | 0.20950804682793275 | 0.24812338368005352 |
| all_tasks_geomean | temporal_full_candidate | 3 | 0.25018377506971284 | 0.2959987312914904 |
| all_tasks_geomean | state_reset_ablation | 4 | 0.25399805216439214 | 0.2997369550961877 |
| all_tasks_geomean | permuted_recurrence_sham | 5 | 0.2582985740037386 | 0.3033136470839994 |
| all_tasks_geomean | fading_memory_only_ablation | 6 | 0.3016241405923007 | 0.3554034351532751 |
| all_tasks_geomean | lag_only_online_lms_control | 7 | 0.31830835080398523 | 0.3766275968672313 |
| all_tasks_geomean | recurrent_hidden_only_ablation | 8 | 0.4308634336321673 | 0.5062196306564367 |
| all_tasks_geomean | fixed_random_reservoir_online_control | 9 | 0.47107999924015703 | 0.5631607976089791 |
| all_tasks_geomean | frozen_temporal_state_ablation | 10 | 0.5483494562320071 | 0.6477419909986577 |
| all_tasks_geomean | temporal_shuffled_target_control | 11 | 0.884778028421198 | 1.045199659989322 |
| all_tasks_geomean | shuffled_temporal_state_sham | 12 | 0.9458152997485376 | 1.1175298522284212 |
| all_tasks_geomean | raw_cra_v2_1_online | 13 | 1.0411469073411987 | 1.2439020210462581 |
| all_tasks_geomean | temporal_no_plasticity_ablation | 14 | 1.0411469073411987 | 1.2439020210462581 |
| standard_three_geomean | fixed_esn_train_prefix_ridge_baseline | 1 | 0.022724530415998184 | 0.034427453982721255 |
| standard_three_geomean | temporal_plus_lag_reference | 2 | 0.11026817744995471 | 0.16602608568850538 |
| standard_three_geomean | temporal_full_candidate | 3 | 0.1488559612698296 | 0.22415006603384427 |
| standard_three_geomean | lag_only_online_lms_control | 4 | 0.1514560842638888 | 0.22797373549106173 |
| standard_three_geomean | state_reset_ablation | 5 | 0.15312905770687735 | 0.23011450121926336 |
| standard_three_geomean | permuted_recurrence_sham | 6 | 0.1533416618160833 | 0.2293871087806021 |
| standard_three_geomean | fading_memory_only_ablation | 7 | 0.1964703354402648 | 0.2954382881368845 |
| standard_three_geomean | recurrent_hidden_only_ablation | 8 | 0.23268819159246634 | 0.34881781618785546 |
| standard_three_geomean | fixed_random_reservoir_online_control | 9 | 0.24027271643056972 | 0.36472651551966856 |
| standard_three_geomean | frozen_temporal_state_ablation | 10 | 0.44531124190752774 | 0.6716184699167629 |
| standard_three_geomean | temporal_shuffled_target_control | 11 | 0.6814170835134368 | 1.0304443891034165 |
| standard_three_geomean | raw_cra_v2_1_online | 12 | 0.744299442671371 | 1.1243682956201968 |
| standard_three_geomean | temporal_no_plasticity_ablation | 13 | 0.744299442671371 | 1.1243682956201968 |
| standard_three_geomean | shuffled_temporal_state_sham | 14 | 0.7451462272653201 | 1.1251204311022545 |

## Interpretation Rule

- This tier may recommend promotion, narrowing, or repair; it does not freeze a baseline by itself.
- If recurrence-specific controls do not separate, do not claim bounded nonlinear recurrence.
- No hardware migration is allowed from this tier alone.
