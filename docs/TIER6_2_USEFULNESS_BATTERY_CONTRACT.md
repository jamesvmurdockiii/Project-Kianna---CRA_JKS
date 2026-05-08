# Tier 6.2 / Tier 7 Usefulness Benchmark Contract

Last updated: 2026-05-08

This contract answers the project-level concern:

```text
Are we proving CRA on tasks that serious reviewers recognize, or are we just
making up private tasks that fit the architecture?
```

The answer must be:

```text
Public/standardized benchmarks are the scoreboard.
Custom synthetic tasks are diagnostics only.
Mechanisms are added one at a time only when a measured public/standard gap or
a predeclared architecture question justifies them.
```

## Core Rule

Do not claim usefulness from custom tasks alone.

Custom tasks may be used to:

```text
isolate a failure mode
test leakage controls
stress one planned mechanism
debug why a public benchmark failed
verify an ablation before returning to public benchmarks
```

Custom tasks may not be used to:

```text
replace public benchmarks
manufacture a win
avoid strong baselines
justify a paper usefulness claim by themselves
```

## Current Context

Tier 7.0 already ran the standard continuous-valued dynamical benchmark suite:

```text
Mackey-Glass future prediction
Lorenz future prediction
NARMA10 nonlinear memory/system identification
aggregate geometric-mean MSE
```

Result:

```text
CRA v2.1 underperformed simple continuous-regression sequence baselines.
Tier 7.0d showed lag-only regression explained that benchmark path under the
tested interface.
```

After that, the project did not invent an easier scoreboard. It implemented and
promoted a general missing mechanism:

```text
v2.2 fading-memory temporal state
```

The original Tier 7.0 run was deliberately conservative and short:

```text
default length: 720 samples
train/test split: chronological 65% train prefix / 35% held-out suffix
approximate train-prefix samples: 468
seeds: 42, 43, 44
```

That result is a real limitation under the tested protocol, but it is not proof
that CRA would still fail after a much longer pretraining/exposure budget.
Therefore the next standardized benchmark move is:

```text
Tier 7.0e — Standard Dynamical Benchmark Rerun With v2.2 And Run-Length Sweep
```

This rerun determines whether the v2.2 temporal substrate actually improves the
previously failed public benchmark path, and whether the prior negative result
was partly a short-horizon/training-budget artifact.

## Recurring Scoreboard Rule

Mackey-Glass, Lorenz, and NARMA10 remain the first recurring standardized
scoreboard for continuous temporal usefulness. After each relevant general
mechanism is promoted, rerun the same benchmark path before moving the goalposts.

The loop is:

```text
standard benchmark result
-> failure diagnosis
-> one general mechanism
-> ablation/sham controls
-> compact regression
-> rerun the same standard benchmark scoreboard
```

If the entire planned temporal/readout/recurrent mechanism stack still cannot
move this standardized triplet, stop claiming or pursuing CRA as a competitive
continuous sequence/system-identification learner. If no other public benchmark
family shows usefulness either, stop the broad usefulness paper and narrow the
project to architecture/mechanism/hardware-substrate evidence.

## Tier 7.0e Training-Budget Protocol

Tier 7.0e must answer the "did we just not train long enough?" question.

Predeclared run lengths:

```text
720      # exact original diagnostic scale
2,000    # short extension
10,000   # medium local benchmark scale
50,000   # long exposure scale if runtime remains practical
```

Rules:

```text
all models receive the same chronological stream length
normalization remains train-prefix only
test rows remain held out chronologically
predictions are emitted before online updates where applicable
baseline hyperparameter budgets are logged
runtime is measured separately from accuracy
if 50,000 is too slow, record the blocker and run the largest practical length
```

Required output:

```text
MSE/NMSE/tail MSE by task, model, seed, and run length
aggregate geometric-mean MSE by model and run length
learning curve / length sensitivity table
CRA slope versus baseline slope
runtime per model and run length
claim boundary for whether length helped
```

Interpretation:

```text
If CRA improves substantially with length and baselines saturate, the next step
is a longer-run promotion/ablation gate.

If CRA and baselines both improve but baselines remain far ahead, diagnose the
remaining mechanism gap.

If CRA does not improve with length, stop blaming training duration and move to
mechanism diagnosis or claim narrowing.
```

2026-05-08 result:

```text
Tier 7.0e short/medium calibration completed at:
  controlled_test_output/tier7_0e_20260508_length_calibration/

Status:
  pass, 8/8 criteria

Interpretation:
  v2.2 substantially improved versus raw v2.1 at 720 and 2000 steps, but did
  not become competitive with the strongest ESN public baseline.

Tier 7.0e 10k scoreboard attempt completed at:
  controlled_test_output/tier7_0e_20260508_length_10000_scoreboard/

Status:
  fail, 7/8 criteria

Blocker:
  NARMA10 seed 44 at length 10000 generated 1,688 non-finite target values.
  The 10k three-task/three-seed public scoreboard is therefore invalid as model
  evidence until a finite-stream policy is predeclared and rerun.
```

