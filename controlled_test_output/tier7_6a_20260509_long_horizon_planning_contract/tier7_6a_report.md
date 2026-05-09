# Tier 7.6a Long-Horizon Planning / Subgoal-Control Contract

- Generated: `2026-05-09T04:08:38+00:00`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier7_6a_20260509_long_horizon_planning_contract`
- Runner revision: `tier7_6a_long_horizon_planning_contract_20260509_0001`
- Criteria: `19/19`
- Next gate: `Tier 7.6b - Long-Horizon Planning / Subgoal-Control Local Diagnostic`

## Question

Can CRA use bounded internal state to select and maintain subgoals over multi-step horizons, improving delayed sparse-return tasks beyond reactive policy/action selection and fair planning/RL baselines?

## Hypothesis

A bounded subgoal-control layer that uses context memory, routing, predictive state, and self-evaluation can improve multi-step goal completion, recovery after blocked subgoals, and regret versus reactive CRA references under causal observations.

## Null Hypothesis

CRA's proposed subgoal-control path does not outperform reactive v2.4, no-planning ablations, or simple planning/RL baselines under identical action budgets and hidden holdout schedules.

## Boundary

Contract only. No planning score, no public usefulness claim, no new baseline freeze, no hardware/native transfer, and no language, AGI, or ASI claim.

## Criteria

| Criterion | Value | Rule | Pass | Details |
| --- | --- | --- | --- | --- |
| tier7_5d_prerequisite_exists | `True` | must exist | yes | /Users/james/JKS:CRA/controlled_test_output/tier7_5d_20260509_curriculum_environment_attribution_closeout/tier7_5d_results.json |
| tier7_5d_prerequisite_passed | `PASS` | case-insensitive == PASS | yes |  |
| contract_question_defined | `True` | non-empty | yes |  |
| hypothesis_defined | `True` | non-empty | yes |  |
| null_hypothesis_defined | `True` | non-empty | yes |  |
| task_families_declared | `5` | >= 5 | yes |  |
| splits_declared | `4` | >= 4 | yes |  |
| baselines_declared | `9` | >= 8 | yes |  |
| planning_rl_baselines_included | `True` | must include simple planning/RL baselines | yes |  |
| shams_declared | `9` | >= 8 | yes |  |
| metrics_declared | `9` | >= 8 | yes |  |
| leakage_guards_declared | `6` | >= 6 | yes |  |
| pass_fail_rules_declared | `9` | >= 8 | yes |  |
| nonclaims_declared | `6` | >= 6 | yes |  |
| expected_artifacts_declared | `8` | >= 8 | yes |  |
| contract_no_scoring | `False` | must be False | yes |  |
| contract_no_freeze | `False` | must be False | yes |  |
| contract_no_hardware_transfer | `False` | must be False | yes |  |
| next_gate_selected | `Tier 7.6b - Long-Horizon Planning / Subgoal-Control Local Diagnostic` | == Tier 7.6b - Long-Horizon Planning / Subgoal-Control Local Diagnostic | yes |  |
