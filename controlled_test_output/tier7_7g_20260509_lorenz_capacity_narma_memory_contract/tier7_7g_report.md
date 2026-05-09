# Tier 7.7g Lorenz State-Capacity / NARMA Memory-Depth Contract

- Generated: `2026-05-09T14:39:06+00:00`
- Status: **PASS**
- Criteria: `15/15`
- Outcome: `lorenz_capacity_narma_memory_contract_locked`

## Question

Are the remaining Lorenz and repaired-NARMA gaps capacity/state-interface limited, or do they remain flat under matched-capacity sweeps?

## Capacity Matrix

| Variant | Family | Units | Required |
| --- | --- | ---: | --- |
| `cra_v2_5_temporal_state_16` | CRA temporal-state capacity sweep | 16 | True |
| `esn_train_prefix_ridge_16` | matched-capacity ESN reference | 16 | True |
| `random_reservoir_online_16` | matched-capacity random reservoir control | 16 | True |
| `cra_v2_5_temporal_state_32` | CRA temporal-state capacity sweep | 32 | True |
| `esn_train_prefix_ridge_32` | matched-capacity ESN reference | 32 | True |
| `random_reservoir_online_32` | matched-capacity random reservoir control | 32 | True |
| `cra_v2_5_temporal_state_64` | CRA temporal-state capacity sweep | 64 | True |
| `esn_train_prefix_ridge_64` | matched-capacity ESN reference | 64 | True |
| `random_reservoir_online_64` | matched-capacity random reservoir control | 64 | True |
| `cra_v2_5_temporal_state_128` | CRA temporal-state capacity sweep | 128 | True |
| `esn_train_prefix_ridge_128` | matched-capacity ESN reference | 128 | True |
| `random_reservoir_online_128` | matched-capacity random reservoir control | 128 | True |
| `lag_ridge_reference` | simple lag/readout baseline | 0 | True |
| `online_lms_reference` | simple online linear baseline | 0 | True |

## Diagnostic Questions

- `lorenz_capacity_closure`: Does increasing CRA temporal-state capacity materially close the Lorenz gap toward matched-capacity ESN/reservoir references?
- `narma_memory_depth_closure`: Does increasing CRA temporal-state capacity improve repaired NARMA10 memory-depth performance beyond v2.5-16?
- `capacity_vs_architecture`: If capacity increases do not help, does the result justify a structural mechanism rather than more units?
- `external_capacity_fairness`: Do ESN/reservoir baselines remain stronger at comparable state counts, or is the comparison unfairly capacity-skewed?
- `mackey_anchor_regression`: Does any higher-capacity variant preserve the Mackey signal, or does capacity damage the only confirmed standardized gain?

## Pass/Fail Classes

- `capacity_limited_closing`: Higher-capacity CRA improves Lorenz or repaired NARMA by >=25% versus 16-unit v2.5 and closes >=30% of the gap to matched-capacity ESN/reservoir with shams separated.
- `capacity_helps_but_baseline_gap_persists`: Higher-capacity CRA improves materially versus 16-unit v2.5 but ESN/reservoir remains substantially better.
- `architecture_limited_flat`: CRA remains flat across 16/32/64/128 while matched-capacity ESN/reservoir remains much stronger.
- `overfit_or_sham_blocked`: Train metrics improve while test/tail fails, or shams match candidate performance.
- `mackey_regression`: Capacity variants damage the confirmed Mackey signal without improving Lorenz/NARMA.

## Nonclaims

- not a new baseline freeze
- not a mechanism promotion
- not broad public usefulness
- not hardware/native transfer
- not evidence of external-baseline superiority unless the scoring gate shows it
- not language, broad reasoning, AGI, or ASI evidence
