# Tier 4.21a Keyed Context-Memory Bridge

Upload only `experiments/` and `coral_reef_spinnaker/` under a fresh `cra_421a/` folder.

Run this in the EBRAINS JobManager command-line field:

```text
cra_421a/experiments/tier4_21a_keyed_context_memory_bridge.py --mode run-hardware --tasks context_reentry_interference --variants keyed_context_memory,slot_reset_ablation,slot_shuffle_ablation,wrong_key_ablation --seeds 42 --steps 720 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.2 --context-memory-slot-count 4 --no-require-real-hardware --output-dir tier4_21a_job_output
```

Do not upload `controlled_test_output/`, `baselines/`, reports, or downloads.
