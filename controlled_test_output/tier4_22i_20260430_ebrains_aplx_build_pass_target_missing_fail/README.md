# Tier 4.22i EBRAINS APLX Build Pass / Target Missing Failure

- Source package: `cra_422p`
- Runner revision: `tier4_22i_custom_runtime_roundtrip_20260430_0007`
- Status: `FAIL`, noncanonical hardware evidence
- Important result: the official Spin1API/APLX build passed on EBRAINS.
- Remaining blocker: the raw custom-runtime runner did not acquire a board hostname/transceiver/IP, so app load and `CMD_READ_STATE` round-trip were not attempted.

This is not a CRA learning failure and not a custom C build failure. It is an EBRAINS target-acquisition gap for the raw sidecar loader. Prior PyNN hardware jobs acquired the board internally, so the next repair is to let Tier 4.22i acquire the same PyNN/sPyNNaker transceiver/IP context before loading the custom `.aplx`.

Claim boundary: build-pass evidence only; no board-load, command round-trip, speedup, or on-chip learning claim.
