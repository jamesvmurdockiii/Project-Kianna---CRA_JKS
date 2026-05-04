# Tier 4.20b v2.1 One-Seed Chunked Hardware Probe

This capsule is the first SpiNNaker bridge checkpoint after the frozen v2.1 software baseline.
It delegates low-level pyNN.spiNNaker execution to the already-proven Tier 4.16 chunked-host hardware runner, then wraps the result with the v2.1 transfer claim boundary.

## Run

```bash
bash controlled_test_output/<tier4_20b_prepared_run>/jobmanager_capsule/run_tier4_20b_on_jobmanager.sh /tmp/tier4_20b_job_output
```

## Boundary

A pass is hardware transport evidence for the v2.1 bridge profile, not full native v2.1/on-chip execution.
Macro eligibility is explicitly excluded because Tier 5.9c failed promotion.
