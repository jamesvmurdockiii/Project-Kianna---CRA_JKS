# CRA Controlled Experiments

This directory contains reproducible experiment harnesses for the staged CRA
validation plan.

## Current Evidence Count

The original validation plan has **12 core tests**:

- Tier 1 sanity: tests 1-3
- Tier 2 learning proof: tests 4-6
- Tier 3 architecture ablations: tests 7-9
- Tier 4 scaling/portability: tests 10-12

`Tier 4.10b - Hard Population Scaling` is an added scaling stress test between
core test 10 and core test 11. `Tier 4.13 - SpiNNaker Hardware Capsule` is a
post-core hardware addendum after backend parity. `Tier 4.14 - Hardware Runtime
Characterization` is a post-v0.1 hardware engineering addendum. `Tier 4.15 -
SpiNNaker Hardware Multi-Seed Repeat` is a hardware repeatability addendum.
`Tier 5.1 - External Baselines` is a post-hardware comparison tier. `Tier 5.2 -
Learning Curve / Run-Length Sweep` tests whether the Tier 5.1 comparison changes
with longer runs. `Tier 5.3 - CRA Failure Analysis / Learning Dynamics Debug`
diagnoses the Tier 5.2 weaknesses. `Tier 5.4 - Delayed-Credit Confirmation`
checks the leading Tier 5.3 candidate against current CRA and external baselines
at longer run lengths. `Tier 4.16a - Repaired Delayed-Cue Hardware Repeat`
then tests the confirmed delayed-credit setting on real SpiNNaker hardware
across three seeds. `Tier 4.16b - Repaired Hard-Switch Hardware Repeat` tests
the repaired hard_noisy_switching capsule on the same hardware path. `Tier
4.18a - v0.7 Chunked Hardware Runtime Baseline` characterizes the current
chunked-host hardware bridge and selects chunk `50` as the fastest viable
default. Tiers 5.12a/5.12c/5.12d validate predictive-pressure tasks, repair the
visible predictive-context mechanism shams, and freeze a bounded v1.8 software
baseline after compact regression. With these addenda included, the tracked
evidence suite is **27 entries total**:

```text
3 sanity + 3 learning + 3 architecture + 1 baseline scaling
+ 1 hard-scaling addendum + 1 domain transfer + 1 backend parity
+ 1 hardware capsule + 1 runtime characterization + 1 hardware repeat
+ 1 external-baseline comparison + 1 learning-curve sweep
+ 1 failure-analysis diagnostic + 1 delayed-credit confirmation
+ 1 repaired delayed-cue hardware repeat
+ 1 repaired hard-switch hardware repeat
+ 1 v0.7 chunked hardware runtime baseline
+ 1 expanded baseline suite + 1 tuned-baseline fairness audit
+ 1 compact regression guardrail
+ 1 predictive task-pressure validation + 1 predictive-context sham repair
+ 1 predictive-context compact-regression gate
+ 1 lifecycle/self-scaling + 1 lifecycle sham-control suite
+ 1 circuit motif causality suite
+ 1 four-core distributed context/route/memory/learning smoke = 27
```

As of the latest documented run, tests 1-12, 10b, Tier 4.13, Tier 4.14,
Tier 4.15, Tier 5.1, Tier 5.2, Tier 5.3, Tier 5.4, Tier 4.16a,
Tier 4.16b, Tier 4.18a, Tier 5.5, Tier 5.6, Tier 5.7,
Tier 5.12a, Tier 5.12c, Tier 5.12d, Tier 6.1, Tier 6.3,
Tier 6.4, and Tier 4.26 have been implemented and run. Tier 4.12 proves NEST/Brian2 parity plus SpiNNaker
PyNN readiness prep. Tier 4.13 records a real SpiNNaker hardware-capsule pass
for the minimal fixed-pattern task through EBRAINS/JobManager. Tier 4.14
characterizes the runtime overhead of that hardware pass while keeping the
learning, repeatability, and scaling claims separate. Tier 4.15 repeats the same
minimal capsule across three hardware seeds. Tier 5.1 compares CRA against
simple external learners and documents both the CRA hard-task edge and the
delayed-cue baseline loss. Tier 5.2 shows those Tier 5.1 edges do not strengthen
at the 1500-step horizon under the tested settings. Tier 5.3 identifies
stronger delayed credit as the leading candidate fix, but does not yet justify
harder hardware migration by itself. Tier 5.4 confirms that candidate versus
the predeclared software criteria. Tier 4.17b passes as a local NEST/Brian2
step-vs-chunked parity diagnostic, and the repaired Tier 4.16a `delayed_cue`
hardware repeat now passes on seeds `42`, `43`, and `44`. The repaired
Tier 4.16b `hard_noisy_switching` hardware repeat also passes on seeds `42`,
`43`, and `44`. Tier 4.18a runtime/resource characterization for the v0.7
chunked hardware path now passes and recommends chunk `50` as the current
hardware default. SNN-native reviewer-defense coverage now includes passed
software temporal-code diagnostics and passed NEST neuron-parameter sensitivity
diagnostics. Tier 5.17 remains a failed broad pre-reward representation
diagnostic, but Tier 5.17d now supplies bounded predictive-binding repair
evidence on cross-modal and reentry binding tasks. Tier 5.17e then passes the
promotion/regression gate and freezes v2.0 after v1.8 compact regression, v1.9
composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d
predictive-binding guardrails all remain green. Broader unsupervised concept
formation, hardware/on-chip temporal coding, hardware neuron-model robustness,
and hardware/on-chip representation formation remain future obligations, not
current claims.

Tier 5.9a macro eligibility has now been implemented and run as a noncanonical
mechanism diagnostic. It completed the full 108-run NEST matrix with no feedback
leakage and active traces, but failed promotion criteria, so it is audit history
and a Tier 5.9b repair target rather than a canonical claim. Tier 5.9b has also
now completed as a clean failed residual-repair diagnostic: the bounded residual
trace preserved delayed_cue but still failed trace-ablation specificity, so
macro eligibility is parked as non-promoted research scaffold. Tier 5.9c later
rechecked that decision against the v2.1 evidence state: v2.1 guardrails stayed
green, but macro still failed trace-ablation specificity, so it remains parked
and excluded from hardware/custom-C migration.

Tier 4.20a now passes as a v2.1 hardware-transfer readiness audit. It is not
hardware evidence; it maps each v2.1 mechanism to chunked-host readiness versus
future hybrid/custom-C/on-chip blockers and recommends a one-seed v2.1 chunked
hardware probe without macro eligibility.

Tier 4.20b now passes as that one-seed probe at
`controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass/`
with an ingested copy at
`controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass_ingested/`.
The JobManager return delegates real SpiNNaker execution to the proven Tier 4.16
chunked-host runner, records the v2.1 bridge profile explicitly, and shows real
spike readback, zero fallback, zero `sim.run` failures, and zero readback
failures. It is bridge/transport evidence only, not native/on-chip v2.1
mechanism execution.

Before uploading for hardware, use the local source/simulation
preflight:

```bash
make tier4-20b-preflight
```

Upload `experiments/`, `coral_reef_spinnaker/`, and optionally
`run_tier4_20b.py` into one EBRAINS workspace folder. Do not upload local
`controlled_test_output/`, and do not upload `baselines/` just to run hardware.
Tier 4.20a audit context is optional provenance only and is not a runtime
dependency. Do not run the simulation preflight on EBRAINS; the EBRAINS-side
probe is the direct JobManager command:

```text
cra/experiments/tier4_20b_v2_1_hardware_probe.py --mode run-hardware --tasks delayed_cue,hard_noisy_switching --seeds 42 --steps 1200 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20 --no-require-real-hardware --output-dir tier4_20b_job_output
```

That probe is a tiny empirical hardware run, not a source/typecheck gate. If the
local detector cannot see a machine target, the caveat is recorded, but the
claim is decided by actual pyNN.spiNNaker execution, zero fallback, zero
readback failures, and nonzero real spike readback.

Tier 5.10 multi-timescale memory has now been implemented and run as a
noncanonical recurrence/forgetting diagnostic. It completed the full 99-run NEST
matrix with no feedback leakage, but the proxy memory candidate failed
promotion criteria and sign-persistence dominated the return phases. The next
memory step was recurrence-task repair, not sleep/replay promotion.
Tier 5.10b has now completed as a noncanonical task-validation pass: repaired
memory-pressure streams require remembered context, oracle/context-memory
controls solve them, and shuffled/reset/wrong-memory controls fail. It
authorizes Tier 5.10c mechanism testing; it is not a CRA memory claim.
Tier 5.10c has now completed as a noncanonical software mechanism pass:
explicit host-side context binding reaches perfect accuracy on the repaired
streams and survives reset/shuffle/wrong-memory ablations. It is still not
native/internal CRA memory or sleep/replay evidence.
Tier 5.10d has now completed as a noncanonical internal software-memory pass:
the context-memory mechanism lives inside `Organism`, receives raw
observations, matches the external scaffold, survives memory ablations, and
keeps full compact regression green. It is still not native on-chip memory,
hardware transfer, or sleep/replay evidence.
Tier 5.10e has now completed as a noncanonical internal memory-retention stress
pass: the same internal memory pathway survives longer gaps, denser distractors,
and hidden recurrence pressure while matching the external scaffold and beating
v1.4/raw CRA, memory ablations, sign persistence, and the best standard
baseline. Tier 5.10f has now completed as a clean noncanonical
capacity/interference stress failure: the full 153-run matrix completed with
zero leakage and active memory updates, but the single-slot internal memory
candidate fails under overlapping contexts and context reentry. Tier 5.10g then
repairs that measured failure with bounded keyed/multi-slot context memory
inside `Organism`: the full 171-run matrix completes with zero leakage, reaches
`1.0` all accuracy on all three capacity/interference tasks, beats v1.5
single-slot memory and slot ablations, and keeps compact regression green. This
is v1.6 host-side keyed-memory evidence, not sleep/replay, hardware memory,
module routing, compositionality, or general working memory.

Tier 5.18 self-evaluation/metacognitive monitoring now has passed software
diagnostic evidence over frozen v2.0, and Tier 5.18c passed the promotion gate
that freezes v2.1. The diagnostic exported pre-feedback confidence/uncertainty
traces, passed leakage-safe shams, beat trivial/random/shuffled confidence
controls, and showed confidence-gated behavioral benefit; the promotion gate
reran the full v2.0 compact gate plus the Tier 5.18 guardrail. Tier 7.6
long-horizon planning/subgoal control remains a future capability obligation.

Tier 5.13, Tier 5.13b, and Tier 5.13c now form the compositionality/routing
audit ladder. Tier 5.13 proves an explicit reusable-module scaffold can solve
held-out skill compositions; Tier 5.13b proves an explicit contextual router can
select the correct module before feedback; Tier 5.13c internalizes both as a
host-side CRA pathway with no-write/reset/shuffle/random/always-on shams, zero
feedback leakage across `22941` checked rows, `1.0` minimum held-out
composition/routing accuracy, and a fresh full compact regression preserved.
This freezes v1.9 as bounded host-side software composition/routing evidence.
It does not yet prove SpiNNaker hardware routing, native on-chip composition,
language, planning, AGI, or external-baseline superiority.
Tier 5.17e now freezes v2.0 as bounded host-side software predictive-binding
evidence after v1.8 compact regression, v1.9 composition/routing, Tier 5.14
working-memory/context binding, and Tier 5.17d predictive-binding guardrails
all pass. It remains software-only and does not prove hardware/on-chip
representation learning, broad unsupervised concept learning, full world
modeling, language, planning, AGI, or external-baseline superiority.

## Evidence Categories

This repo uses five evidence labels so paper claims stay clean:

- **Canonical registry evidence**: entries in `controlled_test_output/STUDY_REGISTRY.json`; these populate the paper-facing results table and require all registered criteria/artifacts to pass.
- **Baseline-frozen mechanism evidence**: a mechanism diagnostic or promotion gate that passed its predeclared gate, preserved compact regression, and has a frozen `baselines/CRA_EVIDENCE_BASELINE_vX.Y.*` lock, but is not necessarily listed as a canonical registry bundle yet.
- **Noncanonical diagnostic evidence**: useful pass/fail diagnostic work that answers a design question but does not by itself freeze a new baseline or enter the canonical paper table.
- **Failed/parked diagnostic evidence**: clean negative evidence retained to prevent p-hacking and explain why a mechanism was not promoted.
- **Hardware prepare/probe evidence**: prepared capsules and one-off probes; these are not hardware claims until returned artifacts are reviewed and explicitly promoted.

In short: `noncanonical` does not mean worthless. It means "not a formal registry/paper-table claim by itself." A frozen baseline such as v1.6, v1.7, v1.9, v2.0, or v2.1 is stronger than an ordinary diagnostic even when its source bundle remains outside the canonical registry.

After adding or ingesting evidence, update and validate the study ledger:

```bash
python3 experiments/evidence_registry.py
```

The registry writes `controlled_test_output/STUDY_REGISTRY.json`,
`controlled_test_output/STUDY_REGISTRY.csv`, `controlled_test_output/README.md`,
and the source-facing `STUDY_EVIDENCE_INDEX.md`. Schema and citation rules live
in `experiments/EVIDENCE_SCHEMA.md`.

Export the paper-facing result table after the registry is current:

```bash
python3 experiments/export_paper_results_table.py
```

Run the repository hygiene and paperwork audit after the paper table is current:

```bash
python3 experiments/repo_audit.py
```

The latest hardware repeatability result is Tier 4.15, which repeats the minimal
SpiNNaker hardware capsule across seeds `42,43,44` with zero fallback/failures
and nonzero spike readback in every seed.

## Tier 1 Sanity Tests

Run the full Tier 1 sequence:

```bash
python3 experiments/tier1_sanity.py --tests all --stop-on-fail
```

The tests run in this order:

1. `zero_signal`
2. `shuffled_label`
3. `seed_repeat`

If `--stop-on-fail` is enabled, the harness stops at the first failed test so
debugging starts from the earliest broken assumption.

## Outputs

Each Tier 1 run writes an evidence bundle under:

```text
controlled_test_output/tier1_<timestamp>/
```

The bundle includes:

- `tier1_report.md`: human-readable findings
- `tier1_results.json`: machine-readable manifest
- `tier1_summary.csv`: compact summary table
- per-test CSV files with step-level metrics
- PNG plots for the time series and seed-repeat distribution

`controlled_test_output/tier1_latest_manifest.json` points to the latest run.

