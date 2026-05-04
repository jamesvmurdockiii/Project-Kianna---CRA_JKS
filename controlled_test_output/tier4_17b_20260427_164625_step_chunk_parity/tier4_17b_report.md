# Tier 4.17b Step vs Chunked Parity

- Generated: `2026-04-27T16:46:31+00:00`
- Status: **PASS**
- Output directory: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_17b_20260427_164625_step_chunk_parity`

Tier 4.17b is a local runtime parity diagnostic. It is not SpiNNaker
hardware evidence and not a continuous/on-chip learning claim.

## Claim Boundary

- The step reference uses scheduled PyNN input but still runs one `sim.run` per original CRA step.
- Chunked runs use the same scheduled input source, fewer `sim.run` calls, binned spike readback, and host-side delayed-credit replay.
- Passing this tier authorizes implementing the same mechanics in the hardware capsule path; it does not by itself promote Tier 4.16.

## Aggregate

- expected comparisons: `8`
- observed comparisons: `8`
- max tail accuracy delta: `0`
- max prediction delta: `0`
- max step spike delta: `0`
- min spike-bin correlation: `1`
- sim.run reduction range: `5` to `40`

## Comparisons

| Backend | Chunk | Calls | Reduction | Tail Delta | Prediction Delta | Spike Delta | Spike Corr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `nest` | 5 | 24 | 5 | 0 | 0 | 0 | 1 |
| `nest` | 10 | 12 | 10 | 0 | 0 | 0 | 1 |
| `nest` | 25 | 5 | 24 | 0 | 0 | 0 | 1 |
| `nest` | 50 | 3 | 40 | 0 | 0 | 0 | 1 |
| `brian2` | 5 | 24 | 5 | 0 | 0 | 0 | 1 |
| `brian2` | 10 | 12 | 10 | 0 | 0 | 0 | 1 |
| `brian2` | 25 | 5 | 24 | 0 | 0 | 0 | 1 |
| `brian2` | 50 | 3 | 40 | 0 | 0 | 0 | 1 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| all backend/chunk comparisons completed | 8 | == 8 | yes |
| no execution exceptions | 0 | == 0 | yes |
| zero synthetic fallback | True | == True | yes |
| zero backend/readback failures | True | == True | yes |
| same evaluation targets | True | == True | yes |
| tail accuracy parity | 0 | <= 1e-12 | yes |
| all accuracy parity | 0 | <= 1e-12 | yes |
| prediction replay parity | 0 | <= 1e-12 | yes |
| per-bin spike readback parity | 0 | <= 0 | yes |
| spike-bin correlation parity | 1 | >= 0.999999 | yes |
| chunking reduces sim.run calls | 5 | > 1 | yes |
| no continuous/on-chip claim | local runtime parity diagnostic; not hardware evidence | contains not hardware evidence | yes |

## Next Order

1. Wire this scheduled-input and binned-readback path into the Tier 4.16 hardware capsule runner.
2. Run the repaired Tier 4.16a delayed_cue seed `43`, 1200 steps, chunked hardware.
3. If that passes, repeat repaired Tier 4.16a across seeds `42,43,44`.

## Artifacts

- `summary_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_17b_20260427_164625_step_chunk_parity/tier4_17b_summary.csv`
- `comparison_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_17b_20260427_164625_step_chunk_parity/tier4_17b_comparisons.csv`
- `timeseries_csv`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_17b_20260427_164625_step_chunk_parity/tier4_17b_timeseries.csv`
- `manifest_json`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_17b_20260427_164625_step_chunk_parity/tier4_17b_results.json`
- `report_md`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_17b_20260427_164625_step_chunk_parity/tier4_17b_report.md`
- `parity_png`: `/Users/james/Kimi_Agent_Spinnaker Neuromorphic Design/controlled_test_output/tier4_17b_20260427_164625_step_chunk_parity/tier4_17b_parity.png`
