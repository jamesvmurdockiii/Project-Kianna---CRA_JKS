# Tier 4.22i EBRAINS APLX Load Pass / SDP Payload Short Failure

- Source package: `cra_422q`
- Runner revision: `tier4_22i_custom_runtime_roundtrip_20260430_0008`
- Status: `FAIL`, noncanonical hardware diagnostic
- Important result: target acquisition passed through `pyNN.spiNNaker`/`SpynnakerDataView`, the custom runtime `.aplx` built successfully, and `execute_flood` loaded the app onto core `(0,0,4)`.
- Remaining blocker: SDP command replies were only a 2-byte payload, and `CMD_READ_STATE` did not return the expected 73-byte schema-v1 state packet.

Diagnosis after official documentation review: Spin1API `sdp_msg_t` includes `cmd_rc`, `seq`, `arg1`, `arg2`, and `arg3` before `data[256]`. The host was sending CRA opcodes directly after the 8-byte SDP header while the C callback read `msg->data[0]`. The command/reply wire protocol must be repaired to use the official `sdp_msg_t` command/argument layout.

Claim boundary: build/load/target-acquisition diagnostic only; no command round-trip, learning, speedup, or on-chip autonomy claim.
