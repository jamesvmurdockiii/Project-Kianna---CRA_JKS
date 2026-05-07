# EBRAINS Job Upload Folders

This directory contains clean, source-only job folders that are safe to upload to EBRAINS/JobManager.

Canonical operating instructions and the mistake/repair ledger live in
[`docs/SPINNAKER_EBRAINS_RUNBOOK.md`](../docs/SPINNAKER_EBRAINS_RUNBOOK.md).
Update that runbook whenever an EBRAINS run teaches us a new platform rule.

Rules:

- Upload the specific job folder, not the full repo.
- The JobManager command should include the uploaded folder name, e.g. `cra_422r/experiments/...`.
- Do not upload `controlled_test_output/`; it is local evidence storage and can be GBs large.
- Do not upload compiled host binaries, caches, or downloaded reports.
- Do not commit or upload symlinked `cra_*` folders; upload packages must be real, self-contained source directories.
- Returned EBRAINS files should be downloaded and then ingested/documented into `controlled_test_output/` by a tier-specific ingest step.

Public repository hygiene rules live in
[`docs/PUBLIC_REPO_HYGIENE.md`](../docs/PUBLIC_REPO_HYGIENE.md).

## Current Jobs

### `cra_432a_rep`

Status: **HARDWARE PASS / INGESTED** for Tier 4.32a-hw-replicated
single-chip replicated-shard MCPL-first scale stress.

Purpose: run the predeclared replicated 8/12/16-core stress points after the
Tier 4.32a-r1 MCPL repair and the Tier 4.32a-hw single-shard hardware pass.
The job builds shard-specific context/route/memory/learning images and loads
independent shard groups onto one chip.

Upload folder:

```text
ebrains_jobs/cra_432a_rep
```

Exact JobManager command:

```text
cra_432a_rep/experiments/tier4_32a_hw_replicated_shard_stress.py --mode run-hardware --output-dir tier4_32a_replicated_job_output
```

Prepared artifact:

```text
controlled_test_output/tier4_32a_hw_replicated_20260507_prepared/
```

Ingested artifact:

```text
controlled_test_output/tier4_32a_hw_replicated_20260507_hardware_pass_ingested/
```

Result: board `10.11.215.121`, raw remote status `pass`, ingest status `pass`,
`185/185` raw hardware criteria, `9/9` ingest criteria, `80` returned artifacts,
point08 `2` shards / `192` total events / `288` lookup replies per shard,
point12 `3` shards / `384` total events / `384` lookup replies per shard,
point16 `4` shards / `512` total events / `384` lookup replies per shard, zero
stale replies, zero duplicate replies, zero timeouts, and zero synthetic
fallback.

Boundary: single-chip replicated-shard stress only. It is not static reef
partitioning, not multi-chip evidence, not speedup evidence, and not a
native-scale baseline freeze.

### `cra_432a_hw`

Status: **HARDWARE PASS / INGESTED** for Tier 4.32a-hw single-shard
MCPL-first EBRAINS scale stress.

Purpose: run only the two Tier 4.32a single-shard points authorized after the
Tier 4.32a-r1 MCPL repair: `point_04c_reference` and
`point_05c_lifecycle`. The returned EBRAINS run passed and was ingested at
`controlled_test_output/tier4_32a_hw_20260507_hardware_pass_ingested/`.

Previous upload folder:

```text
ebrains_jobs/cra_432a_hw
```

Previous JobManager command:

```text
cra_432a_hw/experiments/tier4_32a_hw_single_shard_scale_stress.py --mode run-hardware --output-dir tier4_32a_hw_job_output
```

Prepared artifact:

```text
controlled_test_output/tier4_32a_hw_20260506_prepared/
```

Result: board `10.11.215.185`, raw remote status `pass`, ingest status `pass`,
`31/31` raw hardware criteria, `8/8` ingest criteria, `63` returned artifacts,
point04 `48` events / `144` lookup replies, point05 `96` events / `288` lookup
replies, zero stale replies, zero duplicate replies, zero timeouts, and zero
synthetic fallback.

Boundary: single-shard single-chip hardware stress only. It is not
replicated-shard stress, not multi-chip evidence, not speedup evidence, not
static reef partitioning, and not a native-scale baseline freeze.

Next: Tier 4.32d two-chip split-role single-shard MCPL lookup hardware smoke is
prepared and ready for EBRAINS. Tier 4.32d-r0 blocked the first upload, then
Tier 4.32d-r1 passed local route repair/QA with explicit learning-core request
link routes, state-core local request delivery, state-core value/meta reply link
routes, and clean MCPL regressions. The prepared output is
`controlled_test_output/tier4_32d_20260507_prepared/`; upload folder is
`ebrains_jobs/cra_432d`; JobManager command is
`cra_432d/experiments/tier4_32d_interchip_mcpl_smoke.py --mode run-hardware --output-dir tier4_32d_job_output`.
Learning scale, benchmarks, speedup claims, native-scale baseline-freeze claims,
and true two-partition cross-chip learning remain blocked.

### Tier 4.31e

Status: **LOCAL DECISION PASS**. No EBRAINS upload folder is needed for this
gate. Tier 4.31e is documented at
`controlled_test_output/tier4_31e_20260506_native_replay_eligibility_decision_closeout/`
and passed `15/15`.

Decision: native replay buffers, sleep-like replay, and native macro eligibility
are deferred until measured blockers exist; Tier 4.31f is deferred; Tier 4.32
mapping/resource modeling is authorized next; no baseline freeze.

Boundary: local decision evidence only. It is not hardware evidence and should
not produce or upload an EBRAINS job folder.

### Tier 4.32 native-runtime mapping/resource model

Status: **LOCAL RESOURCE-MODEL PASS**. No EBRAINS upload folder is needed for
this gate. Tier 4.32 is documented at
`controlled_test_output/tier4_32_20260506_mapping_resource_model/` and passed
`23/23`.

Decision: MCPL is the scale data plane; SDP remains host control/readback or
fallback only. Current returned profile builds have positive ITCM/DTCM
headroom. Tier 4.32a single-chip multi-core scale stress is the next active
gate. No native-scale baseline freeze is authorized yet.

