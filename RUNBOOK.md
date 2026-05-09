# CRA Runbook

This is the operational path for keeping the repo clean, reproducible, and easy
to audit.

For EBRAINS/SpiNNaker uploads, JobManager command formats, returned-file
handling, and the running mistake/repair ledger, use
[`docs/SPINNAKER_EBRAINS_RUNBOOK.md`](docs/SPINNAKER_EBRAINS_RUNBOOK.md) as the
canonical operational reference.

## Daily Sanity Check

```bash
make validate
```

This runs:

1. `python3 -m pytest coral_reef_spinnaker/tests`
2. `python3 experiments/evidence_registry.py`
3. `python3 experiments/export_paper_results_table.py`
4. `python3 experiments/repo_audit.py`

## Evidence Workflow

After any new controlled run:

1. Confirm the run wrote JSON, CSV, Markdown, and plots/provenance where expected.
2. Promote the intended bundle in `experiments/evidence_registry.py` if it should
   become canonical.
3. Run `make registry`.
4. Run `make paper-table` if the result should appear in paper-facing summaries.
5. Run `make audit`.
6. Read `controlled_test_output/README.md`, `STUDY_EVIDENCE_INDEX.md`,
   `docs/PAPER_RESULTS_TABLE.md`, and `docs/RESEARCH_GRADE_AUDIT.md`.
7. If the registry or audit reports missing artifacts, stale docs, or failed
   criteria, do not cite the run.

## Frozen Baseline

The historical v0.1 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v0.1.md
baselines/CRA_EVIDENCE_BASELINE_v0.1.json
baselines/CRA_EVIDENCE_BASELINE_v0.1_STUDY_REGISTRY.snapshot.json
```

The pre-Tier-5.2 v0.2 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v0.2.md
baselines/CRA_EVIDENCE_BASELINE_v0.2.json
baselines/CRA_EVIDENCE_BASELINE_v0.2_STUDY_REGISTRY.snapshot.json
```

The post-Tier-5.3 v0.3 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v0.3.md
baselines/CRA_EVIDENCE_BASELINE_v0.3.json
baselines/CRA_EVIDENCE_BASELINE_v0.3_STUDY_REGISTRY.snapshot.json
```

The post-Tier-5.4 v0.4 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v0.4.md
baselines/CRA_EVIDENCE_BASELINE_v0.4.json
baselines/CRA_EVIDENCE_BASELINE_v0.4_STUDY_REGISTRY.snapshot.json
```

The pre-Tier-4.17 runtime-refactor v0.5 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v0.5.md
baselines/CRA_EVIDENCE_BASELINE_v0.5.json
baselines/CRA_EVIDENCE_BASELINE_v0.5_STUDY_REGISTRY.snapshot.json
```

The post-Tier-4.16a delayed-cue hardware-repeat v0.6 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v0.6.md
baselines/CRA_EVIDENCE_BASELINE_v0.6.json
baselines/CRA_EVIDENCE_BASELINE_v0.6_STUDY_REGISTRY.snapshot.json
```

The post-Tier-4.16b hard-switch hardware-repeat v0.7 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v0.7.md
baselines/CRA_EVIDENCE_BASELINE_v0.7.json
baselines/CRA_EVIDENCE_BASELINE_v0.7_STUDY_REGISTRY.snapshot.json
```

The post-Tier-4.18a chunked-runtime v0.8 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v0.8.md
baselines/CRA_EVIDENCE_BASELINE_v0.8.json
baselines/CRA_EVIDENCE_BASELINE_v0.8_STUDY_REGISTRY.snapshot.json
```

The post-Tier-5.5 expanded-baseline v0.9 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v0.9.md
baselines/CRA_EVIDENCE_BASELINE_v0.9.json
baselines/CRA_EVIDENCE_BASELINE_v0.9_STUDY_REGISTRY.snapshot.json
```

The post-Tier-5.6 tuned-baseline fairness v1.0 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v1.0.md
baselines/CRA_EVIDENCE_BASELINE_v1.0.json
baselines/CRA_EVIDENCE_BASELINE_v1.0_STUDY_REGISTRY.snapshot.json
```

The post-Tier-5.7 compact-regression v1.1 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v1.1.md
baselines/CRA_EVIDENCE_BASELINE_v1.1.json
baselines/CRA_EVIDENCE_BASELINE_v1.1_STUDY_REGISTRY.snapshot.json
```

The post-Tier-6.1 lifecycle/self-scaling v1.2 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v1.2.md
baselines/CRA_EVIDENCE_BASELINE_v1.2.json
baselines/CRA_EVIDENCE_BASELINE_v1.2_STUDY_REGISTRY.snapshot.json
```

The post-Tier-6.3 lifecycle sham-control v1.3 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v1.3.md
baselines/CRA_EVIDENCE_BASELINE_v1.3.json
baselines/CRA_EVIDENCE_BASELINE_v1.3_STUDY_REGISTRY.snapshot.json
```

The post-Tier-6.4 circuit-motif causality v1.4 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v1.4.md
baselines/CRA_EVIDENCE_BASELINE_v1.4.json
baselines/CRA_EVIDENCE_BASELINE_v1.4_STUDY_REGISTRY.snapshot.json
```

The post-Tier-5.10e internal memory-retention v1.5 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v1.5.md
baselines/CRA_EVIDENCE_BASELINE_v1.5.json
baselines/CRA_EVIDENCE_BASELINE_v1.5_STUDY_REGISTRY.snapshot.json
```

The post-Tier-5.10g keyed context-memory repair v1.6 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v1.6.md
baselines/CRA_EVIDENCE_BASELINE_v1.6.json
baselines/CRA_EVIDENCE_BASELINE_v1.6_STUDY_REGISTRY.snapshot.json
```

The post-Tier-5.11d correct-binding replay/consolidation v1.7 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v1.7.md
baselines/CRA_EVIDENCE_BASELINE_v1.7.json
baselines/CRA_EVIDENCE_BASELINE_v1.7_STUDY_REGISTRY.snapshot.json
```

The post-Tier-5.12d bounded visible predictive-context v1.8 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v1.8.md
baselines/CRA_EVIDENCE_BASELINE_v1.8.json
baselines/CRA_EVIDENCE_BASELINE_v1.8_STUDY_REGISTRY.snapshot.json
```

The post-Tier-5.13c internal host-side composition/routing v1.9 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v1.9.md
baselines/CRA_EVIDENCE_BASELINE_v1.9.json
baselines/CRA_EVIDENCE_BASELINE_v1.9_STUDY_REGISTRY.snapshot.json
```

The post-Tier-5.17e bounded predictive-binding v2.0 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v2.0.md
baselines/CRA_EVIDENCE_BASELINE_v2.0.json
baselines/CRA_EVIDENCE_BASELINE_v2.0_STUDY_REGISTRY.snapshot.json
```

The post-Tier-5.18c bounded self-evaluation / reliability-monitoring v2.1
evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v2.1.md
baselines/CRA_EVIDENCE_BASELINE_v2.1.json
baselines/CRA_EVIDENCE_BASELINE_v2.1_STUDY_REGISTRY.snapshot.json
```


The current bounded host-side software planning/subgoal-control v2.5 evidence lock lives in:

```text
baselines/CRA_EVIDENCE_BASELINE_v2.5.md
baselines/CRA_EVIDENCE_BASELINE_v2.5.json
baselines/CRA_EVIDENCE_BASELINE_v2.5_STUDY_REGISTRY.snapshot.json
```

Treat these as historical claim locks. New tiers extend the current registry but
do not rewrite what a frozen baseline claimed.

## Evidence Categories

- **Canonical registry evidence** lives in `controlled_test_output/STUDY_REGISTRY.json` and drives the paper table.
- **Baseline-frozen mechanism evidence** passed a mechanism/promotion gate, preserved compact regression, and has a frozen `baselines/CRA_EVIDENCE_BASELINE_vX.Y.*` lock even if its source bundle is not a registry row.
- **Noncanonical diagnostic evidence** answers a design or debugging question but does not freeze a new baseline by itself.
- **Failed/parked diagnostic evidence** is retained deliberately to show what did not earn promotion.
- **Hardware prepare/probe evidence** is a package or one-off probe until returned artifacts are reviewed and promoted.

Use this taxonomy when writing reports: v1.6, v1.7, v1.9, v2.0, v2.1, v2.2, v2.3, v2.4, and v2.5 are baseline-frozen mechanism evidence. Tier 5.14, Tier 5.15, and Tier 5.16 are still diagnostic coverage unless explicitly included in a later promotion gate.

## Research Narrative Workflow

When evidence or architecture changes, update the narrative docs in this order:

1. `controlled_test_output/STUDY_REGISTRY.json`
2. `STUDY_EVIDENCE_INDEX.md`
3. `docs/WHITEPAPER.md`
4. `docs/ABSTRACT.md`
5. `docs/PAPER_READINESS_ROADMAP.md`
6. `docs/REVIEWER_DEFENSE_PLAN.md`
7. `docs/CODEBASE_MAP.md`

The whitepaper should never claim more than the registry supports.

## Stop-On-Fail Rule

The controlled plan is sequential. If a test fails:

1. Stop the tier sequence.
2. Preserve the failed bundle as noncanonical audit history.
3. Debug the code or harness.
4. Rerun from the failed tier.
5. Refresh the registry.

## Canonical Test Commands

```bash
python3 experiments/tier1_sanity.py --tests all --stop-on-fail
python3 experiments/tier2_learning.py --tests all --stop-on-fail
python3 experiments/tier3_ablation.py --tests all --stop-on-fail
python3 experiments/tier4_scaling.py --stop-on-fail
python3 experiments/tier4_hard_scaling.py --stop-on-fail
python3 experiments/tier4_domain_transfer.py --stop-on-fail
python3 experiments/tier4_backend_parity.py --stop-on-fail
```

## SpiNNaker Hardware Capsule

Local prep:

```bash
python3 experiments/tier4_spinnaker_hardware_capsule.py --mode prepare
```

Real hardware run inside the proper JobManager/SpiNNaker environment:

```bash
python3 experiments/tier4_spinnaker_hardware_capsule.py --mode run-hardware --require-real-hardware --stop-on-fail
```

A Tier 4.13 pass requires:

- real `pyNN.spiNNaker` execution
- zero synthetic fallback
- zero `sim.run` failures
- zero summary-read failures
- nonzero spike readback
- fixed-pattern accuracy/correlation above threshold

## Hardware Runtime Characterization

Characterize the canonical Tier 4.13 pass without rerunning hardware:

```bash
python3 experiments/tier4_hardware_runtime_characterization.py --mode characterize-existing
```

Prepare a fresh JobManager runtime-characterization capsule:

```bash
python3 experiments/tier4_hardware_runtime_characterization.py --mode prepare
```

Run a fresh runtime characterization inside the proper hardware environment:

```bash
python3 experiments/tier4_hardware_runtime_characterization.py --mode run-hardware --require-real-hardware --stop-on-fail
```

Tier 4.14 is not a learning expansion. It must report wall-clock/provenance
costs, dominant runtime categories, and source claim boundaries.

## Hardware Multi-Seed Repeat

Prepare the next JobManager capsule:

```bash
python3 experiments/tier4_spinnaker_hardware_repeat.py --mode prepare
```

Run it inside the proper hardware environment:

```bash
python3 experiments/tier4_spinnaker_hardware_repeat.py --mode run-hardware --seeds 42,43,44 --require-real-hardware --stop-on-fail
```

Tier 4.15 is canonical only after the returned hardware bundle passes, is
reviewed, and is promoted in `experiments/evidence_registry.py`. The current
canonical Tier 4.15 pass lives at:

```text
controlled_test_output/tier4_15_20260427_030501_hardware_pass/
```

Use it as three-seed repeatability evidence for the minimal fixed-pattern
hardware capsule only; do not cite it as harder-task hardware or hardware
population scaling evidence.

## Harder Hardware Capsule

Prepare the repaired three-seed Tier 4.16a JobManager capsule:

```bash
python3 experiments/tier4_harder_spinnaker_capsule.py --mode prepare --tasks delayed_cue --seeds 42,43,44 --steps 1200 --runtime-mode chunked --learning-location host --chunk-size-steps 25
```

Run it inside the proper hardware environment:

```bash
python3 experiments/tier4_harder_spinnaker_capsule.py --mode run-hardware --tasks delayed_cue --seeds 42,43,44 --steps 1200 --delayed-readout-lr 0.20 --runtime-mode chunked --learning-location host --chunk-size-steps 25 --require-real-hardware --stop-on-fail
```

Ingest returned hardware artifacts:

```bash
python3 experiments/tier4_harder_spinnaker_capsule.py --mode ingest --ingest-dir <job-output-dir>
```

The repaired three-seed Tier 4.16a hardware repeat has now passed on seeds
`42`, `43`, and `44` and is ingested at:

```text
controlled_test_output/tier4_16_20260427_184635_delayed_cue_3seed_hardware_pass/
```

This pass proves the repaired delayed-cue chunked path transfers to real
SpiNNaker across three seeds with real readback. It does not prove
hard-switching transfer, hardware scaling, or on-chip learning. The local
prepared capsule lives at:

```text
controlled_test_output/tier4_16_20260427_131914_prepared/
```

Use it as a run package only. Do not cite the prepared bundle as evidence. If
the hardware run passes, cite it narrowly as repaired delayed-cue hardware
transfer of `delayed_lr_0_20`, not as hardware scaling, full CRA hardware deployment, or
best-baseline superiority.

Historical Tier 4.16b failure/probe sequence:

```text
controlled_test_output/tier4_16_20260427_194526_hard_noisy_switching_3seed_hardware_fail/
status = fail
reason = clean hardware execution, failed hard_noisy_switching learning gate

