# Tier 4.22w EBRAINS Tiny Native Decoupled Memory-Route Composition Custom-Runtime Smoke Job

Upload the `cra_422af` folder itself so the JobManager path starts with `cra_422af/`. Do not upload `controlled_test_output`.

This job builds and loads the custom C runtime, writes bounded keyed context slots with `CMD_WRITE_CONTEXT`, keyed route slots with `CMD_WRITE_ROUTE_SLOT`, keyed memory slots with `CMD_WRITE_MEMORY_SLOT`, and then schedules each decision with `CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING`. For each decision the host sends independent `context_key`, `route_key`, `memory_key`, `cue`, and `delay`; the chip retrieves context, route, and memory slots by their own keys, computes `feature=context[context_key]*route[route_key]*memory[memory_key]*cue`, scores the pre-update prediction, and matures delayed credit in order.

Run command:

```text
cra_422af/experiments/tier4_22w_native_decoupled_memory_route_composition_smoke.py --mode run-hardware --output-dir tier4_22w_job_output
```

Pass means a tiny native decoupled memory-route composition primitive layered on native keyed-context, keyed-route, and keyed-memory state matched the local fixed-point reference and met the predeclared context/route/memory-slot/tail-accuracy gates. It is not full v2.1 on-chip memory/routing, full CRA task learning, speedup evidence, or final autonomy.