Boundary: local mapping/resource evidence only. It is not a new SpiNNaker run,
not speedup evidence, not multi-chip evidence, and should not produce or upload
an EBRAINS job folder.

### `cra_431d_r1`

Status: **HARDWARE PASS / INGESTED** for Tier 4.31d native temporal-substrate
hardware smoke. The successful return is preserved at
`controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested/`. The
first incomplete EBRAINS return is preserved separately at
`controlled_test_output/tier4_31d_hw_20260506_incomplete_return/`.

Purpose: Verify on one real SpiNNaker board that the C-owned seven-EMA temporal
state from Tier 4.31c builds, loads, updates, and reads back through commands
`39-42`. The probe checks compact temporal payload length `48`, exact
fixed-point reference counters/checksums, and enabled versus zero/frozen/reset
controls.

Upload folder:

```text
ebrains_jobs/cra_431d_r1
```

JobManager command:

```text
cra_431d_r1/experiments/tier4_31d_native_temporal_hardware_smoke.py --mode run-hardware --output-dir tier4_31d_hw_job_output
```

Runner revision:

```text
tier4_31d_native_temporal_hardware_smoke_20260506_0003
```

Returned pass summary:

```text
board = 10.11.216.121
target_method = pyNN.spiNNaker_probe
dest = (0,0,4)
remote hardware criteria = 59/59
ingest criteria = 5/5
returned artifacts preserved = 21
temporal_payload_len = 48
scenarios = enabled, zero_state, frozen_state, reset_each_update all pass
```

Revision `0003` added streamed build logs, build timeout, milestone
breadcrumbs, structured exception finalization, and incomplete-return artifact
preservation. If this tier is rerun, download all returned files;
`tier4_31d_hw_milestone.json` and `tier4_31d_hw_results.json` are the first
files to inspect.

Boundary: one-board hardware execution/readback smoke only. It is not speedup,
benchmark superiority, multi-chip scaling, nonlinear recurrence, replay/sleep,
or full v2.2 hardware-transfer evidence.

### `cra_430g`

Status: **HARDWARE PASS / INGESTED** for Tier 4.30g lifecycle
task-benefit/resource bridge.

Purpose: Verify on real SpiNNaker that native lifecycle state can be ferried
into the bounded task-bearing context/route/memory/learning path. Enabled
lifecycle must open the bridge gate; fixed-pool, random replay, active-mask
shuffle, no-trophic, and no-dopamine/no-plasticity controls must close it.

Upload folder:

```text
ebrains_jobs/cra_430g
```

JobManager command used:

```text
cra_430g/experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py --mode run-hardware --output-dir tier4_30g_hw_job_output
```

Prepared artifact:

```text
controlled_test_output/tier4_30g_hw_20260506_prepared/
```

Ingested artifact:

```text
controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/
```

Returned metrics:

```text
Board: 10.11.242.97
Raw remote status: pass
Ingest status: pass
Hardware criteria: 285/285
Ingest criteria: 5/5
Returned artifacts preserved: 36
Enabled lifecycle gate: open
Five predeclared controls: closed
```

Boundary: host-ferried lifecycle task-benefit/resource bridge only. It is not
autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip scaling, not
v2.2 temporal migration, and not full organism autonomy. This pass contributes
to `CRA_LIFECYCLE_NATIVE_BASELINE_v0.4`.


### `cra_430f`

Status: **HARDWARE PASS / INGESTED** for Tier 4.30f lifecycle sham-control
hardware subset.

Purpose: Verify that the lifecycle sham controls alter lifecycle behavior on
real SpiNNaker hardware rather than merely toggling a readback flag. The job
builds and loads the same five runtime profiles as Tier 4.30e, then runs the
canonical 32-event lifecycle trace through enabled, fixed-pool, random-event
replay, active-mask shuffle, no-trophic-pressure, and
no-dopamine/no-plasticity modes.

Upload folder:

```text
ebrains_jobs/cra_430f
```

JobManager command:

```text
cra_430f/experiments/tier4_30f_lifecycle_sham_hardware_subset.py --mode run-hardware --output-dir tier4_30f_hw_job_output
```

Prepared artifact:

```text
controlled_test_output/tier4_30f_hw_20260505_prepared/
```

Ingested artifact:

```text
controlled_test_output/tier4_30f_hw_20260505_hardware_pass_ingested/
```

Returned metrics:

```text
Board: 10.11.227.9
Raw remote status: pass
Ingest status: pass
Hardware criteria: 185/185
Ingest criteria: 5/5
Returned artifacts preserved: 35
```

Boundary: this is a compact lifecycle sham-control hardware subset, not full
Tier 6.3 hardware, not lifecycle task-benefit evidence, not speedup evidence,
not multi-chip scaling, and not a baseline freeze. Tier 4.30g-hw now passes and is ingested; lifecycle-native baseline v0.4 is frozen with a host-ferried bridge boundary. Tier 4.31a local temporal-substrate readiness also passed, but no temporal EBRAINS package is pending yet.

### `cra_430e`

Status: **HARDWARE PASS / INGESTED** for Tier 4.30e multi-core lifecycle
hardware smoke.

Purpose: Verify the native lifecycle/core split on real SpiNNaker with five
runtime profiles: context, route, memory, learning, and lifecycle. The job
builds and loads all five profile binaries, verifies compact profile readback,
checks that non-lifecycle profiles reject lifecycle reads, probes duplicate and
stale lifecycle event rejection, and runs the canonical 32-event plus boundary
64-event lifecycle schedules against the local Tier 4.30 reference.

Upload folder:

```text
ebrains_jobs/cra_430e
```

JobManager command that produced the returned artifacts:

```text
cra_430e/experiments/tier4_30e_multicore_lifecycle_hardware_smoke.py --mode run-hardware --output-dir tier4_30e_hw_job_output
```

Prepared and ingested artifacts:

```text
controlled_test_output/tier4_30e_hw_20260505_prepared/
controlled_test_output/tier4_30e_hw_20260505_hardware_pass_ingested/
```

Returned metrics:
- Board: `10.11.226.145`
- Raw remote status: `pass`
- Ingest status: `pass`
- Hardware criteria: `75/75`
- Ingest criteria: `5/5`
- Returned artifacts preserved: `31`
- Scenario parity: `canonical_32` and `boundary_64` passed
- Duplicate/stale lifecycle event rejection: passed

