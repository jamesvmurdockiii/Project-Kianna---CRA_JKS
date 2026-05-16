# Tier 5.45a Sharded Execution Plan

Last updated: 2026-05-15.

This document is the operational run plan for Tier 5.45a, the healthy-NEST
rebaseline scoring gate. It exists because the full gate is large enough that a
single monolithic local run is easy to start accidentally and hard to audit.

## Source Contract

Tier 5.45 locked the contract for this gate. Tier 5.45a implements the scoring
runner.

Source files:

- `experiments/tier5_45_healthy_nest_rebaseline_contract.py`
- `experiments/tier5_45a_healthy_nest_rebaseline_scoring.py`
- `experiments/tier5_45a_shard_orchestrator.py`
- `docs/REPO_ALIGNMENT_REMEDIATION_PLAN.md`
- `docs/MASTER_EXECUTION_PLAN.md`
- `codebasecontract.md`

## Question

Does the corrected healthy-NEST organism path show any promotable mechanism
value after removing fallback-contaminated evidence and keeping experimental
mechanisms opt-in?

## Required Comparisons

The final merged gate must compare:

- `v2_6_predictive_reference`
- `organism_defaults_experimental_off`
- each individual opt-in candidate mechanism
- `full_opt_in_stack`
- external baselines emitted by the runner

Candidate mechanisms:

- `enable_neural_heritability`
- `enable_stream_specialization`
- `enable_variable_allocation`
- `enable_task_fitness_selection`
- `enable_operator_diversity`
- `enable_synaptic_heritability`
- `enable_niche_pressure`
- `enable_signal_transport`
- `enable_energy_economy`
- `enable_maturation`
- `enable_vector_readout`
- `enable_alignment_pressure`
- `enable_task_coupled_selection`
- `enable_causal_credit_selection`
- `enable_cross_polyp_coupling`
- `full_opt_in_stack`

Required tasks and seeds:

- tasks: `sine,mackey_glass,lorenz,narma10`
- seeds: `42,43,44`
- default steps: `2000`
- backend: `nest`
- runtime cadence: `100 ms` of NEST simulation per CRA macro-step

## Noncanonical Smoke And Runtime Probe

Use smoke only for plumbing:

```bash
make tier5-45a-smoke
```

Smoke output is noncanonical and must not be cited as mechanism evidence.

A representative runtime probe may be run to estimate wall time before launching
all shards:

```bash
python3 experiments/tier5_45a_healthy_nest_rebaseline_scoring.py \
  --tasks sine \
  --seeds 42 \
  --conditions defaults \
  --steps 2000 \
  --runtime-ms-per-step 100 \
  --output-dir /tmp/cra_tier5_45a_runtime_probe_sine_seed42_defaults_2000
```

The probe is operational only. It does not replace the full merged gate.

Observed local runtime note from 2026-05-15 before runner revision
`tier5_45a_healthy_nest_rebaseline_scoring_20260515_0002`: the representative 2000-step
`sine` / seed `42` / `defaults` organism probe was interrupted after `834.71`
seconds real time before completing one full organism scoring cell. This is not
a mechanism result and must not be cited as evidence. It exposed that the runner
was not passing `--runtime-ms-per-step` through to `train_adapter_step()`.
Revision `0002` repairs this by using `dt_seconds = runtime_ms_per_step / 1000`.

A redirected 128-step local health probe completed in `41.884` seconds with
`10/10` criteria, zero synthetic fallback, zero `sim.run` failures, and zero
summary-read failures. This confirms runner plumbing after console redirection,
but it is still noncanonical and does not replace the full 2000-step merged
gate.

After revision `0002`, the same redirected 128-step health probe completed in
`21.413` seconds with `10/10` criteria and the same zero-failure diagnostics.

A full 2000-step `sine` / seed `42` / `defaults` cell under revision `0002`
completed in `420.115` seconds with `10/10` criteria, zero synthetic fallback,
zero `sim.run` failures, and zero summary-read failures. This confirms the
repaired runner is valid for full-length scoring, but it also means local
full-matrix execution should be scheduled as small resumable shards.

The shard orchestrator was smoke-validated on 2026-05-15 with a tiny `/tmp`
cell matrix (`defaults`, `sine`, seed `42`, `16` steps, `20 ms` runtime cadence,
population `2`). It successfully detected the pending cell, ran the scoring
runner, marked the cell complete from generated artifacts, and merged the
complete one-cell matrix. This is workflow validation only, not Tier 5.45a
evidence.

