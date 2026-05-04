# Tier 4.20b Empirical Run Failure: No sPyNNaker Machine Version

- Classification: `empirical_spynnaker_run_failed_no_machine_version`
- Command format: direct JobManager command-line invocation was accepted
- `--no-require-real-hardware` propagated to child runner: `True`
- Hardware path attempted: `True`
- Completed task/seed runs: `0`

## Root Cause

The run bypassed CRA's strict target precheck and reached sPyNNaker/PACMAN mapping. It then failed because the EBRAINS runtime still had no SpiNNaker Machine target/version configured.

```text
task hard_noisy_switching seed 42 raised SpinnMachineException: No version with cfg [Machine] values version=None, machine_name=None, spalloc_server=None, remote_spinnaker_url=None, virtual_board=False, width=None, and height=None
```

The stderr confirms this happened during graph partitioning:

```text
WARNING: The cfg has no version. This is deprecated! Please add a version
Splitter partitioner exited with SpinnMachineException
```

## Important Interpretation

This is not a CRA learning failure, not a source-layout failure, and not a typecheck failure. It is an EBRAINS/sPyNNaker target configuration failure: `pyNN.spiNNaker` is installed, but the process is not attached to a SpiNNaker machine/version that PACMAN can map onto.

## Evidence

- `machineName`: `None`
- `version`: `None`
- `spalloc_server`: `None`
- `remote_spinnaker_url`: `None`
- `SPINNAKER_MACHINE`: `False`
- `SPALLOC_SERVER`: `False`
- `REMOTE_SPINNAKER_URL`: `False`

## Next Action

The same direct command format is fine. The next run needs to be submitted in an EBRAINS/SpiNNaker execution context that provides a Machine target/version to sPyNNaker, or the command needs the correct `--spinnaker-hostname`/machine configuration if EBRAINS exposes one.