Boundary: this is hardware smoke evidence for the five-profile lifecycle
surface only. It is not lifecycle task-benefit evidence, not lifecycle
sham-control evidence, not multi-chip scaling, not speedup evidence, not v2.2
temporal migration, and not a baseline freeze.

### `cra_429p`

Status: **HARDWARE PASS / INGESTED** for Tier 4.29e native replay/consolidation bridge.

Purpose: Verify that host-scheduled replay/consolidation events run through the
native four-core state pipeline using context, route, memory, and learning cores.
This is host-scheduled replay only; it is not native on-chip replay buffers or
biological sleep.

Upload folder:

```text
ebrains_jobs/cra_429p
```

JobManager command used:

```text
cra_429p/experiments/tier4_29e_native_replay_consolidation_bridge.py --mode run-hardware --seeds 42,43,44
```

Package metadata:
- Runner revision: `tier4_29e_native_replay_consolidation_20260505_0003`
- Based on: `cra_429j` binaries
- C runtime changes: none for 4.29e
- Controls: `no_replay`, `correct_replay`, `wrong_key_replay`, `random_event_replay`

Canonical artifact:

```text
controlled_test_output/tier4_29e_20260505_pass_ingested/
```

Result:
- Seed 42: board `10.11.226.129`, `38/38` criteria.
- Seed 43: board `10.11.226.1`, `38/38` criteria.
- Seed 44: board `10.11.226.65`, `38/38` criteria.

Known noncanonical failure chain before `cra_429p`:
- `cra_429k`: missing 4.29e runner from package.
- `cra_429l`: runner called nonexistent `base.probe_board_hostname()`.
- `cra_429m`: schedule-entry fixed-point double conversion.
- `cra_429n`: context/route/memory state-write fixed-point double conversion.
- `cra_429o`: real hardware diagnostic fail due to schedule/reference gate, not promoted.

Next action: Tier 4.29f compact native mechanism regression.


### `cra_429d`

Status: **HISTORICAL / SUPERSEDED** (Tier 4.29b pass has been ingested; retained for audit history).

Purpose: Tier 4.29b native routing/composition gate. Tests whether the native
route_core can handle keyed routing with non-neutral values (+1.0, -1.0) and
that the chip correctly computes `feature = context[key] * route[key] * cue`.
Four-core MCPL distributed scaffold with explicit wrong-route and route overwrite
controls.

Upload folder:

```text
ebrains_jobs/cra_429d
```

JobManager command:

```text
cra_429d/experiments/tier4_29b_native_routing_composition_gate.py --mode run-hardware --seeds 42,43,44
```

Local/prepared metrics: 32 events, 2 route keys (101=+1.0, 102=-1.0),
8 context slots, 8 wrong-context events, 8 wrong-route events,
2 context overwrite events, 6 route overwrite events.
Host ref weight=35329, bias=655, tail accuracy=1.0.
All 18/18 local criteria pass.

Boundary: this job tests native keyed routing/composition on real SpiNNaker.
It is NOT speedup evidence, NOT multi-chip scaling, NOT a general multi-core
framework, NOT full native v2.1 autonomy, and NOT true continuous generation.

### `cra_429c`

Status: **FAILED** on EBRAINS (48/52 criteria per seed, three seeds).

Failure stage: hardware execution / readback schema mismatch.

Symptoms: All three seeds failed the same 4 route-specific criteria:
- wrong-route events fail cleanly (route misses): expected 6, got 0
- route overwrite uses new value (route writes): expected 3, got 0
- route lookups maintain correctness (route hits): expected 24, got 0
- route_core active_slots matches expected: expected 2, got 0

Root cause: `host_interface.c` `host_if_pack_state_summary()` unconditionally
emitted context-slot counters (`slot_writes`, `slot_hits`, `slot_misses`,
`active_slots`) into the readback payload for ALL profiles. The route_core
profile correctly handled `CMD_WRITE_ROUTE_SLOT` and `CMD_READ_ROUTE_SLOT`,
updated its own route-slot counters (`route_slot_writes`, `route_slot_hits`,
etc.), but these were never copied into the payload. The host always read zeros.

Classification: **C runtime readbug**, NOT a CRA mechanism failure. The route
slot table worked correctly on-chip; only the readback path was wrong.

Repair: Added profile-specific logic in `host_if_pack_state_summary()` so that
`ROUTE_CORE` emits route-slot counters and `MEMORY_CORE` emits memory-slot
counters. Context/learning/decoupled profiles keep the original context-slot
behavior. Rebuilt all four profiles, verified local mode passes 18/18,
regenerated as `cra_429d` per Rule 10.

### `cra_429b`

Status: **HARDWARE PASS, INGESTED** (47/47 criteria per seed, three seeds,
three boards). Evidence archived to
`controlled_test_output/tier4_29a_20260503_hardware_pass_ingested/`.

Purpose: Tier 4.29a native keyed-memory overcapacity gate. Tests whether the
native context_core can handle multi-slot keyed lookup with wrong-key,
overwrite, and slot-shuffle controls on real SpiNNaker. Four-core MCPL
distributed scaffold. MAX_SCHEDULE_ENTRIES=512.

Upload folder:

```text
ebrains_jobs/cra_429b
```

JobManager command:

```text
cra_429b/experiments/tier4_29a_native_keyed_memory_overcapacity_gate.py --mode run-hardware --seeds 42,43,44
```

Returned metrics:
- Seed 42: board 10.11.193.145, 47/47 criteria, weight=32768, bias=0,
  pending=32/32, lookups=96/96, stale=0, timeouts=0
- Seed 43: board 10.11.194.129, 47/47 criteria, weight=32768, bias=0,
  pending=32/32, lookups=96/96, stale=0, timeouts=0
- Seed 44: board 10.11.193.81, 47/47 criteria, weight=32768, bias=0,
  pending=32/32, lookups=96/96, stale=0, timeouts=0
- Context hits=26, misses=6, active_slots=8, slot_writes=9 on all seeds.
- Zero variance across seeds. Exact parity with local reference.