## Interpretation

Tier 1 is a negative-control tier. Passing Tier 1 does not prove learning. It
proves the organism does not appear to learn when:

- there is no input/target signal
- labels are deliberately broken
- the result is repeated across many random seeds

Tier 2 is where fixed-pattern, delayed-reward, and nonstationary learning proof
tests begin.

## Tier 2 Learning-Proof Tests

Run the full Tier 2 sequence:

```bash
python3 experiments/tier2_learning.py --tests all --stop-on-fail
```

The default backend is `nest` when available. The tests run in this order:

1. `fixed_pattern`
2. `delayed_reward`
3. `nonstationary_switch`

Tier 2 defaults to a fixed population so learning can be evaluated without
birth/death confounds. Trophic selection gets its own ablation in Tier 3.

Outputs are written under:

```text
controlled_test_output/tier2_<timestamp>/
```

## Tier 3 Architecture Ablation Tests

Run the full Tier 3 sequence:

```bash
python3 experiments/tier3_ablation.py --tests all --stop-on-fail
```

The tests run in this order:

1. `no_dopamine_ablation`
2. `no_plasticity_ablation`
3. `no_trophic_selection_ablation`

Tier 3 uses paired comparisons. Each test runs an intact organism and a
targeted ablation over the same controlled task and seeds, then requires the
ablated mechanism to fail, freeze, or lose measurable value in the expected
direction.

The default run uses seeds `42`, `43`, and `44` on the `nest` backend.
Fixed-pattern ablations use 180 steps; trophic-selection ablation uses a
220-step nonstationary switch stressor.

Outputs are written under:

```text
controlled_test_output/tier3_<timestamp>/
```

The bundle includes:

- `tier3_report.md`: human-readable architecture findings
- `tier3_results.json`: machine-readable manifest
- `tier3_summary.csv`: compact summary table
- per-case, per-seed CSV files with step-level metrics
- PNG comparison plots for intact versus ablated behavior

`controlled_test_output/tier3_latest_manifest.json` points to the latest run.

Interpretation:

- `no_dopamine_ablation` should fail the fixed-pattern task while keeping raw
  dopamine at zero and readout weights frozen.
- `no_plasticity_ablation` should fail the fixed-pattern task even though
  dopamine is still present, proving the issue is frozen plasticity rather
  than missing consequence signals.
- `no_trophic_selection_ablation` should suppress births/deaths and show lower
  adaptation value than the ecology-enabled organism on the switch stressor.
  The criterion uses full-stressor accuracy and prediction/target correlation
  because both ablated and intact runs can eventually saturate tail accuracy
  after the switch.

## Tier 4 Population Scaling Tests

Run the population-scaling test:

```bash
python3 experiments/tier4_scaling.py --population-sizes 4,8,16,32,64
```

Tier 4.10 runs the same nonstationary switch task at exact fixed population
sizes. `initial_population` and `max_population_hard` are both set to the
requested size; reproduction and apoptosis are disabled so the x-axis is
controlled.

The default run uses:

- backend: `nest`
- sizes: `4`, `8`, `16`, `32`, `64`
- seeds: `42`, `43`, `44`
- steps: `220`

Outputs are written under:

```text
controlled_test_output/tier4_<timestamp>/
```

The bundle includes:

- `tier4_report.md`: human-readable scaling findings
- `tier4_results.json`: machine-readable manifest
- `tier4_summary.csv`: compact size-by-size summary
- per-size, per-seed CSV files with step-level metrics
- `population_scaling_summary.png`
- `population_scaling_timeseries.png`

`controlled_test_output/tier4_latest_manifest.json` points to the latest run.

Interpretation:

- Passing means larger fixed populations do not collapse, preserve exact live
  counts, meet accuracy/correlation floors, and do not degrade sharply versus
  the smallest tested population.
- A flat curve is still meaningful: it says scaling is stable but not yet
  adding much behavioral value on this specific task.

## Tier 4.10b Hard Population Scaling

Run the hard-scaling addendum:

```bash
python3 experiments/tier4_hard_scaling.py --population-sizes 4,8,16,32,64
```

Tier 4.10b keeps the fixed-population control from Tier 4.10, but makes the
task hard enough for scaling to have something to prove:

- noisy delayed cue/reward trials
- reward delay of 3-5 steps
- irregular rule switches every 40-50 steps by default
- population sizes `4`, `8`, `16`, `32`, `64`
- seeds `42`, `43`, `44`
- backend `nest` by default
- births and deaths disabled to keep N exact
- trophic/energy dynamics still active
- deterministic founder diversity across readout weights and local readout
  learning-rate scales

Outputs are written under:

```text
controlled_test_output/tier4_10b_<timestamp>/
```

The bundle includes:

- `tier4_10b_report.md`: human-readable hard-scaling findings
- `tier4_10b_results.json`: machine-readable manifest
- `tier4_10b_summary.csv`: compact size-by-size summary
- per-size, per-seed CSV files with step-level metrics
- `hard_population_scaling_summary.png`
- `hard_population_scaling_timeseries.png`

`controlled_test_output/tier4_10b_latest_manifest.json` points to the latest
run.

Pass criteria:

- no extinction or population collapse
- fixed population has no births/deaths
- all population sizes stay above the random overall-accuracy floor
- larger N does not degrade sharply versus N=4
- larger N improves at least one scaling-value signal: accuracy, correlation,
  recovery speed, or seed-to-seed variance

Latest documented run:

- output: `controlled_test_output/tier4_10b_20260426_161251/`
- status: `PASS`
- all sizes remained above the random floor
- N=64 matched N=4 overall accuracy, improved prediction/target correlation,
  improved recovery by about 9.26 steps, and preserved exact fixed population
  counts

Interpretation:

- Tier 4.10 showed baseline scaling was stable but saturated.
- Tier 4.10b shows the harder stressor is also stable and exposes useful
  scaling value through correlation, recovery, and variance.
- The honest claim is still not "bigger is always more accurate"; it is
  "larger populations do not collapse and can add robustness/adaptation value
  when the task is harder."

## Tier 4.11 Domain Transfer

Run the domain-transfer test:

```bash
python3 experiments/tier4_domain_transfer.py --backend nest --stop-on-fail
```

Tier 4.11 tests whether CRA is a substrate-level learner rather than a
trading-shaped learner. It compares the existing controlled
finance/signed-return path against a non-finance `sensor_control` adapter under
the same core settings:

- same `Organism`
- same `LearningManager`
- same NEST backend
- same seeds `42`, `43`, `44`
- same fixed population size `N=8`
- same delayed signed cue/consequence structure
- same zero-signal and shuffled-label controls

The domain cases are:

- `finance_signed_return`: controlled finance-style signed-return task through
  `TradingBridge`
- `sensor_control`: non-finance task through `SensorControlAdapter`
- `finance_zero_signal`
- `sensor_zero_signal`
- `finance_shuffled_label`
- `sensor_shuffled_label`

The `sensor_control` cases use:

```python
Organism(config, sim, use_default_trading_bridge=False)
organism.train_adapter_step(SensorControlAdapter(), observation)
```

That means no `TradingBridge` is constructed for the non-finance adapter path.

Outputs are written under:

```text
controlled_test_output/tier4_11_<timestamp>/
```

The bundle includes:

- `tier4_11_report.md`: human-readable domain-transfer findings
- `tier4_11_results.json`: machine-readable manifest
- `tier4_11_summary.csv`: compact case-by-case summary
- per-case, per-seed CSV files with step-level metrics
- per-case, per-seed PNG time-series plots
- `domain_transfer_summary.png`

`controlled_test_output/tier4_11_latest_manifest.json` points to the latest
run.

Latest documented run:

- output: `controlled_test_output/tier4_11_20260426_164655/`
- status: `PASS`
- finance overall accuracy: `0.863636`
- sensor_control overall accuracy: `0.954545`
- finance shuffled accuracy: `0.530303`
- sensor shuffled accuracy: `0.560606`
- sensor adapter path reported `trading_bridge_present_any_run=False`

Interpretation:

- CRA learned the finance and non-finance delayed signed tasks.
- Zero and shuffled controls did not show fake learning.
- The non-finance adapter path did not require trading/capital APIs.
- In sparse delayed-control cases, the useful signal can appear through matured
  delayed-consequence credit rather than same-step raw dopamine telemetry; check
  matured horizon counts alongside `raw_dopamine`.

## Tier 4.12 Backend Parity

Run the backend-parity test:

```bash
python3 experiments/tier4_backend_parity.py --backends nest,brian2 --stop-on-fail
```

Tier 4.12 tests whether the same fixed-pattern learning result survives backend
movement:

- NEST fixed-pattern baseline
- Brian2 same task, config, seeds, and population size
- SpiNNaker PyNN import/setup/factory readiness prep
- no synthetic spike fallback allowed for NEST or Brian2
- no `sim.run()` or hardware execution claimed for SpiNNaker prep

The default run uses:

- backends: `nest`, `brian2`
- seeds: `42`, `43`, `44`
- fixed population size: `N=8`
- steps per run: `120`
- task: fixed-pattern inverse next-symbol mapping

Outputs are written under:

```text
controlled_test_output/tier4_12_<timestamp>/
```

The bundle includes:

- `tier4_12_report.md`: human-readable backend-parity findings
- `tier4_12_results.json`: machine-readable manifest
- `tier4_12_summary.csv`: compact backend/parity/prep summary
- per-backend, per-seed CSV files with step-level metrics
- per-backend, per-seed PNG time-series plots
- `backend_parity_summary.png`

`controlled_test_output/tier4_12_latest_manifest.json` points to the latest
run.

Latest documented run:

- output: `controlled_test_output/tier4_12_20260426_170808/`
- status: `PASS`
- NEST overall accuracy: `0.974790`
- Brian2 overall accuracy: `0.974790`
- NEST tail accuracy: `1.0`
- Brian2 tail accuracy: `1.0`
- NEST/Brian2 accuracy delta: `0.0`
- NEST/Brian2 tail-correlation delta: `0.0`
- synthetic fallbacks: `0`
- `sim.run` failures: `0`
- summary-read failures: `0`
- SpiNNaker PyNN prep: import/setup/factory readiness passed

Interpretation:

- The fixed-pattern learning behavior is portable across NEST and Brian2 in
  this controlled harness.
- The Brian2 path is now real backend spike readback, not synthetic fallback;
  the harness fails if fallback counters move above zero.
- The local SpiNNaker PyNN stack is ready for the next stricter step, but this
  result is only prep readiness, not a SpiNNaker hardware learning claim.

## Tier 4.13 SpiNNaker Hardware Capsule

Prepare the hardware capsule locally:

```bash
python3 experiments/tier4_spinnaker_hardware_capsule.py --mode prepare
```

Run the capsule inside a real EBRAINS/JobManager SpiNNaker allocation:

```bash
python3 experiments/tier4_spinnaker_hardware_capsule.py --mode run-hardware --require-real-hardware --stop-on-fail
```

Ingest a completed JobManager result directory:

```bash
python3 experiments/tier4_spinnaker_hardware_capsule.py --mode ingest --ingest-dir <job-output-dir>
```

Tier 4.13 is intentionally not the same as Tier 4.12. It tests the next real
door:

- same minimal fixed-pattern CRA task
- same `N=8`, seed `42`, 120-step configuration as the Tier 4.12 fixed-pattern
  parity run, as much as hardware allows
- execution through `pyNN.spiNNaker`
- zero synthetic fallbacks allowed
- zero `sim.run` failures allowed
- zero summary-read failures allowed
- real spike readback required
- output logs/provenance/results exported for comparison
- failure runs export a traceback, backend diagnostics JSON, and recent
  sPyNNaker `reports/` directories for hardware triage

Outputs are written under:

```text
controlled_test_output/tier4_13_<timestamp>/
```

The local prepare bundle includes:

- `tier4_13_report.md`: human-readable capsule findings
- `tier4_13_results.json`: machine-readable manifest
- `tier4_13_summary.csv`: compact status summary
- `local_environment.json`: local sPyNNaker/JobManager readiness facts
- `tier4_13_reference_tier4_12.json`: current local parity reference
- `jobmanager_capsule/`: config, expected outputs, and run script

`controlled_test_output/tier4_13_latest_manifest.json` points to the latest
Tier 4.13 bundle.

Latest canonical hardware-pass bundle:

- output: `controlled_test_output/tier4_13_20260427_011912_hardware_pass/`
- source generated at: `2026-04-27T00:33:33+00:00`
- source remote output:
  `/tmp/job18372215669669985472.tmp/cra_test/controlled_test_output/tier4_13_20260427_011912`
- status: `PASS`
- backend: `pyNN.spiNNaker`
- seed: `42`
- population/steps: `N=8`, fixed population, 120 steps
- hardware run attempted: `True`
- hardware target configured by detector: `False`
- synthetic fallbacks: `0`
- `sim.run` failures: `0`
- summary-read failures: `0`
- total spike readback: `283903`
- overall strict accuracy: `0.9747899159663865`
- tail strict accuracy: `1.0`
- overall prediction-target correlation: `0.8917325875598855`
- tail prediction-target correlation: `0.9999839178111984`
- final alive polyps: `8.0`
- births/deaths: `0 / 0`
- runtime seconds: `858.6201063019689`
- imported study record: `study_data.json`
- raw intake record: `DOWNLOAD_INTAKE_MANIFEST.json`
- extracted provenance:
  `spinnaker_reports/2026-04-27-01-19-12-390038/`
- quarantined older blocked/failure downloads:
  `_quarantine_noncanonical/`

Interpretation:

- Tier 4.13 passes as a minimal fixed-pattern SpiNNaker hardware capsule.
- The run learned the fixed-pattern capsule in the limited sense required here:
  overall strict accuracy is above threshold, tail strict accuracy is perfect,
  tail prediction-target correlation is near one, and real spike readback is
  nonzero.
- This is still a single-seed, fixed-population hardware capsule. Do not describe
  it as full hardware scaling or full CRA hardware deployment.
- `hardware_target_configured=False` is retained as a detector/env caveat, not as
  fallback evidence. The pass relies on completed hardware `sim.run`, zero
  fallback/failure counters, and nonzero spike readback.

## Tier 4.14 Hardware Runtime Characterization

Characterize the canonical Tier 4.13 hardware pass without rerunning hardware:

```bash
python3 experiments/tier4_hardware_runtime_characterization.py --mode characterize-existing
```

Prepare a fresh JobManager runtime-characterization capsule:

```bash
python3 experiments/tier4_hardware_runtime_characterization.py --mode prepare
```

