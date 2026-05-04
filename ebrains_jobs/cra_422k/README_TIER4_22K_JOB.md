# Tier 4.22k EBRAINS Spin1API Event-Symbol Discovery

Upload the `cra_422k` folder itself so the JobManager path starts with `cra_422k/`.

Do not upload `controlled_test_output/`, repo history, downloaded reports, or compiled binaries.

Run command:

```text
cra_422k/experiments/tier4_22k_spin1api_event_discovery.py --mode run-hardware --output-dir tier4_22k_job_output
```

Download every `tier4_22k*` file after it finishes. This job does not need a board hostname; it inspects and compiles against the EBRAINS build image headers.
