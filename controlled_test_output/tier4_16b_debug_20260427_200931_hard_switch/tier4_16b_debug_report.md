# Tier 4.16b Hard-Switch Local Debug Findings

- Generated: `2026-04-27T20:44:18+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch`

This is a local-only root-cause diagnostic for the failed Tier 4.16b
`hard_noisy_switching` hardware run. It is not canonical hardware evidence.

## Decision

- classification: `chunked_host_bridge_learning_failure`
- next_step: `repair host-replay bridge or macro delayed-credit path before hardware rerun`
- full_step_cra_tail_min: `0.52381`
- direct_chunked_host_tail_min: `0.428571`
- hardware_tail_min: `1`
- max_bridge_tail_delta: `0`
- max_hardware_tail_delta: `0.571429`

## Path Aggregates

| Path | Backend | Runs | Tail Mean | Tail Min | All Mean | Corr Mean | Spikes Mean | Runtime Mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `full_step_cra` | `all` | 6 | 0.539683 | 0.52381 | 0.532164 | 0.148016 | None | 166.063 |
| `full_step_cra` | `nest` | 3 | 0.539683 | 0.52381 | 0.532164 | 0.148016 | None | 41.278 |
| `full_step_cra` | `brian2` | 3 | 0.539683 | 0.52381 | 0.532164 | 0.148016 | None | 290.849 |
| `direct_step_host_replay` | `all` | 6 | 0.47619 | 0.428571 | 0.467836 | -0.0209815 | 128887 | 171.525 |
| `direct_step_host_replay` | `nest` | 3 | 0.47619 | 0.428571 | 0.467836 | -0.0209815 | 100976 | 143.235 |
| `direct_step_host_replay` | `brian2` | 3 | 0.47619 | 0.428571 | 0.467836 | -0.0209815 | 156797 | 199.814 |
| `direct_chunked_host_replay` | `all` | 6 | 0.47619 | 0.428571 | 0.467836 | -0.0209815 | 128901 | 9.69652 |
| `direct_chunked_host_replay` | `nest` | 3 | 0.47619 | 0.428571 | 0.467836 | -0.0209815 | 100976 | 5.83638 |
| `direct_chunked_host_replay` | `brian2` | 3 | 0.47619 | 0.428571 | 0.467836 | -0.0209815 | 156827 | 13.5567 |
| `returned_hardware_chunked_host_replay` | `all` | 3 | 1 | 1 | 1 | 0.0822073 | 94812.7 | None |
| `returned_hardware_chunked_host_replay` | `spinnaker` | 3 | 1 | 1 | 1 | 0.0822073 | 94812.7 | None |

## Key Comparisons

| Type | Left | Right | Seed | Backend | Tail Delta | Prediction Corr | Spike Corr |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: |
| `direct_step_vs_chunked` | `direct_step_host_replay` | `direct_chunked_host_replay` | 42 | `nest` | 0 | 1 | 1 |
| `full_cra_vs_direct_chunked` | `full_step_cra` | `direct_chunked_host_replay` | 42 | `nest` | 0.0238095 | 0.303662 | None |
| `local_chunked_vs_hardware` | `direct_chunked_host_replay` | `returned_hardware_chunked_host_replay` | 42 | `nest` | 0.452381 | 0.984845 | 0.444256 |
| `direct_step_vs_chunked` | `direct_step_host_replay` | `direct_chunked_host_replay` | 42 | `brian2` | 0 | 1 | 0.998876 |
| `full_cra_vs_direct_chunked` | `full_step_cra` | `direct_chunked_host_replay` | 42 | `brian2` | 0.0238095 | 0.303662 | None |
| `local_chunked_vs_hardware` | `direct_chunked_host_replay` | `returned_hardware_chunked_host_replay` | 42 | `brian2` | 0.452381 | 0.984845 | 0.87471 |
| `direct_step_vs_chunked` | `direct_step_host_replay` | `direct_chunked_host_replay` | 43 | `nest` | 0 | 1 | 1 |
| `full_cra_vs_direct_chunked` | `full_step_cra` | `direct_chunked_host_replay` | 43 | `nest` | -0.0714286 | 0.161555 | None |
| `local_chunked_vs_hardware` | `direct_chunked_host_replay` | `returned_hardware_chunked_host_replay` | 43 | `nest` | 0.547619 | 0.888714 | 0.454791 |
| `direct_step_vs_chunked` | `direct_step_host_replay` | `direct_chunked_host_replay` | 43 | `brian2` | 0 | 1 | 0.998879 |
| `full_cra_vs_direct_chunked` | `full_step_cra` | `direct_chunked_host_replay` | 43 | `brian2` | -0.0714286 | 0.161555 | None |
| `local_chunked_vs_hardware` | `direct_chunked_host_replay` | `returned_hardware_chunked_host_replay` | 43 | `brian2` | 0.547619 | 0.888714 | 0.863443 |
| `direct_step_vs_chunked` | `direct_step_host_replay` | `direct_chunked_host_replay` | 44 | `nest` | 0 | 1 | 1 |
| `full_cra_vs_direct_chunked` | `full_step_cra` | `direct_chunked_host_replay` | 44 | `nest` | -0.142857 | 0.127397 | None |
| `local_chunked_vs_hardware` | `direct_chunked_host_replay` | `returned_hardware_chunked_host_replay` | 44 | `nest` | 0.571429 | 0.648987 | 0.446768 |
| `direct_step_vs_chunked` | `direct_step_host_replay` | `direct_chunked_host_replay` | 44 | `brian2` | 0 | 1 | 0.999233 |
| `full_cra_vs_direct_chunked` | `full_step_cra` | `direct_chunked_host_replay` | 44 | `brian2` | -0.142857 | 0.127397 | None |
| `local_chunked_vs_hardware` | `direct_chunked_host_replay` | `returned_hardware_chunked_host_replay` | 44 | `brian2` | 0.571429 | 0.648987 | 0.871254 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| full diagnostic matrix completed | 18 | == 18 | yes |
| hardware traces loaded | 3 | == 3 | yes |
| no execution exceptions | 0 | == 0 | yes |
| failure class assigned | True | == True | yes |
| direct step/chunked comparison produced | 6 | == 6 | yes |
| hardware/local comparison produced | 6 | == 6 | yes |

## Interpretation Boundary

- If full step-mode CRA fails locally, the hard-switch weakness is not primarily a SpiNNaker transfer bug.
- If direct step and direct chunked match, chunking itself is not the primary failure.
- If local chunked and returned hardware are similar, the returned hardware failure is reproducing the local bridge behavior.
- Architecture fixes should be added one at a time only after this diagnosis is accepted.

## Artifacts

- `summary_csv`: `<repo>/controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch/tier4_16b_debug_summary.csv`
- `path_summary_csv`: `<repo>/controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch/tier4_16b_debug_path_summary.csv`
- `comparisons_csv`: `<repo>/controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch/tier4_16b_debug_comparisons.csv`
- `timeseries_csv`: `<repo>/controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch/tier4_16b_debug_timeseries.csv`
- `report_md`: `<repo>/controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch/tier4_16b_debug_report.md`
- `manifest_json`: `<repo>/controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch/tier4_16b_debug_results.json`
- `summary_png`: `<repo>/controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch/tier4_16b_debug_summary.png`