Run a fresh runtime characterization inside a real SpiNNaker allocation:

```bash
python3 experiments/tier4_hardware_runtime_characterization.py --mode run-hardware --require-real-hardware --stop-on-fail
```

Tier 4.14 answers a different question from Tier 4.13:

- Tier 4.13 asks whether the minimal capsule runs and learns on hardware.
- Tier 4.14 asks where the wall-clock time went.

Outputs are written under:

```text
controlled_test_output/tier4_14_<timestamp>/
```

The bundle includes:

- `tier4_14_report.md`: human-readable runtime findings
- `tier4_14_results.json`: machine-readable manifest
- `tier4_14_summary.csv`: compact runtime summary
- `tier4_14_category_timers.csv`: sPyNNaker category timer aggregates
- `tier4_14_top_algorithms.csv`: sPyNNaker algorithm timer aggregates
- `tier4_14_runtime_breakdown.csv`: combined timer breakdown
- `tier4_14_runtime_breakdown.png`: runtime category plot

Latest canonical runtime-characterization bundle:

- output: `controlled_test_output/tier4_14_20260426_213430/`
- source bundle: `controlled_test_output/tier4_13_20260427_011912_hardware_pass/`
- status: `PASS`
- runtime seconds: `858.6201063019689`
- simulated biological seconds: `6.0`
- wall-to-simulated-time ratio: `143.10335105032814`
- mean wall time per 50 ms step: `7.155167552516407`
- dominant category: `Running Stage`, `637.741974` seconds
- dominant algorithm: `Application runner`, `87.375508` seconds total
- application-runner time per step: `0.7281292333333333` seconds
- buffer extraction: `32.786108999999996` seconds total

Interpretation:

- Tier 4.14 passes as runtime/provenance characterization, not as a new learning claim.
- The large wall time is dominated by repeated short-step sPyNNaker/hardware orchestration and readback.
- The correct scaling implication is to batch more work per hardware run, reduce readback cadence, or move more adaptation on-chip before making larger hardware-scaling claims.

## Tier 4.15 SpiNNaker Hardware Multi-Seed Repeat

Prepare the local JobManager capsule:

```bash
python3 experiments/tier4_spinnaker_hardware_repeat.py --mode prepare
```

Run the capsule inside a real EBRAINS/JobManager SpiNNaker allocation:

```bash
python3 experiments/tier4_spinnaker_hardware_repeat.py --mode run-hardware --seeds 42,43,44 --require-real-hardware --stop-on-fail
```

Ingest a completed result directory:

```bash
python3 experiments/tier4_spinnaker_hardware_repeat.py --mode ingest --ingest-dir <job-output-dir>
```

Tier 4.15 is repeatability evidence only:

- same fixed-pattern capsule as Tier 4.13
- same `N=8`, 120-step configuration
- seeds `42`, `43`, `44`
- zero synthetic fallback allowed
- zero `sim.run` failures allowed
- zero summary-read failures allowed
- nonzero spike readback required for every seed
- accuracy/correlation thresholds must pass for every seed

Latest canonical hardware-repeat bundle:

- output: `controlled_test_output/tier4_15_20260427_030501_hardware_pass/`
- status: `PASS`
- requested seeds: `42,43,44`
- all seed statuses: `pass`
- overall strict accuracy mean/min: `0.9747899159663865 / 0.9747899159663865`
- tail strict accuracy mean/min: `1.0 / 1.0`
- tail prediction-target correlation mean/min:
  `0.9999901037892215 / 0.9999839178111984`
- total spike readback min/mean/max: `284154 / 291103.6666666667 / 295521`
- runtime seconds min/mean/max:
  `865.3982471250929 / 873.6344163606409 / 884.8983335739467`
- synthetic fallbacks: `0`
- `sim.run` failures: `0`
- summary-read failures: `0`

Tier 4.15 can be cited only as repeatability of the same minimal fixed-pattern
hardware capsule. It is not a harder-task hardware result, hardware population
scaling result, or full CRA hardware deployment.

## Tier 4.16 Harder SpiNNaker Hardware Capsule

Prepare the repaired three-seed local JobManager capsule:

```bash
python3 experiments/tier4_harder_spinnaker_capsule.py --mode prepare --tasks delayed_cue --seeds 42,43,44 --steps 1200 --runtime-mode chunked --learning-location host --chunk-size-steps 25
```

Run the repaired three-seed capsule inside a real EBRAINS/JobManager SpiNNaker allocation:

```bash
python3 experiments/tier4_harder_spinnaker_capsule.py --mode run-hardware --tasks delayed_cue --seeds 42,43,44 --steps 1200 --delayed-readout-lr 0.20 --runtime-mode chunked --learning-location host --chunk-size-steps 25 --require-real-hardware --stop-on-fail
```

Ingest a completed result directory:

```bash
python3 experiments/tier4_harder_spinnaker_capsule.py --mode ingest --ingest-dir <job-output-dir>
```

Tier 4.16 is a harder-task hardware-transfer test only:

- `4.16a delayed_cue`
- `4.16b hard_noisy_switching`
- `delayed_lr_0_20`
- `N=8`
- seeds `42`, `43`, `44`
- zero synthetic fallback allowed
- zero `sim.run` failures allowed
- zero summary-read failures allowed
- nonzero real spike readback required for every completed run

Current prepared capsule:

- output: `controlled_test_output/tier4_16_20260427_131914_prepared/`
- status: `prepared`
- tasks: `delayed_cue`
- seeds: `43`
- population: `8`
- delayed readout learning rate: `0.20`
- runtime mode: `chunked + host`
- chunk size: `25`

Tier 4.16a is now canonical evidence for the narrow repaired delayed-cue
hardware-transfer claim. A prepare bundle only proves that the hardware package
exists locally. The passed three-seed repaired run can be cited only as
delayed-cue transfer of the confirmed delayed-credit setting onto SpiNNaker. It
is not hardware scaling, not full CRA hardware deployment, not the full two-task
Tier 4.16 pass, and not a superiority claim over the best external
hard-switching baseline.

Current repaired three-seed hardware repeat:

- output: `controlled_test_output/tier4_16_20260427_184635_delayed_cue_3seed_hardware_pass/`
- status: `pass`
- task/seeds: `delayed_cue`, seeds `42`, `43`, `44`
- steps: `1200`
- runtime mode: `chunked + host`
- chunk size: `25`
- hardware `sim.run` calls: `48` per seed
- minimum real spike readback: `94976`
- fallback/failure counters: `0`
- tail accuracy mean/min: `1.0`
- all accuracy mean: `0.9933333333333333`
- tail prediction-target correlation mean: `0.9999999999999997`
- runtime mean: `562.8373009915618` seconds

Next hardware transfer run:

```bash
python3 experiments/tier4_harder_spinnaker_capsule.py --mode run-hardware --tasks hard_noisy_switching --seeds 42,43,44 --steps 1200 --delayed-readout-lr 0.20 --runtime-mode chunked --learning-location host --chunk-size-steps 25 --require-real-hardware --stop-on-fail
```

Current noncanonical hardware failure:

- output: `controlled_test_output/tier4_16_20260427_124916_hardware_fail/`
- status: `fail`
- hardware execution: all six requested task/seed runs completed
- fallback/failure counters: `0`
- failure criterion: `4.16a delayed_cue tail accuracy`

Run the local delayed-cue failure analysis before any full hardware rerun:

```bash
python3 experiments/tier4_16a_delayed_cue_debug.py --backends nest,brian2 --seeds 42,43,44
```

Current local diagnostic bundle:

- output: `controlled_test_output/tier4_16a_debug_20260427_141912/`
- diagnosis: `software_config_or_metric_issue`
- NEST, Brian2, and SpiNNaker all match: seed `42` passes, seeds `43` and `44`
  fail the `0.85` delayed-cue tail threshold
- tail event count: `3`
- one tail event changes tail accuracy by `0.3333333333333333`

Interpretation: the Tier 4.16a failure is not primarily a hardware-transfer
failure. The exact delayed-cue capsule is underpowered/brittle under the current
120-step tail metric. Fix or redesign that local task/metric before spending
another six-run hardware allocation.

Run the repaired longer delayed-cue local probe:

```bash
python3 experiments/tier4_16a_delayed_cue_fix.py --run-lengths 1200 --backends nest,brian2 --seeds 42,43,44
```

Current repair diagnostics:

- NEST length sweep:
  `controlled_test_output/tier4_16a_fix_nest_length_sweep_20260427_145400/`
- NEST 1200-step pass:
  `controlled_test_output/tier4_16a_fix_nest_1200_20260427_145600/`
- Brian2 1200-step pass:
  `controlled_test_output/tier4_16a_fix_brian2_1200_20260427_145800/`
- NEST+Brian2 1500-step pass:
  `controlled_test_output/tier4_16a_fix_20260427_143252/`

Result:

- `240`, `480`, and `960` steps are not stable enough under the `0.85` tail
  threshold
- `1200` steps passes in NEST and Brian2
- 1200-step minimum tail accuracy: `0.972972972972973`
- 1200-step tail events: `37`
- `1500` steps also passes in NEST and Brian2 with tail accuracy `1.0`

Decision: use `1200` steps for repaired delayed-cue hardware, but do not run it
through the slow per-step loop by default. The three-seed chunked delayed-cue
repeat passed. The first hard_noisy_switching hardware run completed cleanly but
failed the learning gate. The host-replay bridge is now repaired locally on
NEST/Brian2, the repaired seed-44 hardware probe passes narrowly, and the
repaired three-seed hard-switch repeat now passes. Tier 4.18a also now passes:
a small v0.7 chunked hardware runtime baseline with seed `42`, tasks
`delayed_cue` and `hard_noisy_switching`, and chunk sizes `10`, `25`, and `50`.
Chunk `50` is the fastest viable current hardware default. Tier 4.18b may add
chunk `100` or more seeds only if it is worth the hardware cost.

Prepare Tier 4.18a:

```bash
make tier4-18a-prepare
```

Run the generated capsule inside real SpiNNaker/JobManager:

```bash
bash controlled_test_output/<tier4_18a_prepared_run>/jobmanager_capsule/run_tier4_18a_on_jobmanager.sh /tmp/tier4_18a_job_output
```

Tier 4.18a expected outputs:

- `tier4_18a_results.json`
- `tier4_18a_report.md`
- `tier4_18a_summary.csv`
- `tier4_18a_runtime_matrix.csv`
- `tier4_18a_runtime_matrix.png`
- `spinnaker_hardware_<task>_chunk<chunk>_seed<seed>_timeseries.csv`
- `spinnaker_hardware_<task>_chunk<chunk>_seed<seed>_timeseries.png`

Claim boundary: prepared Tier 4.18a bundles are not evidence. The canonical
hardware pass lives at
`controlled_test_output/tier4_18a_20260428_012822_hardware_pass/`. It is
runtime/resource characterization for the v0.7 chunked-host path only; it is not
hardware scaling, lifecycle/self-scaling, native on-chip dopamine/eligibility,
continuous/custom-C learning, or external-baseline superiority.

Refresh the Tier 4.17 runtime contract inventory:

```bash
python3 experiments/tier4_chunked_runtime.py --steps 1200 --chunk-sizes 1,5,10,25,50
```

Run the Tier 4.17b local step-vs-chunked parity diagnostic:

```bash
python3 experiments/tier4_17b_step_vs_chunked_parity.py --backends nest,brian2 --seed 42 --steps 120 --chunk-sizes 5,10,25,50
```

Current Tier 4.17b result:

```text
controlled_test_output/tier4_17b_20260427_164625_step_chunk_parity/
```

Interpretation:

- status: `PASS`
- backends: `nest`, `brian2`
- task: `delayed_cue`
- seed: `42`
- steps: `120`
- chunk sizes: `5`, `10`, `25`, `50`
- synthetic fallback/readback failures: `0`
- max tail/all accuracy delta: `0.0`
- max prediction delta: `0.0`
- max per-bin spike delta: `0`
- minimum spike-bin correlation: `1.0`
- `sim.run` reduction range: `5x` to `40x`

This proves the local mechanics for scheduled input, binned spike readback, and
host replay. It does not prove chunked SpiNNaker hardware learning.

Returned hard-switching chunked hardware transfer:

```text
controlled_test_output/tier4_16_20260427_194526_hard_noisy_switching_3seed_hardware_fail/
```

It used `48` hardware `sim.run` calls per seed and completed with zero fallback,
zero `sim.run` failures, zero summary-read failures, and real spike readback,
but failed the predeclared learning gate: worst-seed tail accuracy
`0.47619047619047616 < 0.5`.

Run the aligned local bridge-repair diagnostic:

```bash
python3 experiments/tier4_16b_hard_switch_debug.py --backends nest,brian2 --seeds 42,43,44 --steps 1200 --chunk-size-steps 25
```

Superseded corrected diagnostic:

```text
controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch_corrected/
classification = chunked_host_bridge_learning_failure
full_step_cra_tail_min = 0.5238095238095238
direct_chunked_host_tail_min = 0.42857142857142855
hardware_tail_min = 0.47619047619047616
max_bridge_tail_delta = 0.0
```

Latest aligned bridge-repair diagnostics:

```text
controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427/
controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_brian2_20260427/
classification = hardware_transfer_or_timing_failure
full_step_cra_tail_min = 0.5476190476190477
direct_chunked_host_tail_min = 0.5238095238095238
hardware_tail_min = 0.47619047619047616
max_bridge_tail_delta = 0.0
```

Repaired seed-44 hardware probe:

```text
controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/
status = pass
seed = 44
tail_accuracy = 0.5238095238095238
tail_events = 22 / 42 correct
all_accuracy = 0.5730994152046783
tail_prediction_target_corr = 0.10016740018210536
real spike readback = 94707
```

This remains a noncanonical one-seed probe superseded by the canonical repaired three-seed hard-switch pass. `raw_dopamine` is zero because this delayed task does not align same-step prediction and delayed feedback; audit the chunked host delayed-credit path with `matured_horizons_this_step`, `pending_horizons`, and `host_replay_weight`.


Canonical repaired three-seed hard-switch hardware pass:

```text
controlled_test_output/tier4_16_20260427_230043_hard_noisy_switching_3seed_hardware_pass/
status = pass
seeds = 42,43,44
tail_accuracy_mean = 0.5476190476190476
tail_accuracy_min = 0.5238095238095238
real spike readback min = 94707
zero fallback/failures = true
```

## Tier 5.1 External Baselines

