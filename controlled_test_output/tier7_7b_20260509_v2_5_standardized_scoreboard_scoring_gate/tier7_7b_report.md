# Tier 7.7b v2.5 Standardized Scoreboard Scoring Gate

- Generated: `2026-05-09T13:30:05+00:00`
- Status: **PASS**
- Criteria: `15/15`
- Outcome: `standardized_progress_pass`
- Recommendation: Standardized progress versus v2.3 is supported, but external baseline gap remains; do not claim broad superiority.

## Claim Boundary

Tier 7.7b scores frozen v2.5 on the pre-registered Tier 7.7a standardized scoreboard. It may support standardized progress or localized usefulness, but it does not freeze a new baseline, does not authorize hardware/native transfer, does not tune benchmarks after seeing results, and does not claim language, broad reasoning, AGI, or ASI.

## Primary Scoreboard

- v2.5 geomean MSE: `0.07354147408230836`
- v2.3 geomean MSE: `0.09510713419835835`
- v2.3 / v2.5 ratio: `1.293244871484538`
- Paired delta mean: `0.021409047218212518`
- Paired CI: `0.01979481221807447` to `0.024408343990874895`
- Task wins versus v2.3: `1/3`
- Best external: `{'model': 'fixed_esn_train_prefix_ridge_baseline', 'geomean_mse': 0.01956749387082184, 'v2_5_divided_by_model': 3.758349156402194}`

## Per-Task v2.5 vs v2.3

| Task | v2.5 MSE | v2.3 MSE | v2.3/v2.5 | v2.5 wins |
| --- | ---: | ---: | ---: | --- |
| mackey_glass | 0.07415031802179879 | 0.16121290687038103 | 2.174136418713504 | True |
| lorenz | 0.015587301268163906 | 0.01520910286292334 | 0.9757367616924804 | False |
| narma10 | 0.35349532308758885 | 0.35308407205135234 | 0.9988366153400716 | False |

## Sham Controls

| Model | Geomean MSE | Sham / v2.5 | Separates |
| --- | ---: | ---: | --- |
| planning_disabled_v2_3_equivalent | 0.09510713419835835 | 1.293244871484538 | True |
| policy_action_disabled | 0.07317257418238983 | 0.994983784258857 | False |
| state_disabled | 0.26391825952054204 | 3.5886996122101396 | True |
| memory_disabled | 0.07292609252948286 | 0.9916321836010961 | False |
| replay_disabled_not_applicable_standardized_core | 0.0732949646270343 | 0.9966480212920649 | False |
| prediction_disabled | 0.07240066028452198 | 0.9844874771409997 | False |
| self_evaluation_disabled | 0.07996408321785266 | 1.087333157455561 | True |
| composition_routing_disabled | 0.07824816615974135 | 1.0640005131276702 | True |
| target_shuffle_control | 1.0403036321918144 | 14.145808812963091 | True |
| time_shuffle_control | 1.0447372129207653 | 14.206095620975516 | True |

## Secondary Confirmation

- `cmapss_fd001_maintenance_utility`: `supportive_prior_v2_4_policy_evidence`; supports strong-pass clause: `True`
- `nab_heldout_alarm_action_cost`: `nab_claim_narrowed_return_to_general_mechanisms`; supports strong-pass clause: `False`

## Nonclaims

- not a new baseline freeze
- not hardware/native evidence
- not evidence that planning helps every standardized task
- not ESN/ridge/GRU superiority unless the table says so
- not language, broad planning, AGI, or ASI evidence
- secondary C-MAPSS/NAB evidence cannot rescue a failed primary standardized core
