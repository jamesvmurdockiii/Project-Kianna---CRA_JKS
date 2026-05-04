# Tier 4.16 Harder SpiNNaker Hardware Capsule

This capsule tests whether the Tier 5.4 confirmed delayed-credit setting survives on real SpiNNaker hardware.

Chunked mode uses scheduled input, per-step binned spike readback, and host-side delayed-credit replay. It is still not continuous/on-chip learning.

## Run

```bash
bash controlled_test_output/<tier4_16_prepared_run>/jobmanager_capsule/run_tier4_16_on_jobmanager.sh /tmp/tier4_16_job_output
```

## Claim Boundary

A prepared capsule is not a hardware pass. A pass requires real `pyNN.spiNNaker`, zero fallback, zero `sim.run` failures, zero summary-read failures, real spike readback, and task metrics above threshold.

This is not a superiority claim and not hardware population scaling.

## Parts

- 4.16a: `delayed_cue`