Run the full comparison:

```bash
python3 experiments/tier5_external_baselines.py --backend nest --seed-count 3 --steps 240 --models all --tasks all
```

Tier 5.1 compares CRA against:

- `random_sign`
- `sign_persistence`
- `online_perceptron`
- `online_logistic_regression`
- `echo_state_network`
- `small_gru`
- `stdp_only_snn`
- `evolutionary_population`

Future Tier 5.5/Tier 5.6 expanded baselines should add stronger
reviewer-defense baselines where the task interface is fair and causal:

- `surrogate_gradient_snn`
- `ann_trained_readout`
- `ann_to_snn_converted` where task-compatible
- liquid-state / reservoir variants
- bandit/RL baselines for action tasks

Expanded baselines should also export sample-efficiency metrics:

- steps to threshold
- tail events to threshold
- reward events to threshold
- switch recovery steps
- area under the learning curve

## Tier 5.5 Expanded Baseline Suite

Run the paper-grade expanded baseline matrix:

```bash
make tier5-5
```

Run a quick harness smoke test:

```bash
make tier5-5-smoke
```

Direct command:

```bash
python3 experiments/tier5_expanded_baselines.py --backend nest --seed-count 10 --run-lengths 120,240,480,960,1500 --tasks fixed_pattern,delayed_cue,hard_noisy_switching,sensor_control --models all --cra-variants v0_8 --stop-on-fail
```

Tier 5.5 compares the locked v0.8 CRA setting (`delayed_lr_0_20`) against the
implemented fair external baselines across tasks, run lengths, and seeds. It
exports:

- aggregate model/task/run-length metrics
- per-seed audit rows
- paired CRA-vs-baseline deltas
- bootstrap confidence intervals
- paired effect sizes
- steps/reward-events to threshold
- area under the online learning curve
- switch recovery and runtime metrics
- a JSON fairness contract

Tier 5.5 has passed and is now canonical v0.9 evidence at:

```text
controlled_test_output/tier5_5_20260427_222736/
```

It is still software-only. It is not hardware evidence, not a hyperparameter
fairness audit, and not a universal-superiority claim. The honest result is
robust advantage/non-dominated hard-adaptive behavior, with documented ties and
best-baseline losses. Deferred reviewer-defense baselines such as
surrogate-gradient SNN, ANN-trained readout, ANN-to-SNN conversion, contextual
bandit/RL, and liquid-state variants belong in Tier 5.6+ until implemented.

## Tier 5.6 Baseline Hyperparameter Fairness Audit

Run the canonical tuned-baseline audit:

```bash
make tier5-6
```

Run a quick harness smoke test:

```bash
make tier5-6-smoke
```

Direct command:

```bash
python3 experiments/tier5_baseline_fairness_audit.py --backend nest --seed-count 5 --run-lengths 960,1500 --tasks delayed_cue,hard_noisy_switching,sensor_control --models all --cra-variants v0_8 --budget standard --stop-on-fail
```

Tier 5.6 has passed and is canonical v1.0 evidence. It keeps CRA locked at the
promoted delayed-credit setting and gives external baselines a predeclared
hyperparameter budget. It exports:

- aggregate candidate metrics
- per-seed audit rows
- paired CRA-vs-retuned-baseline deltas
- confidence intervals and effect sizes
- best and median tuned baseline settings by task/run length
- a JSON fairness contract
- the exact candidate budget used for every external model

Boundary: Tier 5.6 is still software-only. It is not hardware evidence and not
proof of universal superiority. It answers a narrower reviewer-defense question:
does any Tier 5.5 CRA advantage survive after reasonable external-baseline
retuning? The canonical answer is yes for four target regimes, while still not
beating the best tuned baseline on every metric or horizon.

Tier 5.5 canonical tasks:

- `fixed_pattern`
- `delayed_cue`
- `sensor_control`
- `hard_noisy_switching`

Tier 5.6 defaults to the target hard/adaptive set:

- `delayed_cue`
- `sensor_control`
- `hard_noisy_switching`

## Tier 5.7 Compact Regression

Run the canonical compact-regression guardrail:

```bash
make tier5-7
```

Run a quick smoke:

```bash
make tier5-7-smoke
```

Direct command:

```bash
python3 experiments/tier5_compact_regression.py --backend nest --readout-lr 0.10 --delayed-readout-lr 0.20 --stop-on-fail
```

Tier 5.7 has passed and is canonical v1.1 evidence. It reruns compact Tier 1
negative controls, Tier 2 positive controls, Tier 3 architecture ablations, and
delayed_cue/hard_noisy_switching smoke checks under the promoted delayed-credit
setting. This was the guardrail before Tier 6.1 lifecycle/self-scaling was
promoted, not a new capability or superiority claim.

## Tier 6.1 Lifecycle / Self-Scaling

Run the canonical lifecycle/self-scaling benchmark:

```bash
make tier6-1
```

Run a quick smoke:

```bash
make tier6-1-smoke
```

Direct command:

```bash
python3 experiments/tier6_lifecycle_self_scaling.py --backend nest --tasks hard_noisy_switching,delayed_cue --cases fixed4,fixed8,fixed16,life4_16,life8_32,life16_64 --steps 960 --seed-count 3 --cra-readout-lr 0.10 --cra-delayed-readout-lr 0.20 --stop-on-fail
```

Tier 6.1 has passed and is canonical v1.2 evidence. It compares fixed-N CRA
against lifecycle-enabled CRA on identical delayed_cue and hard_noisy_switching
streams under NEST. It supports software lifecycle expansion/self-scaling with
clean lineage and hard_noisy_switching advantage regimes, but the event analysis
must travel with the claim: 74 cleavage events, 1 adult birth event, and 0
deaths. This is not full adult turnover, not hardware lifecycle, not
sham-control proof, and not external-baseline superiority.

## Tier 6.3 Lifecycle Sham Controls

Run the canonical sham-control suite:

```bash
make tier6-3
```

Run a quick smoke:

```bash
make tier6-3-smoke
```

Direct command:

```bash
python3 experiments/tier6_lifecycle_sham_controls.py --backend nest --tasks hard_noisy_switching --regimes life4_16,life8_32 --controls intact,fixed_initial,fixed_max,random_event_replay,active_mask_shuffle,lineage_id_shuffle,no_trophic,no_dopamine,no_plasticity --steps 960 --seed-count 3 --cra-readout-lr 0.10 --cra-delayed-readout-lr 0.20 --stop-on-fail
```

Tier 6.3 has passed and is canonical v1.3 evidence. It tests the Tier 6.1
lifecycle/self-scaling advantage against fixed max-pool capacity, event-count
replay, active-mask/lineage shuffle audits, no trophic pressure, no dopamine,
and no plasticity. The pass records 36/36 actual runs, 26 intact non-handoff
lifecycle events, 0 fixed capacity-control lifecycle events, 0 actual-run
lineage failures, 10/10 performance-sham wins, 2/2 fixed max-pool wins, 2/2
event-count replay wins, and 6/6 lineage-ID shuffle detections. This is
software-only sham-control evidence, not hardware lifecycle, native on-chip
lifecycle, full adult turnover, or external-baseline superiority.

## Tier 6.4 Circuit Motif Causality

Run the canonical motif-causality suite:

```bash
make tier6-4
```

Run a quick smoke:

```bash
make tier6-4-smoke
```

Direct command:

```bash
python3 experiments/tier6_circuit_motif_causality.py --backend nest --tasks hard_noisy_switching --regimes life4_16,life8_32 --variants intact,no_feedforward,no_feedback,no_lateral,no_wta,random_graph_same_edge_count,motif_shuffled,monolithic_same_capacity --steps 960 --seed-count 3 --cra-readout-lr 0.10 --cra-delayed-readout-lr 0.20 --message-passing-steps 1 --message-context-gain 0.025 --message-prediction-mix 0.35 --stop-on-fail
```

Tier 6.4 has passed and is canonical v1.4 evidence. It seeds motif-diverse
graphs before the first outcome feedback, tests feedforward/feedback/lateral/WTA
ablation variants, and compares intact CRA against random graph, motif-label
shuffle, and monolithic same-capacity controls. The pass records 48/48 actual
runs, 2/2 intact motif-diverse aggregates, 1920 intact motif-active steps, 4/8
motif-ablation losses, 0/2 motif-label shuffle losses, 0/4 random/monolithic
dominations, and 0 lineage-integrity failures. This is controlled software
motif structure/edge-role evidence, not hardware motif execution, custom-C or
on-chip learning, compositionality, world modeling, real-world usefulness, or
universal baseline superiority.

Latest canonical external-baseline bundle:

- output: `controlled_test_output/tier5_1_20260426_232530/`
- status: `PASS`
- model/task/seed runs: `108 / 108`
- CRA backend: `nest`
- seeds: `42,43,44`
- hard advantage tasks versus external median: `sensor_control`, `hard_noisy_switching`
- delayed cue caveat: simple online learners beat CRA clearly
- hard noisy switching recovery: CRA `15.066666666666666` steps versus external median `32.33333333333333`

Tier 5.1 can be cited only as controlled software baseline evidence. It is not a
hardware result and not a claim that CRA beats every simpler learner.

## Tier 5.2 Learning Curve / Run-Length Sweep

Run the full sweep:

```bash
python3 experiments/tier5_learning_curve.py --backend nest --seed-count 3 --run-lengths 120,240,480,960,1500 --tasks sensor_control,hard_noisy_switching,delayed_cue --models all --stop-on-fail
```

Latest canonical learning-curve bundle:

- output: `controlled_test_output/tier5_2_20260426_234500/`
- status: `PASS`
- model/task/seed/run-length runs: `405 / 405`
- CRA backend: `nest`
- run lengths: `120,240,480,960,1500`
- final advantage tasks at 1500 steps: `0`
- delayed cue final classification: `external_baselines_dominate_final`
- sensor_control final classification: `mixed_or_neutral`
- hard noisy switching final classification: `mixed_or_neutral`

Tier 5.2 can be cited only as controlled software learning-curve evidence. It is
not a hardware result. Its important finding is that CRA's Tier 5.1 hard-task
edge does not strengthen at the longest tested horizon.

## Tier 5.3 CRA Failure Analysis / Learning Dynamics Debug

Run the full diagnostic matrix:

```bash
python3 experiments/tier5_cra_failure_analysis.py --backend nest --seed-count 3 --steps 960 --tasks delayed_cue,hard_noisy_switching --variants core --stop-on-fail
```

Latest canonical failure-analysis bundle:

- output: `controlled_test_output/tier5_3_20260427_055629/`
- status: `PASS`
- CRA diagnostic runs: `78 / 78`
- CRA backend: `nest`
- seeds: `42,43,44`
- steps: `960`
- tasks: `delayed_cue`, `hard_noisy_switching`
- variants: `13`
- leading candidate fix: `delayed_lr_0_20`
- delayed cue: tail accuracy improves from `0.5555555555555556` to `1.0`
- hard noisy switching: tail accuracy improves from `0.45098039215686275` to `0.5392156862745098`
- hard noisy switching caveat: the tuned CRA variant beats the external median but still trails the best external baseline

Tier 5.3 can be cited only as controlled software failure-analysis evidence. It
is not a hardware result and not a final superiority claim. Its useful result is
that stronger delayed credit became the candidate tested in Tier 5.4 before any
harder SpiNNaker hardware capsule.

## Tier 5.4 Delayed-Credit Confirmation

Run the full confirmation matrix:

```bash
python3 experiments/tier5_delayed_credit_confirmation.py --backend nest --seed-count 3 --run-lengths 960,1500 --tasks delayed_cue,hard_noisy_switching --stop-on-fail
```

Latest canonical delayed-credit confirmation bundle:

- output: `controlled_test_output/tier5_4_20260427_065412/`
- status: `PASS`
- total runs: `120 / 120`
- CRA backend: `nest`
- seeds: `42,43,44`
- run lengths: `960,1500`
- tasks: `delayed_cue`, `hard_noisy_switching`
- candidate: `cra_delayed_lr_0_20`
- delayed cue: candidate tail accuracy `1.0` at both run lengths
- hard noisy switching: candidate beats the external median at both run lengths
- hard noisy switching caveat: the candidate still trails the best external
  baseline at both run lengths

Tier 5.4 can be cited only as controlled software confirmation evidence. It is
not a hardware result and not a hard-switching best-baseline superiority claim.
Its useful result is that Tier 4.16 can now be designed around
`delayed_lr_0_20` instead of the weaker current CRA setting.

## Tier 5.9a Macro Eligibility Trace Diagnostic

Run the quick harness smoke:

```bash
make tier5-9a-smoke
```

Run the full diagnostic matrix:

```bash
make tier5-9a
```

Latest noncanonical diagnostic bundle:

- output: `controlled_test_output/tier5_9a_20260428_162345/`
- status: `FAIL`
- backend: `nest`
- runs: `108 / 108`
- seeds: `42,43,44`
- steps: `960`
- tasks: `delayed_cue`, `hard_noisy_switching`, `variable_delay_cue`, `aba_recurrence`
- variants: `v1_4_pending_horizon`, `macro_eligibility`,
  `macro_eligibility_shuffled`, `macro_eligibility_zero`
- selected baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `stdp_only_snn`
- leakage violations: `0`
- macro trace active steps: `11520`
- macro matured updates: `8536`
- failed criteria: delayed-cue nonregression, variable-delay benefit, and trace
  ablation specificity

Tier 5.9a can be cited only as failed software mechanism-diagnostic evidence.
Its important finding is that the first macro trace is active but not
promotion-ready: normal and shuffled traces matched on multiple tasks, and the
trace replacement regressed known delayed-cue behavior. v1.4 remains the frozen
baseline. If macro credit remains the next blocker, run a bounded Tier 5.9b
repair that blends a normalized trace residual with the v1.4 PendingHorizon
feature instead of replacing it.

## Tier 5.9b Residual Macro Eligibility Repair

Run the quick harness smoke:

```bash
make tier5-9b-smoke
```

Run the full diagnostic matrix:

```bash
make tier5-9b
```

Latest noncanonical diagnostic bundle:

- output: `controlled_test_output/tier5_9b_20260428_174327/`
- status: `FAIL`
- backend: `nest`
- runs: `45 / 45`
- seeds: `42,43,44`
- steps: `960`
- tasks: `delayed_cue`, `hard_noisy_switching`, `variable_delay_cue`
- variants: `v1_4_pending_horizon`, `macro_eligibility`,
  `macro_eligibility_shuffled`, `macro_eligibility_zero`
