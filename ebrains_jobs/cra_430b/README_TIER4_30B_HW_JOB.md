# Tier 4.30b-hw EBRAINS Lifecycle Active-Mask/Lineage Smoke

Upload the `cra_430b` folder itself so the JobManager path starts with `cra_430b/`. Do not upload `controlled_test_output`.

Purpose: build and load the custom runtime with `RUNTIME_PROFILE=decoupled_memory_route`, initialize the Tier 4.30 static lifecycle pool, apply the canonical 32-event and boundary 64-event lifecycle schedules, and read back compact lifecycle telemetry with `CMD_LIFECYCLE_READ_STATE`.

Run command:

```text
cra_430b/experiments/tier4_30b_lifecycle_hardware_smoke.py --mode run-hardware --output-dir tier4_30b_hw_job_output
```

Pass means lifecycle active masks, event counters, lineage checksum, and trophic checksum matched the Tier 4.30a reference on real SpiNNaker. It is not a task-benefit claim, not multi-core lifecycle migration, not speedup evidence, and not a lifecycle baseline freeze.
