# SpiNNaker / EBRAINS Custom Runtime Guide

This guide is the canonical operating manual for CRA custom-runtime work on
EBRAINS/SpiNNaker. Use it before every raw custom-runtime run.

It is deliberately stricter than the older PyNN bridge workflow because a custom
C runtime has to satisfy three different interfaces at once:

1. EBRAINS JobManager upload and command execution.
2. SpiNNakerManchester C toolchain, Spin1API, SARK, and router APIs.
3. Host-to-core SDP/SCP wire protocol.

## Official References

Use official SpiNNakerManchester material first:

- SpiNNaker Technical Documents: `https://spinnakermanchester.github.io/docs/`
- AppNote 4, SDP specification: `https://spinnakermanchester.github.io/docs/spinn-app-4.pdf`
- AppNote 5, SCP specification: `https://spinnakermanchester.github.io/docs/spinn-app-5.pdf`
- Spin1API documentation: `https://spinnakermanchester.github.io/docs/SpiNNapi_docV200.pdf`
- Spin1API generated docs: `https://spinnakermanchester.github.io/spinnaker_tools/spin1__api_8c.html`

Important AppNote 4 point: SDP/SCP command packets are not just:

```text
8-byte SDP header + arbitrary data
```

For command traffic, the data area is structured as:

```text
cmd_rc u16
seq    u16
arg1   u32
arg2   u32
arg3   u32
data   up to 256 bytes
```

That command header is exactly why CRA host packets now place the opcode in
`cmd_rc`, simple command arguments in `arg1`/`arg2`/`arg3`, and compact state
bytes in `data[]`.

## Current Passed Gates

```text
Tier 4.22i - Custom Runtime Board Round-Trip Smoke
runner_revision = tier4_22i_custom_runtime_roundtrip_20260430_0009
upload folder   = ebrains_jobs/cra_422r
returned pass    = controlled_test_output/tier4_22i_20260501_ebrains_board_roundtrip_pass/
```

Tier 4.22i is not a learning tier. It is a tiny board smoke test:

```text
build .aplx
acquire EBRAINS board target
load app onto one free core
send RESET/BIRTH/SYNAPSE/DOPAMINE/READ_STATE commands
validate 73-byte CMD_READ_STATE schema-v1 payload
```

Pass means the custom C sidecar can be built, loaded, commanded, and read back
on real hardware. It does not prove full CRA learning, speedup, scale, or final
on-chip autonomy.

```text
Tier 4.22j - Minimal Custom-Runtime Closed-Loop Learning Smoke
runner_revision = tier4_22j_minimal_custom_runtime_learning_20260501_0001
upload folder   = ebrains_jobs/cra_422s
returned pass   = controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/
```

```text
Tier 4.22l - Tiny Custom-Runtime Learning Parity
runner_revision = tier4_22l_custom_runtime_learning_parity_20260501_0001
upload folder   = ebrains_jobs/cra_422t
prepared output = controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/
returned pass   = controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_hardware_pass_ingested/
```

```text
Tier 4.22m - Minimal Custom-Runtime Task Micro-Loop
runner_revision = tier4_22m_custom_runtime_task_micro_loop_20260501_0001
upload folder   = ebrains_jobs/cra_422u
local output    = controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_local/
prepared output = controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_prepared/
returned pass   = controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_hardware_pass_ingested/
```

```text
Tier 4.22n - Tiny Delayed-Cue Custom-Runtime Micro-Task
runner_revision = tier4_22n_delayed_cue_micro_task_20260501_0001
upload folder   = ebrains_jobs/cra_422v
local output    = controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_local/
prepared output = controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_prepared/
returned pass   = controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/
```

```text
Tier 4.22o - Tiny Noisy-Switching Custom-Runtime Micro-Task
runner_revision = tier4_22o_noisy_switching_micro_task_20260501_0002_mul64
upload folder   = ebrains_jobs/cra_422x
local output    = controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_local/
prepared output = controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_prepared/
returned pass   = controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/
```

Tier 4.22o `cra_422w` is intentionally preserved as a noncanonical failed
hardware diagnostic. It proved the board/build/load/command path worked, then
exposed a signed fixed-point overflow in `FP_MUL` during the first
noisy-switching regime flip. The repaired `cra_422x` package carries the
`int64_t` fixed-point multiply repair and host tests for both the large signed
product and the pending-horizon switch update; it then passed on real hardware
with all prediction/weight/bias raw deltas equal to `0`.