- selected baseline: `sign_persistence`
- leakage violations: `0`
- macro trace active steps: `8640`
- macro matured updates: `7040`
- failed criterion: trace ablations were not worse than the normal trace

Tier 5.9b can be cited only as failed software mechanism-diagnostic evidence.
The residual repair preserved delayed_cue but did not add causal value beyond
shuffled/zero trace controls, and hard_noisy_switching slightly regressed versus
v1.4. v1.4 PendingHorizon remains the proven delayed-credit mechanism.

## Tier 5.9c Macro Eligibility v2.1 Recheck

Run the quick harness smoke:

```bash
make tier5-9c-smoke
```

Run the full recheck:

```bash
make tier5-9c
```

Latest noncanonical diagnostic bundle:

- output: `controlled_test_output/tier5_9c_20260429_190503/`
- status: `FAIL`
- v2.1 guardrail child: `PASS`
- macro residual recheck child: `FAIL`
- runtime seconds: `2889.924`
- failed reason: residual macro eligibility did not earn promotion
- macro child failed criterion: trace ablations were not worse than normal trace

Tier 5.9c can be cited only as failed software mechanism-diagnostic evidence.
It proves the repo did recheck macro after v2.1, and the answer stayed no:
normal, shuffled, zero-trace, and no-macro paths remained identical on the
delayed-credit harness. Macro eligibility remains parked.

## Tier 5.10 Multi-Timescale Memory / Forgetting Diagnostic

Run the quick harness smoke:

```bash
make tier5-10-smoke
```

Run the full diagnostic matrix:

```bash
make tier5-10
```

Latest noncanonical diagnostic bundle:

- output: `controlled_test_output/tier5_10_20260428_181322/`
- status: `FAIL`
- backend: `nest`
- runs: `99 / 99`
- seeds: `42,43,44`
- steps: `960`
- tasks: `aba_recurrence`, `abca_recurrence`, `hidden_regime_switching`
- variants: `v1_4_pending_horizon`, `multi_timescale_memory`,
  `no_slow_memory`, `no_structural_memory`, `no_bocpd_unlock`,
  `overrigid_memory`
- selected baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `stdp_only_snn`
- leakage violations: `0`
- failed criteria: tail nonregression versus v1.4, recurrence/recovery benefit,
  and memory-ablation specificity

Tier 5.10 can be cited only as failed software mechanism-diagnostic evidence.
The proxy memory-timescale candidate regressed recurrence behavior instead of
improving it. The run also exposed a task-design weakness: sign-persistence was
the strongest external return-phase baseline on all tasks, so Tier 5.10b
repaired the task surface before any sleep/replay or explicit memory-store
claim.

## Tier 5.10b Recurrence-Task Repair / Memory-Pressure Validation

Run the quick task-validation smoke:

```bash
make tier5-10b-smoke
```

Run the full task-validation matrix:

```bash
make tier5-10b
```

Latest noncanonical task-validation bundle:

- output: `controlled_test_output/tier5_10b_20260428_193639/`
- status: `PASS`
- backend: `mock`
- runs: `99 / 99`
- seeds: `42,43,44`
- steps: `720`
- tasks: `delayed_context_cue`, `distractor_gap_context`,
  `hidden_context_recurrence`
- standard baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `small_gru`,
  `stdp_only_snn`
- context controls: `oracle_context`, `stream_context_memory`,
  `shuffled_context`, `memory_reset`, `wrong_context`
- leakage violations: `0`
- sign_persistence max accuracy: `0.5333333333333333`
- oracle/context-memory min accuracy: `1.0`
- context-memory edge versus sign_persistence min: `0.4666666666666667`
- wrong/reset/shuffled-memory control edge min: `0.4642857142857143`
- best standard baseline max accuracy: `0.8154761904761904`

Tier 5.10b can be cited only as software task-validation evidence. It proves the
repaired tasks now create real memory pressure and clean sham controls; it does
not promote a CRA memory mechanism. Tier 5.10c has now tested v1.4 CRA and an
explicit context-memory candidate on these repaired tasks. Tier 5.10d has now
internalized the candidate inside `Organism`.

## Tier 5.10c Explicit Context-Memory Mechanism Diagnostic

Run the quick mechanism smoke:

```bash
make tier5-10c-smoke
```

Run the full NEST mechanism matrix:

```bash
make tier5-10c
```

Latest noncanonical software mechanism bundle:

- output: `controlled_test_output/tier5_10c_20260428_201314/`
- status: `PASS`
- backend: `nest`
- runs: `144 / 144`
- seeds: `42,43,44`
- steps: `720`
- tasks: `delayed_context_cue`, `distractor_gap_context`,
  `hidden_context_recurrence`
- CRA variants: `v1_4_raw`, `explicit_context_memory`,
  `memory_reset_ablation`, `shuffled_memory_ablation`,
  `wrong_memory_ablation`
- standard baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `small_gru`,
  `stdp_only_snn`
- context controls: `oracle_context`, `stream_context_memory`,
  `shuffled_context`, `memory_reset`, `wrong_context`
- leakage violations: `0`
- candidate all accuracy: `1.0` on all repaired tasks
- candidate minimum edge versus v1.4 raw CRA: `0.4666666666666667`
- candidate minimum edge versus best memory ablation: `0.3555555555555556`
- candidate minimum edge versus best standard baseline: `0.18452380952380965`

Tier 5.10c can be cited only as software mechanism-diagnostic evidence. It
shows that explicit host-side context binding is useful and ablation-specific on
the repaired memory-pressure streams. It does not prove native CRA memory,
sleep/replay consolidation, hardware memory, or solved catastrophic forgetting.

## Tier 5.10d Internal Context-Memory Implementation Diagnostic

Run the quick internal-memory smoke:

```bash
make tier5-10d-smoke
```

Run the full NEST internal-memory matrix:

```bash
make tier5-10d
```

Latest noncanonical internal software-memory bundle:

- output: `controlled_test_output/tier5_10d_20260428_212229/`
- status: `PASS`
- backend: `nest`
- runs: `153 / 153`
- seeds: `42,43,44`
- steps: `720`
- tasks: `delayed_context_cue`, `distractor_gap_context`,
  `hidden_context_recurrence`
- CRA variants: `v1_4_raw`, `external_context_memory_scaffold`,
  `internal_context_memory`, `memory_reset_ablation`,
  `shuffled_memory_ablation`, `wrong_memory_ablation`
- standard baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `small_gru`,
  `stdp_only_snn`
- context controls: `oracle_context`, `stream_context_memory`,
  `shuffled_context`, `memory_reset`, `wrong_context`
- leakage violations: `0` across `5151` checked feedback rows
- internal candidate all accuracy: `1.0` on all repaired tasks
- internal candidate minimum edge versus v1.4 raw CRA:
  `0.4666666666666667`
- internal candidate minimum edge versus external scaffold: `0.0`
- internal candidate minimum edge versus best memory ablation:
  `0.4666666666666667`
- internal candidate minimum edge versus best standard baseline:
  `0.18452380952380965`
- full compact regression:
  `controlled_test_output/tier5_7_20260428_214807/`, status `PASS`

Tier 5.10d can be cited only as internal host-side software-memory evidence. It
shows that the Tier 5.10c capability no longer depends on external
preprocessing. It does not prove native on-chip memory, hardware transfer of
memory, sleep/replay consolidation, or solved catastrophic forgetting.

### Tier 5.10e - Internal Memory Retention Stressor

Command:

```bash
make tier5-10e
```

Smoke:

```bash
make tier5-10e-smoke
```

Latest output:

- `controlled_test_output/tier5_10e_20260428_220316/`

Result:

- status: `PASS`
- backend: NEST
- steps: `960`
- seeds: `42`, `43`, `44`
- tasks: `delayed_context_cue`, `distractor_gap_context`,
  `hidden_context_recurrence`
- expected/observed runs: `153 / 153`
- leakage violations: `0` across `2448` checked feedback rows
- stress profile: `context_gap=48`, `context_period=96`,
  `long_context_gap=96`, `long_context_period=160`,
  `distractor_density=0.85`, `distractor_scale=0.45`,
  `recurrence_phase_len=240`, `recurrence_trial_gap=24`,
  `recurrence_decision_gap=64`
- internal candidate all accuracy: `1.0` on all retention-stress tasks
- internal candidate minimum edge versus v1.4 raw CRA:
  `0.33333333333333337`
- internal candidate minimum edge versus external scaffold: `0.0`
- internal candidate minimum edge versus best memory ablation:
  `0.33333333333333337`
- internal candidate minimum edge versus sign persistence:
  `0.33333333333333337`
- internal candidate minimum edge versus best standard baseline:
  `0.33333333333333337`

Tier 5.10e can be cited only as internal host-side memory-retention evidence.
It shows the Tier 5.10d mechanism survives the first retention stressor. It
does not prove native on-chip memory, hardware transfer of memory,
sleep/replay consolidation, capacity-limited memory, or solved catastrophic
forgetting.

### Tier 5.10f - Memory Capacity / Interference Stressor

Command:

```bash
make tier5-10f
```

Smoke:

```bash
make tier5-10f-smoke
```

Latest output:

- `controlled_test_output/tier5_10f_20260428_224805/`

Result:

- status: `FAIL`
- backend: NEST
- steps: `720`
- seeds: `42`, `43`, `44`
- tasks: `intervening_contexts`, `overlapping_contexts`,
  `context_reentry_interference`
- expected/observed runs: `153 / 153`
- leakage violations: `0` across `1938` checked feedback rows
- internal candidate feature-active steps: `114`
- internal candidate context-memory updates: `121`
- internal candidate minimum all accuracy: `0.25`
- internal candidate minimum edge versus v1.4 raw CRA: `-0.25`
- internal candidate minimum edge versus external single-slot scaffold: `0.0`
- internal candidate minimum edge versus best memory ablation: `-0.5`
- internal candidate minimum edge versus sign persistence: `-0.25`
- internal candidate minimum edge versus best standard baseline: `-0.25`

Tier 5.10f can be cited only as failed noncanonical capacity/interference
stress evidence. It does not invalidate v1.5; it shows the v1.5 single-slot
memory is not enough for intervening contexts, overlap, and context reentry.

### Tier 5.10g - Multi-Slot / Keyed Context-Memory Repair

Command:

```bash
make tier5-10g
```

Smoke:

```bash
make tier5-10g-smoke
```

Latest output:

- `controlled_test_output/tier5_10g_20260428_232844/`

Result:

- status: `PASS`
- backend: NEST
- steps: `720`
- seeds: `42`, `43`, `44`
- tasks: `intervening_contexts`, `overlapping_contexts`,
  `context_reentry_interference`
- expected/observed runs: `171 / 171`
- leakage violations: `0` across `2166` checked feedback rows
- keyed candidate feature-active steps: `114.0`
- keyed candidate context-memory updates: `121.0`
- keyed candidate all accuracy: `1.0` on all three stress tasks
- keyed candidate minimum edge versus v1.4 raw CRA: `0.5`
- keyed candidate minimum edge versus v1.5 single-slot memory:
  `0.33333333333333337`
- keyed candidate minimum edge versus oracle-key scaffold: `0.0`
- keyed candidate minimum edge versus best memory ablation:
  `0.33333333333333337`
- keyed candidate minimum edge versus sign persistence: `0.5`
- keyed candidate minimum edge versus best standard baseline: `0.5`
- compact regression after keyed-memory addition:
  `controlled_test_output/tier5_7_20260428_235507/`

Tier 5.10g can be cited as baseline-frozen internal host-side keyed-memory repair evidence.
It repairs the measured Tier 5.10f single-slot failure under the tested bounded
stress tasks. It does not prove native on-chip memory, sleep/replay,
hardware memory transfer, module routing, compositionality, or general working
memory.

### Tier 5.11a - Sleep/Replay Need Test

Run:

```bash
make tier5-11a-smoke
make tier5-11a
```

Latest output:

- `controlled_test_output/tier5_11a_20260429_004340/`

Result:

- status: `PASS`
- backend: NEST
- steps: `960`
- seeds: `42`, `43`, `44`
- tasks: `silent_context_reentry`, `long_gap_silent_reentry`, `partial_key_reentry`
- expected/observed runs: `171 / 171`
- feedback timing leakage violations: `0`
- v1.6 no-replay minimum accuracy: `0.6086956521739131`
- unbounded keyed minimum accuracy: `1.0`
- oracle scaffold minimum accuracy: `1.0`
- max upper-bound gap versus v1.6 no-replay: `0.3913043478260869`
- max tail upper-bound gap versus v1.6 no-replay: `1.0`
- diagnostic decision: `replay_or_consolidation_needed`

Tier 5.11a can be cited only as a sleep/replay need diagnostic. It proves that
there is now a measured bounded-memory consolidation failure worth testing with
Tier 5.11b, not that replay works. v1.6 remains the frozen current memory
baseline.

### Tier 5.11b - Prioritized Replay / Consolidation Intervention

Run:

```bash
make tier5-11b-smoke
make tier5-11b
```

Latest output:

- `controlled_test_output/tier5_11b_20260429_022048/`

Result:

- status: `FAIL`
- backend: NEST
- steps: `960`
- seeds: `42`, `43`, `44`
- tasks: `silent_context_reentry`, `long_gap_silent_reentry`, `partial_key_reentry`
- expected/observed runs: `162 / 162`
- feedback timing leakage violations: `0`
- replay future violations: `0`
- prioritized replay events/consolidations: `1185 / 1185`
- prioritized minimum all accuracy: `1.0`
- prioritized minimum tail accuracy: `1.0`
- prioritized all/tail gap closure versus unbounded: `1.0 / 1.0`
- no-consolidation writes: `0`
- failed criterion: shuffled replay does not match prioritized tail
- minimum prioritized tail edge versus shuffled: `0.4444444444444444`
- required shuffled-control edge: `0.5`

Tier 5.11b can be cited only as non-promoted replay-intervention evidence. It
shows prioritized replay repairs the measured silent-reentry failure, but it
does not yet prove replay is causally distinct from sham replay opportunity on
partial-key reentry. v1.6 remains the current memory baseline at this point; do not freeze
v1.7 from this bundle.

### Tier 5.11c - Replay Sham-Separation Repair

Run:

```bash
make tier5-11c-smoke
make tier5-11c
```

Latest output:

- `controlled_test_output/tier5_11c_20260429_031427/`

Result:

- status: `FAIL`
- backend: NEST
- steps: `960`
- seeds: `42`, `43`, `44`
- tasks: `silent_context_reentry`, `long_gap_silent_reentry`, `partial_key_reentry`
- expected/observed runs: `189 / 189`
- feedback/replay leakage violations: `0 / 0`
- candidate replay events/consolidations: `1185 / 1185`
- candidate minimum all/tail accuracy: `1.0 / 1.0`
- candidate all/tail gap closure versus unbounded: `1.0 / 1.0`
- minimum tail edge versus shuffled-order replay: `0.40740740740740733`
- minimum tail edge versus wrong-key replay: `0.5555555555555556`
- minimum tail edge versus key-label-permuted, priority-only, no-consolidation controls: `1.0`

Tier 5.11c blocks the narrower priority-specific replay claim because
shuffled-order replay still comes too close. It does not block the broader
correct-binding replay/consolidation hypothesis.

### Tier 5.11d - Generic Replay / Consolidation Confirmation

Run:

```bash
make tier5-11d-smoke
make tier5-11d
make tier5-7
```

Latest output:

- `controlled_test_output/tier5_11d_20260429_041524/`
- compact regression: `controlled_test_output/tier5_7_20260429_050527/`
- baseline lock: `baselines/CRA_EVIDENCE_BASELINE_v1.7.md`

Result:

- status: `PASS`
- backend: NEST
- steps: `960`
- seeds: `42`, `43`, `44`
- tasks: `silent_context_reentry`, `long_gap_silent_reentry`, `partial_key_reentry`
- expected/observed runs: `189 / 189`
- feedback/replay leakage violations: `0 / 0`
- candidate replay events/consolidations: `1185 / 1185`
- candidate minimum all/tail accuracy: `1.0 / 1.0`
- candidate minimum tail delta versus no replay: `1.0`
- candidate all/tail gap closure versus unbounded: `1.0 / 1.0`
- minimum tail edge versus wrong-key replay: `0.5555555555555556`
- minimum tail edge versus key-label-permuted, priority-only, no-consolidation controls: `1.0`

Tier 5.11d promotes host-side correct-binding replay/consolidation as
baseline-frozen software mechanism evidence and freezes v1.7 after compact regression. It does not prove
priority weighting is essential, native/on-chip replay, hardware memory
transfer, composition, routing, or world modeling.


### Tier 5.12a - Predictive Task-Pressure Validation

Run:

```bash
make tier5-12a-smoke
make tier5-12a
```

Latest output:

- `controlled_test_output/tier5_12a_20260429_054052/`

Result:

- status: `PASS`
- matrix: `144 / 144` task-model-seed cells
- feedback leakage violations: `0` across `10044` checked rows
- tasks: `hidden_regime_switching`, `masked_input_prediction`, `event_stream_prediction`, `sensor_anomaly_prediction`
- causal predictive-memory accuracy: `1.0` on all tasks
- max current-reflex accuracy: `0.5393258426966292`
- max sign-persistence accuracy: `0.5649717514124294`
- max wrong/shuffled-target accuracy: `0.5444444444444444`

Tier 5.12a validates predictive task pressure before mechanism work. It is not
CRA predictive coding, full world modeling, language, planning, hardware
prediction, or a v1.8 freeze.

### Tier 5.12b - Internal Predictive Context Mechanism Diagnostic

Run:

```bash
make tier5-12b-smoke
make tier5-12b
```

Latest output:

- `controlled_test_output/tier5_12b_20260429_055923/`

Result:

- status: `FAIL`
- matrix: `162 / 162` NEST task-variant-model-seed cells
- feedback leakage violations: `0`
- candidate predictive-context writes / active decision uses: `570 / 570`
- candidate matched the external predictive scaffold on all tasks
- failed gates: absolute candidate accuracy, tail accuracy, and ablation separation

Interpretation: Tier 5.12b is retained as a failed diagnostic. The predictive
path was active and useful, but wrong-sign context was shown to be a stable
alternate code rather than a destructive sham, so the sham contract needed
repair.

### Tier 5.12c - Predictive Context Sham-Separation Repair

Run:

```bash
make tier5-12c-smoke
make tier5-12c
```

Latest output:

- `controlled_test_output/tier5_12c_20260429_062256/`

Result:

- status: `PASS`
- matrix: `171 / 171` NEST task-variant-model-seed cells
- feedback leakage violations: `0`
- candidate predictive-context writes / active decision uses: `570 / 570`
- candidate accuracy: `1.0` on `event_stream_prediction`
- candidate accuracy: `0.8444444444444444` on `masked_input_prediction`
- candidate accuracy: `1.0` on `sensor_anomaly_prediction`
- minimum candidate tail accuracy: `0.888888888888889`
- minimum edge versus v1.7 reactive CRA: `0.8444444444444444`
- minimum edge versus shuffled/permuted/no-write shams: `0.3388888888888889`
- minimum edge versus shortcut controls: `0.3`
- minimum edge versus best selected external baseline: `0.31666666666666665`

Tier 5.12c is host-side visible predictive-context mechanism evidence. It is
not hidden-regime inference, full world modeling, language, planning, hardware
prediction, hardware scaling, native on-chip learning, compositionality, or
external-baseline superiority. Tier 5.12d is the separate compact-regression
promotion gate.

### Tier 5.12d - Predictive-Context Compact Regression

Run:

```bash
make tier5-12d-smoke
make tier5-12d
```

Latest output:

- `controlled_test_output/tier5_12d_20260429_070615/`
- baseline lock: `baselines/CRA_EVIDENCE_BASELINE_v1.8.md`

Result:

- status: `PASS`
- child checks passed: `6 / 6`
- criteria passed: `6 / 6`
- runtime seconds: `319.63600204200003`
- passed child checks: Tier 1 controls, Tier 2 learning, Tier 3 ablations,
  delayed_cue/hard_noisy_switching smokes, v1.7 replay/consolidation guardrail,
  and compact predictive-context sham separation

Tier 5.12d freezes v1.8 as a bounded host-side visible predictive-context
software baseline. It is not hidden-regime inference, full world modeling,
language, planning, hardware prediction, hardware scaling, native on-chip
learning, compositionality, or external-baseline superiority.

### Tier 5.13 - Compositional Skill Reuse Diagnostic

Run:

```bash
make tier5-13-smoke
make tier5-13
```

Latest output:

- `controlled_test_output/tier5_13_20260429_075539/`

Result:

- status: `PASS`
- matrix cells: `126 / 126`
- feedback leakage violations: `0`
- tasks: `heldout_skill_pair`, `order_sensitive_chain`,
  `distractor_skill_chain`
- seeds: `42`, `43`, `44`
- candidate first-heldout accuracy min: `1.0`
- candidate total heldout accuracy min: `1.0`
- edge versus raw v1.8 first-heldout min: `1.0`
- edge versus best module sham min: `0.7083333333333333`
- edge versus combo memorization min: `1.0`
- edge versus best selected standard baseline min:
  `0.16666666666666663`

Artifacts:

- `tier5_13_results.json`
- `tier5_13_report.md`
- `tier5_13_summary.csv`
- `tier5_13_comparisons.csv`
- `tier5_13_fairness_contract.json`
- `tier5_13_composition.png`
- per-task/per-model/per-seed time-series CSVs

Tier 5.13 is explicit host-side reusable-module composition evidence. It shows
the composition task pressure is real and that a reusable-module scaffold solves
held-out combinations that raw v1.8, combo memorization, composition shams, and
selected external baselines do not. It does not prove native/internal CRA
compositionality, module routing, hardware composition, language, planning, AGI,
or a v1.9 freeze.

### Tier 5.13b - Module Routing / Contextual Gating Diagnostic

Run:

```bash
make tier5-13b-smoke
make tier5-13b
```

Latest output:

- `controlled_test_output/tier5_13b_20260429_121615/`

Result:

- status: `PASS`
- matrix cells: `126 / 126`
- feedback leakage violations: `0 / 11592`
- tasks: `heldout_context_routing`, `distractor_router_chain`,
  `context_reentry_routing`
- seeds: `42`, `43`, `44`
- candidate first-heldout routing accuracy min: `1.0`
- candidate heldout routing accuracy min: `1.0`
- candidate router accuracy min: `1.0`
- pre-feedback route selections: `276`
- edge versus raw v1.8 first-heldout min: `1.0`
- edge versus best routing sham min: `0.375`
- edge versus best selected standard baseline min: `0.45833333333333337`

Artifacts:

- `tier5_13b_results.json`
- `tier5_13b_report.md`
- `tier5_13b_summary.csv`
- `tier5_13b_comparisons.csv`
- `tier5_13b_fairness_contract.json`
- `tier5_13b_routing.png`
- per-task/per-model/per-seed time-series CSVs

Tier 5.13b is explicit host-side contextual routing evidence. It shows a router
scaffold can select the correct learned module before feedback under delayed
context, distractor, and reentry pressure. Raw v1.8 and the CRA router-input
bridge did not solve the first-heldout routing trials, so this authorizes
internal CRA routing/gating work but does not prove native/internal routing,
hardware routing, language, planning, AGI, or a v1.9 freeze.

Tier 5.14 working memory / context binding diagnostic:

```bash
make tier5-14-smoke
make tier5-14
```

Latest output:

```text
controlled_test_output/tier5_14_20260429_165409/
```

Result:

```text
status = PASS
memory/context-binding subsuite = PASS
module-state/routing subsuite = PASS
runtime_seconds = 647.690871625
memory tasks = intervening_contexts, overlapping_contexts, context_reentry_interference
routing tasks = heldout_context_routing, distractor_router_chain, context_reentry_routing
minimum context-memory edge vs best sham = 0.5
minimum context-memory edge vs sign persistence = 0.5
minimum routing edge vs routing-off CRA = 1.0
minimum routing edge vs best routing sham = 0.5
```

Required outputs:

- `tier5_14_results.json`
- `tier5_14_report.md`
- `tier5_14_fairness_contract.json`
- `tier5_14_working_memory_summary.png`
- `memory_context_binding/` traces and summaries
- `module_state_routing/` traces and summaries

Tier 5.14 is noncanonical software diagnostic evidence over frozen v1.9. It
tests whether context/cue memory and delayed module-state routing survive
working-memory pressure and whether reset/shuffle/no-write/random shams lose.
It does not freeze v2.0 by itself and is not hardware/on-chip working memory,
language, planning, AGI, or external-baseline superiority.

Optional Tier 5.14b promotion gate: run only if freezing v2.0 or elevating
working-memory/context-binding into a formal paper-table claim. It should rerun
5.14 plus compact regression and keep all shams/leakage checks green.

## Tier 5.15: Spike Encoding / Temporal Code

Run:

```bash
make tier5-15
```

Smoke:

```bash
make tier5-15-smoke
```

Latest output:

```text
controlled_test_output/tier5_15_20260429_135924/
```

Result:

```text
status = PASS
expected_runs = observed_runs = 540
spike_trace_artifacts = 60
encoding_metadata_artifacts = 60
good_temporal_row_count = 9
nonfinance_good_temporal_row_count = 3
```

Required outputs:

- `tier5_15_results.json`
- `tier5_15_report.md`
- `tier5_15_summary.csv`
- `tier5_15_comparisons.csv`
- `tier5_15_fairness_contract.json`
- `tier5_15_temporal_edges.png`
- `tier5_15_encoding_matrix.png`
- sampled `*_spike_trace.csv`
- per-task/per-encoding `*_encoding_metadata.json`
- per-task/per-encoding/per-model/per-seed `*_timeseries.csv`

Tier 5.15 is noncanonical software diagnostic evidence. It shows that latency,
burst, and temporal-interval spike timing can carry task-relevant information in
the current diagnostic, with time-shuffle and rate-only controls losing on the
successful temporal cells. It does not freeze v2.0, does not prove hardware or
custom-C/on-chip temporal coding, and does not prove hard_noisy_switching
temporal superiority.

## Tier 5.16: Neuron Model / Parameter Sensitivity

Run:

```bash
make tier5-16
```

Smoke:

```bash
make tier5-16-smoke
```

Latest output:

```text
controlled_test_output/tier5_16_20260429_142647/
```

Result:

```text
status = PASS
backend = nest
expected_runs = observed_runs = 66
aggregate_cells = 33
functional_cell_count = 33
functional_cell_fraction = 1.0
default_min_tail_accuracy = 0.8
collapse_count = 0
propagation_failures = 0
sim_run_failures = 0
summary_read_failures = 0
synthetic_fallbacks = 0
response_probe_monotonic_fraction = 1.0
```

Required outputs:

- `tier5_16_results.json`
- `tier5_16_report.md`
- `tier5_16_summary.csv`
- `tier5_16_comparisons.csv`
- `tier5_16_parameter_propagation.csv`
- `tier5_16_lif_response_probe.csv`
- `tier5_16_protocol.json`
- `tier5_16_robustness_matrix.png`
- `tier5_16_lif_response_probe.png`
- per-task/per-variant/per-seed `*_timeseries.csv`

Tier 5.16 is noncanonical NEST software diagnostic evidence. It shows that the
current CRA path remains functional across threshold, membrane-tau, refractory,
capacitance, and synaptic-tau LIF variants, with audited parameter propagation
and direct monotonic LIF current-response checks. It does not freeze v2.0, does
not prove SpiNNaker hardware or custom-C/on-chip neuron-model robustness, and
does not prove adaptive-LIF/Izhikevich robustness.

