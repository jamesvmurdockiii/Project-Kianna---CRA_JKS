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

## Hardware Note

The sPyNNaker dopamine/neuromodulation projection is sharded across multiple dopamine source neurons. This avoids the 255-synapse-per-source-row cap that appears when one dopamine source fans out to all 256 target atoms in the N=8 capsule.

The runner also applies narrow NumPy 2 compatibility shims for sPyNNaker/spinnman 7.4.x neuromodulation synapse flags, hardware byte buffers, and host-side memory-upload checksums. This does not change the CRA model or pass criteria; it only prevents valid 32-bit SpiNNaker words from failing scalar uint8 casts during upload/readback bookkeeping.

On failure, the capsule exports `seed_<seed>_failure_traceback.txt`, `seed_<seed>_backend_diagnostics.json`, `seed_<seed>_inner_backend_traceback.txt`, and recent `reports/` directories so the next hardware blocker has a full stack/provenance trail.

## Expected Claim If It Passes

`CRA minimal learning capsule executes on real SpiNNaker hardware and preserves expected fixed-pattern behavior.`
