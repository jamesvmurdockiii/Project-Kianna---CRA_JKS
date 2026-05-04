# Tier 5.11b Prioritized Replay / Consolidation Intervention Findings

- Generated: `2026-04-29T05:46:30.788290+00:00`
- Status: **PASS**
- Backend: `mock`
- Steps: `240`
- Seeds: `42`
- Tasks: `silent_context_reentry`
- Variants: `all`
- Selected standard baselines: `sign_persistence,online_perceptron`
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier5_11b_20260429_014626`

Tier 5.11b tests whether prioritized offline replay repairs the Tier 5.11a silent-reentry failure. It is not hardware replay and not native on-chip replay.

## Claim Boundary

- A pass promotes prioritized replay only as a software memory/consolidation mechanism candidate.
- A pass does not prove hardware replay, on-chip replay, general working memory, or compositional reuse.
- Replay events must use only previously observed context episodes and must remain outside online scoring steps.
- Shuffled, random, and no-consolidation controls must not match prioritized replay.

## Summary Metrics

- prioritized replay events: `8.0`
- prioritized replay consolidations: `8.0`
- no-consolidation writes: `0.0`
- prioritized min all accuracy: `1.0`
- prioritized min tail accuracy: `1.0`
- prioritized min tail delta vs no replay: `0.0`
- prioritized min all gap closure: `1.0`
- prioritized min tail gap closure: `1.0`
- prioritized min tail edge vs shuffled: `1.0`
- prioritized min tail edge vs random: `0.0`
- prioritized min tail edge vs no-consolidation: `0.0`

## Task Comparisons

| Task | No replay tail | Prioritized tail | Shuffled tail | Random tail | No-consolidation tail | Unbounded tail | Tail gain vs no replay | Tail edge vs shuffled | Tail edge vs random | Gap closure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| silent_context_reentry | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 |

## Aggregate Matrix

| Task | Model | Group | All acc | Tail acc | Replay events | Writes | Replay leakage | Runtime s |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| silent_context_reentry | `no_consolidation_replay` | replay_ablation | 1 | 1 | 8 | 0 | 0 | 0.614543 |
| silent_context_reentry | `oracle_context_scaffold` | external_scaffold | 1 | 1 | 0 | 0 | 0 | 0.612057 |
| silent_context_reentry | `prioritized_replay` | replay_candidate | 1 | 1 | 8 | 8 | 0 | 0.626729 |
| silent_context_reentry | `random_replay` | replay_ablation | 1 | 1 | 8 | 8 | 0 | 0.617567 |
| silent_context_reentry | `shuffled_replay` | replay_ablation | 0.25 | 0 | 8 | 8 | 0 | 0.612524 |
| silent_context_reentry | `unbounded_keyed_control` | capacity_upper_bound | 1 | 1 | 0 | 0 | 0 | 0.619626 |
| silent_context_reentry | `v1_6_no_replay` | candidate_no_replay | 1 | 1 | 0 | 0 | 0 | 0.630825 |
| silent_context_reentry | `memory_reset` |  | 0.75 | 0.666667 | None | None | None | 0.000919208 |
| silent_context_reentry | `online_perceptron` |  | 0.25 | 0 | None | None | None | 0.00141467 |
| silent_context_reentry | `oracle_context` |  | 1 | 1 | None | None | None | 0.000919583 |
| silent_context_reentry | `shuffled_context` |  | 0.5 | 0.333333 | None | None | None | 0.000932917 |
| silent_context_reentry | `sign_persistence` |  | 0.75 | 0.666667 | None | None | None | 0.00140612 |
| silent_context_reentry | `stream_context_memory` |  | 0.75 | 0.333333 | None | None | None | 0.000997791 |
| silent_context_reentry | `wrong_context` |  | 0 | 0 | None | None | None | 0.00135512 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| full replay/control/baseline/task/seed matrix completed | 14 | == 14 | yes |  |
| feedback timing has no leakage violations | 0 | == 0 | yes |  |
| replay uses no future context episodes | 0 | == 0 | yes |  |
| prioritized replay selected episodes | 8 | > 0 | yes |  |
| prioritized replay consolidated episodes | 8 | > 0 | yes |  |

## Artifacts

- `tier5_11b_results.json`: machine-readable manifest.
- `tier5_11b_report.md`: human findings and claim boundary.
- `tier5_11b_summary.csv`: aggregate task/model metrics.
- `tier5_11b_comparisons.csv`: no-replay/replay/control comparison table.
- `tier5_11b_replay_events.csv`: auditable replay selections and writes.
- `tier5_11b_fairness_contract.json`: predeclared replay/fairness/leakage rules.
- `tier5_11b_replay_edges.png`: replay edge plot.
- `*_timeseries.csv`: per-task/per-model/per-seed traces.

![replay_edges](tier5_11b_replay_edges.png)
