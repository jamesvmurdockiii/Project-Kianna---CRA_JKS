# Tier 5.12c Internal Predictive Context Mechanism Findings

- Generated: `2026-04-29T20:39:25+00:00`
- Status: **PASS**
- Steps: `240`
- Seeds: `42`
- Tasks: `masked_input_prediction,event_stream_prediction,sensor_anomaly_prediction`
- Variants: `all`
- Selected standard baselines: `sign_persistence,online_perceptron`
- Backend: `nest`
- Smoke mode: `False`
- Output directory: `<repo>/controlled_test_output/tier5_17e_20260429_163058/v1_8_compact_regression/predictive_context_guardrail`

Tier 5.12c tests whether CRA can store a visible causal predictive precursor before feedback arrives and use it later at a decision point.

## Claim Boundary

- This is software mechanism evidence, not hardware evidence.
- This is visible predictive-context binding, not full world modeling or hidden-state inference.
- This does not prove language grounding, planning, or AGI capability.
- A pass authorizes compact regression/promotion review; it does not automatically freeze v1.8.
- `hidden_regime_switching` is intentionally excluded from the default mechanism run because that needs latent-regime inference, not visible precursor storage.

## Comparisons

| Task | v1.7 acc | Scaffold acc | Internal predictive acc | Best ablation | Ablation acc | Best control | Control acc | Best baseline | Baseline acc | Edge vs v1.7 | Edge vs ablation | Edge vs baseline | Updates | Active steps |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| event_stream_prediction | 0 | 1 | 1 | `permuted_predictive_context` | 0.608696 | `shuffled_target_control` | 0.652174 | `online_perceptron` | 0.391304 | 1 | 0.391304 | 0.608696 | 23 | 23 |
| masked_input_prediction | 0 | 0.75 | 0.75 | `permuted_predictive_context` | 0.5 | `rolling_majority` | 0.6 | `sign_persistence` | 0.5 | 0.75 | 0.25 | 0.25 | 20 | 20 |
| sensor_anomaly_prediction | 0 | 1 | 1 | `shuffled_predictive_context` | 0.526316 | `sign_persistence_control` | 0.631579 | `sign_persistence` | 0.631579 | 1 | 0.473684 | 0.368421 | 19 | 19 |

## Aggregate Matrix