Immediate consequence:

```text
Tier 7.0f must start with benchmark-protocol repair and public failure
localization. Do not add a new mechanism, freeze a software baseline, or move
benchmark claims to hardware from the Tier 7.0e evidence alone.
```

Tier 7.0f and valid 8000 rerun result:

```text
Tier 7.0f:
  output: controlled_test_output/tier7_0f_20260508_benchmark_protocol_failure_localization/
  status: pass, 8/8 criteria
  largest original-seed finite NARMA10 length: 8000
  optional 10000 finite-seed sensitivity: 42,43,45

Tier 7.0e 8000 same-seed scoreboard:
  output: controlled_test_output/tier7_0e_20260508_length_8000_scoreboard/
  status: pass, 8/8 criteria
  invalid streams: 0

Aggregate geomean MSE:
  ESN:                0.020109884207162095
  v2.2 fading memory: 0.19348969000027122
  lag-only LMS:       0.1986311714577415
  random reservoir:   0.2075278737499566
```

Interpretation:

```text
v2.2 has useful signal and ranks second at the largest valid same-seed length,
but ESN remains far ahead. Longer exposure alone is not sufficient. The next
step is mechanism repair from the measured failure class.
```

## Usefulness Ladder

CRA must climb the usefulness ladder in this order:

| Step | Tier | Purpose | Claim If Passed |
| --- | --- | --- | --- |
| 1 | 7.0e | Rerun Mackey-Glass/Lorenz/NARMA10 using v2.2 plus a run-length sweep | v2.2 closes/narrows the known standardized sequence gap or exposes a true training-budget curve. |
| 2 | 7.0f | If 7.0e still fails, diagnose the public benchmark failure | The next missing general mechanism is identified without making up a win. |
| 3 | 6.2a | Diagnostic hard tasks only if needed | A failure mode is isolated under controlled conditions. |
| 4 | 7.0g | Select one planned general mechanism from the measured public gap | The next mechanism is chosen without inventing a private win. |
| 5 | 7.0h | Test the bounded recurrent candidate on public tasks | The candidate improves the public scoreboard or is parked. |
| 6 | 7.0i | Repair/prove recurrence-topology specificity | Topology-specific recurrence is either separated from shams or explicitly narrowed. |
| 7 | 7.0j | Generic bounded recurrent-state promotion/regression | A narrower generic recurrent-state interface is promoted only if compact regression passes. |
| 8 | 7.1 | Public/real-ish adapter suite | CRA works outside private task generators. |
| 9 | 7.2 | Held-out challenge | CRA survives a task family that was not tuned. |
| 10 | 7.3 | Real public datasets | CRA has a useful regime on at least one externally sourced dataset. |
| 11 | 7.4 | Standard policy/action tasks | CRA can act under delayed consequences, not only predict. |
| 12 | 7.5-7.6 | Curriculum and long-horizon planning | CRA begins testing generated task families and subgoal control. |
| 13 | Final matrix | Paper lock | The final claim level is selected by evidence, not ambition. |

## Primary Standard/Public Benchmark Families

Exact dataset sources, licenses, splits, and preprocessing must be verified from
primary sources before implementation. The benchmark plan should prioritize:

```text
continuous sequence/system identification:
  Mackey-Glass, Lorenz, NARMA10, and repaired-interface reruns

stream anomaly detection:
  NAB-style anomaly streams or similarly standardized public anomaly datasets

predictive maintenance / degradation:
  NASA C-MAPSS / turbofan-style degradation or remaining-useful-life streams

time-series classification:
  UCR/UEA-style time-series classification tasks selected for streaming or
  online-prefix evaluation

biosignal/event streams:
  PhysioNet/MIT-BIH-style ECG or related public biosignal classification/anomaly
  tasks where licensing and preprocessing are clean

human activity / sensor streams:
  UCI HAR/WISDM-style activity-recognition streams with chronological or
  subject-held-out splits

neuromorphic/event datasets:
  SHD/SSC/DVS-style SNN/event datasets if the input interface is ready

standard control:
  Gymnasium CartPole and LunarLander-style tasks only after Tier 7.4 policy
  action selection is defined
```

Finance may be included as one domain, but it cannot be the sole usefulness
claim.

## Mechanics Layering Rule

If a standardized benchmark fails, do not tune randomly and do not invent an
easier private task. Use this process:

```text
1. Diagnose the failure on the public benchmark.
2. Decide whether the failure maps to a planned general mechanism.
3. Implement exactly one mechanism or repair.
4. Run a compact diagnostic to verify the mechanism is doing what it claims.
5. Rerun the same public benchmark scoreboard.
6. Run ablations/shams.
7. Freeze only if public benchmark movement plus regression justify it.
```

The planned mechanisms are general capabilities, not benchmark-specific hacks:

```text
fading-memory temporal state — promoted as v2.2, now needs public rerun
continuous-value readout/interface repair — only if public failure localizes to readout
CRA-native nonlinear recurrent state — only if fading memory is insufficient
macro/native eligibility — parked unless delayed-credit failure reappears
stronger unsupervised/predictive representation — only if public stream tasks need it
stronger routing/composition — only if public tasks require reusable substructure
working-memory/context binding extension — only if public tasks exceed current keyed memory
stronger policy/action selection — only for action/control benchmarks
curriculum/environment generation — after core public benchmarks are stable
long-horizon planning/subgoal control — after policy/action exists
native/on-chip replay buffers — only if replay is useful and host scheduling blocks scale
native eligibility traces — only if eligibility is useful and host scheduling blocks scale
multi-shard lifecycle scaling — only after lifecycle helps on public/real tasks
```

## Baseline Requirements

Each benchmark family needs strong fair baselines. At minimum:

```text
random/sign persistence where meaningful
online perceptron
online logistic regression
lag/ridge baseline for time-series structure
AR/ARIMA-style baseline where forecasting is the task
reservoir / echo-state network
small GRU
small LSTM where fair and feasible
tree/boosting baseline for tabular-window classification where standard
STDP-only SNN
simple evolutionary population
task-specific simple control baseline where applicable
oracle/context upper bound where needed
```

If a standard baseline is excluded, the report must explain why.

## Required Metrics

Each public/standardized benchmark report must include:

```text
primary task metric
mean
median
standard deviation
worst seed
paired delta versus strongest fair baseline
effect size
confidence or bootstrap interval where practical
sample efficiency
runtime
failure/collapse count
seed-level table
artifact paths
claim boundary
```

No single average score is enough.

## Pass Criteria

A usefulness gate passes only if:

```text
CRA beats or clearly complements the strongest fair baseline on a predeclared
public/standardized benchmark family, with seed-level stability and effect
size.

The result survives leakage checks, ablations, and at least one compact
regression gate.

The claimed mechanism matters: disabling or shuffling it reduces the effect.
```

Complementary usefulness can mean:

```text
better recovery after drift
lower collapse rate
lower variance / better worst-seed behavior
better sparse/delayed adaptation
better sample efficiency before regime change
```

## Fail Criteria

A usefulness gate fails or narrows the claim if:

```text
standard baselines dominate all meaningful public metrics
CRA wins only on custom synthetic diagnostics
the result depends on task-specific hacks
mechanism ablations do not matter
the result vanishes under worst-seed/tail/held-out scoring
the result cannot be reproduced from a fresh checkout
```

Failure does not kill the project. It tells us whether the paper is:

```text
a useful adaptive neuromorphic learning paper
a narrower architecture/mechanism paper
a hardware substrate/control study
```

Hard stop for broad usefulness:

```text
If the planned mechanism stack is exhausted and CRA still fails to beat or
complement strong baselines on Mackey-Glass/Lorenz/NARMA10 and the selected
public benchmark families, do not keep adding speculative features. Stop the
broad usefulness track, document the negative result, and decide whether the
remaining contribution is only architecture, controls, and SpiNNaker substrate.
```

## Hardware Transfer Rule

Do not move broad task work to SpiNNaker just because the native substrate exists.
Hardware transfer resumes only after a software benchmark or mechanism earns it.

Valid reasons to reopen native transfer:

```text
a public/standardized benchmark identifies a useful regime worth hardware validation
a promoted mechanism shows causal value and has a clear chip-native mapping
host scheduling becomes a measured blocker for a useful mechanism
```

Invalid reasons:

```text
"we need everything on chip eventually"
"hardware might rescue a failed software benchmark"
"a mechanism sounds biologically plausible"
"a custom diagnostic produced the only win"
```

## Tier 6.2a Result

2026-05-08 result:

```text
Tier 6.2a — targeted hard-task validation over frozen v2.3
output: controlled_test_output/tier6_2a_20260508_targeted_usefulness_validation/
status: PASS, 12/12 criteria
outcome: v2_3_partial_regime_signal_next_needs_failure_specific_mechanism_or_7_1_probe
```

Key result:

