# Tier 4.22s EBRAINS Tiny Native Route-State Custom-Runtime Smoke Job

Upload the `cra_422ab` folder itself so the JobManager path starts with `cra_422ab/`. Do not upload `controlled_test_output`.

This job builds and loads the custom C runtime, writes bounded keyed context slots with `CMD_WRITE_CONTEXT`, writes chip-owned route state with `CMD_WRITE_ROUTE`, and then schedules each decision with `CMD_SCHEDULE_ROUTED_CONTEXT_PENDING`. For each decision the host sends only key+cue+delay; the chip retrieves the context and route state, computes `feature=context*route*cue`, scores the pre-update prediction, and matures delayed credit in order.

Run command:

```text
cra_422ab/experiments/tier4_22s_native_route_state_smoke.py --mode run-hardware --output-dir tier4_22s_job_output
```

Pass means a tiny native route-state primitive layered on native keyed-context state matched the local fixed-point reference and met the predeclared context/route/tail-accuracy gates. It is not full v2.1 on-chip memory/routing, full CRA task learning, speedup evidence, or final autonomy.
