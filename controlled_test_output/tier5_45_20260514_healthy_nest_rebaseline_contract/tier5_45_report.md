# Tier 5.45 — Healthy-NEST Rebaseline Decision Contract

- Generated: `2026-05-15T01:17:53+00:00`
- Status: **PASS**
- Outcome: `healthy_nest_rebaseline_contract_locked`
- Runner revision: `tier5_45_healthy_nest_rebaseline_contract_20260514_0001`
- Next gate: `Tier 5.45a — Healthy-NEST Rebaseline Scoring Gate`

## Question

After the NEST fallback correction and repo-alignment cleanup, do any currently opt-in organism-development mechanisms improve prediction or a predeclared substrate metric enough to justify promotion beyond the v2.7 diagnostic snapshot?

## Conditions

- Reference models: `v2_6_predictive_reference, organism_defaults_experimental_off, persistence_baseline, online_linear_or_lag_ridge, esn_or_random_reservoir`
- Tasks: `sine, mackey_glass, lorenz, narma10`
- Seeds: `42, 43, 44`
- Experimental flags: `15` current `LifecycleConfig` opt-in flags

## Promotion Boundary

Contract only. This tier does not prove a mechanism, freeze a baseline, claim hardware transfer, claim public usefulness, or claim AGI/ASI relevance.

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| question locked | `True` | `true` | yes |
| experimental flags exist | `[]` | `[]` | yes |
| experimental defaults off | `[]` | `[]` | yes |
| all single-feature conditions declared | `15` | `== 15` | yes |
| v2.6 reference included | `True` | `true` | yes |
| organism conservative baseline included | `True` | `true` | yes |
| external baselines included | `3` | `>= 3` | yes |
| standard tasks included | `['sine', 'mackey_glass', 'lorenz', 'narma10']` | `contains sine, MG, Lorenz, NARMA10` | yes |
| three seeds locked | `[42, 43, 44]` | `== [42, 43, 44]` | yes |
| zero fallback metric required | `True` | `true` | yes |
| fallback-blocked outcome defined | `True` | `true` | yes |
| no baseline freeze in contract | `contract_only` | `no freeze claim` | yes |

## Decision

This contract authorizes Tier 5.45a scoring only. Promotion requires the scoring gate, sham separation, zero fallback, and documentation updates.
