# Tier 4.16 Hardware Failure Artifact

This directory preserves the returned Tier 4.16 real SpiNNaker hardware run as noncanonical failure evidence.

Claim boundary:

- Hardware execution completed for all requested task/seed runs.
- This is not a Tier 4.16 pass.
- The failure is criterion-level: `4.16a delayed_cue tail accuracy` did not meet the predeclared threshold.
- Do not cite this as successful harder-task hardware transfer.

Key result:

- backend: `pyNN.spiNNaker`
- tasks: `delayed_cue`, `hard_noisy_switching`
- seeds: `42`, `43`, `44`
- hardware run attempted: `true`
- synthetic fallbacks: `0`
- sim.run failures: `0`
- summary-read failures: `0`
- real spike readback: nonzero in every run
- failed criterion: delayed_cue tail accuracy min `0.3333333333333333` vs threshold `0.85`

Next step: debug Tier 4.16a locally and with one-seed hardware probes before repeating the full six-run capsule.
