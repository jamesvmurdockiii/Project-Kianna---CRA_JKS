# Tier 4.27e — Two-core MCPL Round-trip Smoke

- Runner revision: `tier4_27e_two_core_mcpl_smoke_20260502_0001`
- Generated: 2026-05-03T03:17:07.952056+00:00
- Status: **PASS**

## Criteria

| Criterion | Value | Rule | Pass |
|-----------|-------|------|------|
| runner revision current | tier4_27e_two_core_mcpl_smoke_20260502_0001 | expected | yes |
| source wiring all checks pass | True | == True | yes |
| context_core .aplx built with MCPL | True | == True | yes |
| context_core ITCM < 32KB | 11248 | < 32768 | yes |
| learning_core .aplx built with MCPL | True | == True | yes |
| learning_core ITCM < 32KB | 12968 | < 32768 | yes |
| MCPL host test pass | 0 | == 0 | yes |
| MCPL callback registered | mcpl_lookup_callback + MCPL_PACKET_RECEIVED | present | yes |
| send/request use MCPL path | cra_state_mcpl_lookup_send_* | present | yes |

## Wiring Checks

- [PASS] main.c: mcpl_lookup_callback calls cra_state_mcpl_lookup_receive
- [PASS] main.c: cra_state_mcpl_init called in c_main
- [PASS] main.c: MCPL callback registered
- [PASS] state_manager.c: _send_lookup_request uses MCPL path
- [PASS] state_manager.c: _send_lookup_reply uses MCPL path
- [PASS] state_manager.c: cra_state_mcpl_init defined
- [PASS] state_manager.c: cra_state_mcpl_lookup_receive handles REQUEST
- [PASS] state_manager.c: cra_state_mcpl_lookup_receive handles REPLY

## Claim Boundary

Local build and wiring validation. NOT hardware evidence. Hardware deployment pending.
