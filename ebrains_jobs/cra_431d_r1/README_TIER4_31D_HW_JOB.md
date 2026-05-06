# Tier 4.31d EBRAINS Native Temporal-Substrate Hardware Smoke

Upload the `cra_431d_r1` folder itself so the JobManager path starts with `cra_431d_r1/`. Do not upload `controlled_test_output`.

JobManager command:

```text
cra_431d_r1/experiments/tier4_31d_native_temporal_hardware_smoke.py --mode run-hardware --output-dir tier4_31d_hw_job_output
```

Runner revision: `tier4_31d_native_temporal_hardware_smoke_20260506_0003`.

Purpose: build/load the learning_core runtime image and exercise C-owned temporal commands 39-42 on one real SpiNNaker board. The runner sends enabled, zero-state, frozen-state, and reset-each-update temporal-control sequences, then compares compact 48-byte readbacks against the fixed-point reference.

Diagnostic artifacts to download on failure include `tier4_31d_hw_milestone.json`, `tier4_31d_hw_results.json`, `tier4_31d_aplx_build_stdout.txt`, and `tier4_31d_aplx_build_stderr.txt` when present. An ELF or profile stdout by itself is not hardware evidence.

PASS is hardware execution/readback only: real target acquisition, no fallback, successful build/load, payload_len=48, schema/checksum/counter/reference matches, and destructive controls separated. It is not benchmark performance, speedup, multi-chip scaling, nonlinear recurrence, replay/sleep, or full v2.2 hardware transfer.