```text
Tier 4.22p - Tiny A-B-A Reentry Custom-Runtime Micro-Task
runner_revision = tier4_22p_reentry_micro_task_20260501_0001
upload folder   = ebrains_jobs/cra_422y
local output    = controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_local/
prepared output = controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_prepared/
returned pass   = controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_hardware_pass_ingested/
```

Tier 4.22p has passed on EBRAINS. It keeps the same
`CMD_SCHEDULE_PENDING`/`CMD_MATURE_PENDING` command surface but expands the
task reference to a 30-event A-B-A stream: regime A follows the feature, regime
B reverses it, and the final A phase returns to the first rule. Local reference
accuracy is `0.8666666667`, tail accuracy is `1.0`, max pending depth is `3`,
and final raw readout is `30810/-1`. The returned run matched the local
fixed-point reference exactly with all prediction/weight/bias raw deltas `0`.

```text
Tier 4.22q - Tiny Integrated V2 Bridge Custom-Runtime Smoke
runner_revision = tier4_22q_integrated_v2_bridge_smoke_20260501_0001
upload folder   = ebrains_jobs/cra_422z
local output    = controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_local/
prepared output = controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_prepared/
returned pass   = controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_hardware_pass_ingested/
```

Tier 4.22q has passed on EBRAINS. It adds a tiny host-side v2-style bridge in
front of the custom runtime: keyed context slots plus route state transform
visible cues into a signed scalar feature stream. The custom runtime still owns
pending horizon state, pre-update prediction scoring, oldest-first delayed
maturation, and fixed-point readout updates. The returned run passed on board
`10.11.236.65`, selected core `(0,0,4)`, with `47/47` remote criteria plus
ingest criterion, all prediction/weight/bias raw deltas `0`, accuracy
`0.9333333333`, tail accuracy `1.0`, bridge context/route updates `9/9`, max
keyed slots `3`, max pending depth `3`, and final raw readout `32768/0`.

Tier 4.22j is the first tiny chip-owned learning heartbeat after the 4.22i
board command path passed:

```text
RESET
CMD_SCHEDULE_PENDING(feature, delay)
wait for the pending horizon to become due
CMD_MATURE_PENDING(target, learning_rate)
CMD_READ_STATE verifies pending/reward/readout counters changed
```

Pass means one delayed pending/readout update happened inside the loaded custom
runtime. It does not prove full CRA task learning, v2.1 mechanism transfer,
speedup, scale, or final on-chip autonomy.

Raw EBRAINS status was `fail` because the runner criterion used
`active_pending or -1`; the returned state had the correct value
`active_pending=0`. The raw manifest/report are preserved in the ingested
folder, the evaluator is fixed, and the normalized ingested result is the
auditable evidence classification.

## Clean Upload Layout

For the current Tier 4.22q run, upload exactly this generated folder:

```text
<repo>/ebrains_jobs/cra_422z
```

The remote JobManager workspace should contain:

```text
cra_422z/
  README_TIER4_22Q_JOB.md
  experiments/
    tier4_22q_integrated_v2_bridge_smoke.py
    tier4_22l_custom_runtime_learning_parity.py
    tier4_22j_minimal_custom_runtime_learning.py
    tier4_22i_custom_runtime_roundtrip.py
  coral_reef_spinnaker/
    __init__.py
    python_host/
      colony_controller.py
    spinnaker_runtime/
      Makefile
      src/
      stubs/
      tests/
```

Do not upload:

```text
controlled_test_output/
docs/
baselines/
old ebrains_jobs folders
repo root with stale cached packages
```

Reason: EBRAINS jobs need a compact source package. The evidence folders are
research artifacts, not runtime inputs, and can be gigabytes.

## EBRAINS Command

Run this command in JobManager:

```text
cra_422z/experiments/tier4_22q_integrated_v2_bridge_smoke.py --mode run-hardware --output-dir tier4_22q_job_output
```

Do not wrap this in `bash`, `cd`, or local shell-only instructions. EBRAINS
JobManager executes the uploaded command path directly.

If EBRAINS exposes a board hostname and auto acquisition fails, use:

```text
cra_422z/experiments/tier4_22q_integrated_v2_bridge_smoke.py --mode run-hardware --spinnaker-hostname <host> --output-dir tier4_22q_job_output
```

Default target acquisition is:

```text
--target-acquisition auto
```

That means:

1. Try explicit hostname/config/environment discovery.
2. If no raw hostname is visible, run a tiny `pyNN.spiNNaker` probe.
3. Reuse `SpynnakerDataView` transceiver/IP for raw `.aplx` loading.
4. Avoid cores occupied by the probe placement when choosing `dest_cpu`.

## Local Preparation Gate

Before any EBRAINS upload, run:

```text
make tier4-22q-local
make tier4-22q-prepare
```

Expected:

```text
status = prepared
upload_folder = <repo>/ebrains_jobs/cra_422z
```

The prepare gate checks:

```text
main.c syntax against strict host stubs
CMD_SCHEDULE_PENDING / CMD_MATURE_PENDING command surface
fixed-point prediction/update equation guards
explicit mature_timestep support
host-v2 bridge metadata guards
three keyed context slots plus route updates in the task reference
source and bundle parity guards
```

## What We Got Right

These are the practices that moved the custom runtime from vague failure to
real progress:

1. We stopped uploading the whole repo.
   The generated `ebrains_jobs/cra_422*` folders are small, source-only, and
   cache-busting. The latest passed one is `ebrains_jobs/cra_422z`. They avoid
   `controlled_test_output/` and other local evidence folders that EBRAINS does
   not need.

2. We preserved every failed EBRAINS return.
   Each failure folder remains noncanonical diagnostic evidence instead of
   being hidden or overwritten. That made the platform mismatch trail auditable.

3. We separated claim layers.
   Build, target acquisition, app load, command round-trip, and learning are
   separate criteria. The `cra_422q` result was therefore correctly classified
   as build/load progress but command-protocol failure.

4. We created discovery tiers instead of guessing forever.
   Tier 4.22k inspected the EBRAINS build-image headers and confirmed the
   official Spin1API callback names before the next raw board attempt.

5. We made local stubs stricter after each platform mismatch.
   The stubs now mirror official event names, packed SARK SDP fields, router
   APIs, and command-header fields so local checks are less likely to bless
   code EBRAINS cannot build or run.

6. We switched to the official SpiNNaker build chain.
   Delegating hardware build/link/APLX creation to `spinnaker_tools.mk` fixed
   the empty-ELF/manual-link problem and aligned the runtime with the official
   toolchain path.

7. We added automatic target acquisition through PyNN/sPyNNaker.
   The pyNN probe plus `SpynnakerDataView` transceiver/IP bridge solved the
   EBRAINS raw-hostname visibility problem and selected a free application
   core.

8. We validated the next upload package locally before asking for hardware.
   `cra_422r` is prepared only after source and bundle guards pass for
   callbacks, SARK SDP fields, router APIs, build recipe, nested object dirs,
   and official SDP/SCP command-header layout.

9. We documented the exact command format.
   The JobManager command now starts with the uploaded folder path directly. No
   `bash`, no local `cd`, no accidental wrapper command unless a package README
   explicitly says so.

10. We turned an error into a protocol contract.
    The 2-byte payload-short failure identified the missing SDP/SCP command
    header. The repair now lives in source, tests, protocol spec, runbook, and
    generated package docs.

## What We Did Wrong

This is the frank ledger.

1. We reused mental models from the PyNN bridge path.
   PyNN/sPyNNaker jobs validate graph construction and spike readback. A raw C
   sidecar also needs explicit toolchain ABI and SDP command compatibility.

2. We trusted local stubs too much.
   The stubs compiled code that did not match EBRAINS SARK/Spin1API naming. We
   fixed this by adding Tier 4.22k header discovery and making stubs stricter.

3. We guessed callback names.
   EBRAINS exposed `MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`, not guessed
   `MC_PACKET_RX` names.

4. We guessed SARK SDP field names.
   EBRAINS SARK uses packed fields such as `dest_port`, `srce_port`,
   `dest_addr`, and `srce_addr`, plus `sark_mem_cpy`.

5. We guessed router helper names.
   EBRAINS SARK exposes `rtr_alloc`, `rtr_mc_set`, and `rtr_free`, not
   local-only `sark_router_*` helpers.

6. We tried a manual linker recipe.
   The object-only link omitted official startup/build objects and produced an
   invalid/empty ELF/APLX path. The runtime now delegates to official
   `spinnaker_tools.mk`.

7. We did not create nested object directories before official build rules.
   `spinnaker_tools.mk` emitted objects under `build/gnu/src/`; the Makefile now
   creates those directories explicitly.

8. We treated target discovery as raw hostname-only.
   EBRAINS often gives pyNN/sPyNNaker access without exposing a simple hostname.
   The current runner uses a tiny `pyNN.spiNNaker` probe and `SpynnakerDataView`
   transceiver/IP when needed.

9. We treated SDP command data as starting immediately after the SDP header.
   Official SDP/SCP command packets include `cmd_rc`, `seq`, `arg1`, `arg2`,
   and `arg3` before `data[]`. This caused the Apr 30 `cra_422q` result:
   app load passed, but command round-trip returned only 2-byte short payloads.