controlled_test_output/tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass/
status = pass
reason = repaired one-seed probe crossed the hard-switch gate
```

Canonical repaired Tier 4.16b hardware repeat:

```text
controlled_test_output/tier4_16_20260427_230043_hard_noisy_switching_3seed_hardware_pass/
status = pass
task = hard_noisy_switching
seeds = 42,43,44
steps = 1200
runtime = chunked + host
chunk_size_steps = 25
tail_accuracy_mean = 0.5476190476190476
tail_accuracy_min = 0.5238095238095238
all_accuracy_mean = 0.5497076023391813
tail_prediction_target_corr_mean = 0.04912970304751133
real spike readback min = 94707
sim_run_calls = 48 per seed
zero fallback/failures = true
```

Claim boundary: Tier 4.16b now passes as repaired hard-switch hardware transfer
across seeds `42`, `43`, and `44`, using chunked host delayed-credit replay. It
is not hardware scaling, lifecycle/self-scaling, continuous/on-chip learning,
native dopamine/eligibility, or external-baseline superiority. The pass is close
to the `0.5` hard-tail threshold, so keep runtime/resource characterization and
expanded baseline work in the next phase.

Tier 5.5 expanded-baseline suite:

```bash
make tier5-5-smoke
make tier5-5
```

Tier 5.5 has passed and is now canonical v0.9 evidence. It compares CRA against
implemented external baselines across run lengths, tasks, and seeds, and
exports paired seed deltas, confidence intervals, effect sizes,
sample-efficiency metrics, recovery, runtime, and a fairness contract. It is
software-only evidence. The honest Tier 5.5 result is robust/non-dominated
hard-adaptive behavior, not universal or best-baseline superiority.

Tier 5.6 tuned-baseline fairness audit:

```bash
make tier5-6-smoke
make tier5-6
```

Tier 5.6 has passed and is now canonical v1.0 evidence. It keeps CRA locked and
retunes the external baselines under a documented candidate budget. It exports
the candidate budget, best-profile table, per-seed audit rows, paired comparison
rows, and fairness contract. The honest Tier 5.6 result is that retuned
baselines do not erase all CRA target-regime evidence; it is not universal
superiority, all-possible-baselines coverage, or proof that CRA beats the best
tuned baseline on every metric.

Tier 5.7 compact regression:

```bash
make tier5-7-smoke
make tier5-7
```

Tier 5.7 has passed and is now canonical v1.1 evidence. It reruns compact Tier
1 negative controls, Tier 2 positive controls, Tier 3 architecture ablations,
and delayed_cue/hard_noisy_switching task smokes under the promoted
`delayed_readout_lr=0.20` setting. This is a guardrail authorizing Tier 6.1
lifecycle/self-scaling work; it is not a new capability or superiority claim.

Tier 5.9a macro eligibility diagnostic:

```bash
make tier5-9a-smoke
make tier5-9a
```

Tier 5.9a has completed as noncanonical failed mechanism evidence. It ran the
full NEST matrix, exported a fairness contract, found zero feedback-leakage
violations, and confirmed active/matured macro traces. It did not promote the
mechanism: delayed_cue regressed versus v1.4, variable_delay_cue did not show
benefit, and shuffled/zero trace ablations were not cleanly worse. If macro
credit remains the selected blocker, use Tier 5.9b for a bounded
residual/blended trace repair before any compact regression, hardware, or
custom-C migration.

Tier 5.9b residual macro eligibility repair:

```bash
make tier5-9b-smoke
make tier5-9b
```

Tier 5.9b has completed as noncanonical failed mechanism evidence. It preserved
delayed_cue with the bounded residual trace but failed trace-ablation
specificity and slightly regressed hard_noisy_switching versus v1.4/zero-trace.
Do not continue residual-scale tuning by default. Park macro eligibility until a
later measured blocker gives a specific reason to revive it.

Tier 5.10 multi-timescale memory / forgetting:

```bash
make tier5-10-smoke
make tier5-10
```

Tier 5.10 has completed as noncanonical failed mechanism evidence. The full
NEST recurrence matrix completed with zero feedback-leakage violations, but the
proxy memory-timescale candidate regressed or matched v1.4, lost to ablations,
and sign-persistence dominated the first return-phase tasks. Tier 5.10b was
therefore used as the recurrence-task repair / memory-pressure hardening gate
before sleep/replay or explicit memory stores.

Tier 5.10b recurrence-task repair / memory-pressure validation:

```bash
make tier5-10b-smoke
make tier5-10b
```

Tier 5.10b has completed as a noncanonical task-validation pass. It proves the
repaired streams now require remembered context: sign_persistence no longer
dominates, oracle/context-memory controls solve the tasks, and
wrong/reset/shuffled-memory controls fail. This authorizes Tier 5.10c mechanism
testing, but it is not a CRA memory claim and does not promote sleep/replay.

Tier 5.10c explicit context-memory mechanism diagnostic:

```bash
make tier5-10c-smoke
make tier5-10c
```

Tier 5.10c has completed as a noncanonical software mechanism pass. It shows an
explicit host-side context-binding scaffold can drive CRA to perfect accuracy on
the repaired memory-pressure tasks while reset/shuffle/wrong-memory ablations
fall behind. This authorizes internal-memory design and compact regression, but
it is not native/on-chip memory or sleep/replay evidence.

Tier 5.10d internal context-memory implementation diagnostic:

```bash
make tier5-10d-smoke
make tier5-10d
```

Tier 5.10d has completed as a noncanonical software mechanism pass. It shows
the context-memory mechanism now lives inside `Organism`: the internal
candidate receives raw observations, updates only on visible context events,
matches the Tier 5.10c external scaffold at `1.0` all-accuracy on all repaired
tasks, beats v1.4/raw CRA and reset/shuffled/wrong-memory ablations, and keeps
full compact regression green. This is internal host-side memory evidence, not
native/on-chip memory, sleep/replay evidence, or solved catastrophic forgetting.

Tier 5.10e internal memory retention stressor:

```bash
make tier5-10e-smoke
make tier5-10e
```

Tier 5.10e has completed as a noncanonical software stress pass. It shows the
internal host-side context-memory mechanism survives longer context gaps,
denser distractors, and hidden recurrence pressure: 153/153 NEST runs, zero
leakage across 2448 checked feedback rows, internal all-accuracy `1.0` on all
stress tasks, and minimum edge `0.33333333333333337` versus v1.4/raw CRA,
memory ablations, sign persistence, and best standard baseline. This is still
not sleep/replay, native/on-chip memory, hardware memory transfer, or solved
catastrophic forgetting.

Tier 5.10f memory capacity/interference stressor:

```bash
make tier5-10f-smoke
make tier5-10f
```

Tier 5.10f has completed as a noncanonical software stress failure. The full
153-run NEST matrix completed with zero feedback leakage, active context
features, and memory updates, but the internal candidate failed promotion:
minimum all accuracy `0.25`, minimum edge `-0.25` versus v1.4/raw CRA, minimum
edge `-0.5` versus best memory ablation, and minimum edge `-0.25` versus sign
persistence and the best standard baseline. Preserve this as failure evidence:
v1.5 memory survives retention stress, but not capacity/interference stress.
Tier 5.10g has now repaired that measured single-slot failure with keyed slots;
do not use the 5.10f result to justify sleep/replay or hardware memory by
itself.

Tier 5.10g multi-slot / keyed context-memory repair:

```bash
make tier5-10g-smoke
make tier5-10g
```

Tier 5.10g has completed as baseline-frozen software repair evidence. The full
171-run NEST matrix completed with zero feedback leakage across 2166 checked
feedback rows, active keyed context features, 121 context-memory updates,
candidate all accuracy `1.0` on all three capacity/interference tasks, minimum
edge `0.33333333333333337` versus v1.5 single-slot memory, minimum edge
`0.33333333333333337` versus best memory ablation, and minimum edge `0.5`
versus sign persistence and the best standard baseline. Full compact regression
after keyed-memory addition passed at
`controlled_test_output/tier5_7_20260428_235507/`. This freezes v1.6 as the
current internal host-side memory baseline, still not sleep/replay, native
on-chip memory, hardware memory transfer, compositionality, module routing, or
general working memory.

Tier 5.11a sleep/replay need test:

```bash
make tier5-11a-smoke
make tier5-11a
```

Tier 5.11a has completed as a noncanonical software diagnostic, not as a replay
implementation. The full 171-run NEST matrix completed with zero feedback
leakage, active v1.6 context features, and context-memory updates. v1.6
no-replay minimum accuracy was `0.6086956521739131`, while unbounded keyed memory
and the oracle context scaffold both reached `1.0` minimum accuracy. The
predeclared diagnostic decision was `replay_or_consolidation_needed`. This
authorizes Tier 5.11b prioritized replay/consolidation intervention testing; it
does not freeze v1.7 or prove sleep/replay works.

Tier 5.11b prioritized replay/consolidation intervention:

```bash
make tier5-11b-smoke
make tier5-11b
```

Tier 5.11b has completed as a failed/non-promoted software intervention. The
corrected full NEST bundle lives at
`controlled_test_output/tier5_11b_20260429_022048/`. It completed 162/162
task/model/seed cells with zero feedback timing leakage and zero replay future
violations. Prioritized replay reached `1.0` minimum all accuracy, `1.0`
minimum tail accuracy, `1.0` all/tail gap closure toward the unbounded keyed
upper bound, and `1185` replay consolidations. However, it failed the
predeclared shuffled-replay sham-control edge: the minimum prioritized tail edge
versus shuffled replay was `0.4444444444444444`, below the `0.5` threshold.
Therefore do not freeze v1.7 from this bundle and do not claim
sleep/replay consolidation works from 5.11b alone. v1.6 remains the current
memory baseline at this point. The next replay step, if pursued, is a
Tier 5.11c repair focused on making prioritized consolidation causally distinct
from shuffled/replay-by-opportunity controls.

Tier 5.11c replay sham-separation repair:

```bash
make tier5-11c-smoke
make tier5-11c
```

Tier 5.11c has completed as a failed/non-promoted priority-specific replay
diagnostic. The full NEST bundle lives at
`controlled_test_output/tier5_11c_20260429_031427/`. It completed 189/189
task/model/seed cells with zero feedback timing leakage and zero replay future
violations. Candidate replay again reached `1.0` minimum all accuracy, `1.0`
minimum tail accuracy, and `1.0` gap closure, with `1185` replay events and
`1185` writes. The sharper wrong-key, key-label-permuted, priority-only, and
no-consolidation controls did not match the candidate, but the narrower
priority-specific promotion gate still failed because shuffled-order replay came
too close: minimum candidate tail edge versus shuffled-order was
`0.40740740740740733`, below the `0.5` threshold. Do not promote priority
weighting from this tier.

Tier 5.11d generic replay/consolidation confirmation:

```bash
make tier5-11d-smoke
make tier5-11d
make tier5-7
```

Tier 5.11d has completed as baseline-frozen software mechanism evidence.
The full NEST bundle lives at
`controlled_test_output/tier5_11d_20260429_041524/`, and the compact regression
afterward lives at `controlled_test_output/tier5_7_20260429_050527/`. It
completed 189/189 task/model/seed cells with zero feedback timing leakage and
zero replay future violations. Correct-binding candidate replay selected and
consolidated `1185` episodes, reached `1.0` minimum all accuracy, `1.0`
minimum tail accuracy, improved tail accuracy over no replay by `1.0`, and
closed the all/tail gap to the unbounded keyed upper bound by `1.0`/`1.0`.
Wrong-key replay, key-label-permuted replay, priority-only ablation, and
no-consolidation replay did not match the candidate; no-consolidation wrote `0`
slots while matched replay controls wrote `1185`. This freezes v1.7 as
host-side software replay/consolidation evidence. It does not prove priority
weighting is essential, native/on-chip replay, hardware memory transfer,
composition, routing, or world modeling.


Tier 5.12a predictive task-pressure validation:

```bash
make tier5-12a-smoke
make tier5-12a
```

Latest output:

```text
controlled_test_output/tier5_12a_20260429_054052/
```

Result:

```text
status = PASS
matrix = 144 / 144 task-model-seed cells
feedback leakage violations = 0 / 10044 checked feedback rows
tasks = hidden_regime_switching, masked_input_prediction,
        event_stream_prediction, sensor_anomaly_prediction
