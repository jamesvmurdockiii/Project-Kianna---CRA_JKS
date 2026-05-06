# Tier 4.30f EBRAINS Lifecycle Sham-Control Hardware Subset

Upload the `cra_430f` folder itself so the JobManager path starts with `cra_430f/`. Do not upload `controlled_test_output`.

Purpose: build/load the same five custom runtime profiles as 4.30e, then run a compact lifecycle sham-control subset on the lifecycle core: enabled, fixed-pool, random event replay, active-mask shuffle, no trophic pressure, and no dopamine/plasticity.

Run command:

```text
cra_430f/experiments/tier4_30f_lifecycle_sham_hardware_subset.py --mode run-hardware --output-dir tier4_30f_hw_job_output
```

Paste the command directly into the EBRAINS JobManager command field. Do not wrap it in `bash`, `cd`, or `python3`.

PASS is a sham-control hardware subset only: real target acquisition, five profile builds/loads, compact lifecycle readback, expected enabled/control separations, and zero synthetic fallback. It is not lifecycle task-benefit evidence, not full Tier 6.3 hardware, not speedup, not multi-chip scaling, and not a lifecycle baseline freeze.