10. We did not initially log raw reply bytes on short-payload failure.
    The controller now attaches compact raw reply debug to failed read-state
    parses.

## Latest Passed Board Smoke

```text
artifact folder:
controlled_test_output/tier4_22i_20260501_ebrains_board_roundtrip_pass/

source package:
cra_422r

runner:
tier4_22i_custom_runtime_roundtrip_20260430_0009

meaning:
build pass, target acquisition pass, app load pass, command round-trip pass
```

The pass showed:

```text
hardware target = 10.11.194.113
selected core = (0,0,4)
custom C host tests = pass
.aplx build = pass
app load = pass
RESET/BIRTH/CREATE_SYN/DOPAMINE acknowledgements = true
CMD_READ_STATE schema_version = 1
CMD_READ_STATE payload_len = 73
post-mutation neuron_count = 2
post-mutation synapse_count = 1
post-dopamine reward_events = 1
synthetic fallback = 0
```

This unlocks Tier 4.22j minimal custom-runtime closed-loop learning smoke. It
does not prove full CRA learning, speedup, multi-core scaling, continuous
runtime parity, or final on-chip autonomy.

## Latest Failure Class Before Pass

```text
artifact folder:
controlled_test_output/tier4_22i_20260430_ebrains_aplx_load_pass_sdp_payload_short_fail/

source package:
cra_422q

runner:
tier4_22i_custom_runtime_roundtrip_20260430_0008

meaning:
build pass, target acquisition pass, app load pass, command protocol fail
```

This was not a science failure and not a build failure. It was a host/runtime
SDP command-layout mismatch.

The repair is:

```text
cra_422r
runner_revision = tier4_22i_custom_runtime_roundtrip_20260430_0009
```

Progress worth preserving:

```text
cra_422q proved the official build recipe, target acquisition, free-core
selection, and app-load path can work on EBRAINS/SpiNNaker. The remaining
failure was narrower than the previous ones: command protocol only.
```

That is useful progress, but not yet a pass.

## Common Failure Triage

If `.aplx` build fails:

```text
read tier4_22i_aplx_build_stderr.txt
check Spin1API/SARK/router symbol mismatch
do not run board claims
```

If target acquisition fails:

```text
read tier4_22i_target_acquisition.json
check hostname discovery attempt
check pyNN.spiNNaker probe attempt
do not treat as CRA failure
```

If app load fails:

```text
read tier4_22i_load_result.json
check selected dest_cpu
check occupied cores
check execute_flood exception
```

If command round-trip fails:

```text
read tier4_22i_roundtrip_result.json
inspect reset/birth/synapse/dopamine ack flags
inspect state_after_reset/state_after_mutation debug.raw_hex
check whether reply payload length is 2, 73, or timeout
```

If `payload_too_short` with payload length 2:

```text
the board likely replied with cmd/status only
the app received a command but did not return schema state
check cmd_rc/data[] offsets and runtime dispatch path
```

If timeout:

```text
check app core state
check SDP destination CPU/port
check whether load actually started the app
check IOBUF if available
```

## Why This Matters For The Roadmap

Tier 4.22i was the gate before:

```text
Tier 4.22j - minimal custom-runtime closed-loop learning smoke
Tier 4.22k+ - deeper on-chip mechanism ports
```

We should not port memory/replay/routing/self-evaluation into C until the tiny
custom runtime can be reliably:

```text
built
loaded
commanded
mutated
read back
```

That is the correct scaffold for eventual full on-chip learning. It is not the
final runtime. It is the first reliable wire, build, and state-readback contract.

Tier 4.22j passed as the smallest proof that the runtime can own a delayed
pending/readout update rather than merely accepting commands.

## Current Operator Step

Tier 4.22q has passed. Rerun it only if a fresh confirmation is needed.
Generate or refresh it locally with:

```text
make tier4-22q-local
make tier4-22q-prepare
```

Upload:

```text
<repo>/ebrains_jobs/cra_422z
```

Run command:

```text
cra_422z/experiments/tier4_22q_integrated_v2_bridge_smoke.py --mode run-hardware --output-dir tier4_22q_job_output
```

Download every returned file after it finishes and ingest it before citing it.
The current ingested pass is:

```text
controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_hardware_pass_ingested/
```

Tier 4.22p has passed. Rerun it only if a fresh confirmation is needed.
Generate or refresh it locally with:

```text
make tier4-22p-local
make tier4-22p-prepare
```

Upload:

```text
<repo>/ebrains_jobs/cra_422y
```

Run command:

```text
cra_422y/experiments/tier4_22p_reentry_micro_task.py --mode run-hardware --output-dir tier4_22p_job_output
```

Download every returned file after it finishes and ingest it before citing it.
The current ingested pass is:

```text
controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_hardware_pass_ingested/
```

Tier 4.22p task reference:

```text
30 signed A-B-A reentry events
regime A initial: target follows feature
regime B: target is opposite feature
regime A reentry: target follows feature again
pending_gap_depth=2
max_pending_depth=3
learning_rate=0.5625
expected accuracy=0.8666666667
expected tail_accuracy=1.0
expected final readout_weight_raw=30810
expected final readout_bias_raw=-1
```

Returned 4.22p result:

```text
board=10.11.222.17
selected_core=(0,0,4)
criteria=44/44
events=30 schedule/mature pairs
max_observed_pending_depth=3
prediction/weight/bias raw deltas=0
observed accuracy=0.8666666667
observed tail_accuracy=1.0
final pending_created=pending_matured=reward_events=decisions=30
final active_pending=0
final readout_weight_raw=30810
final readout_bias_raw=-1
```

Boundary: 4.22p is tiny A-B-A reentry custom-runtime micro-task evidence only.
It does not prove full CRA recurrence, v2.1 mechanism transfer, speedup,
multi-core scaling, or final autonomy.

Tier 4.22n has passed after EBRAINS ingest. Regenerate or rerun it only if a
fresh confirmation is needed:

```text
make tier4-22n-local
make tier4-22n-prepare
```

Upload:

```text
<repo>/ebrains_jobs/cra_422v
```

Run command:

```text
cra_422v/experiments/tier4_22n_delayed_cue_micro_task.py --mode run-hardware --output-dir tier4_22n_job_output
```

Download every returned file after it finishes and ingest it before citing it.

Tier 4.22n task reference:

```text
12 signed delayed-cue-like events
feature alternates +1.0, -1.0
target equals feature
pending_gap_depth=2
max_pending_depth=3
learning_rate=0.125
expected accuracy=0.8333333333
expected tail_accuracy=1.0
expected final readout_weight_raw=30720
expected final readout_bias_raw=0
```

Returned 4.22n result:

```text
board=10.11.205.1
selected_core=(0,0,4)
.aplx build/load=pass
events=12 delayed schedule/mature pairs
max_observed_pending_depth=3
prediction/weight/bias raw deltas=0
observed accuracy=0.8333333333
observed tail_accuracy=1.0
final pending_created=pending_matured=reward_events=decisions=12
final active_pending=0
final readout_weight_raw=30720
final readout_bias_raw=0
```

Tier 4.22o has since passed as `ebrains_jobs/cra_422x`; Tier 4.22p
`ebrains_jobs/cra_422y` has also passed. Use the current operator step above
only for reruns.

Tier 4.22m has passed after ingest. Regenerate locally only if a rerun is needed:

```text
make tier4-22m-local
make tier4-22m-prepare
```

Upload:

```text
<repo>/ebrains_jobs/cra_422u
```

Rerun command:

```text
cra_422u/experiments/tier4_22m_custom_runtime_task_micro_loop.py --mode run-hardware --output-dir tier4_22m_job_output
```

Downloaded returned files were ingested at `controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_hardware_pass_ingested/` before citation.

Tier 4.22m task reference and returned result:

```text
12 signed fixed-pattern events
feature alternates +1.0, -1.0
target equals feature
learning_rate=0.25
expected accuracy=0.9166666667
expected tail_accuracy=1.0
expected final readout_weight_raw=32256
expected final readout_bias_raw=0
returned board IP=10.11.202.65
returned selected core=(0,0,4)
returned observed accuracy=0.9166666667
returned observed tail_accuracy=1.0
returned raw deltas all 0
```

Tier 4.22l has passed after ingest. Regenerate locally only if a rerun is
needed:

```text
make tier4-22l-local
make tier4-22l-prepare
```

Upload:

```text
<repo>/ebrains_jobs/cra_422t
```

Rerun command:

```text
cra_422t/experiments/tier4_22l_custom_runtime_learning_parity.py --mode run-hardware --output-dir tier4_22l_job_output
```

Download every returned file after it finishes and ingest it before citing it.

Tier 4.22l tiny parity sequence:

```text
feature= 1.0 target= 1.0
feature= 1.0 target=-1.0
feature=-1.0 target=-1.0
feature=-1.0 target= 0.5
learning_rate=0.25
expected final readout_weight_raw=-4096
expected final readout_bias_raw=-4096
```

Returned evidence from the pass:

