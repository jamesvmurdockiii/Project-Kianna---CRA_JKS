# Tier 4.20b EBRAINS Upload Bundle

Upload this whole `CRA_TIER4_20B_UPLOAD` folder, or upload the zip that contains it.
Do **not** upload only `jobmanager_capsule/`; that folder is just metadata and a local wrapper.

## Entry Point

Run this from the uploaded bundle root:

```bash
python3 run.py
```

If the EBRAINS UI asks for a script/entry file, use:

```text
run.py
```

If it asks for arguments, leave blank or use:

```text
--output-dir tier4_20b_job_output
```

## What It Runs

```text
Tier 4.20b
seed = 42
tasks = delayed_cue, hard_noisy_switching
steps = 1200
N = 8
chunk_size_steps = 50
learning_location = host
macro eligibility = disabled
```

## What To Download After It Finishes

Download the entire output directory, usually:

```text
tier4_20b_job_output/
```

It should contain:

```text
tier4_20b_results.json
tier4_20b_report.md
tier4_20b_summary.csv
tier4_20b_bridge_profile.json
child_tier4_16/
```

Also download any `reports.zip`, `global_provenance.sqlite3`, `finished`, or raw SpiNNaker reports if EBRAINS exposes them separately.

## Claim Boundary

This is a one-seed v2.1 chunked-host bridge probe. It is not full native/on-chip v2.1 execution, not custom C, and not macro eligibility evidence.
