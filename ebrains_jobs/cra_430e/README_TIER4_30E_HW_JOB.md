# Tier 4.30e EBRAINS Multi-Core Lifecycle Hardware Smoke

Upload the `cra_430e` folder itself so the JobManager path starts with `cra_430e/`. Do not upload `controlled_test_output`.

Purpose: build and load five custom runtime profiles (`context_core`, `route_core`, `memory_core`, `learning_core`, `lifecycle_core`), verify profile readback and lifecycle ownership guards, run canonical lifecycle schedules on `lifecycle_core`, and probe duplicate/stale lifecycle event rejection on real SpiNNaker.

Run command:

```text
cra_430e/experiments/tier4_30e_multicore_lifecycle_hardware_smoke.py --mode run-hardware --output-dir tier4_30e_hw_job_output
```

Do not wrap the command in `bash`, `cd`, or `python3`; paste it directly into the EBRAINS JobManager command field.

PASS is a smoke-gate hardware claim only: real target acquisition, five profile builds/loads, compact lifecycle readback, lifecycle profile ownership, canonical/boundary reference parity, duplicate/stale rejection, and zero synthetic fallback. It is not lifecycle task-benefit evidence, not sham-control success, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not a lifecycle baseline freeze.