- `tier5_unsupervised_representation.py`: Tier 5.17 failed noncanonical pre-reward representation diagnostic; no-label/no-reward exposure, offline probes, and strict controls.
- `tier5_pre_reward_representation_failure_analysis.py`: Tier 5.17b passed noncanonical failure-analysis diagnostic; classifies the failed 5.17 bundle and routes the next repair to intrinsic predictive / MI-style preexposure without promoting reward-free representation learning.
- `tier5_intrinsic_predictive_preexposure.py`: Tier 5.17c failed noncanonical intrinsic predictive preexposure diagnostic; zero-label/zero-reward exposure plus target/domain/time shams, held-out episode probes, and failed promotion gates.
- `tier5_predictive_binding_repair.py`: Tier 5.17d passed bounded noncanonical predictive-binding repair diagnostic; zero-label/zero-reward exposure plus held-out ambiguous episode probes, target-shuffled/wrong-domain/history/reservoir/STDP-only controls, and bounded claim gates.
- `tier5_predictive_binding_compact_regression.py`: Tier 5.17e passed predictive-binding promotion/regression gate; reruns v1.8 compact regression, v1.9 composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d predictive-binding guardrails before freezing v2.0.
- `tier5_self_evaluation_metacognition.py`: Tier 5.18 passed noncanonical self-evaluation/metacognitive-monitoring diagnostic; tests calibrated pre-feedback uncertainty, OOD/error prediction, confidence-gated intervention, monitor-only, random, shuffled, disabled, anti-confidence, and oracle controls over frozen v2.0.
- `tier5_self_evaluation_compact_regression.py`: Tier 5.18c passed self-evaluation promotion/regression gate; reruns the full v2.0 compact gate and Tier 5.18 guardrail before freezing v2.1.
- `tier5_macro_eligibility_v2_1_recheck.py`: Tier 5.9c failed noncanonical macro-eligibility v2.1 recheck; v2.1 guardrails passed, but macro residual did not beat trace ablations.
- `tier4_20a_hardware_transfer_audit.py`: Tier 4.20a passed engineering audit; maps v2.1 mechanisms to chunked-host, hybrid, and on-chip readiness without making a hardware claim.
- `tier4_20b_v2_1_hardware_probe.py`: Tier 4.20b one-seed v2.1 chunked SpiNNaker bridge probe; prepares/runs/ingests JobManager artifacts, delegates low-level hardware execution to the proven Tier 4.16 chunked-host runner, and keeps macro eligibility excluded.
- `tier4_20b_sim_preflight.py`: cheap source/simulation preflight for Tier 4.20b; runs source prepare smoke plus local NEST step-vs-chunked parity before hardware.
- `tier4_20c_v2_1_hardware_repeat.py`: Tier 4.20c three-seed v2.1 chunked SpiNNaker bridge repeat; prepares/runs/ingests JobManager artifacts for seeds `42`, `43`, and `44`, delegates low-level hardware execution to the proven Tier 4.16 chunked-host runner, keeps macro eligibility excluded, and treats prior Tier 4.20b evidence as a local registry/prerequisite rather than a required EBRAINS upload artifact.
- `tier4_21a_keyed_context_memory_bridge.py`: Tier 4.21a targeted v2 keyed-context-memory hardware bridge probe; prepares/runs/ingests a one-seed JobManager capsule for `context_reentry_interference`, schedules a causal host-side keyed-memory-transformed input stream through chunked `StepCurrentSource`, reads binned spikes, replays the host learner, and compares keyed memory against slot-reset/slot-shuffle/wrong-key ablations. A local-bridge pass is source/logic preflight only; a returned `run-hardware` pass would be keyed-memory bridge evidence, not native/on-chip memory or custom C.
- `tier4_22a_custom_runtime_contract.py`: Tier 4.22a custom/hybrid on-chip runtime contract; reads the passed Tier 4.20c and Tier 4.21a manifests, declares constrained-NEST plus sPyNNaker mapping preflight before further expensive hardware, assigns host/hybrid/on-chip state ownership, and exports staged parity, runtime, and memory/resource gates. This is engineering contract evidence only, not custom-C or continuous/on-chip hardware evidence.
- `tier4_22a0_spinnaker_constrained_preflight.py`: Tier 4.22a0 executable local pre-hardware gate; imports NEST/PyNN/sPyNNaker, runs a constrained PyNN/NEST `StepCurrentSource` scheduled-input smoke with binned readback, checks the bridge source for static hardware-safe PyNN compliance, records bounded resource/fixed-point checks, and runs the custom C runtime host tests. This is transfer-risk reduction only, not real hardware evidence.
- `tier4_22b_continuous_transport_scaffold.py`: Tier 4.22b continuous transport scaffold; runs reference task streams with one scheduled-input `sim.run` per task/seed and binned spike readback. Learning is disabled to isolate transport before persistent state and reward/plasticity gates. Supports `local`, `prepare`, `run-hardware`, and `ingest` modes.
- `tier4_22c_persistent_state_scaffold.py`: Tier 4.22c persistent custom-C state scaffold; runs custom C host tests and static source checks proving bounded keyed context slots, no-leak pending horizons, readout state, decision/reward counters, reset semantics, and no dynamic allocation inside `state_manager.c`. This is state-ownership groundwork for full custom/on-chip CRA, not hardware or learning evidence.
- `tier4_22d_reward_plasticity_scaffold.py`: Tier 4.22d custom-C reward/plasticity scaffold; runs custom C host tests and static source checks proving synaptic eligibility traces, trace-gated dopamine, fixed-point trace decay, signed one-shot dopamine, and runtime-owned readout reward updates. This is local scaffold evidence, not hardware or continuous-learning parity.
- `tier4_22e_local_learning_parity.py`: Tier 4.22e local continuous-learning parity scaffold; compares the custom-C fixed-point delayed-readout equations against a floating reference on delayed-credit streams, verifies no future-target storage in pending horizons, and checks a no-pending ablation. This is local minimal parity evidence, not hardware or full CRA parity.
- `tier4_22f0_custom_runtime_scale_audit.py`: Tier 4.22f0 custom-runtime scale-readiness audit; keeps PyNN/sPyNNaker as the primary supported hardware layer, audits the custom-C sidecar for scalable data-structure/readback blockers, and blocks direct custom-runtime hardware learning until event-indexed spike delivery, lazy/active eligibility traces, and compact state readback are repaired. This is audit evidence, not hardware or scale-ready evidence.
- `tier4_22g_event_indexed_trace_runtime.py`: Tier 4.22g local custom-C optimization gate; verifies pre-indexed outgoing spike delivery plus active-trace-only decay/dopamine, repairs the first three Tier 4.22f0 scale blockers locally, and keeps hardware learning blocked until compact state readback and command/build acceptance pass.
- `tier4_22h_compact_readback_acceptance.py`: Tier 4.22h compact-readback/build-readiness gate; verifies `CMD_READ_STATE` schema v1, host-tests compact state packing, records local `.aplx` build availability honestly, checks official Spin1API callback and packed SARK-SDP compatibility, and keeps board-load/command round-trip as the next hardware-facing gate.
- `tier4_22i_custom_runtime_roundtrip.py`: Tier 4.22i custom-runtime board round-trip smoke; prepares and refreshes the minimal `ebrains_jobs/cra_422r` EBRAINS upload folder, runs local `main.c` syntax/callback guards plus `host_interface.c` SARK-SDP guards, official SARK router guards, official SDP command-header guards, official `spinnaker_tools.mk` build-recipe guards, nested object-directory guards, and automatic target-acquisition checks, and in `run-hardware` mode builds/loads the custom `.aplx`, sends `CMD_READ_STATE`, and validates schema-v1 state mutation on real SpiNNaker. Prepared output is not hardware evidence. Returned EBRAINS failures before the `cra_422r` pass are preserved in `controlled_test_output/` and documented in `docs/SPINNAKER_EBRAINS_RUNBOOK.md`.
- `tier4_22j_minimal_custom_runtime_learning.py`: Tier 4.22j minimal custom-runtime closed-loop learning smoke; prepares and refreshes `ebrains_jobs/cra_422s`, depends on the Tier 4.22i board-roundtrip pass, guards `CMD_SCHEDULE_PENDING` and `CMD_MATURE_PENDING` in source and bundle, and in `run-hardware` mode schedules one pending delayed-credit decision, matures it, and validates pending/reward/readout state changes through compact `CMD_READ_STATE`. The first returned hardware run is ingested at `controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/`; raw status was a false-fail from a zero-value evaluator bug, while returned hardware data satisfy the pass criteria. This is one minimal chip-owned pending/readout update only, not full CRA task learning or speedup evidence.
- `tier4_22l_custom_runtime_learning_parity.py`: Tier 4.22l tiny custom-runtime learning parity; generates a four-update signed s16.15 local readout reference, prepares and refreshes `ebrains_jobs/cra_422t`, guards the fixed-point prediction/update equations in source and bundle, supports ingest of returned EBRAINS files, and in `run-hardware` mode schedules/matures four pending horizons with explicit due-timestep maturation. The returned hardware pass is ingested at `controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_hardware_pass_ingested/`; prediction, readout weight, and readout bias raw deltas were all `0`, ending with `pending_created=4`, `pending_matured=4`, `reward_events=4`, `active_pending=0`, and final weight/bias raw `-4096`. This is tiny fixed-point custom-runtime parity only, not full CRA task learning or speedup evidence.
- `tier4_22m_custom_runtime_task_micro_loop.py`: Tier 4.22m minimal custom-runtime task micro-loop; generates a 12-event signed fixed-pattern s16.15 task reference, prepares and refreshes `ebrains_jobs/cra_422u`, guards the pending/readout command surface, supports ingest of returned EBRAINS files, and in `run-hardware` mode scores pre-update prediction signs while maturing one pending horizon per event. Local/prepared outputs passed at `controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_local/` and `controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_prepared/`; returned EBRAINS hardware passed after ingest at `controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_hardware_pass_ingested/` with observed accuracy `0.9166666667`, tail accuracy `1.0`, final `readout_weight_raw=32256`, final `readout_bias_raw=0`, and all raw deltas `0`. This is a minimal fixed-pattern task micro-loop only, not full CRA task learning or speedup evidence.
- `tier4_22n_delayed_cue_micro_task.py`: Tier 4.22n tiny delayed-cue custom-runtime micro-task; generates a 12-event signed pending-queue s16.15 task reference with `pending_gap_depth=2`, prepares and refreshes `ebrains_jobs/cra_422v`, guards the same pending/readout command surface, supports ingest of returned EBRAINS files, and in `run-hardware` mode checks rolling pending depth, delayed oldest-first maturation, pre-update prediction signs, and raw fixed-point parity. Local/prepared outputs passed at `controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_local/` and `controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_prepared/`; returned EBRAINS hardware passed after ingest at `controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/` with observed accuracy `0.8333333333`, tail accuracy `1.0`, max pending depth `3`, final `readout_weight_raw=30720`, final `readout_bias_raw=0`, and all raw deltas `0`. This is a tiny delayed-cue-like micro-task only, not full CRA task learning or speedup evidence.
- `tier4_22o_noisy_switching_micro_task.py`: Tier 4.22o tiny noisy-switching custom-runtime micro-task; generates a 14-event signed noisy-switching s16.15 task reference with `pending_gap_depth=2`, a rule switch, and two label-noise events, prepares and refreshes `ebrains_jobs/cra_422x`, guards the same pending/readout command surface, supports ingest of returned EBRAINS files, and in `run-hardware` mode checks rolling pending depth, delayed oldest-first maturation, pre-update prediction signs, and raw fixed-point parity. Local/prepared outputs passed at `controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_local/` and `controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_prepared/`; reference accuracy is `0.7857142857`, tail accuracy is `1.0`, max pending depth is `3`, final `readout_weight_raw=-48768`, and final `readout_bias_raw=-1536`. The first returned EBRAINS attempt, `controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_overflow_fail_ingested/`, is preserved as a noncanonical custom-runtime arithmetic failure: hardware target/build/load/schedule/mature worked, but signed fixed-point multiplication overflowed at the regime switch. The repaired `cra_422x` run passed after ingest at `controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/` with board `10.11.210.25`, selected core `(0,0,4)`, 44/44 criteria passed, every prediction/weight/bias raw delta `0`, observed accuracy `0.7857142857`, tail accuracy `1.0`, final `readout_weight_raw=-48768`, and final `readout_bias_raw=-1536`. This is a tiny noisy-switching micro-task only, not full CRA hard_noisy_switching or speedup evidence.
- `tier4_22p_reentry_micro_task.py`: Tier 4.22p tiny A-B-A reentry custom-runtime micro-task; generates a 30-event signed A-B-A reentry s16.15 task reference with `pending_gap_depth=2`, prepares and refreshes `ebrains_jobs/cra_422y`, guards the same pending/readout command surface, supports ingest of returned EBRAINS files, and in `run-hardware` mode checks rolling pending depth, delayed oldest-first maturation, pre-update prediction signs, reentry/tail metrics, and raw fixed-point parity. Local/prepared outputs passed at `controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_local/` and `controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_prepared/`; returned EBRAINS hardware passed after ingest at `controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_hardware_pass_ingested/` with board `10.11.222.17`, selected core `(0,0,4)`, 44/44 criteria passed, every prediction/weight/bias raw delta `0`, observed accuracy `0.8666666667`, tail accuracy `1.0`, max pending depth `3`, final `readout_weight_raw=30810`, and final `readout_bias_raw=-1`. This is tiny A-B-A reentry micro-task evidence only, not full recurrence, v2.1 transfer, speedup evidence, or final autonomy.
- `tier4_22q_integrated_v2_bridge_smoke.py`: Tier 4.22q tiny integrated v2 bridge custom-runtime smoke; generates a 30-event signed stream from a host-side keyed-context plus route-state bridge, prepares and refreshes `ebrains_jobs/cra_422z`, guards bridge metadata plus the same pending/readout command surface, supports ingest of returned EBRAINS files, and in `run-hardware` mode checks rolling pending depth, delayed oldest-first maturation, pre-update prediction signs, bridge/tail metrics, and raw fixed-point parity. Local/prepared outputs passed at `controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_local/` and `controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_prepared/`; returned EBRAINS hardware passed after ingest at `controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_hardware_pass_ingested/` with board `10.11.236.65`, selected core `(0,0,4)`, 47/47 remote criteria plus ingest criterion passed, every prediction/weight/bias raw delta `0`, observed accuracy `0.9333333333`, tail accuracy `1.0`, context updates `9`, route updates `9`, max keyed slots `3`, max pending depth `3`, final `readout_weight_raw=32768`, and final `readout_bias_raw=0`. This is tiny integrated host-v2/custom-runtime bridge evidence only, not native/on-chip v2 memory/routing, full CRA task learning, speedup evidence, or final autonomy.
- `tier4_22k_spin1api_event_discovery.py`: Tier 4.22k EBRAINS Spin1API event-symbol discovery; prepares `ebrains_jobs/cra_422k`, inspects the actual EBRAINS toolchain/header image, writes a header inventory, and compiles callback probes for `TIMER_TICK`, `SDP_PACKET_RX`, official multicast receive symbols, legacy guessed symbols, and related constants. This is build-image/toolchain discovery only, not board execution or learning evidence.

