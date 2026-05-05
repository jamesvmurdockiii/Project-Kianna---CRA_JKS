# Tier 5.19a Local Continuous Temporal Substrate Reference

- Generated: `2026-05-05T17:38:02+00:00`
- Status: **PASS**
- Criteria: `12/12`
- Outcome: `fading_memory_ready_but_recurrence_not_yet_specific`

## Claim Boundary

Tier 5.19a is local software reference evidence only. It defines and tests a bounded temporal-substrate candidate against lag, reservoir, frozen/shuffled-state, no-recurrence, no-plasticity, and shuffled-target controls. It is not hardware evidence, not a baseline freeze, and not a promoted CRA mechanism by itself.

## Classification

- Held-out candidate MSE: `0.38570722690740805`
- Held-out lag-only MSE: `1.2710078678632046`
- Held-out margin vs lag-only: `3.2952658887263206`
- Held-out margin vs shuffled state: `4.900069939484292`
- Held-out margin vs frozen state: `1.474026780849015`
- Held-out margin vs no recurrence: `1.0303693588886562`
- Standard-suite candidate geomean MSE: `0.1488559612698296`
- Standard-suite lag-only geomean MSE: `0.1514560842638888`
- Recommendation: Proceed carefully: fading memory helps, but recurrence-specific value needs a sharper ablation in 5.19b.

## Aggregate Summary

| Scope | Model | Rank | Geomean MSE mean | Geomean NMSE mean |
| --- | --- | ---: | ---: | ---: |
| all_tasks_geomean | fixed_esn_train_prefix_ridge_baseline | 1 | 0.07063372824047988 | 0.09127509309273751 |
| all_tasks_geomean | temporal_substrate_plus_lag_online_reference | 2 | 0.14890870357248773 | 0.18629469592886236 |
| all_tasks_geomean | no_recurrence_temporal_ablation | 3 | 0.1811195372898694 | 0.2265596104751182 |
| all_tasks_geomean | temporal_substrate_online_candidate | 4 | 0.18451788135094607 | 0.23063210878161644 |
| all_tasks_geomean | lag_only_online_lms_control | 5 | 0.2496152851933052 | 0.31182320117331735 |
| all_tasks_geomean | random_reservoir_online_lms_control | 6 | 0.3904528379038279 | 0.49883645914280744 |
| all_tasks_geomean | frozen_temporal_state_ablation | 7 | 0.4597015095429468 | 0.5751372232177946 |
| all_tasks_geomean | temporal_substrate_shuffled_target_control | 8 | 0.8325163424201376 | 1.0402500620164854 |
| all_tasks_geomean | shuffled_temporal_state_sham | 9 | 0.9101382289071305 | 1.136004535294892 |
| all_tasks_geomean | raw_cra_v2_1_online | 10 | 1.0367660903512352 | 1.3160681243853982 |
| all_tasks_geomean | temporal_substrate_no_plasticity_ablation | 11 | 1.0367660903512352 | 1.3160681243853982 |
| standard_three_geomean | fixed_esn_train_prefix_ridge_baseline | 1 | 0.022724530415998184 | 0.034427453982721255 |
| standard_three_geomean | temporal_substrate_plus_lag_online_reference | 2 | 0.11026817744995471 | 0.16602608568850538 |
| standard_three_geomean | no_recurrence_temporal_ablation | 3 | 0.14396158248006105 | 0.2165101083326537 |
| standard_three_geomean | temporal_substrate_online_candidate | 4 | 0.1488559612698296 | 0.22415006603384427 |
| standard_three_geomean | lag_only_online_lms_control | 5 | 0.1514560842638888 | 0.22797373549106173 |
| standard_three_geomean | random_reservoir_online_lms_control | 6 | 0.24027271643056972 | 0.36472651551966856 |
| standard_three_geomean | frozen_temporal_state_ablation | 7 | 0.44531124190752774 | 0.6716184699167629 |
| standard_three_geomean | temporal_substrate_shuffled_target_control | 8 | 0.6814170835134368 | 1.0304443891034165 |
| standard_three_geomean | raw_cra_v2_1_online | 9 | 0.744299442671371 | 1.1243682956201968 |
| standard_three_geomean | temporal_substrate_no_plasticity_ablation | 10 | 0.744299442671371 | 1.1243682956201968 |
| standard_three_geomean | shuffled_temporal_state_sham | 11 | 0.7451462272653201 | 1.1251204311022545 |

## Interpretation Rule

- This is a local software reference gate, not a baseline freeze.
- If shams or lag-only explain the result, park or repair before 5.19b.
- Do not move any Tier 7 benchmark workload to hardware from this tier alone.
