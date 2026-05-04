# Tier 4.22i EBRAINS SDP Struct Build Failure

- Ingested: 2026-04-30
- Source attempt package: `cra_422l`
- Status: **FAIL**
- Classification: noncanonical raw custom-runtime toolchain/API compatibility failure

## What Happened

The run got past the Tier 4.22k multicast callback repair. EBRAINS compiled `main.c`, `neuron_manager.c`, `synapse_manager.c`, and `state_manager.c`, then failed compiling `src/host_interface.c`.

The failing symbols were old/local SDP struct assumptions: `dest_y`, `src_y`, `dest_x`, `src_x`, `src_port`, `dest_cpu`, and `src_cpu`. The EBRAINS SARK header exposes the packed official fields `dest_port`, `srce_port`, `dest_addr`, and `srce_addr`. The build also showed the SARK copy API is `sark_mem_cpy`, not `sark_memcpy`.

## Boundary

This is not CRA learning evidence, not a board-load failure, and not a command round-trip failure. The `.aplx` build failed before app load, so `CMD_READ_STATE` was not attempted. The hostname check also remained unset, but that is secondary until the runtime builds.

## Repair

Regenerate Tier 4.22i after updating the custom runtime to use official packed `sdp_msg_t` fields and `sark_mem_cpy`, and after tightening local stubs/static checks so this class is caught before upload.
