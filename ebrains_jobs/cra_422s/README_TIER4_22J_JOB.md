# Tier 4.22j EBRAINS Minimal Custom-Runtime Learning Job

Upload the `cra_422s` folder itself so the JobManager path starts with `cra_422s/`. Do not upload `controlled_test_output`.

This job depends on the Tier 4.22i board-roundtrip pass. It builds and loads the custom C runtime, then sends `CMD_SCHEDULE_PENDING` followed by `CMD_MATURE_PENDING` and validates that compact `CMD_READ_STATE` shows one pending horizon matured and readout weight/bias changed on chip.

Run command:

```text
cra_422s/experiments/tier4_22j_minimal_custom_runtime_learning.py --mode run-hardware --output-dir tier4_22j_job_output
```

Pass means a minimal delayed pending/readout update happened in the custom runtime on real SpiNNaker. It is not full CRA task learning or speedup evidence.
