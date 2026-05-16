# Tier 5.11d Generic Replay / Consolidation Confirmation Findings

- Generated: `2026-04-29T11:09:09.714510+00:00`
- Status: **PASS**
- Backend: `mock`
- Steps: `240`
- Seeds: `42`
- Tasks: `silent_context_reentry`
- Variants: `all`
- Selected standard baselines: `sign_persistence,online_perceptron`
- Output directory: `<repo>/controlled_test_output/tier5_12d_20260429_070615/replay_consolidation_guardrail`

Tier 5.11d tests whether correct-binding replay/consolidation itself adds causal value after the Tier 5.11b/5.11c priority-specific gates failed. It is not hardware replay and not native on-chip replay.

## Claim Boundary

- A pass promotes correct-binding replay/consolidation only as a software memory mechanism; it does not prove priority weighting is essential.
- A pass does not prove hardware replay, on-chip replay, general working memory, or compositional reuse.
- Replay events must use only previously observed context episodes and must remain outside online scoring steps.
- Wrong-key, key-label-permuted, priority-only, and no-consolidation controls must not match correct-binding replay. Shuffled-order and random replay are reported as generic replay-opportunity comparators, not priority-specific promotion gates.

## Summary Metrics

- candidate replay events: `8.0`
- candidate replay consolidations: `8.0`
- no-consolidation writes: `0.0`
- candidate min all accuracy: `1.0`
- candidate min tail accuracy: `1.0`
- candidate min tail delta vs no replay: `0.0`
- candidate min all gap closure: `1.0`
- candidate min tail gap closure: `1.0`
- candidate min tail edge vs shuffled-order comparator: `0.0`
- candidate min tail edge vs random comparator: `0.0`
- candidate min tail edge vs wrong-key: `1.0`
- candidate min tail edge vs key-label-permuted: `1.0`
- candidate min tail edge vs priority-only: `0.0`
- candidate min tail edge vs no-consolidation: `0.0`

## Task Comparisons

| Task | No replay tail | Candidate tail | Shuffled-order tail | Random tail | Wrong-key tail | Key-label tail | Priority-only tail | No-consolidation tail | Unbounded tail | Tail gain vs no replay | Tail edge vs shuffled-order | Tail edge vs wrong-key | Gap closure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| silent_context_reentry | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 1 | 1 |

## Aggregate Matrix

| Task | Model | Group | All acc | Tail acc | Replay events | Writes | Replay leakage | Runtime s |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| silent_context_reentry | `key_label_permuted_replay` | replay_ablation | 0.25 | 0 | 8 | 8 | 0 | 0.591672 |
| silent_context_reentry | `no_consolidation_replay` | replay_ablation | 1 | 1 | 8 | 0 | 0 | 0.590606 |
| silent_context_reentry | `oracle_context_scaffold` | external_scaffold | 1 | 1 | 0 | 0 | 0 | 0.614055 |
| silent_context_reentry | `prioritized_replay` | replay_candidate | 1 | 1 | 8 | 8 | 0 | 0.939419 |
| silent_context_reentry | `priority_only_ablation` | replay_ablation | 1 | 1 | 8 | 8 | 0 | 0.594387 |
| silent_context_reentry | `random_replay` | replay_ablation | 1 | 1 | 8 | 8 | 0 | 0.689321 |
| silent_context_reentry | `shuffled_order_replay` | replay_ablation | 1 | 1 | 8 | 8 | 0 | 0.754452 |
| silent_context_reentry | `unbounded_keyed_control` | capacity_upper_bound | 1 | 1 | 0 | 0 | 0 | 0.612102 |
| silent_context_reentry | `v1_6_no_replay` | candidate_no_replay | 1 | 1 | 0 | 0 | 0 | 0.708966 |
| silent_context_reentry | `wrong_key_replay` | replay_ablation | 0.5 | 0 | 8 | 8 | 0 | 0.65133 |
| silent_context_reentry | `memory_reset` |  | 0.75 | 0.666667 | None | None | None | 0.00103413 |
| silent_context_reentry | `online_perceptron` |  | 0.25 | 0 | None | None | None | 0.00139108 |
| silent_context_reentry | `oracle_context` |  | 1 | 1 | None | None | None | 0.000943375 |
| silent_context_reentry | `shuffled_context` |  | 0.5 | 0.333333 | None | None | None | 0.000898792 |
| silent_context_reentry | `sign_persistence` |  | 0.75 | 0.666667 | None | None | None | 0.001331 |
| silent_context_reentry | `stream_context_memory` |  | 0.75 | 0.333333 | None | None | None | 0.000909583 |
| silent_context_reentry | `wrong_context` |  | 0 | 0 | None | None | None | 0.0009325 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| full replay/control/baseline/task/seed matrix completed | 17 | == 17 | yes |  |
| feedback timing has no leakage violations | 0 | == 0 | yes |  |
| replay uses no future context episodes | 0 | == 0 | yes |  |
| candidate replay selected episodes | 8 | > 0 | yes |  |
| candidate replay consolidated episodes | 8 | > 0 | yes |  |

## Artifacts

- `tier5_11d_results.json`: machine-readable manifest.
- `tier5_11d_report.md`: human findings and claim boundary.
- `tier5_11d_summary.csv`: aggregate task/model metrics.
- `tier5_11d_comparisons.csv`: no-replay/replay/control comparison table.
- `tier5_11d_replay_events.csv`: auditable replay selections and writes.
- `tier5_11d_fairness_contract.json`: predeclared replay/fairness/leakage rules.
- `tier5_11d_replay_edges.png`: replay edge plot.
- `*_timeseries.csv`: per-task/per-model/per-seed traces.

![replay_edges](tier5_11d_replay_edges.png)
