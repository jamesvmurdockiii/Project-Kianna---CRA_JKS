# Tier 4.22i EBRAINS Custom Runtime Round-Trip Job

Upload the `cra_422r` folder itself so the JobManager path starts with `cra_422r/`. Do not upload `controlled_test_output`.

This package uses the Tier 4.22k-confirmed official Spin1API event enum constants `MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`; legacy guessed names such as `MC_PACKET_RX` are intentionally blocked by the local syntax guard. It also uses the EBRAINS-confirmed packed SARK SDP fields (`dest_port`, `srce_port`, `dest_addr`, `srce_addr`) and `sark_mem_cpy`. Host commands follow the official Spin1API `sdp_msg_t` layout: opcode/status in `cmd_rc`, simple command arguments in `arg1`/`arg2`/`arg3`, and optional bytes in `data[]`. Router entries use official SARK router calls (`rtr_alloc`, `rtr_mc_set`, `rtr_free`) rather than local-stub-only helper names. The hardware Makefile delegates linking/APLX creation to official `spinnaker_tools.mk` so the generated build object, `cpu_reset` entrypoint, `libspin1_api.a`, and RO/RW section packing are present; it also creates nested object directories such as `build/gnu/src/` before official compile rules emit `build/gnu/src/*.o`.

Run command:

```text
cra_422r/experiments/tier4_22i_custom_runtime_roundtrip.py --mode run-hardware --output-dir tier4_22i_job_output
```

Target acquisition defaults to `--target-acquisition auto`: first use an explicit hostname/config if EBRAINS exposes one, otherwise run a tiny `pyNN.spiNNaker` probe and reuse `SpynnakerDataView`'s transceiver/IP for the raw custom-runtime load. If the EBRAINS image exposes a known board hostname, `--spinnaker-hostname <host>` is still accepted.

Expected pass means the custom C runtime builds, loads, and replies to `CMD_READ_STATE` on real SpiNNaker. It is not a full learning claim.
