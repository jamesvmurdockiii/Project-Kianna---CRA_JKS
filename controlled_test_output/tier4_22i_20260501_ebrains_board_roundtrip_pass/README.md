# Tier 4.22i EBRAINS Board Round-Trip Pass

- Ingested locally from `/Users/james/Downloads` after the EBRAINS JobManager run.
- Remote generated UTC: `2026-05-01T00:53:20+00:00`
- Remote output dir: `/tmp/job11618096177016154229.tmp/tier4_22i_job_output`
- Status: **PASS**
- Runner revision: `tier4_22i_custom_runtime_roundtrip_20260430_0009`
- Upload package: `cra_422r`

## What Passed

```text
custom C host tests pass: pass
main syntax check pass: pass
.aplx build status: pass
hardware target acquisition: pass via pyNN.spiNNaker_probe
spinnaker hostname/IP: 10.11.194.113
selected core: (0,0,4)
app load status: pass
command round-trip status: pass
read_state schema version: 1
read_state payload len: 73
post-mutation neuron_count: 2
post-mutation synapse_count: 1
reward_events after dopamine: 1
synthetic fallback: 0
```

## Claim Boundary

This is custom-runtime board-load and command round-trip evidence. It proves the
custom C sidecar can build into an `.aplx`, load onto a real SpiNNaker core,
accept mutation commands, and return the compact `CMD_READ_STATE` schema-v1
payload after state mutation.

It is not full CRA learning evidence, speedup evidence, multi-core scaling,
continuous runtime parity, or final on-chip autonomy. It unlocks Tier 4.22j, the
minimal custom-runtime closed-loop learning smoke.

## Files

Key normalized files in this folder:

```text
tier4_22i_results.json
tier4_22i_report.md
tier4_22i_environment.json
tier4_22i_target_acquisition.json
tier4_22i_load_result.json
tier4_22i_roundtrip_result.json
tier4_22i_aplx_build_stdout.txt
tier4_22i_aplx_build_stderr.txt
tier4_22i_host_test_stdout.txt
tier4_22i_host_test_stderr.txt
coral_reef.aplx
coral_reef.elf
coral_reef.txt
spinnaker_reports_2026-05-01-01-52-33-015933.zip
spinnaker_reports/reports/2026-05-01-01-52-33-015933/finished
spinnaker_reports/reports/2026-05-01-01-52-33-015933/global_provenance.sqlite3
```

## Missing Expected Download Files

```text
none
```
