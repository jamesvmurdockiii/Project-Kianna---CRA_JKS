# Tier 4.20b Target Check Diagnosis

- Classification: `ebrains_target_check_blocked_no_machine_target`
- This is not a CRA learning failure.
- This is not a Python typecheck/type error in the returned artifacts.
- Hardware run attempted: `None`
- Child status: `None`
- Child hardware attempted: `None`

## Root Cause

None

## Evidence

- `pyNN.spiNNaker` import: OK
- `spynnaker.pyNN` import: OK
- `.spynnaker.cfg` exists: `True`
- `machineName`: `None`
- `version`: `None`
- `spalloc_server`: `None`
- `remote_spinnaker_url`: `None`
- `SPINNAKER_MACHINE`: `False`
- `SPALLOC_SERVER`: `False`
- `REMOTE_SPINNAKER_URL`: `False`

## Interpretation

The source layout reached EBRAINS and the child hardware runner was found. The job failed correctly at the hardware target gate because EBRAINS did not expose a real SpiNNaker target to sPyNNaker.

## Next Action

Run the same uploaded source in an EBRAINS/SpiNNaker context that actually provides a machine target, or provide the correct target setting only if EBRAINS has given you one. Do not upload `controlled_test_output/`.
