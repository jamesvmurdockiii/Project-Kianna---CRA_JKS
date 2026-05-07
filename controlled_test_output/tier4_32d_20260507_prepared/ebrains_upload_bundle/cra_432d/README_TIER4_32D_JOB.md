# Tier 4.32d - Two-Chip Split-Role Single-Shard MCPL Lookup Smoke

Upload the `cra_432d` folder itself so the JobManager path starts with `cra_432d/`. Do not upload `controlled_test_output`, the full repo, Downloads, or compiled host-test binaries.

## Exact JobManager Command

```text
cra_432d/experiments/tier4_32d_interchip_mcpl_smoke.py --mode run-hardware --output-dir tier4_32d_job_output
```

Paste the command directly into the EBRAINS JobManager command field. Do not wrap it in `bash`, `cd`, or `python3`.

## Placement Assumption

- Source/learning chip: `(0,0)`, learning core `7`.
- Remote/state chip: `(1,0)`, context/route/memory cores `4/5/6`.
- Source requests route east using `ROUTE_E`; remote replies route west using `ROUTE_W`.
- This is shard `0` only and uses 32 schedule events.

## Pass Boundary

PASS requires real target acquisition, profile builds/loads on both chips, state writes on the remote chip, schedule upload on the source chip, 96 lookup requests and 96 lookup replies on the learning core, zero stale/duplicate/timeout counters, compact readback, and zero synthetic fallback.

## Nonclaims

Tier 4.32d is a two-chip split-role single-shard MCPL lookup communication/readback smoke. It proves only the named source-chip learning to remote-chip state-core lookup path for shard 0 if hardware artifacts pass. It is not speedup evidence, not benchmark evidence, not true two-partition learning, not lifecycle scaling, not multi-shard learning, and not a native-scale baseline freeze.
