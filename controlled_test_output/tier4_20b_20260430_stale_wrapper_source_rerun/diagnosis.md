# Tier 4.20b Stale Wrapper Source Rerun

- Classification: `stale_tier4_20b_wrapper_source_rerun`
- This return did not use the updated in-process Tier 4.20b runner.

## Evidence

The returned manifest still includes a child subprocess command:

```text
['/home/jovyan/spinnaker/bin/python', '<jobmanager_tmp>', '--mode', 'run-hardware', '--no-require-real-hardware', '--tasks', 'delayed_cue,hard_noisy_switching', '--seeds', '42', '--steps', '1200', '--population-size', '8', '--runtime-mode', 'chunked', '--learning-location', 'host', '--chunk-size-steps', '50', '--delayed-readout-lr', '0.2', '--output-dir', '<jobmanager_tmp>']
```

The returned criteria still include:

```text
child Tier 4.16 command exited cleanly
```

The updated local code should instead report:

```text
child Tier 4.16 in-process runner exited cleanly
child_execution_mode = in_process
```

## Interpretation

The EBRAINS `/cra/experiments` folder was not replaced with the current local source, or the job reused/cached the older folder. The failure is the same old wrapper/subprocess PACMAN `No version` failure, not a result from the new in-process runner.
