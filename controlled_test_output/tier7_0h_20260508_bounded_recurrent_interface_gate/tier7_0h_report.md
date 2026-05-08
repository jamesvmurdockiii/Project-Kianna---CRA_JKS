# Tier 7.0h Bounded Recurrent Interface Gate

- Generated: `2026-05-08T19:12:11+00:00`
- Status: **PASS**
- Criteria: `10/10`
- Outcome: `bounded_recurrent_candidate_improves_scoreboard_but_topology_specificity_unproven`
- Recommendation: Do not freeze yet; run topology-specificity repair/gate before promoting bounded nonlinear recurrence.

## Claim Boundary

Tier 7.0h is software public-benchmark mechanism evidence only. It tests a bounded nonlinear recurrent continuous-state/interface candidate against v2.2, public baselines, and shams. It is not hardware evidence, not native on-chip recurrence, not a baseline freeze, and not AGI/ASI evidence.

## Length Results

| Length | Candidate MSE | v2.2 MSE | ESN MSE | Candidate/v2.2 improvement | Candidate/ESN | Lag margin | Reservoir margin |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 720 | 0.15026721016608235 | 0.19853975759572184 | 0.02537065477597153 | 1.3212447171694104 | 5.922874734332831 | 1.0227245586180096 | 1.658450088754954 |
| 2000 | 0.18530506091614488 | 0.2514764000158321 | 0.06236159958411151 | 1.3570940738074682 | 2.9714609976642885 | 1.2782504050065353 | 1.7191153608430876 |
| 8000 | 0.09530752189727928 | 0.19348969000027122 | 0.020109884207162095 | 2.0301617978149813 | 4.739337179442122 | 2.0841080274002146 | 2.177455353142288 |

## Longest-Length Control Margins

- `frozen_state_ablation` margin vs candidate: `4.849540129883862`
- `no_update_ablation` margin vs candidate: `10.624657586825794`
- `permuted_recurrence_sham` margin vs candidate: `1.036590722013174`
- `recurrent_hidden_only_ablation` margin vs candidate: `2.781374506877662`
- `shuffled_state_sham` margin vs candidate: `10.857665025380983`
- `shuffled_target_control` margin vs candidate: `10.925543333237488`
- `state_reset_ablation` margin vs candidate: `1.1176534809685916`

## Promotion Checks

- Material improvement versus v2.2: `2.0301617978149813`
- Beats lag and random-reservoir online controls: `True`
- ESN gap narrowed: `True`
- Destructive controls separated: `True`
- Recurrence/topology controls separated: `False`
- Promotion recommended: `False`

## Nonclaims

- not hardware evidence
- not native on-chip recurrence
- not a baseline freeze
- not ESN superiority
- not universal benchmark superiority
- not sleep/replay, lifecycle, planning, language, AGI, or ASI