seeds = 42, 43, 44
causal predictive_memory accuracy = 1.0 on all tasks
max current-reflex accuracy = 0.5393258426966292
max sign-persistence accuracy = 0.5649717514124294
max wrong/shuffled-target accuracy = 0.5444444444444444
minimum predictive edge vs best reflex = 0.4350282485875706
minimum predictive edge vs best wrong/shuffled sham = 0.4555555555555556
```

Tier 5.12a validates the task battery for the next predictive mechanism test.
Do not cite it as CRA predictive coding, world modeling, language, planning,
hardware prediction, or a v1.8 freeze.

Tier 5.12b/5.12c predictive-context mechanism sequence:

```bash
make tier5-12b-smoke
make tier5-12b
make tier5-12c-smoke
make tier5-12c
make tier5-12d-smoke
make tier5-12d
```

Latest outputs:

```text
controlled_test_output/tier5_12b_20260429_055923/  # failed diagnostic
controlled_test_output/tier5_12c_20260429_062256/  # repaired pass
controlled_test_output/tier5_12d_20260429_070615/  # compact regression / v1.8 freeze
```

Result:

```text
Tier 5.12b = FAIL, 162 / 162 NEST cells, zero leakage
5.12b meaning = wrong-sign context is alternate-code, not destructive sham

Tier 5.12c = PASS, 171 / 171 NEST cells, zero leakage
candidate writes / active decisions = 570 / 570
candidate accuracy = 1.0 event_stream_prediction
candidate accuracy = 0.8444444444444444 masked_input_prediction
candidate accuracy = 1.0 sensor_anomaly_prediction
minimum tail accuracy = 0.888888888888889
minimum edge vs v1.7 = 0.8444444444444444
minimum edge vs shuffled/permuted/no-write shams = 0.3388888888888889
minimum edge vs shortcut controls = 0.3
minimum edge vs best selected external baseline = 0.31666666666666665

Tier 5.12d = PASS, 6 / 6 child checks, 6 / 6 criteria
child checks = tier1_controls, tier2_learning, tier3_ablations,
               target_task_smokes, replay_consolidation_guardrail,
               predictive_context_guardrail
baseline freeze = baselines/CRA_EVIDENCE_BASELINE_v1.8.md
```

Tier 5.12c supports host-side visible predictive-context binding. Tier 5.12d is
the compact-regression gate that freezes bounded v1.8. Do not cite v1.8 as
hidden-regime inference, full world modeling, language, planning, hardware
prediction, hardware scaling, native on-chip learning, compositionality, or
external-baseline superiority. Also do not cite it as
self-evaluation/metacognitive monitoring or long-horizon planning/subgoal
control.

Tier 5.13 compositional skill-reuse diagnostic:

```bash
make tier5-13-smoke
make tier5-13
```

Latest output:

```text
controlled_test_output/tier5_13_20260429_075539/
```

Result:

```text
status = PASS
matrix = 126 / 126 task-model-seed cells
feedback leakage violations = 0
tasks = heldout_skill_pair, order_sensitive_chain, distractor_skill_chain
seeds = 42, 43, 44
candidate first-heldout accuracy min = 1.0
candidate total heldout accuracy min = 1.0
minimum edge vs raw v1.8 first-heldout = 1.0
minimum edge vs best module sham = 0.7083333333333333
minimum edge vs combo memorization = 1.0
minimum edge vs best selected standard baseline = 0.16666666666666663
```

Tier 5.13 supports only explicit host-side reusable-module composition as a
diagnostic scaffold. It authorizes internal CRA composition/routing work. Do not
cite it as native/internal CRA compositionality, hardware composition, language,
planning, AGI, or a v1.9 freeze.

Tier 5.13b module routing / contextual gating:

```bash
make tier5-13b-smoke
make tier5-13b
```

Latest output:

```text
controlled_test_output/tier5_13b_20260429_121615/
```

Result:

```text
status = PASS
matrix = 126 / 126 task-model-seed cells
feedback leakage violations = 0 / 11592 checked feedback rows
tasks = heldout_context_routing, distractor_router_chain, context_reentry_routing
seeds = 42, 43, 44
candidate first-heldout routing accuracy min = 1.0
candidate heldout routing accuracy min = 1.0
candidate router accuracy min = 1.0
pre-feedback route selections = 276
minimum edge vs raw v1.8 first-heldout = 1.0
minimum edge vs best routing sham = 0.375
minimum edge vs best selected standard baseline = 0.45833333333333337
```

Tier 5.13b supports only explicit host-side contextual routing as a diagnostic
scaffold. Raw v1.8 and the CRA router-input bridge stayed at `0.0`
first-heldout accuracy, so this authorizes internal CRA routing/gating work but
does not prove native/internal CRA routing, hardware routing, language,
planning, AGI, or a v1.9 freeze.

Tier 5.13c internal composition/routing promotion gate:

```bash
make tier5-13c-smoke
make tier5-13c
make tier5-12d
```

Latest output:

```text
controlled_test_output/tier5_13c_20260429_160142/
full compact regression = controlled_test_output/tier5_12d_20260429_122720/
baseline freeze = baselines/CRA_EVIDENCE_BASELINE_v1.9.md
```

Result:

```text
status = PASS
matrix = 243 / 243 task-model-seed cells
feedback leakage violations = 0 / 22941 checked feedback rows
pre-feedback feature selections = 6096
candidate module updates = 192
candidate router updates = 88
candidate pre-feedback route selections = 276
composition first-heldout accuracy min = 1.0
composition heldout accuracy min = 1.0
routing first-heldout accuracy min = 1.0
routing heldout accuracy min = 1.0
router accuracy min = 1.0
minimum edge vs raw CRA = 1.0
minimum edge vs best internal sham = 0.5
selected-standard delta min = 0.0
selected-standard delta max = 0.5
```

Tier 5.13c supports internal host-side CRA composition/routing. It separates
from internal no-write/reset/shuffle/random/always-on shams and a fresh full
compact regression stays green, so v1.9 is frozen as bounded host-side software
composition/routing evidence. Do not cite it as SpiNNaker hardware evidence,
native/custom-C on-chip routing, language, planning, AGI, or external-baseline
superiority.

Tier 5.14 working memory / context binding:

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
memory comparisons = 3
routing comparisons = 3
minimum context-memory edge vs best sham = 0.5
minimum context-memory edge vs sign persistence = 0.5
minimum routing edge vs best sham = 0.5
minimum routing edge vs routing-off CRA = 1.0
memory candidate accuracy = 1.0 on all 3 memory-pressure tasks
routing first-heldout accuracy = 1.0 on all 3 routing tasks
routing heldout accuracy = 1.0 on all 3 routing tasks
routing router accuracy = 1.0 on all 3 routing tasks
```