```text
v2.3 best task: variable_delay_multi_cue only
v2.3 beats v2.2 tasks: 1/5
v2.3 sham-separated tasks: 3/5
aggregate geomean MSE:
  v2.2: 0.15892013746238234
  v2.3: 0.17604715537423876
  lag-only: 0.2055968384080941
  reservoir: 0.22089786655426447
  ESN: 0.4224303829071217
```

Interpretation:

```text
v2.3 has a narrow targeted signal on variable-delay pressure, but it does not
beat v2.2 on the aggregate diagnostic hard-task suite. Tier 6.2a is therefore
failure localization plus a possible adapter direction, not a new usefulness
claim, baseline freeze, or hardware-transfer authorization.
```

## Tier 7.1a Result

2026-05-08 result:

```text
Tier 7.1a — real-ish/public adapter contract
output: controlled_test_output/tier7_1a_20260508_realish_adapter_contract/
status: PASS, 12/12 criteria
selected adapter: nasa_cmapss_rul_streaming
dataset family: NASA C-MAPSS / turbofan engine degradation
```

Interpretation:

```text
Tier 7.1a selected and predeclared the first public/real-ish adapter family for
testing the narrow Tier 6.2a variable-delay signal. It is a contract only, not
C-MAPSS scoring, not a public usefulness result, not a baseline freeze, and not
hardware/native transfer authorization.
```

## Tier 7.1b Result

2026-05-08 result:

```text
Tier 7.1b — NASA C-MAPSS source/data preflight
output: controlled_test_output/tier7_1b_20260508_cmapss_source_data_preflight/
status: PASS, 16/16 criteria
ZIP SHA256: 74bef434a34db25c7bf72e668ea4cd52afe5f2cf8e44367c55a82bfd91a5a34f
FD001 profile: 20631 train rows, 13096 test rows, 100 train units,
               100 test units, 100 RUL labels, 26 columns
```

Interpretation:

```text
Tier 7.1b verified reproducible source access, checksums, schema,
train-only normalization, prediction-before-update stream ordering, and
label-separated smoke artifacts. It is still preflight only, not C-MAPSS
scoring, not public usefulness evidence, not a baseline freeze, and not
hardware/native transfer authorization.
```

## Tier 7.1c Result

2026-05-08 result:

```text
Tier 7.1c — compact C-MAPSS FD001 scoring gate
output: controlled_test_output/tier7_1c_20260508_cmapss_fd001_scoring_gate/
status: PASS, 12/12 criteria
outcome: v2_3_no_public_adapter_advantage
```

Key result:

```text
best model: monotone_age_to_rul_ridge, RMSE 46.10944999532139
v2.3: rank 5, RMSE 49.4908802462679
v2.2: RMSE 48.739451335025144
v2.3 sham separations: 3
```

Interpretation:

```text
Tier 7.1c executed the compact C-MAPSS FD001 scalar-adapter scoring gate under
the predeclared leakage controls, but it did not show public-adapter advantage
for v2.3. The monotone age baseline won, and v2.3 did not beat v2.2. This is a
negative usefulness result for the compact scalar adapter, not a failed runner.
It authorizes failure analysis / adapter repair only; it does not authorize a
new baseline freeze, a public usefulness claim, or hardware/native transfer.
```

## Tier 7.1d Result

2026-05-08 result:

```text
Tier 7.1d — C-MAPSS failure analysis / adapter repair
output: controlled_test_output/tier7_1d_20260508_cmapss_failure_analysis_adapter_repair/
status: PASS, 14/14 criteria
outcome: compact_failure_partly_readout_or_target_policy
```

Key result:

```text
best promotable: scalar_pca1_v2_2_ridge_capped125, RMSE 20.271418942340336
best public baseline: lag_multichannel_ridge_capped125, RMSE 20.305268771358435
v2.3 scalar ridge capped: RMSE 20.688665138670245
v2.3 multichannel ridge capped: RMSE 22.697166948526846
multichannel sham separation delta RMSE: 12.995250110072181
```

Interpretation:

```text
Tier 7.1d localized most of the compact C-MAPSS gap to target/readout policy:
capped RUL plus ridge readout substantially repaired scalar scoring. v2.3 still
did not win, and multichannel v2.3 did not beat scalar repair or fair public
baselines. The tiny v2.2 capped-ridge advantage over lag-multichannel ridge is
not yet a public usefulness claim and needs fairness/statistical confirmation.
```

## Immediate Next Action

The current next action is:

```text
Tier 7.1e — C-MAPSS capped-RUL/readout fairness confirmation.
```

Determine whether the v2.2 capped-ridge signal is statistically meaningful or
only a tiny FD001/adapter artifact. Require per-unit paired comparisons,
bootstrap/confidence intervals, effect sizes, capped-RUL fairness controls, and
seed/stochastic sensitivity before any public usefulness claim, mechanism
promotion, or hardware/native transfer.
