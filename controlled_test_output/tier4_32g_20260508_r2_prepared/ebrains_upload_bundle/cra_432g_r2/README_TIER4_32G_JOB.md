# Tier 4.32g - Two-Chip Lifecycle Traffic/Resource Hardware Smoke

Upload the `cra_432g_r2` folder itself so the JobManager path starts with `cra_432g_r2/`. Do not upload `controlled_test_output`, the full repo, Downloads, or compiled host-test binaries.

## Exact JobManager Command

```text
cra_432g_r2/experiments/tier4_32g_multichip_lifecycle_traffic_resource_smoke.py --mode run-hardware --output-dir tier4_32g_job_output
```

Paste the command directly into the EBRAINS JobManager command field. Do not wrap it in `bash`, `cd`, or `python3`.

## Placement Assumption

- Source/learning chip: `(0,0)`, learning core `7`.
- Remote/lifecycle chip: `(1,0)`, lifecycle core `4`.
- Source lifecycle requests route east using `ROUTE_E`; lifecycle mask sync routes west using `ROUTE_W`.
- This is shard `0` only and sends one trophic request plus one death event request.

## Pass Boundary

PASS requires real target acquisition, profile builds/loads on both chips, lifecycle init, source event/trophic emission, remote lifecycle receipt/mutation, source active-mask sync receipt, compact lifecycle traffic counters, zero stale/duplicate/missing-ack counters, and zero synthetic fallback.

## Nonclaims

Tier 4.32g is a two-chip lifecycle traffic/resource smoke. It proves only that the named source-chip learning core can emit lifecycle event/trophic MCPL requests to a remote-chip lifecycle core and receive the resulting active-mask/lineage sync through compact readback counters. It is not lifecycle scaling, not benchmark evidence, not speedup evidence, not multi-shard learning, not true partitioned ecology, and not a native-scale baseline freeze.