Tier 5.14 is a noncanonical software diagnostic over frozen v1.9. It combines
context/cue memory pressure with delayed module-state routing pressure. It
supports the bounded claim that v1.9 can maintain host-side working state across
ambiguous gaps, and that reset/shuffle/no-write/random shams lose. It does not
freeze v2.0 by itself and is not SpiNNaker hardware evidence, native/custom-C
on-chip working memory, language, long-horizon planning, AGI, or
external-baseline superiority.

Tier 5.15 spike encoding / temporal code:

```bash
make tier5-15-smoke
make tier5-15
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
time_shuffle_loss_count = 9
rate_only_loss_count = 9
```

Tier 5.15 is a noncanonical software diagnostic. It shows that latency, burst,
and temporal-interval spike timing can carry task-relevant information in the
current `numpy_temporal_code` diagnostic, with time-shuffle and rate-only
controls losing on the successful temporal cells. It does not freeze v2.0 and is
not SpiNNaker hardware evidence, native/custom-C on-chip temporal coding,
hard_noisy_switching temporal superiority, neuron-model robustness, language,
long-horizon planning, AGI, or external-baseline superiority.

Tier 5.16 neuron model / parameter sensitivity:

```bash
make tier5-16-smoke
make tier5-16
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

Tier 5.16 is a noncanonical software robustness diagnostic. It shows that the
current CRA NEST path remains functional across a predeclared LIF parameter band
covering threshold, membrane tau, refractory period, capacitance, and synaptic
tau. It also audits config-to-neuron parameter propagation and direct LIF
current-response monotonicity. It does not freeze v2.0 and is not SpiNNaker
hardware evidence, native/custom-C on-chip neuron evidence, adaptive/Izhikevich
evidence, language, long-horizon planning, AGI, or external-baseline
superiority.

Tier 6.1 lifecycle/self-scaling:

```bash
make tier6-1-smoke
make tier6-1
```

Tier 6.3 lifecycle sham controls:

```bash
make tier6-3-smoke
make tier6-3
```

Tier 6.4 circuit-motif causality:

```bash
make tier6-4-smoke
make tier6-4
```

Tier 6.1 has passed and is now canonical v1.2 evidence. It compares fixed-N CRA
against lifecycle-enabled CRA on identical delayed_cue and hard_noisy_switching
streams under NEST, seeds `42`, `43`, and `44`, and `960` steps. The pass
supports controlled software lifecycle expansion/self-scaling with clean lineage
and two hard_noisy_switching advantage regimes. The event-type boundary matters:
the run produced `74` cleavage events, `1` adult birth event, and `0` death
events, so this is not full adult birth/death turnover, not hardware lifecycle,
not sham-control proof, and not external-baseline superiority. Tier 6.3 has now
passed as the sham-control reviewer-defense gate. Tier 6.4 has also passed as
controlled software circuit-motif causality: a seeded motif-diverse graph logs
pre-reward motif activity, motif ablations produce predicted losses, and
random/monolithic controls do not dominate under adaptive criteria. It is not
hardware motif execution, custom-C/on-chip learning, compositionality, or
world-model evidence, self-evaluation/metacognitive monitoring, or
long-horizon planning/subgoal control.

Superseded local diagnostics remain useful for audit history:

```text
controlled_test_output/tier4_16b_debug_20260427_200931_hard_switch_corrected/
controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_nest_20260427/
controlled_test_output/tier4_16b_bridge_repair_orderfix_aligned_brian2_20260427/
```

Current Tier 4.17b diagnostic bundle:

```text
controlled_test_output/tier4_17b_20260427_164625_step_chunk_parity/
```

Tier 4.17b remains the local runtime-parity gate for scheduled input, binned
readback, and host replay. It is not itself a SpiNNaker hardware pass.

## Tier 4.18a Chunked Hardware Runtime Baseline

Prepare the v0.7 chunked hardware runtime baseline:

```bash
make tier4-18a-prepare
```

This creates a `jobmanager_capsule/` containing the hardware run wrapper,
configuration, expected outputs, and claim boundary. Run the generated wrapper
inside a real EBRAINS/JobManager SpiNNaker allocation:

```bash
bash controlled_test_output/<tier4_18a_prepared_run>/jobmanager_capsule/run_tier4_18a_on_jobmanager.sh /tmp/tier4_18a_job_output
```

Protocol:

```text
tasks = delayed_cue, hard_noisy_switching
seed = 42
chunk_size_steps = 10,25,50
steps = 1200
N = 8
runtime_mode = chunked
learning_location = host
```

Tier 4.18a has passed as runtime/resource characterization for the already-promoted v0.7
system and recommends `chunk_size_steps=50` as the current hardware default. It is not a new learning claim, not hardware scaling, not lifecycle
self-scaling, not continuous/on-chip learning, and not external-baseline
superiority. A pass requires zero fallback/failures, real spike readback,
documented `sim.run` counts and runtime, stable task metrics, and a justified
default chunk-size recommendation.

## External Baselines

Run the Tier 5.1 external-baseline comparison:

```bash
python3 experiments/tier5_external_baselines.py --backend nest --seed-count 3 --steps 240 --models all --tasks all
```

The current canonical Tier 5.1 pass lives at:

```text
controlled_test_output/tier5_1_20260426_232530/
```

Use it as controlled software baseline evidence only. It documents that CRA has
a median-baseline edge on `sensor_control` and `hard_noisy_switching`, while
simple online learners beat CRA on the easy `delayed_cue` task.

Run the Tier 5.2 learning-curve / run-length sweep:

```bash
python3 experiments/tier5_learning_curve.py --backend nest --seed-count 3 --run-lengths 120,240,480,960,1500 --tasks sensor_control,hard_noisy_switching,delayed_cue --models all --stop-on-fail
```

The current canonical Tier 5.2 pass lives at:

```text
controlled_test_output/tier5_2_20260426_234500/
```

Use it as controlled software learning-curve evidence only. It shows that the
Tier 5.1 CRA edge does not strengthen at the 1500-step horizon under the tested
settings: `sensor_control` saturates for everyone, `delayed_cue` remains
externally dominated, and `hard_noisy_switching` is mixed/negative for CRA.

Run the Tier 5.3 CRA failure-analysis diagnostic:

```bash
python3 experiments/tier5_cra_failure_analysis.py --backend nest --seed-count 3 --steps 960 --tasks delayed_cue,hard_noisy_switching --variants core --stop-on-fail
```

The current canonical Tier 5.3 pass lives at:

```text
controlled_test_output/tier5_3_20260427_055629/
```

Use it as controlled software diagnostic evidence only. It identifies stronger
delayed credit, especially `delayed_lr_0_20`, as the leading candidate fix. Do
not cite it as hardware evidence or final CRA superiority: hard noisy switching
improves above the external median but still trails the best external baseline.

Run the Tier 5.4 delayed-credit confirmation:

```bash
python3 experiments/tier5_delayed_credit_confirmation.py --backend nest --seed-count 3 --run-lengths 960,1500 --tasks delayed_cue,hard_noisy_switching --stop-on-fail
```

The current canonical Tier 5.4 pass lives at:

```text
controlled_test_output/tier5_4_20260427_065412/
```

Use it as controlled software confirmation evidence only. It confirms
`delayed_lr_0_20` against current CRA and external-baseline medians at 960 and
1500 steps: `delayed_cue` stays at tail accuracy `1.0`, and
`hard_noisy_switching` beats the external median at both lengths. Do not cite it
as hardware evidence or hard-switching superiority over the best external
baseline, because the best external baseline still wins that task.

Run the Tier 5.17 pre-reward representation diagnostic:

```bash
python3 experiments/tier5_unsupervised_representation.py --tasks latent_cluster_sequence,temporal_motif_sequence,ambiguous_reentry_context --variants all --steps 520 --seed-count 3 --seeds 42,43,44 --stop-on-fail
```

Smoke:

```bash
python3 experiments/tier5_unsupervised_representation.py --smoke --stop-on-fail
```

The current Tier 5.17 diagnostic output lives at:

```text
controlled_test_output/tier5_17_20260429_190501/
```

Use it as failed noncanonical pre-reward representation evidence only. It
completed the full 81-run matrix with zero non-oracle label leakage, zero reward
visibility, and zero raw dopamine during exposure, but it failed the strict
promotion gate. Do not cite it as unsupervised representation learning or a new
baseline.

Run the Tier 5.17b failure-analysis diagnostic:

```bash
make tier5-17b
```

Smoke:

```bash
make tier5-17b-smoke
```

The current Tier 5.17b output lives at:

```text
controlled_test_output/tier5_17b_20260429_191512/
```

Use Tier 5.17b as diagnostic scaffolding only. It classifies Tier 5.17 as one
positive subcase, one input-encoded/easy task, and one temporal task dominated
by fixed history baselines. It routes the next repair to Tier 5.17c intrinsic
predictive / MI-style preexposure and explicitly does not promote reward-free
representation learning or send the project back to Tier 5.9 yet.

Run the Tier 5.17c intrinsic predictive preexposure diagnostic:

```bash
make tier5-17c
```

Smoke:

```bash
make tier5-17c-smoke
```

The current Tier 5.17c output lives at:

```text
controlled_test_output/tier5_17c_20260429_193147/
```

Use it as failed noncanonical evidence. It completed `99/99` rows with zero
label/reward leakage and zero dopamine during preexposure, but it failed the
promotion gate because target-shuffled, wrong-domain, STDP-only, and best
non-oracle controls were not separated under held-out episode probes. Do not
cite it as reward-free representation learning.

Run the Tier 5.17d predictive binding repair:

```bash
make tier5-17d
```

Smoke:

```bash
make tier5-17d-smoke
```

The current Tier 5.17d output lives at:

```text
controlled_test_output/tier5_17d_20260429_194613/
```

Use it as bounded noncanonical software evidence only. It passed on
`cross_modal_binding` and `reentry_binding` with zero label/reward leakage and
zero dopamine, and it separated target-shuffled, wrong-domain, fixed-history,
reservoir, STDP-only, and best non-oracle controls on held-out ambiguous
episodes. Do not cite it as general unsupervised concept learning, hardware
evidence, native/on-chip representation learning, or a v2.0 freeze.

Run the Tier 5.17e predictive-binding promotion/regression gate:

```bash
make tier5-17e
```

Smoke:

```bash
make tier5-17e-smoke
```

The current Tier 5.17e output lives at:

```text
controlled_test_output/tier5_17e_20260429_163058/
```

Use it as the v2.0 freeze gate. It passed v1.8 compact regression, v1.9
composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d
predictive-binding guardrails. It freezes bounded host-side software
predictive-binding evidence only; it is not hardware/on-chip representation
learning, general unsupervised concept learning, full world modeling, language,
planning, AGI, or external-baseline superiority.

Run the Tier 5.18 self-evaluation / metacognitive-monitoring diagnostic:

```bash
make tier5-18
```

Smoke:

```bash
make tier5-18-smoke
```

The current Tier 5.18 output lives at:

```text
controlled_test_output/tier5_18_20260429_213002/
```

Use it as noncanonical software diagnostic evidence over frozen v2.0. It
completed `150/150` rows with zero outcome leakage and zero pre-feedback monitor
failures; the candidate passed calibration, OOD/error prediction, and
confidence-gated behavior controls. It does not freeze v2.1 and is not
consciousness, self-awareness, hardware evidence, language, planning, AGI, or
external-baseline superiority.

Run the Tier 5.18c self-evaluation promotion/regression gate:

```bash
make tier5-18c
```

Smoke:

```bash
make tier5-18c-smoke
```

The current Tier 5.18c output lives at:

```text
controlled_test_output/tier5_18c_20260429_221045/
```

Use it as the v2.1 freeze gate. It passed the full v2.0 compact-regression gate
and the Tier 5.18 self-evaluation guardrail. It freezes bounded host-side
software self-evaluation / reliability-monitoring evidence only; it is not
consciousness, self-awareness, hardware evidence, language, planning, AGI, or
external-baseline superiority.

Run the Tier 5.9c macro-eligibility v2.1 recheck:

```bash
make tier5-9c
```

Smoke:

```bash
make tier5-9c-smoke
```

The current Tier 5.9c output lives at:

```text
controlled_test_output/tier5_9c_20260429_190503/
```

Use it as failed/non-promoted diagnostic evidence. The full v2.1 guardrail
passed, but the residual macro trace failed again because trace ablations were
not worse than the normal trace. Macro eligibility remains parked and should not
be included in hardware, hybrid runtime, or custom-C work unless a later
measured blocker specifically revives it.

Run the Tier 4.20a v2.1 hardware-transfer readiness audit:

```bash
make tier4-20a
```

Smoke:

```bash
make tier4-20a-smoke
```

The current Tier 4.20a output lives at:

```text
controlled_test_output/tier4_20a_20260429_195403/
```

Use it as an engineering transfer plan only. It passed and classified the v2.1
mechanisms by chunked-host readiness versus future custom-runtime/on-chip
blockers. It is not a hardware pass. Tier 4.20b then passed as the one-seed
v2.1 bridge probe; the next hardware action is Tier 4.20c, the same bridge
repeated across seeds `42`, `43`, and `44`.

Prepare the Tier 4.20b v2.1 one-seed chunked hardware probe:

```bash
make tier4-20b-prepare
```

Run the cheap local/source simulation preflight before uploading:

```bash
make tier4-20b-preflight
```

Smoke prepare:

```bash
make tier4-20b-smoke
```

The current prepared Tier 4.20b capsule lives at:

```text
controlled_test_output/tier4_20b_20260429_205214_prepared/
```

Historical Tier 4.20b EBRAINS upload workflow: upload the source tree directly
into one EBRAINS workspace folder. Do not upload `controlled_test_output/`.

```text
experiments/
coral_reef_spinnaker/
run_tier4_20b.py
```

Run command:

```text
cra/experiments/tier4_20b_v2_1_hardware_probe.py --mode run-hardware --tasks delayed_cue,hard_noisy_switching --seeds 42 --steps 1200 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20 --no-require-real-hardware --output-dir tier4_20b_job_output
```

The source-only runner does not require local `controlled_test_output/`.
It also does not require uploading `baselines/`; Tier 4.20b records `baseline =
v2.1` in the returned report and local ingest/audit links that run back to the
frozen baseline lock.
Tier 4.20a audit context is recorded as optional provenance only; it is not a
runtime preflight blocker on EBRAINS.

The source/simulation preflight is **local only**. It runs a source prepare
smoke plus local NEST step-vs-chunked parity before upload. On EBRAINS,
`--target-check` is a tiny empirical pyNN.spiNNaker run, not a source/typecheck
gate. If the detector cannot see `machineName`, `version`, `spalloc_server`,
`remote_spinnaker_url`, `SPINNAKER_MACHINE`, or `SPALLOC_SERVER`, that is
recorded as an advisory environment caveat; the hardware claim is decided by
actual `sim.run` success, zero fallback, zero readback failures, and nonzero
real spike readback.

The current Tier 4.20b runner executes the proven Tier 4.16 chunked-host path
in-process. This avoids the EBRAINS/JobManager failure mode where a wrapper
process can spawn a child Python that reaches sPyNNaker/PACMAN without the
same usable execution context as direct Tier 4.16/4.18 hardware runs.

Returned EBRAINS no-target diagnostic:

```text
controlled_test_output/tier4_20b_20260430_no_machine_target_fail/
```

This was a noncanonical environment failure, not a science or source-package
layout failure. The uploaded source loaded correctly, but sPyNNaker had no
Machine target configured: no `machineName`, no `version`, no `spalloc_server`,
no `remote_spinnaker_url`, no `SPINNAKER_MACHINE`, and no `SPALLOC_SERVER`.
After this return, Tier 4.16 briefly used a strict no-target gate. That was
retained as a diagnostic but not as the final run policy, because earlier
JobManager evidence can expose real hardware behavior even when the local
detector cannot see the target flag.

Returned EBRAINS strict-gate diagnostic:

```text
controlled_test_output/tier4_20b_20260430_full_run_blocked_by_target_gate/
```

This full-run return proved the strict detector gate was too conservative for
EBRAINS. The current policy is advisory detection plus empirical run evidence.

Then ingest the returned job output from the repo root:

```bash
python3 experiments/tier4_20b_v2_1_hardware_probe.py --mode ingest --ingest-dir /tmp/tier4_20b_job_output
```

Claim boundary: the prepared capsule remains a run package only, but the
returned Tier 4.20b artifacts now pass as one-seed v2.1 bridge/transport
evidence through the current chunked-host path:

```text
controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass/
controlled_test_output/tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass_ingested/
```

This does not prove full native/on-chip v2.1 execution, hardware memory,
hardware routing, hardware self-evaluation, custom C, language, planning, AGI,
or macro eligibility.

## Tier 4.20c Three-Seed v2.1 Bridge Repeat

Tier 4.20c is the repeatability gate for the current v2.1 chunked-host
bridge. It uses the same bridge profile that passed in Tier 4.20b, but runs
both `delayed_cue` and `hard_noisy_switching` across seeds `42`, `43`, and
`44`.

Prepared local capsule:

```text
controlled_test_output/tier4_20c_20260430_000433_prepared/
```

For EBRAINS, create a fresh folder named:

```text
cra_420c/
```

Upload exactly:

```text
cra_420c/
  experiments/
  coral_reef_spinnaker/
