# Tier 4.22i EBRAINS Manual-Link Empty ELF Failure

Generated from the EBRAINS JobManager output downloaded on 2026-04-30 after running the Tier 4.22i custom-runtime round-trip package `cra_422n`.

## What Failed

The custom C sources compiled successfully through `router.c`, proving the previous SARK router API repair worked. The build then failed during ELF-to-binary/APLX creation:

```text
ld: warning: cannot find entry symbol cpu_reset; not setting start address
arm-none-eabi-objcopy: error: the input file 'build/coral_reef.elf' has no sections
make: *** [Makefile:91: build/coral_reef.aplx] Error 1
```

## Interpretation

This is not a CRA learning failure, not a board-load failure, and not a `CMD_READ_STATE` protocol failure. The app never loaded.

The runtime Makefile was using a hand-written link recipe that linked only CRA object files. It did not use the official SpiNNaker application build chain, which supplies the generated build object and `libspin1_api.a` needed for the `cpu_reset` entrypoint and the `RO_DATA` / `RW_DATA` sections consumed by the official APLX tooling.

## Repair Direction

Replace the manual hardware link/objcopy/APLX recipe with the official SpiNNakerManchester `spinnaker_tools.mk` rules while keeping host tests independent. Add local guards so future Tier 4.22i packages reject direct manual linking before EBRAINS upload.

## Claim Boundary

Status: `FAIL`, build-recipe only.

No board load, no command round-trip, no learning, no performance, and no hardware-transfer claim should be made from this artifact.
