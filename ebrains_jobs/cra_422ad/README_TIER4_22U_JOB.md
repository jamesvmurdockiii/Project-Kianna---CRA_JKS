# Tier 4.22u EBRAINS Tiny Native Memory-Route State Custom-Runtime Smoke Job

Upload the `cra_422ad` folder itself so the JobManager path starts with `cra_422ad/`. Do not upload `controlled_test_output`.

This job builds and loads the custom C runtime, writes bounded keyed context slots with `CMD_WRITE_CONTEXT`, keyed route slots with `CMD_WRITE_ROUTE_SLOT`, keyed memory slots with `CMD_WRITE_MEMORY_SLOT`, and then schedules each decision with `CMD_SCHEDULE_MEMORY_ROUTE_CONTEXT_PENDING`. For each decision the host sends only key+cue+delay; the chip retrieves context, route, and memory slots by key, computes `feature=context[key]*route[key]*memory[key]*cue`, scores the pre-update prediction, and matures delayed credit in order.

Run command:

```text
cra_422ad/experiments/tier4_22u_native_memory_route_state_smoke.py --mode run-hardware --output-dir tier4_22u_job_output
```

Pass means a tiny native memory-route state primitive layered on native keyed-context and keyed-route state matched the local fixed-point reference and met the predeclared context/route/memory-slot/tail-accuracy gates. It is not full v2.1 on-chip memory/routing, full CRA task learning, speedup evidence, or final autonomy.
