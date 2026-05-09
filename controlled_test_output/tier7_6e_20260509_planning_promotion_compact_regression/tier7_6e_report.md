# Tier 7.6e Planning/Subgoal-Control Promotion Gate

- Generated: `2026-05-09T05:12:22+00:00`
- Status: **PASS**
- Criteria: `20/20`
- Outcome: `reduced_feature_planning_ready_for_v2_5_freeze`
- Freeze authorized: `True`
- Hardware transfer authorized: `False`

## Claim Boundary

# Tier 7.6e Claim Boundary

- Outcome: `reduced_feature_planning_ready_for_v2_5_freeze`
- Freeze authorized: `True`
- Hardware/native transfer authorized: `False`
- Broad planning claim authorized: `False`

## Authorized Claim

Reduced-feature planning/subgoal-control improves bounded local planning diagnostics under aliased context/route/memory features and survives compact regression.

## Nonclaims

- not public usefulness proof
- not broad planning or reasoning
- not language
- not hardware/native transfer
- not autonomous on-chip planning
- not AGI
- not ASI


## Locked Tier 7.6d Support

- supported families: `4` / `5`
- supported family IDs: `two_stage_delayed_goal_chain, resource_budget_route_plan, blocked_subgoal_recovery, hierarchical_composition_holdout`
- candidate return mean: `11.460606060606061`
- best non-oracle baseline: `dyna_q_model_based_baseline` at `6.97`
- best sham/ablation: `self_evaluation_disabled` at `7.473939393939394`
- CI low vs best non-oracle: `3.354848484848485`
- CI low vs best sham: `2.860909090909091`

## Compact Guardrail

- compact mode: `full`
- compact backend: `nest`
- compact pass: `True`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier7_6e_planning_promotion_compact_regression_20260509_0001` | expected current source | yes |
| Tier 7.6d exists | `/Users/james/JKS:CRA/controlled_test_output/tier7_6d_20260509_reduced_feature_planning_generalization/tier7_6d_results.json` | exists | yes |
| v2.4 baseline exists | `/Users/james/JKS:CRA/baselines/CRA_EVIDENCE_BASELINE_v2.4.json` | exists | yes |
| Tier 7.6d passed | `PASS` | == PASS | yes |
| Tier 7.6d candidate outcome | `reduced_feature_planning_signal_supported_requires_promotion_gate` | == reduced_feature_planning_signal_supported_requires_promotion_gate | yes |
| Tier 7.6d reduced-feature signal authorized | `True` | == true | yes |
| supported family count | `4` | >= 4 | yes |
| prior weak families repaired | `True` | == true | yes |
| return margin vs best non-oracle | `4.490606060606061` | > 0 | yes |
| return CI low vs best non-oracle | `3.354848484848485` | > 0 | yes |
| return margin vs best sham | `3.9866666666666672` | > 0 | yes |
| return CI low vs best sham | `2.860909090909091` | > 0 | yes |
| source gate did not already freeze | `False` | == false | yes |
| source gate did not authorize hardware | `False` | == false | yes |
| source gate did not authorize broad planning | `False` | == false | yes |
| compact regression guardrail pass | `True` | == true | yes |
| full compact regression for freeze | `True` | == true for freeze authorization | yes |
| freeze compact backend is non-mock | `True` | nest or brian2 required for freeze | yes |
| hardware transfer remains blocked | `False` | == false | yes |
| broad planning claim remains blocked | `False` | == false | yes |

## Nonclaims

- not public usefulness proof
- not broad planning or reasoning
- not language
- not hardware/native transfer
- not autonomous on-chip planning
- not AGI
- not ASI
