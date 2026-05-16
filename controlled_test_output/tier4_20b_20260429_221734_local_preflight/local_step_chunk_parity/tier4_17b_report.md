# Tier 4.17b Step vs Chunked Parity

- Generated: `2026-04-30T02:17:37+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_20b_20260429_221734_local_preflight/local_step_chunk_parity`

Tier 4.17b is a local runtime parity diagnostic. It is not SpiNNaker
hardware evidence and not a continuous/on-chip learning claim.

## Claim Boundary

- The step reference uses scheduled PyNN input but still runs one `sim.run` per original CRA step.
- Chunked runs use the same scheduled input source, fewer `sim.run` calls, binned spike readback, and host-side delayed-credit replay.
- Passing this tier authorizes implementing the same mechanics in the hardware capsule path; it does not by itself promote Tier 4.16.

## Aggregate

- expected comparisons: `2`
- observed comparisons: `2`
- max tail accuracy delta: `0`
- max prediction delta: `0`
- max step spike delta: `0`
- min spike-bin correlation: `1`
- sim.run reduction range: `5` to `10`

## Comparisons

| Backend | Chunk | Calls | Reduction | Tail Delta | Prediction Delta | Spike Delta | Spike Corr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `nest` | 5 | 8 | 5 | 0 | 0 | 0 | 1 |
| `nest` | 10 | 4 | 10 | 0 | 0 | 0 | 1 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| all backend/chunk comparisons completed | 2 | == 2 | yes |
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

1. Keep this local parity bundle as the gate for the Tier 4.16 chunked runner.
2. Repaired Tier 4.16a delayed_cue, 1200-step chunked hardware has passed across seeds `42,43,44`.
3. Run Tier 4.16b hard_noisy_switching with the same chunked bridge.

## Artifacts

- `summary_csv`: `<repo>/controlled_test_output/tier4_20b_20260429_221734_local_preflight/local_step_chunk_parity/tier4_17b_summary.csv`
- `comparison_csv`: `<repo>/controlled_test_output/tier4_20b_20260429_221734_local_preflight/local_step_chunk_parity/tier4_17b_comparisons.csv`
- `timeseries_csv`: `<repo>/controlled_test_output/tier4_20b_20260429_221734_local_preflight/local_step_chunk_parity/tier4_17b_timeseries.csv`
- `manifest_json`: `<repo>/controlled_test_output/tier4_20b_20260429_221734_local_preflight/local_step_chunk_parity/tier4_17b_results.json`
- `report_md`: `<repo>/controlled_test_output/tier4_20b_20260429_221734_local_preflight/local_step_chunk_parity/tier4_17b_report.md`
- `parity_png`: `<repo>/controlled_test_output/tier4_20b_20260429_221734_local_preflight/local_step_chunk_parity/tier4_17b_parity.png`
