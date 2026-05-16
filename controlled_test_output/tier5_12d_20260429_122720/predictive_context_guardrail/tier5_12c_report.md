# Tier 5.12c Internal Predictive Context Mechanism Findings

- Generated: `2026-04-29T16:32:39+00:00`
- Status: **PASS**
- Steps: `240`
- Seeds: `42`
- Tasks: `masked_input_prediction,event_stream_prediction,sensor_anomaly_prediction`
- Variants: `all`
- Selected standard baselines: `sign_persistence,online_perceptron`
- Backend: `nest`
- Smoke mode: `False`
- Output directory: `<repo>/controlled_test_output/tier5_12d_20260429_122720/predictive_context_guardrail`

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
| event_stream_prediction | `current_reflex` | predictive_control | None | 0 | 0 | None | 0.000964125 |
| event_stream_prediction | `external_predictive_scaffold` | CRA | external_scaffold | 1 | 1 | 1 | 6.27356 |
| event_stream_prediction | `internal_predictive_context` | CRA | candidate | 1 | 1 | 1 | 6.42341 |
| event_stream_prediction | `no_write_predictive_context` | CRA | predictive_ablation | 0 | 0 | None | 6.22209 |
| event_stream_prediction | `online_perceptron` | linear | None | 0.2 | 0.391304 | -0.163133 | 0.00158388 |
| event_stream_prediction | `permuted_predictive_context` | CRA | predictive_ablation | 0.4 | 0.608696 | 0.195005 | 6.32489 |
| event_stream_prediction | `predictive_memory` | predictive_control | None | 1 | 1 | 1 | 0.00106567 |
| event_stream_prediction | `rolling_majority` | predictive_control | None | 0.2 | 0.26087 | -0.452381 | 0.00129563 |
| event_stream_prediction | `shuffled_predictive_context` | CRA | predictive_ablation | 0.4 | 0.391304 | -0.2599 | 6.33561 |
| event_stream_prediction | `shuffled_target_control` | predictive_control | None | 0.8 | 0.652174 | 0.269841 | 0.00114571 |
| event_stream_prediction | `sign_persistence` | rule | None | 0.4 | 0.391304 | -0.195336 | 0.00144917 |
| event_stream_prediction | `sign_persistence_control` | predictive_control | None | 0.4 | 0.391304 | -0.195336 | 0.00108775 |
| event_stream_prediction | `v1_7_reactive` | CRA | frozen_baseline | 0 | 0 | None | 6.15356 |
| event_stream_prediction | `wrong_horizon_control` | predictive_control | None | 0.4 | 0.391304 | -0.277778 | 0.00108254 |
| event_stream_prediction | `wrong_predictive_context` | CRA | alternate_code_control | 1 | 0.956522 | 0.914174 | 6.25484 |
| masked_input_prediction | `current_reflex` | predictive_control | None | 0 | 0 | None | 0.000985167 |
| masked_input_prediction | `external_predictive_scaffold` | CRA | external_scaffold | 0.8 | 0.75 | 0.486919 | 6.20179 |
| masked_input_prediction | `internal_predictive_context` | CRA | candidate | 0.8 | 0.75 | 0.486919 | 6.24184 |
| masked_input_prediction | `no_write_predictive_context` | CRA | predictive_ablation | 0 | 0 | None | 6.1742 |
| masked_input_prediction | `online_perceptron` | linear | None | 0.6 | 0.4 | -0.00983157 | 0.00150642 |
| masked_input_prediction | `permuted_predictive_context` | CRA | predictive_ablation | 0 | 0.5 | -0.01082 | 6.22043 |
| masked_input_prediction | `predictive_memory` | predictive_control | None | 1 | 1 | 1 | 0.00106871 |
| masked_input_prediction | `rolling_majority` | predictive_control | None | 0.6 | 0.6 | 0.24232 | 0.00126263 |
| masked_input_prediction | `shuffled_predictive_context` | CRA | predictive_ablation | 0.2 | 0.35 | -0.288854 | 6.26246 |
| masked_input_prediction | `shuffled_target_control` | predictive_control | None | 0.6 | 0.6 | 0.191919 | 0.00107346 |
| masked_input_prediction | `sign_persistence` | rule | None | 1 | 0.5 | 0.031607 | 0.00143417 |
| masked_input_prediction | `sign_persistence_control` | predictive_control | None | 1 | 0.5 | 0.031607 | 0.00114717 |
| masked_input_prediction | `v1_7_reactive` | CRA | frozen_baseline | 0 | 0 | None | 6.10794 |
| masked_input_prediction | `wrong_horizon_control` | predictive_control | None | 0.2 | 0.3 | -0.414141 | 0.00118096 |
| masked_input_prediction | `wrong_predictive_context` | CRA | alternate_code_control | 1 | 0.95 | 0.904534 | 6.22183 |
| sensor_anomaly_prediction | `current_reflex` | predictive_control | None | 0 | 0 | None | 0.000971458 |
| sensor_anomaly_prediction | `external_predictive_scaffold` | CRA | external_scaffold | 1 | 1 | 1 | 6.31185 |
| sensor_anomaly_prediction | `internal_predictive_context` | CRA | candidate | 1 | 1 | 1 | 6.28847 |
| sensor_anomaly_prediction | `no_write_predictive_context` | CRA | predictive_ablation | 0 | 0 | None | 6.22551 |
| sensor_anomaly_prediction | `online_perceptron` | linear | None | 0.75 | 0.526316 | 0.0511881 | 0.00149042 |
| sensor_anomaly_prediction | `permuted_predictive_context` | CRA | predictive_ablation | 0 | 0.421053 | -0.147138 | 6.27321 |
| sensor_anomaly_prediction | `predictive_memory` | predictive_control | None | 1 | 1 | 1 | 0.00116175 |
| sensor_anomaly_prediction | `rolling_majority` | predictive_control | None | 0.25 | 0.421053 | -0.16855 | 0.00119892 |
| sensor_anomaly_prediction | `shuffled_predictive_context` | CRA | predictive_ablation | 0.25 | 0.526316 | 0.0449677 | 6.32769 |
| sensor_anomaly_prediction | `shuffled_target_control` | predictive_control | None | 0.25 | 0.473684 | -0.0555556 | 0.00108125 |
| sensor_anomaly_prediction | `sign_persistence` | rule | None | 0.5 | 0.631579 | 0.287527 | 0.00136358 |
| sensor_anomaly_prediction | `sign_persistence_control` | predictive_control | None | 0.5 | 0.631579 | 0.287527 | 0.00110175 |
| sensor_anomaly_prediction | `v1_7_reactive` | CRA | frozen_baseline | 0 | 0 | None | 6.15701 |
| sensor_anomaly_prediction | `wrong_horizon_control` | predictive_control | None | 0.25 | 0.473684 | -0.0555556 | 0.00112917 |
| sensor_anomaly_prediction | `wrong_predictive_context` | CRA | alternate_code_control | 1 | 0.947368 | 0.9 | 6.35164 |

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
