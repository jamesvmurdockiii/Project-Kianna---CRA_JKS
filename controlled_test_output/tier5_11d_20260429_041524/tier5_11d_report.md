# Tier 5.11d Generic Replay / Consolidation Confirmation Findings

- Generated: `2026-04-29T09:05:07.137947+00:00`
- Status: **PASS**
- Backend: `nest`
- Steps: `960`
- Seeds: `42, 43, 44`
- Tasks: `silent_context_reentry,long_gap_silent_reentry,partial_key_reentry`
- Variants: `all`
- Selected standard baselines: `sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn`
- Output directory: `<repo>/controlled_test_output/tier5_11d_20260429_041524`

Tier 5.11d tests whether correct-binding replay/consolidation itself adds causal value after the Tier 5.11b/5.11c priority-specific gates failed. It is not hardware replay and not native on-chip replay.

## Claim Boundary

- A pass promotes correct-binding replay/consolidation only as a software memory mechanism; it does not prove priority weighting is essential.
- A pass does not prove hardware replay, on-chip replay, general working memory, or compositional reuse.
- Replay events must use only previously observed context episodes and must remain outside online scoring steps.
- Wrong-key, key-label-permuted, priority-only, and no-consolidation controls must not match correct-binding replay. Shuffled-order and random replay are reported as generic replay-opportunity comparators, not priority-specific promotion gates.

## Summary Metrics

- candidate replay events: `1185.0`
- candidate replay consolidations: `1185.0`
- no-consolidation writes: `0.0`
- candidate min all accuracy: `1.0`
- candidate min tail accuracy: `1.0`
- candidate min tail delta vs no replay: `1.0`
- candidate min all gap closure: `1.0`
- candidate min tail gap closure: `1.0`
- candidate min tail edge vs shuffled-order comparator: `0.40740740740740733`
- candidate min tail edge vs random comparator: `0.2962962962962963`
- candidate min tail edge vs wrong-key: `0.5555555555555556`
- candidate min tail edge vs key-label-permuted: `1.0`
- candidate min tail edge vs priority-only: `1.0`
- candidate min tail edge vs no-consolidation: `1.0`

## Task Comparisons

| Task | No replay tail | Candidate tail | Shuffled-order tail | Random tail | Wrong-key tail | Key-label tail | Priority-only tail | No-consolidation tail | Unbounded tail | Tail gain vs no replay | Tail edge vs shuffled-order | Tail edge vs wrong-key | Gap closure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| long_gap_silent_reentry | 0 | 1 | 0.592593 | 0.703704 | 0 | 0 | 0 | 0 | 1 | 1 | 0.407407 | 1 | 1 |
| partial_key_reentry | 0 | 1 | 0.407407 | 0.444444 | 0.444444 | 0 | 0 | 0 | 1 | 1 | 0.592593 | 0.555556 | 1 |
| silent_context_reentry | 0 | 1 | 0.481481 | 0.666667 | 0 | 0 | 0 | 0 | 1 | 1 | 0.518519 | 1 | 1 |

## Aggregate Matrix

