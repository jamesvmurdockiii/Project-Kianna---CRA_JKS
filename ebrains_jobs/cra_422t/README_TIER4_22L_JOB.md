# Tier 4.22l EBRAINS Tiny Custom-Runtime Learning Parity Job

Upload the `cra_422t` folder itself so the JobManager path starts with `cra_422t/`. Do not upload `controlled_test_output`.

This job depends conceptually on the Tier 4.22j minimal learning-smoke pass. It builds and loads the custom C runtime, then sends a four-event `CMD_SCHEDULE_PENDING`/`CMD_MATURE_PENDING` sequence and validates that compact `CMD_READ_STATE` matches the local s16.15 fixed-point reference.

Run command:

```text
cra_422t/experiments/tier4_22l_custom_runtime_learning_parity.py --mode run-hardware --output-dir tier4_22l_job_output
```

Pass means the tiny chip-owned readout update sequence matched the local reference. It is not full CRA task learning, v2.1 transfer, or speedup evidence.