```text
board IP = 10.11.194.1
selected core = (0,0,4)
prediction raw deltas = [0, 0, 0, 0]
weight raw deltas = [0, 0, 0, 0]
bias raw deltas = [0, 0, 0, 0]
final readout_weight_raw = -4096
final readout_bias_raw = -4096
```

Pass means the loaded custom runtime's predictions and readout updates matched
the local reference within raw tolerance `1`. It still does not prove full CRA
task learning, v2.1 mechanism transfer, speedup, scale, or final on-chip
autonomy.

## Tier 4.22r Native Context-State Gate

Tier 4.22r passed as the first custom-runtime gate that moves a v2-style state
primitive from host bridge code into C-owned runtime state.

```text
Tier 4.22r - Tiny Native Context-State Custom-Runtime Smoke
runner_revision = tier4_22r_native_context_state_smoke_20260501_0001
upload folder   = ebrains_jobs/cra_422aa
local output    = controlled_test_output/tier4_22r_20260501_native_context_state_smoke_local/
prepared output = controlled_test_output/tier4_22r_20260501_native_context_state_smoke_prepared/
returned pass   = controlled_test_output/tier4_22r_20260501_native_context_state_smoke_hardware_pass_ingested/
```

Upload folder:

```text
<repo>/ebrains_jobs/cra_422aa
```

JobManager command:

```text
cra_422aa/experiments/tier4_22r_native_context_state_smoke.py --mode run-hardware --output-dir tier4_22r_job_output
```

Key difference from Tier 4.22q:

```text
4.22q: host computes feature from keyed context + route and sends feature
4.22r: host writes context, then chip retrieves context and computes feature=context*cue
```

New protocol commands:

```text
CMD_WRITE_CONTEXT = 11
CMD_READ_CONTEXT = 12
CMD_SCHEDULE_CONTEXT_PENDING = 13
```

Returned pass metrics: board `10.11.237.25`, selected core `(0,0,4)`, `58/58` remote criteria plus ingest criterion, all raw deltas `0`, context writes `9`, context reads `30`, tail accuracy `1.0`, final `readout_weight_raw=32752`, final `readout_bias_raw=-16`. Boundary: Tier 4.22r is still a tiny native state-primitive smoke. It is not full v2.1 memory/routing, not full CRA task learning, and not speedup evidence.

## Tier 4.22s Native Route-State Gate

Tier 4.22s is prepared as the next custom-runtime gate after the Tier 4.22r
native context hardware pass. It adds one native route-state primitive while
leaving learning, pending credit, and the task size unchanged.

```text
Tier 4.22s - Tiny Native Route-State Custom-Runtime Smoke
runner_revision = tier4_22s_native_route_state_smoke_20260501_0001
upload folder   = ebrains_jobs/cra_422ab
local output    = controlled_test_output/tier4_22s_20260501_native_route_state_smoke_local/
prepared output = controlled_test_output/tier4_22s_20260501_native_route_state_smoke_prepared/
```

Upload folder:

```text
<repo>/ebrains_jobs/cra_422ab
```

JobManager command:

```text
cra_422ab/experiments/tier4_22s_native_route_state_smoke.py --mode run-hardware --output-dir tier4_22s_job_output
```

Key difference from Tier 4.22r:

```text
4.22r: host writes context, then chip retrieves context and computes feature=context*cue
4.22s: host writes context and route, then chip retrieves both and computes feature=context*route*cue
```

New protocol commands:

```text
CMD_WRITE_ROUTE = 14
CMD_READ_ROUTE = 15
CMD_SCHEDULE_ROUTED_CONTEXT_PENDING = 16
```

