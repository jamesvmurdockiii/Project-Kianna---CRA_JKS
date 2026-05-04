# Tier 4.16b Repaired Hard-Switch Seed-44 Hardware Probe Analysis

- Source result generated UTC: `2026-04-27T22:32:10+00:00`
- Ingested bundle: `controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/`
- Status: **PASS** as a one-seed repaired hardware probe
- Claim boundary: this is not the full repaired three-seed Tier 4.16b result.

## What Passed

The repaired `hard_noisy_switching` probe ran on real `pyNN.spiNNaker` with:

- task: `hard_noisy_switching`
- seed: `44`
- steps: `1200`
- population: `N=8`
- runtime mode: `chunked`
- learning location: `host`
- chunk size: `25` steps
- hardware `sim.run` calls: `48`
- synthetic fallbacks: `0`
- `sim.run` failures: `0`
- summary/readback failures: `0`
- real spike readback: `94707` spikes
- all accuracy: `0.5730994152046783`
- tail accuracy: `0.5238095238095238`
- tail events: `22 / 42` correct
- tail prediction-target correlation: `0.10016740018210536`
- runtime: `413.99025471205823` seconds

This crosses the predeclared seed-level hard-switch hardware gate of tail accuracy `>= 0.5`, but only narrowly.

## Why Raw Dopamine Is Zero

`raw_dopamine` is zero in this probe because this chunked hardware path is deliberately using host-side delayed-credit replay, not native on-chip dopamine learning.

For this delayed task, the nonzero sensory cue and the delayed reward/target do not land on the same CRA step. The same-step telemetry formula observes nonzero `target_return_1m` on delayed feedback steps where the immediate sensory feature and `colony_prediction` are zero, so the same-step `raw_dopamine` channel remains zero.

That does not mean no learning signal was applied. The relevant delayed-credit evidence is:

- `matured_horizons_this_step` was nonzero on `1195 / 1200` steps.
- `pending_horizons` stayed active with a maximum of `5` pending records.
- `host_replay_weight` moved from `-1.5481208031612956` to `1.6514538242232368` across the run.
- `colony_prediction` became nonzero on the evaluation/cue steps.

Therefore, cite this as chunked host delayed-credit replay, not native dopamine delivery, native eligibility traces, or on-chip learning.

## Interpretation

The earlier three-seed hard-switch hardware attempt failed because worst-seed tail accuracy was below threshold. After the local host-replay ordering/defaults repair, the previous worst seed `44` now passes on real SpiNNaker hardware.

This supports rerunning the repaired three-seed Tier 4.16b capsule. It does not yet prove hard-switch hardware repeatability across seeds `42`, `43`, and `44`.

## Next Gate

Run the repaired three-seed hardware repeat:

```bash
python3 experiments/tier4_harder_spinnaker_capsule.py --mode run-hardware --tasks hard_noisy_switching --seeds 42,43,44 --steps 1200 --delayed-readout-lr 0.20 --runtime-mode chunked --learning-location host --chunk-size-steps 25 --require-real-hardware --stop-on-fail
```

Pass criteria remain:

- all three seed runs complete
- zero synthetic fallback
- zero `sim.run` failures
- zero summary/readback failures
- real spike readback in every seed
- fixed population, no births/deaths
- hard-switch tail accuracy minimum `>= 0.5`
- finite tail prediction-target correlation
- delayed-readout learning rate `0.20`