```

Do not upload:

```text
controlled_test_output/
baselines/
docs/
old reports/
downloaded artifacts/
```

Run this in the EBRAINS JobManager command-line field:

```text
cra_420c/experiments/tier4_20c_v2_1_hardware_repeat.py --mode run-hardware --tasks delayed_cue,hard_noisy_switching --seeds 42,43,44 --steps 1200 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20 --no-require-real-hardware --output-dir tier4_20c_job_output
```

Expected runtime, based on Tier 4.20b, is roughly three times the one-seed
probe: about `28-35` minutes, depending on EBRAINS scheduling and extraction
overhead.

Pass requires:

```text
status = pass
child_status = pass
child_runs = 6
child seeds = [42, 43, 44]
child tasks = [delayed_cue, hard_noisy_switching]
zero sim.run failures
zero readback/summary failures
zero synthetic fallback
nonzero real spike readback
```

Claim boundary: a Tier 4.20c pass is repeatability evidence for the v2.1
bridge/transport path. It is still not native/on-chip v2.1 memory, replay,
routing, self-evaluation, custom C, language, planning, AGI, or macro
eligibility evidence.

Returned result:

```text
raw false-fail = controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_raw_false_fail/
corrected ingested pass = controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_hardware_pass_ingested/
raw wrapper status = FAIL due only to missing controlled_test_output/tier4_20b_latest_manifest.json
child status = pass
child runs = 6
seeds = 42,43,44
tasks = delayed_cue,hard_noisy_switching
sim.run failures = 0
summary/readback failures = 0
synthetic fallback = 0
minimum real spike readback = 94727
```

Lesson learned: EBRAINS source bundles must not require `controlled_test_output/`.
The Tier 4.20c runner now treats the Tier 4.20b local prerequisite as a local
prepare/registry concern, not a blocking run-hardware dependency inside a fresh
JobManager workspace.

## Tier 4.21a Keyed Context-Memory Bridge Probe

Tier 4.21a is the first targeted v2 mechanism bridge probe. It does not rerun
the generic delayed-cue/hard-switch transport proof. Instead, it asks whether
the host-side keyed context-memory scheduler can be represented through the
chunked SpiNNaker path with real spike readback.

Local preflight already passed:

```text
controlled_test_output/tier4_21a_local_bridge_smoke/
```

Prepared local capsule:

```text
controlled_test_output/tier4_21a_20260430_prepared/
```

Returned one-seed hardware pass:

```text
controlled_test_output/tier4_21a_20260430_keyed_context_memory_seed42_hardware_pass_ingested/
```

For EBRAINS, create a fresh folder named:

```text
cra_421a/
```

Upload exactly:

```text
cra_421a/
  experiments/
  coral_reef_spinnaker/