Boundary: this job proves native keyed-memory lookup with wrong-key, overwrite,
and slot-shuffle controls works on real SpiNNaker across multiple seeds and
boards. It is NOT speedup evidence, NOT multi-chip scaling, NOT a general
multi-core framework, NOT full native v2.1 autonomy, and NOT true continuous
generation (still schedule-driven; deferred to Tier 4.32).

### `cra_429a`

Status: **BLOCKED** on EBRAINS before task execution.

Failure stage: container environment / setup script.

Symptoms:
1. `setup.bash` emitted `/tmp/job*/setup.bash: line 4: jq: command not found`.
2. The container's zip extraction produced a 72KB archive, but the local
   verified `cra_429a` package zip is 213KB. This suggests either a stale
   cached upload or the web UI created an incomplete zip.
3. Python `FileNotFoundError`: the runner script could not be found after
   extraction, causing immediate process exit with code 2.

Classification: platform/infrastructure failure, NOT a CRA mechanism failure.

Repair: fresh package `cra_429b` generated per codebasecontract Rule 10.
User should upload `cra_429b` (not `cra_429a`) to EBRAINS.

### `cra_427b`

Status: **HARDWARE PASS, INGESTED** (38/38 criteria, board 10.11.194.65,
cores 4/5/6/7). Evidence archived to
`controlled_test_output/tier4_27a_20260502_pass_ingested/`.

Purpose: Tier 4.27a four-core runtime resource / timing characterization.
Reuses the 4.26 four-core distributed architecture but with an instrumented C
runtime (schema v2, 105-byte readback) that counts lookup requests/replies,
stale/duplicate replies, timeouts, per-core commands, schedule length, and
readback bytes. Captures wall time, load time, task time, and pause/readback
time for resource-envelope measurement.

Upload folder:

```text
ebrains_jobs/cra_427b
```

JobManager command:

```text
cra_427b/experiments/tier4_27a_four_core_distributed_smoke.py --mode run-hardware --seed 42
```

Local/prepared metrics: 48 rows, context/route/memory writes `4` each, lookup
requests/replies `144/144`, stale replies `0`, timeouts `0`, schema version `2`,
payload bytes `105`, expected accuracy `0.9583`, tail accuracy `1.0`, final
`readout_weight_raw=32768`, final `readout_bias_raw=0`.

Boundary: this job measures the four-core SDP scaffold timing envelope and
counter telemetry. It is NOT speedup evidence, NOT multi-chip scaling, NOT a
general multi-core framework, and NOT full native v2.1 autonomy. SDP remains
transitional.

### `cra_427a`

Status: **FAILED** on EBRAINS (board 10.11.194.129). Hardware execution was
correct (weight=32768, bias=0, pending=48/48, schema=2, payload=105), but 7/38
criteria failed because `colony_controller.py` `parse_state_payload()` returned
keys `lookup_requests_sent`/`lookup_replies_received` while the runner criteria
checked `lookup_requests`/`lookup_replies`. Root cause: naming drift between C
struct fields, Python parser output, and runner validation. Not a runtime bug.

Repair: renamed parser keys to match runner criteria; bumped to `cra_427b` per
contract §9.1 rule 6; added Rule 9 to Section 9.1.2 (parser-key/criteria-key
name parity).

### `cra_426f`

Status: **HARDWARE PASS, INGESTED** (30/30 criteria, board 10.11.194.1,
cores 4/5/6/7). Evidence archived to
`controlled_test_output/tier4_26_20260502_pass_ingested/`.

Purpose: Tier 4.26 four-core context/route/memory/learning distributed smoke.
Splits the custom runtime across four SpiNNaker cores: core 4 (context_core)
holds context slot table and replies to context lookups; core 5 (route_core)
holds route slot table and replies to route lookups; core 6 (memory_core) holds
memory slot table and replies to memory lookups; core 7 (learning_core) holds
the event schedule, sends parallel lookup requests, composes features from
replies, manages the pending horizon, and updates readout.

Upload folder:

```text
ebrains_jobs/cra_426f
```

JobManager command:

```text
cra_426f/experiments/tier4_26_four_core_distributed_smoke.py --mode run-hardware --seed 42
```

Local/prepared metrics: 48 rows, context writes `4`, route writes `4`, memory
writes `4`, lookup requests/replies `144/144`, max pending depth `3`, expected
accuracy `0.9583`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final
`readout_bias_raw=0`.

Boundary: this job tests whether four independent cores can hold distributed
state and cooperate to reproduce the monolithic delayed-credit result within
tolerance. It is NOT speedup evidence, NOT multi-chip scaling, NOT a general
multi-core framework, and NOT full native v2.1 autonomy.

Failure/repair ledger:
- `cra_426a` failed before task execution: argparse used positional `mode`,
  but EBRAINS passes `--mode run-hardware`. Repair: add `--mode` flag.
- `cra_426b` build/load/pre-flight passed, but ZERO JSON artifacts written.
  Root cause unknown; runner `mode_run` placed `write_json` outside `try/finally`.
  Repair: wrap hardware execution in `try/except/finally`, capture exceptions.
- `cra_426c` also produced zero JSON artifacts. Diagnosis revealed:
  1. Missing parser args (`--target-probe-population-size`, `--target-probe-run-ms`,
     `--target-probe-timestep-ms`) caused target acquisition to fail via
     `AttributeError`, which was caught but meant no hardware target was ever
     acquired.
  2. C learning core stored lookup requests in a table but **never sent them**
     via SDP, so state cores would never reply, pending horizons would never be
     created, and the test could never pass even if the runner reached hardware.
  3. Context/route/memory cores did not capture their chip address, so lookup
     replies would use address 0.
  4. No top-level `BaseException` handler meant any unhandled crash produced
     no crash report.
  5. No intermediate artifact writes inside the `try` block meant partial
     progress was lost if the process was killed.
  Repair: add missing parser args; add `_send_lookup_request()` in learning core
  tick; add `cra_state_capture_chip_addr()` for context/route/memory cores;
  add `sark_chip_id()` stub; add top-level `BaseException` handler with crash
  report; add intermediate `write_json` calls after each major step; bump
  revision to `20260502_0003`; regenerate as `cra_426d` per codebasecontract §9.1.
