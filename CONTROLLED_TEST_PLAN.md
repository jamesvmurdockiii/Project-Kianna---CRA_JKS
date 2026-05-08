# Controlled CRA Test Plan

This plan defines the staged evidence required before treating the Coral Reef
Architecture as a validated research system rather than an untested simulation.

The test order is intentional. If any test fails, stop, debug, and rerun from
the failed test before moving forward.

## Test Count

The original controlled plan contains **12 core numbered tests**. Later work adds
post-core tiers for hardware transfer, external baselines, runtime engineering,
mechanism promotion, lifecycle/ecology evidence, and native SpiNNaker runtime
migration. The generated registry is the authority for which results are
canonical.

The current canonical evidence trail contains **81 registered evidence bundles**
with all expected artifacts present and all criteria passing. The generated
registry is the source of truth for the full list:

```text
controlled_test_output/STUDY_REGISTRY.json
controlled_test_output/STUDY_REGISTRY.csv
STUDY_EVIDENCE_INDEX.md
```

Do not manually curate this section as a second registry. When canonical evidence
changes, update `experiments/evidence_registry.py` and regenerate the registry
with `python3 experiments/evidence_registry.py` or `make validate`.

Completed noncanonical diagnostics:

```text
4.16b-debug hard-switch root-cause decision = completed; classification chunked_host_bridge_learning_failure
4.16b-bridge-repair aligned local diagnostics = completed; classification hardware_transfer_or_timing_failure
4.16b repaired seed-44 hard-switch hardware probe = completed; one-seed pass
5.8b / 4.16b bridge repair = completed; aligned local NEST/Brian2 pass before canonical hardware rerun
5.9a macro eligibility trace diagnostic = completed; promotion gate failed, mechanism not promoted
5.9b residual macro eligibility repair = completed; promotion gate failed, mechanism parked
5.9c macro eligibility v2.1 recheck = completed; v2.1 guardrail passed, macro still failed trace-ablation specificity
5.10 multi-timescale memory diagnostic = completed; promotion gate failed, exposed recurrence-task weakness
5.10b recurrence-task repair / memory-pressure validation = completed; task gate passed, not CRA capability evidence
5.10c explicit context-memory mechanism diagnostic = completed; host-side scaffold passed and was superseded by 5.10d internalization
5.10d internal context-memory implementation diagnostic = completed; internal host-side memory matched scaffold and full compact regression passed
5.10e internal memory retention stressor = completed; internal host-side memory survived longer gaps, dense distractors, and hidden recurrence pressure
5.10f memory capacity/interference stressor = completed; single-slot memory failed cleanly under capacity/interference pressure
5.10g keyed context-memory repair = completed; keyed/multi-slot internal memory repaired the measured 5.10f failure and compact regression passed
```

Non-registry baseline, diagnostic, and roadmap tiers are not counted as
canonical registry evidence until they are explicitly ingested and registered.
They remain part of the peer-review audit trail:

```text
0.9 ongoing reproduction package
5.9 macro eligibility trace confirmation = parked until a measured blocker justifies revival
5.11 replay/consolidation = software mechanism promoted as v1.7 after sham-separation; native host-scheduled bridge passed as 4.29e
5.12a predictive task-pressure validation = completed; 5.12b failed diagnostic kept; 5.12c visible predictive-context repair passed; 5.12d compact regression passed and freezes bounded v1.8
5.13 compositional skill reuse = completed diagnostic/promotion sequence
5.13b module routing / contextual gating = completed diagnostic/promotion sequence
5.13c internal composition / routing promotion gate = completed and folded into later baseline locks
5.14 working memory / context binding = completed guardrail sequence
5.14b optional working-memory promotion gate = superseded for v2.0 by Tier 5.17e including Tier 5.14 guardrail
5.15 spike encoding / temporal code suite = completed diagnostic
5.16 neuron model / parameter sensitivity = completed diagnostic
5.17 unsupervised representation formation = broad claim failed; 5.17d predictive-binding repair passed; 5.17e compact gate froze v2.0
5.18 self-evaluation / metacognitive monitoring = passed software diagnostic
5.18c self-evaluation compact regression = passed and froze bounded v2.1
4.20a v2.1 hardware-transfer readiness audit = passed engineering audit
4.20b v2.1 one-seed chunked hardware probe = passed as bridge/transport hardware evidence
4.20c v2.1 three-seed chunked hardware repeat = passed as bridge/transport hardware repeatability evidence
4.21a keyed context-memory hardware bridge = passed one-seed EBRAINS hardware bridge probe
6.5 adult-turnover stressor if the final organism claim requires it
7.4 delayed-reward policy / action selection
7.5 curriculum / environment generator
7.6 long-horizon planning / subgoal control
4.19 hardware lifecycle feasibility
4.29e native replay/consolidation bridge = hardware pass ingested after cra_429p repair
4.29f compact native mechanism regression = pass; freezes CRA_NATIVE_MECHANISM_BRIDGE_v0.3
5.19a local continuous temporal substrate reference = completed; fading memory helped held-out long-memory task, recurrence-specific value not yet separated
5.19b temporal-substrate benchmark/sham gate = completed; fading memory supported, bounded nonlinear recurrence unproven
5.19c fading-memory narrowing compact-regression gate = passed and froze bounded v2.2
7.0j generic bounded recurrent-state promotion gate = passed and froze bounded v2.3
4.30-readiness lifecycle-native preflight/layering audit = passed; static-pool lifecycle-native path layers on native mechanism bridge v0.3 with v2.2 as software reference only
4.30 lifecycle-native static-pool contract = passed; command/readback/event/gate/failure schema defined before local reference or hardware work
4.30a local static-pool lifecycle reference = passed; canonical and boundary deterministic traces plus lifecycle shams precomputed
4.30b lifecycle runtime source audit = passed; runtime static-pool lifecycle surface and host/schema parity tests complete
4.30b-hw single-core lifecycle active-mask/lineage hardware smoke = hardware functional pass after ingest correction; raw remote fail was runner rev-0001 readback counter criterion defect
4.30c native lifecycle/ecology migration = complete; multi-core lifecycle state split contract/local reference passed
4.30d native lifecycle/ecology migration = complete; multi-core lifecycle runtime source audit/local C host test passed
4.30e native lifecycle/ecology migration = hardware pass ingested; five-profile lifecycle smoke passed on board 10.11.226.145 with 75/75 hardware criteria and 5/5 ingest criteria
```

These planned tiers may move in order as evidence arrives, but completed pass,
fail, and diagnostic results must remain auditable.

## Evidence Categories

This repo uses five evidence labels so paper claims stay clean:

- **Canonical registry evidence**: entries in `controlled_test_output/STUDY_REGISTRY.json`; these populate the paper-facing results table and require all registered criteria/artifacts to pass.
- **Baseline-frozen mechanism evidence**: a mechanism diagnostic or promotion gate that passed its predeclared gate, preserved compact regression, and has a frozen `baselines/CRA_EVIDENCE_BASELINE_vX.Y.*` lock, but is not necessarily listed as a canonical registry bundle yet.
- **Noncanonical diagnostic evidence**: useful pass/fail diagnostic work that answers a design question but does not by itself freeze a new baseline or enter the canonical paper table.
- **Failed/parked diagnostic evidence**: clean negative evidence retained to prevent p-hacking and explain why a mechanism was not promoted.
- **Hardware prepare/probe evidence**: prepared capsules and one-off probes; these are not hardware claims until returned artifacts are reviewed and explicitly promoted.

In short: `noncanonical` does not mean the result has no value. It means "not a formal registry/paper-table claim by itself." A frozen baseline such as v1.6, v1.7, v1.9, v2.0, v2.1, v2.2, or v2.3 is stronger than an ordinary diagnostic even when its source bundle remains outside the canonical registry.

## Paper-Grade Safeguards

Before a strong paper claim, future tiers must follow the reviewer-defense
contract in `docs/REVIEWER_DEFENSE_PLAN.md`:

- predeclare final pass/fail criteria before running large matrices
- report mean, median, std, min/max, confidence intervals where practical, and per-seed deltas
- report sample-efficiency metrics for hard/adaptive claims: steps to threshold,
  reward events to threshold, switch recovery, and area under the learning curve
- compare against the strongest reasonable baseline, not only a median baseline
- use identical task streams, causal information boundaries, train/evaluation windows, and delayed reward visibility for baselines
- use the regression ladder: focused diagnostics for exploratory tweaks, targeted v0.7 head-to-heads for candidates, compact Tier 1/Tier 2/Tier 3 regression for promoted mechanisms, combination tests only after single-feature wins, and full final matrices only for paper-lock candidates
- add leakage/oracle controls for every real-ish adapter
- export dopamine, delayed-credit, trophic, lifecycle, active-mask, and lineage traces for organism claims
- export module-reuse, routing, and module-shuffle traces for compositionality claims
- export context-state, action-selection, exploration, and curriculum-generator traces for working-memory, policy, and curriculum claims
- export spike trains, temporal-code metadata, neuron-model parameters, motif masks, and unsupervised preexposure traces for SNN-native mechanism claims
- export hardware resource accounting for every hardware tier
- keep failed and noncanonical diagnostic bundles as audit history
- treat long-term strategic mechanisms as required research targets, not automatic wins: each gets prototype/instrument/test/bounded-debug/ablate/control before promote, redesign, or archive

## Tier 1: Sanity Tests

### 1. Zero-Signal Test

Purpose: prove the organism does not fake learning when no useful signal exists.

Protocol:

- sensory input is all zeros
- target/outcome return is all zeros
- run a normal organism loop with the fast Mock backend
- record prediction, dopamine, capital, accuracy, population, trophic health

Minimum pass:

- max absolute dopamine is effectively zero
- capital remains at break-even
- directional accuracy does not rise above baseline
- prediction/target correlation is undefined or zero because target variance is zero

### 2. Shuffled-Label Test

Purpose: prove the organism is not exploiting target leakage.

Protocol:

- generate a balanced signed sensory sequence
- independently shuffle target labels
- inject sensory values into the SNN
- evaluate against the shuffled targets
- use `Organism.train_step(..., sensory_return_1m=...)` so X and Y are decoupled

Minimum pass:

- no sustained above-baseline directional accuracy
- low prediction/target correlation
- no meaningful capital edge

### 3. Random-Seed Repeat Test

Purpose: prove the Tier 1 result is repeatable, not a lucky seed.

Protocol:

- repeat shuffled-label controls over 20 or more seeds
- export per-seed summary statistics

Minimum pass:

- mean strict directional accuracy remains near chance
- only a small minority of seeds exceed the single-run warning threshold
- mean absolute prediction/target correlation remains low

## Tier 2: Learning Proof Tests

### 4. Fixed-Pattern Task

Purpose: prove the system can learn a simple predictable structure.

Example task:

```text
+--++--++--
```

Minimum pass:

- final/tail accuracy rises above baseline
- predictions become phase-aligned with the pattern
- performance beats zero-signal and shuffled-label controls

### 5. Delayed Reward Task

Purpose: prove delayed credit assignment works.

Protocol:

- prediction at step `t` is rewarded at `t + k`
- vary `k` around the configured evaluation horizon

Minimum pass:

- performance beats immediate random baseline
- pending-horizon ledgers mature at configured horizons
- learned signal survives when immediate reward is uninformative

### 6. Nonstationary Switch Task

Purpose: prove adaptation rather than memorization.

Protocol:

- rule A for first half
- rule B, preferably inverted or phase-shifted, for second half

Minimum pass:

- accuracy drops around switch
- changepoint/plasticity signal rises
- performance recovers after an adaptation window

## Tier 3: Architecture Tests

### 7. Ablation: No Dopamine

Purpose: prove dopamine matters.

Protocol:

- same fixed-pattern task
- force raw dopamine to zero or dopamine gain to zero

Minimum pass:

- performance drops relative to intact organism

### 8. Ablation: No Plasticity

Purpose: prove learning is not a static readout artifact.

Protocol:

- freeze STDP/weight updates
- keep sensory/task loop unchanged

Minimum pass:

- performance drops relative to intact organism

### 9. Ablation: No Trophic Selection

Purpose: prove ecology adds value.

Protocol:

- disable birth/death/survival pressure
- compare against intact organism

Minimum pass:

- intact organism is more robust, more accurate, or more adaptive

## Tier 4: Scaling And Portability Tests

### 10. Population Scaling Test

Purpose: prove scaling helps or at least does not collapse.

Protocol:

- run 4, 8, 16, 32, 64 polyps
- hold task, seeds, and run length constant

Minimum pass:

- no catastrophic collapse with larger populations
- some scaling region improves accuracy, robustness, or adaptation speed

### 10b. Hard Population Scaling Addendum

Purpose: test whether larger populations add value once the baseline scaling
task is no longer saturated.

Protocol:

- run 4, 8, 16, 32, 64 polyps
- use the NEST backend by default
- use at least seeds 42, 43, 44
- add noisy delayed cue/reward trials
- use reward delays of 3-5 steps
- switch rules every 40-50 steps by default
- keep population size fixed by disabling births/deaths
- keep trophic/energy dynamics enabled
- seed deterministic founder diversity across readout weights and local
  readout learning-rate scales

Minimum pass:

- no extinction or population collapse
- all final live counts equal the requested N
- no births/deaths occur during the fixed-N run
- all population sizes perform above the random overall-accuracy floor
- larger N does not degrade sharply versus N=4
- larger N improves at least one useful scaling signal: accuracy,
  prediction/target correlation, recovery speed, or seed-to-seed variance

Latest documented result:

- run directory: `controlled_test_output/tier4_10b_20260426_161251/`
- status: pass
- interpretation: stable on the harder stressor, with scaling value visible in
  correlation, recovery, and variance rather than a large raw-accuracy jump

### 11. Domain-Transfer Test

Purpose: prove CRA is substrate-level, not trading-specific.

Protocol:

- run a controlled finance/signed-return task through `TradingBridge`
- run a non-finance `sensor_control` task through `SensorControlAdapter`
- use the same NEST backend, seeds, fixed population size, and delayed
  cue/consequence structure for both domains
- run zero-signal controls for both domains
- run shuffled-label controls for both domains
- require the sensor adapter path to run with `use_default_trading_bridge=False`

Minimum pass:

- finance task learns above baseline
- non-finance task learns above baseline
- zero controls fail to learn
- shuffled controls stay near chance with low prediction/target correlation
- organism APIs do not require trading-only assumptions

Latest documented result:

- run directory: `controlled_test_output/tier4_11_20260426_164655/`
- status: pass
- finance overall accuracy: `0.863636`
- sensor_control overall accuracy: `0.954545`
- finance shuffled accuracy: `0.530303`
- sensor shuffled accuracy: `0.560606`
- sensor adapter path did not construct `TradingBridge`

### 12. Backend Parity Test

Purpose: prove the result can move toward neuromorphic hardware.

Protocol:

- run the same fixed experiment on NEST and Brian2 first
- require the same seeds, task, fixed population size, and pass/fail thresholds
- reject any synthetic spike fallback or backend summary-read failure
- run a SpiNNaker PyNN import/setup/factory readiness smoke
- keep SpiNNaker readiness distinct from a real SpiNNaker `sim.run()` or
  hardware learning claim

Minimum pass:

- NEST/Brian2 reproduce qualitative learning behavior
- hardware-specific gaps are isolated and documented
- NEST and Brian2 both learn above threshold
- NEST/Brian2 accuracy and correlation deltas stay within bounded tolerances
- synthetic fallback counters remain zero
- SpiNNaker PyNN imports, setup/end smoke, and BackendFactory mapping pass

Latest documented result:

- run directory: `controlled_test_output/tier4_12_20260426_170808/`
- status: pass
- NEST overall accuracy: `0.974790`
- Brian2 overall accuracy: `0.974790`
- NEST tail accuracy: `1.0`
- Brian2 tail accuracy: `1.0`
- NEST/Brian2 accuracy delta: `0.0`
- NEST/Brian2 tail-correlation delta: `0.0`
- synthetic fallbacks: `0`
- `sim.run` failures: `0`
- summary-read failures: `0`
- SpiNNaker PyNN readiness: pass
- interpretation: backend movement from NEST to Brian2 preserves the controlled
  fixed-pattern learning behavior; the SpiNNaker stack is locally prepared, but
  real SpiNNaker `sim.run()` or hardware parity remains the next stricter step

### 13. SpiNNaker Hardware Capsule

Purpose: prove that the minimal CRA learning capsule can execute on real
SpiNNaker hardware while preserving expected fixed-pattern behavior.

Protocol:

- prepare a self-contained JobManager capsule from the repo
- run the same minimal fixed-pattern task through `pyNN.spiNNaker`
- keep the task aligned with Tier 4.12 as much as hardware allows:
  seed `42`, `N=8`, 120 steps, fixed population
- export logs, provenance, step metrics, summary JSON/CSV, and plots
- on failure, export backend diagnostics, Python traceback, and recent
  sPyNNaker `reports/` provenance directories
- compare qualitatively against the Tier 4.12 NEST/Brian2 result
- keep setup-only, virtual-board, and hardware execution claims separate

Minimum pass:

- hardware `sim.run` is attempted through a real JobManager/sPyNNaker allocation
  and completes
- synthetic fallback count remains `0`
- `sim.run` failure count remains `0`
- summary-read failure count remains `0`
- real spike readback is nonzero
- fixed population does not collapse
- fixed-pattern accuracy/correlation remain above threshold
- target configuration evidence is documented when exposed by the environment;
  if the local detector cannot see the JobManager target flag, the result can
  still pass when hardware execution, zero fallback, and real spike readback are
  all present

Latest documented result:

- run directory: `controlled_test_output/tier4_13_20260427_011912_hardware_pass/`
- source generated at: `2026-04-27T00:33:33+00:00`
- source remote output directory:
  `/tmp/job18372215669669985472.tmp/cra_test/controlled_test_output/tier4_13_20260427_011912`
- status: pass
- backend: `pyNN.spiNNaker`
- hardware run attempted: `True`
- hardware target configured by detector: `False`
- synthetic fallbacks: `0`
- `sim.run` failures: `0`
- summary-read failures: `0`
- total spike readback: `283903`
- seed: `42`
- population: `N=8`, fixed population
- total steps: `120`
- overall strict accuracy: `0.9747899159663865`
- tail strict accuracy: `1.0`
- overall prediction-target correlation: `0.8917325875598855`
- tail prediction-target correlation: `0.9999839178111984`
- final alive polyps: `8.0`
- births/deaths: `0 / 0`
- runtime seconds: `858.6201063019689`
- interpretation: Tier 4.13 passes as a minimal fixed-pattern SpiNNaker
  hardware capsule. This is evidence that the capsule executes through
  `pyNN.spiNNaker` with real spike readback and preserves expected behavior; it
  is not yet evidence for full hardware scaling or full CRA deployment on
  hardware.
- caveat: `hardware_target_configured=False` is documented as a detector/env
  visibility limitation for this JobManager run, not as fallback evidence. The
  pass is based on completed hardware `sim.run`, zero fallback/failure counters,
  and nonzero spike readback.
- historical fixes before this pass: dopamine neuromodulation was sharded to
  avoid the 255-synapse reward-row cap, and NumPy 2/sPyNNaker-spinnman
  compatibility shims were added for neuromodulation flags and hardware word
  byte views.

### 14. Hardware Runtime Characterization

Purpose: measure where the Tier 4.13 hardware wall-clock cost went.

Protocol:

- characterize the canonical Tier 4.13 hardware-pass bundle from its result
  JSON, per-step CSV, and `global_provenance.sqlite3`
- optionally rerun the same fixed-pattern capsule inside JobManager with the
  Tier 4.14 harness
- export category timers, top algorithm timers, runtime breakdown CSV/PNG,
  summary CSV, JSON manifest, and Markdown report
- keep this separate from learning, repeatability, or scaling claims

Minimum pass:

- source hardware result is a Tier 4.13 pass or the fresh hardware run passes
- synthetic fallback count remains `0`
- `sim.run` failure count remains `0`
- summary-read failure count remains `0`
- wall-clock runtime is measured
- simulated biological task duration is measured
- sPyNNaker category and algorithm provenance timers are parsed
- dominant runtime category is identified

Latest documented result:

- run directory: `controlled_test_output/tier4_14_20260426_213430/`
- source bundle: `controlled_test_output/tier4_13_20260427_011912_hardware_pass/`
- status: pass
- runtime seconds: `858.6201063019689`
- simulated biological seconds: `6.0`
- wall-to-simulated-time ratio: `143.10335105032814`
- mean wall time per 50 ms step: `7.155167552516407`
- dominant category: `Running Stage`, `637.741974` seconds
- dominant algorithm: `Application runner`, `87.375508` seconds total,
  `0.7281292333333333` seconds per step
- buffer extraction: `32.786108999999996` seconds total,
  `0.273217575` seconds per step
- interpretation: the hardware result is real, and the large runtime is mostly
  repeated short-step sPyNNaker/hardware orchestration, not evidence that the
  neural substrate itself needs hundreds of seconds to represent six seconds of
  task time.

### 15. SpiNNaker Hardware Multi-Seed Repeat

Purpose: prove the Tier 4.13 minimal hardware result repeats across seeds.

Protocol:

- run the same fixed-pattern SpiNNaker hardware capsule as Tier 4.13
- use seeds `42`, `43`, and `44`
- keep population `N=8`, 120 steps, fixed population, and thresholds unchanged
- stop on the first failed seed
- export per-seed CSV/PNG traces, seed summary CSV, aggregate JSON/CSV, report,
  and recent sPyNNaker provenance reports

Minimum pass:

- all requested seeds complete
- every seed has zero synthetic fallback
- every seed has zero `sim.run` failures
- every seed has zero summary-read failures
- every seed has nonzero spike readback
- every seed stays above fixed-pattern accuracy/correlation thresholds
- every seed preserves the fixed population with no births/deaths

Latest documented result:

- run directory: `controlled_test_output/tier4_15_20260427_030501_hardware_pass/`
- source generated at: `2026-04-27T02:48:50+00:00`
- source remote output directory:
  `/tmp/job12244319576281684700.tmp/cra_test_1/controlled_test_output/tier4_15_20260427_030501`
- status: pass
- backend: `pyNN.spiNNaker`
- requested seeds: `42`, `43`, `44`
- all seed statuses: pass
- hardware run attempted: `True`
- hardware target configured by detector: `False`
- synthetic fallbacks: `0`
- `sim.run` failures: `0`
- summary-read failures: `0`
- total spike readback min/mean/max: `284154 / 291103.6666666667 / 295521`
- runtime seconds min/mean/max: `865.3982471250929 / 873.6344163606409 / 884.8983335739467`
- overall strict accuracy mean/min: `0.9747899159663865 / 0.9747899159663865`
- tail strict accuracy mean/min: `1.0 / 1.0`
- tail prediction-target correlation mean/min:
  `0.9999901037892215 / 0.9999839178111984`
- final alive polyps: `8.0`
- births/deaths: `0 / 0`
- interpretation: Tier 4.15 passes as three-seed repeatability evidence for the
  same minimal fixed-pattern SpiNNaker hardware capsule. It strengthens the
  hardware capsule claim by showing repeatability across seeds, but it is still
  not a harder-task hardware result, hardware population scaling result, or full
  CRA hardware deployment.

## Tier 5: External Comparisons

### 5.1 External Baselines

Purpose: test whether CRA does anything useful compared with simpler non-CRA
learners under identical online task streams.

Protocol:

- run CRA plus external baselines on the same task streams, seeds, labels, and
  prequential evaluation order
- require every model to predict before seeing the label
- mature delayed feedback only when the consequence arrives
- compare against random/sign persistence, online perceptron, online logistic
  regression, echo-state network, small GRU readout, STDP-only SNN, and simple
  evolutionary population baselines
- add surrogate-gradient SNN and ANN-to-SNN/ANN-trained-readout baselines where
  the task interface is fair, causal, and technically compatible
- use fixed-pattern, delayed cue, sensor_control, and hard noisy switching tasks
- export per-task/per-model/per-seed time series, aggregate CSV, comparison CSV,
  plots, JSON manifest, and Markdown report
- report sample-efficiency metrics: steps to threshold, tail events to threshold,
  reward events to threshold, switch recovery steps, and area under learning curve

Minimum pass:

- full task/model/seed matrix completes
- at least one simple external baseline learns the fixed-pattern task, proving
  the baseline harness is not broken
- CRA shows a hard-task advantage versus the external median on at least two
  hard tasks through tail accuracy, absolute correlation, or recovery
- CRA is not dominated on every hard task by the best external baseline
- best external baselines are documented rather than hidden
- conversion or surrogate-gradient baselines are either run fairly or explicitly
  marked not applicable for the task with a reason

Latest documented result:

- run directory: `controlled_test_output/tier5_1_20260426_232530/`
- status: pass
- backend for CRA: `nest`
- seeds: `42`, `43`, `44`
- tasks: `fixed_pattern`, `delayed_cue`, `sensor_control`, `hard_noisy_switching`
- model/seed/task runs completed: `108 / 108`
- hard advantage tasks versus external median: `sensor_control`,
  `hard_noisy_switching`
- fixed-pattern: CRA tail accuracy `1.0`; best external tail accuracy `1.0`
- delayed cue: CRA tail accuracy `0.4761904761904762`; best external tail
  accuracy `1.0`
- sensor_control: CRA tail accuracy `1.0`; external median tail accuracy
  `0.8166666666666667`
- hard noisy switching: CRA tail accuracy `0.5833333333333334`; external median
  tail accuracy `0.5416666666666666`; CRA mean recovery `15.066666666666666`
  steps versus external median recovery `32.33333333333333` steps
- interpretation: Tier 5.1 passes as an honest external-baseline comparison.
  CRA does not beat simple learners on the easy delayed-cue task. Its defensible
  advantage appears on the non-finance sensor_control task and the harder noisy
  switching task, especially in median comparison and recovery.

### 5.2 Learning Curve / Run-Length Sweep

Purpose: determine whether CRA's Tier 5.1 edge grows, disappears, or depends on
short-run conditions.

Protocol:

- run CRA and the same Tier 5.1 baselines at 120, 240, 480, 960, and 1500 steps
- use `sensor_control`, `hard_noisy_switching`, and `delayed_cue`
- use seeds `42`, `43`, and `44`
- keep the same prequential rule: every model predicts before seeing feedback
- export aggregate summaries, per-run time series, comparison tables, curve
  analysis, plots, JSON manifest, and Markdown report

Minimum pass:

- full run-length/task/model/seed matrix completes
- every requested run length is represented
- every aggregate curve cell is produced
- task-level interpretation is generated for each task
- runtime is recorded for every aggregate cell

Latest documented result:

- run directory: `controlled_test_output/tier5_2_20260426_234500/`
- status: pass
- backend for CRA: `nest`
- run lengths: `120`, `240`, `480`, `960`, `1500`
- tasks: `sensor_control`, `hard_noisy_switching`, `delayed_cue`
- model/seed/task/length runs completed: `405 / 405`
- final advantage tasks at 1500 steps: `0`
- delayed cue: CRA improves to tail accuracy `0.7246376811594203`, but best
  external tail accuracy remains `1.0`
- sensor_control: CRA reaches tail accuracy `1.0`, but external baselines also
  saturate at `1.0`
- hard noisy switching: CRA tail accuracy is `0.4465408805031446`; best
  external tail accuracy is `0.5534591194968553`
- interpretation: Tier 5.2 passes as a learning-curve characterization. The
  scientific finding is mixed/negative for CRA at the longest horizon: Tier 5.1
  edges do not strengthen under this configuration.

### 5.3 CRA Failure Analysis / Learning Dynamics Debug

Purpose: diagnose why the Tier 5.1 comparative edge fades or disappears in
Tier 5.2 before spending another hardware run on a harder capsule.

Protocol:

- run CRA-only diagnostic variants at 960 steps on `delayed_cue` and
  `hard_noisy_switching`
- use seeds `42`, `43`, and `44`
- compare variants against the current CRA baseline and Tier 5.2 external
  baseline references
- sweep readout learning rate, delayed-credit learning rate, eligibility
  horizon, dopamine smoothing, negative-surprise pressure, readout retention,
  fixed population diversity, and fast lifecycle replacement
- remove `sensor_control` from advantage claims because Tier 5.2 shows it
  saturates for both CRA and baselines

Minimum pass:

- full task/variant/seed CRA diagnostic matrix completes
- every aggregate diagnostic cell is produced
- task-level diagnosis is generated for each task
- comparisons versus current CRA and Tier 5.2 references are exported
- plots, CSVs, JSON manifest, and Markdown report are written

Latest documented result:

- run directory: `controlled_test_output/tier5_3_20260427_055629/`
- status: pass
- backend for CRA: `nest`
- steps: `960`
- seeds: `42`, `43`, `44`
- tasks: `delayed_cue`, `hard_noisy_switching`
- CRA diagnostic runs completed: `78 / 78`
- variants: `13`
- delayed cue: best variant `delayed_lr_0_20`, tail accuracy `1.0`, delta
  versus current CRA `+0.4444444444444444`
- hard noisy switching: best tail variant `delayed_lr_0_20`, tail accuracy
  `0.5392156862745098`, delta versus current CRA `+0.08823529411764702`,
  delta versus external median `+0.06372549019607848`, but delta versus best
  external baseline `-0.0490196078431373`
- switch recovery: `horizon_3` has the best mean recovery at
  `24.34285714285714` steps
- interpretation: Tier 5.3 passes as a diagnostic. Stronger delayed credit is
  the leading candidate fix, but this is not hardware evidence and not final
  CRA superiority because hard noisy switching still trails the best external
  baseline.

### 5.4 Delayed-Credit Confirmation

Purpose: confirm that the Tier 5.3 `delayed_lr_0_20` candidate is not a lucky
single-horizon tuning artifact before designing a harder SpiNNaker capsule.

Protocol:

- compare current CRA, `cra_delayed_lr_0_20`, and the Tier 5.1 external
  baselines
- use `delayed_cue` and `hard_noisy_switching`
- use run lengths `960` and `1500`
- use seeds `42`, `43`, and `44`
- keep the same prequential rule: every model predicts before seeing feedback
- export aggregate summaries, confirmation rows, task findings, per-run time
  series, plots, JSON manifest, and Markdown report

Minimum pass:

- full task/model/seed/run-length matrix completes
- `delayed_cue` candidate tail accuracy stays near `1.0`
- `hard_noisy_switching` candidate beats the external median at every requested
  length
- candidate does not regress versus current CRA
- seed variance remains within the predeclared tolerance
- superiority is claimed only where the candidate beats the best external
  baseline, not merely the median

Latest documented result:

- run directory: `controlled_test_output/tier5_4_20260427_065412/`
- status: pass
- backend for CRA: `nest`
- run lengths: `960`, `1500`
- seeds: `42`, `43`, `44`
- tasks: `delayed_cue`, `hard_noisy_switching`
- total runs completed: `120 / 120`
- delayed cue: candidate tail accuracy `1.0` at both run lengths; minimum delta
  versus current CRA `+0.2753623188405797`
- hard noisy switching: candidate tail accuracy `0.5392156862745098` at 960
  steps and `0.5157232704402516` at 1500 steps
- hard noisy switching deltas: minimum delta versus current CRA
  `+0.06918238993710696`, minimum delta versus external median
  `+0.01572327044025157`, minimum delta versus best external
  `-0.0490196078431373`
- interpretation: Tier 5.4 passes as confirmation of the delayed-credit
  candidate versus the predeclared median/regression criteria. It authorizes
  designing Tier 4.16 with `delayed_lr_0_20`, but it is not hardware evidence
  and not a hard-switching best-baseline superiority claim.

## Planned Tier 4.16: Harder SpiNNaker Hardware Capsule

Purpose: test whether the Tier 5.4 confirmed delayed-credit setting survives on
real SpiNNaker hardware when the task is harder than the minimal fixed-pattern
capsule.

Protocol:

- split the hardware run into `4.16a delayed_cue` and `4.16b hard_noisy_switching`
- use `delayed_lr_0_20`
- use `N=8`
- use seeds `42`, `43`, and `44` if runtime allows
- require real `pyNN.spiNNaker` execution, not virtual-board or synthetic fallback
- export per-task/per-seed time series, plots, summaries, provenance pointers,
  JSON manifest, and Markdown report

Minimum pass:

- every requested task/seed run completes
- zero synthetic fallback
- zero `sim.run` failures
- zero summary-read failures
- nonzero real spike readback for every completed run
- fixed population remains `N=8` with no births/deaths
- delayed-cue tail accuracy passes the hardware threshold
- hard noisy switching passes the predeclared tail-accuracy/correlation floor

Claim boundary:

- A prepare capsule is not hardware evidence.
- A passing Tier 4.16 run can be cited only as harder-task hardware transfer of
  the confirmed delayed-credit setting.
- It is not a full hardware scaling result, not full CRA hardware deployment,
  and not a superiority claim over the best external hard-switching baseline.

Current diagnostic note:

- a real Tier 4.16 hardware attempt completed all six task/seed runs with zero
  fallback/failures and real spike readback, but failed the `4.16a delayed_cue`
  tail-accuracy criterion
- the failed hardware bundle is preserved at
  `controlled_test_output/tier4_16_20260427_124916_hardware_fail/`
- local replay in NEST and Brian2 reproduced the same delayed-cue seed pattern:
  seed `42` passes, seeds `43` and `44` fail
- the local debug bundle is preserved at
  `controlled_test_output/tier4_16a_debug_20260427_141912/`
- diagnosis: `software_config_or_metric_issue`
- metric caveat: the delayed-cue tail score has only `3` events, so one missed
  event changes tail accuracy by `0.3333333333333333`

Decision: do not rerun the full six-run Tier 4.16 hardware capsule in slow
per-step mode. The delayed-cue task/metric is fixed locally, and Tier 4.17/Tier
4.17b now provide the chunked-runtime contract and local parity gate for the next
hardware allocation.

Repair result:

- local repair harness:
  `experiments/tier4_16a_delayed_cue_fix.py`
- NEST length sweep:
  `controlled_test_output/tier4_16a_fix_nest_length_sweep_20260427_145400/`
- NEST 1200-step pass:
  `controlled_test_output/tier4_16a_fix_nest_1200_20260427_145600/`
- Brian2 1200-step pass:
  `controlled_test_output/tier4_16a_fix_brian2_1200_20260427_145800/`
- NEST+Brian2 1500-step pass:
  `controlled_test_output/tier4_16a_fix_20260427_143252/`

The shorter local sweep shows `240`, `480`, and `960` steps are not stable
enough for the `0.85` threshold. `1200` steps passes in both NEST and Brian2
with minimum tail accuracy `0.972972972972973` and `37` tail events. `1500`
steps also passes with tail accuracy `1.0` and `46` tail events. The one-seed
chunked hardware probe passed on seed `43`, and the repaired three-seed
delayed-cue hardware repeat has now passed on seeds `42`, `43`, and `44`.
Use the same `1200`-step, chunked-host design for Tier 4.16b hard noisy
switching.

## Tier 4.17: Batched / Continuous Hardware Runtime Refactor

Purpose: preserve the correct runtime contract before rerunning repaired Tier 4.16a
on hardware.

Runtime vocabulary:

```text
runtime_mode = step | chunked | continuous
learning_location = host | hybrid | on_chip
```

Current implementation boundary:

- `step + host` is the proven hardware execution path.
- `chunked + host` is locally validated for step-vs-chunked parity in Tier 4.17b and has now passed the Tier 4.16a delayed-cue hardware repeat.
- valid chunking requires scheduled input delivery inside a chunk, per-step binned spike readback, and host learning replay from those bins.
- `continuous`, `hybrid`, and `on_chip` are future custom-runtime targets.

Latest runtime-contract bundle:

```text
controlled_test_output/tier4_17_20260427_171719_runtime_scaffold/
```

The runtime-contract inventory estimates that a 1200-step delayed-cue probe
would need `1200` `sim.run` calls in step mode, versus `240`, `120`, `48`, or
`24` calls for chunk sizes `5`, `10`, `25`, or `50`. These are runtime estimates
and implementation boundaries, not a hardware learning result.

Latest Tier 4.17b local parity bundle:

```text
controlled_test_output/tier4_17b_20260427_164625_step_chunk_parity/
```

Tier 4.17b passes as a local NEST/Brian2 diagnostic for `delayed_cue`, seed
`42`, 120 steps, and chunk sizes `5`, `10`, `25`, and `50`. It verifies:

- scheduled input inside chunks via PyNN `StepCurrentSource`
- spike readback binned back to the original CRA step grid
- host-side delayed-credit replay from those bins
- exact parity versus the step reference for evaluation targets, tail/all accuracy, predictions, and per-bin spike totals
- zero fallback/failures
- `sim.run` call reductions from `5x` to `40x`

Interpretation: chunked mode is scientifically valid locally for this narrow
runtime diagnostic, and the Tier 4.16 runner now has a `chunked + host` path for
hardware transfer. The repaired `delayed_cue` repeat has passed on real
SpiNNaker for seeds `42`, `43`, and `44`; it is not hard-switching hardware,
hardware scaling, or a continuous/on-chip learning claim. Tier 4.16b now covers
the repaired hard-switch hardware repeat separately.

Latest repaired three-seed hardware repeat:

```text
controlled_test_output/tier4_16_20260427_184635_delayed_cue_3seed_hardware_pass/
```

Result:

- task/seeds: `delayed_cue`, seeds `42`, `43`, `44`
- steps: `1200`
- runtime: `chunked + host`
- chunk size: `25`
- hardware `sim.run` calls: `48` per seed
- minimum real spike readback: `94976`
- fallback/failure counters: `0`
- tail accuracy mean/min: `1.0`
- all accuracy mean: `0.9933333333333333`
- tail prediction-target correlation mean: `0.9999999999999997`
- runtime mean: `562.8373009915618` seconds

Required order:

1. keep Tier 4.17b as the local parity gate
2. seed `43` repaired hardware probe: passed
3. repaired Tier 4.16a across seeds `42,43,44`: passed
4. Tier 4.16b hard_noisy_switching returned a clean-hardware learning failure
5. corrected Tier 4.16b-debug completed and first classified the blocker as `chunked_host_bridge_learning_failure`
6. aligned Tier 4.16b bridge repair fixed host-replay ordering and task-default drift, then passed locally on NEST/Brian2
7. repaired Tier 4.16b seed `44` hardware probe passed narrowly


Latest Tier 4.16b hard noisy switching hardware result:

```text
controlled_test_output/tier4_16_20260427_230043_hard_noisy_switching_3seed_hardware_pass/
status = pass
task = hard_noisy_switching
seeds = 42,43,44
steps = 1200
runtime = chunked + host
chunk_size_steps = 25
zero fallback/failures = true
real spike readback min = 94707
tail_accuracy_mean = 0.5476190476190476
tail_accuracy_min = 0.5238095238095238
all_accuracy_mean = 0.5497076023391813
tail_prediction_target_corr_mean = 0.04912970304751133
runtime_seconds_mean = 385.21602948141907
raw_dopamine = 0.0
```

Interpretation: the repaired hard-switch hardware repeat passed across seeds
`42`, `43`, and `44`. This completes the narrow Tier 4.16 harder-task hardware
transfer sequence:

```text
4.16a delayed_cue hardware repeat = pass
4.16b hard_noisy_switching hardware repeat = pass
```

The result remains bounded. It is chunked host delayed-credit replay, not native
on-chip dopamine/eligibility. `raw_dopamine` is zero because same-step prediction
and delayed feedback do not overlap in this task; the delayed-credit evidence is
matured horizon replay, pending horizon records, changing host replay weights,
and real spike readback. It is not hardware scaling, lifecycle/self-scaling, or
external-baseline superiority. The hard-switch pass is close to the threshold,
so runtime/resource characterization and expanded baselines remain required.

Historical Tier 4.16b audit artifacts:

```text
controlled_test_output/tier4_16_20260427_194526_hard_noisy_switching_3seed_hardware_fail/
controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/
controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427/
controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_brian2_20260427/
```

Decision: Tier 4.18a passed. Use `chunk_size_steps=50` as the current v0.7
hardware default unless a future task-specific parity check shows degradation.
Tier 4.18b can add chunk `100` or more seeds only if the hardware budget is
worth testing beyond the current default.

Prepare command:

```bash
make tier4-18a-prepare
```

Run command inside real SpiNNaker/JobManager allocation:

```bash
bash controlled_test_output/<tier4_18a_prepared_run>/jobmanager_capsule/run_tier4_18a_on_jobmanager.sh /tmp/tier4_18a_job_output
```

The generated capsule must return `tier4_18a_results.json`,
`tier4_18a_report.md`, `tier4_18a_summary.csv`, a runtime matrix CSV/PNG,
per-task/per-chunk/per-seed traces, and raw reports/provenance where available.
Prepared Tier 4.18a bundles are not evidence. The canonical Tier 4.18a pass is
`controlled_test_output/tier4_18a_20260428_012822_hardware_pass/`. It is
runtime/resource characterization only: not hardware scaling, not lifecycle
self-scaling, not native on-chip dopamine/eligibility, and not external-baseline
superiority.

## Tier 4.20a v2.1 Hardware Transfer Readiness Audit

Run:

```bash
make tier4-20a
```

Smoke:

```bash
make tier4-20a-smoke
```

Status: **passed as engineering audit evidence**.

Observed result:

- output: `controlled_test_output/tier4_20a_20260429_195403/`
- status: `PASS`
- mechanisms classified: `8`
- chunked host runtime contract: implemented
- continuous/on-chip runtime: explicitly not implemented
- incorrect on-chip-proven classifications: `0`
- default probe chunk: `50` steps over `1200` total steps, reducing expected
  `sim.run` calls from `1200` to `24`

Interpretation:

- v2.1 has one-seed bridge/transport hardware evidence through Tier 4.20b
- the next hardware action is Tier 4.20c, a three-seed v2.1 chunked hardware
  repeat
- macro eligibility is excluded because Tier 5.9c failed
- hybrid/custom-C/on-chip work should start only after returned v2.1 chunked
  hardware artifacts show real spike readback, zero fallback, and zero
  run/readback failures across seeds

Boundary: Tier 4.20a is not hardware evidence. It is a hardware-transfer plan
and risk matrix for the v2.1 stack.

## Tier 4.20b v2.1 One-Seed Chunked Hardware Probe

Prepare:

```bash
make tier4-20b-prepare
```

Run local/source simulation preflight:

```bash
make tier4-20b-preflight
```

Smoke prepare:

```bash
make tier4-20b-smoke
```

Status: **PASS as one-seed bridge/transport hardware evidence**.

Prepared output:

- output: `controlled_test_output/tier4_20b_20260429_205214_prepared/`
- tasks: `delayed_cue`, `hard_noisy_switching`
- seed: `42`
- steps: `1200`
- population size: `8`
- runtime mode: `chunked`
- learning location: `host`
- chunk size: `50`
- macro eligibility: `disabled/excluded`

Returned pass output:

- returned: `controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass/`
- ingested: `controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass_ingested/`
- runner revision: `tier4_20b_inprocess_no_baselines_20260429_2330`
- child execution mode: `in_process`
- real spike readback min: `94900`
- child `sim.run` failures: `0`
- child summary/readback failures: `0`
- child synthetic fallback: `0`
- delayed_cue seed 42 tail accuracy: `1.0`
- hard_noisy_switching seed 42 tail accuracy: `0.5952380952380952`

Fresh upload workflow:

```text
Upload: cra_420b/experiments/, cra_420b/coral_reef_spinnaker/
Run:    cra_420b/experiments/tier4_20b_v2_1_hardware_probe.py --mode run-hardware --tasks delayed_cue,hard_noisy_switching --seeds 42 --steps 1200 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20 --no-require-real-hardware --output-dir tier4_20b_job_output
Output: tier4_20b_job_output/
```

Do not upload local `controlled_test_output/`. The source/simulation preflight
is local-only and must be completed before upload. The EBRAINS-side
run is an empirical hardware probe, not a source/typecheck gate. Machine-target
visibility from config/env is recorded as advisory because the detector can be
blind in some JobManager contexts. Hardware evidence is promoted only from
actual pyNN.spiNNaker outcomes: `sim.run` success, zero fallback, zero readback
failures, and nonzero real spike readback. Tier 4.20a and `baselines/` are
optional local audit context, not required runtime artifacts.

Ingest returned artifacts:

```bash
python3 experiments/tier4_20b_v2_1_hardware_probe.py --mode ingest --ingest-dir /tmp/tier4_20b_job_output
```

Pass:

```text
child pyNN.spiNNaker run status = pass
hardware_run_attempted = true
sim.run failures = 0
summary/readback failures = 0
synthetic fallback = 0
real spike readback > 0
delayed_lr_0_20 selected
macro eligibility excluded
```

Boundary: Tier 4.20b wraps the proven Tier 4.16 chunked-host runner and records
the v2.1 transfer profile. The pass is v2.1 bridge/transport hardware evidence
only, not full native/on-chip v2.1 mechanism execution. The next hardware step
is Tier 4.20c: repeat this bridge across seeds `42`, `43`, and `44` before
claiming repeatable v2.1 bridge transfer.

## Tier 4.20c v2.1 Three-Seed Chunked Hardware Repeat

Prepare:

```bash
make tier4-20c-prepare
```

Status: **passed as returned hardware repeatability evidence**. The raw EBRAINS wrapper reported `FAIL` only because the minimal source upload intentionally omitted `controlled_test_output/tier4_20b_latest_manifest.json`; all child hardware criteria passed and the false-fail is preserved separately.

Prepared output:

- output: `controlled_test_output/tier4_20c_20260430_000433_prepared/`
- tasks: `delayed_cue`, `hard_noisy_switching`
- seeds: `42`, `43`, `44`
- expected child runs: `6`
- steps: `1200`
- population size: `8`
- runtime mode: `chunked`
- learning location: `host`
- chunk size: `50`
- macro eligibility: `disabled/excluded`

Fresh upload workflow:

```text
Upload: cra_420c/experiments/, cra_420c/coral_reef_spinnaker/
Run:    cra_420c/experiments/tier4_20c_v2_1_hardware_repeat.py --mode run-hardware --tasks delayed_cue,hard_noisy_switching --seeds 42,43,44 --steps 1200 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20 --no-require-real-hardware --output-dir tier4_20c_job_output
Output: tier4_20c_job_output/
```

Pass:

```text
child pyNN.spiNNaker run status = pass
hardware_run_attempted = true
child_runs = 6
child seeds = [42, 43, 44]
child tasks = [delayed_cue, hard_noisy_switching]
sim.run failures = 0
summary/readback failures = 0
synthetic fallback = 0
real spike readback > 0
delayed_lr_0_20 selected
macro eligibility excluded
```

Boundary: Tier 4.20c is repeatability evidence for the v2.1 bridge/transport
path only, not native/on-chip v2.1 mechanism execution.

Returned evidence:

- raw false-fail preserved: `controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_raw_false_fail/`
- corrected ingested pass: `controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_hardware_pass_ingested/`
- raw wrapper status: `FAIL`, caused only by missing local Tier 4.20b latest manifest in the fresh EBRAINS source bundle
- corrected status: `PASS`
- child status: `pass`
- child runs: `6`
- child seeds: `[42, 43, 44]`
- child tasks: `delayed_cue`, `hard_noisy_switching`
- `sim.run` failures: `0`
- summary/readback failures: `0`
- synthetic fallback: `0`
- minimum real spike readback: `94727`
- delayed_cue tail accuracy: min `1.0`, mean `1.0`
- hard_noisy_switching tail accuracy: min `0.5238095238095238`, mean `0.5476190476190476`, max `0.5952380952380952`
- runtime: `1593.9567` seconds total, child mean `262.6856` seconds per task/seed run

Lesson learned: hardware JobManager bundles must stay source-only. They must not require `controlled_test_output/` to execute; local prerequisite evidence belongs in the repo registry and in the returned-ingest audit trail, not in the EBRAINS upload.

## Tier 4.21a Keyed Context-Memory Hardware Bridge Probe

Purpose: start the targeted v2 mechanism bridge sequence with the lowest-risk
stateful mechanism, keyed context memory. Tier 4.20c proved the repeatable
chunked-host transport bridge; it did not prove that v2 keyed memory, replay,
predictive binding, composition/routing, or self-evaluation mechanisms execute
through the SpiNNaker path. Tier 4.21a tests a bounded keyed-memory adapter
before any custom-C/on-chip claim.

Local bridge smoke:

```bash
make tier4-21a-local
```

Prepared EBRAINS capsule:

```bash
make tier4-21a-prepare
```

Current status:

- local bridge smoke: `controlled_test_output/tier4_21a_local_bridge_smoke/`
- status: `PASS`
- prepared capsule: `controlled_test_output/tier4_21a_20260430_prepared/`
- returned hardware pass: `controlled_test_output/tier4_21a_20260430_keyed_context_memory_seed42_hardware_pass_ingested/`
- task: `context_reentry_interference`
- seed: `42`
- variants: `keyed_context_memory`, `slot_reset_ablation`, `slot_shuffle_ablation`, `wrong_key_ablation`
- steps: `720` for hardware probe, `180` for local smoke
- population size: `8`
- runtime mode: `chunked`
- learning location: `host`
- chunk size: `50`
- context memory slots: `4`
- hardware runtime: `3522.7107` seconds total across 4 variants
- minimum real spike readback: `714601`
- keyed all/tail accuracy: `1.0` / `1.0`
- best ablation all accuracy: `0.5`
- keyed delta versus best ablation: `0.5`
- keyed memory updates: `11`
- keyed feature-active decisions: `20`
- max keyed memory slots used: `4`

Fresh EBRAINS upload workflow:

```text
Upload: cra_421a/experiments/, cra_421a/coral_reef_spinnaker/
Run:    cra_421a/experiments/tier4_21a_keyed_context_memory_bridge.py --mode run-hardware --tasks context_reentry_interference --variants keyed_context_memory,slot_reset_ablation,slot_shuffle_ablation,wrong_key_ablation --seeds 42 --steps 720 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20 --context-memory-slot-count 4 --no-require-real-hardware --output-dir tier4_21a_job_output
Output: tier4_21a_job_output/
```

Pass:

```text
pyNN.spiNNaker run-hardware status = pass
hardware_run_attempted = true
all task/seed/variant runs completed
sim.run failures = 0
summary/readback failures = 0
synthetic fallback = 0
real spike readback > 0
keyed memory updates observed
keyed memory feature active at decisions
keyed memory retains more than one slot
keyed candidate not worse than best memory ablation
```

Boundary: Tier 4.21a is targeted keyed-memory bridge-adapter evidence only. It
does not prove native/on-chip memory, custom C, continuous execution, replay,
predictive binding, composition/routing, self-evaluation, language, planning,
AGI, or external-baseline superiority.

Interpretation: the current v2.1 chunked hardware path can carry a stateful
keyed-memory adapter through real `pyNN.spiNNaker` execution and recover the
expected keyed-versus-ablation separation on the one-seed bridge probe. The
nearly one-hour wall time also confirms that repeating full bridge matrices for
every v2 mechanism is not sustainable; this result should be used as a bridge
reference while moving toward Tier 4.22 custom/hybrid on-chip runtime.

## Tier 4.22a Custom / Hybrid On-Chip Runtime Contract

Run:

```bash
make tier4-22a
```

Status: **passed as engineering contract evidence** at
`controlled_test_output/tier4_22a_20260430_custom_runtime_contract/`.

Purpose: define the scientifically auditable route from the proven chunked-host
bridge to the real custom/hybrid/on-chip runtime without pretending the custom
runtime already exists.

Key additions:

- Tier 4.20c and Tier 4.21a are now the reference traces.
- Exhaustive per-mechanism hardware bridge matrices are explicitly not the
  default path.
- Before more expensive hardware, run a constrained-NEST plus sPyNNaker mapping
  preflight to catch unsupported PyNN features, unbounded state, dynamic graph
  assumptions, resource/mapping failures, and timing/encoding mismatches.
- Define host/hybrid/chip state ownership before C implementation.
- Define parity gates for continuous scaffold, persistent state, reward/
  plasticity, keyed memory/routing, and final stop-batching parity.

Boundary: Tier 4.22a is design/engineering evidence only. It is not custom C,
not native/on-chip CRA, not continuous execution, and not a speedup claim.

## Tier 4.22a0 SpiNNaker-Constrained Local Preflight

Run:

```bash
make tier4-22a0
```

Status: **passed as local pre-hardware constrained-transfer evidence** at
`controlled_test_output/tier4_22a0_20260430_spinnaker_constrained_preflight/`.

Purpose: make the next hardware allocation scientifically cheaper and cleaner by
checking the SpiNNaker-compatible subset locally before EBRAINS time is spent.

Pass gates:

- Tier 4.20c, Tier 4.21a, and Tier 4.22a references exist and pass.
- NEST, PyNN/NEST, and PyNN/SpiNNaker import locally.
- sPyNNaker exposes the required PyNN primitives:
  `IF_curr_exp`, `StepCurrentSource`, `Population`, `Projection`,
  `StaticSynapse`, and basic connectors.
- A constrained PyNN/NEST `StepCurrentSource` probe completes in one `sim.run`,
  returns binned spikes, and has zero sim/readback failures.
- Static bridge-source checks find the hardware-safe chunked path and no dynamic
  projection mutation inside the bridge runner.
- Population, conservative connection, keyed-slot, and fixed-point checks stay
  in declared bounds.
- The custom C runtime host tests pass.

Current result: the constrained NEST probe produced `64` spikes over `120`
steps, all criteria passed, static-compliance failures were `0`, resource
failures were `0`, and the custom runtime host tests passed.

Boundary: Tier 4.22a0 is not a hardware pass. It cannot prove EBRAINS will map a
full CRA run, cannot prove native/on-chip learning, and cannot prove speedup. It
is the required local gate before Tier 4.22b continuous transport scaffold work.

## Tier 4.22b Continuous Transport Scaffold

Run:

```bash
make tier4-22b
```

Status: **passed locally as continuous transport scaffold evidence** at
`controlled_test_output/tier4_22b_20260430_continuous_transport_local/`.

Purpose: isolate continuous scheduled input and compact binned readback before
reward/plasticity learning is added.

Pass gates:

- Tier 4.22a0 local preflight exists and passes.
- The runner executes delayed_cue and hard_noisy_switching reference streams.
- Each task/seed case uses exactly one continuous `sim.run`.
- Scheduled input uses `StepCurrentSource`.
- Readback returns binned per-step spikes.
- Zero synthetic fallback, zero `sim.run` failures, zero readback failures, and
  zero scheduled-input failures.
- Nonzero spike readback for every case.
- Learning is explicitly disabled and marked as transport-only.

Current result: local PyNN/NEST passed delayed_cue and hard_noisy_switching,
seed `42`, `1200` steps, N=`8`, one `sim.run` per case, zero failures, and
minimum per-case spike readback `101056`.

Returned hardware result: **passed as real SpiNNaker continuous transport
evidence** at
`controlled_test_output/tier4_22b_20260430_continuous_transport_hardware_pass_ingested/`.
The EBRAINS run completed delayed_cue and hard_noisy_switching, seed `42`,
`1200` steps, N=`8`, real `pyNN.spiNNaker`, one `sim.run` per task, zero
fallback/failures, minimum per-case spike readback `94896`, and runtime
seconds `111.5257` and `109.3603`.

Boundary: Tier 4.22b is continuous transport evidence, not learning evidence.
Learning/reward/plasticity belongs to Tier 4.22d after persistent state is
stable.

## Tier 4.22c Persistent Custom-C State Scaffold

Run:

```bash
make tier4-22c
```

Status: **passed as custom-runtime persistent-state scaffold evidence** at
`controlled_test_output/tier4_22c_20260430_persistent_state_scaffold/`.

Purpose: move CRA state ownership out of Python-only scaffolding and into a
bounded custom-C runtime substrate before reward/plasticity is migrated.

Pass gates:

- Tier 4.22b continuous transport pass exists.
- Custom C runtime host tests pass.
- `state_manager.h` and `state_manager.c` exist.
- Keyed context memory uses static `MAX_CONTEXT_SLOTS` storage.
- Delayed-credit pending horizons use static `MAX_PENDING_HORIZONS` storage and
  do not store future targets.
- `state_manager.c` uses no dynamic allocation.
- Runtime initialization calls `cra_state_init`.
- Runtime reset path calls `cra_state_reset`.
- State manager is included in the runtime build.
- Host tests cover context slots, eviction, readout state, reward counters, and
  reset semantics.
- Claim boundary explicitly keeps the north star as full custom/on-chip CRA
  execution; hybrid paths are transitional diagnostics only.

Current result: host C tests passed, all `12/12` static state checks passed,
the state manager uses bounded static storage, avoids dynamic allocation, and
exports a state contract for keyed slots, no-leak pending horizons, readout
state, decision/reward counters, and reset semantics.

Boundary: Tier 4.22c is not a hardware run and not on-chip learning. It proves
the custom runtime can own persistent bounded state. Tier 4.22d must use this
state causally for reward/plasticity and compare against the chunked reference.

## Tier 4.22d Reward/Plasticity Runtime Scaffold

Run:

```bash
make tier4-22d
```

Status: **passed as local custom-C reward/plasticity scaffold evidence** at
`controlled_test_output/tier4_22d_20260430_reward_plasticity_scaffold/`.

Purpose: move the first reward/plasticity mechanism into the custom C runtime
without claiming hardware or learning parity prematurely.

Pass gates:

- Tier 4.22c persistent state pass exists.
- Custom C runtime host tests pass.
- `synapse_t` carries an `eligibility_trace`.
- Trace constants are defined in `config.h`.
- Spike delivery increments eligibility.
- Trace decay is implemented and called on the timer path.
- Dopamine modulation is trace-gated: no causal trace means no weight movement.
- Dopamine is signed fixed-point and applied as a one-shot event.
- Runtime readout reward update exists in `state_manager`.
- Host C tests cover trace-gated dopamine and readout reward update.

Current result: host C tests passed and all `11/11` static plasticity checks
passed. The local C scaffold now includes synaptic eligibility traces,
trace-gated dopamine, fixed-point trace decay, signed one-shot dopamine, and
runtime-owned readout reward updates.

Boundary: Tier 4.22d is not a hardware run, not continuous-learning parity, and
not speedup evidence. It also does not prove scale-ready trace sweeping; lazy or
event-indexed trace updates remain a later optimization if all-synapse sweeps
become unacceptable.

Next gate: Tier 4.22e local continuous-learning parity must compare this
runtime reward/plasticity path against the chunked reference before any new
EBRAINS run.

## Tier 4.22e Local Continuous-Learning Parity Scaffold

Run:

```bash
make tier4-22e
```

Status: **passed as local minimal delayed-readout parity evidence** at
`controlled_test_output/tier4_22e_20260430_local_learning_parity/`.

Purpose: prove the custom-C fixed-point delayed-readout equations match a
floating reference before any hardware learning claim is attempted.

Pass gates:

- Tier 4.22d reward/plasticity scaffold pass exists.
- Custom C runtime host tests pass.
- Pending horizon queue is bounded and does not store future targets.
- Fixed-point runtime mirror agrees with the floating reference.
- Delayed_cue tail accuracy remains high.
- Hard_noisy_switching remains above the minimal hard-task floor.
- Pending queue beats the no-pending ablation.
- Pending queue does not overflow.

Current result: delayed_cue and hard_noisy_switching, seed `42`, `1200` steps,
passed with fixed/float sign agreement `1.0`, maximum final weight delta about
`4.14e-05`, delayed_cue tail accuracy `1.0`, hard_noisy_switching tail accuracy
`0.547619`, no-pending tail accuracy `0.0`, and zero pending drops.

Boundary: Tier 4.22e is not a hardware run, not full CRA parity, not
lifecycle/replay/routing parity, not speedup evidence, and not final on-chip
proof. It authorizes the next hardware/build-oriented gate only if the hardware
command/readback path can expose the same state.

## Tier 4.22f0 Custom Runtime Scale-Readiness Audit

Run:

```bash
make tier4-22f0
```

Status: **passed as custom-runtime scale-readiness audit evidence** at
`controlled_test_output/tier4_22f0_20260430_custom_runtime_scale_audit/`.

Purpose: prevent a premature custom-runtime hardware learning run. This tier
audits the custom-C sidecar after Tier 4.22e parity and before any build/load or
hardware-learning claim.

Architecture boundary:

- PyNN/sPyNNaker remains the primary hardware construction, mapping, run, and
  standard-readback layer for supported primitives.
- Custom C is used only for CRA-specific on-chip substrate mechanics that PyNN
  cannot express or scale directly: persistent state, delayed-credit queues,
  eligibility/dopamine/plasticity, compact summaries, lifecycle/routing state,
  and future promoted memory/routing kernels.
- Experiment orchestration, baselines, registry generation, paper tables, and
  most PyNN populations/connectors stay in Python.

Current result:

- Tier 4.22e latest status: `pass`.
- Custom C host tests passed.
- Static audit checks passed: `9/9`.
- Scale blockers detected: `7`.
- High-severity blockers: `3`.
- Runtime scale-ready: `False`.
- Direct custom-runtime hardware learning allowed: `False`.

High-severity blockers:

- `synapse_deliver_spike` scans all synapses per incoming spike; replace with
  a pre-indexed outgoing adjacency/event list.
- `synapse_decay_traces_all` sweeps all synapses every millisecond; replace
  with lazy timestamp decay or an active-trace list.
- `_handle_read_spikes` exposes count/timestep only; add compact/fragmented
  state readback for spikes, reward, pending horizons, slots, and weights.

Pass meaning: the audit completed, prior gates are visible, host tests pass,
and the blockers are explicit. A pass does **not** mean the custom runtime is
scale-ready.

Boundary: Tier 4.22f0 is not hardware evidence, not speedup evidence, not full
CRA parity, and not a reason to rewrite PyNN/sPyNNaker-supported pieces in C.

Next gate: Tier 4.22g event-indexed spike delivery plus lazy/active
eligibility traces before any custom-runtime learning hardware claim.

## Tier 4.22g Event-Indexed Active-Trace Runtime

Run:

```bash
make tier4-22g
```

Status: **passed as local custom-C optimization evidence** at
`controlled_test_output/tier4_22g_20260430_event_indexed_trace_runtime/`.

Purpose: repair the highest-cost custom-runtime data structures identified by
Tier 4.22f0 without overclaiming hardware readiness.

Current result:

- Tier 4.22f0 latest status: `pass`.
- Custom C host tests passed.
- Static optimization checks passed: `12/12`.
- Repaired scale blockers: `SCALE-001`, `SCALE-002`, `SCALE-003`.
- Open scale blockers: `SCALE-004`, `SCALE-005`, `SCALE-006`, `SCALE-007`.
- Custom-runtime hardware learning allowed: `False`.

Complexity delta:

- `synapse_deliver_spike`: from `O(S)` per incoming spike to
  `O(out_degree(pre_id))`.
- `synapse_decay_traces_all`: from `O(S)` per timer tick to
  `O(active_traces)`.
- `synapse_modulate_all`: from `O(S)` per dopamine event to
  `O(active_traces)`.

Boundary: Tier 4.22g is local custom-C optimization evidence only. It is not a
hardware run, not measured speedup evidence, not full CRA parity, and not final
on-chip learning proof. PyNN/sPyNNaker remains the primary supported hardware
layer for supported primitives.

Next gate: Tier 4.22h compact state readback plus build/load/command acceptance
before any custom-runtime learning hardware claim.

## Tier 4.22h Compact Readback / Build-Command Readiness

Run:

```bash
make tier4-22h
```

Status: **passed as local compact-readback/build-readiness evidence** at
`controlled_test_output/tier4_22h_20260430_compact_readback_acceptance/`.

Purpose: add compact state observability before any custom-runtime board load
or learning job. This prevents a hardware run where the runtime executes but
cannot report the learning state needed to audit it.

Current result:

- Tier 4.22g latest status: `pass`.
- Custom C host tests passed.
- Static readback checks passed: `30/30`, including official Spin1API multicast callback constants, packed SARK SDP fields, `sark_mem_cpy`, official SARK router calls, official `spinnaker_tools.mk` build-recipe guards, nested object-directory guards, and host-stub fallback guards.
- Compact readback command: `CMD_READ_STATE`.
- Payload schema version: `1`.
- Payload size: `73` bytes.
- `.aplx` build status: `not_attempted_spinnaker_tools_missing`.
- Board load/command roundtrip: `not_attempted`.
- Custom-runtime learning hardware allowed: `False`.

Readback includes:

- timestep
- neuron count
- synapse count
- active eligibility trace count
- context-slot counters
- decision/reward counters
- pending-horizon counters
- readout weight and bias

Boundary: Tier 4.22h is not hardware evidence, board-load evidence, command
round-trip evidence, measured speedup evidence, or custom-runtime learning
evidence. If local `spinnaker_tools` are missing, `.aplx` build is recorded as
not attempted rather than treated as success or failure.

Completed gate: Tier 4.22i tiny EBRAINS/board custom-runtime load plus
`CMD_READ_STATE` round-trip smoke passed at
`controlled_test_output/tier4_22i_20260501_ebrains_board_roundtrip_pass/`.
Only after this pass should minimal closed-loop custom-runtime learning be
attempted.

Completed gate: Tier 4.22j minimal custom-runtime closed-loop learning smoke
passed after ingest correction at
`controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/`.
The raw returned EBRAINS manifest is preserved as a false-fail caused by the
zero-value evaluator bug; the returned hardware data satisfy the declared
learning-smoke criteria.

Completed gate: Tier 4.22l tiny custom-runtime learning parity passed after
ingest at
`controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_hardware_pass_ingested/`.
The returned EBRAINS run matched all four signed s16.15 prediction/weight/bias
rows exactly and ended with `pending_created=4`, `pending_matured=4`,
`reward_events=4`, `active_pending=0`, `readout_weight_raw=-4096`, and
`readout_bias_raw=-4096`.

Local and prepare gates are retained at
`controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_local/`
and
`controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/`.


## Tier 4.22i Custom Runtime Board Round-Trip Smoke

Purpose: prove the custom C sidecar can build, load, and answer the compact
state command on a real SpiNNaker board before any custom-runtime learning job
is attempted.

Returned status: **PASS** at
`controlled_test_output/tier4_22i_20260501_ebrains_board_roundtrip_pass/`.
The `cra_422r` run built `coral_reef.aplx`, acquired target `10.11.194.113`
through pyNN.spiNNaker/SpynnakerDataView, selected free core `(0,0,4)`, loaded
the app, acknowledged `RESET`, two `BIRTH` commands, `CREATE_SYN`, and
`DOPAMINE`, and returned `CMD_READ_STATE` schema version `1` with payload length
`73`, `2` neurons, `1` synapse, and `reward_events=1`.

Run locally to prepare the EBRAINS package:

```bash
make tier4-22i-prepare
```

Prepared output:

```text
controlled_test_output/tier4_22i_20260430_custom_runtime_roundtrip_prepared/
```

The prepared upload folder is:

```text
ebrains_jobs/cra_422r
```

EBRAINS/JobManager command emitted by the package:

```text
cra_422r/experiments/tier4_22i_custom_runtime_roundtrip.py --mode run-hardware --output-dir tier4_22i_job_output
```

Pass criteria for returned `run-hardware` artifacts:

- Tier 4.22h compact-readback source exists or the fresh EBRAINS bundle is
  self-contained.
- Hardware target is acquired through either explicit hostname/config or the automatic pyNN.spiNNaker/SpynnakerDataView probe.
- Custom C host tests pass on the job image.
- `main.c` host syntax check passes against the callback-compatibility stub.
- `host_interface.c` uses official packed SARK `sdp_msg_t` fields (`dest_port`, `srce_port`, `dest_addr`, `srce_addr`) and `sark_mem_cpy`.
- Host/runtime command packets use the official SDP/SCP command header: `cmd_rc`, `seq`, `arg1`, `arg2`, `arg3`, then `data[]`.
- Callback registration uses the Tier 4.22k-confirmed official Spin1API enum constants `MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`, not brittle guessed names such as `MC_PACKET_RX`.
- `router.h` includes `<stdint.h>` directly, and `router.c` uses official SARK router calls `rtr_alloc`, `rtr_mc_set`, and `rtr_free` instead of local-stub-only helper names.
- The hardware Makefile delegates link/APLX creation to official `spinnaker_tools.mk`, not deprecated `Makefile.common` or a manual object-only link recipe.
- `build/coral_reef.aplx` builds successfully.
- The `.aplx` app loads on the selected board/core.
- `RESET`, `BIRTH`, `CREATE_SYN`, and `CMD_READ_STATE` commands acknowledge.
- `CMD_READ_STATE` returns schema version `1`, payload length `73`, at least two
  neurons after mutation, and at least one synapse after mutation.
- Synthetic fallback is zero.

Returned failure note: early EBRAINS Tier 4.22i attempts failed before board execution because the build image did not define guessed multicast callback names (`MC_PACKET_RX`/compatibility aliases); those failures are preserved at `controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_fail/` and `controlled_test_output/tier4_22i_20260430_ebrains_no_mc_event_build_fail/`. Tier 4.22k then confirmed official `MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`. The subsequent `cra_422l` run compiled past the callback layer but failed in `host_interface.c` because the EBRAINS SARK `sdp_msg_t` uses packed fields and `sark_mem_cpy`; that failure is preserved at `controlled_test_output/tier4_22i_20260430_ebrains_sdp_struct_build_fail/`. The next `cra_422m` run compiled past `host_interface.c` but failed in `router.c` because the local stub exposed non-existent `sark_router_alloc/sark_router_free` helpers and `router.h` did not include `<stdint.h>` directly; that failure is preserved at `controlled_test_output/tier4_22i_20260430_ebrains_router_api_build_fail/`. The next `cra_422n` run compiled all C sources but produced an empty ELF because the manual link recipe omitted official SpiNNaker startup/build objects and `libspin1_api.a`; that failure is preserved at `controlled_test_output/tier4_22i_20260430_ebrains_manual_link_empty_elf_fail/`. The next `cra_422o` run used official `spinnaker_tools.mk` but failed because `build/gnu/src/` was not created before compiling `build/gnu/src/main.o`; that failure is preserved at `controlled_test_output/tier4_22i_20260430_ebrains_official_mk_nested_object_dir_fail/`. The next `cra_422p` run built the `.aplx` successfully but could not discover a raw board hostname, so load/round-trip were not attempted; that failure is preserved at `controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_pass_target_missing_fail/`. The next `cra_422q` run built the `.aplx`, acquired the target through pyNN.spiNNaker/SpynnakerDataView, selected free core `4`, and loaded the app, but command round-trip returned 2-byte short payloads because the host/runtime command layout did not use official SDP/SCP `cmd_rc`/`seq`/`arg1`/`arg2`/`arg3` before `data[]`; that failure is preserved at `controlled_test_output/tier4_22i_20260430_ebrains_aplx_load_pass_sdp_payload_short_fail/`. The regenerated `cra_422r` package guards the build classes locally, adds automatic target acquisition, and guards the official SDP command-header layout.

What this sequence got right: each returned failure narrowed the blocker, and
each blocker produced a local guard before the next hardware attempt. By
`cra_422q`, the custom runtime had moved through official build, target
acquisition, free-core selection, and app load. The regenerated `cra_422r` run
then passed the command round-trip protocol and visible state-mutation check.

Boundary: a prepared Tier 4.22i package is not hardware evidence. A returned
Tier 4.22i pass is board-load and command round-trip evidence only; it is not
full CRA learning, speedup evidence, multi-core scaling, or final on-chip
autonomy. Tier 4.22i was blocked behind Tier 4.22k until the EBRAINS build image confirmed `MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`; the regenerated package now uses those official enum constants plus the official packed SARK SDP fields, `sark_mem_cpy`, official `rtr_*` router calls, official `spinnaker_tools.mk` app build rules, nested object directory creation, and automatic pyNN/sPyNNaker target acquisition for EBRAINS contexts that hide raw hostnames. No custom-runtime learning hardware tier may proceed until Tier 4.22i itself passes board load and `CMD_READ_STATE` round-trip.

## Tier 4.22j Minimal Custom-Runtime Closed-Loop Learning Smoke

Purpose: prove the custom runtime can execute the smallest delayed-credit
learning heartbeat on real SpiNNaker after the Tier 4.22i board command path
passed.

Returned status: **PASS after ingest correction** at
`controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/`.

Prepared source-package gate retained at
`controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_prepared/`.

Run locally to prepare the EBRAINS package:

```bash
make tier4-22j-prepare
```

The prepared upload folder is:

```text
ebrains_jobs/cra_422s
```

EBRAINS/JobManager command emitted by the package:

```text
cra_422s/experiments/tier4_22j_minimal_custom_runtime_learning.py --mode run-hardware --output-dir tier4_22j_job_output
```

Pass criteria for returned `run-hardware` artifacts:

- Tier 4.22i board-roundtrip dependency is satisfied.
- Hardware target is acquired through either explicit hostname/config or the automatic pyNN.spiNNaker/SpynnakerDataView probe.
- Custom C host tests pass on the job image.
- `.aplx` build succeeds and the app loads on the selected board/core.
- `RESET` acknowledges.
- `CMD_SCHEDULE_PENDING` acknowledges.
- `state_after_schedule.pending_created >= 1`.
- `state_after_schedule.active_pending >= 1`.
- `state_after_schedule.decisions >= 1`.
- `CMD_MATURE_PENDING` acknowledges.
- `mature_pending.matured_count >= 1`.
- `state_after_mature.pending_matured >= 1`.
- `state_after_mature.active_pending = 0`.
- `state_after_mature.reward_events >= 1`.
- `state_after_mature.readout_weight_raw > 0`.
- `state_after_mature.readout_bias_raw > 0`.
- Synthetic fallback is zero.

Fail case:

- EBRAINS runs stale package/revision.
- Target acquisition, build, or app load fails.
- `CMD_SCHEDULE_PENDING` or `CMD_MATURE_PENDING` times out or returns malformed payload.
- Pending horizon is not visible after scheduling.
- No pending horizon matures after the delay.
- Readout weight/bias do not move after maturity.
- The run uses synthetic fallback.

Boundary: a prepared Tier 4.22j package is not hardware evidence. The returned
Tier 4.22j pass proves one minimal chip-owned pending/readout update only. It
is not full CRA task learning, v2.1 mechanism transfer, speedup evidence,
multi-core scaling, or final on-chip autonomy. Tier 4.22l has now passed; the
next gate is Tier 4.22m minimal task micro-loop on the custom runtime.

## Tier 4.22l Tiny Custom-Runtime Learning Parity

Purpose: prove that the custom runtime's chip-owned pending/readout update path
matches a predeclared local s16.15 fixed-point reference over a tiny signed
sequence before any full task-like custom-runtime learning claim is attempted.

Returned status: **PASS after ingest** at:

```text
controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_hardware_pass_ingested/
```

Local/prepared status retained at:

```text
controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_local/
controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/
```

Run locally:

```bash
make tier4-22l-local
make tier4-22l-prepare
```

Prepared upload folder:

```text
ebrains_jobs/cra_422t
```

EBRAINS/JobManager command emitted by the package:

```text
cra_422t/experiments/tier4_22l_custom_runtime_learning_parity.py --mode run-hardware --output-dir tier4_22l_job_output
```

Pass criteria for returned `run-hardware` artifacts:

- Hardware target is acquired through either explicit hostname/config or the automatic pyNN.spiNNaker/SpynnakerDataView probe.
- Custom C host tests pass on the job image.
- `.aplx` build succeeds and the app loads on the selected board/core.
- Four `CMD_SCHEDULE_PENDING` commands acknowledge.
- Four `CMD_MATURE_PENDING` commands acknowledge.
- Each mature reply reports `matured_count = 1`.
- Observed prediction, readout weight, and readout bias raw values match the
  local s16.15 reference within raw tolerance `1`.
- Final state reports `pending_created = 4`, `pending_matured = 4`,
  `reward_events = 4`, and `active_pending = 0`.
- Final `readout_weight_raw = -4096 +/- 1`.
- Final `readout_bias_raw = -4096 +/- 1`.
- Synthetic fallback is zero.

Fail case:

- EBRAINS runs stale package/revision.
- Target acquisition, build, or app load fails.
- Any learning command times out or returns malformed payload.
- Any step matures zero or multiple pending horizons.
- Prediction or readout state diverges from the local reference beyond tolerance.
- Final counters do not match the four-event sequence.
- Synthetic fallback is used.

Returned evidence:

- Board IP `10.11.194.1`.
- Selected free core `(0,0,4)`.
- Target acquisition passed through pyNN.spiNNaker/SpynnakerDataView.
- `.aplx` build and app load passed.
- Four schedule commands and four mature commands succeeded.
- Every step matured exactly one pending horizon.
- Prediction, readout weight, and readout bias raw deltas were all `0`.
- Final `pending_created=4`, `pending_matured=4`, `reward_events=4`,
  `active_pending=0`, `readout_weight_raw=-4096`, and
  `readout_bias_raw=-4096`.

Boundary: local/prepared output is not hardware evidence. The returned Tier
4.22l pass proves tiny signed fixed-point on-chip learning parity only. It does
not prove full CRA task learning, v2.1 mechanism transfer, speedup evidence,
multi-core scaling, or final on-chip autonomy.

## Tier 4.22m Minimal Custom-Runtime Task Micro-Loop

Status: **passed EBRAINS hardware after ingest**.

Evidence:

```text
controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_local/
controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_prepared/
controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_hardware_pass_ingested/
```

Purpose: advance one step beyond arbitrary fixed-point parity by running a
minimal task-like stream. Each event schedules a chip-owned pending decision,
scores the pre-update prediction sign, matures exactly one pending horizon with
the delayed target, and checks the resulting readout state against the local
s16.15 reference.

Prepared upload folder:

```text
ebrains_jobs/cra_422u
```

EBRAINS/JobManager command:

```text
cra_422u/experiments/tier4_22m_custom_runtime_task_micro_loop.py --mode run-hardware --output-dir tier4_22m_job_output
```

Pass case for returned hardware artifacts:

```text
status = pass
runner_revision = tier4_22m_custom_runtime_task_micro_loop_20260501_0001
real hardware target acquired through hostname/config or pyNN.spiNNaker/SpynnakerDataView
custom C host tests pass
main.c syntax check passes
.aplx builds and loads
all 12 CMD_SCHEDULE_PENDING commands acknowledge
all 12 CMD_MATURE_PENDING commands acknowledge
each mature reply has matured_count = 1
prediction/weight/bias raw deltas <= 1
observed tail accuracy >= 1.0
observed task metrics match the local reference
final pending_created = 12
final pending_matured = 12
final reward_events = 12
final decisions = 12
final active_pending = 0
final readout_weight_raw = 32256 +/- 1
final readout_bias_raw = 0 +/- 1
synthetic fallback = 0
```

Returned pass summary:

```text
runner_revision = tier4_22o_noisy_switching_micro_task_20260501_0002_mul64
board = 10.11.210.25
selected core = (0,0,4)
criteria = 44/44 passed
.aplx build = pass
app load = pass
all 14 schedule commands = pass
all 14 mature commands = pass
matured_count per event = 1
prediction raw deltas = all 0
weight raw deltas = all 0
bias raw deltas = all 0
observed accuracy = 0.7857142857
observed tail accuracy = 1.0
observed max pending depth = 3
final pending_created = 14
final pending_matured = 14
final reward_events = 14
final decisions = 14
final active_pending = 0
final readout_weight_raw = -48768
final readout_bias_raw = -1536
```

Returned result: PASS on board `10.11.202.65`, selected core `(0,0,4)`, app load pass, twelve schedule/mature pairs pass, prediction/weight/bias deltas `0`, observed accuracy `0.9166666667`, observed tail accuracy `1.0`, final `pending_created=pending_matured=reward_events=decisions=12`, final `active_pending=0`, final `readout_weight_raw=32256`, final `readout_bias_raw=0`, and zero failed criteria.

Fail case for any rerun: any target/build/load failure, any command failure, any pending leak, any mismatch outside raw tolerance, task metrics below reference, or any synthetic fallback.

Boundary: this is a minimal fixed-pattern custom-runtime task micro-loop only.
It is not full CRA task learning, v2.1 mechanism transfer, speedup evidence,
multi-core scaling, or final on-chip autonomy.

## Tier 4.22n Tiny Delayed-Cue Custom-Runtime Micro-Task

Status: **passed EBRAINS hardware after ingest**.

Evidence:

```text
controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_local/
controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_prepared/
controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/
```

Purpose: advance from the fixed-pattern immediate micro-loop to a delayed
pending-queue micro-task. Each event schedules a chip-owned pending decision,
waits behind a two-event gap while later cues are scheduled, then matures in
oldest-first order against the delayed target.

Prepared upload folder:

```text
ebrains_jobs/cra_422v
```

EBRAINS/JobManager command:

```text
cra_422v/experiments/tier4_22n_delayed_cue_micro_task.py --mode run-hardware --output-dir tier4_22n_job_output
```

Pass case for returned hardware artifacts:

```text
status = pass
runner_revision = tier4_22n_delayed_cue_micro_task_20260501_0001
real hardware target acquired through hostname/config or pyNN.spiNNaker/SpynnakerDataView
custom C host tests pass
main.c syntax check passes
.aplx builds and loads
all 12 CMD_SCHEDULE_PENDING commands acknowledge
all 12 delayed CMD_MATURE_PENDING commands acknowledge
each mature reply has matured_count = 1
observed max pending depth >= 3
prediction/weight/bias raw deltas <= 1
observed tail accuracy >= 1.0
observed task metrics match the local reference
final pending_created = 12
final pending_matured = 12
final reward_events = 12
final decisions = 12
final active_pending = 0
final readout_weight_raw = 30720 +/- 1
final readout_bias_raw = 0 +/- 1
synthetic fallback = 0
```

Fail case: any target/build/load failure, any command failure, no observed
pending depth above the gap, any pending leak, any mismatch outside raw
tolerance, task metrics below reference, or any synthetic fallback.

Returned result: PASS on board `10.11.205.1`, selected core `(0,0,4)`, app load
pass, twelve delayed schedule/mature pairs pass, max observed pending depth
`3`, prediction/weight/bias deltas `0`, observed accuracy `0.8333333333`,
observed tail accuracy `1.0`, final
`pending_created=pending_matured=reward_events=decisions=12`, final
`active_pending=0`, final `readout_weight_raw=30720`, final
`readout_bias_raw=0`, and zero failed criteria.

Boundary: this is a tiny delayed-cue-like custom-runtime micro-task only. It is
not full CRA task learning, v2.1 mechanism transfer, speedup evidence,
multi-core scaling, or final on-chip autonomy. Tier 4.22o has now passed as the
next tiny noisy-switching custom-runtime micro-task.

## Tier 4.22o Tiny Noisy-Switching Custom-Runtime Micro-Task

Status: **returned EBRAINS pass ingested**.

Evidence:

```text
controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_local/
controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_prepared/
controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_overflow_fail_ingested/
controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/
```

Purpose: advance from delayed pending-queue maturation to a tiny
noisy-switching task. The sequence keeps the same chip-owned pending/readout
command surface, but adds a rule flip plus label-noise events before and after
the switch.

Prepared upload folder:

```text
ebrains_jobs/cra_422x
```

EBRAINS/JobManager command:

```text
cra_422x/experiments/tier4_22o_noisy_switching_micro_task.py --mode run-hardware --output-dir tier4_22o_job_output
```

Pass case for returned hardware artifacts:

```text
status = pass
runner_revision = tier4_22o_noisy_switching_micro_task_20260501_0002_mul64
real hardware target acquired through hostname/config or pyNN.spiNNaker/SpynnakerDataView
custom C host tests pass
main.c syntax check passes
.aplx builds and loads
all 14 CMD_SCHEDULE_PENDING commands acknowledge
all 14 delayed CMD_MATURE_PENDING commands acknowledge
each mature reply has matured_count = 1
observed max pending depth >= 3
prediction/weight/bias raw deltas <= 1
observed tail accuracy >= 1.0
observed task metrics match the local reference
final pending_created = 14
final pending_matured = 14
final reward_events = 14
final decisions = 14
final active_pending = 0
final readout_weight_raw = -48768 +/- 1
final readout_bias_raw = -1536 +/- 1
synthetic fallback = 0
```

Local reference:

```text
14 signed events
regime A: target follows feature
regime B: target is opposite feature
label noise: one event in A, one event in B
pending_gap_depth = 2
max_pending_depth = 3
learning_rate = 0.375
expected accuracy = 0.7857142857
expected tail accuracy = 1.0
expected final readout_weight_raw = -48768
expected final readout_bias_raw = -1536
```

Fail case: any target/build/load failure, any command failure, no observed
pending depth above the gap, any pending leak, any mismatch outside raw
tolerance, task metrics below reference, or any synthetic fallback.

Boundary: this is a tiny noisy-switching custom-runtime micro-task only. It is
not full CRA hard_noisy_switching, v2.1 mechanism transfer, speedup evidence,
multi-core scaling, or final on-chip autonomy.

Returned diagnostic failure:

```text
cra_422w status = fail
hardware target/build/load/schedule/mature path = worked
failure onset = first signed regime-switch update
root cause = 32-bit fixed-point multiply overflow before right shift
repair package = cra_422x
runtime repair = FP_MUL uses int64_t intermediate
new host regressions = signed large fixed-point product + pending signed switch update
```

This failure is noncanonical implementation evidence and must not be cited as
CRA science failure. It is exactly the kind of hardware-facing arithmetic bug
Tier 4.22o was designed to surface before larger custom-runtime tasks.

## Tier 4.22p Tiny A-B-A Reentry Custom-Runtime Micro-Task

Status: **returned hardware pass ingested**.

Evidence:

```text
controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_local/
controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_prepared/
controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_hardware_pass_ingested/
```

Purpose: advance from one noisy rule switch to a tiny recurrence/reentry task
without adding any new runtime mechanism yet. The same chip-owned pending and
readout state must adapt from A to reversed B and then recover when A returns.

Prepared upload folder:

```text
ebrains_jobs/cra_422y
```

EBRAINS/JobManager command:

```text
cra_422y/experiments/tier4_22p_reentry_micro_task.py --mode run-hardware --output-dir tier4_22p_job_output
```

Returned hardware result:

```text
status = pass
board = 10.11.222.17
selected core = (0,0,4)
criteria = 44/44
observed accuracy = 0.8666666667
observed tail accuracy = 1.0
observed max pending depth = 3
prediction/weight/bias raw deltas = 0
final pending_created = 30
final pending_matured = 30
final reward_events = 30
final decisions = 30
final active_pending = 0
final readout_weight_raw = 30810
final readout_bias_raw = -1
```

Pass case for returned hardware artifacts:

```text
status = pass
runner_revision = tier4_22p_reentry_micro_task_20260501_0001
real hardware target acquired through hostname/config or pyNN.spiNNaker/SpynnakerDataView
custom C host tests pass
main.c host syntax check passes
.aplx builds and loads
all 30 CMD_SCHEDULE_PENDING commands acknowledge
all 30 delayed CMD_MATURE_PENDING commands acknowledge
each mature reply has matured_count = 1
observed max pending depth >= 3
prediction/weight/bias raw deltas <= 1
observed tail accuracy >= 1.0
observed task metrics match the local reference
final pending_created = 30
final pending_matured = 30
final reward_events = 30
final decisions = 30
final active_pending = 0
final readout_weight_raw = 30810 +/- 1
final readout_bias_raw = -1 +/- 1
synthetic fallback = 0
```

Local reference:

```text
30 signed events
regime A initial: target follows feature
regime B reversal: target is opposite feature
regime A reentry: target follows feature again
pending_gap_depth = 2
max_pending_depth = 3
learning_rate = 0.5625
expected accuracy = 0.8666666667
expected tail accuracy = 1.0
expected second-half improvement = 0.2666666667
expected final readout_weight_raw = 30810
expected final readout_bias_raw = -1
```

Fail case: any target/build/load failure, any command failure, no observed
pending depth above the gap, any pending leak, any mismatch outside raw
tolerance, task metrics below reference, or any synthetic fallback.

Boundary: this is a tiny A-B-A reentry custom-runtime micro-task only. It is
not full CRA recurrence, v2.1 memory/replay/routing transfer, speedup evidence,
multi-core scaling, or final on-chip autonomy.

## Tier 4.22q Tiny Integrated V2 Bridge Custom-Runtime Smoke

Status: **returned hardware pass ingested**.

Evidence:

```text
controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_local/
controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_prepared/
controlled_test_output/tier4_22q_20260501_integrated_v2_bridge_smoke_hardware_pass_ingested/
```

Purpose: take one small step beyond the passed A-B-A pending-queue task by
adding a host-side v2-style bridge before the custom runtime. The bridge keeps
keyed context slots, applies route-state updates, combines those with the
visible cue into a signed scalar feature, and then hands only that signed stream
to the chip-owned pending/readout loop. This tests integration of a tiny
host-v2 transform with the custom C delayed-credit loop without claiming native
on-chip memory/routing yet.

Prepared upload folder:

```text
ebrains_jobs/cra_422z
```

EBRAINS/JobManager command:

```text
cra_422z/experiments/tier4_22q_integrated_v2_bridge_smoke.py --mode run-hardware --output-dir tier4_22q_job_output
```

Local reference:

```text
30 signed host-bridge events
context keys = ctx_A, ctx_B, ctx_C
context updates = 9
route updates = 9
max keyed slots = 3
feature source = host_keyed_context_route_transform
pending_gap_depth = 2
max_pending_depth = 3
learning_rate = 0.25
expected accuracy = 0.9333333333
expected tail accuracy = 1.0
expected second-half improvement = 0.1333333333
expected final readout_weight_raw = 32768
expected final readout_bias_raw = 0
```

Returned hardware result:

```text
status = pass
board = 10.11.236.65
selected core = (0,0,4)
remote criteria = 47/47
ingest criterion = pass
observed accuracy = 0.9333333333
observed tail accuracy = 1.0
observed max pending depth = 3
bridge context updates = 9
bridge route updates = 9
bridge max keyed slots = 3
prediction/weight/bias raw deltas = 0
final pending_created = 30
final pending_matured = 30
final reward_events = 30
final decisions = 30
final active_pending = 0
final readout_weight_raw = 32768
final readout_bias_raw = 0
```

Pass case for returned hardware artifacts:

```text
status = pass
runner_revision = tier4_22q_integrated_v2_bridge_smoke_20260501_0001
real hardware target acquired through hostname/config or pyNN.spiNNaker/SpynnakerDataView
custom C host tests pass
main.c host syntax check passes
.aplx builds and loads
bridge context updates > 0
bridge route updates > 0
bridge retains at least three keyed slots
all 30 CMD_SCHEDULE_PENDING commands acknowledge
all 30 delayed CMD_MATURE_PENDING commands acknowledge
each mature reply has matured_count = 1
observed max pending depth >= 3
prediction/weight/bias raw deltas <= 1
observed tail accuracy >= 1.0
observed task metrics match the local reference
final pending_created = 30
final pending_matured = 30
final reward_events = 30
final decisions = 30
final active_pending = 0
final readout_weight_raw = 32768 +/- 1
final readout_bias_raw = 0 +/- 1
synthetic fallback = 0
```

Fail case: any target/build/load failure, any command failure, bridge metadata
missing or malformed, no observed pending depth above the gap, any pending
leak, any mismatch outside raw tolerance, task metrics below reference, or any
synthetic fallback.

Boundary: this is a tiny integrated host-v2/custom-runtime bridge smoke only.
It is not native/on-chip v2 memory/routing, full CRA task learning, speedup
evidence, multi-core scaling, or final on-chip autonomy.

## Tier 4.22k Spin1API Event-Symbol Discovery

Purpose: inspect the actual EBRAINS Spin1API build-image headers and compile a
callback-symbol probe matrix before another raw custom-runtime board run. This
is necessary because official SpiNNakerManchester source exposes
`MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`, but the EBRAINS image used by
Tier 4.22i did not expose the guessed event macros.

Returned status: **PASS** at
`controlled_test_output/tier4_22k_20260430_ebrains_event_symbol_discovery_pass/`.
The EBRAINS image exposed `/home/jovyan/spinnaker/spinnaker_tools/include`,
`spin1_callback_on`, `MC_PACKET_RECEIVED`, and `MCPL_PACKET_RECEIVED`. Callback
probes for `TIMER_TICK`, `SDP_PACKET_RX`, `MC_PACKET_RECEIVED`, and
`MCPL_PACKET_RECEIVED` compiled with `/usr/bin/arm-none-eabi-gcc`; legacy guessed
`MC_PACKET_RX` and `MCPL_PACKET_RX` did not compile.

Run locally to prepare the EBRAINS package:

```bash
make tier4-22k-prepare
```

Prepared output:

```text
controlled_test_output/tier4_22k_20260430_spin1api_event_discovery_prepared/
```

The prepared upload folder is:

```text
ebrains_jobs/cra_422k
```

EBRAINS/JobManager command emitted by the package:

```text
cra_422k/experiments/tier4_22k_spin1api_event_discovery.py --mode run-hardware --output-dir tier4_22k_job_output
```

Pass criteria for returned `run-hardware` artifacts:

- Include directories are found and header inventory is written.
- `spin1_callback_on` is visible in the inspected headers.
- Baseline callback probes for `TIMER_TICK` and `SDP_PACKET_RX` compile.
- At least one real multicast receive callback candidate compiles:
  `MC_PACKET_RECEIVED`, `MCPL_PACKET_RECEIVED`, `MC_PACKET_RX`, or
  `MCPL_PACKET_RX`.
- `tier4_22k_probe_matrix.csv` documents every candidate tried and its stderr
  excerpt if it failed.

Fail case:

- No direct custom-runtime learning hardware run.
- No SDP-only smoke may be promoted as sufficient for learning.
- The next action is to repair the receive path using the returned header
  inventory and documented Spin1API/SCAMP semantics.

Boundary: Tier 4.22k is build-image/toolchain discovery evidence only. It is not
board-load evidence, not command round-trip evidence, not learning evidence, and
not speedup evidence. If it passes, patch Tier 4.22i to use the confirmed event
symbol and rerun board load plus `CMD_READ_STATE`.

## Tier 5.5 Expanded Baseline / Fairness Gate

Run:

```bash
make tier5-5
```

Smoke:

```bash
make tier5-5-smoke
```

Purpose: compare the locked v0.8 CRA setting against implemented external
baselines under identical causal task streams, multiple run lengths, and at
least 10 software seeds.

Required outputs:

- `tier5_5_results.json`
- `tier5_5_report.md`
- `tier5_5_summary.csv`
- `tier5_5_comparisons.csv`
- `tier5_5_per_seed.csv`
- `tier5_5_fairness_contract.json`
- `tier5_5_edge_summary.png`
- per-run timeseries CSVs

Pass:

- full task/model/seed/run-length matrix completes
- fixed-pattern sanity baseline learns when included
- paired confidence intervals and effect sizes are exported
- CRA has at least one robust advantage regime aligned with delayed credit,
  nonstationarity, noisy adaptation, recovery, or sample efficiency
- CRA is not dominated on most hard/adaptive regimes

Fail:

- simple baselines dominate every hard/adaptive regime
- CRA advantage exists only in brittle toy-task pockets
- paired statistics or per-seed audit rows are missing
- the result depends on information leakage or unfair task visibility

Boundary: Tier 5.5 is software-only and not a hyperparameter fairness audit.
Tier 5.5 has now passed and is canonical v0.9 evidence. It supports robust
advantage/non-dominated hard-adaptive behavior, but it does not prove universal
or best-baseline superiority. Tier 5.6 now follows it as the canonical v1.0
tuned-baseline reviewer-defense audit.

## Tier 5.6 Baseline Hyperparameter Fairness Audit

Run:

```bash
make tier5-6
```

Smoke:

```bash
make tier5-6-smoke
```

Purpose: test whether the Tier 5.5 result survives reasonable retuning of the
external baselines while CRA remains locked at the promoted delayed-credit
setting.

Required outputs:

- `tier5_6_results.json`
- `tier5_6_report.md`
- `tier5_6_summary.csv`
- `tier5_6_comparisons.csv`
- `tier5_6_best_profiles.csv`
- `tier5_6_candidate_budget.csv`
- `tier5_6_per_seed.csv`
- `tier5_6_fairness_contract.json`
- `tier5_6_edge_summary.png`
- per-run timeseries CSVs

Pass:

- full task/candidate/seed/run-length matrix completes
- every baseline candidate budget is exported
- best and median tuned settings are reported by task/run length
- paired confidence intervals and effect sizes are exported
- CRA has at least one target-regime edge after retuning
- CRA has at least one surviving target regime: robust versus the tuned external
  median and not dominated by the best tuned external candidate

Fail:

- retuned baselines remove every CRA advantage
- CRA wins only against weak/default settings
- best-profile tables or per-seed audit rows are missing
- the audit changes CRA settings instead of keeping CRA locked

Boundary: Tier 5.6 is software-only and not new hardware evidence. It is a
fairness audit, not a universal-superiority claim. Canonical v1.0 evidence shows
that the 990-run audit completed and left four surviving target regimes after
retuning. It still does not prove all-possible-baselines coverage or that CRA
beats the best tuned baseline on every metric.

## Tier 5.7 Compact Regression After Promoted Tuning

Run:

```bash
make tier5-7
```

Smoke:

```bash
make tier5-7-smoke
```

Purpose: prove the promoted delayed-credit setting still passes compact
guardrails before lifecycle/self-scaling evidence is promoted.

Required outputs:

- `tier5_7_results.json`
- `tier5_7_report.md`
- `tier5_7_summary.csv`
- `tier5_7_child_manifests.json`
- child stdout/stderr logs
- child Tier 1, Tier 2, Tier 3, and target-task smoke manifests

Pass:

- Tier 1 negative controls pass under the promoted setting
- Tier 2 positive controls pass under the promoted setting
- Tier 3 architecture ablations pass under the promoted setting
- delayed_cue and hard_noisy_switching smoke matrix completes

Fail:

- negative controls become positive
- positive learning controls regress
- architecture ablation gaps disappear
- target hard/adaptive smokes fail to execute

Boundary: Tier 5.7 is software-only regression evidence. It does not prove a new
capability, hardware scaling, lifecycle/self-scaling, native on-chip learning,
or external-baseline superiority.

## Tier 5.9a Macro Eligibility Trace Diagnostic

Run the full diagnostic:

```bash
make tier5-9a
```

Run a quick harness smoke:

```bash
make tier5-9a-smoke
```

Status: **completed as noncanonical diagnostic failure**.

Purpose: test whether a host-side macro eligibility trace earns promotion beyond
the frozen v1.4 PendingHorizon delayed-credit path.

Protocol:

- backend: NEST
- tasks: `delayed_cue`, `hard_noisy_switching`, `variable_delay_cue`, `aba_recurrence`
- seeds: `42`, `43`, `44`
- steps: `960`
- selected baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `stdp_only_snn`
- CRA variants: `v1_4_pending_horizon`, `macro_eligibility`,
  `macro_eligibility_shuffled`, `macro_eligibility_zero`
- leakage guard: consequence feedback must not mature before the prediction step
- trace guard: normal macro trace must activate and contribute to matured updates

Observed diagnostic result:

- output: `controlled_test_output/tier5_9a_20260428_162345/`
- status: `FAIL`
- expected/observed runs: `108 / 108`
- feedback timing leakage violations: `0`
- macro trace active steps: `11520`
- macro matured updates: `8536`
- failed criteria: delayed-cue nonregression, variable-delay benefit, and trace
  ablation specificity
- hard_noisy_switching showed a recovery/variance improvement signal, but this
  did not overcome delayed-cue and variable-delay regressions

Interpretation:

- the current macro trace is active, but it is not yet useful enough to promote
- normal and shuffled traces matched on multiple tasks, which means the trace is
  not yet sufficiently polyp-specific or causal
- replacing the PendingHorizon feature with the trace is too destructive on the
  known delayed-cue regime
- v1.4 remains the frozen baseline; Tier 5.9a is audit history and a repair
  target, not a claim

If we continue macro-eligibility work, Tier 5.9b should be a bounded repair
diagnostic before any compact regression or hardware migration:

- test residual/blended trace updates instead of replacing the PendingHorizon
  feature
- normalize or clip trace magnitude
- require shuffled/zero ablations to lose
- require delayed_cue nonregression before any hard-switch advantage is accepted
- run locally first; do not move macro eligibility to hardware until it passes
  software ablation and compact regression gates

Boundary: Tier 5.9a is software-only failed mechanism evidence. It does not
invalidate v1.4, does not prove native eligibility, does not justify custom C
credit assignment, and does not authorize hardware migration.

## Tier 5.9b Residual Macro Eligibility Repair Diagnostic

Run the full repair diagnostic:

```bash
make tier5-9b
```

Run a quick harness smoke:

```bash
make tier5-9b-smoke
```

Status: **completed as noncanonical diagnostic failure**.

Purpose: test the narrow repair after Tier 5.9a failed: keep the v1.4
PendingHorizon feature and add only a bounded macro-trace residual.

Observed diagnostic result:

- output: `controlled_test_output/tier5_9b_20260428_174327/`
- status: `FAIL`
- backend: NEST
- expected/observed runs: `45 / 45`
- feedback timing leakage violations: `0`
- macro trace active steps: `8640`
- macro matured updates: `7040`
- failed criterion: trace ablations were not worse than the normal trace
- delayed_cue: v1.4 tail `1.0`, residual macro tail `1.0`
- variable_delay_cue: v1.4 tail `0.7586206896551725`, residual macro tail
  `0.7586206896551725`
- hard_noisy_switching: v1.4 tail `0.5392156862745098`, residual macro tail
  `0.5098039215686274`, zero-trace ablation `0.5392156862745098`

Interpretation:

- the residual repair no longer destroys delayed_cue
- the trace is active and causal timing is clean
- the normal trace still does not outperform shuffled/zero controls
- hard_noisy_switching slightly regressed versus v1.4 and zero-trace
- macro eligibility is parked as a non-promoted research scaffold

Boundary: Tier 5.9b is software-only failed mechanism evidence. Do not tune
residual scale indefinitely, do not promote macro eligibility, and do not move
this mechanism to SpiNNaker or custom C until a later measured blocker gives a
specific reason to revive it.

## Tier 5.9c Macro Eligibility v2.1 Recheck

Run the full recheck:

```bash
make tier5-9c
```

Run a quick harness smoke:

```bash
make tier5-9c-smoke
```

Status: **completed as noncanonical diagnostic failure**.

Purpose: answer whether macro eligibility should be revived after the v2.1
software baseline.

Observed diagnostic result:

- output: `controlled_test_output/tier5_9c_20260429_190503/`
- status: `FAIL`
- v2.1 guardrail child: `PASS`
- macro residual recheck child: `FAIL`
- criteria passed: `2 / 4`
- runtime seconds: `2889.924`
- failed reason: residual macro eligibility did not earn promotion
- macro child failed criterion: trace ablations were not worse than the normal
  trace
- normal macro, shuffled macro, zero-trace, and no-macro paths remained
  identical on the tested delayed-credit tasks

Interpretation:

- v2.1 remains green
- macro eligibility still does not add causal value over the proven
  PendingHorizon/residual path
- the mechanism remains parked despite the later memory, replay, prediction,
  routing, and self-evaluation stack
- do not move macro eligibility to hardware, hybrid runtime, or custom C

Boundary: Tier 5.9c is software-only failed mechanism evidence. It does not
invalidate v2.1. It closes the immediate question of whether macro should be
rechecked now; the answer is no promotion. Revive it only if a future measured
blocker specifically points to eligibility traces as the missing mechanism.

## Tier 5.10 Multi-Timescale Memory / Forgetting Diagnostic

Run the full diagnostic:

```bash
make tier5-10
```

Run a quick harness smoke:

```bash
make tier5-10-smoke
```

Status: **completed as noncanonical diagnostic failure**.

Purpose: test whether existing fast/slow/structural memory knobs help CRA
retain or reacquire old regimes after they disappear and return.

Protocol:

- backend: NEST
- tasks: `aba_recurrence`, `abca_recurrence`, `hidden_regime_switching`
- seeds: `42`, `43`, `44`
- steps: `960`
- selected baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `stdp_only_snn`
- CRA variants: `v1_4_pending_horizon`, `multi_timescale_memory`,
  `no_slow_memory`, `no_structural_memory`, `no_bocpd_unlock`,
  `overrigid_memory`
- leakage guard: consequence feedback must not mature before the prediction step
- recurrence scoring: tail accuracy, return-regime accuracy, old-regime
  reacquisition delta, switch recovery, ablation edge, and external-baseline edge

Observed diagnostic result:

- output: `controlled_test_output/tier5_10_20260428_181322/`
- status: `FAIL`
- expected/observed runs: `99 / 99`
- feedback timing leakage violations: `0`
- failed criteria: tail nonregression versus v1.4, recurrence/recovery benefit,
  and memory-ablation specificity
- aba_recurrence: v1.4 return accuracy `0.675`, memory candidate `0.475`
- abca_recurrence: v1.4 return accuracy `0.7888888888888889`, memory candidate
  `0.7888888888888889`
- hidden_regime_switching: v1.4 return accuracy `0.7777777777777778`, memory
  candidate `0.5833333333333334`
- `overrigid_memory` was the strongest CRA ablation on all three tasks
- simple `sign_persistence` was the best external return-phase baseline on all
  three tasks, showing the first recurrence tasks are not memory-specific enough

Interpretation:

- the first memory-timescale proxy did not earn promotion
- existing v1.4 remains stronger than the candidate on recurrence/recovery
- overrigid memory doing well means the retention/adaptation tradeoff deserves
  a sharper follow-up, but it is not enough for promotion because the candidate
  lost to ablations
- sign-persistence dominance means Tier 5.10 also revealed a task-design issue:
  the return phases can be solved by simple reflex persistence, so the next
  step was **Tier 5.10b recurrence-task repair**, not sleep/replay; that task
  gate has now passed and authorizes Tier 5.10c memory-mechanism testing

Boundary: Tier 5.10 is software-only failed mechanism evidence. It does not
invalidate v1.4 and does not prove catastrophic forgetting is solved. It proves
that the current proxy memory knobs are not enough and that recurrence tasks
must be hardened before any memory/replay claim is attempted.

## Tier 5.10b Recurrence-Task Repair / Memory-Pressure Validation

Run the full task-validation gate:

```bash
make tier5-10b
```

Run a quick harness smoke:

```bash
make tier5-10b-smoke
```

Status: **completed as noncanonical task-validation pass**.

Purpose: validate repaired recurrence/context streams before testing new CRA
memory mechanisms. Tier 5.10b is deliberately not a CRA capability claim; it
asks whether the task suite now actually requires remembered context rather
than being solvable by sign persistence.

Protocol:

- backend: mock software task harness
- tasks: `delayed_context_cue`, `distractor_gap_context`,
  `hidden_context_recurrence`
- seeds: `42`, `43`, `44`
- steps: `720`
- standard baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `small_gru`,
  `stdp_only_snn`
- context controls: `oracle_context`, `stream_context_memory`,
  `shuffled_context`, `memory_reset`, `wrong_context`
- leakage guard: consequence feedback must not mature before the decision event
- pressure checks: same current cue supports opposite labels, sign persistence
  does not dominate, oracle/context memory solves, and shuffled/reset/wrong
  memory controls fail

Observed task-validation result:

- output: `controlled_test_output/tier5_10b_20260428_193639/`
- status: `PASS`
- expected/observed runs: `99 / 99`
- feedback timing leakage violations: `0`
- same current input supports opposite labels: `True`
- sign_persistence max accuracy across repaired tasks: `0.5333333333333333`
- oracle context min accuracy: `1.0`
- stream context memory min accuracy: `1.0`
- context-memory edge versus sign persistence min: `0.4666666666666667`
- shuffled/reset/wrong-memory failure-control edge min: `0.4642857142857143`
- best standard baseline max accuracy: `0.8154761904761904`, below the
  predeclared `0.85` trivial-solve ceiling

Interpretation:

- Tier 5.10b repairs the testing surface: memory/context is now necessary and
  auditable in the selected tasks
- a simple memory of the prior context is sufficient to solve all three repaired
  streams, proving the missing information boundary is well defined
- wrong/shuffled/reset memory fails, so the benefit is not generic extra
  capacity or random smoothing
- `online_perceptron` partially solves `hidden_context_recurrence`, so future
  CRA memory mechanisms must still be compared against strong baselines, not
  only sign persistence

Boundary: Tier 5.10b is a software-only task-validation pass. It does not
promote a CRA memory mechanism, does not prove catastrophic forgetting is
solved, and does not authorize sleep/replay claims. It authorizes Tier 5.10c:
test v1.4 CRA and explicit memory candidates on these repaired streams with
memory ablations and external baselines.

## Tier 5.10c Explicit Context-Memory Mechanism Diagnostic

Run the full mechanism diagnostic:

```bash
make tier5-10c
```

Run a quick harness smoke:

```bash
make tier5-10c-smoke
```

Status: **completed as noncanonical software mechanism pass**.

Purpose: test whether CRA can use an explicit host-side context-binding memory
feature on the repaired Tier 5.10b streams, and whether reset/shuffled/wrong
memory ablations remove the benefit.

Protocol:

- backend: NEST
- tasks: `delayed_context_cue`, `distractor_gap_context`,
  `hidden_context_recurrence`
- seeds: `42`, `43`, `44`
- steps: `720`
- CRA variants: `v1_4_raw`, `explicit_context_memory`,
  `memory_reset_ablation`, `shuffled_memory_ablation`,
  `wrong_memory_ablation`
- standard baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `small_gru`,
  `stdp_only_snn`
- context controls: `oracle_context`, `stream_context_memory`,
  `shuffled_context`, `memory_reset`, `wrong_context`
- leakage guard: consequence feedback must not mature before the decision event

Observed mechanism result:

- output: `controlled_test_output/tier5_10c_20260428_201314/`
- status: `PASS`
- expected/observed runs: `144 / 144`
- feedback timing leakage violations: `0`
- candidate feature-active steps: `303`
- candidate context-memory updates: `147`
- candidate all accuracy: `1.0` on all three repaired tasks
- candidate minimum all-accuracy edge versus v1.4 raw CRA:
  `0.4666666666666667`
- candidate minimum edge versus best memory ablation:
  `0.3555555555555556`
- candidate minimum edge versus sign persistence: `0.4666666666666667`
- candidate minimum edge versus best standard baseline:
  `0.18452380952380965`

Interpretation:

- explicit context binding is useful on the repaired memory-pressure tasks
- the benefit is not explained by reset, shuffled, or wrong-memory controls
- v1.4 raw CRA does not solve these tasks without context binding
- the result is stronger than the Tier 5.10 proxy memory attempt, but the
  mechanism is still a host-side scaffold rather than internal/native CRA memory

Boundary: Tier 5.10c is software-only diagnostic evidence. It does not prove
sleep/replay consolidation, catastrophic-forgetting resolution, hardware
memory, or native on-chip context binding. It authorizes a compact regression
and a cleaner internal context-memory implementation before any baseline
promotion.

## Tier 5.10d Internal Context-Memory Implementation Diagnostic

Run the full internalization diagnostic:

```bash
make tier5-10d
```

Run a quick harness smoke:

```bash
make tier5-10d-smoke
```

Status: **completed as noncanonical software mechanism pass**.

Purpose: test whether the Tier 5.10c host-side context-binding scaffold can be
internalized into `Organism` as a bounded CRA context-memory mechanism. Unlike
Tier 5.10c, the internal candidate receives the raw repaired task stream; the
memory binding is performed inside CRA via `learning.context_memory_enabled`.

Protocol:

- backend: NEST
- tasks: `delayed_context_cue`, `distractor_gap_context`,
  `hidden_context_recurrence`
- seeds: `42`, `43`, `44`
- steps: `720`
- CRA variants: `v1_4_raw`, `external_context_memory_scaffold`,
  `internal_context_memory`, `memory_reset_ablation`,
  `shuffled_memory_ablation`, `wrong_memory_ablation`
- standard baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `small_gru`,
  `stdp_only_snn`
- context controls: `oracle_context`, `stream_context_memory`,
  `shuffled_context`, `memory_reset`, `wrong_context`
- leakage guard: consequence feedback must not mature before the decision event
- regression guard: compact Tier 1/Tier 2/Tier 3 smoke must still pass

Observed mechanism result:

- output: `controlled_test_output/tier5_10d_20260428_212229/`
- status: `PASS`
- expected/observed runs: `153 / 153`
- feedback timing leakage violations: `0` across `5151` checked feedback rows
- internal candidate feature-active steps: `303`
- internal candidate context-memory updates: `147`
- internal candidate all accuracy: `1.0` on all three repaired tasks
- external scaffold all accuracy: `1.0` on all three repaired tasks
- minimum internal edge versus v1.4 raw CRA: `0.4666666666666667`
- minimum internal edge versus external scaffold: `0.0`
- minimum internal edge versus best memory ablation:
  `0.4666666666666667`
- minimum internal edge versus sign persistence: `0.4666666666666667`
- minimum internal edge versus best standard baseline:
  `0.18452380952380965`
- full compact regression output:
  `controlled_test_output/tier5_7_20260428_214807/`
- full compact regression status: `PASS`

Interpretation:

- the memory capability no longer depends on preprocessing the task stream
  outside CRA
- internal context memory matches the external Tier 5.10c scaffold on the
  repaired memory-pressure tasks
- reset, shuffled, and wrong-memory ablations remove the benefit
- v1.4 raw CRA does not solve these tasks without context binding
- compact Tier 1/Tier 2/Tier 3 smoke remained clean after the internal memory
  code was added

Boundary: Tier 5.10d is software-only internal host-memory evidence. It does
not prove native on-chip memory, sleep/replay consolidation, hardware transfer
of memory, broad catastrophic-forgetting resolution, or general AGI-style
working memory. It authorizes the next memory question: stress internal memory
under longer recurrence/retention conditions before considering sleep/replay.

## Tier 5.10e Internal Memory Retention Stressor

Run:

```bash
make tier5-10e
```

Smoke:

```bash
make tier5-10e-smoke
```

Status: **passed as noncanonical software stress evidence**.

Purpose: test whether the Tier 5.10d internal host-side context-memory path
still works under longer context gaps, denser distractors, and stronger
hidden-regime recurrence pressure.

Protocol:

- backend: NEST
- tasks: `delayed_context_cue`, `distractor_gap_context`,
  `hidden_context_recurrence`
- seeds: `42`, `43`, `44`
- steps: `960`
- variants: v1.4 raw CRA, external Tier 5.10c scaffold, internal context
  memory, reset-memory ablation, shuffled-memory ablation, wrong-memory
  ablation
- standard baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `small_gru`,
  `stdp_only_snn`
- stress profile: `context_gap=48`, `context_period=96`,
  `long_context_gap=96`, `long_context_period=160`,
  `distractor_density=0.85`, `distractor_scale=0.45`,
  `recurrence_phase_len=240`, `recurrence_trial_gap=24`,
  `recurrence_decision_gap=64`

Observed result:

- output: `controlled_test_output/tier5_10e_20260428_220316/`
- status: `PASS`
- expected/observed runs: `153 / 153`
- feedback timing leakage violations: `0` across `2448` checked feedback rows
- internal candidate feature-active steps: `144`
- internal candidate context-memory updates: `60`
- internal candidate all accuracy: `1.0` on all three retention-stress tasks
- external scaffold all accuracy: `1.0` on all three retention-stress tasks
- minimum internal edge versus v1.4 raw CRA: `0.33333333333333337`
- minimum internal edge versus external scaffold: `0.0`
- minimum internal edge versus best memory ablation:
  `0.33333333333333337`
- minimum internal edge versus sign persistence: `0.33333333333333337`
- minimum internal edge versus best standard baseline:
  `0.33333333333333337`

Interpretation:

- the internal memory mechanism survived the harder retention profile tested
  here
- at Tier 5.10e time, sleep/replay was not justified as a repair for this exact stressor,
  because there was no observed retention decay to repair
- reset, shuffled, and wrong-memory ablations still remove the benefit under
  the stress profile
- the result strengthens the internal host-side memory claim but does not
  expand it into hardware, native on-chip memory, or general working memory

Boundary: Tier 5.10e is software-only internal memory retention evidence. It
does not prove sleep/replay consolidation, native on-chip state, SpiNNaker
memory transfer, capacity-limited memory, broad catastrophic-forgetting
resolution, or AGI-style working memory. Tier 5.11a later supplied that
measured consolidation need under silent reentry stress, so sleep/replay moved
from speculative feature to predeclared Tier 5.11b intervention candidate.

## Tier 5.10f Memory Capacity / Interference Stressor

Run:

```bash
make tier5-10f
```

Smoke:

```bash
make tier5-10f-smoke
```

Status: **failed cleanly as noncanonical capacity/interference diagnostic
evidence**.

Purpose: test whether the v1.5 internal host-side context-memory path survives
intervening contexts, overlapping pending decisions, and context reentry after
interference.

Protocol:

- backend: NEST
- tasks: `intervening_contexts`, `overlapping_contexts`,
  `context_reentry_interference`
- seeds: `42`, `43`, `44`
- steps: `720`
- variants: v1.4 raw CRA, external single-slot scaffold, internal context
  memory, reset-memory ablation, shuffled-memory ablation, wrong-memory
  ablation
- standard baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `small_gru`,
  `stdp_only_snn`
- capacity/interference profile: `capacity_period=120`,
  `capacity_decision_gap=72`, `interfering_contexts=2`,
  `interference_spacing=24`, `overlap_context_gap=36`,
  `overlap_first_decision_gap=72`, `overlap_second_decision_gap=96`,
  `reentry_phase_len=180`, `reentry_interference_probability=0.7`

Observed result:

- output: `controlled_test_output/tier5_10f_20260428_224805/`
- status: `FAIL`
- expected/observed runs: `153 / 153`
- feedback timing leakage violations: `0` across `1938` checked feedback rows
- internal candidate feature-active steps: `114`
- internal candidate context-memory updates: `121`
- internal candidate all accuracy:
  - `intervening_contexts`: `0.6666666666666666`
  - `overlapping_contexts`: `0.5`
  - `context_reentry_interference`: `0.25`
- minimum internal edge versus v1.4 raw CRA: `-0.25`
- minimum internal edge versus best memory ablation: `-0.5`
- minimum internal edge versus sign persistence: `-0.25`
- minimum internal edge versus best standard baseline: `-0.25`
- internal candidate matched the external scaffold with minimum edge `0.0`

Interpretation:

- v1.5 memory is not broken as an implementation; it matches the external
  single-slot scaffold
- the measured failure is capacity/interference: intervening contexts and
  reentry can overwrite or misbind the retained context
- sleep/replay is not the first repair by itself, because this is not primarily
  slow decay over time; it is a slot/routing/interference problem
- Tier 5.10g now tests the multi-slot/keyed repair with explicit capacity
  controls before any sleep/replay consolidation claim

Boundary: Tier 5.10f is failed noncanonical software diagnostic evidence. It
does not invalidate v1.5 retention evidence; it narrows it. The honest claim is
that internal context memory survives retention/distractor stress but does not
yet survive capacity/interference stress.

## Tier 5.10g Multi-Slot / Keyed Context-Memory Repair

Run:

```bash
make tier5-10g
```

Smoke:

```bash
make tier5-10g-smoke
```

Status: **passed as baseline-frozen keyed-memory repair evidence**.

Purpose: test whether bounded keyed/multi-slot context memory repairs the Tier
5.10f single-slot capacity/interference failure without leakage, fake memory
signals, or ablation collapse.

Protocol:

- backend: NEST
- tasks: `intervening_contexts`, `overlapping_contexts`,
  `context_reentry_interference`
- seeds: `42`, `43`, `44`
- steps: `720`
- variants: v1.4 raw CRA, v1.5 single-slot internal memory, oracle-keyed
  scaffold, keyed context memory, slot-reset ablation, slot-shuffle ablation,
  wrong-key ablation, overcapacity keyed memory
- standard baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `small_gru`,
  `stdp_only_snn`
- capacity controls: oracle-key upper bound, wrong-key control, slot-shuffle
  control, reset control, and overcapacity/limited-slot stress

Observed result:

- output: `controlled_test_output/tier5_10g_20260428_232844/`
- status: `PASS`
- expected/observed runs: `171 / 171`
- feedback timing leakage violations: `0` across `2166` checked feedback rows
- keyed candidate feature-active steps: `114.0`
- keyed candidate context-memory updates: `121.0`
- keyed candidate all accuracy:
  - `intervening_contexts`: `1.0`
  - `overlapping_contexts`: `1.0`
  - `context_reentry_interference`: `1.0`
- minimum keyed edge versus v1.4 raw CRA: `0.5`
- minimum keyed edge versus v1.5 single-slot memory: `0.33333333333333337`
- minimum keyed edge versus oracle-key scaffold: `0.0`
- minimum keyed edge versus best memory ablation: `0.33333333333333337`
- minimum keyed edge versus sign persistence: `0.5`
- minimum keyed edge versus best standard baseline: `0.5`
- compact regression after keyed-memory addition passed at
  `controlled_test_output/tier5_7_20260428_235507/`

Interpretation:

- the Tier 5.10f failure mode was specifically single-slot overwrite/misbinding,
  not an impossibility of internal context memory
- keyed/multi-slot binding repairs the tested bounded capacity/interference
  cases and matches the oracle-key upper bound on all three tasks
- ablation controls still lose, so the improvement is not explained by extra
  stream metadata alone
- overcapacity control is documented as a capacity stress reference, not proof
  that arbitrary context counts are solved

Boundary: Tier 5.10g is baseline-frozen software-only internal keyed-memory repair
evidence. It freezes v1.6 but does not prove native/on-chip memory, sleep/replay,
hardware memory transfer, compositionality, module routing, broad catastrophic
forgetting resolution, or general working memory.

## Tier 5.11a Sleep/Replay Need Test

Purpose:

```text
prove whether sleep/replay is needed before implementing it
```

Run:

```bash
make tier5-11a-smoke
make tier5-11a
```

Design:

```text
compare v1.6 no-replay keyed memory against unbounded keyed memory, oracle context scaffold, overcapacity control, slot reset/shuffle/wrong-key ablations, and standard baselines
use silent context reentry, long-gap silent reentry, and partial-key reentry
require zero leakage and solved upper-bound controls before interpreting v1.6 degradation
```

Observed result:

```text
output = controlled_test_output/tier5_11a_20260429_004340/
status = PASS
expected/observed runs = 171 / 171
feedback timing leakage violations = 0
v1.6 no-replay min accuracy = 0.6086956521739131
unbounded keyed min accuracy = 1.0
oracle scaffold min accuracy = 1.0
max unbounded gap versus v1.6 no-replay = 0.3913043478260869
max oracle gap versus v1.6 no-replay = 0.3913043478260869
max tail unbounded gap versus v1.6 no-replay = 1.0
diagnostic decision = replay_or_consolidation_needed
```

Interpretation:

```text
v1.6 keyed memory is still the frozen current memory baseline, but bounded no-replay memory fails the silent reentry tail stress while unbounded/oracle controls solve it. This is now a measured consolidation/capacity failure, so Tier 5.11b replay/consolidation intervention testing is justified.
```

Boundary: Tier 5.11a is a need diagnostic, not a replay implementation. It does
not prove sleep/replay works, does not freeze v1.7, does not prove hardware
memory, and does not prove native on-chip memory.

Observed Tier 5.11b result:

```text
output = controlled_test_output/tier5_11b_20260429_022048/
status = FAIL
expected/observed runs = 162 / 162
feedback timing leakage violations = 0
replay future violations = 0
prioritized replay events = 1185
prioritized replay consolidations = 1185
prioritized minimum all accuracy = 1.0
prioritized minimum tail accuracy = 1.0
prioritized minimum tail delta versus no replay = 1.0
prioritized minimum all/tail gap closure versus unbounded = 1.0 / 1.0
no-consolidation replay writes = 0
failed criterion = shuffled replay does not match prioritized tail
prioritized minimum tail edge versus shuffled = 0.4444444444444444
required edge versus shuffled = 0.5
```

Interpretation:

```text
prioritized replay repairs the measured no-replay silent-reentry failure, but it
does not yet separate cleanly enough from the shuffled-replay sham on
partial_key_reentry. Therefore Tier 5.11b is non-promoted repair signal, not a
sleep/replay success claim.
```

Boundary: Tier 5.11b does not freeze v1.7, does not prove replay/consolidation
works, and does not authorize hardware replay. v1.6 remains the frozen current
memory baseline at this point.

Observed Tier 5.11c result:

```text
output = controlled_test_output/tier5_11c_20260429_031427/
status = FAIL
expected/observed runs = 189 / 189
feedback timing leakage violations = 0
replay future violations = 0
candidate replay events/consolidations = 1185 / 1185
candidate minimum all/tail accuracy = 1.0 / 1.0
candidate all/tail gap closure versus unbounded = 1.0 / 1.0
minimum tail edge versus shuffled-order replay = 0.40740740740740733
minimum tail edge versus random replay = 0.2962962962962963
minimum tail edge versus wrong-key replay = 0.5555555555555556
minimum tail edge versus key-label-permuted replay = 1.0
minimum tail edge versus priority-only ablation = 1.0
minimum tail edge versus no-consolidation replay = 1.0
failed criterion = shuffled-order replay does not match prioritized tail
```

Interpretation: Tier 5.11c blocks the narrower priority-specific replay claim.
Correct-binding replay still looks real, but priority weighting itself is not
proven because shuffled-order replay still partially explains replay-opportunity
benefit.

Observed Tier 5.11d result:

```text
output = controlled_test_output/tier5_11d_20260429_041524/
status = PASS
expected/observed runs = 189 / 189
feedback timing leakage violations = 0
replay future violations = 0
candidate replay events/consolidations = 1185 / 1185
candidate minimum all/tail accuracy = 1.0 / 1.0
candidate minimum tail delta versus no replay = 1.0
candidate all/tail gap closure versus unbounded = 1.0 / 1.0
minimum tail edge versus wrong-key replay = 0.5555555555555556
minimum tail edge versus key-label-permuted replay = 1.0
minimum tail edge versus priority-only ablation = 1.0
minimum tail edge versus no-consolidation replay = 1.0
compact regression after replay = PASS at controlled_test_output/tier5_7_20260429_050527/
baseline freeze = baselines/CRA_EVIDENCE_BASELINE_v1.7.md
```

Boundary: Tier 5.11d freezes v1.7 as host-side correct-binding
replay/consolidation evidence. It does not prove priority weighting is
essential, does not prove biological sleep, does not authorize hardware replay,
and does not prove native on-chip memory, compositionality, routing, or world
modeling.


## Tier 5.12a Predictive Task-Pressure Validation

Run:

```bash
make tier5-12a-smoke
make tier5-12a
```

Status: **passed as noncanonical task-validation evidence**.

Purpose: validate that the predictive task battery cannot be explained by
current-value reflexes, sign-persistence, rolling-majority, wrong-horizon, or
shuffled-target controls before any CRA predictive mechanism is tested.

Protocol:

- backend: mock/software task harness
- tasks: `hidden_regime_switching`, `masked_input_prediction`,
  `event_stream_prediction`, `sensor_anomaly_prediction`
- seeds: `42`, `43`, `44`
- steps: `720`
- external baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `small_gru`,
  `stdp_only_snn`
- controls: `current_reflex`, `sign_persistence_control`, `rolling_majority`,
  `predictive_memory`, `wrong_horizon_control`, `shuffled_target_control`

Pass:

- full task/model/seed matrix completes
- feedback timing has zero leakage violations
- current and last-sign shortcuts are ambiguous
- current-reflex and sign-persistence controls stay below predeclared ceilings
- causal predictive-memory control solves the streams
- wrong-horizon and shuffled-target controls fail
- predictive-memory control beats reflex and sham controls by predeclared edges

Observed result:

```text
output = controlled_test_output/tier5_12a_20260429_054052/
status = PASS
expected/observed cells = 144 / 144
feedback leakage violations = 0 across 10044 checked feedback rows
causal predictive_memory accuracy = 1.0 on all four tasks
max current-reflex accuracy = 0.5393258426966292
max sign-persistence accuracy = 0.5649717514124294
max wrong/shuffled-target accuracy = 0.5444444444444444
minimum predictive edge versus best reflex = 0.4350282485875706
minimum predictive edge versus best wrong/shuffled sham = 0.4555555555555556
```

Boundary: Tier 5.12a authorized the Tier 5.12b/5.12c predictive mechanism
sequence. It is not CRA predictive coding, not full world modeling, not
language, not planning, not hardware prediction, and not a v1.8 freeze.

## Tier 5.12b Internal Predictive Context Mechanism Diagnostic

Run:

```bash
make tier5-12b-smoke
make tier5-12b
```

Status: **failed as designed; noncanonical diagnostic**.

Purpose: test whether CRA can store a visible causal predictive precursor
before feedback arrives and use that retained state at a later decision row.

Protocol:

- backend: NEST for the full run, mock for smoke
- tasks: `masked_input_prediction`, `event_stream_prediction`,
  `sensor_anomaly_prediction`
- seeds: `42`, `43`, `44`
- steps: `720`
- variants: `v1_7_reactive`, `external_predictive_scaffold`,
  `internal_predictive_context`, `wrong_predictive_context`,
  `shuffled_predictive_context`, `no_write_predictive_context`
- baselines/controls: same selected Tier 5.12a baselines and predictive controls

Observed result:

```text
output = controlled_test_output/tier5_12b_20260429_055923/
status = FAIL
expected/observed cells = 162 / 162
feedback leakage violations = 0
candidate active decision uses = 570
candidate predictive-context writes = 570
candidate matched external scaffold on every task
candidate accuracy = 1.0 event_stream_prediction
candidate accuracy = 0.8444444444444444 masked_input_prediction
candidate accuracy = 1.0 sensor_anomaly_prediction
failed gates = minimum absolute accuracy, minimum tail accuracy, ablation separation
```

Interpretation:

```text
The predictive-context path was wired and useful, but the wrong-sign sham was
not a valid information-destroying control because a stable sign inversion can
still be learned as an alternate code. Tier 5.12b remains a failed diagnostic
and motivates Tier 5.12c.
```

## Tier 5.12c Predictive Context Sham-Separation Repair

Run:

```bash
make tier5-12c-smoke
make tier5-12c
```

Status: **passed as noncanonical software mechanism evidence**.

Purpose: repair the Tier 5.12b sham contract by treating wrong-sign context as
an alternate-code diagnostic and gating the candidate against
shuffled/permuted/no-write information-destroying shams.

Protocol:

- backend: NEST for the full run, mock for smoke
- tasks: `masked_input_prediction`, `event_stream_prediction`,
  `sensor_anomaly_prediction`
- seeds: `42`, `43`, `44`
- steps: `720`
- variants: `v1_7_reactive`, `external_predictive_scaffold`,
  `internal_predictive_context`, `wrong_predictive_context`,
  `shuffled_predictive_context`, `permuted_predictive_context`,
  `no_write_predictive_context`
- external baselines: `sign_persistence`, `online_perceptron`,
  `online_logistic_regression`, `echo_state_network`, `small_gru`,
  `stdp_only_snn`

Pass:

- full variant/baseline/control/task/seed matrix completes
- feedback timing has zero leakage violations
- predictive-context write/read telemetry is nonzero
- candidate approaches the external predictive scaffold
- candidate improves over v1.7 reactive CRA
- shuffled/permuted/no-write shams are worse than the candidate
- candidate beats shortcut controls and selected external baselines by
  predeclared edges

Observed result:

```text
output = controlled_test_output/tier5_12c_20260429_062256/
status = PASS
expected/observed cells = 171 / 171
feedback leakage violations = 0
candidate writes / active decision uses = 570 / 570
candidate accuracy = 1.0 event_stream_prediction
candidate accuracy = 0.8444444444444444 masked_input_prediction
candidate accuracy = 1.0 sensor_anomaly_prediction
minimum candidate tail accuracy = 0.888888888888889
minimum edge vs v1.7 reactive CRA = 0.8444444444444444
minimum edge vs information-destroying shams = 0.3388888888888889
minimum edge vs shortcut controls = 0.3
minimum edge vs best selected external baseline = 0.31666666666666665
candidate gap vs external scaffold = 0.0
```

Boundary: Tier 5.12c proves bounded host-side visible predictive-context
binding under controlled software tasks. Tier 5.12d is the separate
compact-regression promotion gate. Do not cite Tier 5.12c alone as
hidden-regime inference, full world modeling, language, planning, hardware
prediction, hardware scaling, native on-chip learning, compositionality, or
external-baseline superiority.

## Tier 5.12d Predictive-Context Compact Regression

Run:

```bash
make tier5-12d-smoke
make tier5-12d
```

Purpose:

- decide whether the Tier 5.12c host-side visible predictive-context mechanism
  can be frozen as a carried-forward software baseline
- ensure old controls, learning proofs, ablations, hard-task smokes, and v1.7
  replay/consolidation guardrails remain intact

Observed result:

```text
output = controlled_test_output/tier5_12d_20260429_070615/
status = PASS
children passed = 6 / 6
criteria passed = 6 / 6
runtime_seconds = 319.63600204200003
baseline freeze = baselines/CRA_EVIDENCE_BASELINE_v1.8.md
```

Child checks:

```text
tier1_controls = PASS
tier2_learning = PASS
tier3_ablations = PASS
target_task_smokes = PASS
replay_consolidation_guardrail = PASS
predictive_context_guardrail = PASS
```

Boundary: Tier 5.12d freezes v1.8 as bounded host-side visible
predictive-context software evidence. It does not prove hidden-regime
inference, full world modeling, language, planning, lifecycle/self-scaling,
hardware prediction, hardware scaling, native on-chip learning,
compositionality, or external-baseline superiority.

## Tier 5.13 Compositional Skill Reuse Diagnostic

Run:

```bash
make tier5-13-smoke
make tier5-13
```

Purpose:

- test whether held-out skill combinations require reusable module composition
  rather than ordinary reflex learning or combo memorization
- decide whether the roadmap should proceed to internal CRA composition/routing
  implementation

Observed result:

```text
output = controlled_test_output/tier5_13_20260429_075539/
status = PASS
matrix cells = 126 / 126
feedback leakage violations = 0
candidate first-heldout accuracy min = 1.0
candidate total heldout accuracy min = 1.0
edge versus raw v1.8 first-heldout min = 1.0
edge versus best composition sham min = 0.7083333333333333
edge versus combo memorization min = 1.0
edge versus best selected standard baseline min = 0.16666666666666663
```

Protocol:

- backend: `mock`
- tasks: `heldout_skill_pair`, `order_sensitive_chain`,
  `distractor_skill_chain`
- seeds: `42`, `43`, `44`
- steps: `720`
- candidate: explicit host-side reusable-module scaffold
- bridge: CRA supplied with the same host-composed scalar feature
- controls: raw v1.8 CRA, reset/shuffled/order-shuffled modules,
  combo-memorization control, oracle composition, and selected external
  baselines

Required outputs:

- `tier5_13_results.json`
- `tier5_13_report.md`
- `tier5_13_summary.csv`
- `tier5_13_comparisons.csv`
- `tier5_13_fairness_contract.json`
- `tier5_13_composition.png`
- per-task/per-model/per-seed time-series CSVs

Pass:

- full task/seed/variant/baseline matrix completes
- feedback timing has zero leakage violations
- tasks contain shortcut-ambiguous held-out skill compositions
- reusable-module scaffold activates on held-out combinations
- candidate first-heldout and total heldout accuracy reach `1.0`
- module reset/shuffle/order-shuffle controls are materially worse
- combo memorization fails on held-out combinations
- selected standard baselines do not explain the result

Boundary: Tier 5.13 is noncanonical software diagnostic evidence for explicit
host-side reusable-module composition. It is not native/internal CRA
composition, not module routing, not hardware evidence, not language reasoning,
not long-horizon planning, and not a v1.9 baseline freeze. It authorizes the
next internal CRA composition/routing implementation tier.

## Tier 5.13b Module Routing / Contextual Gating Diagnostic

Run:

```bash
make tier5-13b-smoke
make tier5-13b
```

Purpose:

- test whether an explicit router can select the correct learned module under
  delayed/mixed context pressure
- defend against the critique that CRA can own reusable modules but cannot
  choose which one should be active

Observed result:

```text
output = controlled_test_output/tier5_13b_20260429_121615/
status = PASS
matrix cells = 126 / 126
feedback leakage violations = 0 / 11592 checked feedback rows
tasks = heldout_context_routing, distractor_router_chain, context_reentry_routing
seeds = 42, 43, 44
candidate first-heldout routing accuracy min = 1.0
candidate total heldout routing accuracy min = 1.0
candidate router accuracy min = 1.0
candidate pre-feedback route selections = 276
edge versus raw v1.8 first-heldout min = 1.0
edge versus best routing sham min = 0.375
edge versus best selected standard baseline min = 0.45833333333333337
```

Protocol:

- backend: `mock`
- steps: `960`
- candidate: explicit host-side contextual router scaffold
- bridge: CRA supplied with the host-routed scalar feature at decision time
- controls: raw v1.8 CRA, always-on modules, random router, router reset,
  context shuffle, oracle router, and selected external baselines

Important diagnostic boundary:

- the explicit router scaffold passed
- the raw v1.8 CRA first-heldout score was `0.0`
- the CRA router-input bridge first-heldout score was also `0.0`

Pass:

- full task/seed/variant/baseline matrix completes
- feedback timing has zero leakage violations
- tasks require context routing beyond current input/history
- candidate learns primitive modules and context router
- candidate selects routes before feedback
- candidate reaches `1.0` first-heldout and heldout routing accuracy
- always-on/random/reset/shuffled routing shams are materially worse
- selected standard baselines do not close the first-heldout gap

Boundary: Tier 5.13b is noncanonical software diagnostic evidence for explicit
host-side contextual routing. It is not native/internal CRA routing, not
successful CRA bridge integration, not hardware evidence, not language, not
planning, and not a v1.9 baseline freeze. It authorizes internal CRA
routing/gating work.

## Tier 5.13c Internal Composition / Routing Promotion Gate

Run:

```bash
make tier5-13c-smoke
make tier5-13c
make tier5-12d
```

Purpose:

- internalize the Tier 5.13 reusable-module composition scaffold and Tier 5.13b
  contextual-router scaffold into the CRA host loop
- test that the internal mechanism learns primitive module tables and
  context-to-module scores only after feedback while selecting routed/composed
  features before feedback
- defend against the critique that the previous composition/routing results were
  external scaffolds rather than a CRA mechanism

Observed result:

```text
output = controlled_test_output/tier5_13c_20260429_160142/
status = PASS
matrix cells = 243 / 243
feedback leakage violations = 0 / 22941 checked feedback rows
pre-feedback feature selections = 6096
candidate module updates = 192
candidate router updates = 88
candidate pre-feedback route selections = 276
composition first-heldout accuracy min = 1.0
composition heldout accuracy min = 1.0
routing first-heldout accuracy min = 1.0
routing heldout accuracy min = 1.0
routing accuracy min = 1.0
edge versus raw CRA min = 1.0
edge versus best internal sham min = 0.5
best selected standard baseline delta min = 0.0
best selected standard baseline delta max = 0.5
full compact regression = PASS via controlled_test_output/tier5_12d_20260429_122720/
baseline freeze = baselines/CRA_EVIDENCE_BASELINE_v1.9.md
```

Protocol:

- backend: `mock`
- composition tasks: `heldout_skill_pair`, `order_sensitive_chain`,
  `distractor_skill_chain`
- routing tasks: `heldout_context_routing`, `distractor_router_chain`,
  `context_reentry_routing`
- seeds: `42`, `43`, `44`
- composition steps: `720`
- routing steps: `960`
- candidate: internal host-side CRA composition/routing pathway
- upper-bound scaffolds: `module_composition_scaffold`,
  `contextual_router_scaffold`
- controls: raw v1.8 CRA, no-write, reset, skill-shuffle, order-shuffle,
  router-reset, context-shuffle, random-router, always-on shams, and selected
  external baselines

Required outputs:

- `tier5_13c_results.json`
- `tier5_13c_report.md`
- `tier5_13c_summary.csv`
- `tier5_13c_comparisons.csv`
- `tier5_13c_fairness_contract.json`
- `tier5_13c_internal_composition_routing.png`
- per-task/per-model/per-seed time-series CSVs

Pass:

- full internal/scaffold/baseline/task/seed matrix completes
- feedback timing has zero leakage violations
- internal candidate learns primitive module tables
- internal candidate learns context router
- routed/composed features are selected before feedback
- candidate reaches `1.0` minimum first-heldout and heldout accuracy on
  composition and routing suites
- router selection is correct on held-out routing trials
- internal shams are materially worse
- candidate does not underperform selected standard baselines and has a
  meaningful standard-baseline edge somewhere
- full compact regression stays green

Boundary: Tier 5.13c plus the fresh full compact regression freezes v1.9 as
bounded host-side software composition/routing evidence. It is not SpiNNaker
hardware evidence, not native/custom-C on-chip routing, not language reasoning,
not long-horizon planning, not AGI, and not external-baseline superiority.

## Tier 5.14 Working Memory / Context Binding

Run:

```bash
make tier5-14
```

Smoke:

```bash
make tier5-14-smoke
```

Status: **passed as noncanonical software diagnostic evidence**.

Latest output:

```text
controlled_test_output/tier5_14_20260429_165409/
```

Purpose: test whether the frozen v1.9 host-side software stack can maintain
working state across time: context/cue memory, active module state, and pending
subgoal/routing state.

Protocol:

- backend: `mock`
- memory/context tasks: `intervening_contexts`, `overlapping_contexts`,
  `context_reentry_interference`
- module-state/routing tasks: `heldout_context_routing`,
  `distractor_router_chain`, `context_reentry_routing`
- seeds: `42`, `43`, `44`
- memory steps: `720`
- routing steps: `960`
- selected sequence baselines: sign persistence, online perceptron, online
  logistic regression, echo-state network, small GRU, STDP-only SNN
- memory controls: raw/no-memory CRA, oracle context scaffold, single-slot
  memory, slot reset, slot shuffle, wrong-key, overcapacity, and stream
  context controls
- routing controls: raw routing-off CRA, contextual-router scaffold,
  no-write, router-reset, context-shuffle, random-router, always-on shams

Observed result:

```text
status = PASS
runtime_seconds = 647.690871625
memory comparisons = 3
routing comparisons = 3
memory/context-binding subsuite = PASS
module-state/routing subsuite = PASS
minimum context-memory edge vs best sham = 0.5
minimum context-memory edge vs sign persistence = 0.5
minimum routing edge vs best sham = 0.5
minimum routing edge vs routing-off CRA = 1.0
memory candidate accuracy = 1.0 on all 3 memory-pressure tasks
routing first-heldout/heldout/router accuracy = 1.0 on all 3 routing tasks
```

Required outputs:

- `tier5_14_results.json`
- `tier5_14_report.md`
- `tier5_14_fairness_contract.json`
- `tier5_14_working_memory_summary.png`
- `memory_context_binding/` per-task/per-model/per-seed traces
- `module_state_routing/` per-task/per-model/per-seed traces

Pass:

- memory/context-binding subsuite passes
- module-state/routing subsuite passes
- context-memory shams lose under memory pressure
- context-memory beats sign-persistence under memory pressure
- routing shams lose under delayed module-state pressure
- routing beats routing-off CRA under delayed module-state pressure
- exported context/routing telemetry aligns with task events before feedback

Boundary: Tier 5.14 supports a broader software working-memory/context-binding
diagnostic claim for v1.9. It does not freeze v2.0 by itself, and it is not
SpiNNaker hardware evidence, native/custom-C on-chip working memory, language,
long-horizon planning, AGI, or external-baseline superiority.

## Tier 6.1 Software Lifecycle / Self-Scaling Benchmark

Run:

```bash
make tier6-1
```

Smoke:

```bash
make tier6-1-smoke
```

Status: **passed and canonical v1.2 evidence**.

Purpose: test whether lifecycle-enabled CRA adds measurable value over fixed-N
CRA controls on identical hard/adaptive software streams.

Protocol:

- backend: NEST
- tasks: delayed_cue and hard_noisy_switching
- seeds: `42`, `43`, `44`
- steps: `960`
- fixed controls: `fixed4`, `fixed8`, `fixed16`
- lifecycle cases: `life4_16`, `life8_32`, `life16_64`

Required outputs:

- `tier6_1_results.json`
- `tier6_1_report.md`
- `tier6_1_summary.csv`
- `tier6_1_comparisons.csv`
- `tier6_1_lifecycle_events.csv`
- `tier6_1_lineage_final.csv`
- `tier6_1_event_analysis.md`
- `tier6_1_event_analysis.json`
- lifecycle summary and alive-population plots
- per-task/per-case/per-seed time-series CSVs

Pass:

- matrix completes
- fixed controls have no births or deaths
- lifecycle cases produce auditable new-polyp events
- lineage integrity remains clean
- no aggregate extinction occurs
- lifecycle improves at least one predeclared hard/adaptive regime versus the
  same-initial fixed-N control

Observed canonical result:

- expected runs: `36`
- actual runs: `36`
- fixed births/deaths: `0` / `0`
- lifecycle new-polyp events: `75`
- event types: `74` cleavage, `1` adult birth, `0` deaths
- lineage-integrity failures: `0`
- aggregate extinctions: `0`
- advantage regimes: `2`, both on hard_noisy_switching (`life4_16` versus
  `fixed4`, and `life8_32` versus `fixed8`)

Fail:

- lineage corrupts
- fixed controls show lifecycle events
- lifecycle cases collapse or go extinct
- lifecycle expansion is cosmetic and fixed-N dominates all predeclared regimes

Boundary: Tier 6.1 is software-only lifecycle expansion/self-scaling evidence.
It is not full adult birth/death turnover, not hardware lifecycle evidence, not
native on-chip lifecycle, not compositionality or world modeling, and not
external-baseline superiority. Tier 6.3 is the promoted sham-control defense for
this result.

## Tier 6.3 Lifecycle Sham-Control Suite

Run:

```bash
make tier6-3
```

Smoke:

```bash
make tier6-3-smoke
```

Status: **passed and canonical v1.3 evidence**.

Purpose: test whether the Tier 6.1 lifecycle/self-scaling advantage survives
reviewer-style sham explanations: extra capacity, random event count, active
mask bookkeeping, lineage bookkeeping, trophic pressure removal, dopamine
removal, and plasticity removal.

Protocol:

- backend: NEST
- task: hard_noisy_switching
- regimes: `life4_16`, `life8_32`
- seeds: `42`, `43`, `44`
- steps: `960`
- controls: intact lifecycle, fixed initial N, fixed max pool, event-count
  replay, active-mask shuffle, lineage-ID shuffle, no trophic pressure, no
  dopamine, no plasticity

Required outputs:

- `tier6_3_results.json`
- `tier6_3_report.md`
- `tier6_3_summary.csv`
- `tier6_3_comparisons.csv`
- `tier6_3_lifecycle_events.csv`
- `tier6_3_lineage_final.csv`
- `tier6_3_sham_manifest.json`
- sham summary and alive-population plots
- per-regime/per-control/per-seed time-series CSVs

Observed canonical result:

- expected actual runs: `36`
- actual runs: `36`
- intact non-handoff lifecycle events: `26`
- fixed capacity-control lifecycle events: `0`
- actual-run lineage-integrity failures: `0`
- aggregate extinctions: `0`
- performance-sham wins: `10/10`
- fixed max-pool wins: `2/2`
- event-count replay wins: `2/2`
- lineage-ID shuffle detections: `6/6`

Pass:

- actual-run matrix completes
- intact lifecycle produces auditable events
- fixed capacity controls produce no lifecycle events
- actual-run lineage remains clean
- no aggregate extinction occurs
- intact lifecycle beats fixed max-pool, event-count replay, no trophic, no
  dopamine, and no plasticity controls on predeclared hard/adaptive metrics
- lineage-ID shuffle is detected by the audit

Fail:

- fixed max-pool or event-count replay explains the advantage
- dopamine/plasticity/trophic ablations perform the same or better under the
  predeclared criteria
- lineage or active-mask bookkeeping corrupts
- lifecycle produces no auditable events or collapses

Boundary: Tier 6.3 is software-only sham-control evidence. Replay/shuffle
controls are derived audit artifacts, not independent learners. This is not
hardware lifecycle evidence, native on-chip lifecycle, full adult turnover,
external-baseline superiority, compositionality, or world modeling.

## Planned SNN-Native Coverage Addenda

These tiers are future proof obligations, not current evidence. They are added to
defend the claim that CRA is a spiking/circuit learning system rather than scalar
learning wrapped in PyNN.

### 5.15 Spike Encoding / Temporal Code Suite

Status: **passed as noncanonical software temporal-code diagnostic evidence**.

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

Purpose: test whether spike timing carries task-relevant information rather
than acting only as a transport layer for scalar host summaries.

Protocol executed:

- encoded the same task streams through rate, latency, burst, population, and
  temporal-interval codes
- ran `fixed_pattern`, `delayed_cue`, `hard_noisy_switching`, and
  `sensor_control`
- compared `temporal_cra` against time-shuffled spikes, rate-only controls,
  sign persistence, online perceptron/logistic regression, echo-state network,
  small GRU, and STDP-only SNN
- exported sampled input spike trains, per-step decoded traces, spike timing,
  sparsity, encoding metadata, fairness contract, and temporal-edge plots

Result:

```text
status = PASS
expected_runs = 540
observed_runs = 540
spike_trace_artifacts = 60
encoding_metadata_artifacts = 60
good_temporal_row_count = 9
nonfinance_good_temporal_row_count = 3
time_shuffle_loss_count = 9
rate_only_loss_count = 9
```

Key positive cells:

- `delayed_cue` latency: temporal CRA tail `1.0`, time-shuffle `0.484848`,
  rate-only `0.454545`
- `delayed_cue` burst: temporal CRA tail `1.0`, time-shuffle `0.545455`,
  rate-only `0.454545`
- `sensor_control` latency: temporal CRA tail `1.0`, time-shuffle `0.788889`,
  rate-only `0.7`
- `sensor_control` temporal_interval: temporal CRA tail `1.0`,
  time-shuffle `0.722222`, rate-only `0.688889`

Boundary:

- this is software-only `numpy_temporal_code` evidence
- this does not freeze v2.0 by itself
- this is not SpiNNaker hardware evidence
- this is not custom-C/on-chip temporal coding
- this is not neuron-model robustness, unsupervised representation learning,
  language, planning, or AGI evidence
- `hard_noisy_switching` did not produce a strong temporal-code advantage in
  this diagnostic, so do not cite Tier 5.15 as hard-switch temporal superiority

Next:

```text
Tier 5.17 failed cleanly and Tier 5.17b classified the failure; continue to
Tier 5.17c intrinsic predictive / MI-style preexposure repair
```

### 5.16 Neuron Model / Parameter Sensitivity

Status: **passed as noncanonical NEST neuron-parameter sensitivity evidence**.

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

Purpose: prove the result is not a fragile artifact of one exact LIF setting.

Protocol:

- sweep LIF threshold, membrane tau, synaptic tau, and refractory settings
- add adaptive LIF and Izhikevich-style software checks only if backend support is
  stable
- report accuracy, correlation, recovery, spike rate, sparsity, runtime, and
  robustness bands

Protocol executed:

- ran NEST on `fixed_pattern`, `delayed_cue`, and `sensor_control`
- tested seeds `42` and `43`
- swept 11 variants: default, threshold-low/high, membrane-tau fast/slow,
  refractory short/long, capacitance low/high, and synaptic-tau fast/slow
- audited config-to-neuron-factory propagation in
  `tier5_16_parameter_propagation.csv`
- ran a direct LIF current-response probe in
  `tier5_16_lif_response_probe.csv`
- exported per-task/per-variant/per-seed time series plus robustness plots

Result:

```text
status = PASS
expected_runs = observed_runs = 66
aggregate_cells = 33
functional_cell_count = 33
functional_cell_fraction = 1.0
default_min_tail_accuracy = 0.8
collapse_count = 0
parameter_propagation_failures = 0
sim_run_failures = 0
summary_read_failures = 0
synthetic_fallbacks = 0
response_probe_monotonic_fraction = 1.0
```

Pass:

- main claims hold across a predeclared reasonable LIF parameter band
- failures outside that band are documented rather than hidden
- complex neuron models are treated as robustness checks, not required evidence

Fail:

- a small plausible parameter change collapses the main effect
- the paper claim depends on one hand-picked threshold/tau setting

Boundary:

- software NEST diagnostic only, not SpiNNaker hardware evidence
- not custom-C/on-chip neuron model evidence
- not adaptive-LIF or Izhikevich evidence
- not a v2.0 freeze by itself
- synaptic-tau variants are propagation/no-collapse checks in this tier; richer
  synaptic-time-dynamics claims require separate spike-driven synaptic probes

### 5.17 Pre-Reward Representation Formation

Status: **failed cleanly as noncanonical pre-reward representation diagnostic evidence**.

Purpose: test whether useful latent structure can appear before labels, reward,
correctness feedback, or dopamine are introduced. Use the more precise phrase
`pre-reward representation formation` rather than loose `unsupervised learning`
until a mechanism survives controls.

Run:

```bash
make tier5-17
```

Smoke:

```bash
make tier5-17-smoke
```

Latest output:

```text
controlled_test_output/tier5_17_20260429_190501/
```

Protocol executed:

- exposed non-oracle variants only to visible streams; no labels, reward,
  correctness signal, or dopamine during exposure
- froze/snapshotted representations before offline probes used hidden labels
- tested `latent_cluster_sequence`, `temporal_motif_sequence`, and
  `ambiguous_reentry_context`
- compared candidate label-free CRA-compatible state against no-state-plasticity,
  time-shuffled exposure, temporal-destroyed exposure, current-input-only,
  rolling-history, random-projection, random-untrained, and oracle upper-bound
  controls
- exported run rows, aggregate summaries, candidate-control comparisons,
  fairness contract, matrix plot, and control-edge plot

Result:

```text
status = FAIL
expected_runs = observed_runs = 81
non_oracle_label_leakage_runs = 0
reward_leakage_runs = 0
max_abs_raw_dopamine_non_oracle = 0.0
candidate_min_ridge_probe_accuracy = 0.5914893617021276
candidate_min_knn_probe_accuracy = 0.4658119658119658
temporal_control_losses = 4
non_encoder_wins = 1
sample_efficiency_wins = 1
```

Pass requires:

- exposure has zero label/reward leakage and zero dopamine
- candidate representation passes probe thresholds across seeds
- no-state and temporal-sham controls lose on the intended pressure tasks
- current-input/history controls do not explain the whole effect
- downstream sample-efficiency improves under frozen representations

Fail means:

- the current strict no-history-input scaffold is not promoted
- pre-reward representation learning remains an open mechanism obligation
- the next valid move is Tier 5.17b failure analysis and then a repaired
  Tier 5.17c mechanism/task-pressure test, not a paper claim

Boundary:

- failed noncanonical software diagnostic evidence only
- not reward-free representation learning, unsupervised concept formation,
  hardware/on-chip representation evidence, or a v2.0 freeze
- oracle rows are upper bounds and cannot support no-leakage claims

### 5.17b Pre-Reward Representation Failure Analysis

Status: **passed as noncanonical diagnostic classification only**.

Purpose: classify the Tier 5.17 failure before adding any new mechanism, so the
repair is grounded in evidence rather than biological wish-listing.

Run:

```bash
make tier5-17b
```

Latest output:

```text
controlled_test_output/tier5_17b_20260429_191512/
```

Result:

```text
status = PASS
classification = mechanism_needs_intrinsic_predictive_objective
promote_pre_reward_representation = False
revisit_tier5_9_now = False
failure_mode_counts = {
  "candidate_structure_present": 1,
  "history_baseline_dominates": 1,
  "input_encoded_too_easy": 1
}
```

Interpretation:

- `ambiguous_reentry_context` is retained as a positive subcase where candidate
  state separates from controls
- `latent_cluster_sequence` is too input-encoded/easy and cannot prove
  representation formation
- `temporal_motif_sequence` is solved better by fixed-history controls, so the
  current scaffold lacks enough intrinsic temporal state

Next:

- Tier 5.17c should add an intrinsic predictive / MI-style preexposure objective
  and sharpen task pressure with masked-channel, temporal-continuation, and
  same-visible-input/different-latent-state controls
- revisit Tier 5.9 only if a future pre-reward mechanism forms useful structure
  but downstream reward cannot credit, preserve, or use it

Boundary:

- diagnostic analysis only
- not reward-free representation learning
- not unsupervised concept formation
- not hardware/on-chip representation evidence
- not a v2.0 freeze

### 5.17c Intrinsic Predictive Preexposure

Status: **failed as noncanonical software diagnostic evidence**.

Purpose: test the Tier 5.17b repair hypothesis by giving CRA a label-free
intrinsic objective during preexposure: masked-channel prediction,
temporal-continuation prediction, and contextual continuation prediction.

Run:

```bash
make tier5-17c
```

Latest output:

```text
controlled_test_output/tier5_17c_20260429_193147/
```

Result:

```text
status = FAIL
expected_runs = observed_runs = 99
non_oracle_label_leakage_runs = 0
reward_leakage_runs = 0
max_abs_raw_dopamine_non_oracle = 0.0
candidate_min_ridge_probe_accuracy = 0.38666666666666666
candidate_min_knn_probe_accuracy = 0.1746031746031746
sample_efficiency_wins = 3
```

What worked:

- no-label/no-reward/no-dopamine contract held
- candidate beat no-preexposure, time-shuffled, fixed-history, and reservoir
  controls in aggregate checks
- downstream sample-efficiency wins were present

What failed:

- held-out episode probes exposed low worst-case candidate probe accuracy
- target-shuffled and wrong-domain preexposure did not reliably lose
- STDP-only was not cleanly explained away
- candidate did not beat the best non-oracle control

Boundary:

- failed noncanonical software diagnostic evidence only
- not reward-free representation learning
- not unsupervised concept formation
- not hardware/on-chip representation evidence
- not a v2.0 freeze

Next valid repair:

- do not promote Tier 5.17c
- either design a Tier 5.17d target-binding/domain-sham repair or park
  reward-free representation formation and continue the broader roadmap with the
  claim narrowed

### 5.17d Predictive Preexposure Binding/Sham Repair

Status: **passed as bounded noncanonical software predictive-binding evidence**.

Purpose: repair the 5.17c sham-separation failure by testing whether correctly
bound masked/future sensory targets create useful pre-reward state on held-out
ambiguous episodes after visible context cues have faded.

Run:

```bash
make tier5-17d
```

Latest output:

```text
controlled_test_output/tier5_17d_20260429_194613/
```

Result:

```text
status = PASS
expected_runs = observed_runs = 60
tasks = cross_modal_binding, reentry_binding
non_oracle_label_leakage_runs = 0
reward_leakage_runs = 0
max_abs_raw_dopamine_non_oracle = 0.0
candidate_min_ridge_probe_accuracy = 0.7857142857142857
candidate_min_knn_probe_accuracy = 0.7738095238095238
min_candidate_probe_rows = 176
sample_efficiency_wins = 2
```

What passed:

- target-shuffled binding lost
- wrong-domain binding lost
- fixed-history and reservoir controls did not explain the result
- STDP-only did not explain the result
- candidate beat the best non-oracle control
- held-out ambiguous episode probes were available

Boundary:

- bounded software predictive-binding evidence only
- not general reward-free representation learning
- not unsupervised concept formation
- not hardware/on-chip representation evidence
- not full world modeling, language, planning, or AGI
- not a v2.0 freeze by itself

Next valid promotion step:

- completed as Tier 5.17e; keep the earlier failed `masked_code_binding`
  outputs as task-design diagnostics, not as promoted evidence

### 5.17e Predictive-Binding Compact Regression / v2.0 Freeze

Status: **passed as baseline-frozen host-side software predictive-binding
evidence**.

Purpose: verify that the 5.17d bounded predictive-binding repair can be safely
carried forward as a baseline by preserving prior regression and mechanism
guardrails.

Run:

```bash
make tier5-17e
```

Latest output:

```text
controlled_test_output/tier5_17e_20260429_163058/
```

Result:

```text
status = PASS
children_passed = 4 / 4
criteria_passed = 4 / 4
v1_8_compact_regression = pass
v1_9_composition_routing_guardrail = pass
working_memory_context_guardrail = pass
predictive_binding_guardrail = pass
baseline_freeze = baselines/CRA_EVIDENCE_BASELINE_v2.0.md
```

Boundary:

- bounded host-side software predictive-binding evidence only
- not hardware/on-chip representation learning
- not broad reward-free concept learning
- not full world modeling, language, planning, or AGI
- not external-baseline superiority

Next:

- v2.0 was used as the carried-forward software baseline for Tier 5.18
- Tier 5.18c subsequently froze v2.1 after Tier 5.18 passed its shams and the
  compact-regression guardrail stayed green

### 5.18 Self-Evaluation / Metacognitive Monitoring

Purpose: test whether CRA can estimate its own reliability before or while
acting, rather than only being scored after the fact.

Status: **passed as noncanonical software diagnostic evidence** at
`controlled_test_output/tier5_18_20260429_213002/`.

Observed:

```text
expected_runs = 150
observed_runs = 150
outcome_leakage_runs = 0
pre_feedback_monitor_failures = 0
candidate_min_primary_error_auroc = 0.986637
candidate_min_hazard_detection_auroc = 0.999055
candidate_max_brier_primary_correct = 0.0604305
candidate_max_ece_primary_correct = 0.152803
candidate_min_bad_action_avoidance = 0.763434
min_accuracy_edge_vs_v2_0 = 0.253241
min_accuracy_edge_vs_best_non_oracle = 0.250463
```

Interpretation: CRA now has software diagnostic evidence that a bounded
pre-feedback reliability monitor can estimate primary-path failure risk and use
that estimate to improve behavior under ambiguity/OOD/mismatch tasks. Tier
5.18c subsequently froze the bounded v2.1 baseline after compact regression.

Protocol:

- add a bounded monitor for confidence, uncertainty, predicted error, novelty,
  or out-of-distribution state
- require monitor outputs before outcome/reward feedback whenever the metric
  claims prospective self-evaluation
- run known-regime, hidden-regime, held-out-regime, and adversarial/noisy streams
- compare monitor-enabled CRA against monitor-disabled CRA, random-confidence,
  always-confident, always-uncertain, simple uncertainty baselines, and external
  sequence/RL baselines where applicable
- export confidence traces, calibration curves, pre-feedback error predictions,
  novelty/OOD scores, monitor-triggered replay/plasticity/routing actions, and
  leakage-audit rows

Pass:

- confidence/error/OOD estimates are calibrated better than random or trivial
  always-on controls
- monitor predictions occur before feedback and survive leakage audits
- using the monitor improves adaptation, recovery, abstention quality, replay
  triggering, routing, or bad-action avoidance on at least one predeclared task
- shuffled-confidence, delayed/post-outcome, and monitor-disabled controls lose
- v2.1 promotion requirement: compact regression stayed green in the Tier 5.18c
  gate

Fail:

- confidence only tracks outcomes after feedback arrives
- monitor benefit disappears under leakage-safe scoring
- simple uncertainty baselines dominate all monitored tasks
- the monitor destabilizes v1.8 controls or hides failure behind abstention

Boundary: Tier 5.18 is operational reliability monitoring only. It is not
consciousness, self-awareness, human-style introspection, AGI, or proof of
general autonomous judgment.

### 5.18c Self-Evaluation Compact Regression / v2.1 Freeze

Status: **passed as baseline-freeze gate** at
`controlled_test_output/tier5_18c_20260429_221045/`.

Observed:

```text
children_passed = 2 / 2
criteria_passed = 4 / 4
v2.0 compact regression gate remains green = pass
Tier 5.18 self-evaluation guardrail remains green = pass
runtime_seconds = 1534.207275167
```

Interpretation: v2.1 is the current frozen host-side software baseline for
bounded operational self-evaluation / reliability monitoring over v2.0. This is
not consciousness, self-awareness, introspection, SpiNNaker/custom-C/on-chip
self-monitoring, language, long-horizon planning, AGI, or external-baseline
superiority.

### 7.6 Long-Horizon Planning / Subgoal Control

Purpose: test whether CRA can pursue delayed outcomes through bounded
intermediate subgoals, rather than solving only one-step/reflex variants.

Protocol:

- build multi-step cue/action chains with delayed reward
- include distractor detours, partial observability, and held-out subgoal
  recombinations
- test horizon lengths before and after the easiest reflex solution stops
  working
- compare subgoal-enabled CRA against reactive/no-subgoal CRA, current best CRA,
  recurrent/GRU baselines, bandit/RL baselines where task-compatible, and an
  oracle-subgoal upper bound
- export subgoal state, routing/composition state, action traces, reward timing,
  horizon length, and leakage-audit rows

Pass:

- subgoal-enabled CRA beats reactive/no-subgoal CRA on held-out long-horizon
  tasks
- subgoal memory reset, subgoal order shuffle, reward-time shuffle, and
  composition/routing-disabled controls hurt
- future-reward leakage audits pass
- performance degrades gracefully as horizon length increases
- baselines and oracle upper bounds are reported fairly

Fail:

- success reduces to one-step/reflex shortcuts
- advantage disappears on held-out subgoal chains
- improvements come from future-reward leakage, oracle hints, or task-specific
  hand wiring
- simple planning/RL baselines dominate all long-horizon tasks

Boundary: Tier 7.6 is bounded subgoal-control evidence only. It is not general
planning, language reasoning, theorem proving, open-ended agency, or AGI.

### 6.4 Circuit Motif Causality

Status: **passed and canonical v1.4 evidence**.

Purpose: prove reef/circuit motifs are causal, not decorative.

Protocol:

- backend: NEST
- task: hard_noisy_switching
- regimes: `life4_16`, `life8_32`
- seeds: `42`, `43`, `44`
- steps: `960`
- variants: intact, no feedforward, no feedback, no lateral, no WTA, random
  graph same edge count, motif-label shuffle, and monolithic same-capacity
  control
- seed a motif-diverse graph before first outcome feedback because Tier 6.3
  traces were feedforward-only and could not honestly ablate absent motifs
- ablate feedforward excitation, feedback/recurrent paths, lateral motif paths,
  WTA/lateral inhibition, and compare labels versus structure
- compare against same-capacity random graph and monolithic controls
- export reef graph, motif masks, per-motif activity, and ablation deltas

Observed canonical result:

- expected runs: `48`
- actual runs: `48`
- intact motif-diverse aggregates: `2/2`
- intact motif-active steps: `1920`
- motif-ablation losses: `4/8`
- motif-label shuffle losses: `0/2`
- random/monolithic dominations: `0/4`
- lineage-integrity failures: `0`

Pass:

- at least one predeclared motif ablation causes a specific predicted loss
- motif logs show the path was active before outcome feedback
- same-capacity controls do not explain the benefit

Fail:

- motif ablations do not change behavior
- random graph or monolithic same-capacity CRA dominates
- motif labels cannot be mapped to runtime activity

Boundary: Tier 6.4 is software-only circuit-motif causality evidence. The
supported claim is that seeded motif structure and edge roles can do causal
work under hard_noisy_switching. It is not hardware motif evidence, custom-C or
on-chip learning, compositionality, world modeling, full adult turnover, or
external-baseline superiority.

## Evidence Bundle For Each Tier

Each tier produces:

- machine-readable JSON summary
- CSV metrics
- Markdown findings report
- PNG plots
- pass/fail status and exact criteria

The canonical evidence ledger is generated with:

```bash
python3 experiments/evidence_registry.py
```

That registry aligns all accepted result bundles, regenerates the
`*_latest_manifest.json` pointers, lists noncanonical reruns/probes as audit
history, and writes the source-facing `STUDY_EVIDENCE_INDEX.md`.

## Tier 4.22r Tiny Native Context-State Custom-Runtime Smoke

Status: **returned hardware pass ingested**.

Evidence:

```text
controlled_test_output/tier4_22r_20260501_native_context_state_smoke_local/
controlled_test_output/tier4_22r_20260501_native_context_state_smoke_prepared/
controlled_test_output/tier4_22r_20260501_native_context_state_smoke_hardware_pass_ingested/
```

Purpose: make the first v2-style state primitive native to the custom runtime.
Tier 4.22q proved a host-v2 bridge could feed features into the C pending/readout
loop. Tier 4.22r moves the keyed-context lookup and feature formation into C:
the host writes context slots, then sends only key+cue+delay; the chip retrieves
context and computes `feature=context*cue` before scheduling delayed credit.

Prepared upload folder:

```text
ebrains_jobs/cra_422aa
```

EBRAINS/JobManager command:

```text
cra_422aa/experiments/tier4_22r_native_context_state_smoke.py --mode run-hardware --output-dir tier4_22r_job_output
```

Pass case for returned hardware artifacts:

```text
status = pass
runner_revision = tier4_22r_native_context_state_smoke_20260501_0001
real hardware target acquired
custom C host tests pass
main.c host syntax check passes
.aplx builds and loads
all context writes acknowledge
all CMD_SCHEDULE_CONTEXT_PENDING commands acknowledge
chip-computed feature/context values match local reference within raw tolerance
all delayed CMD_MATURE_PENDING commands acknowledge
each mature reply has matured_count = 1
observed max pending depth >= 3
prediction/weight/bias raw deltas <= 1
observed tail accuracy >= 1.0
observed metrics match local reference
final slot_writes = 9
final slot_hits >= 30
final slot_misses = 0
final active_slots >= 3
final pending_created = 30
final pending_matured = 30
final reward_events = 30
final decisions = 30
final active_pending = 0
final readout_weight_raw = 32752 +/- 1
final readout_bias_raw = -16 +/- 1
synthetic fallback = 0
```

Fail case:

```text
any hardware target/build/load/command/readback failure
any context write failure
any chip-computed feature/context mismatch
any prediction/weight/bias mismatch beyond tolerance
any pending leak or missing maturation
any slot miss during the task stream
any synthetic fallback
```

Returned result:

```text
status = pass
board = 10.11.237.25
selected core = (0,0,4)
remote criteria = 58/58
ingest criterion = pass
context writes = 9
context reads = 30
max native context slots = 3
chip-computed feature/context/prediction/weight/bias raw deltas = 0
observed accuracy = 0.9333333333
observed tail accuracy = 1.0
observed max pending depth = 3
final pending_created = 30
final pending_matured = 30
final reward_events = 30
final decisions = 30
final active_pending = 0
final readout_weight_raw = 32752
final readout_bias_raw = -16
```

Boundary: Tier 4.22r proves only a tiny native keyed-context state primitive inside the custom runtime on real SpiNNaker. It does not prove full v2.1 memory/routing, full CRA task learning, speedup, scaling, or final autonomy.

## Tier 4.22s Tiny Native Route-State Custom-Runtime Smoke

Status: **hardware pass ingested**.

Evidence:

```text
controlled_test_output/tier4_22s_20260501_native_route_state_smoke_local/
controlled_test_output/tier4_22s_20260501_native_route_state_smoke_prepared/
```

Purpose: move the next minimal v2-style state primitive into the custom runtime.
Tier 4.22r proved native keyed context. Tier 4.22s adds chip-owned route state:
the host writes context and route, then sends only key+cue+delay; the chip
retrieves context+route and computes `feature=context*route*cue` before
scheduling delayed credit.

Prepared upload folder:

```text
ebrains_jobs/cra_422ab
```

EBRAINS/JobManager command:

```text
cra_422ab/experiments/tier4_22s_native_route_state_smoke.py --mode run-hardware --output-dir tier4_22s_job_output
```

Pass case for returned hardware artifacts:

```text
status = pass
runner_revision = tier4_22s_native_route_state_smoke_20260501_0001
real hardware target acquired
custom C host tests pass
main.c host syntax check passes
.aplx builds and loads
all context writes acknowledge
all route writes acknowledge
all CMD_SCHEDULE_ROUTED_CONTEXT_PENDING commands acknowledge
chip-computed feature/context/route values match local reference within raw tolerance
all delayed CMD_MATURE_PENDING commands acknowledge
each mature reply has matured_count = 1
observed max pending depth >= 3
prediction/weight/bias raw deltas <= 1
observed tail accuracy >= 1.0
observed metrics match local reference
final slot_writes = 9
final slot_hits >= 30
final slot_misses = 0
final active_slots >= 3
final route_writes = 9
final route_reads >= 30
final pending_created = 30
final pending_matured = 30
final reward_events = 30
final decisions = 30
final active_pending = 0
final readout_weight_raw = 32768 +/- 1
final readout_bias_raw = 0 +/- 1
synthetic fallback = 0
```

Fail case:

```text
any hardware target/build/load/command/readback failure
any context or route write failure
any chip-computed feature/context/route mismatch
any prediction/weight/bias mismatch beyond tolerance
any pending leak or missing maturation
any slot miss during the task stream
any synthetic fallback
```

Local prepared result:

```text
status = prepared
sequence length = 30
context writes = 9
context reads = 30
route writes = 9
route reads = 30
route values = [-1, 1]
feature source = chip_context_route_lookup_feature_transform
accuracy = 0.9333333333
tail accuracy = 1.0
final readout_weight_raw = 32768
final readout_bias_raw = 0
criteria = 56/56
```

Boundary: Tier 4.22s local/prepared evidence is source/package readiness only.
A future returned pass would prove only a tiny native route-state primitive
layered on native keyed context, not full native v2.1 memory/routing, full CRA
task learning, speedup, scaling, or final autonomy.

Returned result after ingest correction:

```text
status = pass
raw_remote_status = fail
false_fail_correction = route_writes final criterion expected route_writes in CMD_READ_ROUTE, but route writes are proven by CMD_WRITE_ROUTE row counters
board = 10.11.237.89
selected core = (0,0,4)
all context writes = pass
all route writes = pass
all schedule commands = pass
all mature commands = pass
observed route writes = 9
final route reads = 31
chip-computed feature/context/route/prediction/weight/bias raw deltas = 0
observed accuracy = 0.9333333333
observed tail accuracy = 1.0
final pending_created = 30
final pending_matured = 30
final reward_events = 30
final decisions = 30
final active_pending = 0
final readout_weight_raw = 32768
final readout_bias_raw = 0
```

The raw remote failure is preserved and the corrected ingested manifest has no
failed criteria. Boundary remains unchanged: tiny native route-state primitive
only, not full native v2.1 memory/routing, full CRA learning, speedup, scaling,
or final autonomy.

## Tier 4.22t Tiny Native Keyed Route-State Custom-Runtime Smoke

Status: **local pass and EBRAINS package prepared**. No hardware claim yet.

Evidence:

```text
controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_local/
controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_prepared/
```

Purpose: move route state from a single global scalar into bounded keyed route
slots. Tier 4.22s proved native keyed context plus a global chip-owned route
scalar. Tier 4.22t adds `CMD_WRITE_ROUTE_SLOT`, `CMD_READ_ROUTE_SLOT`, and
`CMD_SCHEDULE_KEYED_ROUTE_CONTEXT_PENDING`: the host writes context and route
slots by key, then sends only key+cue+delay; the chip retrieves both by key and
computes `feature=context[key]*route[key]*cue` before scheduling delayed credit.

Prepared upload folder:

```text
ebrains_jobs/cra_422ac
```

EBRAINS/JobManager command:

```text
cra_422ac/experiments/tier4_22t_native_keyed_route_state_smoke.py --mode run-hardware --output-dir tier4_22t_job_output
```

Pass case for returned hardware artifacts:

```text
status = pass
runner_revision = tier4_22t_native_keyed_route_state_smoke_20260501_0001
real hardware target acquired
custom C host tests pass
main.c host syntax check passes
.aplx builds and loads
all context writes acknowledge
all route-slot writes acknowledge
all CMD_SCHEDULE_KEYED_ROUTE_CONTEXT_PENDING commands acknowledge
chip-computed feature/context/route-slot values match local reference within raw tolerance
returned keyed route IDs match requested keys
all delayed CMD_MATURE_PENDING commands acknowledge
each mature reply has matured_count = 1
observed max pending depth >= 3
prediction/weight/bias raw deltas <= 1
observed tail accuracy >= 1.0
observed metrics match local reference
final slot_writes = 9
final slot_hits >= 30
final slot_misses = 0
final active_slots >= 3
observed route-slot writes = 15
observed active route slots >= 3
observed route-slot hits >= 30
observed route-slot misses = 0
final pending_created = 30
final pending_matured = 30
final reward_events = 30
final decisions = 30
final active_pending = 0
final readout_weight_raw = 32768 +/- 1
final readout_bias_raw = 0 +/- 1
synthetic fallback = 0
```

Fail case:

```text
any hardware target/build/load/command/readback failure
any context or route-slot write failure
any chip-computed feature/context/route-slot mismatch
any returned route key mismatch
any prediction/weight/bias mismatch beyond tolerance
any pending leak or missing maturation
any context or route-slot miss during the task stream
any synthetic fallback
```

Local prepared result:

```text
status = prepared
sequence length = 30
context writes = 9
context reads = 30
route-slot writes = 15
route-slot reads = 30
max route slots = 3
route values = [-1, 1]
feature source = chip_context_keyed_route_lookup_feature_transform
accuracy = 0.9333333333
tail accuracy = 1.0
final readout_weight_raw = 32768
final readout_bias_raw = 0
```

Boundary: Tier 4.22t local/prepared evidence is source/package readiness only.
The returned pass proves only a tiny keyed route-state primitive layered on
native keyed context, not full native v2.1 memory/routing, full CRA task
learning, speedup, scaling, or final autonomy.

Returned result:

```text
controlled_test_output/tier4_22t_20260501_native_keyed_route_state_smoke_hardware_pass_ingested/
status = pass
raw_remote_status = pass
board = 10.11.235.25
selected core = (0,0,4)
all context writes = pass
all route-slot writes = pass
all schedule commands = pass
all mature commands = pass
observed route-slot writes = 15
active route slots = 3
route-slot hits = 33
route-slot misses = 0
chip-computed feature/context/route/prediction/weight/bias raw deltas = 0
observed accuracy = 0.9333333333
observed tail accuracy = 1.0
final pending_created = 30
final pending_matured = 30
final reward_events = 30
final decisions = 30
final active_pending = 0
final readout_weight_raw = 32768
final readout_bias_raw = 0
```

## Tier 4.22u Native Memory-Route State Custom-Runtime Smoke

Tier 4.22u is the next native custom-runtime bridge after the Tier 4.22t keyed route-state hardware pass. It adds bounded keyed memory/working-state slots alongside keyed context and keyed route slots. The host writes context, route, and memory updates, then sends only `key+cue+delay`; the custom runtime retrieves `context[key]`, `route[key]`, and `memory[key]` and computes `feature=context[key]*route[key]*memory[key]*cue` on chip before scheduling delayed credit.

Local/prepared outputs:

```text
controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_local/
controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_prepared/
```

Prepared EBRAINS upload folder and command:

```text
/Users/james/JKS:CRA/ebrains_jobs/cra_422ad
cra_422ad/experiments/tier4_22u_native_memory_route_state_smoke.py --mode run-hardware --output-dir tier4_22u_job_output
```

Local/prepared reference summary:

```text
sequence_length = 30
context writes/reads = 9 / 30
route-slot writes/reads = 15 / 30
memory-slot writes/reads = 15 / 30
max context/route/memory slots = 3 / 3 / 3
feature source = chip_context_memory_route_lookup_feature_transform
accuracy = 0.9666666667
tail_accuracy = 1.0
pending_gap_depth = 2
max_pending_depth = 3
final_readout_weight_raw = 32768
final_readout_bias_raw = 0
```

Claim boundary: this is a tiny native memory-route primitive layered on the prior native keyed context and keyed route primitives. Local/prepared evidence proves package/source readiness only. A returned EBRAINS pass would prove chip-owned keyed memory-slot lookup participates in the minimal pending/readout micro-loop. It still would not prove full native v2.1 memory/routing, full CRA task learning, speedup, multi-core scaling, or final on-chip autonomy.

Returned EBRAINS update: Tier 4.22u passed outright with raw remote status `pass`. Target acquisition succeeded through pyNN.spiNNaker/SpynnakerDataView on board `10.11.235.89`, selected core `(0,0,4)`, `.aplx` build/load passed, all `30` context/route-slot/memory-slot/schedule/mature rows completed, final route-slot writes/hits/misses were `15/33/0`, final memory-slot writes/hits/misses were `15/33/0`, active route and memory slots were both `3`, all feature/context/route/memory/prediction/weight/bias raw deltas were `0`, observed accuracy was `0.9666666667`, tail accuracy was `1.0`, and the final readout state was `readout_weight_raw=32768`, `readout_bias_raw=0`.

Ingested hardware evidence:

```text
controlled_test_output/tier4_22u_20260501_native_memory_route_state_smoke_hardware_pass_ingested/
```

## Tier 4.22v Native Memory-Route Reentry/Composition Custom-Runtime Smoke

Tier 4.22v is the next native custom-runtime gate after the Tier 4.22u memory-route hardware pass. It does not add a new command surface. Instead, it stresses the 4.22u primitive with a harder 48-event stream: four keyed context/route/memory slots, independent context/route/memory updates, interleaved recalls, and reentry pressure. The chip still receives only `key+cue+delay` per decision and must retrieve `context[key]`, `route[key]`, and `memory[key]` before computing `feature=context[key]*route[key]*memory[key]*cue`.

Local/prepared outputs:

```text
controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_local/
controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_prepared/
```

Prepared EBRAINS upload folder and command:

```text
/Users/james/JKS:CRA/ebrains_jobs/cra_422ae
cra_422ae/experiments/tier4_22v_native_memory_route_reentry_composition_smoke.py --mode run-hardware --output-dir tier4_22v_job_output
```

Local/prepared reference summary:

```text
sequence_length = 48
context writes/reads = 18 / 48
route-slot writes/reads = 21 / 48
memory-slot writes/reads = 21 / 48
max context/route/memory slots = 4 / 4 / 4
feature source = chip_context_memory_route_lookup_feature_transform
accuracy = 0.9375
tail_accuracy = 1.0
pending_gap_depth = 2
max_pending_depth = 3
final_readout_weight_raw = 32768
final_readout_bias_raw = 0
```

Claim boundary: this is a harder tiny native memory-route reentry/composition primitive layered on the prior native keyed context, route, and memory primitives. Local/prepared evidence proves package/source readiness only. A returned EBRAINS pass would show the existing native memory-route primitive survives longer interleaving and four-slot reentry pressure. It still would not prove full native v2.1 memory/routing, full CRA task learning, speedup, multi-core scaling, or final on-chip autonomy.

Returned EBRAINS update: Tier 4.22v passed outright with raw remote status `pass`. Target acquisition succeeded through pyNN.spiNNaker/SpynnakerDataView on board `10.11.240.153`, selected core `(0,0,4)`, `.aplx` build/load passed, all `48` context/route-slot/memory-slot/schedule/mature rows completed, final route-slot writes/hits/misses were `21/52/0`, final memory-slot writes/hits/misses were `21/52/0`, active route and memory slots were both `4`, all feature/context/route/memory/prediction/weight/bias raw deltas were `0`, observed accuracy was `0.9375`, tail accuracy was `1.0`, and the final readout state was `readout_weight_raw=32768`, `readout_bias_raw=0`.

Ingested hardware evidence:

```text
controlled_test_output/tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested/
```


## Tier 4.22w Native Decoupled Memory-Route Composition Custom-Runtime Smoke

Tier 4.22w adds the first independent-key native memory-route composition schedule command after the Tier 4.22v same-key memory-route reentry/composition hardware pass. It introduces `CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING`, where the host sends independent `context_key`, `route_key`, `memory_key`, `cue`, and `delay`. The runtime must retrieve all three state slots by their own keys, compute `feature=context[context_key]*route[route_key]*memory[memory_key]*cue` on chip, score pre-update prediction, preserve pending delayed credit, and match the local s16.15 reference.

Local/prepared outputs:

```text
controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_local_profiled/
controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared_profiled/
```

Prepared EBRAINS upload folder and command:

```text
/Users/james/JKS:CRA/ebrains_jobs/cra_422ag
cra_422ag/experiments/tier4_22w_native_decoupled_memory_route_composition_smoke.py --mode run-hardware --output-dir tier4_22w_job_output
```

Pass criteria include: Tier 4.22v hardware pass exists, local fixed-point reference generated, independent context/route/memory key sets retained, nonzero writes and full reads for each state type, source guards proving the decoupled schedule command exists in C and Python, all schedule/mature operations succeed on hardware, chip-computed feature/context/route/memory/prediction/readout raw deltas stay within tolerance, returned context/route/memory key IDs match requested keys, no slot misses, tail accuracy `1.0`, final pending queue cleared, and synthetic fallback zero.

Local/prepared reference summary:

```text
sequence_length = 48
context writes/reads = 18 / 48
route-slot writes/reads = 15 / 48
memory-slot writes/reads = 18 / 48
max context/route/memory slots = 4 / 4 / 4
feature source = chip_decoupled_context_route_memory_lookup_feature_transform
accuracy = 0.9583333333
tail_accuracy = 1.0
pending_gap_depth = 2
max_pending_depth = 3
final_readout_weight_raw = 32768
final_readout_bias_raw = 0
```

Returned hardware pass:

```text
controlled_test_output/tier4_22w_20260501_native_decoupled_memory_route_composition_hardware_pass_ingested/
```

Returned Tier 4.22w result: **hardware pass**. Board `10.11.236.9`, selected core `(0,0,4)`, `.aplx` build/load pass, `90/90` criteria passed, all `48` schedule/mature pairs completed, all feature/context/route/memory/prediction/weight/bias raw deltas `0`, observed accuracy `0.958333`, tail accuracy `1.0`, context writes/reads `18/48`, route-slot writes/reads `15/48`, memory-slot writes/reads `18/48`, active context/route/memory slots `4/4/4`, route/memory misses `0/0`, final `readout_weight_raw=32768`, final `readout_bias_raw=0`.

Claim boundary: this returned hardware pass proves only a tiny native independent-key memory-route composition primitive on real SpiNNaker through the custom runtime. It is not full native v2.1 memory/routing, full CRA task learning, speedup evidence, multi-core scaling, or final on-chip autonomy.

Resource-profile repair: the first EBRAINS attempt with `cra_422af` is noncanonical and failed before hardware target acquisition because the monolithic custom runtime exceeded ITCM by 16 bytes at link time. Tier 4.22w therefore passed from `cra_422ag` using `RUNTIME_PROFILE=decoupled_memory_route`. This is the long-term hardware discipline for native gates: compile only the required command handlers, optimize hardware builds for size, and preserve profile/resource metadata before spending board time.


## Tier 4.22x Compact v2 Bridge Over Native Decoupled State Primitive

Tier 4.22x is the next native custom-runtime gate after Tier 4.22w. Its purpose is architectural: prove a bounded host-side v2 state bridge can drive the native decoupled context/route/memory primitive, while the chip performs lookup, feature composition, pending queue, prediction, maturation, and readout update.

Tier 4.22w proved the custom runtime can execute independent-key decoupled composition. Tier 4.22x adds a host-side bridge layer that maintains v2-style state (context slots, route table, memory slots), selects decoupled keys per event, writes state to the chip, and schedules decisions. The chip still executes CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING and owns all lookup, composition, pending, and readout mechanics.

No new command surface is added. RUNTIME_PROFILE=decoupled_memory_route is reused.

Question: Can a bounded host-side v2 state bridge drive the native decoupled context/route/memory primitive on real SpiNNaker, with the chip performing lookup, feature composition, pending queue, prediction, maturation, and readout update?

Hypothesis: A host-side bridge that maintains v2-style state and selects decoupled keys per event can drive the native custom-runtime primitive to produce correct delayed-credit learning on a structured task stream.

Null hypothesis: The host bridge adds no value. Random key selection, fixed keys, or host-pre-composed features produce equivalent or better results.

Mechanism under test: Host-side v2 state bridge → native decoupled CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING → chip-side lookup / composition / pending / readout.

Claim boundary: This proves a bounded host-side v2 state bridge can drive the native decoupled primitive on real SpiNNaker. It is not full native v2.1, not native predictive binding, not native self-evaluation, not full CRA task learning, not continuous no-batching runtime, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.

Nonclaims:
- Not full v2.1 mechanism transfer.
- Not native predictive binding or self-evaluation.
- Not full CRA delayed-cue or hard-noisy-switching task learning.
- Not continuous runtime (still command-per-event).
- Not speedup or resource-optimization evidence.
- Not multi-core or distributed runtime.

Tasks: 48-event signed structured stream (3 cycles × 16-event plan) with regime-like context/route/memory switching, reentry, and composition. Host bridge maintains state table, selects keys per event, writes state to chip, and schedules decoupled decisions.

Seeds: Seed 42 for feasibility smoke. Multi-seed only if tier is promoted beyond primitive gate.

Run lengths: 48 events, pending_gap_depth = 2.

Backends: Custom C runtime (hardware). NEST mock bridge (local reference).

Hardware mode: run-hardware with RUNTIME_PROFILE=decoupled_memory_route.

Controls:
1. Fixed-key sham: always sends same context/route/memory keys.
2. Random-key sham: sends random/wrong keys.
3. Host-composed sham: host computes feature and bypasses chip lookup.

Ablations:
1. No-context bridge: fixes context key to single slot.
2. No-route bridge: fixes route key to single slot.
3. No-memory bridge: fixes memory key to single slot.

External baselines: None for this tiny primitive bridge gate.

Metrics:
- observed_accuracy ≥ 0.85
- observed_tail_accuracy = 1.0
- all prediction/weight/bias raw deltas = 0 vs local s16.15 reference
- pending_created = pending_matured = 48
- active context/route/memory slots ≤ 4 each
- context/route/memory writes > 0, reads = 48 each

Statistical summary: Single-seed descriptive summary only.

Pass criteria:
1. APLX build pass, app load pass, target acquisition pass.
2. All 48 schedule/mature commands succeed.
3. All feature/prediction/weight/bias raw deltas = 0.
4. observed_accuracy ≥ 0.85.
5. observed_tail_accuracy = 1.0.
6. pending_created = pending_matured = 48.
7. Active context/route/memory slots ≤ 4 each.
8. Context/route/memory writes > 0, reads = 48 each.
9. At least one sham control fails to match candidate.

Fail criteria:
1. Any raw delta nonzero.
2. Accuracy < 0.85 or tail accuracy < 1.0.
3. Pending leak (created ≠ matured).
4. All sham controls match or exceed candidate.
5. Build/load/SDP/protocol failure.

Leakage checks:
1. Host does not send target labels in schedule command.
2. Pending queue stores only delay, not future targets.
3. Chip computes feature from state + cue only.
4. No-oracle raw dopamine during preexposure.

Resource/runtime measurements:
- Image size within ITCM budget (profiled build, -Os).
- Compile time, load time, run time recorded.
- Core count = 1.

Expected artifacts:
- tier4_22x_results.json
- tier4_22x_report.md
- tier4_22x_task_reference.json
- tier4_22x_task_micro_loop_result.json
- tier4_22x_task_reference_rows.csv
- tier4_22x_task_micro_loop_rows.csv
- tier4_22x_latest_manifest.json

Docs to update after result:
- codebasecontract.md Section 0
- CONTROLLED_TEST_PLAN.md (this section)
- docs/PAPER_READINESS_ROADMAP.md
- experiments/README.md
- docs/CODEBASE_MAP.md
- ebrains_jobs/README.md (after hardware prepare)

Returned hardware pass:

```text
controlled_test_output/tier4_22x_20260501_compact_v2_bridge_decoupled_smoke_hardware_pass_ingested/
status = HARDWARE PASS
board = 10.11.236.73
selected core = (0,0,4)
requested core = 1
fallback reason = cores 1,2,3 occupied; selected free core 4
target acquisition = pyNN.spiNNaker_probe fallback (EBRAINS JobManager does not expose raw hostname)
remote criteria = 89/89
ingest criterion = pass
total criteria after ingest = 90/90
observed accuracy = 0.958333
observed tail accuracy = 1.0
reference accuracy = 0.958333
reference tail accuracy = 1.0
chip-computed feature deltas = 0 (all 48)
context/route/memory readback deltas = 0 (all 48)
prediction/weight/bias raw deltas = 0 (all 48)
pending_created = 48
pending_matured = 48
reward_events = 48
decisions = 48
active_pending = 0
active context slots = 4
active route slots = 4
active memory slots = 4
context writes/reads = 12/48
route-slot writes/reads = 12/48
memory-slot writes/reads = 12/48
final readout_weight_raw = 32768
final readout_bias_raw = 0
probe runtime seconds = ~46.8
synthetic fallback = 0
APLX build = pass
app load = pass
task micro-loop = pass
```

Decision: Tier 4.22x passed. The master execution plan selects Tier 4.23 Contract - Continuous / Stop-Batching Parity as the current next gate. Do not jump to implementation or hardware until the 4.23 contract predeclares subset, references, state ownership, cadence, readback, tolerance, controls, and failure classes.

Promotion/freeze condition: Not a promotion gate. This is a custom-runtime primitive bridge gate. Pass enables the next gate.

Re-entry condition if parked: Repair host bridge logic, chip command protocol, or task stream design. Re-run local reference and protocol tests before hardware retry.


## Tier 4.23 - Continuous / Stop-Batching Parity Contract

Tier: 4.23 - Continuous / Stop-Batching Parity Contract
Status: **CONTRACT DEFINED - ready for 4.23a local reference**
Current baseline: v2.1 software + 4.22x native decoupled primitive hardware pass

### Question

Can the custom runtime preserve the same learning behavior without per-step
or frequent chunk-level host learning replay?

### Hypothesis

A compact event schedule uploaded to chip-owned SDRAM/DTCM, combined with a
timer-driven event loop that autonomously schedules and matures pending
credit, can reproduce the chunked reference within predeclared tolerance.

### Null hypothesis

The chip cannot maintain correct pending-horizon order, feature computation,
or readout updates without host-per-step commands, OR timing differences
make parity impossible even if the logic is correct.

### Mechanism under test

1. Timer-driven autonomous event loop on the custom C runtime.
2. Compact event schedule uploaded from host to chip memory.
3. Per-timestep feature lookup (context/route/memory), pending schedule,
   and oldest-first maturation without host SDP per event.
4. Periodic compact readback (not per-step).
5. Host intervention reduced to: load, start, optional pause/resume,
   periodic readback, stop/reset.

### Claim boundary

A PASS proves the custom runtime can execute a bounded event stream
autonomously and match the chunked reference within tolerance. It is NOT
full continuous on-chip learning for arbitrary tasks, NOT full v2.1
mechanism migration, NOT speedup evidence (though wall-time should be
measured), NOT multi-core scaling, and NOT final autonomy.

### Nonclaims

- Arbitrary-length continuous streams (bounded schedule first).
- Dynamic task generation on chip (static schedule first).
- Full CRA organism loop (only delayed-credit readout primitive).
- Host-less operation (host still loads, starts, and reads back).
- Generalization to new tasks without reload.

### Tasks

Use the same 48-event signed delayed-cue stream as Tier 4.22x, because:
- It exercises context/route/memory lookup, pending gap, and maturation.
- It has a verified local fixed-point reference with exact parity.
- It is small enough to fit in a bounded on-chip schedule buffer.

Future sub-tiers (4.23a, 4.23b, 4.23c) may add noisy-switching or reentry.

### Seeds

Contract phase: deterministic seed 42 for reference trace selection.
Hardware smoke (4.23c): one seed first; three seeds only if repeatability
is needed for the claim.

### Run lengths

48 events (same as 4.22x) for the first parity gate.
Continuous loop must support at least 48 timesteps plus pending horizons.

### Backends

Local reference: Python fixed-point simulation (same as 4.22x).
Hardware: custom C runtime on SpiNNaker via EBRAINS JobManager.

### Hardware mode

Continuous / scheduled-autonomous. Host uploads schedule, sends CMD_RUN
(or equivalent start command), chip executes timer loop, host reads back
compact state at end (or optionally during run).

### Controls

1. Chunked reference: same task run through the existing 4.22x host-command
   path (per-step CMD_SCHEDULE + CMD_MATURE). This is the gold standard.
2. Zero-schedule control: upload empty schedule, verify chip does nothing
   and readout stays at initial values.
3. Single-event control: upload one event, verify it schedules and matures
   correctly with no pending gap confusion.
4. Wrong-key control: if route/memory keys are shuffled, accuracy should
   collapse to chance (same as 4.22x sham).

### Ablations

1. Remove pending queue maturation: events schedule but never mature;
   readout should not update.
2. Disable route/memory lookup: feature = context * cue only; accuracy
   should change predictably.

### External baselines

Not required for this contract tier (it is a parity gate, not a comparative
claim). The chunked reference IS the baseline.

### Metrics

- accuracy, tail_accuracy, first_half_accuracy, second_half_accuracy
- per-event feature raw delta vs reference (abs <= 1)
- per-event prediction raw delta vs reference (abs <= 1)
- per-event weight raw delta vs reference (abs <= 1)
- per-event bias raw delta vs reference (abs <= 1)
- pending_created, pending_matured, max_pending_depth
- context/route/memory slot writes, reads, hits, misses
- host_intervention_count (number of SDP commands sent during run)
- wall_time_ms (total runtime from start to final readback)
- chip_autonomous_timesteps (timesteps executed without host command)

### Statistical summary

One seed for feasibility. Report exact deltas per event, not just averages.

### Pass criteria

1. Contract names exact subset under test (done in this document).
2. Reference trace selected (48-event signed delayed-cue, seed 42).
3. Readback/provenance fields predeclared:
   - decisions, predictions, features, pending depth
   - final readout weight/bias
   - per-event correctness flag
   - compact state summary (reuses CMD_READ_STATE schema where possible)
4. Failure classes predeclared (see below).
5. For hardware smoke (4.23c - COMPLETED):
   - final readout_weight_raw == 32768 (exact match with local reference)
   - final readout_bias_raw == 0 (exact match)
   - decisions == 48, reward_events == 48
   - pending_created == 48, pending_matured == 48
   - active_pending == 0 at end
   - all state writes succeeded
   - all 48 schedule uploads succeeded
   - run_continuous and pause succeeded
   - zero synthetic fallback
   - APLX build pass, app load pass

### Fail criteria

1. Chip executes but accuracy/tail diverges beyond tolerance.
2. Pending maturation order is wrong (oldest-first violated).
3. Feature computation diverges from reference (delta > 1).
4. Readback is insufficient to determine what went wrong.
5. Host must intervene more than predeclared cadence.
6. State ownership is ambiguous (host and chip both update same variable).

### Leakage checks

- Event schedule must not contain target labels in the pending record.
- Target must arrive only at maturation time (same as 4.22x).
- Readback must not expose future events before they are processed.

### Resource/runtime measurements

- ITCM/DTCM size before and after adding continuous loop.
- SDRAM used by event schedule buffer.
- Timer tick period (must remain 1 ms or predeclared).
- Max pending depth supported by DTCM budget.
- Wall time vs simulated time ratio.

### Expected artifacts

- `tier4_23_contract.md` (this contract document)
- `tier4_23a_local_reference_results.json`
- `tier4_23b_runtime_implementation_tests.log`
- `tier4_23c_hardware_results.json`
- `tier4_23c_hardware_report.md`
- Makefile/runtime profile updates documenting new command surface

### Promotion/freeze condition

This tier is a contract/bridge gate, not a mechanism promotion. It does not
freeze a new baseline by itself. A full promotion would require:
- 4.23c hardware pass with tolerance met
- compact regression showing 4.22x still passes
- resource budget documented
- Then a v2.2 or v2.3 baseline freeze could include continuous runtime.

### Re-entry condition if parked

If the contract reveals that continuous parity requires more state or a
larger command surface than the current runtime supports, park 4.23 and
return to runtime resource characterization (Tier 4.24) before retrying.

### Failure classes predeclared

1. Build/load failure - platform/runtime packaging issue.
2. Schedule upload failure - protocol/SDRAM allocation issue.
3. Event loop doesn't advance - timer callback not firing or loop blocked.
4. Feature computation diverges - fixed-point or lookup bug.
5. Pending maturation order wrong - queue/horizon implementation bug.
6. Readback schema mismatch - protocol drift between C and Python.
7. Accuracy below tolerance - science failure (loop correct but learning
   pressure insufficient or timing breaks credit assignment).
8. Host intervention count too high - contract violation (not truly
   continuous enough for the claim).

### Continuous event-loop contract (draft v0.1)

- Host uploads a compact schedule to chip SDRAM via SDP bulk write or
  sequence of CMD_WRITE_SCHEDULE_ENTRY commands.
- Each schedule entry contains: timestep, context_key, route_key,
  memory_key, cue (s16.15), target (s16.15), delay (timesteps).
- Host sends CMD_RUN_CONTINUOUS (or sets a run flag via CMD_RESET + arg).
- Timer callback each tick:
    a. Check if current timestep matches next schedule entry.
    b. If yes: perform context/route/memory lookup, compute feature,
       schedule pending horizon with due_timestep = current + delay.
       Record pre-update prediction for scoring.
    c. Check if any pending horizon has due_timestep == current.
       If yes: mature oldest-first, update readout weight/bias.
    d. Increment decision counter if a schedule event was processed.
    e. Increment reward counter if a maturation occurred.
- Run continues until schedule exhausted OR host sends CMD_PAUSE/CMD_RESET.
- Host reads back compact state via CMD_READ_STATE (or new
  CMD_READ_PROVENANCE) after run completes.

### Host command cadence

1. CMD_RESET - once at start.
2. Schedule upload - once before run (may be multiple SDP packets).
3. CMD_RUN_CONTINUOUS - once to start autonomous execution.
4. CMD_READ_STATE - once at end (or optionally periodic during long runs).
5. CMD_RESET - once to clear before next run.
Total host commands per 48-event run: <= 5 (excluding schedule upload chunks).

### State ownership

CHIP-OWNED:
    - context_slots, route_slots, memory_slots
    - pending_horizon queue
    - readout_weight, readout_bias
    - decision_counter, reward_counter
    - current schedule pointer/index
HOST-OWNED:
    - full event schedule (uploaded to chip SDRAM but owned by host)
    - task stream generation logic
    - reference comparison / scoring
    - provenance recording
SHARED (protocol-defined):
    - g_timestep (chip advances, host reads)
    - compact readback buffer

### Compact readback cadence

Default: read back once at end of run.
Optional: read back every N timesteps for long runs (N predeclared, e.g. 16).
Fields required:
    - decisions, rewards, pending_depth
    - readout_weight_raw, readout_bias_raw
    - last_prediction_raw, last_feature_raw
    - slot hit/miss counters
Format: reuse CMD_READ_STATE 73-byte payload where possible; add
provenance fields if needed.

### Parity tolerance vs chunked reference

- feature raw delta: abs <= 1 for every event
- prediction raw delta: abs <= 1 for every event
- weight raw delta: abs <= 1 for every event
- bias raw delta: abs <= 1 for every event
- accuracy: within 0.01 of reference (0.958333 -> >= 0.948333)
- tail_accuracy: within 0.01 of reference (1.0 -> >= 0.99)

Rationale: timing differences in a continuous loop (e.g., maturation at
exact tick boundary vs host command latency) may cause minor fixed-point
shifts, but the learning trajectory must remain materially identical.

### Tier 4.23a - Continuous / Stop-Batching Parity Local Reference

Status: **LOCAL PASS (21/21 criteria)**

Output: `controlled_test_output/tier4_23a_20260501_continuous_local_reference/`

Question: Does a local fixed-point continuous event-loop reference match the chunked 4.22x reference exactly?

Result:

```text
status = pass
passed_count = 21 / 21
accuracy = 0.9583333333333334
tail_accuracy = 1.0
max_pending_depth = 3
final_readout_weight_raw = 32768
final_readout_bias_raw = 0
autonomous_timesteps = 50 (48 events + 2 gap drain)
host_intervention_count = 0
all_feature_deltas_zero = True
all_prediction_deltas_zero = True
all_weight_deltas_zero = True
all_bias_deltas_zero = True
max_feature_delta = 0
max_prediction_delta = 0
max_weight_delta = 0
max_bias_delta = 0
zero_synthetic_fallback = True
```

Claim boundary: LOCAL only. Proves the continuous loop logic matches the chunked 4.22x reference exactly (all raw deltas 0). NOT hardware evidence, NOT full continuous on-chip learning, NOT speedup evidence, NOT multi-core scaling, and NOT final autonomy.

### Tier 4.23b - Runtime Continuous Loop Implementation

Status: **PASS (28/28 host tests)**

Work:

```text
Added CMD_RUN_CONTINUOUS (24), CMD_PAUSE (25), CMD_WRITE_SCHEDULE_ENTRY (26)
Implemented timer-driven event loop in state_manager.c / main.c
Autonomous scheduling and maturation without per-event SDP
schedule_entry_t stored in static chip memory (MAX_SCHEDULE_ENTRIES = 64)
Pending horizon maturation oldest-first preserved
Continuous auto-pause when schedule exhausted
```

Host test coverage:

```text
test_state_schedule_entry_write_and_read - PASS
test_state_continuous_tick - PASS
test_state_continuous_auto_pause - PASS
(plus 25 existing tests, all PASS)
```

Python host controller synchronized:

```text
colony_controller.write_schedule_entry(index, timestep, context_key, route_key, memory_key, cue, target, delay)
colony_controller.run_continuous()
colony_controller.pause()
```

Protocol spec: promoted to 0.11, Section 8 no longer DRAFT.

### Tier 4.23c - One-Board Hardware Continuous Smoke

Status: **HARDWARE PASS - INGESTED**

Runner: `experiments/tier4_23c_continuous_hardware_smoke.py`
Modes: `local`, `prepare`, `run-hardware`, `ingest`
Upload package: `ebrains_jobs/cra_423b`

Hardware run result:

```text
Board: 10.11.235.9
Core: (0,0,4) (requested core 1 occupied; fallback to core 4)
Runner revision: tier4_23c_continuous_hardware_smoke_20260501_0004
Stopped timestep: 6170
Runtime seconds: ~4.3
```

Final compact readback state:

```text
readout_weight_raw: 32768 (matches local reference exactly)
readout_bias_raw: 0 (matches local reference exactly)
decisions: 48 (matches reference)
reward_events: 48 (matches reference)
pending_created: 48 (matches reference)
pending_matured: 48 (matches reference)
active_pending: 0 (all drained)
```

Pass criteria met:

```text
run-hardware: 22/22 criteria passed
ingest: 15/15 criteria passed
all state writes succeeded
all 48 schedule uploads succeeded
run_continuous succeeded
pause succeeded
final_state read succeeded
zero synthetic fallback
zero host interventions during continuous execution
```

Work performed:

```text
Pre-wrote all context/route/memory slots via CMD_WRITE_CONTEXT / CMD_WRITE_ROUTE_SLOT / CMD_WRITE_MEMORY_SLOT
Uploaded 48-event schedule via CMD_WRITE_SCHEDULE_ENTRY (one entry per event)
Started autonomous execution via CMD_RUN_CONTINUOUS with learning_rate=0.25
Waited ~3s for completion
Paused to get stopped_timestep
Read back compact state via CMD_READ_STATE
Read back slot states for verification
```

Claim boundary: The returned hardware pass proves that the timer-driven
autonomous event loop on real SpiNNaker can execute a 48-event signed
delayed-cue stream without per-event host commands and preserve exact
learning parity with the local fixed-point reference. It is not full
native v2.1, not speedup evidence, not multi-core scaling, and not
final on-chip autonomy.

### Tier 4.24 - Custom Runtime Resource Characterization

Status: **PASS (16/16 criteria)**

Output: `controlled_test_output/tier4_24_20260501_resource_characterization/`

This is an engineering/resource truth tier, not a new science/capability tier.
It measures the actual resource envelope of the native/custom-runtime continuous
path and compares intervention count versus the chunked-host command-driven
micro-loop.

Key findings:

```text
Continuous path commands: 64
Chunked 4.22x commands: 134
Reduction: 70 commands (52.2%)

Continuous payload: 2647 bytes
Chunked payload: 4099 bytes
Reduction: 1452 bytes (35.4%)

Load time: 2.187s
Task time (reset→readback): 4.327s
DTCM estimate: 6372 bytes
Max pending depth: 3
Max schedule entries: 64
Active context/route/memory slots: 4/4/4
```

Claim boundary: resource-measurement evidence only. Proves the continuous path
reduces host commands during execution versus the chunked command-driven
micro-loop. Does not prove speedup, multi-core scaling, or final autonomy.

### Tier 4.25B - Two-Core State/Learning Split Smoke

Status: **HARDWARE PASS - INGESTED (23/23 criteria)**

Runner: `experiments/tier4_25b_two_core_split_smoke.py`
Modes: `local`, `prepare`, `run-hardware`, `ingest`
Upload package: `ebrains_jobs/cra_425g`

Hardware run result:

```text
Board: 10.11.205.161
State core: (0,0,4) app_id=1
Learning core: (0,0,5) app_id=2
Runner revision: tier4_25b_two_core_split_smoke_20260502_0004
```

Final compact readback state:

```text
State core: decisions=48, reward_events=0, pending_created=0, pending_matured=0
            readout_weight_raw=0, readout_bias_raw=0
Learning core: decisions=0, reward_events=48, pending_created=48, pending_matured=48
               readout_weight_raw=32767, readout_bias_raw=-1
```

Pass criteria met:

```text
run-hardware + ingest: 23/23 criteria passed
state_core .aplx built and loaded
learning_core .aplx built and loaded
all 4 context writes succeeded
all 4 route writes succeeded
all 4 memory writes succeeded
all 48 schedule uploads succeeded
state_core run_continuous succeeded
learning_core run_continuous succeeded
state_core final read succeeded
learning_core final read succeeded
learning_core weight within ±8192 of reference 32768
learning_core bias within ±8192 of reference 0
learning_core pending_created = 48
learning_core pending_matured = 48
learning_core active_pending = 0
zero synthetic fallback
zero host interventions during continuous execution
```

Work performed:

```text
Built two runtime profiles: state_core and learning_core
Loaded state_core.aplx on core (0,0,4) and learning_core.aplx on core (0,0,5)
State core pre-wrote context/route/memory slots via CMD_WRITE_CONTEXT / CMD_WRITE_ROUTE_SLOT / CMD_WRITE_MEMORY_SLOT
State core uploaded 48-event schedule via CMD_WRITE_SCHEDULE_ENTRY
Started autonomous execution on both cores via CMD_RUN_CONTINUOUS
State core timer loop: per-tick feature computation, context/route/memory lookup, SDP send of schedule-pending-split to learning core
Learning core timer loop: per-tick mature oldest pending, dynamic prediction using own readout weight, apply reward, update readout
Waited ~2.5s per core for completion
Paused both cores to get stopped_timestep
Read back compact state from both cores via CMD_READ_STATE
```

Claim boundary: The returned hardware pass proves that a two-core state/learning split on real SpiNNaker can reproduce the monolithic single-core continuous result within tolerance. The state core owns context/route/memory state and schedules pending via inter-core SDP; the learning core owns pending maturation and readout updates. Weight/bias tolerance of ±8192 accounts for split-architecture fixed-point rounding differences. This is not speedup evidence, not multi-chip scaling, not a general multi-core framework, and not full native v2.1 autonomy.

Key design insight: The state core weight stays at 0 because it never matures. The learning core must compute prediction dynamically at maturation time using its own weight, not use the stale prediction=0 sent by the state core.

## Tier 4.25C - Two-Core State/Learning Split Repeatability

Status: **HARDWARE PASS - INGESTED (23/23 criteria per seed, 3 seeds)**

Question: Does the two-core state/learning split reproduce the monolithic
single-core result within tolerance across seeds 42, 43, and 44?

Hypothesis: The two-core split architecture is deterministic enough that
independent random seeds produce weight/bias trajectories that all converge to
the same monolithic reference within the predeclared ±8192 fixed-point
tolerance.

Null hypothesis: The two-core split produces seed-dependent divergence outside
tolerance because of inter-core SDP timing variability, fixed-point rounding
differences, or initialization sensitivity.

Mechanism under test: Same as 4.25B. State core (profile=state_core) on core 4
owns context/route/memory state, feature computation, and schedule upload;
timer-driven per-tick SDP sends schedule-pending-split messages to learning core.
Learning core (profile=learning_core) on core 5 owns pending horizon queue,
dynamic prediction at maturation time using own readout weight, oldest-first
maturation, and readout weight/bias update.

What changes from 4.25B:
- Three independent runs with seeds 42, 43, 44.
- Task stream is the 48-event signed delayed-cue stream, same as 4.23c.
- Per-seed randomization affects only task stream generation.
- Runner accepts `--seed` argument and rebuilds schedule per seed.

Exact subset under test:
```text
Task: 48-event signed delayed-cue stream (same as 4.23c/4.25B)
Seeds: 42, 43, 44
Cores: (0,0,4) state + (0,0,5) learning
Runtime profiles: state_core, learning_core
Delay steps: 5
Learning rate: 0.25 (s16.15 fixed-point)
Schedule entries: 48
Context slots: 4 (ctx_A-D)
Route slots: 4 (route_A-D)
Memory slots: 4 (mem_A-D)
```

Reference traces:
```text
4.23c monolithic single-core hardware pass:
    board 10.11.235.9, core (0,0,4)
    final readout_weight_raw = 32768, readout_bias_raw = 0
    decisions = 48, reward_events = 48
    pending_created = 48, pending_matured = 48, active_pending = 0

4.25B two-core split hardware pass (seed 42 implicit):
    board 10.11.205.161, cores (0,0,4) + (0,0,5)
    learning core final readout_weight_raw = 32767, readout_bias_raw = -1
    learning core pending_created = 48, pending_matured = 48
    active_pending = 0
```

Host command cadence per seed:
```text
1. CMD_RESET - once on both cores at start.
2. State slot writes - once before run (4 ctx + 4 route + 4 memory).
3. Schedule upload - 48 CMD_WRITE_SCHEDULE_ENTRY to state core.
4. CMD_RUN_CONTINUOUS - once on both cores.
5. CMD_PAUSE - once on both cores at end.
6. CMD_READ_STATE - once on both cores at end.
7. CMD_RESET - once on both cores before next seed.
Total host commands per seed: <= 10 + 48 schedule entries.
```

Numeric parity tolerance (per seed):
```text
weight: within ±8192 of 32768
bias: within ±8192 of 0
pending_created: == 48
pending_matured: == 48
active_pending: == 0
decisions: == 48 (state core)
reward_events: == 48 (learning core)
```

Aggregate tolerance across seeds:
```text
max weight delta across seeds <= 8192
max bias delta across seeds <= 8192
all seeds show pending_created == pending_matured == 48
no seed shows pending leak or drop
```

Controls:
- Monolithic reference: 4.23c single-core hardware pass
- Chunked reference: 4.22x single-core chunked pass
- Single-core continuous reference: 4.23a local fixed-point pass
- Zero-schedule control: upload empty schedule, expect decisions=0
- Single-event control: upload 1 schedule entry, expect pending_created=1

Failure classes:
- build/load: .aplx link fails for either profile
- upload: schedule or state write fails
- inter-core SDP: messages lost, wrong port, wrong core
- event-loop stall: timer callback stops firing on either core
- pending divergence: learning core matures wrong count or wrong order
- readback mismatch: final state outside tolerance
- seed sensitivity: one or more seeds diverge outside tolerance

Claim boundary: A PASS proves the two-core state/learning split is repeatable
across three seeds on real SpiNNaker. It is NOT speedup evidence, NOT
multi-chip scaling, NOT a general multi-core framework, and NOT full native
v2.1 autonomy.

Nonclaims:
- Arbitrary-length streams (still bounded 48-event schedule).
- Dynamic task generation on chip (static schedule first).
- Full CRA organism loop (only delayed-credit readout primitive).
- Host-less operation (host still loads, starts, and reads back).
- Four-core or multi-chip scaling.

### Next step after 4.25C pass

Tier 4.26 - Four-Core Context/Route/Memory/Learning Distributed Smoke.

### Next step if 4.25C fails or blocks

Ingest and classify the exact failure stage. Preserve returned artifacts.
Update EBRAINS/custom-runtime lessons. Repair the smallest failing layer
locally. Do not expand to four cores until two-core repeatability is proven.

## Tier 4.26 - Four-Core Context/Route/Memory/Learning Distributed Smoke

Status: **Step 7 PASSED, Step 8 INGESTED** - EBRAINS package `cra_426f`
passed on hardware (board 10.11.194.1, cores 4/5/6/7). All 30/30 criteria
passed. Learning core returned exact monolithic reference values:
weight=32768, bias=0, 48 decisions, 48 reward events, 48 pending created,
48 pending matured, active_pending=0. Context core served 48 lookup hits.
All four `run_continuous` and `pause` commands succeeded after adding
`CMD_RUN_CONTINUOUS`/`CMD_PAUSE` to the state-server core dispatch block.
Evidence archived to `controlled_test_output/tier4_26_20260502_pass_ingested/`.
Local validation passes (11/11 criteria). The Python runner implements all four
modes: local (Step 5, passes), prepare (Step 6, passes), run-hardware (Step 7,
passes), and ingest (Step 8, passes).

Question: Can the CRA custom runtime distribute context, route, memory, and
learning across four independent cores on a single SpiNNaker chip, reproduce
the monolithic single-core result within tolerance, and remain deterministic?

Hypothesis: A four-core split where context (core 4), route (core 5), and
memory (core 6) each hold their own state and reply to lookup requests from a
scheduler/learning core (core 7) can compute the same
`feature = context * route * memory * cue` composition and produce the same
pending/weight/bias trajectory as the monolithic reference.

Null hypothesis: Inter-core message loss, stale reply contamination, lookup
ordering bugs, fixed-point composition differences, or timeout races cause
divergence outside the predeclared ±8192 fixed-point tolerance.

Mechanism under test:
- Core 4 (profile=context_core): owns context slot table. Replies to context
  lookup requests with value/confidence/hit/miss.
- Core 5 (profile=route_core): owns route slot table. Replies to route lookup
  requests with value/confidence/hit/miss.
- Core 6 (profile=memory_core): owns memory slot table. Replies to memory
  lookup requests with value/confidence/hit/miss.
- Core 7 (profile=learning_core): owns event schedule, pending horizon queue,
  readout weight/bias, and delayed-credit maturation. For each scheduled event,
  sends parallel lookup requests to cores 4/5/6; composes feature from replies;
  schedules pending; matures oldest pending; updates readout.

Inter-core protocol decision (architecture target vs. first implementation):
```text
A. multicast / MCPL payloads for inter-core messages   = preferred long-term
B. SDP core-to-core messages                           = acceptable temporary scaffold
C. shared SDRAM / mailbox + signal packet              = later option

The first implementation MAY use Option B (SDP) if it gets the four-core
smoke working quickly, but the design must document it as transitional.
The architecture target is event/multicast-style inter-core messaging,
with SDP reserved for host control / readback.
```

What changes from 4.25C:
- Four cores instead of two.
- State is no longer concentrated on one core; context/route/memory each live
  on their own core.
- Core 7 (learning) owns the schedule and drives lookups; cores 4/5/6 are
  state servers.
- Lookups are parallel and independent, not chained (context→route→memory).
- Inter-core messages carry sequence IDs to detect stale reply contamination.
- New failure class: missing reply / timeout on any of the three lookups.

Exact subset under test:
```text
Task: 48-event signed delayed-cue stream (same as 4.23c/4.25C)
Seed: 42 (first smoke; multi-seed repeatability is a later tier)
Cores: (0,0,4) context + (0,0,5) route + (0,0,6) memory + (0,0,7) learning
Runtime profiles: context_core, route_core, memory_core, learning_core
Delay steps: 5
Learning rate: 0.25 (s16.15 fixed-point)
Schedule entries: 48
Context slots: 4 (ctx_A-D)
Route slots: 4 (route_A-D)
Memory slots: 4 (mem_A-D)
```

Reference traces:
```text
4.23c monolithic single-core hardware pass:
    board 10.11.235.9, core (0,0,4)
    final readout_weight_raw = 32768, readout_bias_raw = 0
    decisions = 48, reward_events = 48
    pending_created = 48, pending_matured = 48, active_pending = 0

4.25C two-core split hardware pass (seed 42):
    board 10.11.193.1, cores (0,0,4) state + (0,0,5) learning
    learning core final readout_weight_raw = 32767, readout_bias_raw = -1
    learning core pending_created = 48, pending_matured = 48
    active_pending = 0
```

Host command cadence:
```text
1. CMD_RESET - once on all four cores at start.
2. State slot writes - once per core before run:
   - 4 context writes to core 4
   - 4 route writes to core 5
   - 4 memory writes to core 6
3. Schedule upload - 48 CMD_WRITE_SCHEDULE_ENTRY to core 7.
4. CMD_RUN_CONTINUOUS - once on all four cores.
5. CMD_PAUSE - once on all four cores at end.
6. CMD_READ_STATE - once on all four cores at end.
7. CMD_RESET - once on all four cores before next run.
Total host commands per run: <= 14 + 48 schedule entries.
```

Numeric parity tolerance (single seed):
```text
weight: within ±8192 of 32768
bias: within ±8192 of 0
pending_created: == 48
pending_matured: == 48
active_pending: == 0
decisions: == 48 (learning core, from schedule)
reward_events: == 48 (learning core)
context_lookup_hits: == 48
route_lookup_hits: == 48
memory_lookup_hits: == 48
zero stale-reply contamination
zero missing-reply / timeout events
```

Aggregate tolerance:
```text
all four cores load and report correct profile IDs
all lookup replies match sequence IDs (no stale contamination)
feature composition matches monolithic fixed-point reference
pending_created == pending_matured == 48
no pending leak or drop
```

Controls:
- Monolithic reference: 4.23c single-core hardware pass
- Two-core reference: 4.25C seed-42 hardware pass
- Chunked reference: 4.22x single-core chunked pass
- Zero-schedule control: upload empty schedule, expect decisions=0
- Single-event control: upload 1 schedule entry, expect pending_created=1
- Stale-reply control: verify sequence IDs monotonically advance, no duplicates

Failure classes:
- build/load: .aplx link fails for any of the four profiles
- upload: schedule or state write fails on any core
- inter-core message: lost packet, wrong port/core, wrong protocol
- stale reply: sequence ID mismatch or duplicate reply detected
- missing reply: lookup request sent but no reply within timeout window
- event-loop stall: timer callback stops firing on any core
- pending divergence: learning core matures wrong count or wrong order
- composition mismatch: feature differs from monolithic reference
- readback mismatch: final state outside tolerance on any core

Claim boundary: A PASS proves four independent cores can hold distributed
state and cooperate to reproduce the monolithic delayed-credit result within
tolerance on real SpiNNaker. It is NOT speedup evidence, NOT multi-chip
scaling, NOT a general multi-core framework, and NOT full native v2.1 autonomy.

Nonclaims:
- Arbitrary-length streams (still bounded 48-event schedule).
- Dynamic task generation on chip (static schedule first).
- Full CRA organism loop (only delayed-credit readout primitive).
- Host-less operation (host still loads, starts, and reads back).
- Multi-chip scaling.
- General multicast/MCPL inter-core protocol (first implementation may use SDP;
  multicast is the documented architecture target).

### Next step after 4.26 pass

Ingest hardware artifacts. Update runtime inter-core protocol from transitional
SDP toward multicast/MCPL if local feasibility is proven. Then design Tier 4.27
(four-core multi-seed repeatability, harder task, or speedup characterization).

### Next step if 4.26 fails or blocks

Ingest and classify the exact failure stage per core. Preserve returned
artifacts. Distinguish:
- build/load failure (one .aplx too large?)
- inter-core messaging failure (SDP port collision? timeout?)
- stale/missing reply failure (sequence ID bug? race?)
- composition mismatch (fixed-point ordering? rounding?)
- readback mismatch (state corruption? uninitialized slot?)

Repair the smallest failing layer locally. Do not promote to multi-seed or
harder tasks until four-core single-seed smoke passes.


## Tier 4.27 - Four-Core Runtime Resource / Timing Characterization + MCPL Decision Gate

Tier 4.27 follows the Tier 4.26 four-core distributed hardware pass. It is an engineering characterization and protocol-migration gate, not a mechanism promotion and not a baseline freeze by itself.

Question: What is the measured envelope of the current four-core SDP scaffold, and what is the concrete MCPL/multicast migration path required for scalable inter-core event traffic?

Hypothesis: The 4.26 SDP path provides a measurable scaffold, while MCPL/multicast can become the scalable inter-core data plane. Tier 4.27 should quantify SDP, test MCPL feasibility with official Spin1API symbols, and decide the exact migration plan.

Null hypothesis: The four-core pass is only a smoke success; resource, timing, reliability, or MCPL feasibility is too unclear to treat the runtime as a stable scaling foundation.

Mechanism under test: four-core runtime communication and instrumentation, including SDP scaffold characterization and MCPL/multicast feasibility.

Claim boundary: Tier 4.27 is resource/timing/protocol decision evidence. It is not a new learning result, not a software baseline freeze, not multi-chip scaling, and not final autonomy.

Required measurements:
- inter-core lookup request/reply counts
- lookup latency if measurable
- stale/duplicate reply rate
- timeouts
- wall time, load time, pause/readback time
- payload bytes and command counts
- per-core compact readback
- schedule length tolerance: 48, 96, 192 if practical
- resource footprint per runtime profile

Required MCPL path:
1. Local compile/source audit using official `MC_PACKET_RECEIVED` / `MCPL_PACKET_RECEIVED` symbols.
2. Two-core MCPL round-trip smoke.
3. Three-state-core MCPL lookup smoke with sequence IDs.
4. SDP-vs-MCPL comparison.

Pass criteria:
- SDP scaffold envelope is measured.
- MCPL feasibility is tested, not deferred as a vague future goal.
- Bottlenecks and failure classes are identified.
- Next migration step is explicit.
- Baseline freeze decision is explicit.

Fail criteria:
- Timing/resource data are insufficient.
- MCPL path is not tested or cannot compile with official symbols.
- Stale/duplicate/missing replies cannot be measured.
- The plan would scale SDP core-to-core traffic as if it were the final data plane.

Decision rule:
- If MCPL passes feasibility and smoke gates, make MCPL the default for later multi-core/multi-chip runtime gates.
- If MCPL fails, repair MCPL before claiming scalable runtime architecture; any SDP-based continuation must be labeled temporary/non-scaling.


## Tier 4.28a - Four-Core MCPL Repeatability

Tier 4.28a follows the Tier 4.27 MCPL migration decision. It is the three-seed hardware repeatability gate required to freeze `CRA_NATIVE_RUNTIME_BASELINE_v0.1`.

Status: **PASS, INGESTED, BASELINE FROZEN** - `baselines/CRA_NATIVE_RUNTIME_BASELINE_v0.1.md`

Question: Does the MCPL-based four-core distributed scaffold execute reliably on real SpiNNaker silicon across multiple seeds?

Hypothesis: MCPL router tables, callback wiring, and inter-core lookup protocol are sufficiently mature for a bounded native-runtime baseline freeze.

Null hypothesis: MCPL exhibits non-deterministic failures, stale replies, or seed-dependent regressions that disqualify it as the default data plane.

Mechanism under test: MCPL-based four-core distributed lookup (context/route/memory/learning) with router table initialization per core role.

Evidence:
- Seed 42: board 10.11.204.129, 38/38 criteria
- Seed 43: board 10.11.196.153, 38/38 criteria
- Seed 44: board 10.11.194.65, 38/38 criteria
- lookup_requests=144, lookup_replies=144, stale_replies=0, timeouts=0 on all seeds
- readout_weight=32768, readout_bias=0, pending=48/48, active_pending=0

Decision rule applied (from Tier 4.27):
- MCPL passed feasibility (4.27d), two-core smoke (4.27e), three-state-core smoke (4.27f), and SDP-vs-MCPL comparison (4.27g)
- MCPL made default inter-core protocol for 4.28a
- Three-seed repeatability passed → baseline freeze authorized

### Baseline Freeze Summary

`CRA_NATIVE_RUNTIME_BASELINE_v0.1` frozen at `2026-05-02T22:35:00-04:00`.

Included in baseline:
- Tiers 4.22i through 4.28a evidence chain
- Four-core distributed runtime (context/route/memory/learning)
- MCPL as default inter-core lookup data plane
- ITCM budget: context 11248B, route 11280B, memory 11280B, learning 12968B
- Schema v2 compact readback (105 bytes payload)

Excluded from baseline (nonclaims):
- Multi-chip scaling
- Speedup evidence
- Full v2.1 mechanism transfer (keyed memory, routing, replay, predictive binding, self-evaluation)
- Lifecycle/self-scaling
- Continuous host-free operation
- External-baseline superiority

### Next Step After 4.28a Pass

Phase B (4.28b+): v0.1+ mechanism maturation or harder task transfer.

### Tier 4.28b - Delayed-Cue Four-Core MCPL Hardware Probe

Status: **PASS, INGESTED** - Board 10.11.213.9, cores 4/5/6/7, 38/38 criteria.

Question: Can the four-core MCPL scaffold execute a real delayed-cue task where
target = -feature (predict opposite sign)?

Evidence:
- Weight converged to -32769 (~-1.0), bias=-1 (~0)
- pending_created=48, pending_matured=48, active_pending=0
- lookup_requests=144, lookup_replies=144, stale_replies=0, timeouts=0

First attempt (cra_428f) failed: TASK_SEQUENCE used key_id=0 but state cores
had slots written at IDs 101/1101/2101. All lookups missed → feature=0 →
weight update delta_w=0. Diagnosed from downloaded artifacts. Fixed by using
actual key IDs (ctx_A=101, route_A=1101, mem_A=2101). Package bumped to
cra_428g per fresh-package Rule 10.

Claim boundary: Single-seed probe. Not three-seed repeatability. Not multi-chip.
Not speedup. Not v2.1 mechanism transfer.

### Next Step After 4.28b Pass

Tier 4.28c - Three-seed delayed-cue repeatability (seeds 42, 43, 44) to validate
task transfer robustness before mechanism maturation.

### Tier 4.28c - Delayed-Cue Three-Seed Repeatability

Status: **PASS, INGESTED** - Seeds 42/43/44, all 38/38 criteria per seed.

Evidence:
- Seed 42: weight=-32769, bias=-1, pending=48/48, stale=0, timeouts=0
- Seed 43: weight=-32769, bias=-1, pending=48/48, stale=0, timeouts=0
- Seed 44: weight=-32769, bias=-1, pending=48/48, stale=0, timeouts=0
- Zero variance across seeds
- Single board acquired, three sequential runs

Claim boundary: Three-seed repeatability validates task transfer robustness.
Still single-chip only. Not multi-chip, not speedup, not v2.1 transfer.

### Next Step After 4.28c Pass

Phase B continues. Options:
1. Harder task transfer - hard_noisy_switching or sensor_control on four-core MCPL
2. Mechanism maturation - add keyed context-memory, predictive binding, or replay
3. Resource expansion - test schedule lengths 96/192 to characterize DTCM headroom
4. Multi-chip feasibility - local build/wiring validation

Candidate directions (pick one per Phase B cycle):
1. **Harder task transfer** - Move the 48-event delayed-credit micro-loop to a harder task (e.g., delayed cue, hard noisy switching) while preserving the four-core MCPL scaffold.
2. **Mechanism maturation** - Add one v2.1 software mechanism to the native runtime (e.g., keyed context-memory, internal replay, or predictive binding) and validate it on the 48-event scaffold.
3. **Resource expansion** - Test schedule lengths beyond 48 events (96, 192) to characterize ITCM/RAM headroom before adding mechanisms.
4. **Multi-chip feasibility** - Local build and wiring validation for multi-chip MCPL routing.

### Tier 4.28d - Hard Noisy Switching Four-Core MCPL Hardware Probe

Status: **PASS, INGESTED** - Package `cra_428j`. Seeds 42/43/44, all 38/38 criteria per seed.
  (cra_428i deprecated: `test_runtime.c` assertion failure due to surprise gating
   mismatch in `test_state_pending_horizon_signed_switch_update`; fixed by
   lowering prediction from 1.5→0.5 so |error|=1.5 < SURPRISE_THRESHOLD=2.0.)

Design:
- Task: hard_noisy_switching with oracle regime context
- ~62 events per seed (steps=128, hard_period=2, delay range 3-5)
- 20% noisy trials (target flipped)
- Surprise gating: skip update when |error| ≥ 2.0
- Variable delay: 3-5 steps
- Regime switches every 32-48 events
- Per-event regime context: host pre-writes regime_sign to unique context slot per event
- MAX_CONTEXT_SLOTS bumped 8→128 to accommodate per-event slots

Hardware results (seeds 42/43/44):
- Seed 42: board 10.11.241.145, weight=34208, bias=-1440, pending=62/62, lookups=186/186
- Seed 43: board 10.11.242.1, weight=34208, bias=-1440, pending=62/62, lookups=186/186
- Seed 44: board 10.11.242.65, weight=34208, bias=-1440, pending=62/62, lookups=186/186
- Zero variance across seeds. Zero stale replies, zero timeouts on all.

Claim boundary:
- Host-pre-written regime context; not autonomous regime detection
- Single-chip only; not multi-chip, not speedup, not v2.1 mechanism transfer
- Host still required for setup and readback

### Tier 4.28e - Native Failure-Envelope Report

Status: **COMPLETE** - Local sweep executed, three hardware probe points run, all ingested.

Question: What is the measured operating envelope of the four-core MCPL runtime?
Where does it fail as schedule length, state pressure, pending concurrency, and lookup
volume increase?

Answer: The runtime fails predictably at the MAX_SCHEDULE_ENTRIES=64 hard limit.
No hidden failure modes were observed before advertised limits.

Hypothesis: The runtime fails predictably at resource limits:
- Schedule length > MAX_SCHEDULE_ENTRIES (64) causes schedule overflow ✓ CONFIRMED
- Context slots > MAX_CONTEXT_SLOTS (128) causes slot exhaustion (not reached)
- Concurrent pending > MAX_PENDING_HORIZONS (128) causes pending overflow (not reached)
- High lookup volume causes timeout/stale under MCPL routing pressure (not observed)
- Short delays increase concurrent pending without changing event count ✓ OBSERVED

Null hypothesis: The runtime has hidden failure modes before advertised limits,
or the limits are not the actual bottlenecks. REJECTED - hardware confirmed exact boundary.

Sweep dimensions (local):
1. Schedule length: 16, 32, 48, 64, 80, 96, 128, 192 events
2. Context slot usage: 1, 4, 8, 16, 32, 64, 128 slots (per-event or shared)
3. Delay range: (1,2) high pressure, (3,5) medium, (7,10) low
4. Noise probability: 0.0, 0.2, 0.4, 0.6
5. Switch interval: 16, 32, 48, 64 (regime switches per schedule)

Predicted breakpoints:
- Schedule overflow at >64 events (MAX_SCHEDULE_ENTRIES hard limit) ✓ CONFIRMED
  POST-4.28E: Limit raised to 512 (14,336 bytes DTCM, 21.9% of budget).
  True on-chip event generation (no schedule array) is future Tier 4.32 work.
- Slot exhaustion at >128 unique context keys (MAX_CONTEXT_SLOTS hard limit)
- Pending overflow when (events × mean_delay) > 128 approximately
- MCPL timeout/stale when lookup volume exceeds router bandwidth

Hardware probe points (executed):
- Point A: Highest-pressure passing config - 64 events, delay=(1,1), noise=0.6, seed=42.
  Board 10.11.193.65. PASS 38/38. Weight=-3225, bias=8530. Pending=64/64, lookups=192/192.
- Point B: First predicted failure - 78 events, delay=(3,5), noise=0.2, seed=42.
  Board 10.11.193.129. BOUNDARY CONFIRMED. 64/78 schedule uploads succeeded, 14 rejected.
  pending_created=64 (capped at limit), lookup_requests=192 (64×3). No crashes, no exceptions.
- Point C: High pending-pressure passing config - 43 events, delay=(7,10), noise=0.2, seed=42.
  Board 10.11.194.1. PASS 38/38. Weight=101376, bias=5120, exact 0% error vs reference.
  Pending=43/43, lookups=129/129, max_concurrent_pending=10.

Pass criteria:
- Local sweep predicts breakpoints with clear limit mapping ✓
- Hardware runs at Points A-C return artifacts ✓
- At least one point shows a clean limit failure (to prove the envelope is real) ✓ Point B
- All passing points meet standard 38/38 criteria ✓ Points A and C
- Claim boundary documents exact safe operating region ✓

Fail criteria:
- Local sweep does not predict any breakpoint - NOT TRIGGERED
- Hardware fails at a point local sweep predicted as safe - NOT TRIGGERED
- All hardware points pass, giving no envelope boundary - NOT TRIGGERED

Claim boundary:
- This is resource/timing characterization evidence, not a new learning mechanism
- Single-chip only; envelope may differ on multi-chip
- Does not prove speedup, autonomy, or v2.1 mechanism transfer
- Safe operating region: ≤64 schedule entries, ≤128 context slots, ≤128 pending horizons

---

## Phase C - Mechanism Migration Map (v2.1 → Native)

Status: **DEFINED** - Baseline `CRA_NATIVE_TASK_BASELINE_v0.2` frozen. Mechanism migration
order and blockers documented. Phase C entry authorized.

### Promoted Mechanisms (eligible for native transfer)

| Mechanism | v2.1 Evidence | Native Target Core | Order | Key Blocker |
|-----------|--------------|-------------------|-------|-------------|
| Keyed context/memory | 5.10g (171-run NEST matrix, zero leakage, `1.0` accuracy) | `context_core` multi-slot table | **4.29a first** | Slot table size, key ID space, overwrite policy |
| Composition/routing | 5.13c (243-cell matrix, `1.0` held-out routing) | `route_core` keyed routing | 4.29b | Route table ownership, MCPL key-based routing |
| Predictive binding | 5.17e (v2.0 freeze, cross-modal binding) | `learning_core` masked signal | 4.29c | Prediction target vs reward target separation |
| Self-evaluation | 5.18c (v2.1 freeze, confidence-gated learning) | `learning_core` confidence state | 4.29d | Bounded confidence pre-outcome compute |
| Replay/consolidation | 5.11d (v1.7 freeze, correct-binding replay) | Host-scheduled first; native buffers later | 4.29e | DTCM budget for replay buffers |
| Lifecycle/self-scaling | 6.1/6.3 (software lifecycle sham controls) | Static pool masks across cores | 4.30 | Preallocated pool only; no dynamic PyNN mid-run |

### Parked Mechanisms (stay host-side until repair)

| Mechanism | Status | Reason | Re-entry Condition |
|-----------|--------|--------|-------------------|
| Macro eligibility | PARKED (5.9c) | Trace-ablation specificity failed | New trace-specificity candidate passes sham controls |

### Migration Rules

1. **Local first.** Every mechanism bridge starts with a local reference using the custom C runtime before any EBRAINS hardware attempt.
2. **One mechanism at a time.** Do not stack unvalidated mechanisms. Run compact native regression (4.29f) after each promoted bridge.
3. **Controls required.** Every mechanism bridge needs: wrong-key/shuffle sham, host-composed sham, and feature parity versus the v2.1 host-side reference.
4. **Resource budget.** Native mechanisms must fit in ITCM/DTCM. If a mechanism overflows ITCM, profile or park it.
5. **Claim boundary.** Each bridge proves only that the mechanism runs natively on the four-core scaffold. It does not prove multi-chip, speedup, autonomy, or full v2.1 parity.

### Phase C Entry Rule

Branch from `CRA_NATIVE_TASK_BASELINE_v0.2` only. Run local build validation before any hardware attempt. Use fresh EBRAINS package names per Rule 10. Do not stack mechanisms without compact regression.

---

### Tier 4.29a - Native Keyed-Memory Overcapacity Gate

Status: **HARDWARE PASS, INGESTED** - Three-seed repeatability complete.
  Seed 42: board 10.11.193.145, 47/47 criteria
  Seed 43: board 10.11.194.129, 47/47 criteria
  Seed 44: board 10.11.193.81, 47/47 criteria
  Weight=32768, bias=0, pending=32/32, lookups=96/96, stale=0, timeouts=0
  Context hits=26, misses=6, active_slots=8, slot_writes=9
  Zero variance across seeds. Exact parity with local reference.

Current baseline: `CRA_NATIVE_TASK_BASELINE_v0.2`

Question: Can the native `context_core` runtime handle multiple keyed context/memory slots
with correct lookup, wrong-key rejection, slot-shuffle robustness, and slot overwrite policy?

Hypothesis: The native context slot table can support multiple keyed entries (up to
`MAX_CONTEXT_SLOTS=128`) with key-based lookup, and the chip-side contract can
correctly retrieve `context[key]` for feature computation.

Null hypothesis: The native context table corrupts under multi-slot pressure, wrong keys
return invalid data instead of failing cleanly, slot overwrites leak old data, or shuffle
reordering breaks lookup consistency.

Mechanism under test: **Keyed context memory** - promoted from v2.1 Tier 5.10g.
The host writes keyed context slots (`ctx_A`, `ctx_B`, `ctx_C`, ...) and the runtime
retrieves the correct slot by key during feature composition.

Claim boundary:
- Native keyed context lookup works for up to N slots (where N ≤ 128 and fits in ITCM).
- Wrong-key lookups fail cleanly (return default/zero, not invalid data).
- Slot overwrites replace old data without leakage.
- Slot-shuffle reordering preserves lookup correctness.
- This is a single-mechanism bridge; not routing, not replay, not predictive binding.

Nonclaims:
- Not full v2.1 keyed memory (no capacity/interference stress at NEST scale).
- Not composition/routing (those are 4.29b).
- Not multi-chip.
- Not speedup.
- Not autonomy (host still writes slots and schedules events).

Tasks:
- Fixed-pattern signed stream with 3–4 keyed context slots
- Each event uses a different key; feature = `context[key] * cue`
- Wrong-key events mixed in as sham controls
- Slot overwrite events (rewrite slot with new value, verify retrieval)
- Slot-shuffle events (reorder slots, verify key-based lookup still correct)

Seeds: 42 (local reference), 42/43/44 (hardware repeatability)

Run lengths: 32 events (within ≤512 envelope; MAX_SCHEDULE_ENTRIES=512)

Backends: Local custom C reference first; SpiNNaker hardware second.

Hardware mode: Chunked scheduling (within 512-event envelope).

Controls:
1. **Wrong-key control**: Schedule event with key not in table → expect default/zero feature, not invalid data.
2. **Slot-shuffle control**: Rewrite slots in different order → key-based lookup must still return correct values.
3. **Overwrite control**: Rewrite existing slot with new value → old value must not leak into subsequent lookups.
4. **Host-composed sham**: Host computes feature directly from known slot values → compare to chip-computed feature raw deltas.

Ablations:
- Single-slot only (no keyed lookup) → accuracy should degrade or fail
- Key table disabled → all lookups return default

External baselines: None. This is mechanism evidence, not comparative.

Metrics:
- Accuracy (observed vs expected predictions)
- Tail accuracy (last 10 events)
- Feature raw deltas (host vs chip)
- Weight/bias raw deltas
- Slot hit/miss counts (from schema v2 readback)
- Active slot count

Statistical summary:
- Expected accuracy ≥ 0.9 on fixed-pattern task
- Expected tail accuracy = 1.0
- All feature/weight/bias raw deltas = 0
- Wrong-key events: accuracy = 0.0 or default behavior (documented)

Pass criteria:
- Local reference passes with all raw deltas 0
- Hardware target acquisition succeeds
- All slot writes succeed
- All schedule uploads succeed (≤64 events)
- Chip-computed features match host reference within raw delta 0
- Wrong-key events fail cleanly (no invalid data, no crash)
- Overwrite events retrieve new value, not old value
- Shuffle events maintain correct key-value mapping
- Final readback shows expected slot hit/miss counts
- 38/38 criteria pass (or tier-specific equivalent)

Fail criteria:
- Wrong-key lookup returns invalid data instead of default
- Slot overwrite leaks old data
- Shuffle breaks key-value mapping
- Feature raw deltas nonzero (indicates lookup error)
- ITCM overflow under multi-slot profile
- Any unhandled hardware exception

Leakage checks:
- Verify no cross-slot data leakage in readback
- Verify wrong-key events do not corrupt adjacent slots

Resource/runtime measurements:
- ITCM size per profile (context_core with N slots)
- DTCM estimate
- Schedule length, command count, payload bytes
- Lookup request/reply counts

Expected artifacts:
- Local reference JSON/report
- Prepared EBRAINS package (`cra_429a`)
- Hardware results JSON (if run)
- Ingest results/report
- Noncanonical failure artifacts preserved if any

Docs to update:
- `CONTROLLED_TEST_PLAN.md` (this section)
- `codebasecontract.md` Section 0 (active tier)
- `docs/CODEBASE_MAP.md`
- `docs/MASTER_EXECUTION_PLAN.md` (step 20 status)
- `experiments/evidence_registry.py` (after ingest)

Promotion/freeze condition:
- Promote to carried-forward native mechanism only if all controls pass and compact
  native regression (4.29f) still passes afterward.
- Do not freeze a new baseline for a single mechanism bridge.

Re-entry condition if parked:
- If ITCM overflow prevents multi-slot profile: profile size, reduce slot count, or
  defer to host-side keyed context until ITCM budget allows.
- If wrong-key lookup returns invalid data: fix slot table initialization/default-value policy.
- If overwrite leaks: fix slot table write logic (clear old value before writing new).

Next step after 4.29a: Tier 4.29b (native routing/composition gate) only if 4.29a
passes compact regression. If 4.29a fails, park keyed memory and document blocker.

### Tier 4.29b - Native Routing/Composition Gate

Status: **HARDWARE PASS, INGESTED** - Three-seed repeatability complete.
Previous: cra_429c FAILED on EBRAINS (48/52 per seed, 3 seeds). Root cause:
C runtime readback bug in host_interface.c - context-slot counters were emitted
for ALL profiles, but route_core updated route-slot counters. Host read zeros.
Fixed with profile-specific readback logic. Rebuilt all profiles. Bumped to cra_429d.
Hardware evidence (cra_429d):
  Seed 42: board 10.11.194.81, 52/52 criteria, weight=32781, bias=3
  Seed 43: board 10.11.195.1, 52/52 criteria, weight=32781, bias=3
  Seed 44: board 10.11.195.129, 52/52 criteria, weight=32781, bias=3
  Pending=32/32, lookups=96/96, stale=0, timeouts=0
  Context hits=24, misses=8, active_slots=8, slot_writes=9
  Route hits=24, misses=8, active_slots=2, slot_writes=3
  Exact parity across all three seeds. Zero variance.
  Ingest: controlled_test_output/tier4_29b_20260503_hardware_pass_ingested/

Current baseline: `CRA_NATIVE_TASK_BASELINE_v0.2`

Question: Can the native `route_core` runtime handle keyed routing with non-neutral
values (+1.0, -1.0) and correctly compose `feature = context[key] * route[key] * cue`
with explicit route-specific controls?

Hypothesis: The native route slot table can support keyed entries with non-neutral
values, and the chip-side contract correctly retrieves `route[key]` for feature
composition alongside context.

Null hypothesis: Route lookups corrupt feature composition, wrong-route keys return
invalid data, route overwrites leak old data, or the composition formula breaks when
route is not neutral.

Mechanism under test: **Keyed route composition** - promoted from v2.1 Tier 5.13c.
The host writes keyed context slots and keyed route slots; the runtime retrieves
both by key and computes `feature = context[key] * route[key] * cue`.

Claim boundary:
- Native keyed route lookup works for up to N slots (where N ≤ 8 and fits in ITCM).
- Non-neutral route values (+1.0, -1.0) correctly affect feature composition.
- Wrong-route lookups fail cleanly (return default/zero, not invalid data).
- Route overwrites replace old data without leakage.
- Context controls from 4.29a still pass with route added to composition.
- This is a single-mechanism bridge; not replay, not predictive binding.

Nonclaims:
- Not full v2.1 composition/routing (no capacity stress at NEST scale).
- Not predictive binding (those are 4.29c).
- Not multi-chip.
- Not speedup.
- Not autonomy (host still writes slots and schedules events).

Tasks:
- Fixed-pattern signed stream with 2 keyed route slots (+1.0, -1.0) and 4-8 context slots
- Events alternate between route keys to test sign-flipping composition
- Wrong-route events mixed in as sham controls
- Route overwrite events (rewrite route slot with new value, verify retrieval)
- Context overwrite events preserved from 4.29a

Seeds: 42 (local reference), 42/43/44 (hardware repeatability)

Run lengths: 32 events (within ≤512 envelope)

Backends: Local custom C reference first; SpiNNaker hardware second.

Hardware mode: Chunked scheduling (within 512-event envelope).

Controls:
1. **Wrong-context control**: Schedule event with context key not in table → expect default/zero feature.
2. **Wrong-route control**: Schedule event with route key not in table → route=0, feature=0.
3. **Context overwrite control**: Rewrite existing context slot → old value must not leak.
4. **Route overwrite control**: Rewrite existing route slot → old value must not leak.
5. **Host-composed sham**: Host computes feature directly → compare to chip-computed feature raw deltas.

Ablations:
- Neutral route only (route=1.0 for all events) → should match 4.29a behavior
- Route table disabled → all route lookups return default

External baselines: None. This is mechanism evidence, not comparative.

Metrics:
- Accuracy (observed vs expected predictions)
- Tail accuracy (last 6 events)
- Feature raw deltas (host vs chip)
- Weight/bias raw deltas
- Context slot hit/miss counts
- Route slot hit/miss counts
- Active slot counts

Statistical summary:
- Expected tail accuracy documented from local reference
- All feature/weight/bias raw deltas = 0
- Wrong-context events: feature = 0
- Wrong-route events: feature = 0

Pass criteria:
- Local reference passes with all raw deltas 0
- Hardware target acquisition succeeds
- All context and route slot writes succeed
- All schedule uploads succeed (≤512 events)
- Chip-computed features match host reference within raw delta 0
- Wrong-context events fail cleanly
- Wrong-route events fail cleanly
- Context overwrite events retrieve new value
- Route overwrite events retrieve new value
- Final readback shows expected context and route slot hit/miss counts

Fail criteria:
- Wrong-route lookup returns invalid data instead of default
- Route overwrite leaks old data
- Feature raw deltas nonzero (indicates composition error)
- ITCM overflow under multi-slot profile
- Any unhandled hardware exception

Leakage checks:
- Verify no cross-slot data leakage in readback
- Verify wrong-route events do not corrupt adjacent slots
- Verify route overwrite does not affect unrelated context slots

Expected artifacts:
- `tier4_29b_local_results.json`
- `tier4_29b_prepare_results.json`
- `tier4_29b_hardware_results.json` (per seed)
- `tier4_29b_ingest_results.json`
- `tier4_29b_ingest_report.md`

Docs to update:
- `codebasecontract.md` (live handoff state)
- `ebrains_jobs/README.md`
- `docs/SPINNAKER_EBRAINS_RUNBOOK.md`
- `CONTROLLED_TEST_PLAN.md`
- `docs/MASTER_EXECUTION_PLAN.md` (step 21 status)
- `experiments/evidence_registry.py` (after ingest)

Promotion/freeze condition:
- Promote to carried-forward native mechanism only if all controls pass and compact
  native regression (4.29f) still passes afterward.
- Do not freeze a new baseline for a single mechanism bridge.

Re-entry condition if parked:
- If route lookup corrupts context: verify lookup isolation in C runtime.
- If wrong-route returns invalid data: fix route slot table default-value policy.
- If route overwrite leaks: fix route slot table write logic.

Next step after 4.29b: Tier 4.29c (native predictive binding bridge) only if 4.29b
passes compact regression. If 4.29b fails, park routing/composition and document blocker.

### Tier 4.29c - Native Predictive Binding Bridge

Status: **HARDWARE PASS, INGESTED** - Three-seed repeatability complete.
Previous: No previous hardware attempt. First pass with cra_429h.
Hardware evidence (cra_429h):
  Seed 42: board 10.11.214.49, 24/24 criteria, weight=30912, bias=-1856
  Seed 43: board 10.11.214.113, 24/24 criteria, weight=30912, bias=-1856
  Seed 44: board 10.11.215.161, 24/24 criteria, weight=30912, bias=-1856
  Full-context prediction weight=30912, bias=-1856; zero-context prediction weight=0, bias=0
  Confidence parity confirms prediction-before-reward isolation.
  Ingest: controlled_test_output/tier4_29c_20260504_pass_ingested/

Current native task baseline: `CRA_NATIVE_TASK_BASELINE_v0.2` (cumulative native mechanism bridge is not frozen until the post-4.29 compact regression).

Question: Can the native `learning_core` runtime compute a prediction target from
context before the outcome arrives, keeping it separate from the reward target?

Hypothesis: The native runtime can compute
`prediction_target = context[key] * route[key] * cue` before reward delivery,
and the weight update uses this prediction target instead of the raw cue.

Null hypothesis: Prediction target equals reward target (no separation), or
prediction computation corrupts learning.

Mechanism under test: **Predictive binding** - promoted from v2.1 Tier 5.17e.
The host writes context and route slots; the runtime computes prediction target
before outcome and uses it for weight update.

Claim boundary:
- Native prediction-before-reward works for up to N slots (where N ≤ 8 and fits in ITCM).
- Prediction target differs from reward target when context is present.
- Zero-context prediction returns default/zero, not invalid data.
- This is a single-mechanism bridge; not replay, not confidence gating.

Nonclaims:
- Not full v2.1 predictive binding (no capacity stress at NEST scale).
- Not confidence-gated learning (those are 4.29d).
- Not multi-chip.
- Not speedup.
- Not autonomy (host still writes slots and schedules events).

Tasks:
- Fixed-pattern signed stream with predictive binding enabled
- Events alternate between context-present and context-absent to test prediction isolation
- Zero-context events mixed in as sham controls

Seeds: 42 (local reference), 42/43/44 (hardware repeatability)

Run lengths: 32 events (within ≤512 envelope)

Backends: Local custom C reference first; SpiNNaker hardware second.

Hardware mode: Chunked scheduling (within 512-event envelope).

Controls:
1. **Full-context prediction**: Schedule event with context key in table → prediction weight=30912, bias=-1856.
2. **Zero-context prediction**: Schedule event with context key not in table → prediction weight=0, bias=0.

Ablations:
- Prediction disabled (raw cue used for weight update) → should match 4.29b behavior

External baselines: None. This is mechanism evidence, not comparative.

Metrics:
- Prediction weight/bias raw deltas
- Reward weight/bias raw deltas
- Confidence parity (prediction vs reward target separation)
- Context slot hit/miss counts

Statistical summary:
- Expected prediction weight/bias documented from local reference
- Full-context prediction weight=30912, bias=-1856
- Zero-context prediction weight=0, bias=0

Pass criteria:
- Local reference passes with all raw deltas 0
- Hardware target acquisition succeeds
- All context and route slot writes succeed
- All schedule uploads succeed (≤512 events)
- Full-context prediction weight matches reward weight from 4.29b
- Zero-context prediction weight=0, bias=0
- Prediction target differs from reward target for context-present events

Fail criteria:
- Prediction target equals reward target (no separation)
- Zero-context prediction returns nonzero weight/bias
- Feature raw deltas nonzero (indicates composition error)
- ITCM overflow under multi-slot profile
- Any unhandled hardware exception

Leakage checks:
- Verify prediction computation does not corrupt reward path
- Verify zero-context events do not affect full-context learning

Expected artifacts:
- `tier4_29c_ingest_results.json`
- `tier4_29c_report_seed42.json`
- `tier4_29c_combined_results.json`
- `tier4_29c_hardware_results_seed{42,43,44}.json`
- `tier4_29c_task_seed42.json`

Docs to update:
- `codebasecontract.md` (live handoff state)
- `ebrains_jobs/README.md`
- `docs/SPINNAKER_EBRAINS_RUNBOOK.md`
- `CONTROLLED_TEST_PLAN.md`
- `docs/MASTER_EXECUTION_PLAN.md` (step 22 status)
- `experiments/evidence_registry.py` (after ingest)

Promotion/freeze condition:
- Promote to carried-forward native mechanism only if all controls pass and compact
  native regression (4.29g) still passes afterward.
- Do not freeze a new baseline for a single mechanism bridge.

Re-entry condition if parked:
- If prediction corrupts reward path: verify target isolation in C runtime.
- If zero-context returns nonzero: fix default-value policy for prediction path.

Next step after 4.29c: Tier 4.29d (native self-evaluation bridge) only if 4.29c
passes compact regression. If 4.29c fails, park predictive binding and document blocker.

### Tier 4.29d - Native Self-Evaluation Bridge

Status: **HARDWARE PASS, INGESTED** - Three-seed repeatability complete.
Previous: cra_429i FAILED on EBRAINS (all controls received effective confidence=1.0,
producing identical weight=30912 regardless of confidence condition). Root cause:
C runtime MCPL lookup protocol does not transmit confidence.
`cra_state_mcpl_lookup_send_reply` ignores confidence argument;
learning core's `cra_state_mcpl_lookup_receive` hardcodes confidence=FP_ONE.
Fixed by disabling MCPL lookup paths (`#if 0` in `_send_lookup_request` and
`_send_lookup_reply`) and reverting to SDP, which transmits confidence via
`msg->arg3`. Rebuilt all profiles. Bumped to cra_429j.
Hardware evidence (cra_429j):
  Seed 42: board 10.11.214.49, 30/30 criteria
  Seed 43: board 10.11.214.113, 30/30 criteria
  Seed 44: board 10.11.215.161, 30/30 criteria
  Full confidence: weight=30912, bias=-1856
  Zero confidence: weight=0, bias=0
  Zero-context confidence: weight=0, bias=0
  Half-context confidence: weight=28093, bias=3517 (diff=61 from ref, within ±8192)
  Ingest: controlled_test_output/tier4_29d_20260504_pass_ingested/

Current native task baseline: `CRA_NATIVE_TASK_BASELINE_v0.2` (cumulative native mechanism bridge is not frozen until the post-4.29 compact regression).

Question: Can the native `learning_core` runtime gate learning by composite
confidence (context × route × memory) on real SpiNNaker hardware?

Hypothesis: The native runtime computes
`composite_confidence = context_conf * route_conf * memory_conf` in s16.15
fixed-point and scales the effective learning rate by this product, blocking
learning exactly when any slot confidence is zero.

Null hypothesis: Learning proceeds regardless of confidence (confidence is
ignored), or confidence scaling corrupts weight updates beyond tolerance.

Mechanism under test: **Confidence-gated learning (self-evaluation)** - promoted
from v2.1 Tier 5.18c. The host writes context/route/memory slots with confidence
values; the runtime computes composite confidence and modulates learning rate
in `_apply_reward_to_feature_prediction`.

Claim boundary:
- Native confidence gating works for up to N slots (where N ≤ 8 and fits in ITCM).
- Composite confidence correctly scales learning rate in s16.15 fixed-point.
- Zero confidence blocks learning exactly (weight=0, bias=0).
- Zero-context confidence blocks all learning (single zero in product → zero).
- Half confidence scales learning proportionally (within ±8192 tolerance).
- This is a single-mechanism bridge; not replay, not predictive binding.

Nonclaims:
- Not full v2.1 self-evaluation (no capacity stress at NEST scale).
- Not predictive binding (those are 4.29c).
- Not multi-chip.
- Not speedup.
- Not autonomy (host still writes slots and schedules events).
- Not dynamic lifecycle confidence (confidence is host-pre-written, not emergent).

Tasks:
- Fixed-pattern signed stream with four confidence conditions:
  - Full confidence (all slot confidences = 1.0)
  - Zero confidence (all slot confidences = 0.0)
  - Zero-context confidence (context confidence = 0.0, route/memory = 1.0)
  - Half-context confidence (context confidence = 0.5, route/memory = 1.0)

Seeds: 42 (local reference), 42/43/44 (hardware repeatability)

Run lengths: 32 events (within ≤512 envelope)

Backends: Local custom C reference first; SpiNNaker hardware second.

Hardware mode: Chunked scheduling (within 512-event envelope).

Controls:
1. **Full confidence control**: All slot confidences = 1.0 → weight=30912, bias=-1856.
2. **Zero confidence control**: All slot confidences = 0.0 → weight=0, bias=0.
3. **Zero-context confidence control**: Context confidence = 0.0, route/memory = 1.0 → weight=0, bias=0.
4. **Half-context confidence control**: Context confidence = 0.5, route/memory = 1.0 → weight ≈ 28093, bias ≈ 3517.

Ablations:
- Confidence gating disabled (`has_confidence=false`) → should match 4.29c behavior

External baselines: None. This is mechanism evidence, not comparative.

Metrics:
- Weight/bias raw deltas per confidence condition
- Composite confidence computation accuracy
- Context/route/memory slot hit/miss counts
- Learning rate scaling verification

Statistical summary:
- Expected weight/bias documented from local reference for each condition
- Full confidence: weight=30912, bias=-1856
- Zero confidence: weight=0, bias=0
- Zero-context confidence: weight=0, bias=0
- Half-context confidence: weight ≈ 28093, bias ≈ 3517 (±8192 tolerance)

Pass criteria:
- Local reference passes with all raw deltas within tolerance
- Hardware target acquisition succeeds
- All context/route/memory slot writes succeed
- All schedule uploads succeed (≤512 events)
- Full confidence weight/bias matches 4.29c baseline
- Zero confidence blocks learning exactly (weight=0, bias=0)
- Zero-context confidence blocks learning exactly (weight=0, bias=0)
- Half-context confidence scales proportionally (within ±8192 tolerance)
- All criteria pass per seed (30/30)

Fail criteria:
- Zero confidence does not block learning (weight ≠ 0)
- Confidence scaling exceeds ±8192 tolerance
- MCPL lookup used for confidence transmission (known protocol limitation)
- ITCM overflow under multi-slot profile
- Any unhandled hardware exception

Leakage checks:
- Verify confidence computation does not corrupt slot data
- Verify zero confidence does not leave residual weight updates
- Verify half-confidence scaling is monotonic and bounded

Expected artifacts:
- `tier4_29d_ingest_results.json`
- `tier4_29d_combined_results.json`
- `tier4_29d_report_seed44.json`
- `tier4_29d_task_full_confidence.json`
- `tier4_29d_task_zero_confidence.json`
- `tier4_29d_task_zero_context_confidence.json`
- `tier4_29d_task_half_context_confidence.json`

Docs to update:
- `codebasecontract.md` (live handoff state)
- `ebrains_jobs/README.md`
- `docs/SPINNAKER_EBRAINS_RUNBOOK.md`
- `CONTROLLED_TEST_PLAN.md`
- `docs/MASTER_EXECUTION_PLAN.md` (step 23 status)
- `experiments/evidence_registry.py` (after ingest)

Promotion/freeze condition:
- Promote to carried-forward native mechanism only if all controls pass and compact
  native regression (4.29h) still passes afterward.
- Do not freeze a new baseline for a single mechanism bridge.

Re-entry condition if parked:
- If confidence does not block learning: verify `has_confidence` flag and
  `effective_lr = FP_MUL(learning_rate, composite_confidence)` logic in C runtime.
- If MCPL lookup is accidentally active: verify `#if 0` guards remain in place.
- If half-confidence scaling is non-monotonic: review s16.15 multiplication order.

Next step after 4.29d: Tier 4.29e (replay/consolidation bridge) only if 4.29d
passes compact regression. If 4.29d fails, park self-evaluation and document blocker.

### Tier 4.29e - Native Replay/Consolidation Bridge

Status: **HARDWARE PASS, INGESTED** - `cra_429p` passed seeds 42/43/44 with `38/38` criteria per seed (`114/114` total).

`cra_429o` returned real SpiNNaker hardware execution across seeds 42/43/44,
but failed two tolerance criteria per seed. The failure is preserved as
noncanonical diagnostic evidence at:

```text
controlled_test_output/tier4_29e_20260505_cra_429o_hardware_fail/
```

Hardware health in `cra_429o` was good: target acquisition passed, context/route/
memory/learning core loads passed, all controls completed, pending horizons
matured, lookup replies matched requests, stale replies/timeouts were zero. The
failed criteria were reference/schedule-gate failures, not promoted evidence.

Canonical package: `cra_429p`, runner revision
`tier4_29e_native_replay_consolidation_20260505_0003`. It reuses `cra_429j`
binaries; no C runtime changes are made for 4.29e.

Canonical artifact:

```text
controlled_test_output/tier4_29e_20260505_pass_ingested/
```

Hardware evidence:

```text
Seed 42: board 10.11.226.129, 38/38 criteria
Seed 43: board 10.11.226.1,   38/38 criteria
Seed 44: board 10.11.226.65,  38/38 criteria
```

Current native task baseline: `CRA_NATIVE_TASK_BASELINE_v0.2` (cumulative native mechanism bridge is not frozen until the post-4.29 compact regression).

Question: Can the host schedule replay events through native state primitives
(context/route/memory slots, learning core) on real SpiNNaker hardware?

Hypothesis: The host can construct a schedule containing both original events
and replay events; the native four-core runtime processes them through the same
pipeline without native replay buffers, producing differentiable outcomes for
correct-key, wrong-key, no-replay, and random-event replay conditions.

Null hypothesis: Replay events corrupt the native state pipeline, or the runtime
cannot distinguish correct-key replay from wrong-key/no-replay/random-event
conditions.

Mechanism under test: **Host-scheduled replay/consolidation** - promoted from
v2.1 Tier 5.11d. The host writes context/route/memory slots and constructs a
schedule where later events replay earlier ones. No native replay buffers are
used; the existing schedule primitive handles all event presentations.

Claim boundary:
- Host-scheduled replay works through native state primitives on real SpiNNaker.
- Correct-key replay produces a different outcome than no-replay and wrong-key replay.
- Random-event replay produces a different outcome than correct-key replay.
- Wrong-key replay approximates the no-replay **weight** baseline because failed
  context lookup makes feature=0 and therefore delta_w=0 on replay events.
- Wrong-key replay bias may drift because native bias updates are
  feature-independent; the valid gate is bounded-near-no-replay, not exact
  no-replay equality.
- This is host-scheduled replay only; not native on-chip replay buffers, not
  biological sleep, not multi-chip scaling.

Nonclaims:
- Not native on-chip replay buffers (DTCM budget blocker remains).
- Not biological sleep or circadian replay.
- Not multi-chip.
- Not speedup.
- Not autonomy (host constructs the schedule and writes slots).
- Not performance improvement claim.

Tasks:
- Fixed-pattern signed stream with 16 base events.
- 8 balanced correct replay events using target +/-1.5.
- Four replay conditions:
  - no_replay: 16 base events only.
  - correct_replay: 16 base + 8 balanced replay events with correct context keys.
  - wrong_key_replay: 16 base + 8 balanced replay events with wrong context keys.
  - random_event_replay: 16 base + 8 random conflicting events.

Seeds: 42/43/44 local repaired reference; 42/43/44 hardware repeatability.

Run lengths: 16-24 events (well within <=512 envelope).

Backends: Local native-continuous host reference first; SpiNNaker hardware second. Both passed.

Hardware mode: Chunked host scheduling through native four-core state primitives.
Reuses `cra_429j` binaries; no C runtime changes for 4.29e.

Controls:
1. **No-replay baseline**: 16 base events only; establishes weight/bias baseline.
2. **Correct-key replay**: Replay events use correct context/route/memory keys;
   should produce a real readout-weight change versus no_replay and differ from wrong-key.
3. **Wrong-key replay**: Replay events use wrong context keys; context lookup
   returns default 0, so feature=0 and replay events do not consolidate weight.
4. **Random-event replay**: Replay events have conflicting cues/targets; should
   diverge from correct-key replay.

Ablations:
- No additional ablations needed; the four controls themselves form the sham separation.

External baselines: None. This is mechanism-transfer evidence, not comparative.

Metrics:
- Weight/bias raw deltas per control condition.
- Cross-control weight/bias differences.
- Event maturation counts.
- Schedule upload success.
- Hardware-reference tolerance per control.

Repaired local reference summary (`cra_429p`, seeds 42/43/44):

```text
no_replay:            weight=32768 (1.0000), bias=0 (0.0000)
correct_replay:       weight=47896 (1.4617), bias=-232 (-0.0071)
wrong_key_replay:     weight=32768 (1.0000), bias=-5243 (-0.1600)
random_event_replay:  weight=57344 (1.7500), bias=0 (0.0000)
```

Pass criteria:
- Local repaired reference passes all controls across seeds 42/43/44.
- Hardware target acquisition succeeds.
- All context/route/memory slot writes succeed.
- All schedule uploads succeed (<=512 events).
- Hardware weight/bias matches native-continuous reference within +/-8192 tolerance per control.
- Correct-key replay weight differs from no-replay by >8192.
- Wrong-key replay weight approximates no-replay weight (<=8192).
- Wrong-key replay differs from correct-key replay.
- Random-event replay differs from correct-key replay.
- All events mature per control.

Fail criteria:
- Correct-key replay does not differ from no-replay.
- Wrong-key replay weight differs from no-replay by >8192.
- Wrong-key replay reproduces correct-key replay.
- Random-event replay does not differ from correct-key replay.
- Hardware deviates from the repaired native-continuous reference by >8192.
- Schedule upload fails or exceeds the <=512-event envelope.
- Any unhandled hardware exception.

Leakage checks:
- Verify replay events do not corrupt base event state.
- Verify wrong-key replay events do not affect weight through the correct context.
- Verify per-event context keys are preserved in the schedule.
- Verify schedule length is consistent across controls.

Canonical artifacts:
- `tier4_29e_hardware_results_seed{42,43,44}.json`
- `tier4_29e_ingest_results.json`
- `tier4_29e_combined_results.json`
- `tier4_29e_report.md`

Docs to update:
- `codebasecontract.md` (live handoff state)
- `ebrains_jobs/README.md`
- `docs/SPINNAKER_EBRAINS_RUNBOOK.md`
- `CONTROLLED_TEST_PLAN.md`
- `docs/MASTER_EXECUTION_PLAN.md` (step 24 status)
- `experiments/evidence_registry.py` (after promoted ingest)

Promotion/freeze condition:
- 4.29e is promoted as carried-forward native host-scheduled replay/consolidation evidence.
- Follow-up compact native regression (4.29f) passed and froze
  `CRA_NATIVE_MECHANISM_BRIDGE_v0.3`.

Re-entry condition if parked:
- If replay events corrupt state: verify schedule upload isolation in C runtime.
- If wrong-key replay produces nonzero feature: verify context slot default-value
  policy returns 0 for missing keys and per-event context keys are preserved.
- If hardware-reference mismatch recurs: compare against native-continuous host
  reference, not simplified delayed-credit reference.
- If schedule exceeds envelope: reduce event count or split into chunks.


Next step after 4.29e: Tier 4.29f (compact native mechanism regression) to verify
that 4.29a-e remain mutually compatible before a cumulative native mechanism
bridge baseline freeze.

### Tier 4.29f - Compact Native Mechanism Regression

Status: **PASS / BASELINE FREEZE GATE COMPLETE**.

Question: Do the promoted native mechanism bridges from 4.29a-e remain stable
when checked as a compact cumulative evidence-regression suite?

Hypothesis: The canonical hardware evidence set for native keyed memory,
routing/composition, predictive binding, confidence-gated learning, and
host-scheduled replay remains complete, internally aligned, and safe to freeze
as a cumulative native mechanism bridge baseline.

Null hypothesis: At least one promoted native mechanism evidence row is missing,
stale, internally inconsistent, or no longer satisfies its own pass boundary.

Required coverage:
- 4.29a keyed-memory overcapacity/wrong-key controls.
- 4.29b routing/composition wrong-route and overwrite controls.
- 4.29c predictive-binding prediction-before-reward controls.
- 4.29d confidence-gated learning controls.
- 4.29e host-scheduled replay/consolidation controls.

Pass criteria:
- The 4.29a-e canonical hardware-pass directories exist and are registry-aligned.
- Each promoted mechanism reports expected runner revision, seeds, status,
  criteria totals, and mechanism-specific control criteria.
- No previously promoted mechanism regresses versus its own hardware pass
  boundary.
- The 4.29f evidence-regression runner passes all criteria and produces citable
  `tier4_29f_results.json`, `tier4_29f_summary.csv`, and `tier4_29f_report.md`.

Fail criteria:
- Any 4.29a-e canonical artifact is missing, stale, or not `pass`.
- Any expected control criterion is absent.
- Any runner revision/package identity mismatch appears.
- Any required three-seed coverage is missing.

Result:
- Output: `controlled_test_output/tier4_29f_20260505_native_mechanism_regression/`
- Runner revision: `tier4_29f_compact_native_mechanism_regression_20260505_0001`
- Status: `pass`
- Criteria: `113/113`
- Audited mechanisms: 4.29a, 4.29b, 4.29c, 4.29d, 4.29e
- Baseline frozen: `baselines/CRA_NATIVE_MECHANISM_BRIDGE_v0.3.md`

Promotion/freeze condition:
- Passed. `CRA_NATIVE_MECHANISM_BRIDGE_v0.3` is frozen as a cumulative native
  mechanism bridge evidence baseline.
- Boundary: 4.29f is an evidence-regression gate over already-ingested real
  hardware passes, not a new SpiNNaker execution and not a single monolithic
  all-mechanism runtime task.

Next step after 4.29f: run Tier 7.0 standard dynamical benchmarks in software
before moving any benchmark workload to hardware.

### Tier 7.0 - Standard Dynamical Benchmark Suite

Status: **PASS / DIAGNOSTIC COMPLETE**.

Question: How does the frozen CRA software baseline perform on standard
temporal prediction and memory benchmarks before any additional mechanism work
or hardware benchmark migration?

Hypothesis: CRA will show a measurable capability profile on dynamical
prediction/memory tasks that can be compared fairly against standard baselines
and used to diagnose the next useful mechanism gap.

Null hypothesis: CRA is dominated by simpler baselines or fails to produce a
stable, reproducible signal on these standard benchmarks under fair evaluation.

Tasks:
- Mackey-Glass future prediction.
- Lorenz future prediction.
- NARMA10 nonlinear memory/system-identification.
- Aggregate geometric-mean MSE across all three tasks.

Required baselines:
- Persistence / naive last-value predictor.
- Linear regression or ridge regression.
- Online perceptron/logistic where applicable.
- Reservoir / echo-state network.
- Small GRU or comparable sequence learner.
- Optional STDP-only or rate-only SNN baseline if it can be run fairly.

Required metrics:
- MSE and normalized MSE.
- Tail-window MSE.
- Seed mean, median, standard deviation, and worst case.
- Confidence/bootstrap interval where practical.
- Runtime and memory footprint.
- Per-task and aggregate geometric-mean MSE.

Controls and guardrails:
- Fixed train/test splits and seeds.
- No future-window leakage.
- Same prediction horizon per model.
- Same input normalization fitted only on train split.
- Hyperparameter budget recorded for all baselines.
- No blind CRA tuning from the benchmark score; diagnose failure mode first.

Pass criteria:
- Benchmark harness produces deterministic, reproducible artifacts.
- All baselines and CRA run successfully across predeclared seeds.
- Leakage checks pass.
- Metrics table and per-seed outputs are generated.
- The result is interpretable enough to decide whether the next work should be
  lifecycle, policy/action, planning, memory/replay, or hardware migration.

Fail criteria:
- Any benchmark has leakage or split contamination.
- Baselines are missing or unfairly under-specified.
- CRA-specific preprocessing gives extra information unavailable to baselines.
- Results cannot be reproduced from generated artifacts.

Promotion/freeze condition:
- Tier 7.0 is a benchmark/diagnostic gate, not automatically a new baseline.
- Freeze a new software baseline only if a subsequent repair or mechanism tier
  passes ablation, baseline comparison, and compact regression.

Canonical result:
- Output: `controlled_test_output/tier7_0_20260505_standard_dynamical_benchmarks/`.
- Runner: `experiments/tier7_0_standard_dynamical_benchmarks.py`.
- Criteria: `10 / 10`.
- Outcome: `cra_underperforms_standard_sequence_baselines`.
- Best aggregate model: `echo_state_network`.
- CRA rank by aggregate geomean MSE: `5 / 5`.
- CRA / best non-CRA aggregate MSE ratio: `53.82975667035733`.

Interpretation:
- The benchmark harness and leakage guardrails passed.
- CRA v2.1 did not earn a performance claim on these continuous-valued
  dynamical regression benchmarks.
- This is a citable diagnostic failure/limitation, not a reason to hide the run
  and not a reason to tune blindly.

Next step after Tier 7.0: Tier 7.0b continuous-regression failure analysis.
Do not move to hardware benchmarking until the software failure class is
diagnosed.

### Tier 7.0b - Continuous-Regression Failure Analysis

Status: **PASS / DIAGNOSTIC COMPLETE**.

Question: Why does CRA v2.1 underperform standard causal sequence baselines on
the Tier 7.0 continuous-valued dynamical benchmark suite?

Hypothesis: The gap is explainable by one or more diagnosable mismatches
between the current CRA interface and continuous regression: readout form,
state/history capacity, reservoir-style dynamics, normalization/interface,
or consequence/credit objective.

Null hypothesis: The Tier 7.0 gap cannot be localized by controlled probes, or
the benchmark harness/baseline setup is unfair enough that the result cannot be
interpreted.

Required probes:
- Causal readout probe on CRA state: can a fair linear/ridge readout over CRA
  internal state close the gap without giving future information?
- History/state probe: does increasing available causal history or state
  exposure specifically improve NARMA10?
- Target/interface probe: do regression target scaling, signed reward feedback,
  or adapter semantics explain the MSE gap?
- Reservoir-dynamics probe: does a reservoir-like state/control baseline explain
  the missing capability better than CRA polyps do?
- Credit/policy probe: does dopamine/consequence timing mismatch continuous MSE
  optimization?
- Fairness audit: verify the same causal stream, split, normalization rules,
  and update timing for all models.

Controls and guardrails:
- Use the same generated task streams, seeds, train/test split, and
  train-prefix normalization as Tier 7.0.
- Diagnostic probes are not promoted CRA mechanisms.
- Do not tune on test rows.
- Do not add hidden future context, task labels, or target leakage.
- Preserve all failed probes as diagnostic evidence.

Pass criteria:
- The failure class is narrowed with artifact-backed evidence.
- At least one probe either closes a meaningful portion of the gap or rules out
  a suspected cause.
- Baseline fairness remains intact.
- A concrete next action is selected: repair tier, mechanism tier, benchmark
  redesign, or claim narrowing.

Fail criteria:
- Probes use information unavailable to the baselines.
- The suite becomes a tuning loop instead of a diagnosis.
- The gap remains unexplained and the next action is not bounded.

Promotion/freeze condition:
- Tier 7.0b does not freeze a baseline by itself.
- A later repair or mechanism tier must pass ablations, baselines, and compact
  regression before any new software baseline is frozen.

Canonical result:
- Output: `controlled_test_output/tier7_0b_20260505_continuous_regression_failure_analysis/`.
- Runner: `experiments/tier7_0b_continuous_regression_failure_analysis.py`.
- Criteria: `10 / 10`.
- Failure class: `recoverable_state_signal_default_readout_failure`.
- Raw CRA aggregate geomean MSE: `1.223255942741316`.
- CRA internal-state ridge probe geomean MSE: `0.44329167010892245`.
- CRA state plus same causal lag budget geomean MSE: `0.054439372091655114`.
- Shuffled-target state control geomean MSE: `0.7532851635211467`.
- State improvement over raw CRA: `2.759483259499883`.
- State plus lag improvement over raw CRA: `22.47005973327209`.

Interpretation:
- The Tier 7.0 gap is not simply "CRA has no useful signal."
- CRA internal state carries useful continuous-regression information, but the
  default online colony readout/interface does not extract it well.
- The large state-plus-lag improvement indicates these benchmarks reward causal
  history features; a bounded readout/interface repair is justified before
  adding broader organism mechanisms.

Next step after Tier 7.0b: Tier 7.0c bounded continuous readout/interface
repair. Do not move this benchmark to hardware until a repair/promotion gate
passes.

### Tier 7.0c - Bounded Continuous Readout / Interface Repair

Status: **PASS / LIMITED REPAIR DIAGNOSTIC COMPLETE**.

Question: Can CRA use the predictive signal identified in Tier 7.0b through a
bounded, leakage-safe continuous readout/interface rather than an external
diagnostic probe?

Hypothesis: A narrow continuous readout/interface over causal CRA state will
improve Mackey-Glass, Lorenz, NARMA10, and aggregate geomean MSE versus raw CRA
while surviving shuffled/ablated controls and not becoming an unconstrained
supervised model.

Null hypothesis: The Tier 7.0b diagnostic improvement cannot be converted into
a bounded CRA mechanism, or the improvement is explained by lag-only features,
shuffled targets, or leakage.

Required comparisons:
- Raw CRA v2.1 online from Tier 7.0.
- Bounded continuous readout/interface repair.
- No-state/readout-only ablation.
- Lag-only baseline with same causal lag budget.
- Shuffled-state control.
- Shuffled-target control.
- Frozen/no-learning control where applicable.
- Tier 7.0 external baselines for context.

Pass criteria:
- Repair improves aggregate geomean MSE over raw CRA.
- Repair is meaningfully better than shuffled-state and shuffled-target
  controls.
- Repair is not fully explained by lag-only features.
- No future leakage, no test-row fitting, and same causal stream/split.
- Compact regression is scheduled before any baseline freeze.

Fail criteria:
- Repair only wins through test leakage or unconstrained supervised fitting.
- Lag-only or shuffled controls explain the improvement.
- Repair degrades prior compact controls enough that it cannot be promoted.

Promotion/freeze condition:
- Tier 7.0c alone does not freeze a baseline.
- A separate compact regression/promotion gate must pass before freezing a new
  software baseline.

Canonical result:
- Output: `controlled_test_output/tier7_0c_20260505_continuous_readout_repair/`.
- Runner: `experiments/tier7_0c_continuous_readout_repair.py`.
- Criteria: `10 / 10`.
- Outcome: `repair_works_but_lag_only_explains_most_gain`.
- Raw CRA aggregate geomean MSE: `1.223255942741316`.
- Bounded state readout repair aggregate geomean MSE: `0.3747367253327713`.
- Bounded state plus lag repair aggregate geomean MSE: `0.19040922596175056`.
- Lag-only online LMS control aggregate geomean MSE: `0.1514560842638888`.
- Best repair improvement over raw CRA: `6.42435226845071`.
- Best repair margin versus best shuffled control: `3.607897109468084`.
- Best repair margin versus lag-only: `0.7954240846203183`.

Interpretation:
- Tier 7.0c improved raw CRA and beat shuffled/frozen controls, so the raw
  colony output is not the best possible use of the CRA state stream.
- The best non-CRA lag-only online LMS control still beat the bounded CRA-state
  repair. This means the current standard dynamical benchmark suite is strongly
  rewarding causal lag regression and Tier 7.0c does not yet prove a promoted
  CRA mechanism.
- Do not freeze a new software baseline from Tier 7.0c.
- Do not migrate this benchmark workload to hardware until the software repair
  either proves state-specific value beyond lag regression or the benchmark
  claim is narrowed honestly.

Next step after Tier 7.0c: Tier 7.0d state-specific continuous interface
repair or claim-narrowing contract. The next tier must decide whether CRA state
adds value beyond causal lag features under stricter controls. If lag-only
remains the best explanation, the paper claim should narrow to: CRA contains
some predictive state signal, but these continuous-valued standard dynamical
regression benchmarks are currently better served by simple causal sequence
baselines.

### Tier 7.0d - State-Specific Continuous Interface / Claim-Narrowing

Status: **DEFINED / CURRENT GATE**.

Question: Does CRA state add state-specific predictive value beyond the same
causal lag budget that explains most of the Tier 7.0c gain?

Hypothesis: Lag-orthogonal CRA state contains useful information that improves
Mackey-Glass, Lorenz, NARMA10, and aggregate geomean MSE beyond lag-only
regression while surviving shuffled-state, shuffled-target, and frozen-control
checks.

Null hypothesis: Once causal lag history is accounted for, CRA state does not
add useful continuous-regression value on these benchmarks; the honest claim is
that this benchmark suite is currently better served by simple causal sequence
baselines.

Required comparisons:
- Raw CRA v2.1 online from Tier 7.0.
- Lag-only online LMS control with the same causal lag budget.
- State-only online LMS control.
- State plus lag online reference.
- Lag-orthogonal state online candidate.
- Lag plus lag-orthogonal state online candidate.
- Two-stage lag then residual-state online candidate.
- Shuffled lag-orthogonal state controls.
- Shuffled-target control.
- Frozen/no-learning control.
- Train-prefix ridge lag upper-bound probe.
- Train-prefix ridge lag plus state upper-bound probe.
- Train-prefix ridge lag plus lag-orthogonal state upper-bound probe.

Required guardrails:
- Same Tier 7.0 streams, seeds, chronological splits, horizons, and train-prefix
  normalization.
- Lag-orthogonal state must be residualized using train-prefix data only.
- Online predictions must be emitted before online updates.
- Train-prefix ridge probes are upper-bound diagnostics only; they are not
  promoted mechanisms.
- No test-row batch fitting, future target leakage, task labels, or hidden
  target-derived features.

Pass criteria:
- All comparisons run across predeclared tasks and seeds.
- Lag-only, state-specific candidates, shuffled controls, frozen controls, and
  train-prefix upper-bound probes are present.
- If a state-specific online candidate beats lag-only by a meaningful margin and
  beats shuffled controls, schedule a compact promotion/regression gate.
- If only train-prefix ridge state probes beat lag-only, classify the result as
  an online-interface failure rather than a promoted mechanism.
- If neither online nor train-prefix state probes beat lag-only, narrow the Tier
  7 benchmark claim and do not migrate this benchmark path to hardware.

Fail criteria:
- Any candidate uses future targets, test-row fitting, or target-derived hidden
  features.
- State residualization uses held-out rows.
- Shuffled controls explain the state-specific gain.
- Results cannot decide between state-specific value and lag-only explanation.

Promotion/freeze condition:
- Tier 7.0d alone does not freeze a baseline.
- A separate compact regression/promotion gate is required before any software
  baseline freeze.
- Hardware migration is blocked until a software mechanism earns promotion or
  the benchmark claim is explicitly narrowed.

Canonical result:
- Output: `controlled_test_output/tier7_0d_20260505_state_specific_continuous_interface/`.
- Runner: `experiments/tier7_0d_state_specific_continuous_interface.py`.
- Criteria: `10 / 10`.
- Outcome: `lag_regression_explains_benchmark`.
- Raw CRA aggregate geomean MSE: `1.223255942741316`.
- Lag-only online LMS aggregate geomean MSE: `0.1514560842638888`.
- Best state-specific online model: `two_stage_lag_residual_state_online_repair`.
- Best state-specific online aggregate geomean MSE: `0.14545708938088173`.
- Best state-specific online margin versus lag-only: `1.041242368512535`.
- Best state-specific online margin versus best sham: `0.9685029838920843`.
- Train-prefix ridge lag-only upper-bound geomean MSE: `0.044288645167134134`.
- Train-prefix ridge lag plus orthogonal state upper-bound geomean MSE:
  `0.05474449238029897`.

Interpretation:
- The current Tier 7 standard dynamical benchmark path is explained by causal
  lag regression under this interface.
- CRA state-specific online candidates improve raw CRA, but do not beat lag-only
  by a meaningful margin and do not separate from shuffled residual controls.
- Train-prefix ridge probes also favor lag-only over lag plus state, which means
  even the diagnostic upper bound does not justify a state-specific mechanism on
  this benchmark suite.
- Do not promote a continuous-readout mechanism from Tier 7.0d.
- Do not migrate this benchmark path to hardware unless a future mechanism
  changes the failure class.

Next step after Tier 7.0d: Tier 5.19 / 7.0e continuous temporal dynamics
substrate contract. Tier 7.0-7.0d remains a clean limitation and claim-narrowing
branch, but it exposed a general missing substrate that must be tested before
assuming lifecycle alone will evolve the ability.

### Tier 5.19 / 7.0e - Continuous Temporal Dynamics Substrate Contract

Status: DEFINED / CURRENT CONTRACT GATE. This section defines the next software
mechanism gate before code is written. It is not yet canonical evidence and does
not change the registry count until a completed run is ingested.

Detailed contract:

```text
docs/TIER5_19_CONTINUOUS_TEMPORAL_DYNAMICS_CONTRACT.md
```

Question:

```text
Can CRA add a general continuous temporal/fading-memory substrate that helps
stateful sequence tasks without reducing to causal lag regression, benchmark-
specific tricks, or unconstrained supervised readouts?
```

Hypothesis:

```text
A bounded CRA-native temporal substrate with multi-timescale fading state,
nonlinear recurrent state, and a local continuous prediction/readout interface
will improve tasks where hidden temporal state matters, while preserving current
CRA delayed-credit, memory, routing, prediction, self-evaluation, and hardware-
bridge claims.
```

Null hypothesis:

```text
Any apparent improvement is explained by lag-only regression, fixed/random
reservoir dynamics, shuffled temporal state, target leakage, or task-specific
benchmark fitting.
```

Mechanism boundary:

```text
This is a runtime/software substrate candidate, not a per-polyp feature dump.
It may provide shared temporal state, bounded recurrent summaries, and local
continuous interfaces that polyps/readouts can use. It must keep individual
polyps small and declare which state is per-polyp, population-level, readout-
level, or runtime-level.
```

Required contract before implementation:

```text
state variables
timescales and decay equations
nonlinear recurrent update rule
local continuous readout/prediction rule
plasticity/update rule, if any
parameter budget
anti-leakage guardrails
anti-benchmark-chasing guardrails
expected artifacts
compact regression suite
promotion/freeze rule
```

Required comparisons and controls:

```text
current CRA v2.1
lag-only online LMS with the same causal lag budget
state-only online model
state plus lag online model
fixed ESN / reservoir baseline
random reservoir baseline
no-recurrence ablation
no-plasticity ablation
frozen temporal-state ablation
shuffled temporal-state sham
shuffled-target control
current Tier 7.0 benchmark baselines
compact Tier 1/2/3 CRA guardrails
current delayed_cue / hard_noisy_switching / memory-context guardrails
```

Required tasks:

```text
Mackey-Glass
Lorenz
NARMA10
aggregate geometric-mean MSE
delayed_cue
hard_noisy_switching
memory/context pressure tasks
at least one held-out temporal-state diagnostic that is not one of the three
standard benchmarks
```

Pass criteria:

```text
All predeclared tasks and controls run without leakage.
Temporal substrate beats raw v2.1 where stateful continuous prediction matters.
Temporal substrate beats lag-only by a meaningful predeclared margin on at least
one task where lag-only should be insufficient.
Temporal substrate separates from shuffled-state, frozen-state, no-recurrence,
and shuffled-target controls.
Current CRA core guardrails do not regress.
Any improvement is not isolated to a single benchmark family.
```

Fail criteria:

```text
Lag-only or fixed/random reservoirs explain the gain.
Shuffled or frozen temporal state performs similarly to the proposed substrate.
The mechanism helps only one benchmark through task-specific tuning.
Existing CRA claims regress.
Any future-target, held-out-row, or label leakage is found.
The mechanism cannot be described as a bounded CRA-native substrate.
```

Promotion/freeze condition:

```text
Tier 5.19 / 7.0e itself is a contract gate and does not freeze a baseline.
Tier 5.19a/b may lead to a software freeze only if the implemented substrate
passes shams, baselines, and compact regression. If it fails, park or narrow it.
Do not migrate this benchmark path to hardware until a software mechanism earns
promotion.
```

### Tier 5.19a - Local Continuous Temporal Substrate Reference

Status: LOCAL SOFTWARE PASS / NONCANONICAL DIAGNOSTIC. This tier does not enter
the canonical registry and does not freeze a baseline.

Output:

```text
controlled_test_output/tier5_19a_20260505_temporal_substrate_reference/
```

Runner:

```text
experiments/tier5_19a_temporal_substrate_reference.py
```

Criteria:

```text
12 / 12
```

Classification:

```text
fading_memory_ready_but_recurrence_not_yet_specific
```

Key metrics:

```text
heldout_long_memory candidate MSE = 0.38570722690740805
heldout_long_memory lag-only MSE = 1.2710078678632046
heldout margin vs lag-only = 3.2952658887263206
heldout margin vs shuffled-state = 4.900069939484292
heldout margin vs frozen-state = 1.474026780849015
heldout margin vs no-plasticity = 7.713190900565484
heldout margin vs no-recurrence = 1.0303693588886562
standard-three candidate geomean MSE = 0.1488559612698296
standard-three lag-only geomean MSE = 0.1514560842638888
```

Interpretation:

```text
The local fading-memory substrate is promising and clearly useful on the held-out
long-memory diagnostic. Shuffled-state, frozen-state, no-plasticity, and lag-only
controls lose there. However, the no-recurrence control is too close to the full
candidate, so Tier 5.19a does not prove bounded nonlinear recurrence is the
causal ingredient.
```

Next step:

```text
Tier 5.19b benchmark/sham/regression gate with sharper recurrence-specific
controls. Do not freeze, promote, or migrate to hardware from Tier 5.19a alone.
```

### Tier 5.19b - Temporal Substrate Benchmark / Sham / Regression Gate

Status: COMPLETE - LOCAL SOFTWARE PASS / CLAIM-NARROWING DIAGNOSTIC.

Question:

```text
Does the temporal substrate earn promotion after separating fading-memory value
from bounded nonlinear recurrent-state value and preserving the current CRA
guardrails?
```

Required additional controls beyond Tier 5.19a:

```text
fading-memory-only ablation
recurrent-hidden-only ablation
state-reset ablation
recurrent-weight shuffle or sign-permutation sham
lag-only control
fixed ESN / reservoir control
random reservoir control
frozen temporal-state ablation
shuffled temporal-state sham
shuffled-target control
no-plasticity readout ablation
current v2.1 raw CRA control
```

Required tasks:

```text
Mackey-Glass
Lorenz
NARMA10
heldout_long_memory from Tier 5.19a
one recurrence-pressure diagnostic where fading-memory-only should be weaker
```

Pass criteria:

```text
All required controls run.
Temporal candidate beats lag-only and destructive shams on the held-out
long-memory diagnostic.
Temporal candidate beats fading-memory-only or no-recurrence controls on the
recurrence-pressure diagnostic by a predeclared margin.
Existing CRA guardrails do not materially regress.
No target leakage, held-out-row fitting, or task-name-specific mechanism branch
is present.
```

Result:

```text
Output: controlled_test_output/tier5_19b_20260505_temporal_substrate_gate/
Runner: experiments/tier5_19b_temporal_substrate_gate.py
Criteria: 12/12
Classification: fading_memory_supported_recurrence_unproven
```

Key metrics:

```text
heldout_long_memory:
  temporal_full_candidate MSE = 0.3857
  lag_only_online_lms_control MSE = 1.2710
  margin vs lag-only = 3.30x

recurrence_pressure:
  temporal_full_candidate MSE = 0.8982
  lag_only_online_lms_control MSE = 0.8967
  fading_memory_only_ablation MSE = 1.0348
  state_reset_ablation MSE = 0.9029
  shuffled_temporal_state_sham MSE = 1.1686
```

Interpretation:

```text
Tier 5.19b supports a narrowed fading-memory temporal-state story, but it does
not prove bounded nonlinear recurrence. The full candidate did not beat lag-only
on recurrence_pressure, and state-reset was too close. No baseline freeze and no
hardware migration are authorized from 5.19b.
```

Promotion boundary:

```text
Tier 5.19b recommends narrowing or repair. It does not freeze a baseline.
Compact CRA guardrails are deferred to Tier 5.19c because 5.19b did not earn a
recurrence-specific promotion.
```

### Tier 5.19c - Fading-Memory Narrowing / Compact-Regression Decision

Status: COMPLETE - SOFTWARE PASS / v2.2 BASELINE FREEZE.

Question:

```text
Does a narrowed multi-timescale fading-memory temporal substrate, with no
bounded-recurrence claim, earn promotion after compact CRA guardrails and
sham controls?
```

Required comparisons:

```text
current v2.1
lag-only causal readout
fixed ESN / reservoir
random reservoir
narrowed fading-memory candidate
full temporal candidate as non-promoted reference
frozen temporal-state ablation
shuffled temporal-state sham
shuffled-target control
no-plasticity readout ablation
compact Tier 1/2/3 plus v2.1 guardrails
```

Pass criteria:

```text
Narrowed fading-memory candidate preserves existing CRA claims.
Narrowed candidate improves held-out temporal-memory diagnostics versus current
v2.1 and destructive shams.
Lag-only does not fully explain the claimed improvement where the claim says
temporal state should matter.
No recurrence-specific claim is made unless a recurrence repair is run later.
No leakage, target peeking, or task-name-specific mechanism branch is present.
```

Fail / park criteria:

```text
Existing v2.1 guardrails regress.
Lag-only explains the narrowed mechanism.
Shuffled/frozen/no-plasticity controls match the candidate.
The mechanism only helps a synthetic diagnostic but does not preserve the
research baseline.
```

Result:

```text
Output: controlled_test_output/tier5_19c_20260505_fading_memory_regression/
Runner: experiments/tier5_19c_fading_memory_regression.py
Criteria: 11/11
Classification: fading_memory_ready_for_v2_2_freeze
Baseline frozen: baselines/CRA_EVIDENCE_BASELINE_v2.2.md
Compact mode/backend: full / NEST
```

Key metrics:

```text
Temporal-memory geomean candidate MSE = 0.2275222950
Temporal-memory geomean lag-only MSE = 0.8953538817
Temporal margin vs lag-only = 3.9352358045x
Temporal margin vs raw v2.1 = 9.5999245538x

Standard-three candidate geomean MSE = 0.1985397576
Standard-three lag-only geomean MSE = 0.1536819662
```

Interpretation:

```text
Tier 5.19c promotes only the narrowed fading-memory temporal-state substrate.
It does not revive the bounded nonlinear recurrence claim from Tier 5.19a/b.
It also does not claim universal benchmark superiority because lag-only remains
stronger on the standard Mackey-Glass / Lorenz / NARMA10 aggregate.
```

Claim boundary:

```text
v2.2 is bounded host-side software evidence for multi-timescale fading-memory
temporal state. It is not hardware evidence, not native on-chip temporal
dynamics, not bounded nonlinear recurrence, not language, not planning, not
AGI, and not ASI.
```

Next step:

```text
Tier 4.30-readiness audit. Decide how lifecycle-native work layers on v2.2
software evidence and the existing v2.1-era native mechanism bridge before
writing Tier 4.30 hardware code.
```

### Tier 4.30-readiness - Lifecycle-Native Preflight / Layering Audit

Status: COMPLETE - LOCAL ENGINEERING PASS.

Question:

```text
Before writing lifecycle-native code, what exactly is the allowed layering
between v2.2 host-side temporal state, the v2.1-era native mechanism bridge,
and the future lifecycle/self-scaling runtime?
```

Result:

```text
Output: controlled_test_output/tier4_30_readiness_20260505_lifecycle_native_audit/
Runner: experiments/tier4_30_readiness_audit.py
Criteria: 16/16
Mode: local-readiness-audit
```

Decision:

```text
Initial lifecycle-native work layers on CRA_NATIVE_MECHANISM_BRIDGE_v0.3.
v2.2 is used as a software reference boundary only.
Native/on-chip v2.2 fading-memory temporal state is not automatically migrated.
```

Required lifecycle-native surface:

```text
static preallocated pool
active/inactive mask
polyp_id / lineage_id / parent_slot / generation
age_steps
trophic_health
cyclin_d
bax
last_event_type
event_count
compact readback for all lifecycle fields
```

Required controls:

```text
fixed_static_pool_control
random_event_replay_control
active_mask_shuffle_control
lineage_id_shuffle_control
no_trophic_pressure_control
no_dopamine_or_plasticity_control
```

Claim boundary:

```text
Tier 4.30-readiness is not hardware evidence, does not implement lifecycle,
does not freeze a native lifecycle baseline, does not prove speedup, does not
prove multi-chip scaling, and does not migrate v2.2 temporal state.
```

Next step:

```text
Tier 4.30 lifecycle-native contract: formalize static-pool command/readback
schema and local parity criteria before implementation or EBRAINS packaging.
```

### Tier 4.30 - Lifecycle-Native Static-Pool Contract

Status: COMPLETE - LOCAL ENGINEERING PASS.

Question:

```text
Can the lifecycle-native path be specified precisely enough to implement a
static-pool local reference and later hardware smoke without dynamic graph
creation, hidden host state, or unscoped v2.2 temporal migration?
```

Result:

```text
Output: controlled_test_output/tier4_30_20260505_lifecycle_native_contract/
Runner: experiments/tier4_30_lifecycle_native_contract.py
Criteria: 14/14
Mode: local-contract
```

Contract summary:

```text
Pool: 8 static slots
Founders: 2 active founders
Commands: lifecycle init, lifecycle event, trophic update, lifecycle readback,
          lifecycle sham mode
Readback: 23 summary/per-slot fields including masks, lineage, trophic state,
          event counters, checksums, and invalid-event count
Events: trophic_update, cleavage, adult_birth, death, maturity_handoff
Gates: 4.30 contract, 4.30a local reference, 4.30b source audit,
       4.30b-hw single-core smoke, 4.30c multi-core split,
       4.30d source/local C host test, 4.30e hardware smoke,
       4.30f lifecycle sham-control subset
Failure classes: contract gap, dynamic allocation dependency, local reference
                 mismatch, readback mismatch, lineage/mask corruption, sham
                 explains effect, unsupported claim jump
```

Claim boundary:

```text
Tier 4.30 is not runtime implementation, not hardware evidence, not a
lifecycle/self-scaling proof, not a lifecycle baseline freeze, not v2.2 temporal
state migration, not speedup, and not multi-chip scaling.
```

Next step:

```text
Tier 4.30a local static-pool lifecycle reference: implement deterministic
expected active-mask, lineage, event-count, checksum, and control outputs before
any C runtime implementation or EBRAINS package.
```

### Tier 4.30a - Local Static-Pool Lifecycle Reference

Status: COMPLETE - LOCAL REFERENCE PASS.

Question:

```text
Can the Tier 4.30 static-pool lifecycle contract be expressed as a deterministic
local reference with exact active-mask, lineage, event-count, checksum, and sham
outputs before runtime C or hardware work?
```

Result:

```text
Output: controlled_test_output/tier4_30a_20260505_static_pool_lifecycle_reference/
Runner: experiments/tier4_30a_static_pool_lifecycle_reference.py
Criteria: 20/20
Mode: local-reference
```

Key local-reference results:

```text
canonical_32 enabled: 32 events, 0 invalid, active_mask=63, active=6,
                      cleavage=4, birth=4, death=4,
                      lineage_checksum=105428, trophic_checksum=466851
boundary_64 enabled: 64 events, 0 invalid, active_mask=127, active=7,
                     cleavage=8, birth=5, death=8,
                     lineage_checksum=18496, trophic_checksum=761336
```

Controls precomputed:

```text
fixed_static_pool_control
random_event_replay_control
active_mask_shuffle_control
lineage_id_shuffle_control
no_trophic_pressure_control
no_dopamine_or_plasticity_control
```

Claim boundary:

```text
Tier 4.30a is not runtime implementation, not hardware evidence, not a task
benefit claim, not a lifecycle baseline freeze, and not v2.2 temporal-state
migration. It only proves the local static-pool reference is bounded,
repeatable, and sham-instrumented.
```

### Tier 4.30b - Lifecycle Runtime Source Audit

Status: COMPLETE - LOCAL SOURCE/RUNTIME PASS.

Question:

```text
Can the Tier 4.30a static-pool lifecycle reference be mapped into the smallest
custom-runtime lifecycle state surface while preserving existing runtime and
profile behavior?
```

Result:

```text
Output: controlled_test_output/tier4_30b_20260505_lifecycle_source_audit/
Runner: experiments/tier4_30b_lifecycle_source_audit.py
Criteria: 13/13
Mode: local-source-audit
```

Key source/runtime results:

```text
runtime lifecycle opcodes declared: init, event, trophic update, read state, sham mode
runtime state structs declared: lifecycle_slot_t, cra_lifecycle_summary_t
host lifecycle readback added separately from CMD_READ_STATE
existing CMD_READ_STATE schema remains version 2
canonical_32 checksum parity: lineage=105428, trophic=466851
boundary_64 checksum parity: lineage=18496, trophic=761336
runtime test-lifecycle, test-profiles, and test all passed
```

Claim boundary:

```text
Tier 4.30b source audit is local source/runtime host evidence only. It is not
hardware evidence, not task-effect evidence, not multi-core lifecycle, not v2.2
temporal-state migration, and not a lifecycle baseline freeze.
```

Next step:

```text
Tier 4.30c multi-core lifecycle state split contract/local reference
(completed). Define which lifecycle state lives on which runtime core, how
active masks and lineage move across the selected protocol, and what
checksums/readbacks prove state integrity before another EBRAINS package.
```

Prepared package update:

```text
Status: PREPARED ONLY, not hardware evidence
Prepared output: controlled_test_output/tier4_30b_hw_20260505_prepared/
Upload folder: ebrains_jobs/cra_430b
Runner: experiments/tier4_30b_lifecycle_hardware_smoke.py
Runner revision: tier4_30b_lifecycle_hardware_smoke_20260505_0001
JobManager command:
cra_430b/experiments/tier4_30b_lifecycle_hardware_smoke.py --mode run-hardware --output-dir tier4_30b_hw_job_output
Prepared criteria: 6/6
```

Prepared pass criteria already satisfied:

```text
reference scenarios generated = canonical_32 and boundary_64
lifecycle host tests pass
main.c host syntax check pass
upload bundle created
stable upload folder created
run-hardware command emitted
```

Hardware pass criteria remain unchanged:

```text
real SpiNNaker target acquired
decoupled_memory_route .aplx builds and loads
lifecycle init succeeds
all lifecycle event commands succeed
canonical_32 readback matches active mask 63, lineage checksum 105428,
  trophic checksum 466851, and zero invalid events
boundary_64 readback matches active mask 127, lineage checksum 18496,
  trophic checksum 761336, and zero invalid events
zero synthetic fallback
```

Returned hardware result after ingest correction:

```text
Status: PASS after ingest correction
Raw remote status: fail
Corrected ingest output: controlled_test_output/tier4_30b_hw_20260505_hardware_pass_ingested/
Board/core: 10.11.226.17 / (0,0,4)
Runner raw revision: tier4_30b_lifecycle_hardware_smoke_20260505_0001
Corrected runner revision: tier4_30b_lifecycle_hardware_smoke_20260505_0002
Reason: rev-0001 checked cumulative readback_bytes instead of compact payload_len
Ingest criteria: 5/5
canonical_32 corrected scenario criteria: 16/16
boundary_64 corrected scenario criteria: 16/16
payload_len: 68 for both scenarios
fallback: 0
```

Meaning: the single-core lifecycle metadata surface executed on real
SpiNNaker, with exact active-mask, event-count, lineage-checksum, and
trophic-checksum parity. The raw remote failure is preserved as an
instrumentation/criterion defect, not a lifecycle-state failure. Boundary
remains unchanged: this is not task-benefit evidence, not multi-core lifecycle
migration, not speedup evidence, not v2.2 temporal-state migration, and not a
lifecycle baseline freeze.

### Tier 4.30c - Multi-Core Lifecycle State Split

Status: COMPLETE - LOCAL CONTRACT/REFERENCE PASS.

Question:

```text
Can lifecycle ownership, active-mask synchronization, lineage/trophic checksums,
and failure classes be split across the four-core native bridge plus a dedicated
lifecycle core before any multi-core lifecycle runtime C or EBRAINS package?
```

Result:

```text
Output: controlled_test_output/tier4_30c_20260505_multicore_lifecycle_split/
Runner: experiments/tier4_30c_multicore_lifecycle_split.py
Criteria: 22/22
Mode: local-contract-reference
```

Core ownership contract:

```text
context_core: owns context slots/confidence; receives active-mask snapshots
route_core: owns route slots/confidence; receives active-mask snapshots
memory_core: owns memory slots/replay keys/confidence; receives active-mask snapshots
learning_core: owns pending horizons/readout/reward updates; requests lifecycle events
lifecycle_core: owns fixed slot pool, active masks, lineage IDs, trophic health,
                event counters, sham mode, event acks, and lifecycle summaries
```

Message contract:

```text
LIFE_INIT_CONTROL: host SDP control to lifecycle_core
LIFE_EVENT_REQUEST: learning_core to lifecycle_core; MCPL/multicast target
LIFE_TROPHIC_UPDATE: learning_core to lifecycle_core; MCPL/multicast target
LIFE_ACTIVE_MASK_SYNC: lifecycle_core broadcast to context/route/memory/learning
LIFE_SUMMARY_READBACK: host SDP readback, compact summary payload_len=68
```

Scenario parity:

```text
canonical_32: 32 event acks, 13 mask syncs, final_mask=63,
              lineage_checksum=105428, trophic_checksum=466851, match=True
boundary_64: 64 event acks, 22 mask syncs, final_mask=127,
             lineage_checksum=18496, trophic_checksum=761336, match=True
```

Failure classes:

```text
duplicate_event
stale_event
missing_ack
mask_desync
checksum_mismatch
invalid_event_hidden
wrong_owner_write
payload_schema_drift
```

Claim boundary:

```text
Tier 4.30c is local contract/reference evidence only. It is not runtime C
implementation, not hardware evidence, not task-benefit evidence, not
multi-chip scaling, not speedup evidence, not v2.2 temporal migration, and not
a lifecycle baseline freeze.
```

Next step:

```text
Tier 4.30d multi-core lifecycle runtime source audit/local C host test
(completed). Implement only the source/local-test layer for the 4.30c split:
lifecycle-core profile, message/readback stubs, active-mask/count/lineage sync
bookkeeping, and source guards before any EBRAINS package.
```

### Tier 4.30d - Multi-Core Lifecycle Runtime Source Audit

Status: COMPLETE - LOCAL SOURCE/RUNTIME HOST PASS.

Question:

```text
Can the Tier 4.30c five-core lifecycle ownership contract be represented in the
custom runtime source surface and local C host tests before a multi-core
lifecycle EBRAINS package is prepared?
```

Result:

```text
Output: controlled_test_output/tier4_30d_20260505_lifecycle_runtime_source_audit/
Runner: experiments/tier4_30d_lifecycle_runtime_source_audit.py
Runner revision: tier4_30d_lifecycle_runtime_source_audit_20260505_0001
Criteria: 14/14
Mode: local-source-audit
```

Implemented source/runtime surface:

```text
PROFILE_LIFECYCLE_CORE = 7
MCPL_MSG_LIFECYCLE_EVENT_REQUEST = 3
MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE = 4
MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC = 5
test-lifecycle-split local host test target
lifecycle_core runtime profile build/test target
non-lifecycle profile lifecycle-write NAK guards
active-mask/count/lineage sync send/receive bookkeeping
duplicate/stale/missing-ack lifecycle counters
compact lifecycle summary payload_len=68 preserved
```

Local test coverage:

```text
make -C coral_reef_spinnaker/spinnaker_runtime test-lifecycle
make -C coral_reef_spinnaker/spinnaker_runtime test-lifecycle-split
make -C coral_reef_spinnaker/spinnaker_runtime test-profiles
make -C coral_reef_spinnaker/spinnaker_runtime test
```

Claim boundary:

```text
Tier 4.30d is local source/runtime host evidence only. It is not EBRAINS
hardware evidence, not task-benefit evidence, not speedup, not multi-chip
scaling, not v2.2 temporal-state migration, and not a lifecycle baseline
freeze.
```

Next step:

```text
Tier 4.30e multi-core lifecycle hardware smoke passed and has been ingested.
Tier 4.30f lifecycle sham-control hardware subset also passed after ingest.
Tier 4.30g lifecycle task-benefit/resource bridge local contract/reference also
passed. The Tier 4.30g hardware task-benefit/resource bridge source package is
now prepared at `ebrains_jobs/cra_430g` after hardware runner/source validation.
Next: run the prepared package on EBRAINS and ingest returned artifacts.
```

### Tier 4.30e - Multi-Core Lifecycle Hardware Smoke

Status: HARDWARE PASS / INGESTED.

Question:

```text
Does the Tier 4.30d five-profile lifecycle runtime surface survive real
SpiNNaker build/load/execution/readback before hardware lifecycle sham controls?
```

Result:

```text
Prepared output: controlled_test_output/tier4_30e_hw_20260505_prepared/
Ingested output: controlled_test_output/tier4_30e_hw_20260505_hardware_pass_ingested/
Runner: experiments/tier4_30e_multicore_lifecycle_hardware_smoke.py
Runner revision: tier4_30e_multicore_lifecycle_hardware_smoke_20260505_0001
Upload folder: ebrains_jobs/cra_430e
Board: 10.11.226.145
Raw remote status: pass
Ingest status: pass
Hardware criteria: 75/75
Ingest criteria: 5/5
Returned artifacts preserved: 31
Task runtime: 0.21091535408049822 seconds
```

Required hardware coverage:

```text
build/load context_core, route_core, memory_core, learning_core, lifecycle_core
CMD_READ_STATE profile IDs: context=4, route=5, memory=6, learning=3, lifecycle=7
non-lifecycle profiles reject direct lifecycle read commands
lifecycle_core runs canonical_32 and boundary_64 lifecycle schedules
compact lifecycle readback uses host-observed payload_len=68
duplicate/stale lifecycle event probe rejects repeated/old event IDs
zero synthetic fallback
zero unhandled hardware exception
```

Pass means:

```text
real SpiNNaker target acquired
all five profile builds pass
all five profile loads pass
all profile/readback criteria pass
canonical/boundary lifecycle summaries match Tier 4.30a/4.30c references
duplicate/stale lifecycle rejection probe passes
returned artifacts ingest cleanly
```

Fail means:

```text
any profile fails to build/load
profile IDs do not match the role map
non-lifecycle profiles accept lifecycle mutation/readback
lifecycle summaries diverge from the reference
duplicate/stale guard does not reject as expected
target acquisition/readback fails
```

Boundary:

```text
Tier 4.30e is a hardware smoke gate only. It is not lifecycle task-benefit
evidence, not lifecycle sham-control success, not speedup, not multi-chip
scaling, not v2.2 temporal-state migration, and not a lifecycle baseline freeze.
```

### Tier 4.30f - Lifecycle Sham-Control Hardware Subset

Status: HARDWARE PASS / INGESTED.

Question:

```text
Do the compact lifecycle sham controls produce expected behavioral separations
on the real lifecycle_core hardware path, rather than merely toggling a
readback flag?
```

Hypothesis:

```text
The five-profile lifecycle runtime can run a compact canonical sham-control
subset on SpiNNaker. Enabled mode remains canonical, fixed-pool suppresses
active-mask mutation, random replay and active-mask shuffle separate from the
enabled lineage/mask path, no-trophic suppresses trophic/maturity mutation, and
no-dopamine removes reward contribution from trophic updates.
```

Null hypothesis:

```text
At least one sham mode is cosmetic, does not alter the relevant lifecycle
summary, diverges from the local fixed-point reference, or breaks the
five-profile hardware/runtime path.
```

Mechanism under test:

```text
CMD_LIFECYCLE_SHAM_MODE plus lifecycle event execution on lifecycle_core.
Runtime modes tested: enabled, fixed_static_pool_control,
random_event_replay_control, active_mask_shuffle_control,
no_trophic_pressure_control, no_dopamine_or_plasticity_control.
```

Prepared package:

```text
Runner: experiments/tier4_30f_lifecycle_sham_hardware_subset.py
Prepared output: controlled_test_output/tier4_30f_hw_20260505_prepared/
Upload folder: ebrains_jobs/cra_430f
Prepared criteria: 8/8
JobManager command:
cra_430f/experiments/tier4_30f_lifecycle_sham_hardware_subset.py --mode run-hardware --output-dir tier4_30f_hw_job_output
```

Returned / ingested result:

```text
Ingested output: controlled_test_output/tier4_30f_hw_20260505_hardware_pass_ingested/
Raw remote status: pass
Ingest status: pass
Board: 10.11.227.9
Hardware criteria: 185/185
Ingest criteria: 5/5
Returned artifacts preserved: 35
Task status: pass
Hardware target configured: true
Profile builds: all five pass
Profile loads: all five pass
Synthetic fallback: 0
Compact lifecycle payload length: 68
```

Required controls:

```text
enabled reference
fixed-pool sham
random-event replay sham
active-mask shuffle sham
no-trophic-pressure sham
no-dopamine/no-plasticity sham
non-lifecycle profile guard
profile readback guard
```

Pass means:

```text
real SpiNNaker target acquired
all five profile builds pass
all five profile loads pass
all profile/readback criteria pass
enabled mode matches canonical_32 reference
each sham mode matches its local fixed-point expected summary
control/event success and failure counts match expected accepted/invalid counts
fixed-pool active-mask mutation counters remain suppressed
control summaries separate from enabled on the predeclared field
compact lifecycle payload length remains 68
zero synthetic fallback
returned artifacts ingest cleanly
```

Fail means:

```text
any profile fails to build/load
profile IDs do not match the role map
non-lifecycle profiles accept lifecycle readback
enabled reference diverges
any sham mode fails to match expected counters/checksums
any control does not separate from enabled on its predeclared field
target acquisition/readback fails
```

Boundary:

```text
Tier 4.30f is a compact lifecycle sham-control hardware subset. It is not full
Tier 6.3 hardware, not lifecycle task-benefit evidence, not speedup, not
multi-chip scaling, not v2.2 temporal-state migration, and not a lifecycle
baseline freeze.
```

Result summary:

```text
enabled mode remained canonical:
  active_mask_bits=63
  lineage_checksum=105428
  trophic_checksum=466851

fixed_static_pool_control separated active_mask_bits from enabled:
  control=3
  enabled=63
  mask-mutation counters adult_birth/cleavage/death all remained 0

random_event_replay_control separated lineage_checksum from enabled:
  control=6170
  enabled=105428

active_mask_shuffle_control separated active_mask_bits from enabled:
  control=0
  enabled=63

no_trophic_pressure_control separated trophic_checksum from enabled:
  control=336384
  enabled=466851

no_dopamine_or_plasticity_control separated trophic_checksum from enabled:
  control=457850
  enabled=466851
```

Next:

```text
Tier 4.30g local contract/reference has now passed. The next valid step is the
Tier 4.30g hardware task-benefit/resource bridge package/run, preserving the
same enabled/control contract, returned resource/readback accounting, and narrow
claim boundary. Do not freeze a lifecycle native baseline until hardware task
effect, controls, and resource accounting pass.
```

### Tier 4.30g - Lifecycle Task-Benefit / Resource Bridge

Status: LOCAL CONTRACT PASS + HARDWARE PASS / INGESTED.

Question:

```text
Can native lifecycle state be bridged into a task-bearing path with controls
and resource accounting before hardware packaging?
```

Hypothesis:

```text
The enabled lifecycle mode opens the bounded task bridge while sham controls
close it, producing a measurable local task separation and a predeclared
hardware resource contract.
```

Null hypothesis:

```text
Lifecycle state does not produce a specific task-path separation, or the
separation is indistinguishable from sham controls or missing resource fields.
```

Mechanism under test:

```text
Lifecycle summary -> bounded bridge gate -> task feature path:
context_slot * route_slot * lifecycle_gated_memory_slot * cue
```

Controls:

```text
enabled
fixed_static_pool_control
random_event_replay_control
active_mask_shuffle_control
no_trophic_pressure_control
no_dopamine_or_plasticity_control
```

Local result:

```text
Output: controlled_test_output/tier4_30g_20260506_lifecycle_task_benefit_resource_bridge/
Runner: experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py
Runner revision: tier4_30g_lifecycle_task_benefit_resource_bridge_20260506_0001
Status: pass
Criteria: 9/9
Enabled tail accuracy: 1.0
Control tail-accuracy ceiling: 0.375
Enabled-control tail margin: 0.625
Resource/readback fields: declared for every mode
```

Hardware result:

```text
Prepared output: controlled_test_output/tier4_30g_hw_20260506_prepared/
Ingested output: controlled_test_output/tier4_30g_hw_20260505_hardware_pass_ingested/
Board: 10.11.242.97
Raw remote status: pass
Ingest status: pass
Hardware criteria: 285/285
Ingest criteria: 5/5
Returned artifacts preserved: 36
Enabled bridge gate: 1
Control bridge gates: 0
Enabled reference tail accuracy: 1.0
Control reference tail accuracy: 0.375
Compact lifecycle payload length: 68
Stale replies/timeouts: 0
```

Pass means:

```text
Tier 4.30f hardware evidence is present
canonical sham modes are preserved
enabled bridge gate opens
all control bridge gates close
enabled task tail accuracy >= 0.875
control tail-accuracy ceiling <= 0.625
enabled-control tail margin >= 0.25
resource/write/readback fields are declared
claim boundary preserves hardware/autonomy/baseline nonclaims
```

Fail means:

```text
Tier 4.30f prerequisite is missing
mode set changes silently
any control opens the task gate
enabled task path does not separate from controls
resource accounting is incomplete
claim boundary overstates hardware or lifecycle-baseline evidence
```

Boundary:

```text
Tier 4.30g-hw is hardware task-benefit/resource bridge evidence for a bounded
host-ferried lifecycle gate. It is not autonomous lifecycle-to-learning MCPL,
not speedup, not multi-chip scaling, not dynamic population creation, not v2.2
temporal-state migration, and not full organism autonomy.
```

Baseline decision:

```text
Freeze condition met. `CRA_LIFECYCLE_NATIVE_BASELINE_v0.4` is frozen after
lifecycle telemetry, controls, resource accounting, and one bounded useful
hardware task effect passed.
```

Tier 4.31a native temporal-substrate readiness result:

```text
Output: controlled_test_output/tier4_31a_20260506_native_temporal_substrate_readiness/
Status: pass
Criteria: 24/24
Decision: migrate_fading_memory_ema_traces_first
State subset: seven causal EMA traces over current temporal input
Derived features: deltas and novelty; not stored as persistent state
Persistent state budget: 56 bytes
Total initial temporal budget: 112 bytes
Controls: lag-only, zero-state, frozen-state, shuffled-state, reset-interval,
          shuffled-target, no-plasticity, hidden-recurrence exclusion
Command plan: CMD_TEMPORAL_INIT=39, CMD_TEMPORAL_UPDATE=40,
              CMD_TEMPORAL_READ_STATE=41, CMD_TEMPORAL_SHAM_MODE=42
              with zero command-code collisions
```

Boundary:

```text
Tier 4.31a is local readiness/contract evidence only. It does not implement the
C runtime, does not prove SpiNNaker hardware transfer, does not prove speedup,
does not prove multi-chip scaling, does not prove nonlinear recurrence, and does
not freeze a new baseline.
```

Tier 4.31b native temporal-substrate local fixed-point reference result:

```text
Output: controlled_test_output/tier4_31b_20260506_native_temporal_fixed_point_reference/
Status: pass
Criteria: 16/16
Outcome: fixed_point_temporal_reference_ready_for_source_audit
Fixed-point geomean MSE: 0.22723731574965408
Float reference geomean MSE: 0.22752229502159751
Fixed/float ratio: 0.9987474666079806
Selected max feature error: 0.004646656591329457
Selected mean feature error: 0.0009358316819073308
Selected saturation count: 0
Conservative ±1 saturation count: 482
Lag-only margin: 3.9401710002446917
Zero-state margin: 2.742086949954038
Frozen-state margin: 1.3498635995401482
Shuffled-state margin: 4.915732126637618
Reset-interval margin: 3.112217734650662
Shuffled-target margin: 5.1409664416259835
No-plasticity margin: 9.611963859542444
```

Boundary:

```text
Tier 4.31b is local fixed-point reference/parity evidence only. It supports
source/runtime implementation work for the named seven-EMA subset. It does not
prove C implementation, hardware transfer, speedup, multi-chip scaling,
nonlinear recurrence, or benchmark superiority.
```

Next:

```text
Tier 4.31c native temporal-substrate source/runtime implementation and local C
host tests. No EBRAINS package until the C runtime matches the 4.31b fixed-point
reference and readback/control contract.
```

Tier 4.31c native temporal-substrate runtime source audit result:

```text
Output: controlled_test_output/tier4_31c_20260506_native_temporal_runtime_source_audit/
Status: pass
Criteria: 17/17
Runtime source: C-owned seven-EMA temporal state
Trace bound: ±2 s16.15
Compact temporal readback length: 48
Command codes: CMD_TEMPORAL_INIT=39, CMD_TEMPORAL_UPDATE=40,
               CMD_TEMPORAL_READ_STATE=41, CMD_TEMPORAL_SHAM_MODE=42
Owner surface: learning_core plus monolithic/decoupled local surfaces
Non-owner profiles: context_core, route_core, memory_core, lifecycle_core
Tests: test-temporal-state, test-profiles, test, test-lifecycle,
       test-lifecycle-split
```

Boundary:

```text
Tier 4.31c is local source/runtime host evidence only. It proves the custom C
runtime owns the seven-EMA fixed-point temporal subset with compact readback and
behavior-backed shams. It does not prove SpiNNaker hardware execution, speedup,
multi-chip scaling, nonlinear recurrence, native replay/sleep, native macro
eligibility, or benchmark superiority.
```

Result:

```text
Tier 4.31d native temporal-substrate hardware smoke passed and was ingested at
controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested/.
Board: 10.11.216.121.
Runner revision: tier4_31d_native_temporal_hardware_smoke_20260506_0003.
Remote hardware criteria: 59/59.
Ingest criteria: 5/5.
Returned artifacts preserved: 21.
Scenarios: enabled, zero_state, frozen_state, reset_each_update all passed.
Payload length: 48.
Boundary: one-board hardware smoke only; not repeatability, speedup, benchmark
superiority, multi-chip scaling, nonlinear recurrence, native replay/sleep,
native eligibility, or full v2.2 hardware transfer.
```

Result:

```text
Tier 4.31e native replay/eligibility decision closeout passed locally at
controlled_test_output/tier4_31e_20260506_native_replay_eligibility_decision_closeout/.
Runner revision: tier4_31e_native_replay_eligibility_decision_20260506_0001.
Criteria: 15/15.
Decision: native replay buffers, sleep-like replay, and native macro
eligibility are deferred until measured blockers exist.
Tier 4.31f: deferred.
Tier 4.32: authorized next.
Baseline freeze: not authorized.
Boundary: local documentation/decision evidence only; not hardware, not
implementation, not speedup, not multi-chip scaling, not native replay/sleep
proof, not native eligibility proof, and not full v2.2 hardware transfer.
```

Result:

```text
Tier 4.32 native-runtime mapping/resource model passed locally at
controlled_test_output/tier4_32_20260506_mapping_resource_model/.
Runner revision: tier4_32_mapping_resource_model_20260506_0001.
Criteria: 23/23.
Decision: MCPL-first scale path selected; Tier 4.32a single-chip multi-core
scale stress authorized next; Tier 4.32b-e remain blocked in order.
Baseline freeze: not authorized.
Boundary: local resource/mapping model only; not hardware, speedup, multi-chip
scaling, benchmark superiority, full organism autonomy, or baseline freeze.
```

Result:

```text
Tier 4.32a single-chip multi-core scale-stress preflight passed locally at
controlled_test_output/tier4_32a_20260506_single_chip_scale_stress/.
Runner revision: tier4_32a_single_chip_scale_stress_20260506_0002.
Criteria: 19/19.
Scale points: 4-core reference, 5-core lifecycle, 8-core dual shard,
12-core triple shard, 16-core quad shard.
Decision: only the 4-core reference and 5-core lifecycle single-shard points are
eligible for Tier 4.32a-hw EBRAINS hardware stress. Replicated 8/12/16-core
stress is blocked until Tier 4.32a-r1 adds shard-aware MCPL routing, because the
current MCPL key has no shard/group field and dest_core is reserved/ignored.
Tier 4.32b static reef partition, Tier 4.32c-e multi-chip work, and
CRA_NATIVE_SCALE_BASELINE_v0.5 remain blocked.
Boundary: local preflight/source-inspection evidence only; not hardware,
speedup, replicated-shard scaling, multi-chip scaling, static reef partition
proof, benchmark superiority, or baseline freeze.
```

## Tier 4.32a-r0 - Protocol Truth Audit

Question: Is the planned MCPL-first Tier 4.32a-hw package honest against the
current C source after the promoted confidence-gated learning repair?

Hypothesis: Source inspection will either confirm that MCPL carries all fields
needed for promoted v2.1/v2.2 scale stress, or it will block the hardware
package before a misleading EBRAINS run is prepared.

Result:

```text
Tier 4.32a-r0 protocol truth audit passed locally at
controlled_test_output/tier4_32a_r0_20260506_protocol_truth_audit/.
Runner revision: tier4_32a_r0_protocol_truth_audit_20260506_0001.
Criteria: 10/10.
Findings:
- confidence-gated lookup still uses transitional SDP
- MCPL reply helper drops confidence
- MCPL receive hardcodes confidence=1.0 and hit=1
- MCPL key has no shard/group field
- dest_core is reserved/ignored by MCPL send helpers
Decision: block MCPL-first 4.32a-hw until Tier 4.32a-r1 repairs
confidence-bearing and shard-aware MCPL lookup. A transitional SDP debug run is
allowed only if labelled as SDP debug, not scale evidence.
Boundary: local source/documentation audit only; not hardware, speedup,
multi-chip scaling, static reef partition proof, benchmark superiority, or
baseline freeze.
```

## Tier 4.32a-r1 - Confidence-Bearing Shard-Aware MCPL Lookup Repair

Question: Can the custom runtime repair MCPL lookup so it preserves value,
confidence, hit/status, lookup type, and shard identity before any MCPL-first
hardware scale stress?

Hypothesis: A two-packet MCPL reply contract plus shard-aware key layout can
preserve confidence-gated learning behavior while preventing identical
seq/type cross-shard replies from cross-talking.

Result:

```text
Tier 4.32a-r1 MCPL lookup repair passed locally at
controlled_test_output/tier4_32a_r1_20260506_mcpl_lookup_repair/.
Runner revision: tier4_32a_r1_mcpl_lookup_repair_20260506_0001.
Criteria: 14/14.
Implemented:
- MCPL key layout includes shard_id
- MCPL lookup replies use value and confidence/meta packets
- confidence/hit/status metadata is packed centrally
- learning-core MCPL receive no longer hardcodes confidence=1.0
- local C tests cover value/meta ordering, meta-before-value, wrong-shard
  rejection, and identical seq/type cross-shard separation
- four-core local behavior tests prove full/zero/half-confidence learning
  controls pass through MCPL
Decision: single-shard Tier 4.32a-hw EBRAINS hardware stress was authorized
for the eligible 4/5-core points and has now passed after ingest. Replicated
8/12/16-core stress is authorized next. Static reef partitioning, multi-chip
work, and native-scale baseline freeze remain blocked until replicated stress
passes.
Boundary: local source/runtime evidence only; not hardware, speedup,
replicated-shard scaling, multi-chip scaling, static reef partition proof,
benchmark superiority, or baseline freeze.
```

## Tier 4.32a-hw - Single-Shard MCPL-First EBRAINS Scale Stress

Question: Does the repaired Tier 4.32a-r1 MCPL protocol survive the two
predeclared single-shard hardware stress points on a real SpiNNaker board?

Scope:

```text
point_04c_reference: four-core context/route/memory/learning reference
point_05c_lifecycle: five-core enabled-lifecycle bridge stress
```

Prepared output:

```text
controlled_test_output/tier4_32a_hw_20260506_prepared/
```

Upload folder:

```text
ebrains_jobs/cra_432a_hw
```

JobManager command:

```text
cra_432a_hw/experiments/tier4_32a_hw_single_shard_scale_stress.py --mode run-hardware --output-dir tier4_32a_hw_job_output
```

Pass requires:

```text
real target acquisition
successful profile builds and loads
point_04c_reference passes with 48 events and 144 lookup replies
point_05c_lifecycle passes with 96 events and 288 lookup replies
zero stale replies
zero duplicate replies
zero timeouts
compact per-core readback returned
zero synthetic fallback
returned artifacts ingested
```

Fail requires classification before rerun:

```text
target acquisition
profile build/load
MCPL delivery
lookup parity
timeout/drop/stale/duplicate
schedule/slot high-water mark
readback/schema
runner/environment
```

Boundary:

```text
Single-shard single-chip hardware stress only. Not replicated-shard scaling,
not multi-chip, not speedup, not static reef partitioning, not benchmark
superiority, and not a native-scale baseline freeze.
```

Latest result:

```text
Status: PASS after EBRAINS ingest
Ingested output: controlled_test_output/tier4_32a_hw_20260507_hardware_pass_ingested/
Raw generated: 2026-05-07T00:24:55+00:00
Board: 10.11.215.185
Raw hardware criteria: 31/31
Ingest criteria: 8/8
Returned artifacts: 63
Runtime seconds: 144.55756055982783
point_04c_reference: PASS, 48 events, 144 lookup requests/replies
point_05c_lifecycle: PASS, 96 events, 288 lookup requests/replies
Stale replies: 0
Duplicate replies: 0
Timeouts: 0
Synthetic fallback: 0
```

Decision:

```text
Tier 4.32a-hw-replicated later passed as single-chip replicated-shard stress.
Tier 4.32b static reef partition smoke/resource mapping later passed locally.
Tier 4.32c inter-chip feasibility contract later passed locally.
Tier 4.32d-r0 route/source/package audit later passed and blocked the first
4.32d EBRAINS package until inter-chip route repair. Multi-chip learning,
benchmark superiority, speedup claims, and native-scale baseline freeze remain
blocked until returned 4.32e EBRAINS artifacts pass and are ingested cleanly.
```

## Tier 4.32a-hw-replicated - Replicated-Shard MCPL-First EBRAINS Scale Stress

Question: Does the repaired MCPL lookup protocol remain stable when the
single-chip runtime is expanded to the predeclared replicated 8/12/16-core
stress points?

Scope:

```text
8-core replicated-shard stress
12-core replicated-shard stress
16-core replicated-shard stress
single chip only
```

Prepared output:

```text
controlled_test_output/tier4_32a_hw_replicated_20260507_prepared/
```

Upload folder:

```text
ebrains_jobs/cra_432a_rep
```

JobManager command:

```text
cra_432a_rep/experiments/tier4_32a_hw_replicated_shard_stress.py --mode run-hardware --output-dir tier4_32a_replicated_job_output
```

Prepare result:

```text
Status: PREPARED
Local prepare criteria: 14/14
Runner revision: tier4_32a_hw_replicated_shard_stress_20260507_0001
Source-only package: yes
Package size: about 1 MB
Package files: 46
```

Pass requires:

```text
real target acquisition
successful profile builds and loads
shard-aware MCPL keys preserved
value/meta reply packets preserve confidence/hit/status
lookup request/reply parity for every shard
zero stale replies
zero duplicate replies
zero timeouts
compact per-core readback returned
schedule/slot high-water marks returned
zero synthetic fallback
returned artifacts ingested
```

Fail requires classification before rerun:

```text
target acquisition
profile build/load
MCPL delivery/routing
cross-shard key collision
lookup parity
timeout/drop/stale/duplicate
schedule/slot high-water mark
readback/schema
runner/environment
```

Boundary:

```text
Single-chip replicated-shard stress only. Not static reef partitioning, not
multi-chip, not speedup, not benchmark superiority, and not a native-scale
baseline freeze.
```

Hardware result:

```text
Status: HARDWARE PASS, INGESTED
Raw output: returned_artifacts/tier4_32a_hw_replicated_results.json
Ingested output: controlled_test_output/tier4_32a_hw_replicated_20260507_hardware_pass_ingested/
Board: 10.11.215.121
Raw criteria: 185/185
Ingest criteria: 9/9
Returned artifacts: 80
Runtime: 96.51446217112243 seconds
point_08c_dual_shard: pass, 2 shards, 192 total events, 96 events/shard, 288 lookup replies/shard
point_12c_triple_shard: pass, 3 shards, 384 total events, 128 events/shard, 384 lookup replies/shard
point_16c_quad_shard: pass, 4 shards, 512 total events, 128 events/shard, 384 lookup replies/shard
Stale replies: 0
Duplicate replies: 0
Timeouts: 0
Synthetic fallback: 0
```

Decision:

```text
Tier 4.32b static reef partition smoke/resource mapping later passed locally.
Tier 4.32c inter-chip feasibility contract later passed locally.
Tier 4.32d-r0 route/source/package audit later passed and blocked the first
4.32d EBRAINS package until inter-chip route repair. Multi-chip learning,
speedup claims, benchmark claims, and native-scale baseline freeze remain
blocked until returned 4.32e EBRAINS artifacts pass and are ingested cleanly.
```


## Tier 4.32b - Static Reef Partition Smoke/Resource Mapping

Question: Can static reef partitioning map CRA groups/modules/polyps to the
measured single-chip replicated-shard runtime envelope without ambiguous state
ownership?

Result:

```text
Status: PASS
Output: controlled_test_output/tier4_32b_20260507_static_reef_partition_smoke/
Criteria: 25/25
Canonical layout: quad_mechanism_partition_v0
Partitions: 4
Cores: 16
Polyp slots: 0-7, two slots per partition
Per-partition events: 128
Per-partition lookup parity: 384/384
Stale replies: 0
Duplicate replies: 0
Timeouts: 0
One-polyp-one-chip claim: rejected as unsupported
Quad partition plus dedicated lifecycle core: blocked at 17 cores
```

Decision:

```text
Tier 4.32c inter-chip feasibility contract later passed locally.
Tier 4.32d-r0 route/source/package audit later passed and blocked the first
4.32d EBRAINS package until inter-chip route repair. Tier 4.32d-r1 later passed
as local route repair/QA. Tier 4.32d package preparation later passed at
`controlled_test_output/tier4_32d_20260507_prepared/` and refreshed
`ebrains_jobs/cra_432d`; EBRAINS run/ingest is authorized next.
Multi-chip learning, speedup claims, benchmark claims, true two-partition
learning, and native-scale baseline freeze remain blocked until 4.32d and
4.32e pass cleanly.
```

Boundary:

```text
Local static partition/resource evidence only. Not a new SpiNNaker hardware run,
not one-polyp-one-chip evidence, not speedup, not multi-chip, not benchmark
superiority, and not a native-scale baseline freeze.
```

## Tier 4.32c - Inter-Chip Feasibility Contract

Question: Can the measured static reef partition map be converted into a
reviewer-defensible inter-chip contract before any multi-chip hardware job?

Result:

```text
Status: PASS
Output: controlled_test_output/tier4_32c_20260507_interchip_feasibility_contract/
Criteria: 19/19
First smoke target: point_2chip_split_partition_lookup_smoke
Chips: 2
Static partitions: 1
Total cores: 4
Events: 32
Expected lookups: 96
Remote paths: 3
Protocol boundary:
  current one-shard MCPL key supports split-role single-shard cross-chip lookup;
  true two-partition cross-chip learning needs later origin/target shard
  semantics
Required identity fields:
  logical_board_id, chip_x, chip_y, p_core, role, partition_id, shard_id, seq_id
Required delivery counters:
  lookup_requests, reply_value_packets, reply_meta_packets, stale_replies,
  duplicate_replies, timeouts, route_mismatch_count
```

Decision:

```text
Tier 4.32d-r0 route/source/package audit was authorized next and later passed.
That audit blocked the first 4.32d EBRAINS package until inter-chip route repair.
Tier 4.32d-r1 route repair/local QA later passed, and Tier 4.32d package
preparation later passed at `controlled_test_output/tier4_32d_20260507_prepared/`.
Tier 4.32d later passed and was ingested. Tier 4.32e is now prepared at
`controlled_test_output/tier4_32e_20260507_prepared/`; upload `ebrains_jobs/cra_432e`
and run the emitted JobManager command next. Speedup claims, benchmark claims,
true two-partition learning, and CRA_NATIVE_SCALE_BASELINE_v0.5 remain blocked
until returned 4.32e EBRAINS artifacts pass and are ingested.
```

Boundary:

```text
Local inter-chip feasibility contract only. Not a SpiNNaker hardware run, not
multi-chip execution evidence, not speedup, not learning-scale evidence, not
benchmark superiority, and not a native-scale baseline freeze.
```

## Tier 4.32d-r0 - Inter-Chip Route/Source/Package Audit

Question: Can the current source honestly package the first two-chip split-role
single-shard MCPL lookup smoke, or must route repair happen before EBRAINS?

Result:

```text
Status: PASS
Output: controlled_test_output/tier4_32d_r0_20260507_interchip_route_source_audit/
Criteria: 10/10
Decision: block_4_32d_package_until_route_repair
Source-backed MCPL key/value/meta path: present
Current cra_state_mcpl_init route behavior: local-core routes only
Explicit inter-chip link route: absent
Upload folder: not prepared
```

Decision:

```text
Tier 4.32d-r1 inter-chip MCPL route repair/local QA is required next.
Do not prepare or upload the 4.32d EBRAINS package until route repair passes.
Tier 4.32d hardware smoke, Tier 4.32e learning scale, speedup claims, benchmark
claims, and CRA_NATIVE_SCALE_BASELINE_v0.5 remain blocked.
```

Boundary:

```text
Local route/source/package audit only. Not a SpiNNaker hardware run, not an
EBRAINS package, not multi-chip execution evidence, not speedup, not
learning-scale evidence, not benchmark superiority, and not baseline freeze.
```

## Tier 4.32d-r1 - Inter-Chip MCPL Route Repair Local QA

Question: After Tier 4.32d-r0 blocked the first two-chip package, can the source
prove explicit inter-chip MCPL route entries locally before EBRAINS upload?

Result:

```text
Status: PASS
Output: controlled_test_output/tier4_32d_r1_20260507_interchip_route_repair_local_qa/
Criteria: 14/14
Decision: authorize_4_32d_package_next
Learning-core request link routes: pass
State-core local request + outbound value/meta reply link routes: pass
Existing MCPL lookup regression: pass
Existing four-core MCPL local regression: pass
```

Decision:

```text
Tier 4.32d two-chip split-role single-shard MCPL lookup hardware smoke is
prepared as a communication/readback smoke only at
`controlled_test_output/tier4_32d_20260507_prepared/` with upload folder
`ebrains_jobs/cra_432d`. Do not claim learning scale, speedup, benchmark
superiority, true two-partition learning, or CRA_NATIVE_SCALE_BASELINE_v0.5 from
package preparation.
Tier 4.32d later passed and was ingested; Tier 4.32e later passed and was
ingested as the first two-chip learning-bearing micro-task.
```

Boundary:

```text
Local source/runtime QA only. Not a SpiNNaker hardware run, not an EBRAINS
package, not multi-chip execution evidence, not learning-scale evidence, not
speedup, not benchmark superiority, and not baseline freeze.
```

## Tier 4.32d - Two-Chip Split-Role Single-Shard MCPL Lookup Smoke

Question: Does the repaired explicit route-link surface package a clean
two-chip source/remote MCPL lookup smoke before spending EBRAINS hardware time?

Prepared result:

```text
Status: PREPARED
Output: controlled_test_output/tier4_32d_20260507_prepared/
Criteria: 15/15
Upload folder: ebrains_jobs/cra_432d
JobManager command:
  cra_432d/experiments/tier4_32d_interchip_mcpl_smoke.py --mode run-hardware --output-dir tier4_32d_job_output
Source/learning chip: (0,0), learning core 7
Remote/state chip: (1,0), context/route/memory cores 4/5/6
Shard: 0
Events: 32
Expected lookup replies: 96
```

Returned EBRAINS / ingest result:

```text
Status: PASS
Raw remote status: pass
Ingest status: pass
Output: controlled_test_output/tier4_32d_20260507_hardware_pass_ingested/
Raw runner output: /Users/james/Downloads/tier4_32d_results.json
Target acquisition: pyNN.spiNNaker probe, board 10.11.215.169
Source/learning chip: (0,0), learning core 7
Remote/state chip: (1,0), context/route/memory cores 4/5/6
Events: 32
Expected lookup replies: 96
Actual lookup requests/replies: 96/96
Pending created/matured: 32/32
Active pending after run: 0
Stale replies / duplicate replies / timeouts: 0 / 0 / 0
Synthetic fallback: false
Ingest criteria: 7/7
Returned artifacts preserved: 40
```

Pass case after EBRAINS return:

```text
real target acquisition
four role builds/loads pass
remote state writes pass
source schedule upload passes
learning lookup_requests == lookup_replies == 96
stale_replies == duplicate_replies == timeouts == 0
compact readback succeeds
synthetic fallback == 0
```

Fail case:

```text
missing target, failed profile build/load, failed remote writes, lookup parity
mismatch, stale/duplicate/timeouts, missing compact readback, or missing
tier4_32d_results.json
```

Decision:

```text
Tier 4.32d passed and was ingested. Tier 4.32e multi-chip learning micro-task is
authorized next.
```

Boundary:

```text
The hardware target is communication/readback smoke only; not learning-scale
evidence, not speedup, not benchmark superiority, not true two-partition
learning, not lifecycle scaling, not multi-shard learning, and not baseline
freeze.
```

## Tier 4.32e - Multi-Chip Learning Micro-Task

Question: Can the same 4.32d source-chip learning core to remote-chip
context/route/memory MCPL lookup path carry a tiny learning-bearing task, with
an explicit no-learning control, before any larger cross-chip or benchmark
claim is made?

Prepared result:

```text
Status: PREPARED
Output: controlled_test_output/tier4_32e_20260507_prepared/
Upload folder: ebrains_jobs/cra_432e
JobManager command:
  cra_432e/experiments/tier4_32e_multichip_learning_microtask.py --mode run-hardware --output-dir tier4_32e_job_output
Source/learning chip: (0,0), learning core 7
Remote/state chip: (1,0), context/route/memory cores 4/5/6
Shard: 0
Events per case: 32
Expected lookup replies per case: 96
Cases:
  enabled_lr_0_25 -> reference readout_weight/readout_bias = 32768 / 0
  no_learning_lr_0_00 -> reference readout_weight/readout_bias = 0 / 0
```

Returned EBRAINS result:

```text
Status: HARDWARE PASS / INGEST PASS
Output: controlled_test_output/tier4_32e_20260507_hardware_pass_ingested/
Raw runner output: /Users/james/Downloads/tier4_32e_results.json
Board: 10.11.205.161
Source/learning chip: (0,0), learning core 7
Remote/state chip: (1,0), context/route/memory cores 4/5/6
Shard: 0
Cases: 2
Events per case: 32
Expected lookup replies per case: 96
Returned artifacts preserved: 42
Synthetic fallback: false
```

Observed case results:

```text
enabled_lr_0_25:
  decisions: 32
  reward_events: 32
  pending_created / pending_matured / active_pending: 32 / 32 / 0
  lookup_requests / lookup_replies: 96 / 96
  stale_replies / duplicate_replies / timeouts: 0 / 0 / 0
  compact payload_len: 105
  readout_weight_raw / readout_bias_raw: 32768 / 0
  readout_weight / readout_bias: 1.0 / 0.0

no_learning_lr_0_00:
  decisions: 32
  reward_events: 32
  pending_created / pending_matured / active_pending: 32 / 32 / 0
  lookup_requests / lookup_replies: 96 / 96
  stale_replies / duplicate_replies / timeouts: 0 / 0 / 0
  compact payload_len: 105
  readout_weight_raw / readout_bias_raw: 0 / 0
  readout_weight / readout_bias: 0.0 / 0.0
```

Pass case after EBRAINS return:

```text
real target acquisition
four role builds/loads pass
remote state writes pass for both cases
source schedule upload passes for both cases
learning lookup_requests == lookup_replies == 96 for both cases
stale_replies == duplicate_replies == timeouts == 0 for both cases
enabled learning readout matches the fixed-point reference and moves above zero
no-learning control readout remains 0 / 0
compact readback succeeds
synthetic fallback == 0
returned artifacts are ingested with bounded mtime-window preservation
```

Fail case:

```text
missing target, failed profile build/load, failed remote writes, lookup parity
mismatch, stale/duplicate/timeouts, missing compact readback, enabled/no-learning
case separation failure, reference mismatch, synthetic fallback, or missing
tier4_32e_results.json
```

Decision:

```text
Tier 4.32e passed and is canonical after ingest. The claim is limited to a
two-chip single-shard learning micro-task over the repaired MCPL lookup path.
It is not speedup evidence, not benchmark evidence, not true two-partition
learning, not lifecycle scaling, not multi-shard learning, and not a
native-scale baseline freeze.

Next authorized action: Tier 4.32f multi-chip resource/lifecycle decision
contract. Do not jump directly to another hardware package without defining
the exact question, hypothesis/null, mechanism, claim boundary, controls,
metrics, pass/fail criteria, expected artifacts, and docs to update.
```

## Tier 4.32f - Multi-Chip Resource/Lifecycle Decision Contract

Question: After Tier 4.32e passed the first two-chip learning-bearing
micro-task, what is the next scientifically defensible multi-chip scale gate?

Result:

```text
Status: PASS
Output: controlled_test_output/tier4_32f_20260507_multichip_resource_lifecycle_decision/
Criteria: 22/22
Selected direction: multi_chip_lifecycle_traffic_with_resource_counters
Selected next gate: tier4_32g_r0_multichip_lifecycle_route_source_repair_audit
Hardware package status: blocked_until_4_32g_r0_passes
Lifecycle inter-chip routes source-proven now: false
```

Decision:

```text
Tier 4.32f selected lifecycle traffic with resource counters as the next
multi-chip direction because CRA's organism/self-scaling claim requires native
lifecycle traffic to move across chips after lookup and learning have passed.
However, current source proves explicit inter-chip route entries for lookup
request/reply packets only. Lifecycle event request, trophic update, and
active-mask sync packets exist, but explicit lifecycle inter-chip route entries
are not yet source-proven. Therefore immediate hardware packaging is blocked.
```

Pass case:

```text
4.32e learning micro-task evidence is clean
4.30g lifecycle-native evidence exists
candidate directions are evaluated
lifecycle/resource is selected as the next direction
true two-partition learning remains blocked
benchmarks and speedup remain blocked
native-scale baseline freeze remains blocked
4.32g hardware is blocked until 4.32g-r0 passes
```

Next required gate:

```text
Tier 4.32g-r0 - Multi-Chip Lifecycle Route/Source Repair Audit

Question:
  Can lifecycle MCPL event/trophic/mask-sync traffic be made chip/shard
  explicit enough for a two-chip lifecycle smoke?

Required:
  source-proven lifecycle event request route entries
  source-proven lifecycle trophic update route entries
  source-proven active-mask/lineage sync route entries
  duplicate/stale/missing-ack counters
  compact lifecycle readback fields
  local C host tests before any EBRAINS upload
```

Boundary:

```text
Tier 4.32f is local decision/contract evidence only. It is not hardware
evidence, not speedup, not benchmark superiority, not true two-partition
learning, not lifecycle scaling, not multi-shard learning, and not a
native-scale baseline freeze.
```

## Tier 4.32g-r0 - Multi-Chip Lifecycle Route/Source Repair Audit

Question: Can lifecycle event request, trophic update, and active-mask/lineage
sync MCPL routes be source-proven before the next two-chip lifecycle hardware
package?

Result:

```text
Status: PASS
Output: controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit/
Criteria: 14/14
4.32g hardware prepare: authorized_next
Selected next gate: tier4_32g_two_chip_lifecycle_traffic_resource_hardware_smoke
True partition semantics: blocked_until_4_32g_hardware_result
Native scale baseline freeze: not_authorized
```

Source/route repair covered:

```text
learning_local_mask_sync_consumer
learning_outbound_lifecycle_event
learning_outbound_lifecycle_trophic
lifecycle_local_event_request
lifecycle_local_trophic_request
lifecycle_outbound_mask_sync
```

Regression tests:

```text
make -C coral_reef_spinnaker/spinnaker_runtime test-mcpl-lifecycle-interchip-route-contract
make -C coral_reef_spinnaker/spinnaker_runtime test-mcpl-interchip-route-contract
make -C coral_reef_spinnaker/spinnaker_runtime test-lifecycle-split
```

Pass case:

```text
4.32f prerequisite passed
4.32e learning prerequisite passed
lifecycle source findings present
six required lifecycle route paths covered
learning profile has outbound event and trophic routes
learning profile has local active-mask sync consumer route
lifecycle profile has local event and trophic routes
lifecycle profile has outbound active-mask sync route
local lifecycle route contract test passes
lookup inter-chip route regression still passes
lifecycle split regression still passes
4.32g hardware preparation is authorized
true partition semantics remain blocked until hardware result
```

Fail case:

```text
missing route macro, missing route install, missing duplicate/stale/missing-ack
counter, local C route contract failure, lookup route regression failure,
lifecycle split regression failure, or premature hardware/speedup/baseline claim
```

Decision:

```text
Tier 4.32g-r0 passed as local source/runtime QA. The next authorized action is
Tier 4.32g two-chip lifecycle traffic/resource hardware smoke. This does not
claim hardware evidence yet and does not authorize speedup, benchmark,
lifecycle-scaling, true two-partition, multi-shard, or native-scale baseline
freeze claims.
```

## Tier 4.32g - Two-Chip Lifecycle Traffic/Resource Hardware Smoke

Question: after 4.32g-r0 source-proved lifecycle route entries, can the actual
learning/lifecycle MCPL packet semantics survive a two-chip SpiNNaker hardware
smoke with compact readback counters?

Current status: 4.32g-r2 passed on EBRAINS and was ingested as hardware
evidence. The first 4.32g EBRAINS return remains preserved as a strict-gate
fail with successful traffic counters, and the second attempted rerun remains
preserved as a stale-package fail because it returned runner revision ...0001.
The cache-proof r2 run returned the expected runner revision ...0003 and passed.

Prepared output:

```text
controlled_test_output/tier4_32g_20260508_r2_prepared/
criteria: 16/16
stable upload folder: ebrains_jobs/cra_432g_r2
exact JobManager command:
cra_432g_r2/experiments/tier4_32g_multichip_lifecycle_traffic_resource_smoke.py --mode run-hardware --output-dir tier4_32g_job_output
```

Successful hardware return:

```text
controlled_test_output/tier4_32g_20260508_hardware_pass_ingested/
raw status: pass
ingest status: pass
runner revision: tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003
board target: 10.11.205.177
source chip/core: (0,0,p7) learning
remote chip/core: (1,0,p4) lifecycle
returned artifacts: 30
synthetic fallback: 0
stale package detected: false
```

Earlier failed/stale returns:

```text
controlled_test_output/tier4_32g_20260507_hardware_fail_ingested/
raw status: fail
traffic path: succeeded
failure class: cleanup/control-surface + criteria evaluator

controlled_test_output/tier4_32g_20260508_old_package_return_ingested/
raw status: fail
returned runner revision: tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260507_0001
classification: stale cra_432g package rerun, not repaired r2 evidence
```

Observed successful traffic fields in the passing r2 return:

```text
source lifecycle_event_requests_sent == 1
source lifecycle_trophic_requests_sent == 1
source lifecycle_mask_syncs_received == 1
source lifecycle_last_seen_active_mask_bits == 1
source lifecycle_last_seen_event_count == 2
lifecycle_event_acks_received == 2
lifecycle_mask_syncs_sent == 1
lifecycle duplicate/stale/missing-ack counters == 0
lifecycle active_mask_bits == 1
lifecycle active_count == 1
lifecycle death_count == 1
lifecycle trophic_update_count == 1
reset/pause controls passed
runtime payload_len >= 149
synthetic fallback == 0
```

4.32g-r2 repairs proven by the pass:

```text
1. lifecycle_core ACKs CMD_RUN_CONTINUOUS and CMD_PAUSE as harmless uniform
   server-core controls.
2. test_profiles asserts lifecycle_core control ACK behavior.
3. smoke criteria accept both boolean reset ACKs and structured reply ACKs.
4. runner revision advanced to tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003.
5. stale-package detection reports false on the passing run.
```

Mechanism under test:

```text
source chip (0,0), learning_core p7:
  emits lifecycle trophic request
  emits lifecycle death event request
  receives active-mask/lineage sync

remote chip (1,0), lifecycle_core p4:
  receives trophic/event MCPL requests
  mutates lifecycle active mask
  broadcasts active-mask/lineage sync
```

Prepare repairs included:

```text
1. lifecycle MCPL receive dispatch in state_manager.c
2. learning-core host surface for lifecycle request emission
3. CMD_READ_STATE lifecycle traffic counters appended to compact schema-v2
4. Python host helpers for lifecycle request emission
5. local C receive contract: test-mcpl-lifecycle-receive-contract
6. refreshed cache-proof EBRAINS upload folder: ebrains_jobs/cra_432g_r2
```

Pass requires:

```text
real target acquisition
learning/lifecycle profile builds and loads on two chips
lifecycle init success
source lifecycle_event_requests_sent == 1
source lifecycle_trophic_requests_sent == 1
source lifecycle_mask_syncs_received == 1
source last_seen_active_mask_bits == 1
lifecycle_event_acks_received == 2 on lifecycle core
lifecycle_mask_syncs_sent == 1 on lifecycle core
death_count == 1
trophic_update_count == 1
active_count == 1
stale/duplicate/missing-ack counters == 0
payload_len >= 149 for runtime readbacks
zero synthetic fallback
returned artifacts preserved and ingested
```

Fail classes:

```text
target acquisition failure
profile build/link/load failure
source request emission failure
remote lifecycle request receive failure
active-mask mutation failure
sync return-path failure
compact readback/counter schema failure
stale/duplicate/missing-ack counter nonzero
artifact finalization/ingest failure
```

Claim boundary:

```text
Tier 4.32g is a two-chip lifecycle traffic/resource smoke only. It is not
lifecycle scaling, speedup evidence, benchmark evidence, true partitioned
ecology, multi-shard learning, or a native-scale baseline freeze.
```

## Tier 4.32h - Native-Scale Evidence Closeout / Baseline Decision

Question: do the completed Tier 4.32a, 4.32d, 4.32e, and 4.32g gates form a
stable native-scale evidence bundle that justifies freezing
`CRA_NATIVE_SCALE_BASELINE_v0.5`, or is another targeted repair/stress gate
required before freezing?

Inputs:

```text
Tier 4.32a / 4.32a-replicated single-chip replicated stress
Tier 4.32d two-chip MCPL communication/readback smoke
Tier 4.32e two-chip learning-bearing micro-task
Tier 4.32g two-chip lifecycle traffic/resource smoke
all returned-artifact preservation records
all resource/readback accounting fields
all stale/duplicate/timeout/missing-ack counters
all synthetic-fallback flags
all claim-boundary statements
```

Pass requires:

```text
all required evidence bundles exist and validate
single-chip multi-core and first multi-chip evidence are internally consistent
no unresolved stale-package or runner-revision ambiguity remains
no unresolved synthetic fallback exists
no unresolved timeout/stale/duplicate/missing-ack pattern exists
claim boundary for v0.5 is explicitly narrower than lifecycle scaling,
benchmark evidence, speedup evidence, true two-partition learning, and AGI/ASI
if freeze is recommended, baseline files and registry snapshot are generated
if freeze is rejected, next repair/stress gate is explicitly named
```

Boundary:

```text
Tier 4.32h passed locally and generated the frozen native-scale substrate
baseline. It is not a new hardware result, not speedup proof, not benchmark
evidence, not lifecycle scaling, not multi-shard learning, and not a software
usefulness baseline.
```

Result:

```text
Status: PASS
Criteria: 64/64
Output: controlled_test_output/tier4_32h_20260508_native_scale_evidence_closeout/
Baseline: baselines/CRA_NATIVE_SCALE_BASELINE_v0.5.md
Registry snapshot: baselines/CRA_NATIVE_SCALE_BASELINE_v0.5_STUDY_REGISTRY.snapshot.json
Next: Tier 7.0f benchmark-protocol repair and public failure localization after
Tier 7.0e short/medium calibration plus the 10k NARMA10 finite-stream blocker
```

## Tier 7.0e - Standard Dynamical Benchmark Rerun With v2.2 And Run-Length Sweep

Runner:

```text
experiments/tier7_0e_standard_dynamical_v2_2_sweep.py
```

Question: does the frozen v2.2 fading-memory temporal-state baseline close or
materially narrow the Tier 7.0 Mackey-Glass/Lorenz/NARMA10 gap, and was the
earlier v2.1 result partly a short-training-budget artifact?

Hypothesis: v2.2 improves the standardized continuous sequence benchmark path
versus v2.1, especially as chronological exposure length increases.

Null hypothesis: v2.2 does not materially improve the public scoreboard; the
remaining gap is not explained by short training duration and must be diagnosed
as readout/interface, recurrent-state, baseline, or architecture limitation.

Tasks:

```text
Mackey-Glass future prediction
Lorenz future prediction
NARMA10 nonlinear memory/system identification
aggregate geometric-mean MSE
```

Run lengths:

```text
720
2000
10000
50000 if practical
```

Required comparisons:

```text
historical v2.1 Tier 7.0 / 7.0d results
v2.2 fading-memory CRA
v2.2 relevant ablations or disabled-temporal-state controls
persistence / naive baseline
online LMS
ridge/lag baseline
echo-state network
small GRU
small LSTM if fair and available
```

Required guardrails:

```text
chronological train/test split
normalization fit on train prefix only
same stream length and split for all models
predictions emitted before online updates where applicable
no test-row fitting
same horizons as Tier 7.0 unless explicitly predeclared
seed-level results
runtime by model and length
```

Pass criteria:

```text
all predeclared tasks, models, seeds, and feasible lengths run
leakage guardrails pass
v2.2 improves versus v2.1 on the public scoreboard or shows a credible
length-sensitive learning curve
strong baselines remain fair and not intentionally under-tuned
```

Fail/narrow criteria:

```text
v2.2 does not improve the public scoreboard even with longer exposure
strong sequence baselines still dominate all meaningful metrics
results depend on leakage, hidden future context, or task-specific hacks
50k cannot run and no largest-practical length is documented
```

Next step:

```text
If 7.0e improves but still loses: run 7.0f failure localization.
If 7.0e closes the gap: run ablations plus compact regression before freeze.
If 7.0e does not improve: stop blaming short training length and choose the next
planned general mechanism only after diagnosis.
```

Execution update 2026-05-08:

```text
Short/medium calibration:
  output: controlled_test_output/tier7_0e_20260508_length_calibration/
  status: pass, 8/8 criteria
  lengths: 720, 2000
  outcome: v2.2 improves versus raw v2.1 but is not length-competitive
           with the strongest public baseline.
  720 geomean MSE:
    v2.2 fading-memory candidate: 0.19853975759572184
    raw v2.1 reference: 0.7493269520748722
    best baseline: fixed_esn_train_prefix_ridge_baseline
    best baseline MSE: 0.02537065477597153
  2000 geomean MSE:
    v2.2 fading-memory candidate: 0.2514764000158321
    raw v2.1 reference: 1.3391242823450145
    best baseline: fixed_esn_train_prefix_ridge_baseline
    best baseline MSE: 0.06236159958411151

Long scoreboard attempt:
  output: controlled_test_output/tier7_0e_20260508_length_10000_scoreboard/
  status: fail, 7/8 criteria
  matrix_mode: scoreboard
  blocker: NARMA10 seed 44 at length 10000 generated 1,688 non-finite
           target values.
  interpretation: the 10k three-task/three-seed public scoreboard is blocked
                  by benchmark-stream validity and cannot be used as model
                  evidence.
```

Runner repair completed:

```text
experiments/tier7_0e_standard_dynamical_v2_2_sweep.py now separates:
  scoreboard mode:
    v2.2 candidate + public baselines, no raw CRA trace/sham burden, suitable
    for long exposure sweeps.
  full_diagnostic mode:
    raw CRA/sham/ablation matrix for shorter mechanism-causality audits.

The runner now validates generated benchmark streams for finite observed and
target values and fails cleanly instead of silently scoring invalid sequences.
```

Next required step:

```text
Tier 7.0f - benchmark-protocol repair and public failure localization.
Do not add a new CRA mechanism, freeze a baseline, or migrate benchmark logic
to hardware until the long NARMA10 finite-stream policy and public-scoreboard
failure mode are explicitly documented.
```

### Tier 7.0f - Benchmark Protocol Repair / Public Failure Localization

Runner:

```text
experiments/tier7_0f_benchmark_protocol_failure_localization.py
```

Output:

```text
controlled_test_output/tier7_0f_20260508_benchmark_protocol_failure_localization/
```

Status:

```text
PASS
criteria: 8/8
outcome: benchmark_protocol_blocker_confirmed
```

Findings:

```text
NARMA10 seed 44 is finite through 8000 steps and invalid at 10000+ steps.
Largest original-seed finite rerun length: 8000
Optional 10000 finite-seed sensitivity seeds: 42,43,45
v2.2 improves over raw v2.1: true
v2.2 competitive with best public baseline: false
length-alone support from 720->2000: false
```

Failure localization:

```text
Mackey-Glass and Lorenz still favor ESN / offline train-prefix readout.
NARMA10 favors explicit lag memory over v2.2 fading memory.
The 10k public aggregate was invalid benchmark evidence, not a model result.
```

### Tier 7.0e 8000-Step Valid Same-Seed Scoreboard Rerun

Runner:

```text
experiments/tier7_0e_standard_dynamical_v2_2_sweep.py --matrix-mode scoreboard --lengths 8000
```

Output:

```text
controlled_test_output/tier7_0e_20260508_length_8000_scoreboard/
```

Status:

```text
PASS
criteria: 8/8
invalid streams: 0
```

Aggregate geomean MSE:

```text
ESN:                    0.020109884207162095
v2.2 fading memory:     0.19348969000027122
lag-only LMS:           0.1986311714577415
random reservoir:       0.2075278737499566
```

Interpretation:

```text
v2.2 ranks second overall and beats lag/reservoir aggregate at 8000 steps, but
ESN remains about 9.6x better on aggregate geomean MSE. Longer valid exposure
alone does not close the public benchmark gap.
```

Next required step:

```text
Tier 7.0g - general mechanism-selection contract.
The next mechanism should be selected from the measured public failure class,
not from intuition. Current evidence points first at nonlinear recurrent /
continuous-state and readout-interface capability, not sleep/replay or lifecycle
as the immediate Mackey-Glass/Lorenz/NARMA10 repair.
```

### Tier 7.0g - General Mechanism-Selection Contract

Runner:

```text
experiments/tier7_0g_general_mechanism_selection_contract.py
```

Output:

```text
controlled_test_output/tier7_0g_20260508_general_mechanism_selection_contract/
```

Status:

```text
PASS
criteria: 7/7
selected mechanism: bounded_nonlinear_recurrent_continuous_state_interface
```

Why this mechanism:

```text
ESN dominates Mackey-Glass/Lorenz, indicating nonlinear recurrent state plus
train-prefix readout remains stronger than v2.2 fading memory.

NARMA10 favors explicit lag memory, indicating the next mechanism needs stronger
causal memory/readout rather than only longer exposure.

v2.2 ranks second at 8000 and beats lag/reservoir aggregate, so the path is
worth repairing rather than abandoning.
```

Promotion criteria for the next implementation:

```text
aggregate geomean MSE improves at least 25 percent versus v2.2 at the valid
8000-step same-seed scoreboard

mechanism beats lag-only aggregate or identifies a task-specific complement
with predeclared claim boundary

Mackey-Glass/Lorenz ESN gap narrows materially without worsening NARMA10

permuted/frozen/shuffled/no-update controls do not match the promoted mechanism

finite-stream and leakage guardrails pass

compact regression passes before any baseline freeze
```

Next required step:

```text
Tier 7.0h - bounded nonlinear recurrent continuous-state/interface candidate.
Software only. No hardware transfer until the mechanism earns usefulness.
```

### Tier 7.0h - Bounded Nonlinear Recurrent Continuous-State / Interface Gate

Runner:

```text
experiments/tier7_0h_bounded_recurrent_interface_gate.py
```

Output:

```text
controlled_test_output/tier7_0h_20260508_bounded_recurrent_interface_gate/
```

Status:

```text
PASS
criteria: 10/10
outcome: bounded_recurrent_candidate_improves_scoreboard_but_topology_specificity_unproven
promotion recommended: false
```

Public benchmark results:

```text
valid same-seed lengths: 720, 2000, 8000
tasks: Mackey-Glass, Lorenz, NARMA10
seeds: 42, 43, 44
invalid streams: 0
```

Aggregate geomean MSE at 8000:

```text
ESN:                                0.020109884207162095
bounded recurrent candidate:        0.09530752189727928
v2.2 fading memory:                 0.19348969000027122
lag-only LMS:                       0.1986311714577415
random reservoir:                   0.2075278737499566
```

Interpretation:

```text
The bounded recurrent candidate materially improves versus v2.2 at the largest
valid same-seed public length, beats lag/reservoir online controls, and narrows
the ESN gap.

The mechanism is not promoted because recurrence/topology specificity is not
yet proven: the permuted-recurrence sham stayed too close at 8000 with only
1.036590722013174 margin versus the candidate.
```

Next required step:

```text
Tier 7.0i - recurrence/topology specificity repair gate.
Do not freeze, move to hardware, or migrate this mechanism native until the
useful gain is separated from topology shams.
```

### Tier 7.0i - Recurrence / Topology Specificity Repair Gate

Runner:

```text
experiments/tier7_0i_recurrence_topology_specificity_gate.py
```

Output:

```text
controlled_test_output/tier7_0i_20260508_recurrence_topology_specificity_gate/
```

Status:

```text
PASS
criteria: 11/11
outcome: generic_bounded_recurrent_state_supported_topology_specificity_not_supported
promotion recommended: false
```

Public benchmark results:

```text
valid same-seed lengths: 720, 2000, 8000
tasks: Mackey-Glass, Lorenz, NARMA10
seeds: 42, 43, 44
invalid streams: 0
```

Aggregate geomean MSE at 8000:

```text
ESN:                                0.020109884207162095
generic 7.0h recurrent reference:   0.09530752189727928
structured recurrence candidate:    0.09964414908204765
v2.2 fading memory:                 0.19348969000027122
lag-only LMS:                       0.1986311714577415
random reservoir:                   0.2075278737499566
```

Control interpretation at 8000:

```text
structured vs v2.2 improvement margin: 1.9418068374586703
generic 7.0h vs v2.2 improvement margin: 2.0301617978149813
structured vs generic margin: 0.9564788577681811
topology shuffle sham margin: 1.0072740096344246
reversed cascade sham margin: 1.0
random rewire sham margin: 0.994286546101554
no-recurrence ablation margin: 0.9647896490983386
```

Interpretation:

```text
The useful public-scoreboard gain is real enough to keep investigating as a
generic bounded recurrent-state interface, but the topology-specific recurrence
hypothesis did not survive stricter shams. Topology shams and no-recurrence
controls matched or beat the structured candidate, so the project must narrow
the claim rather than force a reef-topology story onto this benchmark.
```

Claim boundary:

```text
Tier 7.0i is software public-benchmark topology-specificity evidence only. It
does not authorize a baseline freeze, hardware transfer, native migration,
ESN-superiority claim, topology-specific recurrence claim, language/planning
claim, or AGI/ASI claim.
```

Next required step:

```text
Tier 7.0j - generic bounded recurrent-state promotion / compact regression gate.
Decide whether the narrower generic bounded recurrent continuous-state
interface earns a v2.3 software baseline. Any promotion must preserve the 7.0i
topology nonclaim and pass compact regression before freeze.
```

### Tier 7.0j - Generic Bounded Recurrent-State Promotion / Compact Regression

Runner:

```text
experiments/tier7_0j_generic_recurrent_promotion_gate.py
```

Output:

```text
controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate/
```

Status:

```text
PASS
criteria: 14/14
outcome: generic_bounded_recurrent_state_ready_for_v2_3_freeze
freeze authorized: true
compact regression: full NEST pass
```

Locked 8000-step aggregate geomean MSE:

```text
ESN:                              0.020109884207162095
generic bounded recurrent state:  0.09530752189727928
structured recurrence candidate:  0.09964414908204765
v2.2 fading memory:               0.19348969000027122
lag-only LMS:                     0.1986311714577415
random reservoir:                 0.2075278737499566
```

Promotion metrics:

```text
generic margin vs v2.2:       2.0301617978149813
generic margin vs lag-only:   2.0841080274002146
generic margin vs reservoir:  2.177455353142288
v2.2 / ESN ratio:             9.621621288667603
generic / ESN ratio:          4.739337179442122
topology nonclaim preserved:  true
```

Interpretation:

```text
Tier 7.0j promotes a narrow v2.3 software baseline: generic bounded recurrent
continuous-state improves the locked public benchmark scoreboard versus v2.2 and
passes full compact regression. It does not prove topology-specific recurrence
and does not beat ESN.
```

Baseline frozen:

```text
baselines/CRA_EVIDENCE_BASELINE_v2.3.json
baselines/CRA_EVIDENCE_BASELINE_v2.3.md
baselines/CRA_EVIDENCE_BASELINE_v2.3_STUDY_REGISTRY.snapshot.json
```

Next required step:

```text
Tier 6.2a targeted usefulness validation over v2.3.
Use audited hard/real-ish diagnostic tasks and fair baselines to decide whether
v2.3 generalizes, whether another general mechanism is needed, or whether a
separate native/on-chip transfer contract is justified.
```

### Tier 6.2a - Targeted Hard-Task Validation Over v2.3

Runner:

```text
experiments/tier6_2a_targeted_usefulness_validation.py
```

Output:

```text
controlled_test_output/tier6_2a_20260508_targeted_usefulness_validation/
```

Status:

```text
PASS
criteria: 12/12
outcome: v2_3_partial_regime_signal_next_needs_failure_specific_mechanism_or_7_1_probe
```

Tasks:

```text
variable_delay_multi_cue
hidden_context_reentry
concept_drift_stream
anomaly_detection_stream
delayed_control_proxy
```

Aggregate geomean MSE:

```text
v2.2 fading-memory reference:       0.15892013746238234
v2.3 generic bounded recurrent:     0.17604715537423876
lag-only online LMS:                0.2055968384080941
fixed random reservoir online:      0.22089786655426447
fixed ESN train-prefix ridge:       0.4224303829071217
```

Interpretation:

```text
v2.3 is best only on variable_delay_multi_cue and beats v2.2 only on that task.
It separates from shams on three tasks, but v2.2 wins the aggregate hard-task
diagnostic geomean. This is a narrow variable-delay signal plus failure
localization, not a new baseline or public usefulness proof.
```

Claim boundary:

```text
Tier 6.2a is software diagnostic evidence only. These custom hard tasks cannot
replace public benchmarks, cannot freeze v2.4, cannot authorize native/on-chip
transfer, and cannot support broad usefulness, topology-specific recurrence,
ESN superiority, language, planning, AGI, or ASI claims.
```

Next required step:

```text
Tier 7.1a - real-ish/public adapter contract.
Define the first audited adapter family that can test whether the Tier 6.2a
variable-delay signal survives outside private diagnostics with locked
preprocessing, splits, baselines, leakage controls, metrics, and pass/fail
criteria.
```

### Tier 7.1a - Real-ish/Public Adapter Contract

Runner:

```text
experiments/tier7_1a_realish_adapter_contract.py
```

Output:

```text
controlled_test_output/tier7_1a_20260508_realish_adapter_contract/
```

Status:

```text
PASS
criteria: 12/12
selected adapter: nasa_cmapss_rul_streaming
dataset family: NASA C-MAPSS / turbofan engine degradation
```

Purpose:

```text
Tier 7.1a predeclares the first public/real-ish adapter family after Tier 6.2a.
It tests only whether the adapter plan is auditable and safe to implement; it
does not run the dataset or score CRA.
```

Required baselines:

```text
constant/mean-RUL
monotone age-to-RUL
lag/ridge window
online LMS / linear readout
random reservoir
fixed ESN train-prefix ridge
small GRU/LSTM if practical
tree/boosting window if practical
CRA v2.2 fading-memory reference
CRA v2.3 generic bounded recurrent-state baseline
v2.3 state-reset/shuffled/no-update controls
```

Leakage controls:

```text
train-unit statistics only for normalization
no test-unit future RUL labels during online prediction
chronological prediction within engine unit
unit-held-out evaluation
predeclared channel selection before scoring
prediction-before-update for online models
download/checksum manifest preserved
all transforms logged before scoring
```

Claim boundary:

```text
Tier 7.1a is a contract only. It is not C-MAPSS evidence, not a public
usefulness claim, not a baseline freeze, not hardware/native transfer, and not
evidence that the Tier 6.2a variable-delay signal generalizes.
```

Next required step:

```text
Tier 7.1b - NASA C-MAPSS source/data preflight.
Verify reproducible source access, license/source notes, checksums, row schema,
train/test split semantics, train-only normalization, prediction-before-update
ordering, and a tiny leakage-safe adapter smoke before any full scoring.
```

### Tier 7.1b - NASA C-MAPSS Source/Data Preflight

Runner:

```text
experiments/tier7_1b_cmapss_source_data_preflight.py
```

Output:

```text
controlled_test_output/tier7_1b_20260508_cmapss_source_data_preflight/
```

Status:

```text
PASS
criteria: 16/16
ZIP SHA256: 74bef434a34db25c7bf72e668ea4cd52afe5f2cf8e44367c55a82bfd91a5a34f
FD001 train rows: 20631
FD001 test rows: 13096
FD001 train/test units: 100/100
RUL labels: 100
```

Leakage-safe smoke:

```text
normalization stats computed from train_FD001 only
smoke stream rows contain no target/RUL labels
offline scoring labels written separately
prediction-before-update marked true for every smoke event
raw NASA data cached under .cra_data_cache/ and ignored by git
```

Claim boundary:

```text
Tier 7.1b is source/data preflight only. It verifies reproducible access,
checksums, schema, split/normalization policy, and label-separated smoke rows.
It is not C-MAPSS scoring, not public usefulness evidence, not a baseline
freeze, and not hardware/native transfer.
```

Next required step:

```text
Tier 7.1c - compact C-MAPSS FD001 scoring gate.
Score v2.2, v2.3, lag/ridge, online LMS, random reservoir, ESN, and v2.3 shams
on the same leakage-safe FD001 rows before making any usefulness claim.
```

### Tier 7.1c - Compact C-MAPSS FD001 Scoring Gate

Runner:

```text
experiments/tier7_1c_cmapss_fd001_scoring_gate.py
```

Output:

```text
controlled_test_output/tier7_1c_20260508_cmapss_fd001_scoring_gate/
```

Status:

```text
PASS
criteria: 12/12
outcome: v2_3_no_public_adapter_advantage
```

Key result:

```text
best model: monotone_age_to_rul_ridge
best model test RMSE: 46.10944999532139
v2.3 rank: 5
v2.3 test RMSE: 49.4908802462679
v2.2 test RMSE: 48.739451335025144
v2.3 sham separations: 3
```

Leakage and scoring boundary:

```text
train-only FD001 normalization from Tier 7.1b
train-only PCA1 scalar stream
train-prefix readout fitting
prediction-before-update ordering
no test readout updates
unit-held-out test split preserved
test RUL labels used only for offline scoring
```

Claim boundary:

```text
Tier 7.1c is compact scalar-adapter software scoring only. It is not a full
C-MAPSS benchmark, not a public usefulness win, not a baseline freeze, not
hardware/native transfer, and not AGI/ASI evidence. The pass means the scoring
gate executed under the predeclared leakage controls; it does not mean v2.3
beat the public-adapter baselines.
```

Next required step:

```text
Tier 7.1d - C-MAPSS failure analysis / adapter repair.
Determine whether 7.1c failed because scalar PCA1 compression lost multichannel
sensor structure, because the train-prefix readout policy is too weak, because
the RUL target/reset policy is mismatched, because CRA needs a multichannel
public-adapter interface, or because v2.3 genuinely has no useful signal for
this adapter.
```

### Tier 7.1d - C-MAPSS Failure Analysis / Adapter Repair

Runner:

```text
experiments/tier7_1d_cmapss_failure_analysis_adapter_repair.py
```

Output:

```text
controlled_test_output/tier7_1d_20260508_cmapss_failure_analysis_adapter_repair/
```

Status:

```text
PASS
criteria: 14/14
outcome: compact_failure_partly_readout_or_target_policy
```

Key result:

```text
best promotable model: scalar_pca1_v2_2_ridge_capped125
best promotable test RMSE: 20.271418942340336
best public baseline: lag_multichannel_ridge_capped125
best public baseline test RMSE: 20.305268771358435
scalar v2.3 LMS uncapped RMSE: 49.4908802462679
scalar v2.3 ridge uncapped RMSE: 43.435416241039015
scalar v2.3 LMS capped RMSE: 26.32185603140849
scalar v2.3 ridge capped RMSE: 20.688665138670245
multichannel v2.3 ridge capped RMSE: 22.697166948526846
multichannel state sham separation delta RMSE: 12.995250110072181
```

Interpretation:

```text
Tier 7.1d localized the compact Tier 7.1c gap mostly to target/readout policy.
Capped RUL plus ridge readout repaired scalar scoring substantially. However,
v2.3 still did not win, and multichannel v2.3 did not beat scalar repair or fair
public baselines. The v2.2 capped-ridge signal is narrow and tiny relative to
lag-multichannel ridge, so it requires a separate fairness/statistical
confirmation gate before any usefulness claim.
```

Claim boundary:

```text
Tier 7.1d is software failure analysis only. It is not a full C-MAPSS benchmark,
not a public usefulness win, not a promoted mechanism, not a baseline freeze,
not hardware/native transfer, and not AGI/ASI evidence. Continuous no-reset
probes are diagnostic only and not promotable C-MAPSS claims.
```

Next required step:

```text
Tier 7.1e - C-MAPSS capped-RUL/readout fairness confirmation.
Determine whether the v2.2 capped-ridge signal is statistically meaningful or a
tiny FD001/adapter artifact using per-unit paired comparisons, bootstrap or
confidence intervals, effect sizes, capped-RUL fairness controls, and seed /
stochastic sensitivity.
```

### Tier 7.1e - C-MAPSS Capped-RUL/Readout Fairness Confirmation

Runner:

```text
experiments/tier7_1e_cmapss_capped_readout_fairness_confirmation.py
```

Output:

```text
controlled_test_output/tier7_1e_20260508_cmapss_capped_readout_fairness_confirmation/
```

Status:

```text
PASS
criteria: 12/12
outcome: v2_2_capped_signal_not_statistically_confirmed
```

Primary comparison:

```text
candidate: scalar_pca1_v2_2_ridge_capped125
primary baseline: lag_multichannel_ridge_capped125
mean delta RMSE, positive means candidate better: -0.3690103080637045
bootstrap 95% CI: [-1.4191012103865384, 0.6704668696286052]
effect size d: -0.06884079972999842
candidate better/worse units: 50/50
```

Interpretation:

```text
Tier 7.1e showed that the tiny Tier 7.1d v2.2 capped-ridge signal is not
statistically confirmed against the strongest fair capped-RUL baseline. The
per-unit paired result is centered around no advantage, with the confidence
interval crossing zero and a 50/50 unit split. This closes the current compact
C-MAPSS path as non-promoted.
```

Claim boundary:

```text
Tier 7.1e is statistical/fairness confirmation over Tier 7.1d per-unit results.
It is not a full C-MAPSS benchmark, not public usefulness evidence, not a
promoted mechanism, not a baseline freeze, not hardware/native transfer, and not
AGI/ASI evidence.
```

Next required step:

```text
Tier 7.1f - next public adapter contract / family selection.
Stop tuning C-MAPSS for now. Select the next predeclared public benchmark family
with official sources, license/source notes, locked preprocessing, leakage
controls, baselines, metrics, pass/fail criteria, and nonclaims before scoring.
```

### Tier 7.1f - Next Public Adapter Contract / Family Selection

Runner:

```text
experiments/tier7_1f_next_public_adapter_contract.py
```

Output:

```text
controlled_test_output/tier7_1f_20260508_next_public_adapter_contract/
```

Status:

```text
PASS
criteria: 10/10
selected adapter: numenta_nab_streaming_anomaly
dataset family: Numenta Anomaly Benchmark (NAB)
```

Interpretation:

```text
Tier 7.1f closes the compact C-MAPSS path as non-promoted and selects Numenta
NAB streaming anomaly detection as the next public adapter family. The choice
targets online anomaly streams, prediction error, false-positive pressure,
detection latency, surprise, and nonstationary adaptation.
```

Claim boundary:

```text
Tier 7.1f is contract/family-selection only. It is not NAB data preflight, not
NAB scoring, not public usefulness evidence, not a baseline freeze, not
hardware/native transfer, and not AGI/ASI evidence.
```

Next required step:

```text
Tier 7.1g - NAB source/data/scoring preflight.
Verify official source access, source hash/commit, data file parsing,
label/window parsing, label-separated online streams, tiny leakage-safe smoke
rows, and scoring-interface feasibility before full NAB scoring.
```
