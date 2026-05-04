# Tier 5.7 Compact Regression Findings

- Generated: `2026-04-28T04:57:08+00:00`
- Status: **PASS**
- Backend: `mock`
- Promoted setting: `readout_lr=0.1`, `delayed_readout_lr=0.2`
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier5_7_20260428_005646`

Tier 5.7 is a compact regression guardrail after the v1.0 promotion. It does not prove a new capability. It checks that the promoted delayed-credit setting does not break negative controls, positive learning, architecture ablations, or the two target hard/adaptive smoke tasks.

## Claim Boundary

- This is software-only regression evidence.
- Passing does not prove lifecycle/self-scaling, hardware scaling, native on-chip learning, compositionality, world modeling, or external-baseline superiority.
- Failure means the promoted setting must be debugged before Tier 6 lifecycle/self-scaling work proceeds.

## Child Runs

| Child | Status | Return Code | Runtime Seconds | Purpose | Manifest |
| --- | --- | ---: | ---: | --- | --- |
| `tier1_controls` | **PASS** | 0 | 4.617 | negative controls stay negative under the promoted learning setting | `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier5_7_20260428_005646/tier1_controls/tier1_results.json` |
| `tier2_learning` | **PASS** | 0 | 3.417 | positive learning controls still pass under the promoted setting | `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier5_7_20260428_005646/tier2_learning/tier2_results.json` |
| `tier3_ablations` | **PASS** | 0 | 11.745 | core mechanism ablation gaps remain meaningful under the promoted setting | `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier5_7_20260428_005646/tier3_ablations/tier3_results.json` |
| `target_task_smokes` | **PASS** | 0 | 2.361 | delayed_cue and hard_noisy_switching smoke matrix still executes with CRA locked | `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier5_7_20260428_005646/target_task_smokes/tier5_6_results.json` |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 1 negative controls pass under promoted setting | `pass` | status == pass and return_code == 0 | yes |
| Tier 2 positive controls pass under promoted setting | `pass` | status == pass and return_code == 0 | yes |
| Tier 3 architecture ablations pass under promoted setting | `pass` | status == pass and return_code == 0 | yes |
| target task smoke matrix completes under promoted setting | `pass` | status == pass and return_code == 0 | yes |

## Required Artifacts

- `tier5_7_results.json`: machine-readable compact-regression manifest.
- `tier5_7_report.md`: this human-readable report.
- `tier5_7_summary.csv`: compact child-run summary.
- `tier5_7_child_manifests.json`: copied child manifest payloads for audit traceability.
- child stdout/stderr logs for every subprocess.
