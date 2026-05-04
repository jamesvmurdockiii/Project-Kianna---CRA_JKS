# Tier 4.22t EBRAINS Tiny Native Keyed Route-State Custom-Runtime Smoke Job

Upload the `cra_422ac` folder itself so the JobManager path starts with `cra_422ac/`. Do not upload `controlled_test_output`.

This job builds and loads the custom C runtime, writes bounded keyed context slots with `CMD_WRITE_CONTEXT`, writes keyed route slots with `CMD_WRITE_ROUTE_SLOT`, and then schedules each decision with `CMD_SCHEDULE_KEYED_ROUTE_CONTEXT_PENDING`. For each decision the host sends only key+cue+delay; the chip retrieves context and route slots by key, computes `feature=context[key]*route[key]*cue`, scores the pre-update prediction, and matures delayed credit in order.

Run command:

```text
cra_422ac/experiments/tier4_22t_native_keyed_route_state_smoke.py --mode run-hardware --output-dir tier4_22t_job_output
```

Pass means a tiny native keyed route-state primitive layered on native keyed-context state matched the local fixed-point reference and met the predeclared context/route-slot/tail-accuracy gates. It is not full v2.1 on-chip memory/routing, full CRA task learning, speedup evidence, or final autonomy.
