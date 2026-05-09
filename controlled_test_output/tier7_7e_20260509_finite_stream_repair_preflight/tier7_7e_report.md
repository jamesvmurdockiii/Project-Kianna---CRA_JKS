# Tier 7.7e Finite-Stream Repair / Preflight Contract

- Generated: `2026-05-09T14:24:47+00:00`
- Status: **PASS**
- Criteria: `16/16`
- Outcome: `finite_stream_repair_preflight_passed`
- Selected generator: `narma10_reduced_input_u02`

## Question

Can the long-run NARMA10 stream be made finite under a predeclared standardized rule before rerunning any long-run scoreboard?

## Selected Repair

- Input distribution: `u_t ~ Uniform(0, 0.2)`
- Output wrapper: `none`
- Labeling rule: future scoreboards must label NARMA as repaired_narma10_reduced_input_u02 and must not merge these scores silently with prior u05 NARMA scores

## Preflight Summary

| Generator | Required cells | Passed cells | Non-finite cells | Selected |
| --- | ---: | ---: | ---: | --- |
| `narma10_standard_u05` | 9 | 7 | 2 | False |
| `narma10_reduced_input_u02` | 9 | 9 | 0 | True |
| `narma10_tanh_bounded_u05` | 9 | 9 | 0 | False |

## Claim Boundary

Tier 7.7e repairs and preflights the long-run NARMA10 benchmark stream only. It authorizes a new repaired-stream long-run scoring gate if the selected generator is finite, but it does not score CRA, does not freeze a baseline, does not claim public usefulness, does not authorize hardware/native transfer, and does not allow prior u05 NARMA scores to be silently mixed with repaired u02 scores.

## Nonclaims

- not a CRA score
- not a public-usefulness result
- not a baseline freeze
- not evidence that CRA beats ESN/ridge/online baselines
- not hardware/native transfer
- not a mechanism implementation
- not language, broad reasoning, AGI, or ASI evidence
