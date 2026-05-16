# Tier 7.4c Cost-Aware Policy/Action Promotion Gate

- Generated: `2026-05-09T01:52:33+00:00`
- Status: **PASS**
- Criteria: `16/16`
- Outcome: `cost_aware_policy_ready_for_v2_4_freeze`
- Freeze authorized: `True`
- Hardware transfer authorized: `False`

## Claim Boundary

Tier 7.4c is a software-only promotion/regression gate for the cost-aware policy/action candidate. It may authorize a v2.4 software freeze, but it is not public usefulness proof, not hardware/native transfer, not planning, and not AGI/ASI evidence.

## Locked Tier 7.4b Support

- v2.3 expected utility mean: `18.046296296296294`
- best external baseline: `fixed_train_only_threshold` at `5.924382716049381`
- best sham/ablation: `random_confidence_ablation` at `15.10277777777778`
- utility margin vs external: `12.121913580246913`
- utility margin vs sham: `2.9435185185185144`
- task-family wins vs external: `2`
- action rate mean: `0.0837962962962963`
- window recall mean: `0.9865196078431373`

## Compact Guardrail

- compact mode: `full`
- compact backend: `nest`
- compact pass: `True`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier7_4c_cost_aware_policy_action_promotion_gate_20260509_0001` | expected current source | yes |
| Tier 7.4b exists | `<repo>/controlled_test_output/tier7_4b_20260509_cost_aware_policy_action_local_diagnostic/tier7_4b_results.json` | exists | yes |
| v2.3 baseline exists | `<repo>/baselines/CRA_EVIDENCE_BASELINE_v2.3.json` | exists | yes |
| Tier 7.4b passed | `pass` | == pass | yes |
| Tier 7.4b candidate outcome | `cost_aware_policy_candidate_requires_regression` | == cost_aware_policy_candidate_requires_regression | yes |
| v2.3 policy best non-oracle | `v2_3_cost_aware_policy` | == v2_3_cost_aware_policy | yes |
| utility margin vs external positive | `12.121913580246913` | > 0 | yes |
| utility margin vs sham positive | `2.9435185185185144` | > 0 | yes |
| task-family wins vs external | `2` | >= 2 | yes |
| no-action collapse blocked | `{'action_rate': 0.0837962962962963, 'window_recall': 0.9865196078431373}` | 0.01 <= action_rate <= 0.35 and recall >= 0.65 | yes |
| source gate did not already freeze | `False` | == false | yes |
| source gate did not authorize hardware transfer | `False` | == false | yes |
| compact regression guardrail pass | `True` | == true | yes |
| full compact regression for freeze | `True` | == true for freeze authorization | yes |
| freeze compact backend is non-mock | `True` | nest or brian2 required for freeze | yes |
| hardware transfer remains blocked | `False` | == false | yes |

## Nonclaims

- not public usefulness proof
- not broad anomaly benchmark superiority
- not reinforcement learning solved
- not long-horizon planning
- not hardware/native transfer
- not language
- not AGI
- not ASI
