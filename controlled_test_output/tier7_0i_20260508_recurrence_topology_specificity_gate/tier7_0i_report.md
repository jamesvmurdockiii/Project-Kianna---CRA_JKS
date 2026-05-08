# Tier 7.0i Recurrence / Topology Specificity Gate

- Generated: `2026-05-08T19:30:54+00:00`
- Status: **PASS**
- Criteria: `11/11`
- Outcome: `generic_bounded_recurrent_state_supported_topology_specificity_not_supported`
- Recommendation: Do not claim topology-specific recurrence; consider a narrower generic bounded recurrent-state promotion gate.

## Claim Boundary

Tier 7.0i is software public-benchmark topology-specificity evidence only. It tests whether the Tier 7.0h bounded recurrent gain can be attributed to a structured recurrent topology rather than generic bounded recurrent features. It is not hardware evidence, not native on-chip recurrence, not a baseline freeze, and not AGI/ASI evidence.

## Length Results

| Length | Structured MSE | Generic 7.0h MSE | v2.2 MSE | ESN MSE | Structured/v2.2 improvement | Structured/generic margin |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 720 | 0.1446960415199875 | 0.15026721016608235 | 0.19853975759572184 | 0.02537065477597153 | 1.372116026880367 | 1.0385025643242998 |
| 2000 | 0.2016689501519892 | 0.18530506091614488 | 0.2514764000158321 | 0.06236159958411151 | 1.246976293704634 | 0.9188576663709928 |
| 8000 | 0.09964414908204765 | 0.09530752189727928 | 0.19348969000027122 | 0.020109884207162095 | 1.9418068374586703 | 0.9564788577681811 |

## Longest-Length Topology / Control Margins

- `structured_frozen_state_ablation` margin vs structured candidate: `4.6803890253`
- `structured_no_recurrence_ablation` margin vs structured candidate: `0.9647896490983386`
- `structured_no_update_ablation` margin vs structured candidate: `10.162260352825175`
- `structured_random_rewire_sham` margin vs structured candidate: `0.994286546101554`
- `structured_reversed_cascade_sham` margin vs structured candidate: `1.0`
- `structured_shuffled_state_sham` margin vs structured candidate: `10.386036159671205`
- `structured_shuffled_target_control` margin vs structured candidate: `10.45491495344292`
- `structured_topology_shuffle_sham` margin vs structured candidate: `1.0072740096344246`

## Promotion Checks

- Structured improves versus v2.2: `True`
- Generic 7.0h reference improves versus v2.2: `True`
- Structured beats public online controls: `True`
- Topology controls separated: `False`
- Destructive controls separated: `True`
- Structured matches/beats generic reference: `True`
- Promotion recommended: `False`

## Nonclaims

- not hardware evidence
- not native on-chip recurrence
- not a baseline freeze
- not ESN superiority
- not universal benchmark superiority
- not lifecycle, sleep/replay, planning, language, AGI, or ASI
