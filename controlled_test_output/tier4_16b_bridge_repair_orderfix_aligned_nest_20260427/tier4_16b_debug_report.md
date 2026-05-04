# Tier 4.16b Hard-Switch Local Debug Findings

- Generated: `2026-04-27T21:47:01+00:00`
- Status: **PASS**
- Output directory: `controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427`

This is a local-only root-cause diagnostic for the failed Tier 4.16b
`hard_noisy_switching` hardware run. It is not canonical hardware evidence.

## Decision

- classification: `hardware_transfer_or_timing_failure`
- next_step: `compare spike/readback timing and run one repaired hardware probe only`
- full_step_cra_tail_min: `0.547619`
- direct_chunked_host_tail_min: `0.52381`
- hardware_tail_min: `0.47619`
- max_bridge_tail_delta: `0`
- max_hardware_tail_delta: `0.047619`

## Path Aggregates

| Path | Backend | Runs | Tail Mean | Tail Min | All Mean | Corr Mean | Spikes Mean | Runtime Mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `full_step_cra` | `all` | 3 | 0.555556 | 0.547619 | 0.526316 | 0.0571022 | None | 37.687 |
| `full_step_cra` | `nest` | 3 | 0.555556 | 0.547619 | 0.526316 | 0.0571022 | None | 37.687 |
| `direct_step_host_replay` | `all` | 3 | 0.547619 | 0.52381 | 0.549708 | 0.0491297 | 100989 | 126.783 |
| `direct_step_host_replay` | `nest` | 3 | 0.547619 | 0.52381 | 0.549708 | 0.0491297 | 100989 | 126.783 |
| `direct_chunked_host_replay` | `all` | 3 | 0.547619 | 0.52381 | 0.549708 | 0.0491297 | 100989 | 5.18762 |
| `direct_chunked_host_replay` | `nest` | 3 | 0.547619 | 0.52381 | 0.549708 | 0.0491297 | 100989 | 5.18762 |
| `returned_hardware_chunked_host_replay` | `all` | 3 | 0.547619 | 0.47619 | 0.461988 | 0.0822073 | 94812.7 | None |
| `returned_hardware_chunked_host_replay` | `spinnaker` | 3 | 0.547619 | 0.47619 | 0.461988 | 0.0822073 | 94812.7 | None |

## Key Comparisons

| Type | Left | Right | Seed | Backend | Tail Delta | Prediction Corr | Spike Corr |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: |
| `direct_step_vs_chunked` | `direct_step_host_replay` | `direct_chunked_host_replay` | 42 | `nest` | 0 | 1 | 1 |
| `full_cra_vs_direct_chunked` | `full_step_cra` | `direct_chunked_host_replay` | 42 | `nest` | 0.047619 | 0.46607 | None |
| `local_chunked_vs_hardware` | `direct_chunked_host_replay` | `returned_hardware_chunked_host_replay` | 42 | `nest` | 0.047619 | 0.181541 | 0.460762 |
| `direct_step_vs_chunked` | `direct_step_host_replay` | `direct_chunked_host_replay` | 43 | `nest` | 0 | 1 | 1 |
| `full_cra_vs_direct_chunked` | `full_step_cra` | `direct_chunked_host_replay` | 43 | `nest` | -0.047619 | 0.265727 | None |
| `local_chunked_vs_hardware` | `direct_chunked_host_replay` | `returned_hardware_chunked_host_replay` | 43 | `nest` | 0 | 0.558869 | 0.442232 |
| `direct_step_vs_chunked` | `direct_step_host_replay` | `direct_chunked_host_replay` | 44 | `nest` | 0 | 1 | 1 |
| `full_cra_vs_direct_chunked` | `full_step_cra` | `direct_chunked_host_replay` | 44 | `nest` | -0.0238095 | 0.62966 | None |
| `local_chunked_vs_hardware` | `direct_chunked_host_replay` | `returned_hardware_chunked_host_replay` | 44 | `nest` | -0.047619 | 0.499661 | 0.4382 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| full diagnostic matrix completed | 9 | == 9 | yes |
| hardware traces loaded | 3 | == 3 | yes |
| no execution exceptions | 0 | == 0 | yes |
| failure class assigned | True | == True | yes |
| direct step/chunked comparison produced | 3 | == 3 | yes |
| hardware/local comparison produced | 3 | == 3 | yes |

## Interpretation Boundary

- If full step-mode CRA fails locally, the hard-switch weakness is not primarily a SpiNNaker transfer bug.
- If direct step and direct chunked match, chunking itself is not the primary failure.
- If local chunked and returned hardware are similar, the returned hardware failure is reproducing the local bridge behavior.
- Architecture fixes should be added one at a time only after this diagnosis is accepted.

## Artifacts

- `summary_csv`: `controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427/tier4_16b_debug_summary.csv`
- `path_summary_csv`: `controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427/tier4_16b_debug_path_summary.csv`
- `comparisons_csv`: `controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427/tier4_16b_debug_comparisons.csv`
- `timeseries_csv`: `controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427/tier4_16b_debug_timeseries.csv`
- `report_md`: `controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427/tier4_16b_debug_report.md`
- `manifest_json`: `controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427/tier4_16b_debug_results.json`
- `summary_png`: `controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427/tier4_16b_debug_summary.png`
