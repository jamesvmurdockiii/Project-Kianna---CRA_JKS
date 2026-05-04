# Tier 4.15 SpiNNaker Hardware Multi-Seed Repeat

- Imported: `2026-04-27T02:56:39.454053+00:00`
- Source generated: `2026-04-27T02:48:50+00:00`
- Status: **PASS**
- Mode: `run-hardware`
- Source output directory: `None`

Tier 4.15 repeats the minimal Tier 4.13 fixed-pattern hardware capsule across seeds `42`, `43`, and `44`.

## Canonical Claim

The minimal fixed-pattern CRA SpiNNaker hardware capsule repeats across three seeds with zero synthetic fallback, zero `sim.run` failures, zero summary-read failures, real spike readback in every seed, and learning metrics above threshold.

## Claim Boundary

- This is repeatability evidence for the minimal fixed-pattern hardware capsule only.
- It uses `N=8`, fixed population, 120 steps, seeds `42`, `43`, and `44`.
- It is not a harder-task hardware result, not hardware population scaling, and not full CRA hardware deployment.
- `hardware_target_configured=False` is retained from the JobManager detector, but the pass is accepted because `hardware_run_attempted=True`, `pyNN.spiNNaker` completed, failures/fallbacks are zero, and spike readback is nonzero for every seed.

## Summary Metrics

| Metric | Value |
| --- | ---: |
| Runs | `3` |
| Backend | `pyNN.spiNNaker` |
| Overall accuracy mean | `0.9747899159663865` |
| Overall accuracy min | `0.9747899159663865` |
| Tail accuracy mean | `1.0` |
| Tail prediction-target corr mean | `0.9999901037892215` |
| Tail prediction-target corr min | `0.9999839178111984` |
| Total spike readback mean | `291103.6666666667` |
| Total spike readback min | `284154.0` |
| Runtime seconds mean | `873.6344163606409` |
| Runtime seconds min | `865.3982471250929` |
| Runtime seconds max | `884.8983335739467` |
| Synthetic fallbacks sum | `0` |
| `sim.run` failures sum | `0` |
| Summary-read failures sum | `0` |
| Final live polyps | `8.0` |
| Births/deaths | `0` / `0` |

## Per-Seed Results

| Seed | Status | Overall Acc | Tail Acc | Tail Corr | Spikes | Runtime s |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `42` | `pass` | `0.9747899159663865` | `1.0` | `0.9999839178111984` | `284154` | `884.8983335739467` |
| `43` | `pass` | `0.9747899159663865` | `1.0` | `0.9999928096452596` | `293636` | `870.6066683828831` |
| `44` | `pass` | `0.9747899159663865` | `1.0` | `0.9999935839112062` | `295521` | `865.3982471250929` |

## Artifacts

- `tier4_15_results.json`: source pass manifest.
- `tier4_15_report.md`: source human report.
- `tier4_15_summary.csv`: compact aggregate summary.
- `tier4_15_seed_summary.csv`: per-seed summary table.
- `tier4_15_multi_seed_summary.png`: multi-seed summary plot.
- `spinnaker_hardware_seed{42,43,44}_timeseries.csv`: per-step telemetry.
- `spinnaker_hardware_seed{42,43,44}_timeseries.png`: per-seed plots.
- `spinnaker_reports/`: extracted per-seed sPyNNaker provenance directories.
- `raw_reports/spinnaker_reports_tier4_15_seeds_42_43_44.zip`: raw reports archive from Downloads.
- `DOWNLOAD_INTAKE_MANIFEST.json`: source/destination checksums and intake decisions.
- `study_data.json`: normalized study record for docs and registry review.
