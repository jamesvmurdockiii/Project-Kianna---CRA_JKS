# Tier 3 Controlled Architecture Ablation Findings

- Generated: `2026-04-26T19:40:42+00:00`
- Backend: `nest`
- Overall status: **STOPPED**
- Seeds: `42, 43, 44`
- Fixed-pattern steps: `180`
- Ecology steps: `220`
- Output directory: `<repo>/controlled_test_output/tier3_20260426_153850`

Tier 3 asks whether named architecture mechanisms are actually doing work. Each result compares an intact organism against a targeted ablation under the same controlled task.

## Artifact Index

- JSON manifest: `tier3_results.json`
- Summary CSV: `tier3_summary.csv`

## Summary

| Test | Status | Key result | Interpretation |
| --- | --- | --- | --- |
| `no_dopamine_ablation` | **PASS** | intact_tail=1, no_da_tail=0, delta=1 | Dopamine-gated learning matters. |
| `no_plasticity_ablation` | **PASS** | intact_tail=1, frozen_tail=0, delta=1 | Plasticity is required, not just inference. |
| `no_trophic_selection_ablation` | **FAIL** | births=36, tail_delta=0, alive_delta=12 | Failed criteria: trophic selection improves tail accuracy |

## no_dopamine_ablation

Status: **PASS**

Criteria:

| Criterion | Value | Rule | Pass |
| --- | ---: | --- | --- |
| intact learns fixed pattern | 1 | >= 0.75 | yes |
| no-dopamine fails fixed pattern | 0 | <= 0.55 | yes |
| dopamine ablation performance drop | 1 | >= 0.2 | yes |
| ablated dopamine is zero | 0 | <= 1e-09 | yes |
| ablated readout remains frozen | 0 | <= 0.01 | yes |

Case aggregates:

- `intact`: tail_acc_mean=1, max_da_mean=0.999998, births_sum=0, final_alive_mean=1, final_weight_mean=-15.8312
- `no_dopamine`: tail_acc_mean=0, max_da_mean=0, births_sum=0, final_alive_mean=1, final_weight_mean=0.25

Artifacts:

- `comparison_plot_png`: `no_dopamine_ablation_comparison.png`

![no_dopamine_ablation comparison](no_dopamine_ablation_comparison.png)



## no_plasticity_ablation

Status: **PASS**

Criteria:

| Criterion | Value | Rule | Pass |
| --- | ---: | --- | --- |
| intact learns fixed pattern | 1 | >= 0.75 | yes |
| no-plasticity fails fixed pattern | 0 | <= 0.55 | yes |
| plasticity ablation performance drop | 1 | >= 0.2 | yes |
| dopamine still present under plasticity ablation | 0.86291 | >= 0.5 | yes |
| ablated readout remains frozen | 0 | <= 0.01 | yes |

Case aggregates:

- `intact`: tail_acc_mean=1, max_da_mean=0.999998, births_sum=0, final_alive_mean=1, final_weight_mean=-15.8312
- `no_plasticity`: tail_acc_mean=0, max_da_mean=0.86291, births_sum=0, final_alive_mean=1, final_weight_mean=0.25

Artifacts:

- `comparison_plot_png`: `no_plasticity_ablation_comparison.png`

![no_plasticity_ablation comparison](no_plasticity_ablation_comparison.png)



## no_trophic_selection_ablation

Status: **FAIL**

Criteria:

| Criterion | Value | Rule | Pass |
| --- | ---: | --- | --- |
| intact trophic selection produces births | 36 | >= 1 | yes |
| ablated selection has no births | 0 | == 0 | yes |
| ablated selection has no deaths | 0 | == 0 | yes |
| trophic selection expands population | 12 | >= 1 | yes |
| trophic selection improves tail accuracy | 0 | >= 0.05 | no |

Case aggregates:

- `intact`: tail_acc_mean=1, max_da_mean=0.999996, births_sum=36, final_alive_mean=13, final_weight_mean=-6.33481
- `no_trophic_selection`: tail_acc_mean=1, max_da_mean=0.999997, births_sum=0, final_alive_mean=1, final_weight_mean=-1.03709

Artifacts:

- `comparison_plot_png`: `no_trophic_selection_ablation_comparison.png`

![no_trophic_selection_ablation comparison](no_trophic_selection_ablation_comparison.png)


## Stop Condition

Execution stopped after `no_trophic_selection_ablation` because `--stop-on-fail` was enabled.