- `cra_426d` produced a crash report (progress vs zero artifacts), but still
  failed. Diagnosis revealed:
  1. Tier 4.26 parser omitted `--dest-cpu` and `--auto-dest-cpu`. The base module
     `tier4_22i_custom_runtime_roundtrip.py` requires these for target acquisition.
     Crash: `AttributeError: 'Namespace' object has no attribute 'dest_cpu'`.
  2. `state_manager.h` declared `cra_state_capture_chip_addr()` only under
     `#ifdef CRA_RUNTIME_PROFILE_STATE_CORE`, but `host_interface.c` calls it for
     all state profiles. Build warning: implicit declaration for cores 4/5/6.
  Repair: add `--dest-cpu` (default=1) and `--auto-dest-cpu`/`--no-auto-dest-cpu`
  to the 4.26 parser; update `state_manager.h` guard to declare the function for
  all state-core profiles; bump runner revision to `20260502_0004`; regenerate
  as `cra_426e` per codebasecontract §9.1.
- `cra_426e` reached full hardware execution and produced complete artifacts.
  Learning core returned exact reference values (weight=32768, bias=0,
  48 decisions/rewards/pending). However, 3/30 criteria failed:
  `context_core run_continuous succeeded`, `route_core run_continuous
  succeeded`, `memory_core run_continuous succeeded`. Root cause:
  `host_interface.c` dispatch included `CMD_RUN_CONTINUOUS` and `CMD_PAUSE`
  only for `LEARNING_CORE` and monolithic `DECOUPLED_MEMORY_ROUTE` profiles.
  The new context/route/memory server-core profiles fell through to NAK for
  these commands. The host runner requires success on all four cores.
  Repair: add `CMD_RUN_CONTINUOUS` and `CMD_PAUSE` to the state-server core
  dispatch block; update profile tests to expect ack instead of NAK; bump
  runner revision to `20260502_0005`; regenerate as `cra_426f` per
  codebasecontract §9.1.
- `cra_426f` **PASSED** on EBRAINS hardware (board 10.11.194.1). All 30/30
  criteria passed. Learning core returned exact monolithic reference values:
  weight=32768, bias=0, 48 decisions, 48 rewards, 48 pending created/matured,
  active_pending=0. Context core served 48 lookup hits. Evidence archived to
  `controlled_test_output/tier4_26_20260502_pass_ingested/`.

### `cra_425i`

Status: **returned hardware pass ingested** at
`controlled_test_output/tier4_25c_20260502_aggregate/`.

Purpose: Tier 4.25C two-core state/learning split repeatability. Reuses the
4.25B runner with `--seed` support. Splits the custom runtime across two
SpiNNaker cores: core 4 holds context/route/memory state and schedules pending
via inter-core SDP; core 5 matures pending and updates readout.

Upload folder:

```text
ebrains_jobs/cra_425i
```

JobManager command:

```text
cra_425i/experiments/tier4_25b_two_core_split_smoke.py --mode run-hardware --seed 42
cra_425i/experiments/tier4_25b_two_core_split_smoke.py --mode run-hardware --seed 43
cra_425i/experiments/tier4_25b_two_core_split_smoke.py --mode run-hardware --seed 44
```

Returned metrics: all three seeds passed `23/23` criteria.
- Seed 42: board `10.11.193.1`, weight=32767, bias=-1
- Seed 43: board `10.11.201.17`, weight=32767, bias=-1
- Seed 44: board `10.11.196.1`, weight=32767, bias=-1
- Max weight delta across seeds: 0. Max bias delta across seeds: 0.

Boundary: this job proves the two-core split repeats across seeds on real
SpiNNaker. It is not speedup evidence, not multi-chip scaling, not a general
multi-core framework, and not full native v2.1 autonomy.

### `cra_425g`

Status: **returned hardware pass ingested** at
`controlled_test_output/tier4_25b_20260502_hardware_pass_ingested/`.

Purpose: Tier 4.25B two-core state/learning split smoke. This job runs after
Tier 4.23c single-core continuous pass and Tier 4.24 resource characterization.
It splits the custom runtime across two SpiNNaker cores: core 4 holds
context/route/memory state and schedules pending via inter-core SDP; core 5
matures pending and updates readout. The learning core must compute prediction
dynamically at maturation time using its own weight.

Upload folder:

```text
ebrains_jobs/cra_425g
```

JobManager command:

```text
cra_425g/experiments/tier4_25b_two_core_split_smoke.py --mode run-hardware
```

Returned metrics: board `10.11.205.161`, state core `(0,0,4)` app_id=1,
learning core `(0,0,5)` app_id=2, `23/23` criteria passed,
state core decisions=48/weight=0/bias=0,
learning core pending_created=48/pending_matured=48/weight=32767/bias=-1.

Boundary: this job proves a two-core split can reproduce the monolithic
single-core result within tolerance. It is not speedup evidence, not multi-chip
scaling, not a general multi-core framework, and not full native v2.1 autonomy.

### `cra_422z`

Status: **returned hardware pass ingested** at
`controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_hardware_pass_ingested/`.
Local/prepared source evidence is preserved at
`controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_local/`
and
`controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_prepared/`.

Purpose: Tier 4.22q tiny integrated v2 bridge custom-runtime smoke. This job
runs after the Tier 4.22p A-B-A reentry hardware pass and adds one deliberately
small host-side v2-style bridge before the custom runtime: keyed context slots
plus route state transform visible cues into signed scalar features. The custom
C runtime still owns pending horizon state, pre-update predictions, delayed
oldest-first maturation, and fixed-point readout updates.

Upload folder:

```text
ebrains_jobs/cra_422z
```

JobManager command:

```text
cra_422z/experiments/tier4_22q_integrated_v2_bridge_smoke.py --mode run-hardware --output-dir tier4_22q_job_output
```

Returned metrics: board `10.11.236.65`, selected core `(0,0,4)`, `47/47`
remote criteria plus ingest criterion passed, sequence length `30`, pending gap
`2`, max pending depth `3`, accuracy `0.9333333333`, tail accuracy `1.0`,
context updates `9`, route updates `9`, max keyed slots `3`, feature source
`host_keyed_context_route_transform`, prediction/weight/bias raw deltas all
`0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`, and
`pending_created=pending_matured=reward_events=decisions=30`.

