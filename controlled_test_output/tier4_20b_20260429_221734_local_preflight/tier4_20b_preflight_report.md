# Tier 4.20b Source/Simulation Preflight

- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_20b_20260429_221734_local_preflight`

This preflight proves the source-only upload folder and local chunked runtime contract are runnable before a full EBRAINS hardware attempt.

It is not hardware evidence and cannot prove EBRAINS attached a SpiNNaker machine target.

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| source-only prepare smoke passed | `prepared` | `== prepared` | yes |
| local step-vs-chunked parity passed | `pass` | `== pass` | yes |
