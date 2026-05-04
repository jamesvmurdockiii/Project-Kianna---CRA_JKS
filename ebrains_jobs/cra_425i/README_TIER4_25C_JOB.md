# Tier 4.25C Two-Core State/Learning Split Repeatability Job

Upload the `cra_425i` folder itself so the JobManager path starts with `cra_425i/`.

This job loads two custom C runtime images onto two SpiNNaker cores:
- Core 4 (app_id=1): `coral_reef_state.aplx` with `RUNTIME_PROFILE=state_core`
- Core 5 (app_id=2): `coral_reef_learning.aplx` with `RUNTIME_PROFILE=learning_core`

The state core holds context/route/memory/schedule. The learning core holds pending/readout.
Inter-core messages use SDP (opcode 30).

Run command (default output dir is tier4_25c_seed42_job_output):

```text
cra_425i/experiments/tier4_25b_two_core_split_smoke.py --mode run-hardware --seed 42
```

For multi-seed repeatability, run three jobs with --seed 42, --seed 43, --seed 44.
Do NOT add --out-dir or --output-dir flags; EBRAINS strips 'out' from arguments.

Pass means the two-core split reproduced the monolithic 4.23c result within tolerance.