Boundary: this job is a tiny integrated host-v2/custom-runtime bridge smoke,
not native/on-chip v2 memory/routing, full CRA task learning, speedup evidence,
multi-core scaling, or final autonomy.

### `cra_422y`

Status: **returned hardware pass ingested** at
`controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_hardware_pass_ingested/`.

Purpose: Tier 4.22p tiny A-B-A reentry custom-runtime micro-task. This job
runs after the Tier 4.22o noisy-switching hardware pass and expands from one
rule switch to a tiny A-B-A recurrence stream while preserving the same
pending/readout command surface.

Upload folder:

```text
ebrains_jobs/cra_422y
```

JobManager command:

```text
cra_422y/experiments/tier4_22p_reentry_micro_task.py --mode run-hardware --output-dir tier4_22p_job_output
```

Returned metrics: board `10.11.222.17`, selected core `(0,0,4)`, `44/44`
criteria passed, sequence length `30`, pending gap `2`, max pending depth `3`,
accuracy `0.8666666667`, tail accuracy `1.0`, accuracy gain `0.2666666667`,
prediction/weight/bias raw deltas all `0`, final `readout_weight_raw=30810`,
final `readout_bias_raw=-1`, and
`pending_created=pending_matured=reward_events=decisions=30`.

Boundary: this job is a tiny A-B-A reentry pending-queue micro-task, not full
CRA recurrence, v2.1 mechanism transfer, speedup evidence, multi-core scaling,
or final autonomy.

### `cra_422x`

Status: **returned hardware pass ingested** at
`controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/`.

Purpose: Tier 4.22o tiny noisy-switching custom-runtime micro-task. This job
runs after the Tier 4.22n delayed pending-queue hardware pass and expands from
a stable delayed-cue-like stream to a tiny rule-switching stream with one
label-noise event in each regime.

Upload folder:

```text
ebrains_jobs/cra_422x
```

JobManager command:

```text
cra_422x/experiments/tier4_22o_noisy_switching_micro_task.py --mode run-hardware --output-dir tier4_22o_job_output
```

Returned metrics: accuracy `0.7857142857`, tail accuracy `1.0`, max
pending depth `3`, prediction/weight/bias raw deltas all `0`, final
`readout_weight_raw=-48768`, final `readout_bias_raw=-1536`, and
`pending_created=pending_matured=reward_events=decisions=14`.

Boundary: this job is a tiny noisy-switching pending-queue micro-task, not full
CRA hard_noisy_switching, v2.1 mechanism transfer, speedup evidence,
multi-core scaling, or final autonomy.

History: the first Tier 4.22o EBRAINS package, `cra_422w`, is preserved as a
noncanonical failed diagnostic. It built, loaded, scheduled, and matured all
14 events, then diverged at the first signed regime-switch update because the
custom runtime's `FP_MUL` used a 32-bit intermediate. `cra_422x` is the
repaired package with `int64_t` fixed-point multiplication and regression
tests for that failure; the returned `cra_422x` board run passed.

### `cra_422v`

Status: **returned hardware pass ingested** at
`controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/`.

Purpose: Tier 4.22n tiny delayed-cue custom-runtime micro-task. This job runs
after the Tier 4.22m hardware task micro-loop pass and expands from immediate
one-event maturation to a rolling pending queue with `pending_gap_depth=2`.

Upload folder:

```text
ebrains_jobs/cra_422v
```

JobManager command:

```text
cra_422v/experiments/tier4_22n_delayed_cue_micro_task.py --mode run-hardware --output-dir tier4_22n_job_output
```

Expected reference metrics: accuracy `0.8333333333`, tail accuracy `1.0`, max
pending depth `3`, final `readout_weight_raw=30720`, final `readout_bias_raw=0`,
and `pending_created=pending_matured=reward_events=decisions=12`.

Returned result: board `10.11.205.1`, selected core `(0,0,4)`, `.aplx`
build/load pass, twelve delayed schedule/mature events pass, max observed
pending depth `3`, all prediction/weight/bias raw deltas `0`, observed
accuracy `0.8333333333`, observed tail accuracy `1.0`, final
`pending_created=pending_matured=reward_events=decisions=12`,
`active_pending=0`, `readout_weight_raw=30720`, and `readout_bias_raw=0`.

Boundary: this job is a tiny delayed-cue-like pending-queue micro-task, not full
CRA task learning, v2.1 mechanism transfer, speedup evidence, multi-core
scaling, or final autonomy. It was followed by the passed Tier 4.22o
`cra_422x` noisy-switching package above.

### `cra_422u`

Status: **passed after ingest** at
`controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_hardware_pass_ingested/`.

Purpose: Tier 4.22m minimal custom-runtime task micro-loop. This job runs after
the Tier 4.22l hardware parity pass and expands from arbitrary parity rows to a
12-event signed fixed-pattern task stream. It scores the runtime's pre-update
prediction sign, matures one pending horizon per event, and must match the
local s16.15 task reference.

Upload folder:

```text
ebrains_jobs/cra_422u
```

JobManager command:

```text
cra_422u/experiments/tier4_22m_custom_runtime_task_micro_loop.py --mode run-hardware --output-dir tier4_22m_job_output
```

Returned evidence: board `10.11.202.65`, free core `(0,0,4)`, `.aplx` build/load pass, twelve schedule/mature command pairs pass, all prediction/weight/bias raw deltas `0`, observed accuracy `0.9166666667`, tail accuracy `1.0`, final `readout_weight_raw=32256`, final `readout_bias_raw=0`, and `pending_created=pending_matured=reward_events=decisions=12`.

Boundary: this job is a minimal fixed-pattern custom-runtime task micro-loop,
not full CRA task learning, v2.1 mechanism transfer, speedup evidence,
multi-core scaling, or final on-chip autonomy.

### `cra_422t`

Status: **passed after ingest** at
`controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_hardware_pass_ingested/`.

Purpose: Tier 4.22l tiny custom-runtime learning parity. This job runs after
the Tier 4.22j minimal learning-smoke pass and compares a four-event
`CMD_SCHEDULE_PENDING`/`CMD_MATURE_PENDING` sequence against the local s16.15
fixed-point readout reference. It is intentionally tiny and signed: final
expected readout weight/bias are both `-4096` raw (`-0.125`).

