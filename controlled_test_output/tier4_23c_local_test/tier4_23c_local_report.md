# Tier 4.23c - One-Board Hardware Continuous Smoke

- Generated: `2026-05-02T01:11:01.589461+00:00`
- Mode: `local`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_23c_local_test`

## Summary

- sequence_length: `48`
- autonomous_timesteps: `50`
- max_pending_depth: `3`
- continuous accuracy: `0.9583333333333334`
- continuous tail_accuracy: `1.0`
- max_feature_delta: `0`
- max_prediction_delta: `0`
- max_weight_delta: `0`
- max_bias_delta: `0`
- final_weight_raw: `32768`
- final_bias_raw: `0`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_23c_continuous_hardware_smoke_20260501_0004` | `expected current source` | yes |
| continuous reference generated | `pass` | `== pass` | yes |
| chunked reference generated | `pass` | `== pass` | yes |
| sequence length matches | `48` | `== 48` | yes |
| autonomous timesteps equal sequence + gap + drain | `50` | `== 50` | yes |
| decisions equal sequence length | `48` | `== 48` | yes |
| rewards equal sequence length | `48` | `== 48` | yes |
| max pending depth matches chunked | `3` | `== 3` | yes |
| max feature delta | `0` | `<= 1` | yes |
| max prediction delta | `0` | `<= 1` | yes |
| max weight delta | `0` | `<= 1` | yes |
| max bias delta | `0` | `<= 1` | yes |
| all feature deltas zero | `True` | `== True` | yes |
| all prediction deltas zero | `True` | `== True` | yes |
| all weight deltas zero | `True` | `== True` | yes |
| all bias deltas zero | `True` | `== True` | yes |
| continuous accuracy matches chunked | `0.9583333333333334` | `== 0.9583333333333334` | yes |
| continuous tail accuracy matches chunked | `1.0` | `== 1.0` | yes |
| continuous final weight matches chunked | `32768` | `== 32768` | yes |
| continuous final bias matches chunked | `0` | `== 0` | yes |
| zero synthetic fallback | `0` | `== 0` | yes |

