# Tier 4.22i EBRAINS Official Make Nested Object Directory Failure

Generated from the EBRAINS JobManager output downloaded on 2026-04-30 after running the Tier 4.22i custom-runtime round-trip package `cra_422o`.

## What Failed

The previous manual-link/empty-ELF issue was repaired: this run used the official `spinnaker_tools.mk` path. The build then failed earlier in the official compile rule because the generated object target was nested under `build/gnu/src/`, but that directory did not exist:

```text
Fatal error: can't create build/gnu/src/main.o: No such file or directory
make: *** [spinnaker_tools.mk:195: build/gnu/src/main.o] Error 1
```

## Interpretation

This is not a CRA learning failure, not a board-load failure, not a `CMD_READ_STATE` protocol failure, and not a rejection of the official SpiNNaker build chain. The app never built or loaded.

The Makefile must keep using `spinnaker_tools.mk`, but it must create all nested object directories implied by `OBJECTS` before the official compile rules run.

## Claim Boundary

Status: `FAIL`, build-directory only.

No board load, no command round-trip, no learning, no performance, and no hardware-transfer claim should be made from this artifact.