Prepared metrics: local/prepared criteria passed, context writes `9`, context reads `30`, route writes `9`, route reads `30`, route values `[-1, 1]`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`. Boundary: Tier 4.22s is still a tiny native state-primitive smoke. It is not full v2.1 memory/routing, not full CRA task learning, and not speedup evidence.

Returned Tier 4.22s pass: the EBRAINS job built, loaded, ran, and produced the
full 30-row native route-state micro-task on board `10.11.237.89` / core
`(0,0,4)`. Raw status was `fail` because of a runner criterion bug, not a
hardware/runtime bug: final `CMD_READ_ROUTE` does not contain `route_writes`.
The ingested correction verifies route writes from the acknowledged
`CMD_WRITE_ROUTE` row counters (`9`), final route reads (`31`), all raw deltas
`0`, tail accuracy `1.0`, and final readout state `32768/0`.

## Tier 4.22t Native Keyed Route-State Gate

Tier 4.22t passed as the next custom-runtime gate after the Tier 4.22s native
route-state hardware pass. It keeps the same tiny 30-event task shape, but
replaces the single global route scalar with bounded keyed route slots.

```text
Tier 4.22t - Tiny Native Keyed Route-State Custom-Runtime Smoke
runner_revision = tier4_22t_native_keyed_route_state_smoke_20260501_0001
upload folder   = ebrains_jobs/cra_422ac
local output    = controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_local/
prepared output = controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_prepared/
```

Upload folder:

```text
<repo>/ebrains_jobs/cra_422ac
```

JobManager command:

```text
cra_422ac/experiments/tier4_22t_native_keyed_route_state_smoke.py --mode run-hardware --output-dir tier4_22t_job_output
```

Key difference from Tier 4.22s:

```text
4.22s: chip retrieves keyed context plus one global route scalar
4.22t: chip retrieves keyed context plus route[key], then computes feature=context[key]*route[key]*cue
```

New protocol commands:

```text
CMD_WRITE_ROUTE_SLOT = 17
CMD_READ_ROUTE_SLOT = 18
CMD_SCHEDULE_KEYED_ROUTE_CONTEXT_PENDING = 19
```

Prepared metrics: local/prepared criteria passed, context writes `9`, context
reads `30`, route-slot writes `15`, route-slot reads `30`, max route slots `3`,
route values `[-1, 1]`, tail accuracy `1.0`, final
`readout_weight_raw=32768`, final `readout_bias_raw=0`. Boundary: Tier 4.22t
is still a tiny keyed route-state primitive smoke. It is not full v2.1
memory/routing, not full CRA task learning, and not speedup evidence.

Returned Tier 4.22t pass: the EBRAINS job built, loaded, ran, and produced the
full 30-row native keyed route-state micro-task on board `10.11.235.25` / core
`(0,0,4)`. Raw status was `pass`. The returned data verify route-slot writes
`15`, active route slots `3`, route-slot hits `33`, route-slot misses `0`, all
raw deltas `0`, tail accuracy `1.0`, and final readout state `32768/0`.

### Tier 4.22u Native Memory-Route State Job

Prepared from `controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_prepared/`.

Upload folder:

```text
<repo>/ebrains_jobs/cra_422ad
```

JobManager command:

```text
cra_422ad/experiments/tier4_22u_native_memory_route_state_smoke.py --mode run-hardware --output-dir tier4_22u_job_output
```

Purpose: test the next tiny native custom-runtime primitive after 4.22t. The chip owns keyed context, keyed route, and keyed memory/working-state slots, then computes `feature=context[key]*route[key]*memory[key]*cue` from `key+cue+delay` before delayed-credit scheduling. Local/prepared metrics: 30 rows, context writes/reads `9/30`, route-slot writes/reads `15/30`, memory-slot writes/reads `15/30`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`. Prepared source package only until returned EBRAINS artifacts pass.

Returned Tier 4.22u result: **hardware pass**. Board `10.11.235.89`, selected core `(0,0,4)`, `.aplx` build/load pass, all `30` rows succeeded, route-slot writes/hits/misses `15/33/0`, memory-slot writes/hits/misses `15/33/0`, active route/memory slots `3/3`, all raw deltas `0`, observed accuracy `0.9666666667`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`.

Ingested artifacts:

```text
controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_hardware_pass_ingested/
```

### Tier 4.22v Native Memory-Route Reentry/Composition Job

Prepared from `controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_prepared/`.

Upload folder:

```text
<repo>/ebrains_jobs/cra_422ae
```

JobManager command:

```text
cra_422ae/experiments/tier4_22v_native_memory_route_reentry_composition_smoke.py --mode run-hardware --output-dir tier4_22v_job_output
```

Purpose: stress the Tier 4.22u native memory-route primitive with four keyed slots, longer interleaving, independent context/route/memory updates, and reentry recalls. Local/prepared metrics: 48 rows, context writes/reads `18/48`, route-slot writes/reads `21/48`, memory-slot writes/reads `21/48`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`. Prepared source package only until returned EBRAINS artifacts pass.

