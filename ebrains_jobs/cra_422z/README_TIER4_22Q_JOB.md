# Tier 4.22q EBRAINS Tiny Integrated V2 Bridge Custom-Runtime Smoke Job

Upload the `cra_422z` folder itself so the JobManager path starts with `cra_422z/`. Do not upload `controlled_test_output`.

This job builds and loads the custom C runtime, then sends a 30-event signed stream produced by a tiny host-side v2-style bridge. The bridge keeps keyed context slots and a route state, transforms visible cues into scalar signed features, then lets the chip-owned pending/readout loop score pre-update predictions and mature delayed credit in order.

Run command:

```text
cra_422z/experiments/tier4_22q_integrated_v2_bridge_smoke.py --mode run-hardware --output-dir tier4_22q_job_output
```

Pass means a tiny integrated host-v2/custom-runtime bridge smoke matched the local fixed-point reference and met the predeclared bridge/tail-accuracy gates. It is not native v2.1 on-chip memory/routing, full CRA task learning, speedup evidence, or final autonomy.
