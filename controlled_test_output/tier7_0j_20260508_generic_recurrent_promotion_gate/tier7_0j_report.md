# Tier 7.0j Generic Bounded Recurrent-State Promotion Gate

- Generated: `2026-05-08T20:10:52+00:00`
- Status: **PASS**
- Outcome: `generic_bounded_recurrent_state_ready_for_v2_3_freeze`
- Freeze authorized: `True`

## Claim Boundary

Tier 7.0j is a software-only promotion/regression gate for a narrow generic bounded recurrent-state interface. It cannot claim topology-specific recurrence, ESN superiority, hardware transfer, native/on-chip recurrence, language, planning, AGI, or ASI.

## Locked 8000-Step Public Scoreboard

| Model | Aggregate geomean MSE |
| --- | ---: |
| ESN | 0.020109884207162095 |
| generic bounded recurrent candidate | 0.09530752189727928 |
| structured recurrence candidate | 0.09964414908204765 |
| v2.2 fading memory | 0.19348969000027122 |
| lag-only LMS | 0.1986311714577415 |
| random reservoir | 0.2075278737499566 |

## Promotion Logic

- generic margin vs v2.2: `2.0301617978149813`
- generic margin vs lag-only: `2.0841080274002146`
- generic margin vs reservoir: `2.177455353142288`
- v2.2 / ESN ratio: `9.621621288667603`
- generic / ESN ratio: `4.739337179442122`
- topology nonclaim preserved: `True`

## Compact Guardrail

- compact mode: `full`
- compact backend: `nest`
- compact pass: `True`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier7_0j_generic_recurrent_promotion_gate_20260508_0001` | expected current source | yes |
| v2.2 baseline artifact exists | `/Users/james/JKS:CRA/baselines/CRA_EVIDENCE_BASELINE_v2.2.json` | exists | yes |
| Tier 7.0h source result pass | `pass` | == pass | yes |
| Tier 7.0i source result pass | `pass` | == pass | yes |
| locked public length | `8000` | == 8000 | yes |
| generic improves v2.2 | `2.0301617978149813` | >= 1.25 | yes |
| generic beats lag-only online control | `2.0841080274002146` | > 1.0 | yes |
| generic beats random reservoir online control | `2.177455353142288` | > 1.0 | yes |
| generic narrows ESN gap | `4.739337179442122` | < v2.2/ESN | yes |
| destructive controls separated | `[True, True]` | both true | yes |
| topology nonclaim preserved | `True` | == true | yes |
| compact regression guardrail pass | `True` | == true unless compact-mode skip | yes |
| full compact regression for freeze | `True` | == true for freeze authorization | yes |
| freeze compact backend is non-mock | `True` | nest or brian2 required for freeze | yes |

## Nonclaims

- not topology-specific recurrence
- not ESN superiority
- not hardware evidence
- not native on-chip recurrence
- not language
- not planning
- not AGI
- not ASI