| Task | Model | Group | All acc | Tail acc | Replay events | Writes | Replay leakage | Runtime s |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| long_gap_silent_reentry | `key_label_permuted_replay` | replay_ablation | 0.26087 | 0 | 381 | 381 | 0 | 31.2551 |
| long_gap_silent_reentry | `no_consolidation_replay` | replay_ablation | 0.608696 | 0 | 381 | 0 | 0 | 29.5526 |
| long_gap_silent_reentry | `oracle_context_scaffold` | external_scaffold | 1 | 1 | 0 | 0 | 0 | 37.488 |
| long_gap_silent_reentry | `prioritized_replay` | replay_candidate | 1 | 1 | 381 | 381 | 0 | 34.8588 |
| long_gap_silent_reentry | `priority_only_ablation` | replay_ablation | 0.608696 | 0 | 381 | 381 | 0 | 35.4255 |
| long_gap_silent_reentry | `random_replay` | replay_ablation | 0.884058 | 0.703704 | 381 | 381 | 0 | 33.1024 |
| long_gap_silent_reentry | `shuffled_order_replay` | replay_ablation | 0.84058 | 0.592593 | 381 | 381 | 0 | 32.5719 |
| long_gap_silent_reentry | `unbounded_keyed_control` | capacity_upper_bound | 1 | 1 | 0 | 0 | 0 | 29.778 |
| long_gap_silent_reentry | `v1_6_no_replay` | candidate_no_replay | 0.608696 | 0 | 0 | 0 | 0 | 37.4242 |
| long_gap_silent_reentry | `wrong_key_replay` | replay_ablation | 0.521739 | 0 | 381 | 381 | 0 | 36.2162 |
| long_gap_silent_reentry | `echo_state_network` |  | 0.188406 | 0.0740741 | None | None | None | 0.0193407 |
| long_gap_silent_reentry | `memory_reset` |  | 0.565217 | 1 | None | None | None | 0.00559517 |
| long_gap_silent_reentry | `online_logistic_regression` |  | 0.478261 | 0.333333 | None | None | None | 0.006963 |
| long_gap_silent_reentry | `online_perceptron` |  | 0.608696 | 0.555556 | None | None | None | 0.0155045 |
| long_gap_silent_reentry | `oracle_context` |  | 1 | 1 | None | None | None | 0.00872243 |
| long_gap_silent_reentry | `shuffled_context` |  | 0.565217 | 0.703704 | None | None | None | 0.00589918 |
| long_gap_silent_reentry | `sign_persistence` |  | 0.565217 | 1 | None | None | None | 0.00537007 |
| long_gap_silent_reentry | `small_gru` |  | 0.188406 | 0.0740741 | None | None | None | 0.0918295 |
| long_gap_silent_reentry | `stdp_only_snn` |  | 0.492754 | 0.481481 | None | None | None | 0.0373473 |
| long_gap_silent_reentry | `stream_context_memory` |  | 0.608696 | 0 | None | None | None | 0.00952942 |
| long_gap_silent_reentry | `wrong_context` |  | 0 | 0 | None | None | None | 0.00448861 |
| partial_key_reentry | `key_label_permuted_replay` | replay_ablation | 0.4 | 0 | 420 | 420 | 0 | 30.3122 |
| partial_key_reentry | `no_consolidation_replay` | replay_ablation | 0.64 | 0 | 420 | 0 | 0 | 33.2146 |
| partial_key_reentry | `oracle_context_scaffold` | external_scaffold | 1 | 1 | 0 | 0 | 0 | 30.4012 |
| partial_key_reentry | `prioritized_replay` | replay_candidate | 1 | 1 | 420 | 420 | 0 | 31.987 |
| partial_key_reentry | `priority_only_ablation` | replay_ablation | 0.64 | 0 | 420 | 420 | 0 | 31.5914 |
| partial_key_reentry | `random_replay` | replay_ablation | 0.8 | 0.444444 | 420 | 420 | 0 | 30.4084 |
| partial_key_reentry | `shuffled_order_replay` | replay_ablation | 0.786667 | 0.407407 | 420 | 420 | 0 | 31.1128 |
| partial_key_reentry | `unbounded_keyed_control` | capacity_upper_bound | 1 | 1 | 0 | 0 | 0 | 31.5995 |
| partial_key_reentry | `v1_6_no_replay` | candidate_no_replay | 0.64 | 0 | 0 | 0 | 0 | 35.6751 |
| partial_key_reentry | `wrong_key_replay` | replay_ablation | 0.72 | 0.444444 | 420 | 420 | 0 | 33.8716 |
| partial_key_reentry | `echo_state_network` |  | 0.226667 | 0.037037 | None | None | None | 0.0101265 |
| partial_key_reentry | `memory_reset` |  | 0.52 | 1 | None | None | None | 0.00349415 |
| partial_key_reentry | `online_logistic_regression` |  | 0.52 | 0.333333 | None | None | None | 0.00568804 |
| partial_key_reentry | `online_perceptron` |  | 0.6 | 0.555556 | None | None | None | 0.00573063 |
| partial_key_reentry | `oracle_context` |  | 1 | 1 | None | None | None | 0.0032391 |
| partial_key_reentry | `shuffled_context` |  | 0.493333 | 0.592593 | None | None | None | 0.003342 |
| partial_key_reentry | `sign_persistence` |  | 0.52 | 1 | None | None | None | 0.00522775 |
| partial_key_reentry | `small_gru` |  | 0.253333 | 0.037037 | None | None | None | 0.0201634 |
| partial_key_reentry | `stdp_only_snn` |  | 0.493333 | 0.481481 | None | None | None | 0.00932246 |
| partial_key_reentry | `stream_context_memory` |  | 0.64 | 0 | None | None | None | 0.00317451 |
| partial_key_reentry | `wrong_context` |  | 0 | 0 | None | None | None | 0.00328168 |
| silent_context_reentry | `key_label_permuted_replay` | replay_ablation | 0.32 | 0 | 384 | 384 | 0 | 32.0311 |
| silent_context_reentry | `no_consolidation_replay` | replay_ablation | 0.64 | 0 | 384 | 0 | 0 | 37.4833 |
| silent_context_reentry | `oracle_context_scaffold` | external_scaffold | 1 | 1 | 0 | 0 | 0 | 34.8053 |
| silent_context_reentry | `prioritized_replay` | replay_candidate | 1 | 1 | 384 | 384 | 0 | 33.1128 |
| silent_context_reentry | `priority_only_ablation` | replay_ablation | 0.64 | 0 | 384 | 384 | 0 | 33.3976 |
| silent_context_reentry | `random_replay` | replay_ablation | 0.88 | 0.666667 | 384 | 384 | 0 | 31.4465 |
| silent_context_reentry | `shuffled_order_replay` | replay_ablation | 0.813333 | 0.481481 | 384 | 384 | 0 | 31.2486 |
| silent_context_reentry | `unbounded_keyed_control` | capacity_upper_bound | 1 | 1 | 0 | 0 | 0 | 35.0901 |
| silent_context_reentry | `v1_6_no_replay` | candidate_no_replay | 0.64 | 0 | 0 | 0 | 0 | 31.195 |
| silent_context_reentry | `wrong_key_replay` | replay_ablation | 0.56 | 0 | 384 | 384 | 0 | 32.1845 |
| silent_context_reentry | `echo_state_network` |  | 0.173333 | 0.037037 | None | None | None | 0.0143495 |
| silent_context_reentry | `memory_reset` |  | 0.52 | 1 | None | None | None | 0.00344606 |
| silent_context_reentry | `online_logistic_regression` |  | 0.506667 | 0.296296 | None | None | None | 0.00778288 |
| silent_context_reentry | `online_perceptron` |  | 0.64 | 0.555556 | None | None | None | 0.00740164 |
| silent_context_reentry | `oracle_context` |  | 1 | 1 | None | None | None | 0.00449728 |
| silent_context_reentry | `shuffled_context` |  | 0.493333 | 0.592593 | None | None | None | 0.00550846 |
| silent_context_reentry | `sign_persistence` |  | 0.52 | 1 | None | None | None | 0.00609015 |
| silent_context_reentry | `small_gru` |  | 0.253333 | 0.111111 | None | None | None | 0.0331389 |
| silent_context_reentry | `stdp_only_snn` |  | 0.493333 | 0.481481 | None | None | None | 0.0118359 |
| silent_context_reentry | `stream_context_memory` |  | 0.64 | 0 | None | None | None | 0.00803586 |
| silent_context_reentry | `wrong_context` |  | 0 | 0 | None | None | None | 0.00572818 |

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| full replay/control/baseline/task/seed matrix completed | 189 | == 189 | yes |  |
| feedback timing has no leakage violations | 0 | == 0 | yes |  |
| replay uses no future context episodes | 0 | == 0 | yes |  |
| candidate replay selected episodes | 1185 | > 0 | yes |  |
| candidate replay consolidated episodes | 1185 | > 0 | yes |  |
| candidate replay minimum all accuracy | 1 | >= 0.85 | yes |  |
| candidate replay minimum tail accuracy | 1 | >= 0.75 | yes |  |
| candidate replay improves tail over no replay | 1 | >= 0.5 | yes |  |
| candidate replay closes all-accuracy gap toward unbounded | 1 | >= 0.75 | yes |  |
| candidate replay closes tail gap toward unbounded | 1 | >= 0.75 | yes |  |
| wrong-key replay does not match candidate tail | 0.555556 | >= 0.5 | yes |  |
| key-label-permuted replay does not match candidate tail | 1 | >= 0.5 | yes |  |
| priority-only ablation does not match candidate tail | 1 | >= 0.5 | yes |  |
| no-consolidation replay is worse than full replay | 1 | >= 0.5 | yes |  |
| no-consolidation replay performs zero writes | 0 | == 0 | yes |  |
| matched replay control write counts match candidate | 1185 | == 1185 | yes |  |

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