Upload folder:

```text
ebrains_jobs/cra_422t
```

JobManager command:

```text
cra_422t/experiments/tier4_22l_custom_runtime_learning_parity.py --mode run-hardware --output-dir tier4_22l_job_output
```

Returned evidence: board `10.11.194.1`, free core `(0,0,4)`, `.aplx`
build/load pass, four schedule/mature command pairs pass, all prediction/weight
/bias raw deltas `0`, final `pending_created=4`, `pending_matured=4`,
`reward_events=4`, `active_pending=0`, `readout_weight_raw=-4096`, and
`readout_bias_raw=-4096`.

Boundary: this job proves only tiny on-chip fixed-point learning parity, not
full CRA task learning, v2.1 mechanism transfer, speedup evidence, multi-core
scaling, or final on-chip autonomy.

### `cra_422s`

Status: **passed after ingest correction** at
`controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/`.

Purpose: Tier 4.22j minimal custom-runtime closed-loop learning smoke. It
depends on the Tier 4.22i board
round-trip pass, then adds the smallest chip-owned learning heartbeat:
`CMD_SCHEDULE_PENDING(feature, delay)` followed by
`CMD_MATURE_PENDING(target, lr)`. A returned pass must show that one pending
horizon was created, matured on chip, and that `CMD_READ_STATE` exposes
updated pending/reward/readout counters.

The first returned EBRAINS run raw-failed because the runner used
`active_pending or -1`, so the correct value `active_pending=0` was treated as
missing. The ingested evidence reclassifies it as a pass and preserves the raw
manifest/report. The source package has been refreshed with the fixed evaluator
for any rerun.

Upload folder:

```text
ebrains_jobs/cra_422s
```

JobManager command:

```text
cra_422s/experiments/tier4_22j_minimal_custom_runtime_learning.py --mode run-hardware --output-dir tier4_22j_job_output
```

Boundary: this job tests one minimal delayed pending/readout update in the
custom runtime. It is not full CRA task learning, v2.1 mechanism transfer,
speedup evidence, multi-core scaling, or final on-chip autonomy.

### `cra_422r`

Status: **passed** at
`controlled_test_output/tier4_22i_20260501_ebrains_board_roundtrip_pass/`.

Purpose: Tier 4.22i custom-runtime board round-trip smoke. This folder is
regenerated by `make tier4-22i-prepare` after the Tier 4.22k pass. It uses the
confirmed official Spin1API event enum constants `MC_PACKET_RECEIVED` and
`MCPL_PACKET_RECEIVED`, and mirrors EBRAINS SARK packed SDP fields plus
`sark_mem_cpy`. It also uses official SARK router calls
`rtr_alloc`, `rtr_mc_set`, and `rtr_free`, and delegates hardware linking/APLX
creation to official `spinnaker_tools.mk` while explicitly creating nested
object directories such as `build/gnu/src/`. It also defaults to
`--target-acquisition auto`, which can acquire the board through a tiny
`pyNN.spiNNaker` probe and reuse `SpynnakerDataView`'s transceiver/IP when
EBRAINS does not expose a raw hostname. The current package also uses the
official SDP/SCP command header (`cmd_rc`, `seq`, `arg1`, `arg2`, `arg3`,
then `data[]`) after the `cra_422q` load-pass / payload-short failure.

Upload folder:

```text
ebrains_jobs/cra_422r
```

JobManager command:

```text
cra_422r/experiments/tier4_22i_custom_runtime_roundtrip.py --mode run-hardware --output-dir tier4_22i_job_output
```

Boundary: this job tests `.aplx` build/load and `CMD_READ_STATE`
state-mutation round-trip only. It is not full CRA learning or speedup evidence.
The next active custom-runtime target is Tier 4.22l tiny learning parity in
`cra_422t`.

### `cra_422k`

Purpose: Tier 4.22k Spin1API event-symbol discovery. This job has passed and is
kept here as the source-only package used to inspect the actual EBRAINS
build-image headers and compile a callback probe matrix for
`TIMER_TICK`, `SDP_PACKET_RX`, `MC_PACKET_RECEIVED`, `MCPL_PACKET_RECEIVED`,
legacy guessed names, and related event constants.

Upload folder:

```text
ebrains_jobs/cra_422k
```

JobManager command:

```text
cra_422k/experiments/tier4_22k_spin1api_event_discovery.py --mode run-hardware --output-dir tier4_22k_job_output
```

Boundary: this job does not need a board hostname and does not run CRA on a
board. It is build-image/toolchain discovery evidence, not board or learning
evidence.

### `cra_422aa`

Status: **returned hardware pass ingested** at
`controlled_test_output/tier4_22r_20260501_native_context_state_smoke_hardware_pass_ingested/`.
Local/prepared evidence is preserved at
`controlled_test_output/tier4_22r_20260501_native_context_state_smoke_local/` and
`controlled_test_output/tier4_22r_20260501_native_context_state_smoke_prepared/`.

Purpose: Tier 4.22r tiny native context-state custom-runtime smoke. This job
runs after the Tier 4.22q integrated host-v2 bridge hardware pass and moves one
state primitive into C. The host writes keyed context slots, then sends only
key+cue+delay; the runtime retrieves context, computes `feature=context*cue`,
schedules pending credit, and matures delayed targets.

Upload folder:

```text
ebrains_jobs/cra_422aa
```

JobManager command:

```text
cra_422aa/experiments/tier4_22r_native_context_state_smoke.py --mode run-hardware --output-dir tier4_22r_job_output
```

Returned metrics: board `10.11.237.25`, selected core `(0,0,4)`, `58/58` remote criteria plus ingest criterion passed, sequence length `30`, context writes `9`, context reads `30`, max native context slots `3`, pending gap `2`, max pending depth `3`, accuracy `0.9333333333`, tail accuracy `1.0`, all raw deltas `0`, final `readout_weight_raw=32752`, and final `readout_bias_raw=-16`. Boundary: tiny native context-state primitive only; not full native v2.1 memory/routing, full CRA learning, speedup, scaling, or final autonomy.

### `cra_422ab`

Status: **local pass and EBRAINS package prepared** at
`controlled_test_output/tier4_22s_20260501_native_route_state_smoke_prepared/`.
No hardware claim yet.

