# Tier 4.24 - Custom Runtime Resource Characterization

- Generated: `2026-05-02T01:51:35.703003+00:00`
- Mode: `local`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_24_20260501_resource_characterization`

## Claim Boundary

Resource-measurement evidence only. Proves the continuous path reduces
host commands during execution versus the chunked command-driven micro-loop.
Does not prove speedup, multi-core scaling, or final autonomy.

## Binary Metrics

- APLX size: `0` bytes
- ELF size: `0` bytes
- text: `0` bytes
- data: `0` bytes
- bss: `0` bytes
- Build time: `0.000` s

## Timing Metrics (from 4.23c hardware pass)

- Board: `10.11.235.9`
- Core: `(0,0,4)`
- Load time: `2.187` s
- Task time (reset through readback): `4.327` s
- Stopped timestep: `6170`

## Intervention Comparison

- Continuous path commands: `64`
- Chunked 4.22x commands: `134`
- Reduction: `70` commands
- Reduction ratio: `0.522`

- Continuous payload: `2647` bytes
- Chunked payload: `4099` bytes
- Reduction: `1452` bytes
- Reduction ratio: `0.354`

## Memory Footprint Estimate

- MAX_CONTEXT_SLOTS: `8` → `128` bytes
- MAX_ROUTE_SLOTS: `8` → `128` bytes
- MAX_MEMORY_SLOTS: `8` → `128` bytes
- MAX_PENDING_HORIZONS: `128` → `4096` bytes
- MAX_SCHEDULE_ENTRIES: `64` → `1792` bytes
- Misc static: `100` bytes
- **DTCM estimate: `6372` bytes**

## Safe Default Limits

- Max observed pending depth: `3`
- Max schedule entries (compile-time): `64`
- Active context slots used: `4` / `8`
- Active route slots used: `4` / `8`
- Active memory slots used: `4` / `8`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_24_resource_characterization_20260501_0001` | `expected current source` | yes |
| custom C host tests pass | `pass` | `== pass` | yes |
| .aplx built (EBRAINS 4.23c proved) | `0` | `> 0 or EBRAINS proved` | yes |
| .elf built (EBRAINS 4.23c proved) | `0` | `> 0 or EBRAINS proved` | yes |
| 4.23c hardware artifacts exist | `6170` | `> 0` | yes |
| load time measured | `2.1873621880076826` | `> 0` | yes |
| task time measured | `4.327049097977579` | `> 0` | yes |
| continuous command count < chunked | `64` | `< 134` | yes |
| command reduction > 0 | `70` | `> 0` | yes |
| payload reduction > 0 | `1452` | `> 0` | yes |
| max pending depth documented | `3` | `>= 3` | yes |
| active slots documented | `ctx=4 route=4 mem=4` | `all > 0` | yes |
| DTCM estimate computed | `6372` | `> 0` | yes |
| max schedule length documented | `64` | `>= 64` | yes |

