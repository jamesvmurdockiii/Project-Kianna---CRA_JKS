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
  --output-dir /tmp/cra_tier5_45a_runtime_probe_sine_seed42_defaults_2000
```

The probe is operational only. It does not replace the full merged gate.

Observed local runtime note from 2026-05-15: the representative 2000-step
`sine` / seed `42` / `defaults` organism probe was interrupted after `834.71`
seconds real time before completing one full organism scoring cell. This is not
a mechanism result and must not be cited as evidence. It does show that a blind
monolithic local Tier 5.45a run is operationally inappropriate.

A redirected 128-step local health probe completed in `41.884` seconds with
`10/10` criteria, zero synthetic fallback, zero `sim.run` failures, and zero
summary-read failures. This confirms runner plumbing after console redirection,
but it is still noncanonical and does not replace the full 2000-step merged
gate.

## Canonical Shard Strategy

Do not run the full matrix as one blind monolith unless runtime has been proven
acceptable. Prefer one shard per candidate condition, then merge.

Example condition shard:

```bash
python3 experiments/tier5_45a_healthy_nest_rebaseline_scoring.py \
  --conditions enable_neural_heritability \
  --tasks sine,mackey_glass,lorenz,narma10 \
  --seeds 42,43,44 \
  --steps 2000 \
  --output-dir controlled_test_output/tier5_45a_20260515_shard_enable_neural_heritability
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
full_stack
```

The runner repeats reference models in every shard. That is acceptable because
merge mode de-duplicates by `(model, task, seed)`.

If condition shards are still too slow, split further by task or seed. Merge mode
accepts any set of shard directories as long as the final row set is complete.

For long local shards, redirect console output to `/tmp` or another ignored log
path. The generated result bundle is the artifact of record, not the console
stream.

## Final Merge

After all shards finish, merge them into the final Tier 5.45a bundle:

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
controlled_test_output/tier5_45a_20260515_shard_full_stack"

python3 experiments/tier5_45a_healthy_nest_rebaseline_scoring.py \
  --merge-input-dirs "$MERGE_INPUT_DIRS" \
  --conditions all \
  --tasks sine,mackey_glass,lorenz,narma10 \
  --seeds 42,43,44 \
  --steps 2000 \
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