Purpose: Tier 4.22s tiny native route-state custom-runtime smoke. This job runs
after the Tier 4.22r native context-state hardware pass and adds chip-owned
route state. The host writes keyed context slots and route state, then sends
only key+cue+delay; the runtime retrieves context and route, computes
`feature=context*route*cue`, schedules pending credit, and matures delayed
targets.

Upload folder:

```text
ebrains_jobs/cra_422ab
```

JobManager command:

```text
cra_422ab/experiments/tier4_22s_native_route_state_smoke.py --mode run-hardware --output-dir tier4_22s_job_output
```

Prepared metrics: sequence length `30`, context writes `9`, context reads `30`, route writes `9`, route reads `30`, route values `[-1, 1]`, pending gap `2`, max pending depth `3`, accuracy `0.9333333333`, tail accuracy `1.0`, final `readout_weight_raw=32768`, and final `readout_bias_raw=0`. Boundary: prepared package only; not hardware evidence until returned EBRAINS artifacts pass and are ingested.

Returned Tier 4.22s result: **hardware pass after ingest correction** at
`controlled_test_output/tier4_22s_20260501_native_route_state_smoke_hardware_pass_ingested/`.
The raw remote manifest reported `fail` because the original runner checked
`route_writes` in the final `CMD_READ_ROUTE` reply, but the protocol returns
route value/confidence/read count there. The ingested pass uses the acknowledged
`CMD_WRITE_ROUTE` row counters, which reached `9`, and preserves the raw remote
manifest/report unchanged.

Returned metrics: board `10.11.237.89`, selected core `(0,0,4)`, build/load
pass, all `30` context/route/schedule/mature rows acknowledged, route writes
`9`, final route reads `31`, all raw deltas `0`, accuracy `0.9333333333`, tail
accuracy `1.0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`.

### `cra_422ac`

Status: **hardware pass ingested** at
`controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_hardware_pass_ingested/`.
The prepared package remains at
`controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_prepared/`.

Purpose: Tier 4.22t tiny native keyed route-state custom-runtime smoke. This
job runs after the Tier 4.22s native route-state hardware pass and replaces the
single global route scalar with bounded keyed route slots. The host writes
keyed context slots and keyed route slots, then sends only key+cue+delay; the
runtime retrieves context and route by key, computes
`feature=context[key]*route[key]*cue`, schedules pending credit, and matures
delayed targets.

Upload folder:

```text
ebrains_jobs/cra_422ac
```

JobManager command:

```text
cra_422ac/experiments/tier4_22t_native_keyed_route_state_smoke.py --mode run-hardware --output-dir tier4_22t_job_output
```

Prepared metrics: sequence length `30`, context writes `9`, context reads
`30`, route-slot writes `15`, route-slot reads `30`, max route slots `3`,
route values `[-1, 1]`, pending gap `2`, max pending depth `3`, accuracy
`0.9333333333`, tail accuracy `1.0`, final `readout_weight_raw=32768`, and
final `readout_bias_raw=0`. Boundary: prepared package only; not hardware
evidence until returned EBRAINS artifacts pass and are ingested.

Returned Tier 4.22t result: **hardware pass**. Board `10.11.235.25`, selected
core `(0,0,4)`, build/load pass, all `30` context/route-slot/schedule/mature
rows acknowledged, route-slot writes `15`, active route slots `3`,
route-slot hits `33`, route-slot misses `0`, all raw deltas `0`, accuracy
`0.9333333333`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final
`readout_bias_raw=0`.

### Tier 4.22u Native Memory-Route State Job

Prepared from `controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_prepared/`.

Upload folder:

```text
/Users/james/JKS:CRA/ebrains_jobs/cra_422ad
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
/Users/james/JKS:CRA/ebrains_jobs/cra_422ae
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
/Users/james/JKS:CRA/ebrains_jobs/cra_422ag
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


### Tier 4.22x Compact v2 Bridge Over Native Decoupled State Primitive Job

Prepared from `controlled_test_output/tier4_22x_20260501_compact_v2_bridge_decoupled_smoke_prepared/`.

Upload folder:

```text
/Users/james/JKS:CRA/ebrains_jobs/cra_422ah
```

JobManager command:

```text
cra_422ah/experiments/tier4_22x_compact_v2_bridge_decoupled_smoke.py --mode run-hardware --output-dir tier4_22x_job_output
```

Purpose: test whether a bounded host-side v2 state bridge can drive the native decoupled context/route/memory primitive on real SpiNNaker. The host maintains v2-style state (context slots, route table, memory slots), selects decoupled keys per event, writes state to the chip, and schedules via `CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING`. The chip performs lookup, feature composition, pending queue, prediction, maturation, and readout update. No new command surface; reuses `RUNTIME_PROFILE=decoupled_memory_route` from 4.22w.

Local/prepared metrics: 48 rows, context writes/reads `12/48`, route-slot writes/reads `12/48`, memory-slot writes/reads `12/48`, max context/route/memory slots `4/4/4`, feature source `chip_decoupled_context_route_memory_lookup_feature_transform`, accuracy `0.9583333333`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`.

Returned Tier 4.22x result: **HARDWARE PASS**. Board `10.11.236.73`, selected core `(0,0,4)` after fallback from requested core 1 (cores 1,2,3 occupied). Target acquisition used `pyNN.spiNNaker` probe fallback because EBRAINS JobManager does not expose a raw hostname. `89/89` criteria passed, all `48` schedule/mature pairs completed, all chip-computed feature/context/route/memory/prediction/weight/bias raw deltas `0`, observed accuracy `0.958333`, tail accuracy `1.0`, active context/route/memory slots `4/4/4`, context writes/reads `12/48`, route-slot writes/reads `12/48`, memory-slot writes/reads `12/48`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`. Probe runtime ~46.8 seconds. Zero synthetic fallback. APLX build pass, app load pass, task micro-loop pass.

Claim boundary: this hardware pass proves only that a bounded host-side v2 state bridge can drive the native decoupled primitive on real SpiNNaker. It is not full native v2.1, not native predictive binding, not native self-evaluation, not full CRA task learning, not continuous no-batching runtime, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.
