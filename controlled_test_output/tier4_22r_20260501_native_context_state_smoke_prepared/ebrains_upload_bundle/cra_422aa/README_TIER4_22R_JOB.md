# Tier 4.22r EBRAINS Tiny Native Context-State Custom-Runtime Smoke Job

Upload the `cra_422aa` folder itself so the JobManager path starts with `cra_422aa/`. Do not upload `controlled_test_output`.

This job builds and loads the custom C runtime, writes bounded keyed context slots with `CMD_WRITE_CONTEXT`, and then schedules each decision with `CMD_SCHEDULE_CONTEXT_PENDING`. For each decision the host sends only key+cue+delay; the chip retrieves the context value, computes `feature=context*cue`, scores the pre-update prediction, and matures delayed credit in order.

Run command:

```text
cra_422aa/experiments/tier4_22r_native_context_state_smoke.py --mode run-hardware --output-dir tier4_22r_job_output
```

Pass means a tiny native keyed-context state primitive matched the local fixed-point reference and met the predeclared native-context/tail-accuracy gates. It is not full v2.1 on-chip memory/routing, full CRA task learning, speedup evidence, or final autonomy.
