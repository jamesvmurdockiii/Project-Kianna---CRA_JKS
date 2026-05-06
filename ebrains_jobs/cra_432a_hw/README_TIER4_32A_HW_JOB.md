# Tier 4.32a-hw - Single-Shard MCPL-First EBRAINS Scale Stress

Upload the `cra_432a_hw` folder itself so the JobManager path starts with `cra_432a_hw/`. Do not upload `controlled_test_output`, the full repo, Downloads, or compiled host-test binaries.

## Exact JobManager Command

```text
cra_432a_hw/experiments/tier4_32a_hw_single_shard_scale_stress.py --mode run-hardware --output-dir tier4_32a_hw_job_output
```

Paste the command directly into the EBRAINS JobManager command field. Do not wrap it in `bash`, `cd`, or `python3`.

## Scope

This job runs only the two Tier 4.32a single-shard points authorized after the Tier 4.32a-r1 MCPL repair:

- `point_04c_reference`: 4-core context/route/memory/learning reference, 48 events, 144 lookup requests/replies.
- `point_05c_lifecycle`: 5-core lifecycle bridge stress, 96 task events, 288 lookup requests/replies.

## Pass Boundary

PASS requires real target acquisition, successful profile builds/loads, compact readback, lookup request/reply parity, zero stale/duplicate/timeout counters, returned point artifacts, and zero synthetic fallback.

## Nonclaims

Tier 4.32a-hw is a single-shard single-chip EBRAINS hardware stress over the repaired Tier 4.32a-r1 MCPL protocol. It is not replicated-shard stress, not multi-chip evidence, not speedup evidence, not static reef partitioning, not benchmark superiority evidence, and not a native-scale baseline freeze.
