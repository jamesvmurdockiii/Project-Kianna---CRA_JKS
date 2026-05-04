# Tier 4.18a v0.7 Chunked Hardware Runtime Baseline

This capsule measures runtime/resource behavior for the already-proven v0.7 chunked-host hardware path.

## Run

```bash
bash controlled_test_output/<tier4_18a_prepared_run>/jobmanager_capsule/run_tier4_18a_on_jobmanager.sh /tmp/tier4_18a_job_output
```

## Boundary

A prepared capsule is not evidence. A pass requires real `pyNN.spiNNaker`, zero fallback/failures, real spike readback, and task metrics above threshold.

Tier 4.18a is runtime/resource characterization, not a new learning claim, not hardware scaling, and not on-chip learning.