Current canonical cell progress as of 2026-05-16:

```text
completed_cells = 14 / 204
completed = organism_defaults_experimental_off / sine,mackey_glass,lorenz,narma10 / seeds 42,43,44; enable_neural_heritability / sine / seeds 42,43
mean_sine_runtime_seconds = 424.926
mean_sine_mse = 0.317516
mean_sine_participation_ratio = 1.917018
mackey_glass_mean_runtime_seconds = 412.473
mackey_glass_mean_mse = 1.764449
mackey_glass_mean_participation_ratio = 2.309325
lorenz_mean_runtime_seconds = 410.410
lorenz_mean_mse = 0.965999
lorenz_mean_participation_ratio = 2.179225
narma10_mean_runtime_seconds = 414.606
narma10_mean_mse = 1.221387
narma10_mean_participation_ratio = 3.434715
enable_neural_heritability_sine_completed_seed_mse_mean = 0.318041
enable_neural_heritability_sine_completed_seed_participation_ratio_mean = 1.941459
criteria = 10/10
synthetic_fallbacks = 0
sim_run_failures = 0
summary_read_failures = 0
next_pending = enable_neural_heritability / sine / seed 44
```

These cells are valid shard artifacts for the eventual merged Tier 5.45a gate, but
it is not interpretable by itself as a mechanism decision.

## Canonical Shard Strategy

Do not run the full matrix as one blind monolith unless runtime has been proven
acceptable. On a local workstation, prefer condition/task/seed shards because
one full 2000-step organism cell currently takes about seven minutes. On a
larger batch system, condition-level shards are acceptable if hour-scale jobs
are reliable.

The preferred local workflow is the shard orchestrator. It tracks completed
condition/task/seed cells, reuses the locked scoring runner for each cell,
redirects long console streams to `/tmp`, and refuses final merge while the
matrix is incomplete unless explicitly told to do a diagnostic incomplete merge.
Default terminal output is compact: it reports counts plus small completed and
pending samples. Use `--verbose-status` only when the full completed/pending
cell list is needed for debugging.

Check status:

```bash
make tier5-45a-shard-status
```

Preview the next cell without running it:

```bash
make tier5-45a-shard-plan
```

Run the next pending cell:

```bash
make tier5-45a-shard-run-next
```

Merge after all cells are complete:

```bash
make tier5-45a-shard-merge
```

Equivalent direct commands:

```bash
python3 experiments/tier5_45a_shard_orchestrator.py --mode status
python3 experiments/tier5_45a_shard_orchestrator.py --mode plan --max-cells 1
python3 experiments/tier5_45a_shard_orchestrator.py --mode run-next --max-cells 1
python3 experiments/tier5_45a_shard_orchestrator.py --mode merge
```

Do not edit shard outputs by hand. If a cell fails or is incomplete, rerun that
same cell through the orchestrator so the final merge remains reproducible.

Example condition shard:

```bash
python3 experiments/tier5_45a_healthy_nest_rebaseline_scoring.py \
  --conditions enable_neural_heritability \
  --tasks sine,mackey_glass,lorenz,narma10 \
  --seeds 42,43,44 \
  --steps 2000 \
  --runtime-ms-per-step 100 \
  --output-dir controlled_test_output/tier5_45a_20260515_shard_enable_neural_heritability
```

Example local cell shard:

```bash
python3 experiments/tier5_45a_healthy_nest_rebaseline_scoring.py \
  --conditions enable_neural_heritability \
  --tasks sine \
  --seeds 42 \
  --steps 2000 \
  --runtime-ms-per-step 100 \
  --output-dir controlled_test_output/tier5_45a_20260515_cell_enable_neural_heritability_sine_seed42 \
  > /tmp/tier5_45a_enable_neural_heritability_sine_seed42.log 2>&1
```

Run one shard for each candidate condition plus `defaults` and `full_stack`:

```text
defaults
enable_neural_heritability
enable_stream_specialization
enable_variable_allocation
enable_task_fitness_selection
enable_operator_diversity
enable_synaptic_heritability
enable_niche_pressure
enable_signal_transport
enable_energy_economy
enable_maturation
enable_vector_readout
enable_alignment_pressure
enable_task_coupled_selection
enable_causal_credit_selection
enable_cross_polyp_coupling
full_opt_in_stack
```

The runner repeats reference models in every shard. That is acceptable because
merge mode de-duplicates by `(model, task, seed)`.

