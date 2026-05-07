# Tier 4.32a-hw-replicated - Replicated-Shard MCPL-First EBRAINS Scale Stress

Upload the `cra_432a_rep` folder itself so the JobManager path starts with `cra_432a_rep/`. Do not upload `controlled_test_output`, the full repo, Downloads, or compiled host-test binaries.

## Exact JobManager Command

```text
cra_432a_rep/experiments/tier4_32a_hw_replicated_shard_stress.py --mode run-hardware --output-dir tier4_32a_replicated_job_output
```

Paste the command directly into the EBRAINS JobManager command field. Do not wrap it in `bash`, `cd`, or `python3`.

## Scope

This job runs the predeclared replicated-shard single-chip stress points only:

- `point_08c_dual_shard`: 2 shards, 8 cores, 192 total task events.
- `point_12c_triple_shard`: 3 shards, 12 cores, 384 total task events.
- `point_16c_quad_shard`: 4 shards, 16 cores, 512 total task events.

Each shard has independent context/route/memory/learning cores, shard-specific MCPL keys, and compact per-core readback.

## Pass Boundary

PASS requires real target acquisition, 16 shard-specific profile builds/loads, per-shard pending/lookup parity, zero stale/duplicate/timeout counters, returned point artifacts, and zero synthetic fallback.

## Nonclaims

Tier 4.32a-hw-replicated is a single-chip replicated-shard EBRAINS hardware stress over the repaired Tier 4.32a-r1 MCPL value/meta protocol. It is not multi-chip evidence, not speedup evidence, not static reef partitioning, not benchmark superiority evidence, and not a native-scale baseline freeze.
