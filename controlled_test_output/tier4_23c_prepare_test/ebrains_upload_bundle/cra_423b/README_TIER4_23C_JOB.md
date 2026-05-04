# Tier 4.23c EBRAINS Hardware Continuous Smoke Job

Upload the `cra_423b` folder itself so the JobManager path starts with `cra_423b/`.

This job builds and loads the custom C runtime with `RUNTIME_PROFILE=decoupled_memory_route`. It pre-writes keyed context slots, route slots, and memory slots, then uploads a compact 48-event schedule via CMD_WRITE_SCHEDULE_ENTRY, starts autonomous execution with CMD_RUN_CONTINUOUS, waits for completion, and reads back compact state via CMD_READ_STATE.

Enabled runtime command surface: `CMD_RESET, CMD_READ_STATE, CMD_MATURE_PENDING, CMD_WRITE_CONTEXT, CMD_READ_CONTEXT, CMD_WRITE_ROUTE_SLOT, CMD_READ_ROUTE_SLOT, CMD_WRITE_MEMORY_SLOT, CMD_READ_MEMORY_SLOT, CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING, CMD_WRITE_SCHEDULE_ENTRY, CMD_RUN_CONTINUOUS, CMD_PAUSE`.

Run command:

```text
cra_423b/experiments/tier4_23c_continuous_hardware_smoke.py --mode run-hardware --output-dir tier4_23c_job_output
```

Pass means the timer-driven autonomous event loop on real SpiNNaker matched the local fixed-point continuous reference within predeclared tolerance. It is not full v2.1 on-chip, not speedup evidence, and not final autonomy.