- `tier4_22r_native_context_state_smoke.py`: Tier 4.22r tiny native context-state custom-runtime smoke. This is the first custom-runtime gate where the host no longer sends the full scalar bridge feature. Instead it writes bounded keyed context slots with `CMD_WRITE_CONTEXT`, then sends key+cue+delay with `CMD_SCHEDULE_CONTEXT_PENDING`; the runtime retrieves context, computes `feature=context*cue`, schedules pending credit, and matures delayed targets through the fixed-point readout path. Local/prepared outputs passed at `controlled_test_output/tier4_22r_20260501_native_context_state_smoke_local/` and `controlled_test_output/tier4_22r_20260501_native_context_state_smoke_prepared/`, preparing `ebrains_jobs/cra_422aa` and command `cra_422aa/experiments/tier4_22r_native_context_state_smoke.py --mode run-hardware --output-dir tier4_22r_job_output`. Returned EBRAINS artifacts passed after ingest at `controlled_test_output/tier4_22r_20260501_native_context_state_smoke_hardware_pass_ingested/`: board `10.11.237.25`, selected core `(0,0,4)`, `58/58` remote criteria plus ingest criterion, all raw deltas `0`, context writes `9`, context reads `30`, tail accuracy `1.0`, final `readout_weight_raw=32752`, final `readout_bias_raw=-16`. Tiny native context-state evidence only.

- `tier4_22s_native_route_state_smoke.py`: Tier 4.22s tiny native route-state custom-runtime smoke. This is the next native state primitive after Tier 4.22r: the host writes keyed context with `CMD_WRITE_CONTEXT`, writes chip-owned route state with `CMD_WRITE_ROUTE`, then sends key+cue+delay with `CMD_SCHEDULE_ROUTED_CONTEXT_PENDING`; the runtime retrieves context and route, computes `feature=context*route*cue`, schedules pending credit, and matures delayed targets through the fixed-point readout path. Local/prepared outputs passed at `controlled_test_output/tier4_22s_20260501_native_route_state_smoke_local/` and `controlled_test_output/tier4_22s_20260501_native_route_state_smoke_prepared/`, preparing `ebrains_jobs/cra_422ab` and command `cra_422ab/experiments/tier4_22s_native_route_state_smoke.py --mode run-hardware --output-dir tier4_22s_job_output`. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass. Tiny native route-state evidence only.
  Returned EBRAINS artifacts passed after ingest correction at `controlled_test_output/tier4_22s_20260501_native_route_state_smoke_hardware_pass_ingested/`: raw remote status was `fail` due to the runner checking `route_writes` in final `CMD_READ_ROUTE`, but route writes are proven by acknowledged `CMD_WRITE_ROUTE` row counters (`9`). Board `10.11.237.89`, selected core `(0,0,4)`, build/load pass, all `30` rows acknowledged, final route reads `31`, all raw deltas `0`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`. Tiny native route-state evidence only.

- `tier4_22t_native_keyed_route_state_smoke.py`: Tier 4.22t tiny native keyed route-state custom-runtime smoke. This is the next native state primitive after Tier 4.22s: the host writes keyed context with `CMD_WRITE_CONTEXT`, writes keyed route slots with `CMD_WRITE_ROUTE_SLOT`, then sends key+cue+delay with `CMD_SCHEDULE_KEYED_ROUTE_CONTEXT_PENDING`; the runtime retrieves context and route by key, computes `feature=context[key]*route[key]*cue`, schedules pending credit, and matures delayed targets through the fixed-point readout path. Local/prepared outputs passed at `controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_local/` and `controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_prepared/`, preparing `ebrains_jobs/cra_422ac` and command `cra_422ac/experiments/tier4_22t_native_keyed_route_state_smoke.py --mode run-hardware --output-dir tier4_22t_job_output`. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass. Tiny native keyed route-state evidence only.
  Returned EBRAINS artifacts passed at `controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_hardware_pass_ingested/`: raw remote status was `pass`, board `10.11.235.25`, selected core `(0,0,4)`, build/load pass, all `30` rows acknowledged, route-slot writes `15`, active route slots `3`, route-slot hits `33`, route-slot misses `0`, all raw deltas `0`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`. Tiny native keyed route-state evidence only.

- `tier4_22u_native_memory_route_state_smoke.py`: Tier 4.22u tiny native memory-route custom-runtime smoke. This is the next native state primitive after Tier 4.22t: the host writes keyed context with `CMD_WRITE_CONTEXT`, keyed route slots with `CMD_WRITE_ROUTE_SLOT`, and keyed memory/working-state slots with `CMD_WRITE_MEMORY_SLOT`, then sends key+cue+delay with `CMD_SCHEDULE_MEMORY_ROUTE_CONTEXT_PENDING`; the runtime retrieves context, route, and memory by key, computes `feature=context[key]*route[key]*memory[key]*cue`, schedules pending credit, and matures delayed targets through the fixed-point readout path. Local/prepared outputs passed at `controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_local/` and `controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_prepared/`, preparing `ebrains_jobs/cra_422ad` and command `cra_422ad/experiments/tier4_22u_native_memory_route_state_smoke.py --mode run-hardware --output-dir tier4_22u_job_output`. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass. Tiny native memory-route evidence only.
  Returned EBRAINS artifacts passed at `controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_hardware_pass_ingested/`: raw remote status was `pass`, board `10.11.235.89`, selected core `(0,0,4)`, build/load pass, all `30` context/route-slot/memory-slot/schedule/mature rows acknowledged, route-slot writes/hits/misses `15/33/0`, memory-slot writes/hits/misses `15/33/0`, active route/memory slots `3/3`, all feature/context/route/memory/prediction/weight/bias raw deltas `0`, observed accuracy `0.9666666667`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`. Tiny native memory-route evidence only.

- `tier4_22v_native_memory_route_reentry_composition_smoke.py`: Tier 4.22v tiny native memory-route reentry/composition custom-runtime smoke. This keeps the Tier 4.22u command surface but hardens the task: four keyed context/route/memory slots, independent updates, interleaved recalls, and reentry pressure while the runtime computes `feature=context[key]*route[key]*memory[key]*cue` from key+cue before delayed-credit scheduling. Local/prepared outputs passed at `controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_local/` and `controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_prepared/`, preparing `ebrains_jobs/cra_422ae` and command `cra_422ae/experiments/tier4_22v_native_memory_route_reentry_composition_smoke.py --mode run-hardware --output-dir tier4_22v_job_output`. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass. Tiny harder native memory-route reentry/composition evidence only.
  Returned EBRAINS artifacts passed at `controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/`: raw remote status was `pass`, board `10.11.240.153`, selected core `(0,0,4)`, build/load pass, all `48` context/route-slot/memory-slot/schedule/mature rows acknowledged, route-slot writes/hits/misses `21/52/0`, memory-slot writes/hits/misses `21/52/0`, active route/memory slots `4/4`, all feature/context/route/memory/prediction/weight/bias raw deltas `0`, observed accuracy `0.9375`, tail accuracy `1.0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`. Tiny harder native memory-route reentry/composition evidence only.

- `tier4_22w_native_decoupled_memory_route_composition_smoke.py`: Tier 4.22w tiny native decoupled memory-route composition custom-runtime smoke. This adds `CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING` after the Tier 4.22v same-key memory-route reentry/composition hardware pass. The host writes keyed context, keyed route slots, and keyed memory/working-state slots, then schedules with independent `context_key`, `route_key`, `memory_key`, `cue`, and `delay` so the runtime computes `feature=context[context_key]*route[route_key]*memory[memory_key]*cue` on chip. Local/prepared outputs passed at `controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_local_profiled/` and `controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared_profiled/`; returned EBRAINS artifacts passed at `controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/` with board `10.11.236.9`, selected core `(0,0,4)`, `90/90` criteria, all raw deltas `0`, observed accuracy `0.958333`, tail accuracy `1.0`, active context/route/memory slots `4/4/4`, and final readout `32768/0`. Tiny independent-key native memory-route composition evidence only, not full native v2.1 or full CRA task learning.
- `tier4_22x_compact_v2_bridge_decoupled_smoke.py`: Tier 4.22x compact v2 bridge over native decoupled state primitive. The host maintains a bounded v2-style state bridge (context slots, route table, memory slots), selects decoupled keys per event, writes state to the chip, and schedules via `CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING`. The chip performs lookup, feature composition, pending queue, prediction, maturation, and readout update. No new command surface; reuses `RUNTIME_PROFILE=decoupled_memory_route`. 48-event structured stream with regime-like switching, reentry, and composition. Modes: `local`, `prepare`, `run-hardware`, `ingest`. Local output passed at `controlled_test_output/tier4_22x_20260501_compact_v2_bridge_decoupled_smoke_local/`; prepared output passed at `controlled_test_output/tier4_22x_20260501_compact_v2_bridge_decoupled_smoke_prepared/`; returned EBRAINS artifacts passed after ingest at `controlled_test_output/tier4_22x_20260501_compact_v2_bridge_decoupled_smoke_hardware_pass_ingested/` with board `10.11.236.73`, selected core `(0,0,4)`, 89 remote criteria plus 1 ingest criterion, all raw deltas `0`, observed accuracy `0.958333`, and tail accuracy `1.0`. Claim boundary: bounded host-side v2 bridge driving native decoupled primitive only; not full native v2.1, not predictive binding, not self-evaluation, not continuous runtime, not speedup evidence.

- `tier4_23a_continuous_local_reference.py`: Tier 4.23a continuous / stop-batching parity local reference. Runs a local fixed-point continuous event-loop reference and compares it against the chunked 4.22x reference. The 48-event signed delayed-cue stream executes autonomously for 50 timesteps (48 events + 2 gap drain) with zero host interventions. Local output passed at `controlled_test_output/tier4_23a_20260501_continuous_local_reference/` with 21/21 criteria, accuracy `0.958333`, tail accuracy `1.0`, max pending depth `3`, and all feature/prediction/weight/bias raw deltas `0`. Local reference evidence only; not hardware evidence, not full continuous on-chip learning, not speedup evidence.
- `tier4_23c_continuous_hardware_smoke.py`: **HARDWARE PASS — INGESTED** — Tier 4.23c one-board hardware continuous smoke. Board `10.11.235.9`, core `(0,0,4)`. 22/22 run-hardware criteria + 15/15 ingest criteria passed. Pre-writes state slots, uploads 48-event schedule, runs `CMD_RUN_CONTINUOUS(learning_rate=0.25)`, pauses, reads back. Final readout `32768/0` exact match with local reference. Decisions/rewards/pending all `48`, active_pending `0`. Upload bundle `ebrains_jobs/cra_423b`. Evidence at `controlled_test_output/tier4_23c_20260501_hardware_pass_ingested/`.

- `tier4_24_custom_runtime_resource_characterization.py`: **PASS (16/16)** — Tier 4.24 custom runtime resource characterization. Measures the actual resource envelope of the continuous path versus chunked 4.22x. Key findings: 64 commands vs 134 chunked (52.2% reduction), 2647 bytes payload vs 4099 chunked (35.4% reduction), load time 2.187s, task time 4.327s, DTCM estimate 6372 bytes, max pending depth 3, max schedule entries 64. Evidence at `controlled_test_output/tier4_24_20260501_resource_characterization/`.
- `tier4_27a_four_core_distributed_smoke.py`: **HARDWARE PASS — INGESTED** — Tier 4.27a four-core runtime characterization. Board `10.11.194.65`, cores 4/5/6/7. 38/38 run-hardware + 38/38 ingest criteria. Schema v2 readback validated: lookup_requests=144, lookup_replies=144, stale_replies=0, timeouts=0. Final readout `32768/0`. Evidence at `controlled_test_output/tier4_27a_20260502_pass_ingested/`. Four-core SDP scaffold with instrumentation counters.
- `tier4_27d_mcpl_feasibility.py`: **PASS (9/9)** — Tier 4.27d MCPL inter-core lookup compile-time feasibility. Validates MCPL key packing/unpacking, send_request/send_reply payload capture, receive extraction, and official Spin1API symbol compile. All four profile .aplx images build with MCPL code included. learning_core ITCM=12,448 bytes. Local compile-time evidence only; not hardware evidence, not full protocol integration.
- `tier4_27e_two_core_mcpl_smoke.py`: **PASS (9/9)** — Tier 4.27e two-core MCPL round-trip smoke. Local build and wiring validation: MCPL wired into `_send_lookup_request` and `_send_lookup_reply`, `mcpl_lookup_callback` routes to `cra_state_mcpl_lookup_receive`, `cra_state_mcpl_init` sets up router entries per core role. context_core ITCM=11,240 bytes; learning_core ITCM=12,960 bytes. Local build evidence only; not hardware evidence.
- `tier4_27f_three_core_mcpl_smoke.py`: **PASS (11/11)** — Tier 4.27f three-state-core MCPL lookup smoke. Local build and wiring validation for all four profiles with MCPL enabled. Learning core router mask broadened to 0xFFFF0000 to catch context/route/memory replies via single entry. context_core=11,240B, route_core=11,272B, memory_core=11,272B, learning_core=12,960B. Local build evidence only; not hardware evidence.
- `tier4_27g_sdp_vs_mcpl_comparison.py`: **PASS (12/12)** — Tier 4.27g SDP-vs-MCPL protocol comparison. Source-code-based analysis: MCPL reduces per-lookup round-trip from 54 bytes (SDP) to 16 bytes (71% reduction). For 48-event schedule, inter-core lookup traffic drops from ~8,064 bytes (SDP) to ~2,304 bytes (MCPL). Latency improves from ~5-20 us monitor-bound (SDP) to ~0.5-2 us hardware-router (MCPL). MCPL requires 4 router entries vs 0 for SDP, but scales via parallel hardware routing rather than monitor-processor bottleneck. Recommendation: make MCPL the default inter-core lookup data plane for Tier 4.28+; keep SDP as fallback until MCPL hardware smoke passes. Pure analysis evidence; no hardware claim.
- `tier4_28a_four_core_mcpl_repeatability.py`: **PREPARED** — Tier 4.28a four-core MCPL repeatability package. Builds all four runtime profiles with `USE_MCPL_LOOKUP=1`, verifies ITCM sizes (context=11,240B, route=11,272B, memory=11,272B, learning=12,960B), and creates EBRAINS upload package `cra_428b` for three-seed hardware repeatability (seeds 42, 43, 44). Modes: `local` (build validation), `prepare` (package creation), `run-hardware` (four-core distributed execution), `ingest` (result comparison). First upload failed due to missing `run-hardware` argparse choice; repaired in runner revision 0002. Hardware execution pending EBRAINS/JobManager. If all three seeds pass: ingest and freeze `CRA_NATIVE_RUNTIME_BASELINE_v0.1`.