Merge mode accepts any set of shard directories as long as the final row set is
complete, so mixing condition shards and smaller cell shards is allowed. If a
large shard fails, rerun only the missing condition/task/seed cells and include
those replacement dirs in the merge input.

For long local shards, redirect console output to `/tmp` or another ignored log
path. The generated result bundle is the artifact of record, not the console
stream.

## Final Merge

After all shards finish, merge them into the final Tier 5.45a bundle:

```bash
make tier5-45a-shard-merge
```

The manual merge form is still documented below for reviewability and for cases
where a batch system produced condition-level shard directories outside the
orchestrator.

```bash
MERGE_INPUT_DIRS="\
controlled_test_output/tier5_45a_20260515_shard_defaults,\
controlled_test_output/tier5_45a_20260515_shard_enable_neural_heritability,\
controlled_test_output/tier5_45a_20260515_shard_enable_stream_specialization,\
controlled_test_output/tier5_45a_20260515_shard_enable_variable_allocation,\
controlled_test_output/tier5_45a_20260515_shard_enable_task_fitness_selection,\
controlled_test_output/tier5_45a_20260515_shard_enable_operator_diversity,\
controlled_test_output/tier5_45a_20260515_shard_enable_synaptic_heritability,\
controlled_test_output/tier5_45a_20260515_shard_enable_niche_pressure,\
controlled_test_output/tier5_45a_20260515_shard_enable_signal_transport,\
controlled_test_output/tier5_45a_20260515_shard_enable_energy_economy,\
controlled_test_output/tier5_45a_20260515_shard_enable_maturation,\
controlled_test_output/tier5_45a_20260515_shard_enable_vector_readout,\
controlled_test_output/tier5_45a_20260515_shard_enable_alignment_pressure,\
controlled_test_output/tier5_45a_20260515_shard_enable_task_coupled_selection,\
controlled_test_output/tier5_45a_20260515_shard_enable_causal_credit_selection,\
controlled_test_output/tier5_45a_20260515_shard_enable_cross_polyp_coupling,\
controlled_test_output/tier5_45a_20260515_shard_full_opt_in_stack"

python3 experiments/tier5_45a_healthy_nest_rebaseline_scoring.py \
  --merge-input-dirs "$MERGE_INPUT_DIRS" \
  --conditions all \
  --tasks sine,mackey_glass,lorenz,narma10 \
  --seeds 42,43,44 \
  --steps 2000 \
  --runtime-ms-per-step 100 \
  --output-dir controlled_test_output/tier5_45a_20260515_healthy_nest_rebaseline_scoring
```

Keep the comma-separated `--merge-input-dirs` value as one shell argument.

## Pass / Fail Rules

The final merged bundle is the decision gate. Individual shards are not enough.

A clean final pass requires:

- all expected `(model, task, seed)` rows present,
- zero synthetic fallback,
- zero backend simulation failures,
- zero summary/read failures,
- valid task metrics for every required condition,
- mechanism decisions written to `tier5_45a_mechanism_decisions.csv`,
- generated report and manifest present,
- `make validate` passing after any registry/doc update.

Promotion is not automatic. A mechanism can only be promoted if it satisfies the
predeclared improvement and attribution rules in the Tier 5.45 contract and the
Tier 5.45a report.

## Decision Outcomes

Use these outcomes after the merged run:

- `no_promotion`: v2.6 remains predictive baseline and v2.7 remains diagnostic
  NEST snapshot.
- `single_mechanism_candidate`: write a separate promotion/regression gate before
  freezing any new baseline.
- `full_stack_candidate`: write a separate full-stack promotion/regression gate
  before freezing any new baseline.
- `backend_or_fallback_failure`: repair runner/backend first; do not interpret
  mechanism scores.
- `incomplete_matrix`: finish or rerun missing shards; do not register the final
  gate.

## Console Noise

Local NEST may print cleanup warnings such as `Cleanup called without calling
Prepare`. These warnings are not evidence by themselves. Trust the generated
backend diagnostics and pass/fail criteria. If the console noise becomes
operationally disruptive, redirect stdout/stderr to an ignored log file while
preserving the generated bundle:

```bash
python3 experiments/tier5_45a_healthy_nest_rebaseline_scoring.py ... \
  > /tmp/tier5_45a_shard.log 2>&1
```

Do not commit large raw console logs.

## Registration Rule

Do not add Tier 5.45a to `experiments/evidence_registry.py` until the final
merged bundle is complete, reviewed, and its claim boundary is documented. After
registration, run:

```bash
make validate
```
