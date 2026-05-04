# Tier 4.20c v2.1 Three-Seed Chunked Hardware Repeat

Upload only `experiments/` and `coral_reef_spinnaker/` under a fresh `cra_420c/` folder.

Use the EBRAINS JobManager command line directly:

```text
cra_420c/experiments/tier4_20c_v2_1_hardware_repeat.py --mode run-hardware --tasks delayed_cue,hard_noisy_switching --seeds 42,43,44 --steps 1200 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20 --no-require-real-hardware --output-dir tier4_20c_job_output
```

Do not upload `controlled_test_output/`, `baselines/`, old reports, or downloaded artifacts.

A pass is repeatability evidence for the v2.1 bridge/transport path, not native/on-chip v2.1 execution.
