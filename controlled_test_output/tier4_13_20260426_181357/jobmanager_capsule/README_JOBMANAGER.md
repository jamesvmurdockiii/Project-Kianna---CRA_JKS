# Tier 4.13 SpiNNaker Hardware Capsule

This capsule is meant to run inside an EBRAINS/JobManager job with real SpiNNaker access.

## Run

From the repository root inside the job:

```bash
bash controlled_test_output/<tier4_13_run>/jobmanager_capsule/run_tier4_13_on_jobmanager.sh
```

Or run the harness directly:

```bash
python3 experiments/tier4_spinnaker_hardware_capsule.py --mode run-hardware --require-real-hardware --stop-on-fail
```

## Claim Boundary

A prepared capsule is not a hardware result. The hardware claim only exists if `run-hardware` completes on a real target with zero synthetic fallbacks, zero `sim.run` failures, and zero summary-read failures.

## Expected Claim If It Passes

`CRA minimal learning capsule executes on real SpiNNaker hardware and preserves expected fixed-pattern behavior.`