| Task | Model | Family | Group | Tail acc | All acc | Corr | Runtime s |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| event_stream_prediction | `current_reflex` | predictive_control | None | 0 | 0 | None | 0.00126638 |
| event_stream_prediction | `external_predictive_scaffold` | CRA | external_scaffold | 1 | 1 | 1 | 20.047 |
| event_stream_prediction | `internal_predictive_context` | CRA | candidate | 1 | 1 | 1 | 16.4589 |
| event_stream_prediction | `no_write_predictive_context` | CRA | predictive_ablation | 0 | 0 | None | 14.0108 |
| event_stream_prediction | `online_perceptron` | linear | None | 0.2 | 0.391304 | -0.163133 | 0.00840246 |
| event_stream_prediction | `permuted_predictive_context` | CRA | predictive_ablation | 0.4 | 0.608696 | 0.195005 | 13.9568 |
| event_stream_prediction | `predictive_memory` | predictive_control | None | 1 | 1 | 1 | 0.00131733 |
| event_stream_prediction | `rolling_majority` | predictive_control | None | 0.2 | 0.26087 | -0.452381 | 0.00595483 |
| event_stream_prediction | `shuffled_predictive_context` | CRA | predictive_ablation | 0.4 | 0.391304 | -0.2599 | 11.3172 |
| event_stream_prediction | `shuffled_target_control` | predictive_control | None | 0.8 | 0.652174 | 0.269841 | 0.00127713 |
| event_stream_prediction | `sign_persistence` | rule | None | 0.4 | 0.391304 | -0.195336 | 0.0151278 |
| event_stream_prediction | `sign_persistence_control` | predictive_control | None | 0.4 | 0.391304 | -0.195336 | 0.00143087 |
| event_stream_prediction | `v1_7_reactive` | CRA | frozen_baseline | 0 | 0 | None | 16.2629 |
| event_stream_prediction | `wrong_horizon_control` | predictive_control | None | 0.4 | 0.391304 | -0.277778 | 0.00150917 |
| event_stream_prediction | `wrong_predictive_context` | CRA | alternate_code_control | 1 | 0.956522 | 0.914174 | 15.2816 |
| masked_input_prediction | `current_reflex` | predictive_control | None | 0 | 0 | None | 0.00309413 |
| masked_input_prediction | `external_predictive_scaffold` | CRA | external_scaffold | 0.8 | 0.75 | 0.486919 | 12.201 |
| masked_input_prediction | `internal_predictive_context` | CRA | candidate | 0.8 | 0.75 | 0.486919 | 18.1467 |
| masked_input_prediction | `no_write_predictive_context` | CRA | predictive_ablation | 0 | 0 | None | 12.1928 |
| masked_input_prediction | `online_perceptron` | linear | None | 0.6 | 0.4 | -0.00983157 | 0.00288604 |
| masked_input_prediction | `permuted_predictive_context` | CRA | predictive_ablation | 0 | 0.5 | -0.01082 | 14.5716 |
| masked_input_prediction | `predictive_memory` | predictive_control | None | 1 | 1 | 1 | 0.00247738 |
| masked_input_prediction | `rolling_majority` | predictive_control | None | 0.6 | 0.6 | 0.24232 | 0.00294296 |
| masked_input_prediction | `shuffled_predictive_context` | CRA | predictive_ablation | 0.2 | 0.35 | -0.288854 | 9.23503 |
| masked_input_prediction | `shuffled_target_control` | predictive_control | None | 0.6 | 0.6 | 0.191919 | 0.00183454 |
| masked_input_prediction | `sign_persistence` | rule | None | 1 | 0.5 | 0.031607 | 0.00856933 |
| masked_input_prediction | `sign_persistence_control` | predictive_control | None | 1 | 0.5 | 0.031607 | 0.00604262 |
| masked_input_prediction | `v1_7_reactive` | CRA | frozen_baseline | 0 | 0 | None | 10.9333 |
| masked_input_prediction | `wrong_horizon_control` | predictive_control | None | 0.2 | 0.3 | -0.414141 | 0.00155621 |
| masked_input_prediction | `wrong_predictive_context` | CRA | alternate_code_control | 1 | 0.95 | 0.904534 | 17.7271 |
| sensor_anomaly_prediction | `current_reflex` | predictive_control | None | 0 | 0 | None | 0.000986209 |
| sensor_anomaly_prediction | `external_predictive_scaffold` | CRA | external_scaffold | 1 | 1 | 1 | 12.2709 |
| sensor_anomaly_prediction | `internal_predictive_context` | CRA | candidate | 1 | 1 | 1 | 15.5626 |
| sensor_anomaly_prediction | `no_write_predictive_context` | CRA | predictive_ablation | 0 | 0 | None | 7.09636 |
| sensor_anomaly_prediction | `online_perceptron` | linear | None | 0.75 | 0.526316 | 0.0511881 | 0.00159542 |
| sensor_anomaly_prediction | `permuted_predictive_context` | CRA | predictive_ablation | 0 | 0.421053 | -0.147138 | 12.5251 |
| sensor_anomaly_prediction | `predictive_memory` | predictive_control | None | 1 | 1 | 1 | 0.00116208 |
| sensor_anomaly_prediction | `rolling_majority` | predictive_control | None | 0.25 | 0.421053 | -0.16855 | 0.00123217 |
| sensor_anomaly_prediction | `shuffled_predictive_context` | CRA | predictive_ablation | 0.25 | 0.526316 | 0.0449677 | 15.854 |
| sensor_anomaly_prediction | `shuffled_target_control` | predictive_control | None | 0.25 | 0.473684 | -0.0555556 | 0.00113296 |
| sensor_anomaly_prediction | `sign_persistence` | rule | None | 0.5 | 0.631579 | 0.287527 | 0.00167438 |
| sensor_anomaly_prediction | `sign_persistence_control` | predictive_control | None | 0.5 | 0.631579 | 0.287527 | 0.00116888 |
| sensor_anomaly_prediction | `v1_7_reactive` | CRA | frozen_baseline | 0 | 0 | None | 10.9986 |
| sensor_anomaly_prediction | `wrong_horizon_control` | predictive_control | None | 0.25 | 0.473684 | -0.0555556 | 0.00107679 |
| sensor_anomaly_prediction | `wrong_predictive_context` | CRA | alternate_code_control | 1 | 0.947368 | 0.9 | 13.5835 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| full variant/baseline/control/task/seed matrix completed | 45 | == 45 | yes |  |
| feedback timing has no leakage violations | 0 | == 0 | yes |  |
| task remains shortcut-ambiguous | True | == True | yes |  |
| candidate predictive context feature is active | 62 | > 0 | yes |  |
| candidate receives predictive-context writes | 62 | > 0 | yes |  |
| metadata exposes precursor writes before decisions | 62 | > 0 | yes |  |
| candidate reaches minimum predictive-task accuracy | 0.75 | >= 0.7 | yes |  |
| candidate reaches minimum tail accuracy | 0.8 | >= 0.75 | yes |  |
| candidate improves over v1.7 reactive CRA | 0.75 | >= 0.15 | yes |  |
| internal candidate approaches external predictive scaffold | 0 | >= -0.1 | yes | Internal predictive context can trail the external scaffold slightly but cannot collapse relative to it. |
| information-destroying predictive shams are worse than candidate | 0.25 | >= 0.15 | yes | Stable wrong-sign coding is reported separately because it can remain learnably informative; the gate uses shuffled/permuted/no-write shams. |
| candidate beats best shortcut control | 0.15 | >= 0.15 | yes |  |
| candidate beats best selected external baseline | 0.25 | >= 0.1 | yes |  |

## Artifacts

- `tier5_12c_results.json`: machine-readable manifest.
- `tier5_12c_report.md`: human findings and claim boundary.
- `tier5_12c_summary.csv`: aggregate task/model metrics.
- `tier5_12c_comparisons.csv`: predictive-context comparison table.
- `tier5_12c_fairness_contract.json`: predeclared comparison/leakage rules.
- `tier5_12c_predictive_context.png`: comparison plot.
- `*_timeseries.csv`: per-task/per-model/per-seed traces.

![predictive_context](tier5_12c_predictive_context.png)
