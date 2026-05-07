# Tier 4.32e - Multi-Chip Learning Micro-Task

Upload the `cra_432e` folder itself so the JobManager path starts with `cra_432e/`. Do not upload `controlled_test_output`, the full repo, Downloads, or compiled host-test binaries.

## Exact JobManager Command

```text
cra_432e/experiments/tier4_32e_multichip_learning_microtask.py --mode run-hardware --output-dir tier4_32e_job_output
```

Paste the command directly into the EBRAINS JobManager command field. Do not wrap it in `bash`, `cd`, or `python3`.

## Placement Assumption

- Source/learning chip: `(0,0)`, learning core `7`.
- Remote/state chip: `(1,0)`, context/route/memory cores `4/5/6`.
- Source requests route east using `ROUTE_E`; remote replies route west using `ROUTE_W`.
- This is shard `0` only and uses 32 schedule events per case.
- It runs two cases: enabled learning at LR `0.25` and a no-learning LR `0.0` control.

## Pass Boundary

PASS requires real target acquisition, profile builds/loads on both chips, state writes on the remote chip, schedule upload on the source chip, 96 lookup requests and 96 lookup replies per case on the learning core, zero stale/duplicate/timeout counters, compact readback, enabled readout movement matching reference, no-learning readout immobility, and zero synthetic fallback.

## Nonclaims

Tier 4.32e is a two-chip split-role single-shard learning micro-task over the MCPL lookup path. It proves only that the named source-chip learning core can retrieve remote context/route/memory state from the remote chip and update its readout on a 32-event deterministic task while a no-learning control stays immobile. It is not speedup evidence, not benchmark evidence, not true two-partition learning, not lifecycle scaling, not multi-shard learning, and not a native-scale baseline freeze.
