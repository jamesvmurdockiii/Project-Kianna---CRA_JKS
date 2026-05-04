# Tier 4.20b EBRAINS No-Machine-Target Failure Diagnostic

- Status: **FAIL / BLOCKED**
- Classification: `noncanonical_environment_failure`
- Not a science failure: `true`
- Not a source-package layout failure: `true`

## What Happened

The source package loaded correctly: v2.1 baseline existed, `coral_reef_spinnaker/` existed, the Tier 4.16 child runner existed, macro eligibility was excluded, and pyNN.spiNNaker imported.

The run failed before spike readback because sPyNNaker had no real machine target configured:

```text
task hard_noisy_switching seed 42 raised SpinnMachineException: No version with cfg [Machine] values version=None, machine_name=None, spalloc_server=None, remote_spinnaker_url=None, virtual_board=False, width=None, and height=None
```

The returned environment reported:

```json
{
  "env_flags": {
    "EBRAINS_JOB_ID": false,
    "JOB_ID": false,
    "SLURM_JOB_ID": false,
    "SPALLOC_SERVER": false,
    "SPINNAKER_MACHINE": false
  },
  "hardware_target_configured": false,
  "spynnaker_config": {
    "exists": true,
    "height": null,
    "machineName": null,
    "mode": null,
    "path": "/home/jovyan/.spynnaker.cfg",
    "spalloc_group": null,
    "spalloc_port": null,
    "spalloc_server": null,
    "spalloc_user": null,
    "version": null,
    "virtual_board": null,
    "width": null
  }
}
```

## Fix Applied After This Failure

The Tier 4.16 child runner now blocks before graph partitioning when no real SpiNNaker target is configured, and source-only runs create their own latest-manifest directory if needed. This prevents another long or misleading failure.

## Next Action

Upload the rebuilt `ebrains_upload/CRA_TIER4_20B_SOURCE/` folder and run it inside an EBRAINS/SpiNNaker allocation that actually provides a Machine target, or pass `--spinnaker-hostname` if EBRAINS gives a target hostname for the allocation.
