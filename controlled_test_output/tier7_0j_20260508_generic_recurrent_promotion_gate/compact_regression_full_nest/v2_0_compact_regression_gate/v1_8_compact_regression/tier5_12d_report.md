# Tier 5.12d Predictive-Context Compact Regression Findings

- Generated: `2026-05-08T19:48:31+00:00`
- Status: **PASS**
- Backend: `nest`
- Candidate baseline: `v1.8_host_predictive_context`, `readout_lr=0.1`, `delayed_readout_lr=0.2`
- Output directory: `<repo>/controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate/compact_regression_full_nest/v2_0_compact_regression_gate/v1_8_compact_regression`

Tier 5.12d is a compact regression and promotion guardrail after the Tier 5.12c predictive-context sham-separation pass. It does not prove a new capability beyond 5.12c. It checks that the candidate host-side predictive-context mechanism does not break negative controls, positive learning, architecture ablations, v1.7 replay/consolidation evidence, or the two target hard/adaptive smoke tasks.

## Claim Boundary

- This is software-only regression evidence.
- Passing authorizes a bounded v1.8 software baseline freeze for visible predictive-context tasks only.
- Passing does not prove hidden-regime inference, full world modeling, language, planning, lifecycle/self-scaling, hardware prediction, hardware scaling, native on-chip learning, compositionality, or external-baseline superiority.
- Failure means the predictive-context mechanism remains non-promoted and v1.7 stays the active carried-forward baseline.

## Child Runs

| Child | Status | Return Code | Runtime Seconds | Purpose | Manifest |
| --- | --- | ---: | ---: | --- | --- |
| `tier1_controls` | **PASS** | 0 | 30.938 | negative controls stay negative under the candidate v1.8 predictive-context baseline | `<repo>/controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate/compact_regression_full_nest/v2_0_compact_regression_gate/v1_8_compact_regression/tier1_controls/tier1_results.json` |
| `tier2_learning` | **PASS** | 0 | 17.710 | positive learning controls still pass under the candidate v1.8 predictive-context baseline | `<repo>/controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate/compact_regression_full_nest/v2_0_compact_regression_gate/v1_8_compact_regression/tier2_learning/tier2_results.json` |
| `tier3_ablations` | **PASS** | 0 | 122.143 | core mechanism ablation gaps remain meaningful under the candidate v1.8 predictive-context baseline | `<repo>/controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate/compact_regression_full_nest/v2_0_compact_regression_gate/v1_8_compact_regression/tier3_ablations/tier3_results.json` |
| `target_task_smokes` | **PASS** | 0 | 9.455 | delayed_cue and hard_noisy_switching smoke matrix still executes with the carried-forward CRA path | `<repo>/controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate/compact_regression_full_nest/v2_0_compact_regression_gate/v1_8_compact_regression/target_task_smokes/tier5_6_results.json` |
| `replay_consolidation_guardrail` | **PASS** | 0 | 10.033 | v1.7 replay/consolidation mechanism still passes a compact bounded-memory guardrail | `<repo>/controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate/compact_regression_full_nest/v2_0_compact_regression_gate/v1_8_compact_regression/replay_consolidation_guardrail/tier5_11d_results.json` |
| `predictive_context_guardrail` | **PASS** | 0 | 152.686 | Tier 5.12c predictive-context candidate still beats shams on a compact predictive task matrix | `<repo>/controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate/compact_regression_full_nest/v2_0_compact_regression_gate/v1_8_compact_regression/predictive_context_guardrail/tier5_12c_results.json` |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 1 negative controls pass under candidate v1.8 baseline | `pass` | status == pass and return_code == 0 | yes |
| Tier 2 positive controls pass under candidate v1.8 baseline | `pass` | status == pass and return_code == 0 | yes |
| Tier 3 architecture ablations pass under candidate v1.8 baseline | `pass` | status == pass and return_code == 0 | yes |
| target task smoke matrix completes under candidate v1.8 baseline | `pass` | status == pass and return_code == 0 | yes |
| v1.7 replay/consolidation guardrail remains intact | `pass` | status == pass and return_code == 0 | yes |
| predictive-context sham-separation guardrail passes | `pass` | status == pass and return_code == 0 | yes |

## Required Artifacts

- `tier5_12d_results.json`: machine-readable compact-regression manifest.
- `tier5_12d_report.md`: this human-readable report.
- `tier5_12d_summary.csv`: compact child-run summary.
- `tier5_12d_child_manifests.json`: copied child manifest payloads for audit traceability.
- child stdout/stderr logs for every subprocess.