Returned Tier 4.22v result: **hardware pass**. Board `10.11.240.153`, selected core `(0,0,4)`, `.aplx` build/load pass, all `48` rows succeeded, route-slot writes/hits/misses `21/52/0`, memory-slot writes/hits/misses `21/52/0`, active route/memory slots `4/4`, all raw deltas `0`, observed accuracy `0.9375`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`.

Ingested artifacts:

```text
controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/
```


### Tier 4.22w Native Decoupled Memory-Route Composition Job

Prepared from `controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared_profiled/`.

Upload folder:

```text
<repo>/ebrains_jobs/cra_422ag
```

JobManager command:

```text
cra_422ag/experiments/tier4_22w_native_decoupled_memory_route_composition_smoke.py --mode run-hardware --output-dir tier4_22w_job_output
```

Purpose: test the next tiny native custom-runtime primitive after 4.22v. The chip already owns keyed context, keyed route, and keyed memory/working-state slots; this job adds independent-key composition by scheduling with `CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING`. The host sends `context_key`, `route_key`, `memory_key`, `cue`, and `delay`; the chip retrieves each state type by its own key and computes `feature=context[context_key]*route[route_key]*memory[memory_key]*cue` before delayed-credit scheduling.

Local/prepared metrics: 48 rows, context writes/reads `18/48`, route-slot writes/reads `15/48`, memory-slot writes/reads `18/48`, max context/route/memory slots `4/4/4`, feature source `chip_decoupled_context_route_memory_lookup_feature_transform`, accuracy `0.9583333333`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`.

Returned Tier 4.22w result: **hardware pass**. Board `10.11.236.9`, selected core `(0,0,4)`, `.aplx` build/load pass, `90/90` criteria passed, all `48` schedule/mature pairs completed, all feature/context/route/memory/prediction/weight/bias raw deltas `0`, observed accuracy `0.958333`, tail accuracy `1.0`, context writes/reads `18/48`, route-slot writes/reads `15/48`, memory-slot writes/reads `18/48`, active context/route/memory slots `4/4/4`, route/memory misses `0/0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`.

Ingested artifacts:

```text
controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/
```

Claim boundary: this returned hardware pass proves only a tiny native independent-key memory-route composition primitive on real SpiNNaker through the custom runtime. It is not full native v2.1 memory/routing, full CRA task learning, speedup evidence, multi-core scaling, or final on-chip autonomy.

Failure/repair ledger: first EBRAINS attempt `cra_422af` failed before target acquisition/app load/task execution. Exact linker error: `RO_DATA will not fit in region ITCM`; `region ITCM overflowed by 16 bytes`. Classification: noncanonical build-size/resource-budget failure, not a CRA mechanism failure. Repair: deduplicate the same-key/decoupled memory-route C schedule path, build hardware images with `-Os`, add `RUNTIME_PROFILE=decoupled_memory_route`, exclude unused neuron/synapse/router command handlers from this tiny primitive image, and regenerate as `cra_422ag`.

## Continuous Runtime Build Considerations (Tier 4.23)

Tier 4.23 introduces a timer-driven autonomous event loop that executes a
compact uploaded schedule without per-event host SDP. Before implementing,
record the following build/load constraints:

1. **Timer loop must not break existing command-driven profiles.**  
   The continuous timer callback should coexist with the existing SDP command
   dispatch path. When continuous mode is not active, the timer tick must
   still service dopamine decay, eligibility trace decay, and any other
   existing periodic work without altering behavior for Tier 4.22x and below.

2. **`-DCRA_RUNTIME_PROFILE_` must gate continuous code.**  
   The custom runtime already uses `RUNTIME_PROFILE=decoupled_memory_route` to
   exclude unused command handlers and avoid ITCM overflow. The continuous
   loop, schedule buffer, and related timer state must be wrapped by a similar
   profile gate (e.g. `-DCRA_RUNTIME_PROFILE_CONTINUOUS`) so that images
   which do not need continuous mode do not pay the ITCM/DTCM cost.

3. **Host tests must cover schedule upload and autonomous execution.**  
   Before any EBRAINS upload, local host tests must verify:
   - `WRITE_SCHEDULE_ENTRY` packs and unpacks correctly.
   - A synthetic schedule of 1–48 entries uploads without corruption.
   - The timer loop advances `g_timestep` and reaches the final entry.
   - Pending horizons are created and matured in oldest-first order without
     host intervention.
   - Readback after autonomous execution matches the reference parity
     tolerance (raw deltas abs <= 1).

4. **Resource budget must be predeclared.**  
   Record ITCM/DTCM size before and after adding the continuous loop.
   Document SDRAM used by the schedule buffer. State the max schedule length
   supported by the DTCM budget so that future hardware runs do not overflow
   silently.

5. **Pause/resume must not lose state.**  
   If `CMD_PAUSE` is implemented, the timer loop must stop at a well-defined
   boundary (end of current tick), leave pending horizons intact, and resume
   from the same `g_timestep` without double-scheduling or skipping entries.

> **Status:** These are pre-implementation notes for Tier 4.23b. No continuous
> runtime code has been written yet. The current operative guide remains the
> Tier 4.22x command-driven path above.
