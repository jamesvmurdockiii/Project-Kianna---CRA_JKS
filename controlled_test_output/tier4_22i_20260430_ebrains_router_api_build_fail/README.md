# Tier 4.22i EBRAINS Router API Build Failure

Generated from the EBRAINS JobManager output downloaded on 2026-04-30 after running the Tier 4.22i custom-runtime round-trip package `cra_422m`.

## What Failed

The custom runtime did not reach board load or `CMD_READ_STATE` round-trip. The `.aplx` build stopped while compiling `src/router.c`.

Primary compiler errors:

```text
src/router.h:45:23: error: unknown type name 'uint32_t'
src/router.h:24:1: note: 'uint32_t' is defined in header '<stdint.h>'; did you forget to '#include <stdint.h>'?
src/router.c:73:26: warning: implicit declaration of function 'sark_router_alloc'
src/router.c:82:9: warning: implicit declaration of function 'sark_router_free'
```

## Interpretation

This is not a CRA learning failure and not a hardware result failure. It is another EBRAINS C ABI/build compatibility failure in the custom runtime.

The previous Tier 4.22i SDP/SARK fix worked: `host_interface.c` compiled on EBRAINS and produced `host_interface.o`. The build then advanced to the router layer and exposed two new issues:

1. `router.h` used `uint32_t` without including `<stdint.h>` directly.
2. The runtime used local-stub-only router helpers `sark_router_alloc()` / `sark_router_free()`, which are not exposed by the EBRAINS SARK headers.

Official SpiNNakerManchester `spinnaker_tools` exposes router allocation through `rtr_alloc()`, `rtr_mc_set()`, and `rtr_free()` in `sark.h`, so the runtime and local stubs must be updated to those names.

## Claim Boundary

Status: `FAIL`, build-interface only.

No board load, no readback, no learning, no performance, and no hardware-transfer claim should be made from this artifact.
