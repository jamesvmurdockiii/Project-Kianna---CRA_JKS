# Tier 7.0e Standard Dynamical Benchmark Rerun

- Generated: `2026-05-08T18:32:32+00:00`
- Status: **FAIL**
- Matrix mode: `scoreboard`
- Criteria: `7/8`
- Outcome: `v2_2_does_not_move_standard_scoreboard`
- Recommendation: Stop blaming training duration; run failure localization or narrow claim.

## Claim Boundary

Tier 7.0e is software benchmark evidence only. It reruns the public standard dynamical scoreboard with v2.2 and a length sweep. It is not hardware evidence, not a custom synthetic usefulness claim, not a new baseline freeze, and not AGI/ASI evidence.

## Length Sweep

| Length | v2.2 candidate MSE | Raw v2.1 MSE | Best baseline | Best baseline MSE | Candidate / best baseline | Margin vs raw v2.1 |
| ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 10000 | inf | None | fixed_esn_train_prefix_ridge_baseline | inf | None | None |

## Benchmark Stream Validity

- Invalid generated task streams: `1`
- `narma10` seed `44` length `10000` target_nonfinite_count=`1688`

## Interpretation

- Candidate improvement first-to-last: `None`
- Best-baseline improvement first-to-last: `None`
- Any competitive length: `False`
- Any improvement versus raw v2.1: `False`

## Nonclaims

- not hardware evidence
- not custom synthetic usefulness proof
- not universal benchmark superiority
- not a new baseline freeze
- not language, planning, AGI, or ASI
