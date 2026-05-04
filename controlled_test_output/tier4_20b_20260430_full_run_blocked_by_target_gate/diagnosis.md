# Tier 4.20b Full Run Blocked By Strict Target Gate

- Classification: `full_run_blocked_by_strict_target_gate`
- Hardware evidence attempted: `False`
- Source layout: passed
- v2.1 baseline artifact: passed
- Child runner found: passed

## Root Cause

The full EBRAINS run still invokes the Tier 4.16 child runner with a strict real-target precheck. That precheck requires visible `machineName`, `version`, `spalloc_server`, `remote_spinnaker_url`, `SPINNAKER_MACHINE`, or `SPALLOC_SERVER` before attempting `sim.run`.

Returned failure:

```text
No real SpiNNaker target is configured in this environment. pyNN.spiNNaker is installed, but sPyNNaker has no Machine target (no machineName, version, spalloc_server, remote_spinnaker_url, SPINNAKER_MACHINE, or SPALLOC_SERVER). Run inside a real SpiNNaker allocation or provide --spinnaker-hostname if that is the correct target for this EBRAINS job.
```

## Interpretation

This is not a CRA science failure and not a v2.1 hardware-transfer failure. It is a run-policy failure: the strict target detector blocked before the actual pyNN.spiNNaker run could decide whether EBRAINS had a usable hardware context.

## Fix

Make the target precheck advisory during `run-hardware`, then evaluate hardware evidence by actual outcomes: backend, `sim.run` success, zero fallback, zero readback failures, and nonzero spike readback.