```

Do not upload:

```text
controlled_test_output/
baselines/
docs/
old reports/
downloaded artifacts/
```

Run this in the EBRAINS JobManager command-line field:

```text
cra_421a/experiments/tier4_21a_keyed_context_memory_bridge.py --mode run-hardware --tasks context_reentry_interference --variants keyed_context_memory,slot_reset_ablation,slot_shuffle_ablation,wrong_key_ablation --seeds 42 --steps 720 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20 --context-memory-slot-count 4 --no-require-real-hardware --output-dir tier4_21a_job_output
```

Expected runtime should be shorter than Tier 4.20c because this is one seed and
720 steps, but it still runs four variants. A rough expectation is `15-25`
minutes depending on EBRAINS scheduling and report extraction.

Pass requires:

```text
status = pass
mode = run-hardware
all four variants completed
zero sim.run failures
zero readback/summary failures
zero synthetic fallback
nonzero real spike readback
keyed memory updates observed
keyed memory feature active at decisions
keyed memory retains more than one slot
keyed candidate not worse than the best memory ablation
```

Claim boundary: a Tier 4.21a pass is keyed context-memory bridge-adapter
evidence only. It is not native/on-chip memory, not custom C, not continuous
runtime, and not evidence for replay, predictive binding, composition/routing,
self-evaluation, language, planning, AGI, or external-baseline superiority.

Observed returned pass:

```text
status = pass
mode = run-hardware
runs = 4 / 4
sim.run failures = 0
summary/readback failures = 0
synthetic fallback = 0
minimum real spike readback = 714601
keyed memory updates = 11
keyed feature-active decisions = 20
max keyed slots used = 4
keyed all/tail accuracy = 1.0 / 1.0
best-ablation all accuracy = 0.5
runtime = 3522.7107 seconds
```

Operational lesson: this pass is valuable, but the nearly one-hour runtime for
one seed and four variants means we should not run large hardware bridge
matrices for every v2 mechanism. Use Tier 4.21a as the stateful-mechanism bridge
reference and move the next engineering work toward custom/hybrid on-chip
runtime.

## Tier 4.22a Custom / Hybrid Runtime Contract

Run locally:

```bash
make tier4-22a
```

Current pass:

```text
controlled_test_output/tier4_22a_20260430_custom_runtime_contract/
```

Tier 4.22a is a design/engineering gate, not a hardware run. It adds the
pre-hardware safety layer that should have existed before any future expensive
allocation:

```text
constrained-NEST parity
static PyNN/SpiNNaker feature compliance
bounded state/resource checks
sPyNNaker map/build or tiny smoke run when a target stack is available
```

The point is to make hardware failure unlikely before EBRAINS time is spent,
while still admitting that only a returned hardware artifact is hardware
evidence.

Claim boundary: Tier 4.22a is not custom C, not native/on-chip execution, not
continuous runtime, and not a speedup claim.

## Tier 4.22a0 SpiNNaker-Constrained Local Preflight

Run locally before any further expensive hardware allocation:

```bash
make tier4-22a0
```

Current pass:

```text
controlled_test_output/tier4_22a0_20260430_spinnaker_constrained_preflight/
```

This gate does the thing we should always want before EBRAINS time:

```text
NEST/PyNN/sPyNNaker import checks
local constrained PyNN/NEST StepCurrentSource smoke
per-step binned spike readback
static bridge-source compliance checks
bounded population / connection / keyed-slot resource checks
fixed-point weight quantization probe
custom C runtime host tests
```

Current measured result: the NEST probe passed with `64` spikes, zero
`sim.run` failures, zero readback failures, zero static-compliance failures,
zero resource failures, and passing host C runtime tests.

Claim boundary: Tier 4.22a0 is local preflight only. It reduces transfer risk
and catches obvious mapping/constraint errors, but it is not real SpiNNaker
hardware evidence, not custom-C hardware execution, not native/on-chip learning,
not continuous runtime, and not a speedup claim. The next implementation step is
Tier 4.22b, a continuous transport scaffold.

## Tier 4.22b Continuous Transport Scaffold

Run locally:

```bash
make tier4-22b
```

Current local pass:

```text
controlled_test_output/tier4_22b_20260430_continuous_transport_local/
```

This tier proves the plumbing we need before adding continuous learning:

```text
scheduled task input for the whole run
one continuous sim.run per task/seed case
compact binned spike readback
zero synthetic fallback
zero sim.run/readback failures
nonzero spikes under the same 1200-step task horizon
```

Current result: delayed_cue and hard_noisy_switching, seed `42`, `1200` steps,
N=`8`, local PyNN/NEST, one `sim.run` per case, `101112` and `101056` spikes,
zero failures.

Learning is deliberately disabled in this tier. That does not change the
destination: the final custom/hybrid runtime must learn continuously. The point
is to prove timing/readback first so Tier 4.22d learning/plasticity bugs are not
mixed with transport bugs.

Prepare a hardware capsule only after the local pass:

```bash
make tier4-22b-prepare
```

Claim boundary: a local Tier 4.22b pass is not real hardware evidence and not a
learning result. A returned `run-hardware` pass would be continuous transport
hardware evidence only, still not continuous learning parity.

Returned hardware pass:

```text
controlled_test_output/tier4_22b_20260430_continuous_transport_hardware_pass_ingested/
```

This EBRAINS run passed both reference tasks with real `pyNN.spiNNaker`, one
`sim.run` per task, zero fallback/failures, and nonzero spike readback:

```text
delayed_cue seed 42: 95000 spikes, runtime 111.5257s
hard_noisy_switching seed 42: 94896 spikes, runtime 109.3603s
```

Interpretation: chunking/readback loops were removed for this transport test,
but SpiNNaker still ran the 60-second simulated streams roughly real-time plus
setup/readback/provenance overhead. The next bottleneck is not chunking; it is
where persistent state and learning live.

## Tier 4.22c Persistent Custom-C State Scaffold

Run locally:

```bash
make tier4-22c
```

Current pass:

```text
controlled_test_output/tier4_22c_20260430_persistent_state_scaffold/
```

This tier is the first concrete state-ownership step toward the real target:
full custom/on-chip CRA execution. It adds static bounded keyed context slots,
bounded no-leak pending horizons, readout state, decision/reward counters,
summary readback state, and reset semantics to the custom C runtime.

Current measured result:

```text
custom C host tests = pass
static state checks = 12 / 12
state owner = custom_c_runtime
dynamic allocation inside state_manager.c = false
bounded context slots = MAX_CONTEXT_SLOTS
bounded pending horizons = MAX_PENDING_HORIZONS
```

Claim boundary: Tier 4.22c is not a hardware run, not reward/plasticity
learning, not native/on-chip learning, and not speedup evidence. It is the C
state substrate that Tier 4.22d reward/plasticity must use causally.

## Tier 4.22d Reward/Plasticity Runtime Scaffold

Run locally:

```bash
make tier4-22d
```

Current pass:

```text
controlled_test_output/tier4_22d_20260430_reward_plasticity_scaffold/
```

This tier adds the first tested reward/plasticity path inside the custom C
runtime:

```text
synaptic eligibility traces
trace-gated dopamine
fixed-point trace decay
signed one-shot dopamine
runtime-owned readout reward update
```

Current measured result:

```text
custom C host tests = pass
static plasticity checks = 11 / 11
reward/plasticity owner = custom_c_runtime
```

Claim boundary: Tier 4.22d is local C scaffold evidence only. It is not a
hardware run, not continuous-learning parity, and not speedup evidence. The next
gate is Tier 4.22e local continuous-learning parity against the chunked
reference before another EBRAINS allocation.

## Tier 4.22e Local Continuous-Learning Parity Scaffold

Run locally:

```bash
make tier4-22e
```

Current pass:

```text
controlled_test_output/tier4_22e_20260430_local_learning_parity/
```

This tier checks the C fixed-point delayed-readout learning equations against a
floating reference before hardware time is spent:

```text
fixed/float sign agreement = 1.0
max final weight delta = ~4.14e-05
delayed_cue tail accuracy = 1.0
hard_noisy_switching tail accuracy = 0.547619
no-pending ablation tail accuracy = 0.0
pending drops = 0
```

Critical leakage rule: pending horizons store feature, prediction, and due
timestep only. The target/reward arrives at maturity, not at prediction time.

Claim boundary: Tier 4.22e is local minimal delayed-readout parity only. It is
not hardware evidence, not full CRA parity, and not speedup evidence. The next
step is the Tier 4.22f0 custom-runtime scale-readiness audit before any
hardware command/readback or `.aplx` build/load acceptance gate.

## Tier 4.22f0 Custom Runtime Scale-Readiness Audit

Run locally:

```bash
make tier4-22f0
```

Current pass:

```text
controlled_test_output/tier4_22f0_20260430_custom_runtime_scale_audit/
```

This gate answers a practical hardware-time question:

```text
Is the custom-C sidecar ready for a learning hardware run, or would we just
burn EBRAINS time on known non-scalable data structures?
```

Current answer:

```text
audit = pass
custom_runtime_scale_ready = false
direct_custom_runtime_hardware_learning_allowed = false
```

Use this boundary when planning runs:

- PyNN/sPyNNaker is still the normal way to build, map, run, and read standard
  SpiNNaker experiments.
- Custom C is only for CRA-specific closed-loop substrate mechanics that PyNN
  cannot express or scale directly.
- Do not upload or run a custom-runtime learning hardware job until Tier 4.22g
  fixes event-indexed spike delivery and lazy/active eligibility traces, and a
  follow-up acceptance gate exposes compact state readback.

The audit records `7` scale blockers. The hardware-learning blockers are
all-synapse spike delivery, all-synapse trace decay, all-synapse dopamine
modulation, linear neuron lookup, and count-only readback.

Claim boundary: Tier 4.22f0 is not hardware evidence, not scale-ready evidence,
and not speedup evidence. It is the reason we do **not** run the next custom
learning job yet.

## Tier 4.22g Event-Indexed Active-Trace Runtime

Run locally:

```bash
make tier4-22g
```

Current pass:

```text
controlled_test_output/tier4_22g_20260430_event_indexed_trace_runtime/
```

This gate repairs the first three custom-C scale blockers:

```text
SCALE-001 synapse_deliver_spike:
  O(S) all-synapse scan -> O(out_degree(pre_id))

