# Tier 7.0e Standard Dynamical Benchmark Rerun

- Generated: `2026-05-08T18:40:40+00:00`
- Status: **PASS**
- Matrix mode: `full_diagnostic`
- Criteria: `8/8`
- Outcome: `v2_2_improves_vs_v2_1_but_not_length_competitive`
- Recommendation: Do not blame short length alone; diagnose readout/recurrent/interface gap.

## Claim Boundary

Tier 7.0e is software benchmark evidence only. It reruns the public standard dynamical scoreboard with v2.2 and a length sweep. It is not hardware evidence, not a custom synthetic usefulness claim, not a new baseline freeze, and not AGI/ASI evidence.

## Length Sweep

| Length | v2.2 candidate MSE | Raw v2.1 MSE | Best baseline | Best baseline MSE | Candidate / best baseline | Margin vs raw v2.1 |
| ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 720 | 0.19853975759572184 | 0.7493269520748722 | fixed_esn_train_prefix_ridge_baseline | 0.02537065477597153 | 7.825566953193429 | 3.774190928552936 |
| 2000 | 0.2514764000158321 | 1.3391242823450145 | fixed_esn_train_prefix_ridge_baseline | 0.06236159958411151 | 4.032552110480233 | 5.3250495166174945 |

## Benchmark Stream Validity

- Invalid generated task streams: `0`
## Interpretation

- Candidate improvement first-to-last: `0.7894965793339751`
- Best-baseline improvement first-to-last: `0.40683136650066726`
- Any competitive length: `False`
- Any improvement versus raw v2.1: `True`

## Nonclaims

- not hardware evidence
- not custom synthetic usefulness proof
- not universal benchmark superiority
- not a new baseline freeze
- not language, planning, AGI, or ASI
