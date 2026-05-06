# Tier 4.30g EBRAINS Lifecycle Task-Benefit / Resource Bridge

Upload the `cra_430g` folder itself so the JobManager path starts with `cra_430g/`. Do not upload `controlled_test_output`.

Purpose: run the bounded lifecycle-to-task bridge on real SpiNNaker. The lifecycle_core executes enabled and sham-control lifecycle modes; the host ferries the resulting lifecycle gate into the context/route/memory/learning task path; the learning core runs the compact delayed task.

Run command:

```text
cra_430g/experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py --mode run-hardware --output-dir tier4_30g_hw_job_output
```

Paste the command directly into the EBRAINS JobManager command field. Do not wrap it in `bash`, `cd`, or `python3`.

The package is source-only and intentionally does not include the full repository evidence archive. Do not use package-local mode as the canonical preflight; the full-repo prepare step already validated the local contract and source checks before this folder was generated.

PASS is a hardware task-benefit/resource bridge only: real target acquisition, five profile builds/loads, enabled lifecycle task gate open, predeclared controls gated closed, learning-core state near fixed-point reference, returned resource/readback accounting, and zero synthetic fallback. It is not autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip scaling, and not a lifecycle baseline freeze.
