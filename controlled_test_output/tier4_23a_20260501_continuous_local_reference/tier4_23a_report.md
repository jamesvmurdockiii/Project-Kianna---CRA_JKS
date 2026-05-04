# Tier 4.23a - Continuous / Stop-Batching Parity Local Reference

- Generated: `2026-05-01T23:35:10.973847+00:00`
- Mode: `local`
- Status: **PASS**
- Output directory: `controlled_test_output/tier4_23a_20260501_continuous_local_reference`

## Claim Boundary

- LOCAL only.  Proves the continuous loop logic matches the chunked reference.
- NOT hardware evidence, NOT full continuous on-chip learning, NOT speedup.

## Summary

- sequence_length: `48`
- autonomous_timesteps: `50`
- decisions: `48`
- rewards: `48`
- max_pending_depth: `3`
- continuous accuracy: `0.9583333333333334`
- continuous tail_accuracy: `1.0`
- chunked accuracy: `0.9583333333333334`
- chunked tail_accuracy: `1.0`
- max_feature_delta: `0`
- max_prediction_delta: `0`
- max_weight_delta: `0`
- max_bias_delta: `0`
- final_weight_raw: `32768`
- final_bias_raw: `0`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_23a_continuous_local_reference_20260501_0001` | `expected current source` | yes |
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
| continuous accuracy matches chunked | `0.958333` | `== 0.9583333333333334` | yes |
| continuous tail accuracy matches chunked | `1` | `== 1.0` | yes |
| continuous final weight matches chunked | `32768` | `== 32768` | yes |
| continuous final bias matches chunked | `0` | `== 0` | yes |
| zero synthetic fallback | `0` | `== 0` | yes |

## Artifacts

- `tier4_23a_results.json`: machine-readable results
- `tier4_23a_continuous_rows.csv`: continuous loop per-event trace
- `tier4_23a_chunked_rows.csv`: chunked reference per-event trace
