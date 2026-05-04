# Tier 4.27f — Three-State-Core MCPL Lookup Smoke

- Runner revision: `tier4_27f_three_core_mcpl_smoke_20260502_0001`
- Generated: 2026-05-03T03:17:09.468741+00:00
- Status: **PASS**

## Criteria

| Criterion | Value | Rule | Pass |
|-----------|-------|------|------|
| runner revision current | tier4_27f_three_core_mcpl_smoke_20260502_0001 | expected | yes |
| source wiring all checks pass | True | == True | yes |
| context_core .aplx built with MCPL | True | == True | yes |
| context_core ITCM < 32KB | 11248 | < 32768 | yes |
| route_core .aplx built with MCPL | True | == True | yes |
| route_core ITCM < 32KB | 11280 | < 32768 | yes |
| memory_core .aplx built with MCPL | True | == True | yes |
| memory_core ITCM < 32KB | 11280 | < 32768 | yes |
| learning_core .aplx built with MCPL | True | == True | yes |
| learning_core ITCM < 32KB | 12968 | < 32768 | yes |
| MCPL host test pass | 0 | == 0 | yes |

## Wiring Checks

- [PASS] learning_core router mask catches all lookup types (0xFFF00000)
- [PASS] state cores use specific lookup type in router key
- [PASS] cra_state_mcpl_lookup_receive handles REQUEST for state cores
- [PASS] cra_state_mcpl_lookup_receive handles REPLY for learning core

## Build Summary

- context_core: text=11248 bytes, aplx_exists=True
- route_core: text=11280 bytes, aplx_exists=True
- memory_core: text=11280 bytes, aplx_exists=True
- learning_core: text=12968 bytes, aplx_exists=True

## Claim Boundary

Local build and wiring validation for four-core MCPL. NOT hardware evidence.
