# Tier 4.24b / 4.25-Preflight — EBRAINS Build/Size Resource Capture — Ingest Report

- Status: **PASS**
- Passed: 11/11
- Hardware output: `controlled_test_output/tier4_24b_20260502_ebrains_build_size_capture`

## Build Metrics

| Metric | Value |
|--------|-------|
| .aplx size | 13684 bytes |
| .elf size | 240892 bytes |
| text | 13608 bytes |
| data | 12 bytes |
| bss | 6813 bytes |
| total (text+data+bss) | 20433 bytes |
| runtime profile | decoupled_memory_route |

## Criteria

- ✓ hardware results exist: `controlled_test_output/tier4_24b_20260502_ebrains_build_size_capture/tier4_24b_hardware_results.json` (exists)
- ✓ build metrics exist: `controlled_test_output/tier4_24b_20260502_ebrains_build_size_capture/tier4_24b_build_metrics.json` (exists)
- ✓ build succeeded: `0` (== 0)
- ✓ .aplx size non-zero: `13684` (> 0)
- ✓ .elf size non-zero: `240892` (> 0)
- ✓ size tool succeeded: `True` (== True)
- ✓ text section non-zero: `13608` (> 0)
- ✓ data section measured: `12` (>= 0)
- ✓ bss section measured: `6813` (>= 0)
- ✓ runtime profile verified: `decoupled_memory_route` (== decoupled_memory_route)
- ✓ no zero-size loopholes: `all sizes > 0` (true)