SCALE-002 synapse_decay_traces_all:
  O(S) all-synapse decay -> O(active_traces)

SCALE-003 synapse_modulate_all:
  O(S) all-synapse dopamine -> O(active_traces)
```

Current answer:

```text
Tier 4.22g = pass
custom_runtime_hardware_learning_allowed = false
```

Why still blocked: `READ_SPIKES` is still count/timestep only, direct neuron
lookup and dynamic allocation remain scale concerns, and there is no
build/load/command acceptance gate yet.

Claim boundary: Tier 4.22g is local C optimization evidence only. It is not a
hardware run, not measured speedup evidence, not full CRA parity, and not final
on-chip learning proof.

## Tier 4.22h Compact Readback / Build-Command Readiness

Run locally:

```bash
make tier4-22h
```

Current pass:

```text
controlled_test_output/tier4_22h_20260430_compact_readback_acceptance/
```

This gate adds `CMD_READ_STATE`, a compact state summary command. It is the
reason a later board smoke can check whether the runtime is alive and carrying
learning state without requiring huge spike dumps.

Current answer:

```text
Tier 4.22h = pass
static readback/callback/SARK-SDP/router-API/build-recipe checks = 30/30
CMD_READ_STATE payload = 73 bytes
aplx_build_status = not_attempted_spinnaker_tools_missing
board_load_command_roundtrip_status = not_attempted
custom_runtime_learning_hardware_allowed = false
```

Do not interpret this as a hardware command pass. It only means the local
runtime source now has compact readback and the build/load status is recorded
honestly.

Next hardware-facing step:

```text
Tier 4.22i tiny EBRAINS/board custom-runtime load + CMD_READ_STATE round-trip
```

Only after that passes should we attempt minimal custom-runtime closed-loop
learning.


## Tier 4.22i Custom Runtime Board Round-Trip Smoke

Prepare locally:

```bash
make tier4-22i-prepare
```

Prepared folder to upload to EBRAINS/JobManager:

```text
ebrains_jobs/cra_422r
```

Run command inside JobManager:

```text
cra_422r/experiments/tier4_22i_custom_runtime_roundtrip.py --mode run-hardware --output-dir tier4_22i_job_output
```

If the job image does not expose the SpiNNaker host automatically, append:

```text
--spinnaker-hostname <board-host-or-ip>
```

Default target acquisition is automatic: the runner first tries explicit
hostname/config discovery, then falls back to a tiny `pyNN.spiNNaker` probe and
uses `SpynnakerDataView`'s transceiver/IP for the raw custom-runtime load.

Expected returned files include:

- `tier4_22i_results.json`
- `tier4_22i_report.md`
- `tier4_22i_environment.json`
- `tier4_22i_target_acquisition.json`
- `tier4_22i_host_test_stdout.txt`
- `tier4_22i_host_test_stderr.txt`
- `tier4_22i_main_syntax_stdout.txt`
- `tier4_22i_main_syntax_stderr.txt`
- `tier4_22i_aplx_build_stdout.txt`
- `tier4_22i_aplx_build_stderr.txt`
- `tier4_22i_load_result.json`
- `tier4_22i_roundtrip_result.json`

Returned failures already seen: early EBRAINS Tier 4.22i attempts failed before
board execution because the job image did not define guessed multicast callback
names such as `MC_PACKET_RX`; those failures are preserved at
`controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_fail/` and
`controlled_test_output/tier4_22i_20260430_ebrains_no_mc_event_build_fail/`.
Tier 4.22k then proved the official event names are `MC_PACKET_RECEIVED` and
`MCPL_PACKET_RECEIVED`. The next predecessor failed later in
`host_interface.c` because the real SARK `sdp_msg_t` uses packed fields
`dest_port`, `srce_port`, `dest_addr`, and `srce_addr`, and the copy API is
`sark_mem_cpy`; that failure is preserved at
`controlled_test_output/tier4_22i_20260430_ebrains_sdp_struct_build_fail/`.
The next `cra_422m` run compiled past `host_interface.c` but failed in
`router.c` because EBRAINS SARK exposes official `rtr_alloc/rtr_mc_set/rtr_free`
router calls, not local-stub-only `sark_router_alloc/sark_router_free`; that
failure is preserved at
`controlled_test_output/tier4_22i_20260430_ebrains_router_api_build_fail/`.
The next `cra_422n` run compiled all custom C sources and linked an ELF, but
the manual object-only link recipe omitted the official SpiNNaker build object
and `libspin1_api.a`, leaving no `cpu_reset` entrypoint and no sections for
binary/APLX creation; that failure is preserved at
`controlled_test_output/tier4_22i_20260430_ebrains_manual_link_empty_elf_fail/`.
The next `cra_422p` run built the `.aplx` successfully with the official build
rules, but the raw custom loader could not discover a board hostname, so app
load and `CMD_READ_STATE` round-trip were not attempted; that failure is
preserved at
`controlled_test_output/tier4_22i_20260430_ebrains_aplx_build_pass_target_missing_fail/`.
The next `cra_422q` run built the `.aplx`, acquired the target through
pyNN.spiNNaker/SpynnakerDataView, selected free core `4`, and loaded the app,
but command round-trip returned 2-byte short payloads because host/runtime
commands did not use the official SDP/SCP `cmd_rc`/`seq`/`arg1`/`arg2`/`arg3`
header before `data[]`; that failure is preserved at
`controlled_test_output/tier4_22i_20260430_ebrains_aplx_load_pass_sdp_payload_short_fail/`.
Do not guess EBRAINS C APIs; discover, patch, guard locally, then rerun.

What this sequence got right:

- We stopped treating the whole repo as the hardware upload artifact.
- We moved to small, source-only, cache-busting EBRAINS packages such as `cra_422r`.
- We preserved every returned EBRAINS failure as noncanonical diagnostic evidence.
- We separated build, target acquisition, app load, command round-trip, and learning claims.
- We added discovery tiers and stricter local guards instead of continuing to guess platform APIs.
- We aligned the runtime with official Spin1API callbacks, packed SARK SDP fields, SARK router calls, and `spinnaker_tools.mk`.
- We added pyNN/sPyNNaker target acquisition so raw custom-runtime jobs can reuse the board context EBRAINS actually exposes.
- We converted the `cra_422q` short-payload failure into a precise SDP/SCP command-header contract for `cra_422r`.

Claim boundary: `PREPARED` is not hardware evidence. A `run-hardware` pass only
proves the custom app can build/load and answer `CMD_READ_STATE` with state
changes. It does not prove full CRA learning or speedup.

Current status: Tier 4.22i passed at `controlled_test_output/tier4_22i_20260501_ebrains_board_roundtrip_pass/`. The `cra_422r` run built the `.aplx`, acquired a real board through pyNN.spiNNaker/SpynnakerDataView, selected free core `(0,0,4)`, loaded the app, acknowledged mutation commands, and returned `CMD_READ_STATE` schema version `1` with a 73-byte payload showing `2` neurons, `1` synapse, and `reward_events=1`. Tier 4.22j passed after ingest correction at `controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/`: raw EBRAINS status was a false-fail caused by the zero-value evaluator bug, while returned hardware data satisfied all learning-smoke criteria. Tier 4.22l passed after ingest at `controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_hardware_pass_ingested/`: the returned EBRAINS run acquired board `10.11.194.1`, selected free core `(0,0,4)`, built/loaded the custom runtime, and matched all four fixed-point prediction/weight/bias parity rows exactly. Tier 4.22k passed, and the `cra_422l` SDP struct failure, `cra_422m` router API failure, `cra_422n` manual-link empty-ELF failure, `cra_422o` official-build nested object-directory failure, `cra_422p` target-acquisition failure, and `cra_422q` SDP payload-short failure remain ingested as noncanonical diagnostic evidence. Tier 4.22m passed after ingest at `controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_hardware_pass_ingested/`: board `10.11.202.65`, selected core `(0,0,4)`, 12/12 task events matched the local s16.15 reference, observed tail accuracy `1.0`, and final readout was `0.984375` with zero bias. Tier 4.22n passed after ingest at `controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/`: board `10.11.205.1`, selected core `(0,0,4)`, 12 delayed pending-queue events matched the local s16.15 reference, observed max pending depth was `3`, observed tail accuracy was `1.0`, and final readout was `0.9375` with zero bias. Tier 4.22o `cra_422w` returned a noncanonical hardware failure at `controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_overflow_fail_ingested/`: build/load/schedule/mature all worked, but the signed regime-switch update exposed a 32-bit fixed-point multiply overflow. Tier 4.22o `cra_422x` then passed after ingest at `controlled_test_output/tier4_22o_20260501_noisy_switching_micro_task_hardware_pass_ingested/`: board `10.11.210.25`, selected core `(0,0,4)`, 44/44 criteria passed, all prediction/weight/bias raw deltas were `0`, observed accuracy/tail accuracy were `0.7857142857/1.0`, and final readout raw values were `-48768/-1536`. Tier 4.22p `cra_422y` passed after ingest at `controlled_test_output/tier4_22p_20260501_aba_reentry_micro_task_hardware_pass_ingested/`: board `10.11.222.17`, selected core `(0,0,4)`, 44/44 criteria passed, all 30 schedule/mature pairs acknowledged, max pending depth was `3`, all prediction/weight/bias raw deltas were `0`, observed accuracy/tail accuracy were `0.8666666667/1.0`, and final readout raw values were `30810/-1`.

## Tier 4.22j Minimal Custom Runtime Closed-Loop Learning Smoke

Returned status: **PASS after ingest correction** at
`controlled_test_output/tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested/`.

The raw EBRAINS manifest reported `FAIL` because the runner checked
`active_pending=0` with `active_pending or -1`, turning a correct zero into the
missing-value sentinel. The raw manifest/report are preserved as
`remote_tier4_22j_results_raw.json` and `remote_tier4_22j_report_raw.md`, and
the evaluator has been fixed.

To rerun Tier 4.22j if needed, prepare locally:

```bash
make tier4-22j-prepare
```

Prepared folder to upload to EBRAINS/JobManager:

```text
ebrains_jobs/cra_422s
```

Run command inside JobManager:

```text
cra_422s/experiments/tier4_22j_minimal_custom_runtime_learning.py --mode run-hardware --output-dir tier4_22j_job_output
```

Expected returned files include:

- `tier4_22j_results.json`
- `tier4_22j_report.md`
- `tier4_22j_environment.json`
- `tier4_22j_target_acquisition.json`
- `tier4_22j_load_result.json`
- `tier4_22j_learning_result.json`
- low-level helper build/test artifacts, some of which may keep the shared `tier4_22i_` prefix
- `reports.zip` or extracted SpiNNaker reports if EBRAINS provides them

Pass criteria:

- `runner_revision = tier4_22j_minimal_custom_runtime_learning_20260501_0001`
- custom C host tests pass
- `.aplx` build passes
- target acquisition passes
- app load passes
- `RESET` acknowledges
- `CMD_SCHEDULE_PENDING` acknowledges
- state after schedule shows `pending_created >= 1`, `active_pending >= 1`, and `decisions >= 1`
- `CMD_MATURE_PENDING` acknowledges
- mature reply shows `matured_count >= 1`
- state after mature shows `pending_matured >= 1`, `active_pending = 0`, `reward_events >= 1`, `readout_weight_raw > 0`, and `readout_bias_raw > 0`
- synthetic fallback is zero

Claim boundary: a Tier 4.22j pass proves only one minimal chip-owned delayed
pending/readout update inside the custom runtime. It does not prove full CRA
task learning, v2.1 mechanism transfer, speedup, multi-core scaling, or final
on-chip autonomy.

## Tier 4.22l Tiny Custom Runtime Learning Parity

Returned status: **PASS after ingest** at
`controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_hardware_pass_ingested/`.

Local/prepared gates are retained at
`controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_local/`
and
`controlled_test_output/tier4_22l_20260501_custom_runtime_learning_parity_prepared/`.

Purpose: compare the custom-runtime readout update path against a predeclared
local s16.15 fixed-point reference before scaling from one learning event into
task-like on-chip loops.

Run locally before upload:

```bash
make tier4-22l-local
make tier4-22l-prepare
```

Prepared folder to upload to EBRAINS/JobManager:

```text
ebrains_jobs/cra_422t
```

Run command inside JobManager:

```text
cra_422t/experiments/tier4_22l_custom_runtime_learning_parity.py --mode run-hardware --output-dir tier4_22l_job_output
```

Tiny parity sequence:

```text
1. feature= 1.0, target= 1.0
2. feature= 1.0, target=-1.0
3. feature=-1.0, target=-1.0
4. feature=-1.0, target= 0.5
learning_rate=0.25
expected final readout_weight_raw=-4096 (-0.125)
expected final readout_bias_raw=-4096 (-0.125)
```

Returned pass criteria:

- `runner_revision = tier4_22l_custom_runtime_learning_parity_20260501_0001`
- local fixed-point reference is generated in the job.
- hardware target acquisition, `.aplx` build, and app load pass.
- all four `CMD_SCHEDULE_PENDING` commands acknowledge.
- all four `CMD_MATURE_PENDING` commands acknowledge.
- each mature call returns `matured_count = 1`.
- observed prediction, readout weight, and readout bias raw values match the local reference within `raw_tolerance=1`.
- final state has `pending_created = 4`, `pending_matured = 4`, `reward_events = 4`, `active_pending = 0`.
- final `readout_weight_raw = -4096 +/- 1`.
- final `readout_bias_raw = -4096 +/- 1`.
- synthetic fallback is zero.

Returned evidence:

```text
board IP = 10.11.194.1
selected core = (0,0,4)
target acquisition = pyNN.spiNNaker_probe / SpynnakerDataView
.aplx build = pass
app load = pass
schedule commands = 4/4 success
mature commands = 4/4 success
matured_count = [1, 1, 1, 1]
prediction raw deltas = [0, 0, 0, 0]
weight raw deltas = [0, 0, 0, 0]
bias raw deltas = [0, 0, 0, 0]
final pending_created = 4
final pending_matured = 4
final reward_events = 4
final active_pending = 0
final readout_weight_raw = -4096
final readout_bias_raw = -4096
```

Boundary: prepared/local Tier 4.22l is not hardware evidence. The returned pass
proves only a tiny signed fixed-point on-chip learning parity sequence, not
full CRA task learning, v2.1 transfer, speedup, multi-core scaling, or final
on-chip autonomy.

## Tier 4.22m Minimal Custom Runtime Task Micro-Loop

Returned status: **PASS** at `controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_hardware_pass_ingested/`.

Prepare/rerun locally if needed:

```bash
make tier4-22m-local
make tier4-22m-prepare
```

Local/prepared evidence also exists at:

```text
controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_local/
controlled_test_output/tier4_22m_20260501_custom_runtime_task_micro_loop_prepared/
```

Prepared folder to upload to EBRAINS/JobManager:

```text
ebrains_jobs/cra_422u
```

Run command inside JobManager:

```text
cra_422u/experiments/tier4_22m_custom_runtime_task_micro_loop.py --mode run-hardware --output-dir tier4_22m_job_output
```

The 4.22m task stream is intentionally tiny and deterministic:

```text
12 signed fixed-pattern events
feature alternates +1.0, -1.0
target equals feature
learning_rate = 0.25
score = sign of the pre-update prediction
expected accuracy = 0.9166666667
expected tail accuracy = 1.0
expected final readout_weight_raw = 32256
expected final readout_bias_raw = 0
```

Returned hardware pass achieved: real target acquisition through pyNN.spiNNaker/SpynnakerDataView, `.aplx` build/load, all twelve schedule/mature pairs acknowledging, exactly one pending matured per step, prediction/weight/bias raw deltas within tolerance `1`, final `pending_created=pending_matured=reward_events=decisions=12`, final `active_pending=0`, final `readout_weight_raw=32256`, final `readout_bias_raw=0`, observed accuracy `0.9166666667`, observed tail accuracy `1.0`, and zero synthetic fallback.

Boundary: Tier 4.22m proves only a minimal fixed-pattern custom-runtime task micro-loop, not full CRA task learning, v2.1 mechanism transfer, speedup, multi-core scaling, or final on-chip autonomy.

## Tier 4.22n Tiny Delayed-Cue Custom Runtime Micro-Task

Prepare locally:

```bash
make tier4-22n-local
make tier4-22n-prepare
```

Current status: **PASS after EBRAINS ingest** at:

```text
controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_local/
controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_prepared/
controlled_test_output/tier4_22n_20260501_delayed_cue_micro_task_hardware_pass_ingested/
```

Prepared folder to upload to EBRAINS/JobManager:

```text
ebrains_jobs/cra_422v
```

Run command inside JobManager:

```text
cra_422v/experiments/tier4_22n_delayed_cue_micro_task.py --mode run-hardware --output-dir tier4_22n_job_output
```

The 4.22n task stream is intentionally tiny but delayed:

```text
12 signed cue/target events
feature alternates +1.0, -1.0
target equals feature
pending_gap_depth = 2
max_pending_depth = 3
learning_rate = 0.125
score = sign of the pre-update prediction
expected accuracy = 0.8333333333
expected tail accuracy = 1.0
expected final readout_weight_raw = 30720
expected final readout_bias_raw = 0
```

Returned hardware pass requires real target acquisition, `.aplx` build/load,
all twelve schedule commands acknowledging, delayed maturation in order with
exactly one pending matured per event, observed max pending depth at least `3`,
prediction/weight/bias raw deltas within tolerance `1`, final
`pending_created=pending_matured=reward_events=decisions=12`, final
`active_pending=0`, final readout matching the reference, and zero synthetic
fallback.

Returned hardware pass achieved: real target acquisition through
pyNN.spiNNaker/SpynnakerDataView on board `10.11.205.1`, selected core
`(0,0,4)`, `.aplx` build/load, all twelve schedule commands acknowledging,
delayed oldest-first maturation with exactly one pending matured per event, max
observed pending depth `3`, prediction/weight/bias raw deltas `0`, final
`pending_created=pending_matured=reward_events=decisions=12`, final
`active_pending=0`, final `readout_weight_raw=30720`, final
`readout_bias_raw=0`, observed accuracy `0.8333333333`, observed tail accuracy
`1.0`, and zero synthetic fallback.

Boundary: Tier 4.22n proves only a tiny delayed-cue-like pending-queue
micro-task, not full CRA task learning, v2.1 mechanism transfer, speedup
evidence, multi-core scaling, or final on-chip autonomy. Tier 4.22o has since
passed as a tiny noisy-switching custom-runtime micro-task, and Tier 4.22p is
now prepared as the next A-B-A reentry custom-runtime micro-task.

## Tier 4.22k Spin1API Event-Symbol Discovery

Prepare locally:

```bash
make tier4-22k-prepare
```

Prepared folder to upload to EBRAINS/JobManager:

```text
ebrains_jobs/cra_422k
```

Run command inside JobManager:

```text
cra_422k/experiments/tier4_22k_spin1api_event_discovery.py --mode run-hardware --output-dir tier4_22k_job_output
```

This command is intentionally a JobManager command, not a local shell recipe.
It does not need `controlled_test_output/`, does not need a board hostname, and
does not run a CRA board experiment. It inspects the EBRAINS toolchain/header
image and compiles a callback-symbol probe matrix.

Expected returned files include:

- `tier4_22k_results.json`
- `tier4_22k_report.md`
- `tier4_22k_environment.json`
- `tier4_22k_header_inventory.csv`
- `tier4_22k_spin1api_symbols.txt`
- `tier4_22k_probe_matrix.csv`
- `tier4_22k_probe_build_stdout.txt`
- `tier4_22k_probe_build_stderr.txt`

Pass means:

- Spin1API headers are inspectable in the EBRAINS image.
- `spin1_callback_on` exists.
- `TIMER_TICK` and `SDP_PACKET_RX` callback probes compile.
- At least one real multicast receive callback macro compiles, preferably
  `MC_PACKET_RECEIVED` or `MCPL_PACKET_RECEIVED`.

Fail means:

- Do not run custom-runtime learning hardware.
- Do not treat SDP-only buildability as enough.
- Inspect the returned header inventory and repair the receive path using a
  documented Spin1API/SCAMP route before returning to Tier 4.22i.

## Housekeeping

Generated clutter belongs under ignored artifact locations:

- `controlled_test_output/`
- `controlled_test_output/_legacy_artifacts/`
- `reports/` if generated by external tooling
- `cra_demo_output/` if regenerated by the demo
- `.pytest_cache/` and `__pycache__/`

Do not mix source files with generated evidence. If something matters for the
study, summarize it in source docs and register the canonical bundle.
